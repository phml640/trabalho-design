# Sistema de gestão de filas e atendimento presencial
---

## Contexto Geral
Sistema para organizar filas de atendimento, emitir senhas, aplicar regras de prioridade, chamar usuários e registrar o histórico dos atendimentos realizados.

## Principais Atores
O grupo identificou os seguintes atores do sistema:
- Administrador
- Usuário
- Atendente

## Requisitos funcionais
1. Emitir uma senha vinculada a uma fila de atendimento.
2. Poder emitir senhas de forma online ou através de totens
3. Classificar a senha emitida como normal ou prioritária.
4. Consultar as senhas presentes em uma fila de atendimento.
5. Selecionar a próxima senha segundo a política de prioridade vigente.
6. Permitir que um atendente chame a próxima senha para um guichê.
7. Poder iniciar um atendimento associado a uma senha.
8. Poder finalizar um atendimento associado a uma senha.
9. Ao realizar a chamada de uma senha, o usuário que a emitiu deve receber notificações em seu celular o avisando de que a senha foi chamada.
10. Um administrador pode esvaziar uma fila de atendimento.
11. Após o início de um novo dia, todas as senhas que estiverem presentes do dia anterior devem ser descartadas.
12. Após início do atendimento, ou finalização, deve ser salvo o histórico com o usuário atendido e o atendente que realizou o atendimento. 

## Restrições
Utilização de banco de dados para o histórico persistente.

## Requisitos arquiteturalmente significativos (ASRs)
- Disponibilidade e continuidade de atendimento: o sistema deve manter o funcionamento mesmo com picos de demanda, permitindo emissão e chamada de senhas com baixa indisponibilidade, especialmente em horários de maior movimento.
- Tempo de resposta rápido: operações críticas, como emitir uma senha, consultar filas e chamar a próxima senha, devem ocorrer em tempo quase imediato para evitar filas longas e espera frustrante.
- Consistência dos dados de atendimentos e histórico: as alterações de status da senha, início e finalização de atendimento e gravação do histórico devem ser persistidas de forma confiável, sem perdas ou inconsistências.
- Integridade da política de prioridade: a seleção da próxima senha deve seguir sempre a regra vigente de prioridade, evitando erros de atendimento e garantindo justiça no processo.
- Notificações confiáveis ao usuário: quando uma senha for chamada, a comunicação ao cliente deve ser entregue de forma segura e oportuna, considerando o canal de celular e a necessidade de atualização em tempo real.
- Escalabilidade por múltiplos pontos de acesso: o sistema deve suportar uso simultâneo por vários usuários, atendentes e totens, sem degradar a experiência de quem acessa as filas.
- Segurança e controle de acesso: o sistema deve separar permissões entre administrador, atendente e usuário, protegendo ações sensíveis como esvaziar filas, iniciar/encerrar atendimentos e visualizar histórico.
- Persistência e rastreabilidade: o histórico de atendimentos deve ser armazenado em banco de dados para permitir consultas futuras, auditoria e geração de relatórios de operação.
