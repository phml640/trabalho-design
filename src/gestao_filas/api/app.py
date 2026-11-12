"""Criação e configuração da aplicação HTTP."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gestao_compartilhada.application import UnidadeDeTrabalho
from gestao_compartilhada.domain import ErroDeRegraDeNegocio
from gestao_compartilhada.infrastructure import UnidadeDeTrabalhoEmMemoria
from gestao_filas.api.routes import router as filas_router
from gestao_senhas.api import router as senhas_router


def criar_app(unidade_de_trabalho: UnidadeDeTrabalho | None = None) -> FastAPI:
    app = FastAPI(title="Gestão de Filas", version="0.1.0")
    app.state.unidade_de_trabalho = (
        unidade_de_trabalho if unidade_de_trabalho is not None else UnidadeDeTrabalhoEmMemoria()
    )
    app.include_router(filas_router)
    app.include_router(senhas_router)

    @app.exception_handler(LookupError)
    async def nao_encontrado(request: Request, error: LookupError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(ErroDeRegraDeNegocio)
    async def conflito(request: Request, error: ErroDeRegraDeNegocio) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(ValueError)
    async def entrada_invalida(request: Request, error: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.get("/health", tags=["Sistema"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = criar_app()
