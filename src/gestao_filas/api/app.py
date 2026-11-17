"""Criação e configuração da aplicação HTTP."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gestao_compartilhada.application import UnidadeDeTrabalho
from gestao_compartilhada.domain import ErroDeRegraDeNegocio
from gestao_compartilhada.configuracao import criar_unidade_de_trabalho
from gestao_compartilhada.api import router as operacoes_router
from gestao_compartilhada.notificacoes import Notificador
from gestao_compartilhada.notificador import FakeNotificador
from gestao_filas.api.routes import router as filas_router
from gestao_senhas.api import router as senhas_router


def criar_app(unidade_de_trabalho: UnidadeDeTrabalho | None = None, *, notificador: Notificador | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            # A aplicação só encerra o pool que ela mesma criou.
            if unidade_de_trabalho is None:
                engine = getattr(app.state.unidade_de_trabalho, "engine", None)
                if engine is not None:
                    engine.dispose()

    app = FastAPI(
        title="Gestão de Filas", version="0.2.0", lifespan=lifespan,
        description="Protótipo acadêmico local, sem autenticação. Visões de usuário e atendente não são uma fronteira de segurança. Prioridade demonstrativa, sem verificação de elegibilidade.",
    )
    app.state.unidade_de_trabalho = (
        unidade_de_trabalho if unidade_de_trabalho is not None else criar_unidade_de_trabalho()
    )
    app.state.notificador = notificador if notificador is not None else FakeNotificador(app.state.unidade_de_trabalho)
    app.state.notificador_falho = FakeNotificador(app.state.unidade_de_trabalho, falhar=True)
    app.include_router(filas_router)
    app.include_router(senhas_router)
    app.include_router(operacoes_router)

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
