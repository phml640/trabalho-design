# Levantamento de componentes, atores e dependências — Sistema de Gestão de Filas

## 1. Contexto e escopo

Este documento identifica os componentes, atores e dependências do sistema de gestão de filas e atendimento presencial, incluindo suas responsabilidades, relações arquiteturais e mecanismos de comunicação.

O levantamento contempla os componentes internos, os clientes externos, os serviços dos quais o sistema depende e a integração com a API externa de consulta de horários.

---

## 2. Componentes do sistema

### 2.1. Componentes arquiteturais internos

| Componente | Responsabilidade | Interface de comunicação |
|---|---|---|
| API REST | Receber requisições HTTP, validar entradas, autenticar e autorizar quando implementado, traduzir erros e retornar respostas. | Endpoints HTTP/REST e chamadas aos casos de uso. |
| Gerenciador de filas | Coordenar operações e consultas relacionadas às filas. | Interfaces internas da aplicação. |
| Gerenciador de senhas | Emitir, consultar, chamar e controlar o estado das senhas. | Interfaces internas da aplicação e interfaces de persistência. |
| Gerenciador de atendimentos | Controlar início e finalização de atendimentos e associação com atendente e guichê. | Interfaces internas da aplicação e interfaces de persistência. |
| Gerenciador de histórico | Registrar transições de estado de senhas e atendimentos. | Interface de registro de histórico e interfaces de persistência. |
| Gerenciador de virada diária | Garantir a mudança do dia operacional, tratar senhas antigas e reiniciar o contador pertinente. | Interface de execução da virada diária e interfaces de persistência. |
| Processador da Outbox | Ler eventos pendentes, solicitar notificações, controlar tentativas e registrar sucesso ou falha. | Interface de acesso à Outbox e interface `Notificador`. |
| Adaptador de persistência | Implementar as portas de persistência utilizando SQLAlchemy e PostgreSQL. | Interfaces de repositórios e comunicação SQL com PostgreSQL. |
| Adaptador de notificação | Implementar a porta `Notificador`, inicialmente com um notificador simulado. | Interface `Notificador` e integração com o provedor externo. |
| Adaptador de consulta de horários | Implementar a porta de consulta de horários, realizando requisições à API externa e convertendo suas respostas para o formato utilizado pela aplicação. | Interface de consulta de horários e HTTP/HTTPS. |

Os componentes representam unidades modulares que encapsulam responsabilidades e colaboram por meio de interfaces. As interfaces internas podem corresponder a contratos de programação entre módulos, não exigindo necessariamente comunicação por rede.

Regras de negócio e eventos de domínio, como `SenhaChamada`, são elementos internos da aplicação e não são considerados componentes independentes neste levantamento.

### 2.2. Componentes externos e clientes

| Componente | Responsabilidade | Situação nos ADRs |
|---|---|---|
| Interface do usuário / cliente | Consumir a API para emitir e consultar senhas e acompanhar informações da fila. | Cliente previsto; tecnologia não definida. |
| Interface do atendente | Consumir a API para chamar senhas e gerenciar atendimentos. | Cliente previsto; tecnologia não definida. |
| Totem de autoatendimento | Consumir a API para emissão presencial de senhas. | Cliente previsto; tecnologia não definida. |
| Provedor de notificações | Encaminhar mensagens ao celular do usuário quando sua senha for chamada. | Dependência externa substituível; provedor concreto não escolhido. |
| PostgreSQL | Persistir os dados do sistema com transações, integridade referencial e mecanismos de controle de concorrência. | Tecnologia definida. |
| API externa de horários | Disponibilizar informações de horários para consulta pelo sistema. | Dependência externa; fornecedor e contrato de integração a definir. |

---

## 3. Atores do sistema

| Ator | Responsabilidades / interações | Situação |
|---|---|---|
| Usuário (cliente) | Solicitar emissão de senha, consultar senha ou fila e receber notificação quando sua senha for chamada. | Decorre dos requisitos descritos no documento de requisitos. |
| Atendente | Solicitar chamada da próxima senha, iniciar atendimento e finalizar atendimento. | Decorre dos fluxos descritos no documento de requisitos. |
| Administrador | Administrar filas, guichês, atendentes e configurações, conforme as funcionalidades administrativas definidas. | Ator previsto nos requisitos. |
| Operador do sistema | Acompanhar falhas, tentativas e eventos pendentes da Outbox para suporte operacional. | Ator possível; interface e permissões não especificadas. |

O totem de autoatendimento e as interfaces web ou de atendente são considerados canais ou clientes externos de acesso ao sistema, não atores humanos.

---

## 4. Dependências do sistema

### 4.1. Dependências arquiteturais e direção do código

| Origem | Destino / contrato utilizado | Explicação |
|---|---|---|
| `api` | `application` | A API chama os casos de uso e traduz requisições e respostas HTTP. |
| `application` | `domain` | Os casos de uso utilizam entidades, regras e eventos do domínio. |
| `application` | Portas de persistência | Os casos de uso utilizam contratos para consultar e armazenar informações. |
| `application` | Porta de notificação | Os componentes responsáveis pelo processamento de notificações utilizam um contrato para solicitar seu envio. |
| `application` | Porta de consulta de horários | Os casos de uso solicitam informações de horários por meio de um contrato definido pela aplicação. |
| `infrastructure` | Portas definidas em `application` | Os adaptadores implementam contratos de persistência, notificação e consulta de horários definidos pela aplicação. |
| `infrastructure` | `domain` | Os adaptadores podem mapear entidades e tratar eventos de domínio, sem transferir detalhes técnicos para o domínio. |
| Processador da Outbox | Porta de acesso à Outbox | O processador consulta eventos pendentes e atualiza seus estados de processamento. |
| Processador da Outbox | Porta `Notificador` | O processador solicita o envio de notificações por meio de uma interface substituível. |
| Adaptador de persistência | PostgreSQL | O adaptador executa consultas e transações no banco. |
| Adaptador de notificação | Provedor externo | O adaptador integra com o canal de mensagens escolhido. |
| Adaptador de consulta de horários | API externa de horários | O adaptador realiza requisições HTTP para obter informações disponibilizadas pelo serviço externo. |

A integração com a API de horários e o mecanismo de persistência seguem o princípio de inversão de dependência: a aplicação define as interfaces, enquanto a infraestrutura fornece suas implementações concretas.

O mesmo princípio é aplicado às notificações, permitindo substituir o provedor de mensagens sem modificar a lógica de processamento da Outbox.

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
| Cliente HTTP (ex.: HTTPX) | Adaptador de consulta de horários | Realizar requisições HTTP à API externa, incluindo timeout e tratamento de erros. |

---

## 5. Relacionamento entre atores e componentes

| Ator | Componente / interface acessada | Operações |
|---|---|---|
| Usuário | API REST | Solicitar emissão e consulta de senha. |
| Usuário | Canal externo de notificação | Receber aviso quando sua senha for chamada. |
| Atendente | API REST | Consultar filas, solicitar chamada de senhas e gerenciar atendimentos. |
| Administrador | API REST / funcionalidades administrativas | Administrar filas, guichês, atendentes e configurações. |
| Operador do sistema | Ferramentas operacionais / monitoramento | Acompanhar tentativas, falhas e eventos pendentes, se disponibilizado. |

O usuário e o atendente interagem com as funcionalidades do sistema por meio da API REST. As operações são encaminhadas aos respectivos casos de uso, que colaboram com os demais componentes por meio de suas interfaces.

O recebimento de notificações pelo usuário ocorre por meio do canal externo disponibilizado pelo provedor de notificações.

O totem de autoatendimento e as interfaces web e do atendente atuam como clientes da API REST.

---

## 6. Interfaces e mecanismos de comunicação

Os componentes do sistema interagem por meio de interfaces HTTP, chamadas internas entre módulos e integrações com serviços externos.

| Origem | Destino | Interface / mecanismo | Finalidade |
|---|---|---|---|
| Cliente web | API REST | HTTP/HTTPS | Emissão e consulta de senhas. |
| Interface do atendente | API REST | HTTP/HTTPS | Chamada de senhas e gerenciamento de atendimentos. |
| Totem | API REST | HTTP/HTTPS | Emissão presencial de senhas. |
| API REST | Casos de uso | Chamadas internas | Executar operações da aplicação. |
| Casos de uso | Interfaces de persistência | Portas internas | Consultar e armazenar informações. |
| Casos de uso | Interface de consulta de horários | Porta interna | Solicitar informações de horários. |
| Processador da Outbox | Interface de acesso à Outbox | Porta interna | Consultar eventos pendentes e atualizar seu processamento. |
| Processador da Outbox | Interface `Notificador` | Porta interna | Solicitar envio de notificações. |
| Adaptador de persistência | PostgreSQL | SQL via SQLAlchemy | Executar consultas e transações. |
| Adaptador de notificação | Provedor externo | SDK/API do provedor | Enviar notificações aos usuários. |
| Adaptador de consulta de horários | API externa de horários | HTTP/HTTPS | Consultar informações de horários disponibilizadas pelo serviço externo. |

As interfaces internas são representadas por contratos de programação, como interfaces de repositórios e portas de serviços. Elas permitem que os componentes colaborem sem depender diretamente dos detalhes de implementação uns dos outros.

---

## 7. Persistência de dados

O sistema utiliza **PostgreSQL** como mecanismo de persistência. O acesso ao banco é realizado pelo adaptador de persistência, implementado com **SQLAlchemy**, enquanto o **Alembic** é responsável pelo versionamento e aplicação das migrações do banco de dados.

São armazenadas informações relacionadas às filas, senhas, atendimentos, histórico de alterações de estado e eventos pendentes de processamento da Outbox.

As operações que exigem consistência são realizadas por meio de transações, utilizando os mecanismos de integridade referencial e controle de concorrência do PostgreSQL. Dessa forma, busca-se garantir a consistência dos dados em operações concorrentes, especialmente na emissão e chamada de senhas.

A API externa de horários é consultada por meio do adaptador de integração. Não foi estabelecida, neste levantamento, a necessidade de persistir localmente as informações retornadas pelo serviço externo. Essa possibilidade depende dos requisitos de atualização, disponibilidade e utilização dos horários.

---

## 8. Decisões de comunicação

As principais decisões relacionadas à comunicação entre os componentes foram definidas considerando o desacoplamento, a interoperabilidade e a consistência das operações.

| Decisão | Justificativa |
|---|---|
| Utilizar API REST sobre HTTP/HTTPS | Padronizar a comunicação entre clientes e backend, permitindo integração com diferentes interfaces. |
| Utilizar chamadas internas entre módulos | Evitar comunicação de rede desnecessária dentro da aplicação. |
| Utilizar interfaces/portas para persistência, notificações e consulta de horários | Desacoplar as regras de negócio das tecnologias externas, permitindo substituir implementações sem modificar os casos de uso. |
| Utilizar o padrão Outbox para notificações | Registrar eventos na mesma transação das alterações de negócio, permitindo seu processamento posterior e novas tentativas em caso de falha no envio. |
| Utilizar PostgreSQL com transações | Garantir consistência nas operações envolvendo senhas, filas e atendimentos, inclusive em cenários de concorrência. |
| Utilizar HTTP/HTTPS para integração com a API externa de horários | Padronizar a comunicação com o serviço externo e permitir sua substituição sem alterações nas regras de negócio. |
| Definir timeout e tratamento de falhas na consulta de horários | Evitar que indisponibilidades ou respostas lentas do serviço externo comprometam indefinidamente as operações do sistema. |
| Utilizar uma interface substituível para notificações | Permitir a troca do provedor de mensagens ou utilização de um notificador simulado sem modificar o Processador da Outbox. |

---

## 9. Processamento de notificações

O sistema utiliza o padrão **Outbox** para desacoplar as operações de negócio do envio de notificações aos usuários.

Quando uma senha é chamada, o evento correspondente é registrado na Outbox na mesma transação das alterações de estado relacionadas à operação. Dessa forma, evita-se que a alteração seja confirmada sem que o evento destinado ao processamento posterior também seja registrado.

O Processador da Outbox consulta os eventos pendentes, identifica aqueles que exigem notificação e solicita o envio por meio da interface `Notificador`. O adaptador de notificação implementa essa interface e realiza a integração com o provedor externo escolhido.

O processamento contempla o controle de tentativas e o registro de sucesso ou falha, permitindo que eventos não processados sejam submetidos a novas tentativas conforme a política definida.

A utilização de uma interface para o notificador permite substituir o provedor externo ou utilizar uma implementação simulada durante o desenvolvimento e os testes, sem modificar a lógica de processamento da Outbox.

O fluxo geral de notificação é:

1. Uma operação de negócio provoca a chamada de uma senha.
2. A alteração de estado e o evento correspondente são registrados na mesma transação.
3. O Processador da Outbox identifica o evento pendente.
4. O processador solicita o envio por meio da interface `Notificador`.
5. O adaptador de notificação encaminha a mensagem ao provedor externo.
6. O resultado do processamento é registrado, permitindo novas tentativas em caso de falha.

---
