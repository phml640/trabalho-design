# Trabalho Final — Design e Arquitetura de Software

**2026-2**

## Objetivo

Cada grupo receberá um problema de software diferente. O objetivo do trabalho é projetar uma solução de software, justificando as decisões de design e arquitetura adotadas, e implementar uma pequena parte funcional que demonstre que a solução proposta pode ser concretizada.

O trabalho deverá responder, ao final, à seguinte questão:

> Como este sistema deve ser organizado para atender aos requisitos atuais e permitir sua evolução sem gerar dependências desnecessárias?

Não existe uma arquitetura obrigatória, qualquer uma que vimos na disciplina pode ser utilizada. A escolha deverá ser consequência dos requisitos, restrições, ASRs e trade-offs analisados pelo grupo.

## Entrega

Cada grupo deverá entregar o link de um repositório Git contendo:

- documentação do projeto;
- diagramas;
- registros de decisões arquiteturais;
- código-fonte;
- testes;
- protótipo executável.

O objetivo não é implementar o sistema completo. O foco é demonstrar coerência entre requisitos, decisões de design, arquitetura, modelos e código.

## 1. Descrição do problema e requisitos

O grupo deverá:

1. apresentar brevemente o contexto do sistema;
2. identificar os principais atores;
3. definir entre 6 e 10 requisitos funcionais;
4. identificar restrições relevantes;
5. selecionar e descrever 3 requisitos arquiteturalmente significativos (ASRs);
6. justificar por que esses ASRs influenciam decisões arquiteturais.

Os ASRs devem ser descritos de forma suficientemente concreta para orientar decisões. Sempre evite formulações vagas.

## 2. Modelo de domínio e responsabilidades

O grupo deverá identificar os principais conceitos do domínio e distribuir responsabilidades entre classes ou módulos.

A documentação deverá apresentar:

- principais classes/conceitos do domínio;
- responsabilidades de cada classe;
- justificativas relacionadas a GRASP, quando necessário;
- análise de coesão e acoplamento;
- aplicação de princípios SOLID quando pertinente.

As decisões devem refletir responsabilidades reais do sistema.

## 3. Modelagem UML

O projeto deverá conter, no mínimo:

1. Diagrama de Classes;
2. Diagrama de Sequência;
3. Diagrama de Comunicação;
4. Diagrama de Componentes ou Pacotes.

Os modelos devem ser consistentes entre si. Por exemplo:

- uma operação utilizada no Diagrama de Sequência deve fazer sentido em relação às responsabilidades mostradas no Diagrama de Classes;
- os componentes/módulos devem ser compatíveis com a organização proposta;
- dependências representadas nos diagramas devem ser coerentes com o código.

## 4. Proposta arquitetural

O grupo deverá apresentar uma visão geral da arquitetura contendo:

- principais componentes ou módulos;
- responsabilidade de cada componente;
- dependências entre eles;
- interfaces relevantes;
- mecanismos de comunicação;
- persistência;
- integrações externas;
- decisões de comunicação;
- documentação de API, quando necessário.

A organização arquitetural deverá ser explicitada. Exemplo:

```text
Cliente-servidor
      +
Monolito modular
      +
Organizacao em camadas
      +
MVC na apresentacao
```

Não basta citar o nome de uma arquitetura. É necessário mostrar como ela aparece na solução proposta.

## 5. Alternativas e trade-offs

O grupo deverá analisar pelo menos duas alternativas arquiteturais além da solução escolhida.

Exemplo:

```text
Alternativa A: monolito simples
Alternativa B: monolito modular
Alternativa C: microsservicos
```

A comparação deverá considerar, quando pertinente:

- modificabilidade;
- desempenho;
- disponibilidade;
- testabilidade;
- complexidade;
- implantação;
- escalabilidade;
- custo de desenvolvimento e operação.

A decisão final deverá ser relacionada aos ASRs identificados anteriormente.

## 6. Architecture Decision Records — ADRs

O projeto deverá conter pelo menos **3 ADRs**.

Cada ADR deverá registrar:

1. contexto;
2. problema ou forças envolvidas;
3. alternativas consideradas;
4. decisão;
5. consequências positivas;
6. consequências negativas, custos ou riscos.

Exemplos de decisões adequadas para ADR:

- monólito modular ou microsserviços;
- banco compartilhado ou separado;
- comunicação síncrona ou assíncrona;
- uso ou não de Arquitetura Hexagonal, Onion ou Clean Architecture;
- estratégia para integração com serviços externos;
- estratégia para persistência;
- isolamento de notificações ou pagamentos.

## 7. Protótipo funcional

Não é necessário implementar o sistema inteiro.

O grupo deverá implementar uma fatia vertical da solução contendo, no mínimo:

1. um caso de uso que modifica o estado do sistema;
2. uma consulta;
3. um fluxo alternativo ou erro relevante;
4. persistência dos dados;
5. pelo menos uma dependência externa simulada ou real.

Exemplo para um sistema de empréstimo de equipamentos:

```text
solicitar emprestimo
        |
        v
verificar disponibilidade
        |
        v
criar emprestimo
        |
        v
persistir
        |
        v
enviar confirmacao
```

Além disso, poderia existir:

```text
consultar emprestimos
```

Com um fluxo alternativo como:

```text
equipamento indisponivel
```

O código implementado deverá ser coerente com os diagramas e com a arquitetura apresentada.

## 8. Dependência externa

Todo projeto deverá conter pelo menos uma integração que possa ser substituída, mesmo que implementada inicialmente de forma simples.

Exemplos:

```text
Notificador
    |-- EmailNotificador
    `-- NotificadorFake
```

Ou:

```text
PagamentoGateway
```

Ou:

```text
ServicoAutenticacao
```

O objetivo é permitir a discussão sobre interfaces, dependências, testabilidade e modificabilidade.

## 9. Análise de evolução

Ao final da documentação, o grupo deverá responder:

> Se uma das principais tecnologias ou integrações utilizadas precisasse ser substituída, quais partes do sistema seriam afetadas?

O grupo deverá selecionar pelo menos duas mudanças possíveis. Exemplos:

```text
PostgreSQL -> outro mecanismo de persistencia
E-mail -> WhatsApp
Web -> inclusao de aplicativo mobile
```

Para cada mudança, explicar:

- quais elementos seriam afetados;
- quais permaneceriam inalterados;
- que decisões arquiteturais ajudariam ou dificultariam a mudança.

## 10. Estrutura sugerida do repositório

```text
projeto/
|
|-- README.md
|
|-- docs/
|   |-- requisitos.md
|   |-- arquitetura.md
|   |-- tradeoffs.md
|   |
|   |-- adr/
|   |   |-- ADR-001.md
|   |   |-- ADR-002.md
|   |   `-- ADR-003.md
|   |
|   `-- diagramas/
|       |-- classes.puml
|       |-- sequencia.puml
|       |-- comunicacao.puml
|       `-- componentes.puml
|
`-- src/
    `-- ...
```

## 11. O que não é necessário

Não será avaliado pelo número de telas nem pela quantidade de funcionalidades.

Não é necessário desenvolver, salvo quando relevante para demonstrar uma decisão arquitetural:

- login completo;
- CRUD de todas as entidades;
- painel administrativo completo;
- interface gráfica sofisticada;
- implantação em nuvem;
- microsserviços apenas para aumentar a complexidade do projeto.

O foco do trabalho é:

> requisitos → responsabilidades → design → arquitetura → código → consequências das decisões

## 12. Critérios de avaliação

| Critério | Peso |
|---|---:|
| Requisitos e identificação dos ASRs | 15% |
| Design | 15% |
| Modelagem UML e consistência entre modelos | 15% |
| Arquitetura proposta e organização das dependências | 20% |
| Justificativas, alternativas, trade-offs e ADRs | 15% |
| Protótipo e coerência entre arquitetura e código | 20% |
| **Total** | **100%** |

A avaliação considerará se a complexidade introduzida é justificada pelos requisitos, restrições e ASRs do problema.

## 13. Defesa

Na defesa, cada grupo deverá:

- apresentar brevemente o problema;
- destacar os principais ASRs;
- explicar a arquitetura escolhida;
- justificar pelo menos duas decisões arquiteturais;
- demonstrar o protótipo;
- responder perguntas sobre alternativas e trade-offs.

Durante a defesa poderá ser apresentada uma mudança de cenário, por exemplo:

- inclusão de um aplicativo mobile;
- substituição do serviço de e-mail;
- aumento significativo de carga;
- troca do mecanismo de persistência;
- necessidade de separar uma funcionalidade para implantação independente.

O grupo deverá explicar como essa mudança afetaria a arquitetura proposta.

## Temas dos projetos

Os temas são:

1. **Sistema de gestão de filas e atendimento presencial** — Sistema para organizar filas de atendimento, emitir senhas, aplicar regras de prioridade, chamar usuários e registrar o histórico dos atendimentos realizados.

2. **Agendamento de consultas em clínica universitária** — Sistema para organizar agendas de profissionais, permitir marcação, cancelamento e reagendamento de consultas, além de controlar conflitos de horários e confirmações.

3. **Reserva de salas e laboratórios** — Sistema para reservar espaços acadêmicos considerando capacidade, recursos disponíveis, horários, bloqueios e conflitos entre solicitações.

4. **Biblioteca com empréstimos e reservas** — Sistema para controlar livros e exemplares, realizar empréstimos, devoluções, renovações e reservas, incluindo situações de indisponibilidade e atraso.

5. **Manutenção de equipamentos de laboratório** — Sistema para registrar chamados de manutenção, classificar prioridades, atribuir técnicos, acompanhar intervenções e manter o histórico dos equipamentos.

6. **Pedidos antecipados do restaurante universitário** — Sistema para permitir a consulta ao cardápio, realização de pedidos antecipados, controle de disponibilidade, cancelamentos e organização da retirada das refeições.

7. **Gerenciamento de estágios** — Sistema para cadastrar vagas de estágio, receber candidaturas, acompanhar aprovações, registrar orientadores e controlar documentos e atividades do estágio.

8. **Eventos acadêmicos e inscrições** — Sistema para cadastrar eventos e atividades, controlar inscrições, vagas, lista de espera, cancelamentos e registro de presença dos participantes.

9. **Monitorias acadêmicas** — Sistema para gerenciar vagas de monitoria, candidaturas, seleção de alunos, horários de atendimento e registro das atividades realizadas pelos monitores.

10. **Sistema de estacionamento universitário** — Sistema para controlar veículos, usuários autorizados, entrada e saída, ocupação de vagas, reservas e restrições específicas de determinadas áreas.

11. **Marketplace de serviços dentro do campus** — Plataforma para que membros da comunidade ofereçam e solicitem serviços, com controle de disponibilidade, contratação, conclusão do serviço e avaliações.

12. **Gestão de projetos de extensão** — Sistema para cadastrar projetos de extensão, participantes e atividades, registrar participação e presença e acompanhar horas e requisitos para certificação.

13. **Controle de uso de infraestrutura computacional** — Sistema para gerenciar solicitações de recursos computacionais, como servidores, GPUs e armazenamento, considerando disponibilidade, período de uso, quotas e autorizações.

14. **Locação de espaços esportivos** — Sistema para organizar reservas de quadras e outros espaços esportivos, controlando horários, restrições de uso, cancelamentos e períodos de manutenção.

15. **Gestão de entregas internas do campus** — Sistema para registrar solicitações de transporte interno de documentos ou volumes, acompanhar coleta, deslocamento e entrega, além de manter prioridade e histórico.

16. **Plataforma de atendimento técnico de TI** — Sistema para registrar chamados de suporte, definir prioridade, atribuir equipes responsáveis, acompanhar estados, controlar prazos de atendimento e registrar interações.
