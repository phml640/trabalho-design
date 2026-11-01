# Sistema de gestão de filas e atendimento presencial

## Contexto e atores

O sistema organiza filas de atendimento, emite senhas, aplica prioridades, chama usuários e mantém o histórico dos atendimentos. Seus atores são **usuário**, **atendente** e **administrador**. Totem e cliente online são canais de acesso do usuário.

## Requisitos funcionais

| ID | Requisito |
| --- | --- |
| RF01 | Emitir uma senha vinculada a uma fila, por canal online ou totem, identificando o usuário e o dia de atendimento. |
| RF02 | Classificar a senha como normal ou prioritária conforme os critérios de elegibilidade adotados pelo serviço. |
| RF03 | Consultar as senhas de uma fila e suas situações, com acesso restrito aos dados pessoais conforme o papel do solicitante. |
| RF04 | Selecionar e chamar a próxima senha para um guichê conforme a política de prioridade, registrando o atendente responsável. |
| RF05 | Iniciar e finalizar o atendimento de uma senha chamada, mantendo sua associação ao atendente e ao guichê. |
| RF06 | Registrar e consultar o histórico de emissão, chamada, início, finalização e cancelamento das senhas e dos atendimentos. |
| RF07 | Notificar o usuário no celular quando sua senha for chamada, registrando a solicitação e o resultado da entrega; no protótipo, a entrega pode ser simulada. |
| RF08 | Permitir que o administrador encerre uma fila para novas emissões e chamadas e cancele suas senhas ainda em espera ou chamadas sem atendimento iniciado. |
| RF09 | Encerrar automaticamente as senhas remanescentes de dias anteriores ao iniciar o dia operacional seguinte, preservando o histórico. |

Os RFs consolidam os 12 itens originais: RF01 reúne emissão e canais; RF04 reúne seleção e chamada; RF05 reúne início e fim do atendimento; RF06 incorpora o registro do histórico; RF09 explicita o descarte diário sem exclusão física.

## Regras de negócio

### Prioridade e ordem de chamada

1. Dentro de cada classe (normal ou prioritária), a ordem é FIFO: primeiro a data e hora de emissão, depois o identificador da senha como critério de desempate.
2. Havendo senhas das duas classes, são chamadas no máximo **duas prioritárias consecutivas** antes de chamar uma normal. Após chamar uma normal, o contador consecutivo volta a zero.
3. Se só houver uma classe aguardando, chama-se a senha mais antiga dessa classe. Chamadas prioritárias nesse caso continuam contando; assim, uma senha normal que chegar após duas prioritárias será a próxima a ser chamada.
4. O contador pertence à fila e ao dia operacional. A seleção, a atualização do contador e a chamada da senha ocorrem numa única transação, para que chamadas simultâneas não escolham a mesma senha.
5. Apenas senhas **aguardando** participam da seleção. Senhas chamadas, em atendimento, finalizadas ou canceladas não voltam à fila automaticamente.

O ciclo regular da senha é **aguardando → chamada → em atendimento → finalizada**. O cancelamento pode partir de **aguardando** ou **chamada** nas condições de encerramento descritas abaixo. Início e finalização de atendimento exigem o estado imediatamente anterior do ciclo regular.

Exemplo: com `N001`, `N002`, `P001`, `N003`, `P002` aguardando nessa ordem de emissão, as chamadas são `P001`, `P002`, `N001`, `N002`, `N003`.

### Encerramento diário e histórico

- O dia operacional segue a data civil no fuso **America/Sao_Paulo**. Na primeira operação do novo dia que emite ou chama uma senha, inicia um atendimento ou consulta a fila ativa, o sistema executa a virada de modo idempotente antes da operação. Um agendamento pode antecipá-la, mas não é necessário para a correção da regra.
- Na virada, senhas anteriores ainda **aguardando** ou **chamadas sem atendimento iniciado** passam a **canceladas**, com motivo `encerramento_diario`. Elas deixam de ser elegíveis para chamada ou início de atendimento. O contador de prioridade do novo dia começa em zero.
- Atendimentos já **em andamento** podem ser finalizados após a meia-noite; conservam o dia de emissão da senha e os horários reais de início e fim. Senhas finalizadas ou canceladas não mudam de estado.
- A ação administrativa de encerrar uma fila aplica o mesmo cancelamento às senhas aguardando ou chamadas, com motivo `encerramento_administrativo`; não interrompe atendimentos em andamento. A reabertura da fila exige ação administrativa e não reativa senhas canceladas.
- Nenhuma senha ou evento histórico é apagado na virada ou no encerramento administrativo. A consulta da fila ativa considera apenas o dia operacional corrente e exclui estados finais; o histórico pode consultar dias anteriores.

### Notificações

Chamar uma senha confirma a mudança de estado e registra uma solicitação de notificação. A entrega ao celular ocorre depois da confirmação e pode falhar ou atrasar sem desfazer a chamada. O canal concreto e os dados de contato necessários serão definidos na implementação; a interface permite usar um notificador simulado no protótipo. Ver [ADR-004](adr/ADR-004-notificacoes.md).

## Restrições e requisitos complementares

- O histórico deve permanecer em banco de dados persistente, incluindo usuário, atendente, guichê, horários e motivo de cancelamento quando aplicável.
- Ações administrativas e de atendimento exigem autorização conforme o papel. Consultas públicas não devem revelar dados pessoais de outras senhas.
- Os critérios que conferem prioridade devem ser definidos pelo serviço e validados na emissão; o tipo prioritário não pode depender apenas de uma escolha não verificada do cliente.
- A identificação de usuário e os dados de contato devem ser limitados ao necessário para atendimento e notificação.

## Requisitos arquiteturalmente significativos (ASRs)

| ID | Requisito e cenário verificável | Influência arquitetural |
| --- | --- | --- |
| ASR01 — Integridade e consistência | Com dois atendentes chamando simultaneamente a mesma fila e ao menos uma senha aguardando, cada senha deve ser atribuída a no máximo um atendimento. Estado da senha, contador de prioridade, registro histórico e solicitação de notificação devem ser confirmados juntos ou revertidos juntos. | Transação no PostgreSQL, bloqueio por fila, invariantes no caso de uso e persistência atômica do evento de saída. |
| ASR02 — Desempenho sob concorrência | Como meta inicial para validação do protótipo, emissão, consulta da fila ativa e chamada devem ter latência p95 de até **500 ms** com **50 clientes concorrentes** e **10 mil senhas armazenadas**, em ambiente de teste definido e documentado. O tempo de entrega da notificação externa fica fora dessa medição. | Índices por fila, dia, estado e ordem de emissão; consultas paginadas; transações curtas; medição de carga antes de otimizar ou escalar. A meta é um critério a verificar, não um resultado já demonstrado. |
| ASR03 — Modificabilidade das integrações | Ao trocar PostgreSQL por outro mecanismo de persistência, ou o canal de notificação por outro provedor, regras de prioridade e casos de uso devem permanecer inalterados; a mudança deve ficar concentrada nos adaptadores e na configuração. | Portas de saída, adaptadores, inversão de dependência e eventos internos para isolar efeitos externos. Testes de contrato deverão verificar as implementações das portas. |

Segurança, disponibilidade e rastreabilidade continuam relevantes como restrições e requisitos complementares. Os três ASRs acima foram selecionados por afetarem diretamente as decisões arquiteturais e a fatia vertical prevista para o protótipo.
