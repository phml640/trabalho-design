# ADR-004 — Notificações após a chamada de senha

- **Data:** 2026-11-01
- **Status:** Aceito
- **Relacionados:** [ADR-002](ADR-002-monolito-modular-hexagonal-eventos.md), [ADR-003](ADR-003-postgresql-persistencia.md), [requisitos](../requisites.md)

## Contexto

O usuário deve ser avisado no celular quando sua senha for chamada. O canal concreto ainda não foi escolhido. A chamada precisa permanecer válida mesmo se o provedor de mensagens estiver lento ou indisponível. O trabalho pede uma dependência externa substituível, que pode ser simulada no protótipo.

## Problema e forças envolvidas

Enviar a mensagem dentro da transação prolongaria o bloqueio da fila e poderia reverter uma chamada legítima por uma falha externa. Enviar apenas depois do commit, sem registrar a intenção de envio, pode perder a notificação se o processo cair entre o commit e a chamada ao provedor. A integração precisa tolerar reenvio sem multiplicar mensagens indevidamente.

## Alternativas consideradas

### 1. Envio síncrono durante a chamada

É simples e informa imediatamente o resultado do provedor. Aumenta a latência, mantém bloqueios abertos e acopla a operação central à disponibilidade externa.

### 2. Envio assíncrono apenas em memória

Desacopla a resposta HTTP do envio e tem implementação curta. Reinícios e falhas do processo podem apagar notificações pendentes.

### 3. Evento persistido em outbox e adaptador de notificação

Registra a intenção de envio na mesma transação da chamada e permite processá-la depois. Requer rotina de entrega, tentativas, tratamento de falhas e limpeza dos registros processados.

## Decisão

Adotar a terceira alternativa. O caso de uso `ChamarProximaSenha` registra o evento `SenhaChamada` na outbox junto com a alteração da senha e o histórico. Um processador lê eventos pendentes e invoca a porta `Notificador`, cuja implementação inicial será um **notificador simulado** que registra a tentativa para demonstração e testes. Um adaptador futuro poderá enviar SMS, WhatsApp ou outra mensagem ao celular sem mudar a política de prioridade nem o caso de uso.

A entrega é **posterior ao commit** e tem semântica de **pelo menos uma tentativa**; falhas transitórias geram novas tentativas. Cada evento possui identificador estável, usado como chave de idempotência pelo processador e, quando disponível, pelo provedor. Não se promete exatamente uma entrega, pois o provedor pode receber a mensagem e a confirmação se perder. O registro de tentativas, erros e horário de sucesso permitirá identificar falhas permanentes para tratamento operacional. A resposta da chamada confirma que a notificação foi **solicitada**, não que chegou ao celular.

Dados de contato são acessados apenas pelo adaptador autorizado e não devem aparecer em logs ou no evento além do mínimo necessário. A retenção desses dados e a escolha do canal dependerão das regras do serviço e da implementação concreta.

## Consequências positivas

- Falha do notificador não desfaz uma chamada já confirmada.
- A intenção de notificar não se perde entre a transação da chamada e o processamento posterior.
- O tempo de resposta da chamada não depende do tempo de resposta do provedor.
- A porta `Notificador` permite simulação, testes e troca de canal.

## Consequências negativas, custos e riscos

- A notificação pode chegar com atraso ou ser repetida se o provedor não oferecer idempotência.
- É preciso executar e observar o processador da outbox, inclusive no protótipo que demonstrar o fluxo.
- Uma outbox acumulada exige política de tentativas, diagnóstico e retenção.
- A troca de provedor pode exigir novos dados de contato, consentimento ou formato de mensagem; a interface reduz o acoplamento, mas não elimina esse trabalho.

## Critérios para revisar a decisão

Reavaliar se o serviço exigir confirmação de entrega antes de considerar a chamada concluída, se a latência de notificação medida não atender à operação, ou se o volume justificar um mensageiro dedicado. Nesse caso, ainda será necessário preservar a gravação atômica da intenção de envio.

## Situação na entrega do protótipo

O caso de uso conceitual `ChamarProximaSenha` corresponde ao método
`GerenciadorDeSenhas.chamar_proxima_senha`. Outbox, tentativas e mensagens do
`FakeNotificador` estão persistidas. O processador fecha a transação de reserva
antes de invocar o adaptador; o Fake usa uma transação própria para registrar a
mensagem. Não há provedor de celular, dados de contato ou worker automático.
Novas tentativas e a retomada de reservas expiradas dependem de outra solicitação
manual de processamento. Assim, a intenção é durável, mas não há garantia de
tentativa automática sem acionar o processador. Endpoints e exemplos estão na
[API](../api.md#notificações-e-demonstração-de-falha).
