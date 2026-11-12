"""Regressões dos contratos comuns e da atomicidade do adaptador em memória."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from threading import Barrier
import unittest
from unittest.mock import patch
from uuid import uuid4

from gestao_compartilhada.domain import ErroDeRegraDeNegocio, QueueNotFoundError
from gestao_compartilhada.infrastructure import TransacaoEmMemoria, UnidadeDeTrabalhoEmMemoria
from gestao_filas.api.app import criar_app
from gestao_filas.application import GestaoDeFilas
from gestao_filas.domain.model import EstadoFila
from gestao_senhas.application import GerenciadorDeSenhas
from gestao_senhas.domain import EstadoSenha, TipoSenha

AGORA = datetime(2026, 11, 12, 15, tzinfo=timezone.utc)


class IntegracaoTest(unittest.TestCase):
    def setUp(self):
        self.uow = UnidadeDeTrabalhoEmMemoria()
        self.filas = GestaoDeFilas(self.uow)
        self.senhas = GerenciadorDeSenhas(self.uow)
        self.fila = self.filas.criar_fila("Caixa", quando=AGORA)
        self.fila_id = str(self.fila.id)

    def emitir(self, tipo=TipoSenha.NORMAL, quando=AGORA):
        return self.senhas.emitir_senha(
            fila_id=self.fila_id, usuario_id="usuario", tipo=tipo,
            canal="totem", emitida_em=quando,
        )

    def chamar(self, atendente="atendente", quando=AGORA):
        return self.senhas.chamar_proxima_senha(
            fila_id=self.fila_id, atendente_id=atendente, guiche_id="guiche", chamada_em=quando,
        )

    def buscar(self, senha_id):
        with self.uow.transacao(self.fila.id) as tx:
            return tx.senhas.buscar(senha_id)

    def test_fila_inexistente_e_encerrada(self):
        for fila_id, erro in [(str(uuid4()), QueueNotFoundError), (self.fila_id, ErroDeRegraDeNegocio)]:
            if fila_id == self.fila_id:
                self.filas.encerrar_fila(self.fila.id, AGORA)
            with self.assertRaises(erro):
                self.senhas.emitir_senha(
                    fila_id=fila_id, usuario_id="u", tipo=TipoSenha.NORMAL, canal="online", emitida_em=AGORA,
                )
            with self.assertRaises(erro):
                self.senhas.chamar_proxima_senha(
                    fila_id=fila_id, atendente_id="a", guiche_id="g", chamada_em=AGORA,
                )
        self.assertEqual(self.uow.historico, ())
        self.assertEqual(self.uow.eventos, ())

    def test_politica_duas_prioritarias_e_fifo(self):
        normais = [self.emitir(quando=AGORA + timedelta(seconds=i)) for i in range(3)]
        prioritarias = [self.emitir(TipoSenha.PRIORITARIA, AGORA + timedelta(seconds=i)) for i in range(3)]
        esperadas = [prioritarias[0], prioritarias[1], normais[0], prioritarias[2], normais[1], normais[2]]
        chamadas = [self.chamar(quando=AGORA + timedelta(minutes=1)) for _ in esperadas]
        self.assertEqual([s.id for s in chamadas], [s.id for s in esperadas])
        self.assertEqual(len(self.uow.eventos), 6)
        self.assertIsNone(self.chamar(quando=AGORA + timedelta(minutes=1)))

    def test_prioritarias_sozinhas_contam_e_reabertura_nao_zera(self):
        for _ in range(2):
            self.emitir(TipoSenha.PRIORITARIA)
            self.chamar()
        self.filas.reabrir_fila(self.fila.id, AGORA)
        self.emitir(TipoSenha.PRIORITARIA)
        normal = self.emitir()
        self.assertEqual(self.chamar().id, normal.id)
        self.assertEqual(self.filas.obter_fila(self.fila.id).chamadas_prioritarias_consecutivas, 0)

    def test_chamadas_concorrentes_nao_repetem_senha(self):
        for _ in range(12):
            self.emitir(TipoSenha.PRIORITARIA)
        barreira = Barrier(16)

        def chamar(i):
            barreira.wait(timeout=10)
            # Instâncias distintas representam requisições independentes.
            return GerenciadorDeSenhas(self.uow).chamar_proxima_senha(
                fila_id=self.fila_id, atendente_id=f"a{i}", guiche_id=f"g{i}", chamada_em=AGORA,
            )

        with ThreadPoolExecutor(max_workers=16) as pool:
            resultados = list(pool.map(chamar, range(16)))
        chamadas = [s for s in resultados if s is not None]
        self.assertEqual(len(chamadas), 12)
        self.assertEqual(len({s.id for s in chamadas}), 12)
        self.assertEqual(len({s.atendente_id for s in chamadas}), 12)
        self.assertEqual(self.filas.obter_fila(self.fila.id).chamadas_prioritarias_consecutivas, 12)
        self.assertEqual(len(self.uow.eventos), 12)
        self.assertEqual(len([t for t in self.uow.historico if t.estado == "chamada"]), 12)
        for s in chamadas:
            self.assertEqual(self.buscar(s.id).atendente_id, s.atendente_id)

    def test_falha_apos_evento_reverte_toda_chamada(self):
        senha = self.emitir(TipoSenha.PRIORITARIA)
        historico = self.uow.historico
        registrar = TransacaoEmMemoria.registrar_evento

        def falhar(tx, evento):
            registrar(tx, evento)
            raise RuntimeError("falha antes do commit")

        with patch.object(TransacaoEmMemoria, "registrar_evento", falhar):
            with self.assertRaises(RuntimeError):
                self.chamar()
        self.assertEqual(self.buscar(senha.id).estado, EstadoSenha.AGUARDANDO)
        self.assertIsNone(self.buscar(senha.id).atendente_id)
        self.assertEqual(self.filas.obter_fila(self.fila.id).chamadas_prioritarias_consecutivas, 0)
        self.assertEqual(self.uow.historico, historico)
        self.assertEqual(self.uow.eventos, ())
        self.assertEqual(self.chamar().id, senha.id)
        self.assertEqual(len(self.uow.eventos), 1)

    def test_prioridade_sob_concorrencia_e_isolada_por_fila(self):
        for _ in range(6):
            self.emitir(TipoSenha.PRIORITARIA)
        for _ in range(3):
            self.emitir()
        outra = self.filas.criar_fila("Outra", quando=AGORA)
        barreira = Barrier(9)

        def chamar(i):
            barreira.wait(timeout=10)
            return self.chamar(atendente=f"a{i}")

        with ThreadPoolExecutor(max_workers=9) as pool:
            chamadas = list(pool.map(chamar, range(9)))
        tipos = {s.id: s.tipo for s in chamadas}
        self.assertEqual(
            [tipos[e.senha_id] for e in self.uow.eventos],
            [TipoSenha.PRIORITARIA, TipoSenha.PRIORITARIA, TipoSenha.NORMAL] * 3,
        )
        self.assertEqual(self.filas.obter_fila(outra.id).chamadas_prioritarias_consecutivas, 0)
        senha = self.senhas.emitir_senha(
            fila_id=str(outra.id), usuario_id="u", tipo=TipoSenha.NORMAL,
            canal="online", emitida_em=AGORA,
        )
        self.assertEqual(senha.numero, "N001")
        self.filas.encerrar_fila(self.fila.id, AGORA)
        self.assertEqual(self.buscar(senha.id).estado, EstadoSenha.AGUARDANDO)

    def test_encerramento_cancela_pendentes_preserva_atendimento_e_e_idempotente(self):
        em_atendimento = self.emitir()
        self.chamar()
        self.senhas.iniciar_atendimento(str(em_atendimento.id), AGORA)
        chamada = self.emitir()
        self.chamar()
        aguardando = self.emitir()
        self.filas.encerrar_fila(self.fila.id, AGORA)
        tamanho = len(self.uow.historico)
        self.filas.encerrar_fila(self.fila.id, AGORA)
        self.assertEqual(len(self.uow.historico), tamanho)
        for senha in (chamada, aguardando):
            atual = self.buscar(senha.id)
            self.assertEqual(atual.estado, EstadoSenha.CANCELADA)
            self.assertEqual(atual.motivo_cancelamento, "encerramento_administrativo")
        self.assertEqual(self.buscar(em_atendimento.id).estado, EstadoSenha.EM_ATENDIMENTO)
        self.senhas.finalizar_atendimento(str(em_atendimento.id), AGORA)
        self.filas.reabrir_fila(self.fila.id, AGORA)
        self.assertIsNone(self.chamar())

    def test_falha_no_encerramento_reverte_cancelamentos_e_fila(self):
        senhas = [self.emitir(), self.emitir()]
        registrar = TransacaoEmMemoria.registrar_transicao

        def falhar(tx, transicao):
            registrar(tx, transicao)
            raise RuntimeError("falha no histórico")

        with patch.object(TransacaoEmMemoria, "registrar_transicao", falhar):
            with self.assertRaises(RuntimeError):
                self.filas.encerrar_fila(self.fila.id, AGORA)
        self.assertEqual(self.filas.obter_fila(self.fila.id).estado, EstadoFila.ABERTA)
        self.assertTrue(all(self.buscar(s.id).estado is EstadoSenha.AGUARDANDO for s in senhas))
        self.assertEqual(len(self.uow.historico), 2)

    def test_encerramento_disputando_emissao_e_chamada(self):
        self.emitir()
        barreira = Barrier(3)

        def executar(acao):
            barreira.wait(timeout=10)
            try:
                return acao()
            except ErroDeRegraDeNegocio:
                return None  # Encerramento venceu a disputa.

        with ThreadPoolExecutor(max_workers=3) as pool:
            resultados = [pool.submit(executar, acao) for acao in (
                self.emitir, self.chamar, lambda: self.filas.encerrar_fila(self.fila.id, AGORA),
            )]
            for resultado in resultados:
                resultado.result(timeout=10)
        self.assertEqual(self.filas.obter_fila(self.fila.id).estado, EstadoFila.ENCERRADA)
        with self.uow.transacao(self.fila.id) as tx:
            senhas = tx.senhas.listar(self.fila.id)
        self.assertTrue(all(s.estado is EstadoSenha.CANCELADA for s in senhas))
        self.assertTrue(all(s.motivo_cancelamento == "encerramento_administrativo" for s in senhas))

    def test_virada_no_fuso_cancela_pendentes_e_reinicia_numero_e_contador(self):
        antes = datetime(2026, 11, 13, 2, 59, tzinfo=timezone.utc)  # Ainda dia 12 em SP.
        depois = antes + timedelta(minutes=2)
        chamada = self.emitir(TipoSenha.PRIORITARIA, antes)
        self.chamar(quando=antes)
        aguardando = self.emitir(quando=antes)
        self.assertEqual(self.senhas.consultar_fila(self.fila_id, depois), [])
        for senha in (chamada, aguardando):
            self.assertEqual(self.buscar(senha.id).motivo_cancelamento, "encerramento_diario")
        self.assertEqual(self.filas.obter_fila(self.fila.id).chamadas_prioritarias_consecutivas, 0)
        nova = self.emitir(TipoSenha.PRIORITARIA, depois)
        self.assertEqual(nova.numero, "P001")
        self.assertEqual(nova.dia_operacional.day, 13)
        self.senhas.consultar_fila(self.fila_id, depois)
        self.assertEqual(len([t for t in self.uow.historico if t.estado == "cancelada"]), 2)

    def test_atendimento_pode_finalizar_no_dia_seguinte(self):
        senha = self.emitir()
        self.chamar()
        self.senhas.iniciar_atendimento(str(senha.id), AGORA)
        amanha = AGORA + timedelta(days=1)
        self.senhas.consultar_fila(self.fila_id, amanha)
        finalizada = self.senhas.finalizar_atendimento(str(senha.id), amanha)
        self.assertEqual(finalizada.estado, EstadoSenha.FINALIZADA)
        self.assertEqual(finalizada.dia_operacional, AGORA.date())

    def test_validacao_nao_consume_numeracao_ou_prioridade(self):
        with self.assertRaises(ValueError):
            self.senhas.emitir_senha(
                fila_id=self.fila_id, usuario_id=" ", tipo=TipoSenha.NORMAL, canal="totem", emitida_em=AGORA,
            )
        self.assertEqual(self.emitir().numero, "N001")
        with self.assertRaises(ValueError):
            self.chamar(atendente=" ")
        with self.assertRaises(ValueError):
            self.chamar(quando=AGORA.replace(tzinfo=None))
        with self.assertRaises(ErroDeRegraDeNegocio):
            self.chamar(quando=AGORA - timedelta(seconds=1))
        self.assertEqual(len(self.uow.historico), 1)
        self.assertEqual(self.uow.eventos, ())

    def test_referencias_externas_nao_alteram_persistencia(self):
        senha = self.emitir()
        senha.estado = EstadoSenha.CANCELADA
        self.fila.chamadas_prioritarias_consecutivas = 100
        self.assertEqual(self.buscar(senha.id).estado, EstadoSenha.AGUARDANDO)
        self.assertEqual(self.filas.obter_fila(self.fila.id).chamadas_prioritarias_consecutivas, 0)
        with self.uow.transacao(self.fila.id) as tx:
            fila = tx.filas.buscar(self.fila.id)
            fila.nome = "Confirmado"
            tx.filas.salvar(fila)
        fila.nome = "Mutação posterior"
        tx.filas.salvar(fila)
        self.assertEqual(self.filas.obter_fila(self.fila.id).nome, "Confirmado")

    def test_numeracao_concorrente_e_unicidade_de_nomes(self):
        barreira = Barrier(8)

        def emitir(_):
            barreira.wait(timeout=10)
            return self.emitir()

        with ThreadPoolExecutor(max_workers=8) as pool:
            senhas = list(pool.map(emitir, range(8)))
        self.assertEqual({s.numero for s in senhas}, {f"N{i:03d}" for i in range(1, 9)})
        barreira = Barrier(8)

        def criar(_):
            barreira.wait(timeout=10)
            try:
                return self.filas.criar_fila(" Outra ", quando=AGORA)
            except ErroDeRegraDeNegocio:
                return None

        with ThreadPoolExecutor(max_workers=8) as pool:
            filas = list(pool.map(criar, range(8)))
        self.assertEqual(len([f for f in filas if f is not None]), 1)


async def requisitar(app, metodo, caminho, dados=None):
    """Executa o contrato ASGI real sem adicionar dependências de cliente HTTP."""
    corpo = json.dumps(dados).encode() if dados is not None else b""
    mensagens = []
    enviada = False

    async def receber():
        nonlocal enviada
        if not enviada:
            enviada = True
            return {"type": "http.request", "body": corpo, "more_body": False}
        await asyncio.Future()

    async def enviar(mensagem):
        mensagens.append(mensagem)

    escopo = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": metodo, "scheme": "http", "path": caminho,
        "raw_path": caminho.encode(), "query_string": b"",
        "root_path": "", "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1234), "server": ("test", 80),
    }
    await asyncio.wait_for(app(escopo, receber, enviar), timeout=10)
    status = next(m["status"] for m in mensagens if m["type"] == "http.response.start")
    resposta = b"".join(m.get("body", b"") for m in mensagens if m["type"] == "http.response.body")
    return status, json.loads(resposta) if resposta else None


class ApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_mesmo_estado_entre_rotas_e_erros_http(self):
        app = criar_app()
        status, fila = await requisitar(app, "POST", "/filas", {"nome": "Teste"})
        self.assertEqual(status, 201)
        caminho = f'/filas/{fila["id"]}'
        status, senha = await requisitar(app, "POST", caminho + "/senhas", {"usuario_id": "u"})
        self.assertEqual(status, 201)
        status, chamada = await requisitar(app, "POST", caminho + "/senhas/chamada", {
            "atendente_id": "a", "guiche_id": "g",
        })
        self.assertEqual(status, 200)
        self.assertEqual(chamada["id"], senha["id"])
        self.assertEqual(chamada["estado"], "chamada")
        self.assertEqual((await requisitar(app, "POST", caminho + "/encerramento"))[0], 200)
        status, senhas = await requisitar(app, "GET", caminho + "/senhas")
        self.assertEqual((status, senhas), (200, []))
        self.assertEqual((await requisitar(app, "POST", caminho + "/senhas", {"usuario_id": "u"}))[0], 409)
        self.assertEqual((await requisitar(app, "POST", caminho + "/senhas/chamada", {
            "atendente_id": "a", "guiche_id": "g",
        }))[0], 409)
        self.assertEqual((await requisitar(app, "POST", f"/filas/{uuid4()}/senhas", {"usuario_id": "u"}))[0], 404)
        self.assertEqual((await requisitar(app, "GET", "/filas/invalido/senhas"))[0], 422)
        self.assertEqual((await requisitar(app, "POST", caminho + "/senhas", {"usuario_id": " "}))[0], 422)
        self.assertEqual((await requisitar(app, "POST", caminho + "/senhas", {
            "usuario_id": "u", "canal": "invalido",
        }))[0], 422)
        self.assertEqual((await requisitar(app, "POST", "/filas", {"nome": " teste "}))[0], 409)
        self.assertEqual((await requisitar(app, "GET", "/health")), (200, {"status": "ok"}))
        self.assertEqual((await requisitar(criar_app(), "GET", caminho))[0], 404)


if __name__ == "__main__":
    unittest.main()
