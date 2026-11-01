# ADR-002 — Monólito modular, Arquitetura Hexagonal e eventos internos

- **Data:** 2026-11-01
- **Status:** Aceito
- **Relacionados:** [ADR-001](ADR-001-escolha-da-stack-do-backend.md), [requisitos](../requisites.md), [ADR-003](ADR-003-postgresql-persistencia.md), [ADR-004](ADR-004-notificacoes.md)

## Contexto

O sistema precisa emitir, consultar e chamar senhas, manter atendimentos e histórico e notificar usuários. A equipe deve demonstrar uma fatia vertical executável com persistência e uma integração substituível. ASR01 exige consistência nas chamadas concorrentes; ASR02 pede transações curtas; ASR03 pede que regras de negócio sobrevivam à troca de banco ou notificador.

## Problema e forças envolvidas

É preciso separar as responsabilidades sem criar várias unidades de implantação para um domínio pequeno e fortemente relacionado. A chamada de senha deve produzir uma mudança de estado atômica e desencadear uma notificação que pode falhar ou demorar. A estrutura precisa mostrar claramente onde ficam as regras, os contratos e os detalhes técnicos.

## Alternativas consideradas

### 1. Monólito simples orientado a endpoints

Tem implantação e implementação iniciais simples. Porém, quando seleção, SQL e notificação ficam nos endpoints, mudanças de tecnologia e testes das regras passam a afetar o fluxo HTTP. A separação exigida pelo ASR03 fica frágil.

### 2. Microsserviços para filas, atendimentos e notificações

Permitem implantação e escala independentes. Em contrapartida, a chamada e o histórico exigiriam comunicação e consistência distribuídas, além de observabilidade e operação de vários serviços. Para o escopo acadêmico e a carga ainda não medida, o custo não se justifica.

### 3. Monólito modular com Arquitetura Hexagonal e eventos internos

Mantém uma implantação e uma transação local, com dependências dirigidas ao domínio. Eventos internos representam fatos já ocorridos e desacoplam efeitos secundários. Exige disciplina para preservar limites de módulos e contratos, mesmo sem isolamento de processos.

## Decisão

Adotar a terceira alternativa. O backend será um **monólito modular** com **Arquitetura Hexagonal** e comunicação **baseada em eventos internos** para efeitos posteriores à mudança de estado. A API REST será a entrada síncrona, com módulos internos organizados por responsabilidade:

| Módulo | Responsabilidade |
| --- | --- |
| `api` | Adaptador de entrada HTTP: autenticação/autorização, validação de entrada e tradução de erros para respostas. |
| `application` | Casos de uso, coordenação de transações e portas de saída para persistência e notificação. |
| `domain` | Entidades, estados, política de prioridade, invariantes e eventos de domínio; sem dependência de FastAPI, ORM ou provedor externo. |
| `infrastructure` | Adaptadores de persistência, processamento da saída de eventos e provedores de notificação. |

As dependências de código apontam para dentro: `api` e `infrastructure` usam contratos de `application`; `application` usa `domain`. A composição dos adaptadores ocorre na borda da aplicação. As portas descrevem operações necessárias aos casos de uso, não modelos de um banco específico.

O fluxo principal de chamada é **síncrono e transacional**: selecionar conforme a política, reservar/chamar a senha, atualizar o contador, registrar o histórico e gravar um evento `SenhaChamada` para entrega posterior. A publicação externa da notificação ocorre **após o commit**, por processamento da tabela de saída (*outbox*). Outros eventos de domínio podem ser adicionados para emissão, início, finalização e cancelamento, conforme a necessidade de consumidores reais. Eventos não substituem o estado corrente nem constituem *event sourcing*.

O evento `SenhaChamada` deve carregar o identificador estável da senha, o identificador da fila, o horário da chamada e o identificador do evento. Dados de contato sensíveis devem ser buscados pelo adaptador autorizado ou armazenados pelo tempo mínimo necessário, evitando sua cópia em eventos e logs.

## Consequências positivas

- Uma transação local atende à consistência da chamada e do histórico exigida pelo ASR01.
- Política de prioridade e estados podem ser testados sem HTTP e banco.
- Trocar banco ou notificador afeta principalmente os adaptadores, conforme ASR03.
- A chamada responde sem aguardar o provedor externo, favorecendo o ASR02.
- A implantação continua simples para a equipe e para a apresentação do protótipo.

## Consequências negativas, custos e riscos

- Há mais contratos e código de composição do que em um monólito orientado apenas a endpoints.
- Uma transação por fila serializa chamadas da mesma fila; a capacidade real precisa ser medida.
- O processamento da outbox exige rotina de leitura, tentativas de reenvio, observabilidade e idempotência do consumidor.
- Limites modulares dependem de revisão e testes; as pastas sozinhas não impedem acoplamento.
- A palavra “eventos” pode sugerir entrega instantânea, que a decisão não garante. O contrato de notificação é assíncrono.

## Critérios para revisar a decisão

Reavaliar se medições mostrarem que uma implantação única não atende à carga, se notificações exigirem escala ou disponibilidade independentes, ou se os limites entre módulos se tornarem estáveis o suficiente para justificar extração. Uma eventual separação deve preservar contratos e tratar explicitamente a perda da transação local.
