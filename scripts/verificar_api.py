"""Teste HTTP da entrega, com registro opcional para conferir persistência após reinício.

Cria dados fictícios e processa notificações globais: use uma instância de demonstração.
Pode ser executado dentro do container da API, sem ferramentas instaladas no host.
"""

import argparse
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


class ClienteAPI:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def requisitar(self, metodo: str, caminho: str, dados=None, *, status=200):
        corpo = json.dumps(dados).encode() if dados is not None else None
        request = Request(self.base_url + caminho, method=metodo, data=corpo,
                          headers={"Content-Type": "application/json"})
        try:
            response = urlopen(request, timeout=self.timeout)
        except HTTPError as error:
            response = error
        with response:
            recebido = response.read().decode()
            if response.status != status:
                raise AssertionError(f"{metodo} {caminho}: esperado {status}, recebido {response.status}: {recebido[:300]}")
            return json.loads(recebido)


def conferir_frontend(url: str):
    for path in ("/", "/usuario", "/admin"):
        with urlopen(url.rstrip("/") + path, timeout=15) as response:
            html = response.read().decode()
            assert response.status == 200 and '<div id="root"></div>' in html, f"SPA indisponível: {path}"
    asset = re.search(r'src="(/assets/[^\"]+\.js)"', html)
    assert asset, "Bundle compilado do React não encontrado."
    with urlopen(url.rstrip("/") + asset.group(1), timeout=15) as response:
        assert response.status == 200 and "javascript" in response.headers.get_content_type()
    print("OK: frontend compilado, assets e rotas diretas /usuario e /admin")


def verificar_fluxo(api: ClienteAPI) -> dict:
    get = lambda path: api.requisitar("GET", path)
    post = lambda path, data=None, status=200: api.requisitar("POST", path, data, status=status)
    assert get("/health") == {"status": "ok"}
    fila = post("/filas", {"nome": f"Entrega {uuid4().hex[:8]}", "descricao": "Verificação acadêmica"}, 201)
    caminho = f'/filas/{fila["id"]}'

    def emitir(tipo):
        return post(caminho + "/senhas", {"usuario_id": uuid4().hex, "tipo": tipo, "canal": "totem"}, 201)

    normal, p1, p2 = emitir("normal"), emitir("prioritaria"), emitir("prioritaria")
    assert len(get(caminho + "/senhas")) == 3
    chamadas = [post(caminho + "/senhas/chamada", {"atendente_id": "demo", "guiche_id": "demo-1"}) for _ in range(3)]
    assert [s["id"] for s in chamadas] == [p1["id"], p2["id"], normal["id"]]
    print("OK: criar fila, emitir normal/prioritárias, consultar e chamar na ordem esperada")

    query = "?" + urlencode({"fila_id": fila["id"], "limite": 100})
    eventos_path = "/notificacoes" + query
    eventos = get(eventos_path)["itens"]
    assert len(eventos) == 3 and all(e["tentativas"] == 0 for e in eventos)
    post("/notificacoes/processamento", {"limite": 100, "simular_falha": True})
    assert all(e["status"] == "falha" for e in get(eventos_path)["itens"])
    assert get(f'/senhas/{p1["id"]}')["estado"] == "chamada"
    post("/notificacoes/processamento", {"limite": 100})
    assert all(e["status"] == "processada" for e in get(eventos_path)["itens"])
    simuladas_path = "/notificacoes/simuladas" + query
    assert len(get(simuladas_path)["itens"]) == 3
    print("OK: eventos, falha sem desfazer chamada, retentativa e mensagens simuladas")

    atendimento = f'/senhas/{p1["id"]}/atendimento'
    assert post(atendimento + "/inicio")["estado"] == "em_atendimento"
    assert post(atendimento + "/finalizacao")["estado"] == "finalizada"
    post(atendimento + "/inicio", status=409)
    historico_path = caminho + "/historico?limite=100"
    assert any(t["estado"] == "finalizada" and t["senha_id"] == p1["id"] for t in get(historico_path)["itens"])
    aguardando = emitir("normal")
    post(caminho + "/encerramento")
    for senha in (normal, p2, aguardando):
        atual = get(f'/senhas/{senha["id"]}')
        assert atual["estado"] == "cancelada" and atual["motivo_cancelamento"] == "encerramento_administrativo"
    post(caminho + "/senhas", {"usuario_id": "demo"}, 409)
    post(caminho + "/senhas/chamada", {"atendente_id": "demo", "guiche_id": "demo"}, 409)
    print("OK: iniciar/finalizar atendimento, histórico, cancelamentos e erros em fila encerrada")

    paths = [caminho, historico_path, eventos_path, simuladas_path]
    paths += [f'/senhas/{s["id"]}' for s in (normal, p1, p2, aguardando)]
    paths += [f'/notificacoes/{e["evento"]["id"]}/tentativas?limite=100' for e in eventos]
    return {"fila_id": fila["id"], "consultas": {path: get(path) for path in paths}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://frontend/api")
    parser.add_argument("--frontend-url", default="http://frontend")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--registrar", type=Path, help="Salva respostas oficiais para comparação após reinício.")
    mode.add_argument("--conferir", type=Path, help="Compara as respostas atuais com o registro anterior.")
    args = parser.parse_args()
    if args.frontend_url:
        conferir_frontend(args.frontend_url)
    api = ClienteAPI(args.base_url)
    if args.conferir:
        snapshot = json.loads(args.conferir.read_text())
        for path, esperado in snapshot["consultas"].items():
            assert api.requisitar("GET", path) == esperado, f"Dados diferentes após reinício: {path}"
        print("OK: estados, números, contador da fila, histórico, eventos, tentativas e mensagens preservados")
    else:
        snapshot = verificar_fluxo(api)
        if args.registrar:
            args.registrar.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
            print(f"Registro de verificação salvo em {args.registrar}")
    print("Verificação de entrega concluída.")


if __name__ == "__main__":
    main()
