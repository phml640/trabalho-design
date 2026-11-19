# Componentes e arquitetura implementada

Este documento descreve o protótipo executável. Os ADRs registram decisões e
intenções; a situação abaixo distingue o que existe no código do que foi apenas
planejado. Diagramas UML são mantidos separadamente pelo integrante responsável.

## Componentes implementados

| Componente | Implementação e responsabilidade |
| --- |
| Frontend React/Vite/TypeScript | `frontend/src`: visões `/usuario` e `/admin`, acompanhamento periódico, histórico e notificações. Não calcula a ordem de chamada. |
| Servidor web Nginx | `frontend/nginx.conf`: serve o build, suporta acesso direto às rotas React e encaminha `/api/` para a API. |
| API REST FastAPI | `gestao_filas.api`, `gestao_senhas.api` e `gestao_compartilhada.api`: validação, respostas tipadas, OpenAPI e tradução de erros para HTTP. Sem autenticação/autorização. |
| Gestão de filas | `GestaoDeFilas`: criação, consulta, encerramento e reabertura. Coordena cancelamentos pela unidade de trabalho. |
| Gestão de senhas e atendimentos | `GerenciadorDeSenhas`: emissão, consulta, chamada, início e finalização. Atendimento é parte da senha; não existe um serviço implantado separadamente para ele. |
| Domínio | `Fila`, `Senha`, `selecionar_proxima` e `SenhaChamada`: estados, transições e política de duas prioritárias consecutivas/FIFO. Não dependem de HTTP, ORM ou provedor. |
| Virada diária | `gestao_compartilhada.operacoes.garantir_dia`: execução idempotente na operação pertinente. Não existe cron ou agendador. |
| Histórico e consultas | `TransicaoSenha`, `Consultas` e repositórios: registro atômico de transições e consultas paginadas por fila/senha/estado. |
| Processador da Outbox | `ProcessadorOutbox`: reserva um evento em transação curta, fecha a reserva antes de invocar o notificador e registra sucesso/falha em outra transação. Execução manual pela API/interface. |
| Persistência PostgreSQL | `gestao_compartilhada.postgres`: modelos e repositórios SQLAlchemy, Session por transação, bloqueio da fila e migrações Alembic. |
| Adaptador em memória | `UnidadeDeTrabalhoEmMemoria`: snapshots, rollback e bloqueio global em um processo; utilizado nas regressões rápidas. Não oferece persistência entre reinícios. |
| Notificador simulado | `FakeNotificador`: persiste uma mensagem única por evento, sem celular, SMS, WhatsApp ou contato real. Permite simular falha e inspecionar tentativas. |

PostgreSQL, API e frontend têm containers próprios por necessidade de execução.
As responsabilidades de negócio estão em **um único backend**, com chamadas
internas e transação local compartilhada. A separação dos containers de banco e
servidor web não torna a solução um conjunto de microsserviços.

Essa é a organização configurada no código e nos Dockerfiles. Cada integrante
deve verificar sua execução no ambiente local, conforme o [README](../README.md).

## Interfaces (portas e contratos)

| Interface | Responsabilidade | Utilizada por | Implementada por |
| --- | --- | --- |
| `UnidadeDeTrabalho` | Delimita as operações de persistência necessárias aos casos de uso e coordena a transação local. | Gestão de filas, gestão de senhas e operações compartilhadas. | Adaptadores PostgreSQL e `UnidadeDeTrabalhoEmMemoria`. |
| Protocolos de repositórios | Definem contratos de acesso aos dados utilizados pelos casos de uso. | Casos de uso e componentes de coordenação. | Repositórios PostgreSQL e implementação em memória. |
| `Notificador.notificar(evento)` | Contrato substituível para solicitar a notificação de um evento, usando id estável como chave de idempotência. | `ProcessadorOutbox`. | `FakeNotificador`. |

## Conceitos e representações do domínio

| Conceito | Representação e responsabilidade |
| --- | --- |
| Fila | `Fila`: estado aberta/encerrada, dia operacional e contador prioritário; suas operações validam disponibilidade e alteram esse estado. |
| Senha | `Senha`: número por fila/dia/tipo, identificação simbólica do usuário, canal e ciclo de estados; valida transições e ordem dos horários. |
| Atendimento | Parte de `Senha`, com atendente, guichê, início e fim. Não há entidade, tabela ou identificador de atendimento separado. |
| Histórico | `TransicaoSenha`: registro imutável com estados anterior/novo, instante e dados operacionais. A identificação do usuário permanece na senha associada, sem cópia no registro da transição. |
| Evento de chamada | `SenhaChamada`: fato imutável, com ids de evento, fila e senha e horário. O acompanhamento de entrega está em `MensagemOutbox` e `TentativaNotificacao`. |
| Usuário, atendente e guichê | Referências textuais na senha; não são entidades cadastradas e não possuem chaves estrangeiras para tabelas próprias. |

## Relações e comunicação entre componentes

- O frontend comunica-se com a API REST por HTTP; não acessa diretamente o banco.
- O Nginx serve o frontend e encaminha `/api/` para a API.
- A API REST traduz as requisições HTTP e coordena os casos de uso.
- `GestaoDeFilas`, `GerenciadorDeSenhas`, `Consultas` e `ProcessadorOutbox` coordenam operações, utilizando o domínio e os contratos necessários.
- Os casos de uso utilizam os protocolos de repositórios e a `UnidadeDeTrabalho`, sem SQL diretamente nas regras de negócio.
- Os adaptadores de persistência implementam os contratos de repositórios e transação; a composição seleciona a implementação.
- `ProcessadorOutbox` utiliza a interface `Notificador`; o `FakeNotificador` implementa o envio simulado.
- A seleção e o atendimento de senhas, o histórico, os estados e os eventos necessários confirmam ou revertem juntos na transação local quando aplicável.

## Atores e funcionalidades fora do escopo

| Elemento | Situação real |
| --- |
| Usuário | Emite e acompanha uma senha pela visão de usuário, sem cadastro ou login. |
| Atendente/administrador | Cria, encerra/reabre filas, chama e atende senhas e consulta registros na mesma visão administrativa. |
| Guichês e atendentes | Identificadores informados na chamada; não possuem cadastro ou gestão de usuários. |
| Operador | Pode inspecionar eventos, mensagens e tentativas no painel; não existe papel/permissão separado. |
| Totem físico | Planejado, não implementado. A API aceita o canal `totem`, mas não há aplicação ou equipamento específico para esse canal. |
| Provedor real de notificações | Planejado, não implementado. Há apenas a porta e sua implementação simulada. |
| API externa de horários | **Fora do escopo do protótipo. Não existem porta, adaptador, endpoint ou requisição a essa API.** Referências anteriores eram uma intenção, não uma dependência implementada. |
| Autenticação, autorização e elegibilidade prioritária | Planejadas como exigências do sistema pretendido, não implementadas no protótipo. A escolha de visão não é uma fronteira de segurança; a prioridade é demonstrativa. |

As simplificações implementadas — identificação simbólica, classificação
demonstrativa e envio simulado/manual — estão relacionadas a RF01, RF02, RF03 e
RF07 na [situação dos requisitos](requisites.md#situação-no-protótipo).

## Coesão, acoplamento e características hexagonais

`gestao_filas` concentra o estado e a coordenação das filas. `gestao_senhas`
concentra a política e o ciclo da senha/atendimento. `gestao_compartilhada`
coordena transações, virada, histórico e notificações. Filas e senhas têm
acoplamento deliberado através do contrato transacional: seleção, contador,
estado, histórico e evento precisam confirmar ou reverter juntos.

O backend é um **monólito modular com características de Arquitetura Hexagonal**:
API e infraestrutura ficam na borda; casos de uso coordenam o domínio por portas;
a composição escolhe os adaptadores em `criar_app()` e `configuracao.py`.
Modelos ORM não atravessam as portas: o adaptador faz o mapeamento para objetos de
domínio. FastAPI/Pydantic permanecem na entrada HTTP. O frontend é outro cliente
dessa entrada e não acessa diretamente o banco.

Essa direção de dependências reduz o acoplamento às tecnologias. As pastas não
impõem isolamento: os limites dependem dos contratos e da revisão do código. O
módulo compartilhado é um ponto de coordenação, portanto exige cuidado para não
virar um depósito de responsabilidades sem relação.

## Responsabilidades e princípios GRASP/SOLID

| Princípio | Aplicação concreta |
| --- |
| GRASP Controller | `GestaoDeFilas`, `GerenciadorDeSenhas`, `Consultas` e `ProcessadorOutbox` coordenam casos de uso; rotas traduzem HTTP. |
| GRASP Information Expert | `Senha` valida suas transições e horários; `Fila` controla seu estado e contador. A função pura `selecionar_proxima` aplica a política. |
| GRASP Creator | O gerenciador cria a senha a partir do número fornecido pelo repositório e das informações da fila. |
| GRASP High Cohesion / Low Coupling | Responsabilidades são agrupadas pelos módulos; as integrações usam portas, sem SQL nos casos de uso. |
| GRASP Indirection / Protected Variations | Unidade de trabalho, repositórios e `Notificador` isolam variações de persistência e envio. |
| SOLID SRP | Entidades tratam regras, casos de uso tratam coordenação, repositórios tratam acesso ao banco e a API trata o contrato HTTP. |
| SOLID DIP | Casos de uso dependem de protocolos, e os adaptadores implementam esses contratos. |
| SOLID OCP | Outro notificador pode ser injetado sem alterar seleção de senhas ou processamento da chamada. |
| SOLID ISP | Portas de filas, senhas, histórico, Outbox e notificações são separadas por responsabilidade; a transação as reúne no contexto de consistência. |
| SOLID LSP, no escopo dos contratos | Memória e PostgreSQL são exercitados com regressões comuns. Isso verifica comportamento nas operações válidas, sem afirmar equivalência de desempenho ou persistência dos dois adaptadores. |

## Transações, histórico e notificação

A transação de emissão/chamada bloqueia a linha da fila com `SELECT FOR UPDATE`.
O isolamento `READ COMMITTED` permite que a operação seguinte veja o commit da
anterior. A numeração por fila/dia/classe também é transacional, sem consumir
números em rollback. Operações globais usam advisory lock para proteger a criação
de nomes comparados com `casefold()`.

A virada diária participa da transação do caso de uso: se a operação abortar,
também são revertidos os cancelamentos e o avanço do dia feitos nessa transação.

`senhas` armazena também atendente, guichê e horários do atendimento, preservando
o modelo existente. `historico_transicoes` conserva as transições; virada e
encerramento não apagam registros. `outbox`, `tentativas_notificacao` e
`notificacoes_simuladas` preservam a intenção, as tentativas e o efeito simulado.

A chamada confirma antes do envio. O processador fecha a transação da reserva
antes de invocar o notificador; o Fake abre sua própria transação para registrar
a mensagem simulada. Falha do notificador não altera o atendimento.
Reservas de processamento expiram em 30 segundos e podem ser retomadas. O id do
evento é estável; o Fake evita mensagens duplicadas por esse id. Um provedor real
precisaria respeitar essa chave para evitar duplicações após perda de confirmação.
O projeto não promete entrega exatamente uma vez e não usa event sourcing.

## Trade-offs e evolução

A comparação com monólito simples e microsserviços está preservada no
[ADR-002](adr/ADR-002-monolito-modular-hexagonal-eventos.md#alternativas-consideradas),
relacionada à consistência do ASR01 e à modificabilidade do ASR03. Os custos de
desempenho do ASR02 aparecem na [medição registrada](resultados/asr02-basico.json).

- Uma transação local e um backend simplificam a demonstração, o diagnóstico e a
  consistência. A contrapartida é compartilhar implantação e recursos entre módulos.
- O bloqueio por fila é simples e evita seleção duplicada, mas serializa operações
  concorrentes dessa fila. Filas diferentes têm bloqueios independentes.
- A seleção continua no domínio e o adaptador carrega as senhas da fila. Isso
  preserva o contrato existente, mas tem custo crescente de consulta e materialização.
  Histórico e notificações são paginados; a fila ativa ainda retorna um array.
- A Outbox evita perder a intenção de notificar entre commit e envio. Acrescenta
  registros, reservas e retentativas; o processamento manual é suficiente para o
  protótipo, mas não substitui uma política operacional de entrega.
- Vários arquivos de adaptação e mapeamento aumentam o código em relação a endpoints
  com SQL direto; em troca, o domínio permanece testável sem HTTP e banco.

**Troca do banco:** implementar os protocolos de repositório e `UnidadeDeTrabalho`,
mapear entidades, criar migrações e substituir a composição. É preciso revalidar
atomicidade, unicidade, numeração e sincronização entre processos. Bloqueios de
linha, advisory locks e upserts são detalhes PostgreSQL que não podem simplesmente
ser copiados para qualquer banco. Regras de prioridade e casos de uso devem permanecer.

**Troca do notificador:** implementar `Notificador`, injetar o novo adaptador e
manter o evento/id de idempotência. A chamada e a política permanecem. Um serviço
real exigiria definir contato, consentimento, timeout e política de retentativas;
esses requisitos não estão resolvidos pelo Fake.

A API externa de horários não participa de nenhum fluxo atual. Só deve ser
reintroduzida se um requisito concreto justificar a nova integração.
