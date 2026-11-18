"""Medição exploratória: três rajadas HTTP de 50 clientes sobre 10 mil senhas.

Use DATABASE_URL e uma API ligados ao mesmo banco descartável. A preparação
insere uma fila exclusiva por execução; não limpa nem altera filas anteriores.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
from threading import Barrier
from time import perf_counter
from uuid import UUID

from sqlalchemy import func, insert, select

from gestao_compartilhada.configuracao import criar_engine_postgres
from gestao_compartilhada.domain import TransicaoSenha
from gestao_compartilhada.postgres.models import ContadorSenhaModelo, FilaModelo, SenhaModelo, TransicaoModelo
from gestao_filas.domain.model import Fila
from gestao_senhas.domain import Senha, TipoSenha
from verificar_api import ClienteAPI


def preparar(quantidade: int):
    agora = datetime.now(timezone.utc)
    fila = Fila(nome=f"ASR02 {agora.isoformat()}", criada_em=agora)
    contadores = {tipo: 0 for tipo in TipoSenha}
    engine = criar_engine_postgres()
    try:
        with engine.begin() as conn:
            conn.execute(insert(FilaModelo), {**asdict(fila), "nome_normalizado": fila.nome.casefold()})
            for inicio in range(0, quantidade, 1000):
                senhas, historico = [], []
                for i in range(inicio, min(inicio + 1000, quantidade)):
                    tipo = TipoSenha.NORMAL if i % 2 == 0 else TipoSenha.PRIORITARIA
                    contadores[tipo] += 1
                    senha = Senha(
                        fila_id=str(fila.id), numero=f"{'N' if tipo == TipoSenha.NORMAL else 'P'}{contadores[tipo]:03d}",
                        tipo=tipo, usuario_id="carga-sintetica", emitida_em=agora, canal="totem",
                    )
                    senhas.append({**asdict(senha), "fila_id": UUID(senha.fila_id)})
                    historico.append(asdict(TransicaoSenha(senha.id, fila.id, None, senha.estado, agora)))
                conn.execute(insert(SenhaModelo), senhas)
                conn.execute(insert(TransicaoModelo), historico)
            conn.execute(insert(ContadorSenhaModelo), [
                {"fila_id": fila.id, "dia_operacional": fila.dia_operacional, "tipo": tipo, "ultimo_numero": valor}
                for tipo, valor in contadores.items()
            ])
            total = conn.scalar(select(func.count()).select_from(SenhaModelo))
        return fila, total
    finally:
        engine.dispose()


def medir(operacao, clientes):
    barreira = Barrier(clientes)

    def executar(i):
        barreira.wait(timeout=30)
        inicio = perf_counter()
        erro = None
        try:
            operacao(i)
        except Exception as exc:
            erro = f"{type(exc).__name__}: {exc}"
        return (perf_counter() - inicio) * 1000, erro

    with ThreadPoolExecutor(max_workers=clientes) as pool:
        amostras = list(pool.map(executar, range(clientes)))
    tempos = sorted(t for t, _ in amostras)
    erros = [e for _, e in amostras if e]
    return {
        "requisicoes": clientes, "erros": len(erros),
        "p50_ms": round(tempos[math.ceil(len(tempos) * .5) - 1], 2),
        "p95_ms": round(tempos[math.ceil(len(tempos) * .95) - 1], 2),
        "max_ms": round(tempos[-1], 2), "detalhes_erros": erros[:3],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--clientes", type=int, default=50)
    parser.add_argument("--senhas", type=int, default=10000)
    parser.add_argument("--ambiente", required=True, help="Descrição das condições, incluindo execução nativa ou em Docker.")
    parser.add_argument("--saida", type=Path)
    args = parser.parse_args()
    if args.clientes < 1 or args.senhas < args.clientes:
        parser.error("Use ao menos um cliente e quantidade de senhas maior ou igual ao número de clientes.")
    fila, total = preparar(args.senhas)
    api = ClienteAPI(args.base_url, timeout=180)
    caminho = f"/filas/{fila.id}/senhas"
    api.requisitar("GET", f"/filas/{fila.id}")
    api.requisitar("GET", caminho)  # Uma consulta de aquecimento, fora das amostras.
    resultados = {}
    operacoes = {
        "emissao": lambda i: api.requisitar("POST", caminho, {"usuario_id": f"carga-{i}", "tipo": "normal"}, status=201),
        "consulta_fila_ativa": lambda i: api.requisitar("GET", caminho),
        "chamada": lambda i: api.requisitar("POST", caminho + "/chamada", {"atendente_id": f"carga-{i}", "guiche_id": f"g-{i}"}),
    }
    for nome, operacao in operacoes.items():
        print(f"Medindo {nome}: {args.clientes} clientes concorrentes…", flush=True)
        resultados[nome] = medir(operacao, args.clientes)
        print(json.dumps(resultados[nome], ensure_ascii=False), flush=True)
    relatorio = {
        "data_utc": datetime.now(timezone.utc).isoformat(), "ambiente": args.ambiente,
        "sistema": platform.platform(), "python": platform.python_version(),
        "fastapi": version("fastapi"), "sqlalchemy": version("SQLAlchemy"),
        "cpus_visiveis": os.cpu_count(), "fila_id": str(fila.id),
        "clientes_concorrentes": args.clientes, "senhas_iniciais_na_fila": args.senhas,
        "senhas_totais_no_banco_antes_das_rajadas": total,
        "cenario": "Uma fila, todas as senhas inicialmente aguardando, 50% prioritárias. Uma rajada por operação, nesta ordem: emissão, consulta, chamada. Uma consulta de aquecimento. Um cliente Python com threads; duração inclui HTTP, transferência e leitura do JSON. Sem processamento de notificações.",
        "meta_p95_ms": 500, "resultados": resultados,
        "todas_rajadas_abaixo_da_meta": all(r["p95_ms"] <= 500 and r["erros"] == 0 for r in resultados.values()),
        "limites": "Amostra pequena e exploratória, sem teste sustentado ou repetição estatística. Não certifica o ASR02 nem substitui validação no hardware da apresentação.",
    }
    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n")
    else:
        print(json.dumps(relatorio, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
