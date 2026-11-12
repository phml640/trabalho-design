"""Interface HTTP do sistema."""

from .app import app

__all__ = ["app"]
"""Interface HTTP da gestão de filas."""

from .routes import router

__all__ = ["router"]
