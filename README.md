# Gestão de filas e atendimento presencial

Trabalho da disciplina de design de software

## Preparar o ambiente

requer python. Sugiro rodar em ambiente virtual (só seguir os comandos abaixo)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Executar

```bash
uvicorn gestao_filas.api:app --reload
```

voces podem acessar `http://localhost:8000/health` para conferir se a API iniciou. o fast api tem a documentação interativa também que fica em `http://localhost:8000/docs`.

## Integração de filas e senhas

Os dois gerenciadores recebem a mesma `UnidadeDeTrabalho`, definida em
`gestao_compartilhada.application`. A API faz essa composição em `criar_app()`.
Crie uma fila em `POST /filas` antes de emitir ou chamar suas senhas.
Filas inexistentes retornam 404, filas encerradas retornam 409 e entradas
inválidas retornam 422.

A transação de chamada confirma seleção, estado da senha, contador da fila,
histórico e evento `SenhaChamada` juntos. Encerrar uma fila cancela suas senhas
aguardando ou chamadas, preservando atendimentos em andamento. O dia operacional
segue `America/Sao_Paulo`; a virada cancela pendências antigas e reinicia o
contador de prioridade e a numeração do novo dia.

Nesta etapa, o adaptador é **em memória**, com bloqueio global por aplicação e
cópias do estado para rollback e isolamento das referências retornadas. Ele
funciona em um único processo e perde os dados no reinício. A etapa PostgreSQL
deverá implementar o mesmo contrato com bloqueio por fila, conforme o ADR-003.
Os eventos já são registrados atomicamente, mas sua entrega pelo notificador
fica para a fatia vertical.

Para executar as regressões de integração, concorrência e rollback:

```bash
python -m unittest discover -s tests -v
```

## Documentação

- [Requisitos e regras de negócio](docs/requisites.md)
- [ADR-001 — Stack inicial do backend](docs/adr/ADR-001-escolha-da-stack-do-backend.md)
- [ADR-002 — Monólito modular, Arquitetura Hexagonal e eventos internos](docs/adr/ADR-002-monolito-modular-hexagonal-eventos.md)
- [ADR-003 — PostgreSQL e estratégia de persistência](docs/adr/ADR-003-postgresql-persistencia.md)
- [ADR-004 — Notificações após a chamada](docs/adr/ADR-004-notificacoes.md)
