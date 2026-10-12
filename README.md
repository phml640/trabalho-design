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