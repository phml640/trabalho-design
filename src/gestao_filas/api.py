"""Ponto de entrada HTTP ."""

from fastapi import FastAPI

app = FastAPI(title="Gestão de Filas", version="0.1.0")


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    """confirma que o processo da API está respondendo."""
    return {"status": "ok"}