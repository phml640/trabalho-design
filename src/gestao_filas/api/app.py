"""Criação e configuração da aplicação HTTP."""

from fastapi import FastAPI

from gestao_senhas.api import router as senhas_router

app = FastAPI(title="Gestão de Filas", version="0.1.0")
app.include_router(senhas_router)


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    """Confirma que o processo da API está respondendo."""
    return {"status": "ok"}
