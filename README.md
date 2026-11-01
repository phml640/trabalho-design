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

## Documentação

- [Requisitos e regras de negócio](docs/requisites.md)
- [ADR-001 — Stack inicial do backend](docs/adr/ADR-001-escolha-da-stack-do-backend.md)
- [ADR-002 — Monólito modular, Arquitetura Hexagonal e eventos internos](docs/adr/ADR-002-monolito-modular-hexagonal-eventos.md)
- [ADR-003 — PostgreSQL e estratégia de persistência](docs/adr/ADR-003-postgresql-persistencia.md)
- [ADR-004 — Notificações após a chamada](docs/adr/ADR-004-notificacoes.md)
