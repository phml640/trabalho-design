"""Casos de uso e contratos necessários para executá-los."""
"""Casos de uso do componente de filas."""


class QueueNotFoundError(LookupError):
    """Indica que a fila solicitada não existe."""


from .service import GestaoDeFilas

__all__ = ["GestaoDeFilas", "QueueNotFoundError"]