"""Executa as regressões com um banco de teste separado, inclusive dentro do Docker."""

import os
from pathlib import Path
import unittest

from gestao_compartilhada.configuracao import url_postgres


if __name__ == "__main__":
    os.environ["PERSISTENCIA"] = "memoria"
    if not os.getenv("TEST_DATABASE_URL"):
        os.environ["TEST_DATABASE_URL"] = url_postgres().set(
            database=os.getenv("TEST_POSTGRES_DB", "gestao_filas_teste"),
        ).render_as_string(hide_password=False)
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parents[1] / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
