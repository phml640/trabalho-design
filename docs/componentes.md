# Levantamento de componentes, atores e dependências — Sistema de Gestão de Filas

## 1. Contexto e escopo

Este documento indentifica os componentes, atores e dependências.
---

## 2. Componentes do sistema

### 2.1. Componentes arquiteturais internos

| Componente | Responsabilidade |
|---|---|
| API REST | Receber requisições HTTP, validar entradas, autenticar e autorizar quando implementado, traduzir erros e retornar respostas. | `api` |
| Casos de uso | Coordenar operações da aplicação, transações e chamadas às portas de saída. |
| Domínio | Concentrar entidades, estados, invariantes, política de prioridade e eventos de domínio. |
| Infraestrutura | Implementar adaptadores de persistência, processamento de eventos e notificação. |
| Gerenciador de filas | Coordenar operações e consultas relacionadas às filas. |
| Gerenciador de senhas | Emitir, consultar, chamar e controlar o estado das senhas. |
| Gerenciador de atendimentos | Controlar início e finalização de atendimentos e associação com atendente e guichê. |
| Política de prioridade | Selecionar a próxima senha respeitando a regra de prioridade e o contador de chamadas prioritárias consecutivas. |
| Gerenciador de histórico | Registrar transições de estado de senhas e atendimentos. |
| Gerenciador de virada diária | Garantir a mudança do dia operacional, tratar senhas antigas e reiniciar o contador pertinente. |
| Registro de eventos internos | Representar fatos ocorridos no domínio, como `SenhaChamada`. |
| Processador da Outbox | Ler eventos pendentes, invocar o notificador, controlar tentativas e registrar sucesso ou falha. |
| Adaptador de persistência | Implementar as portas de persistência usando SQLAlchemy e PostgreSQL. |
| Adaptador de notificação | Implementar a porta `Notificador`, inicialmente com um notificador simulado. |


### 2.2. Componentes de persistência e dados

| Componente / estrutura | Responsabilidade |
|---|---|
| Banco PostgreSQL | Persistir os dados do sistema com transações, integridade referencial e bloqueio de concorrência. |
| Tabela / entidade de fila | Armazenar as filas e os dados necessários à coordenação das operações, incluindo o dia operacional e contadores pertinentes. |
| Tabela / entidade de senha | Persistir senhas, identificadores, número exibido, classe, estado e dados de emissão. |
| Tabela / entidade de atendimento | Persistir atendimentos e associações com senha, atendente e guichê. |
| Tabela / estrutura de histórico | Registrar transições de estado e horários correspondentes. |
| Tabela Outbox | Persistir eventos a processar, na mesma transação da mudança de estado que os originou. |
| Índices de fila | Apoiar consultas por fila, dia operacional, estado, classe e ordem de emissão. |
| Índices de histórico | Apoiar consultas do histórico por senha e horário. |

### 2.3. Componentes tecnológicos

| Tecnologia / componente | Finalidade |
|---|---|
| FastAPI 0.115 ou superior, abaixo da versão 1 | Interface HTTP e geração da documentação OpenAPI. |
| Uvicorn 0.30 ou superior, abaixo da versão 1 | Servidor ASGI da aplicação. |
| setuptools | Build e empacotamento do projeto. |
| Layout `src` | Organizar o pacote em `src/gestao_filas`. |
| PostgreSQL | Banco de dados relacional. |
| SQLAlchemy | Mapeamento objeto-relacional e acesso transacional ao banco. |
| Alembic | Migrações versionadas do esquema do banco. |
| OpenAPI / Swagger UI | Descrever e explorar o contrato HTTP da API. |

### 2.4. Componentes externos e clientes

| Componente | Responsabilidade | Situação nos ADRs |
|---|---|---|
| Interface do usuário / cliente | Consumir a API para emitir e consultar senhas e acompanhar informações da fila. | Cliente previsto; tecnologia não definida. |
| Interface do atendente | Consumir a API para chamar senhas e gerenciar atendimentos. | Cliente previsto; tecnologia não definida. |
| Totem de autoatendimento | Consumir a API para emissão presencial de senhas. | Cliente previsto; tecnologia não definida. |
| Provedor de notificações | Encaminhar mensagens ao celular do usuário. | Dependência externa substituível; provedor concreto não escolhido. |

---

## 3. Atores do sistema

### 3.1. Atores humanos

| Ator | Responsabilidades / interações | Situação |
|---|---|---|
| Usuário (cliente) | Solicitar emissão de senha, consultar senha ou fila e receber notificação quando sua senha for chamada. | Decorre dos requisitos descritos nos ADRs. |
| Atendente | Solicitar chamada da próxima senha, iniciar atendimento e finalizar atendimento. | Decorre dos fluxos descritos nos ADRs. |
| Administrador | Poderia administrar filas, guichês, atendentes e configurações, caso essas funcionalidades sejam definidas. | Ator possível; atribuições não especificadas nos ADRs. |
| Operador do sistema | Poderia acompanhar falhas, tentativas e eventos pendentes da Outbox para suporte operacional. | Ator possível; interface e permissões não especificadas. |

### 3.2. Atores / sistemas externos

| Ator ou sistema | Responsabilidades / interações | Situação |
|---|---|---|
| Totem de autoatendimento | Atuar como cliente da API para solicitar emissão presencial de senhas. | Cliente previsto no contexto do sistema. |
| Provedor de notificações | Receber solicitações do adaptador e tentar entregar mensagens ao usuário. | Dependência externa prevista, ainda sem fornecedor ou canal definido. |
| Interface web ou aplicativo do usuário | Consumir endpoints da API para operações do usuário. | Possível cliente; tecnologia não definida. |
| Interface do atendente | Consumir endpoints da API para operações do atendente. | Possível cliente; tecnologia não definida. |

---

## 4. Dependências do sistema

### 4.1. Dependências arquiteturais e direção do código

| Origem | Destino / contrato utilizado | Explicação |
|---|---|---|
| `api` | `application` | A API chama os casos de uso e traduz requisições e respostas HTTP. |
| `application` | `domain` | Os casos de uso utilizam entidades, regras e eventos do domínio. |
| `infrastructure` | Portas definidas em `application` | Os adaptadores implementam contratos de persistência e notificação definidos pela aplicação. |
| `infrastructure` | `domain` | Os adaptadores podem mapear entidades e tratar eventos de domínio, sem transferir detalhes técnicos para o domínio. |
| Processador da Outbox | Porta `Notificador` | O processador solicita o envio por meio de uma interface substituível. |
| Adaptador de persistência | PostgreSQL | O adaptador executa consultas e transações no banco. |
| Adaptador de notificação | Provedor externo | O adaptador integra com o canal de mensagens escolhido. |

A composição concreta dos adaptadores ocorre na borda da aplicação. O domínio não deve depender diretamente de FastAPI, SQLAlchemy, PostgreSQL ou de um provedor externo.

### 4.2. Dependências tecnológicas

| Dependência | Consumidor / componente | Finalidade |
|---|---|---|
| Python 3.11+ | Backend | Execução do código da aplicação. |
| FastAPI | API REST | Roteamento HTTP, validação e documentação OpenAPI. |
| Uvicorn | Aplicação ASGI | Servir a API HTTP. |
| setuptools | Projeto | Build e empacotamento. |
| SQLAlchemy | Adaptador de persistência | Mapeamento e acesso transacional ao banco. |
| Alembic | Persistência | Aplicar e versionar migrações. |
| PostgreSQL | Adaptador de persistência | Armazenar os dados do sistema. |
| Biblioteca / SDK do provedor | Adaptador de notificação | Integrar com o serviço de mensagens, quando escolhido. |

A biblioteca ou SDK do provedor de notificações ainda não foi definido. O notificador inicial é simulado.

### 4.3. Dependências de execução

| Dependência | Necessidade | Observação |
|---|---|---|
| Ambiente Python | Necessário para executar o backend. | Versão mínima definida no ADR-001. |
| Servidor ASGI (Uvicorn) | Necessário para disponibilizar a API HTTP. | Executa a aplicação FastAPI. |
| PostgreSQL | Necessário para persistência confiável no ambiente do protótipo. | Deve estar disponível para operações persistidas. |
| Migrações Alembic | Necessárias para criar e evoluir o esquema do banco. | Migrações versionadas. |
| Processador da Outbox | Necessário para demonstrar o processamento posterior dos eventos de notificação. | Precisa ser executado e observado. |
| Provedor externo de mensagens | Necessário para entrega real de mensagens. | Não é necessário para o protótipo se o notificador simulado for utilizado. |

### 4.4. Dependências de negócio e dados

O modelo inicial de persistência contempla:

- Fila;
- Senha;
- Atendimento;
- Histórico de transições;
- Mensagem / evento de saída na Outbox.

As associações devem usar identificadores internos estáveis e chaves estrangeiras. O número exibido da senha não substitui seu identificador interno e é único no escopo de fila, dia operacional e classe.

Os horários são armazenados com referência temporal inequívoca (UTC). O dia operacional é calculado em `America/Sao_Paulo` e armazenado separadamente.

---

## 5. Relacionamento entre atores e componentes

| Ator | Componente / interface acessada | Operações |
|---|---|---|
| Usuário | API REST | Solicitar emissão e consulta de senha. |
| Usuário | Casos de uso de senhas / filas, por meio da API | Consultar estado e informações da fila. |
| Usuário | Canal externo de notificação | Receber aviso quando a senha for chamada. |
| Atendente | API REST | Solicitar chamada e gerenciar atendimentos. |
| Atendente | Casos de uso de filas e senhas, por meio da API | Consultar fila e chamar próxima senha. |
| Atendente | Casos de uso de atendimento, por meio da API | Iniciar e finalizar atendimento. |
| Totem | API REST | Solicitar emissão de senha. |
| Administrador | API REST / funcionalidades administrativas | Administrar filas, guichês, atendentes ou configurações, se implementado. |
| Operador do sistema | Ferramentas operacionais / monitoramento | Acompanhar tentativas, falhas e eventos pendentes, se disponibilizado. |
| Provedor de notificações | Adaptador de notificação | Receber solicitações de envio e retornar resultado da tentativa. |

---

## 6. Fluxos relevantes entre componentes

### 6.1. Emissão de senha

Fluxo conceitual:

1. Usuário ou totem envia uma requisição à API REST.
2. A API valida a entrada e encaminha ao caso de uso de emissão.
3. O caso de uso coordena a operação com o domínio e a porta de persistência.
4. A persistência sincroniza a operação com a linha da fila, garantindo coerência com a virada diária e a numeração.
5. A senha é persistida no PostgreSQL.
6. A API retorna o resultado ao cliente.

### 6.2. Consulta da fila ou senha

1. Usuário ou atendente solicita uma consulta pela API.
2. A API encaminha a solicitação ao caso de uso correspondente.
3. O caso de uso garante a virada diária pendente quando necessário.
4. O adaptador consulta o PostgreSQL, aplicando os filtros e a paginação pertinentes.
5. A API retorna os dados ao cliente.

### 6.3. Chamada da próxima senha

1. O atendente solicita a chamada pela API REST.
2. A API valida a requisição e invoca o caso de uso `ChamarProximaSenha`.
3. O caso de uso inicia uma transação.
4. O adaptador de persistência bloqueia a linha da fila com `SELECT ... FOR UPDATE`.
5. A operação executa a virada diária pendente, se necessário.
6. O domínio aplica a política de prioridade e seleciona uma senha aguardando.
7. A senha passa ao estado `chamada` e é associada ao atendente e ao guichê.
8. O contador de chamadas prioritárias é atualizado.
9. A transição é registrada no histórico.
10. O evento `SenhaChamada` é inserido na Outbox.
11. A transação é confirmada.
12. A API responde sem aguardar o provedor externo.
13. Após o commit, o processador da Outbox lê o evento pendente.
14. O processador invoca a porta `Notificador`.
15. O adaptador de notificação tenta encaminhar a mensagem ao provedor.
16. O resultado da tentativa é registrado para acompanhamento e reprocessamento, quando aplicável.

**Garantia importante:** a transação local inclui a alteração da senha, o contador, o histórico e a inserção do evento na Outbox. O envio externo ocorre depois do commit e não desfaz uma chamada já confirmada.

### 6.4. Início e finalização do atendimento

1. O atendente solicita o início ou a finalização pela API.
2. O caso de uso valida a transição permitida.
3. A persistência bloqueia a senha quando necessário.
4. Estado e histórico são atualizados na mesma transação.
5. A transação é confirmada ou revertida integralmente em caso de erro.

A finalização de um atendimento iniciado no dia anterior continua permitida, conforme o ADR-003.

---

## 7. Resumo

| Categoria | Elementos |
|---|---|
| Atores humanos identificados | Usuário, Atendente. |
| Atores humanos possíveis | Administrador, Operador do Sistema. |
| Clientes / sistemas externos | Totem, interface do usuário, interface do atendente. |
| Serviço externo | Provedor de notificações. |
| Módulos arquiteturais | `api`, `application`, `domain`, `infrastructure`. |
| Responsabilidades funcionais | Filas, senhas, atendimentos, prioridade, histórico e virada diária. |
| Componentes de processamento | Casos de uso, processador da Outbox e composição da aplicação. |
| Componentes de persistência | Adaptador de persistência, PostgreSQL e estruturas de fila, senha, atendimento, histórico e Outbox. |
| Componentes de integração | Porta `Notificador`, adaptador de notificação e provedor externo. |
| Tecnologias | Python, FastAPI, Uvicorn, setuptools, PostgreSQL, SQLAlchemy e Alembic. |
| Contrato de API | OpenAPI / Swagger UI. |
| Padrões arquiteturais | Monólito modular, Arquitetura Hexagonal, Ports and Adapters, eventos internos e Outbox Pattern. |
