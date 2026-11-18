FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install . && useradd --create-home app

COPY alembic.ini ./
COPY migrations ./migrations
# Ferramentas de verificação da entrega: executáveis sem Python instalado no host.
COPY tests ./tests
COPY scripts ./scripts
USER app

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn gestao_filas.api:app --host 0.0.0.0 --port 8000"]
