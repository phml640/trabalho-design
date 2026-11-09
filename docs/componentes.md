# Levantamento de componentes, atores e dependências — Sistema de Gestão de Filas

## 1. Contexto e escopo

Este documento indentifica os componentes, atores e dependências.
---

## 2. Componentes do sistema

### 2.1. Componentes arquiteturais internos

| Componente | Responsabilidade |
|---|---|
| API REST | Receber requisições HTTP, validar entradas, autenticar e autorizar quando implementado, traduzir erros e retornar respostas. | `api` |
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

### 2.2. Componentes externos e clientes

| Componente | Responsabilidade | Situação nos ADRs |
|---|---|---|
| Interface do usuário / cliente | Consumir a API para emitir e consultar senhas e acompanhar informações da fila. | Cliente previsto; tecnologia não definida. |
| Interface do atendente | Consumir a API para chamar senhas e gerenciar atendimentos. | Cliente previsto; tecnologia não definida. |
| Totem de autoatendimento | Consumir a API para emissão presencial de senhas. | Cliente previsto; tecnologia não definida. |
| Provedor de notificações | Encaminhar mensagens ao celular do usuário. | Dependência externa substituível; provedor concreto não escolhido. |
| Serviço de Persistência | Persistir os dados do sistema com transações, integridade referencial e bloqueio de concorrência. | Definido o uso de PostgresSQL |

---

## 3. Atores do sistema

| Ator | Responsabilidades / interações | Situação |
|---|---|---|
| Usuário (cliente) | Solicitar emissão de senha, consultar senha ou fila e receber notificação quando sua senha for chamada. | Decorre dos requisitos descritos nos ADRs. |
| Atendente | Solicitar chamada da próxima senha, iniciar atendimento e finalizar atendimento. | Decorre dos fluxos descritos nos ADRs. |
| Administrador | Poderia administrar filas, guichês, atendentes e configurações, caso essas funcionalidades sejam definidas. | Ator possível; atribuições não especificadas nos ADRs. |
| Operador do sistema | Poderia acompanhar falhas, tentativas e eventos pendentes da Outbox para suporte operacional. | Ator possível; interface e permissões não especificadas. |
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

---

## 6. Interfaces e mecanismos de comunicação

Os componentes do sistema interagem por meio de interfaces HTTP, chamadas internas entre camadas e integrações com serviços externos.

| Origem | Destino | Interface / mecanismo | Finalidade |
|---|---|---|---|
| Cliente web | API REST | HTTP/HTTPS | Emissão e consulta de senhas. |
| Interface do atendente | API REST | HTTP/HTTPS | Chamada de senhas e gerenciamento de atendimentos. |
| Totem | API REST | HTTP/HTTPS | Emissão presencial de senhas. |
| API REST | Casos de uso | Chamadas internas | Executar operações da aplicação. |
| Casos de uso | Adaptador de persistência | Interfaces/portas internas | Consultar e armazenar informações. |
| Processador da Outbox | Adaptador de notificação | Interface `Notificador` | Solicitar envio de notificações. |
| Adaptador de persistência | PostgreSQL | SQL via SQLAlchemy | Executar consultas e transações. |
| Adaptador de notificação | Provedor externo | SDK/API do provedor | Enviar notificações aos usuários. |

--- 

## 7. Persistência de dados

O sistema utiliza **PostgreSQL** como mecanismo de persistência. O acesso ao banco é realizado pelo adaptador de persistência, implementado com **SQLAlchemy**, enquanto o **Alembic** é responsável pelo versionamento e aplicação das migrações do banco de dados.

São armazenadas informações relacionadas às filas, senhas, atendimentos, histórico de alterações de estado e eventos pendentes de processamento da Outbox.

As operações que exigem consistência são realizadas por meio de transações, utilizando os mecanismos de integridade referencial e bloqueio de concorrência do PostgreSQL. Dessa forma, busca-se garantir a consistência dos dados em operações concorrentes, especialmente na emissão e chamada de senhas.

---

## 8. Decisões de comunicação

As principais decisões relacionadas à comunicação entre os componentes foram definidas considerando o desacoplamento, a interoperabilidade e a consistência das operações.

| Decisão | Justificativa |
|---|---|
| Utilizar API REST sobre HTTP/HTTPS | Padronizar a comunicação entre clientes e backend, permitindo integração com diferentes interfaces. |
| Utilizar chamadas internas entre camadas | Evitar comunicação de rede desnecessária dentro da aplicação. |
| Utilizar interfaces/portas para persistência e notificações | Desacoplar as regras de negócio das tecnologias externas, permitindo substituir implementações sem modificar os casos de uso. |
| Utilizar o padrão Outbox para notificações | Registrar eventos na mesma transação das alterações de negócio, permitindo seu processamento posterior e novas tentativas em caso de falha no envio. |
| Utilizar PostgreSQL com transações | Garantir consistência nas operações envolvendo senhas, filas e atendimentos, inclusive em cenários de concorrência. |

| Administrador | API REST / funcionalidades administrativas | Administrar filas, guichês, atendentes ou configurações, se implementado. |
| Operador do sistema | Ferramentas operacionais / monitoramento | Acompanhar tentativas, falhas e eventos pendentes, se disponibilizado. |
| Provedor de notificações | Adaptador de notificação | Receber solicitações de envio e retornar resultado da tentativa. |
