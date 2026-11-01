# ADR-003 — PostgreSQL e estratégia de persistência

- **Data:** 2026-11-01
- **Status:** Aceito
- **Relacionados:** [ADR-002](ADR-002-monolito-modular-hexagonal-eventos.md), [requisitos](../requisites.md), [ADR-004](ADR-004-notificacoes.md)

## Contexto

Senhas, atendimentos e histórico precisam sobreviver ao reinício da aplicação. Duas chamadas simultâneas não podem escolher a mesma senha. A virada diária deve retirar senhas antigas da fila ativa sem destruir o histórico. A solicitação de notificação deve ser persistida junto da chamada.

## Problema e forças envolvidas

O banco deve oferecer transações, bloqueio de concorrência, integridade referencial e consultas eficientes por fila e dia. A estratégia deve caber no protótipo e permitir evolução por migrações. O ASR03 recomenda isolar SQL e modelos de persistência dos casos de uso e do domínio.

## Alternativas consideradas

### 1. Memória ou arquivo local

Simplifica os primeiros testes, mas não entrega persistência confiável, concorrência entre processos nem recuperação adequada após falhas. Serve apenas como adaptador de teste.

### 2. SQLite

Tem configuração mínima e transações, sendo útil em testes locais. Seu modelo de concorrência de escrita é menos adequado à estratégia de várias chamadas simultâneas e bloqueio por fila; também não representa o ambiente PostgreSQL da implantação proposta.

### 3. PostgreSQL

Oferece transações ACID, integridade referencial, bloqueio de linhas e índices. Exige instalação/configuração do serviço, migrações e testes de integração com banco real.

## Decisão

Adotar **PostgreSQL** como banco do protótipo. O adaptador de persistência ficará em `infrastructure`, implementando portas da `application`; modelos ORM e consultas SQL não atravessam essas portas. Usar **SQLAlchemy** para mapeamento e acesso transacional e **Alembic** para migrações versionadas. Essas dependências serão adicionadas quando a persistência for implementada.

O modelo inicial terá entidades persistidas para fila, senha, atendimento, histórico de transições e mensagem de saída (*outbox*). Identificadores internos estáveis e chaves estrangeiras preservam associações entre usuário, senha, atendente e guichê. Horários são armazenados com referência temporal inequívoca (UTC); o dia operacional é calculado em `America/Sao_Paulo` e armazenado separadamente para consulta e índices. Número exibido da senha é único no escopo de fila, dia operacional e classe, sem substituir o identificador interno.

### Transação de chamada

1. Iniciar a transação e bloquear a linha da fila com `SELECT ... FOR UPDATE`.
2. Executar a virada diária pendente, se necessário, ainda sob esse bloqueio; atualizar o dia operacional e zerar o contador de chamadas prioritárias consecutivas. A emissão, o início de atendimento e a consulta da fila ativa também devem garantir essa virada antes de agir ou responder; a operação de consulta pode acioná-la por meio de um caso de uso transacional.
3. Buscar as senhas **aguardando** do dia atual em ordem de emissão, aplicar a política e selecionar uma única senha. A emissão para a mesma fila também deve sincronizar com a linha da fila, para que a virada e a numeração de senhas sejam coerentes.
4. Alterar a senha para **chamada**, associar atendente e guichê, atualizar o contador, gravar a transição no histórico e inserir `SenhaChamada` na outbox.
5. Confirmar a transação. Erro antes do commit reverte todas essas alterações. O processamento da outbox ocorre depois, em outra transação.

O bloqueio por fila evita que duas chamadas concorrentes leiam o mesmo contador e selecionem a mesma senha. Início e finalização de atendimento devem validar o estado anterior e persistir estado e histórico na mesma transação, usando bloqueio da senha quando necessário. Operações de virada e encerramento administrativo também devem bloquear a fila, executar cancelamentos e histórico juntos e ser idempotentes. A finalização de um atendimento iniciado no dia anterior continua permitida.

Índices iniciais devem apoiar `(fila_id, dia_operacional, estado, classe, emitida_em, id)` e consultas ao histórico por senha e horário. Consultas de fila serão paginadas. O esquema e os índices serão ajustados após medir o ASR02; nenhum resultado de desempenho é pressuposto aqui.

## Consequências positivas

- Estado, histórico, contador e evento de saída ficam consistentes em uma transação local.
- Bloqueio por fila torna a política de prioridade determinística sob chamadas concorrentes.
- Histórico permanece acessível após virada ou encerramento administrativo.
- Migrações versionadas tornam a evolução do esquema reproduzível.
- A porta de persistência permite testar casos de uso sem depender do ORM.

## Consequências negativas, custos e riscos

- PostgreSQL adiciona um serviço obrigatório ao ambiente e aos testes de integração.
- O bloqueio da fila pode formar gargalo em filas muito concorridas; transações devem ser curtas e não incluir chamadas externas.
- Índices e histórico têm custo de armazenamento e escrita.
- A troca de banco exigirá reimplementar consultas, migrações e garantias de concorrência do adaptador; a porta protege regras de negócio, mas não elimina esse trabalho.
- É necessário tratar falhas de conexão, reversões e tentativas repetidas sem duplicar transições ou notificações.

## Critérios para revisar a decisão

Reavaliar se testes de carga mostrarem contenção excessiva por fila, se o volume histórico exigir particionamento ou retenção definida, ou se restrições de implantação impedirem PostgreSQL. Qualquer alternativa precisa preservar as invariantes de seleção, histórico e outbox.
