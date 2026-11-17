"""Contrato em PostgreSQL real. Cada classe usa um schema descartável exclusivo."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from threading import Event
import time
import unittest
from unittest.mock import patch
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.schema import CreateSchema, DropSchema

from gestao_compartilhada.configuracao import criar_engine_postgres
from gestao_compartilhada.postgres import TransacaoPostgres, UnidadeDeTrabalhoPostgres
from gestao_compartilhada.notificacoes import ProcessadorOutbox
from gestao_compartilhada.notificador import FakeNotificador
from gestao_filas.application import GestaoDeFilas
from gestao_filas.domain.model import EstadoFila
from gestao_senhas.application import GerenciadorDeSenhas
from gestao_senhas.domain import EstadoSenha, TipoSenha

import test_integracao as contrato
import test_fluxo_completo as fluxo

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
RAIZ = Path(__file__).resolve().parents[1]


class BancoPostgresMixin:
    @classmethod
    def setUpClass(cls):
        cls.schema = f"gc_teste_{uuid4().hex}"
        url = make_url(TEST_DATABASE_URL)
        if url.drivername == "postgresql":
            url = url.set(drivername="postgresql+psycopg")
        if url.drivername != "postgresql+psycopg":
            raise ValueError("TEST_DATABASE_URL deve apontar para PostgreSQL com psycopg.")
        cls.admin = create_engine(url)
        cls.addClassCleanup(cls.admin.dispose)
        with cls.admin.begin() as conn:
            conn.execute(CreateSchema(cls.schema))
        cls.addClassCleanup(cls.remover_schema)
        cls.url = url.update_query_dict({"options": f"-c search_path={cls.schema}"})
        cls.engine = criar_engine_postgres(cls.url)
        cls.addClassCleanup(cls.engine.dispose)
        cls.migrar("head")

    @classmethod
    def remover_schema(cls):
        with cls.admin.begin() as conn:
            conn.execute(DropSchema(cls.schema, cascade=True))

    @classmethod
    def migrar(cls, destino, *, reverter=False):
        cfg = Config(str(RAIZ / "alembic.ini"))
        with cls.engine.begin() as conn:
            cfg.attributes["connection"] = conn
            (command.downgrade if reverter else command.upgrade)(cfg, destino)

    def limpar(self):
        with self.engine.begin() as conn:
            conn.execute(text(
                "TRUNCATE notificacoes_simuladas, tentativas_notificacao, outbox, "
                "historico_transicoes, contadores_senhas, senhas, filas RESTART IDENTITY"
            ))


@unittest.skipUnless(TEST_DATABASE_URL, "Defina TEST_DATABASE_URL para testar PostgreSQL real.")
class IntegracaoPostgresTest(BancoPostgresMixin, contrato.IntegracaoTest):
    """Reexecuta as regressões de domínio e concorrência no adaptador real."""

    def setUp(self):
        self.limpar()
        self.uow = UnidadeDeTrabalhoPostgres(self.engine)
        self.filas = GestaoDeFilas(self.uow)
        self.senhas = GerenciadorDeSenhas(self.uow)
        self.fila = self.filas.criar_fila("Caixa", quando=contrato.AGORA)
        self.fila_id = str(self.fila.id)

    def test_falha_apos_evento_reverte_toda_chamada(self):
        senha = self.emitir(TipoSenha.PRIORITARIA)
        historico = self.uow.historico
        registrar = TransacaoPostgres.registrar_evento

        def falhar(tx, evento):
            registrar(tx, evento)  # INSERT já enviado ao banco, ainda sem commit.
            raise RuntimeError("falha antes do commit")

        with patch.object(TransacaoPostgres, "registrar_evento", falhar):
            with self.assertRaises(RuntimeError):
                self.chamar()
        self.assertEqual(self.buscar(senha.id).estado, EstadoSenha.AGUARDANDO)
        self.assertIsNone(self.buscar(senha.id).atendente_id)
        self.assertEqual(self.filas.obter_fila(self.fila.id).chamadas_prioritarias_consecutivas, 0)
        self.assertEqual(self.uow.historico, historico)
        self.assertEqual(self.uow.eventos, ())
        self.assertEqual(self.chamar().id, senha.id)
        self.assertEqual(len(self.uow.eventos), 1)

    def test_falha_no_encerramento_reverte_cancelamentos_e_fila(self):
        senhas = [self.emitir(), self.emitir()]
        registrar = TransacaoPostgres.registrar_transicao

        def falhar(tx, transicao):
            registrar(tx, transicao)
            raise RuntimeError("falha no histórico")

        with patch.object(TransacaoPostgres, "registrar_transicao", falhar):
            with self.assertRaises(RuntimeError):
                self.filas.encerrar_fila(self.fila.id, contrato.AGORA)
        self.assertEqual(self.filas.obter_fila(self.fila.id).estado, EstadoFila.ABERTA)
        self.assertTrue(all(self.buscar(s.id).estado is EstadoSenha.AGUARDANDO for s in senhas))
        self.assertEqual(len(self.uow.historico), 2)

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
        # Repositórios SQL só podem ser usados no contexto; a Session não reabre.
        with self.assertRaises(InvalidRequestError):
            tx.filas.salvar(fila)
        self.assertEqual(self.filas.obter_fila(self.fila.id).nome, "Confirmado")

    def test_falha_de_banco_reverte_emissao_contador_e_historico(self):
        registrar = TransacaoPostgres.registrar_transicao

        def duplicar(tx, transicao):
            registrar(tx, transicao)
            registrar(tx, transicao)  # Viola o identificador único do histórico.

        with patch.object(TransacaoPostgres, "registrar_transicao", duplicar):
            with self.assertRaises(IntegrityError):
                self.emitir()
        self.assertEqual(self.uow.historico, ())
        with self.uow.transacao(self.fila.id) as tx:
            self.assertEqual(tx.senhas.listar(self.fila.id), [])
        self.assertEqual(self.emitir().numero, "N001")

    def test_falha_na_virada_reverte_dia_contador_cancelamentos_e_historico(self):
        senha = self.emitir(TipoSenha.PRIORITARIA)
        self.chamar()
        historico = self.uow.historico
        registrar = TransacaoPostgres.registrar_transicao

        def falhar(tx, transicao):
            registrar(tx, transicao)
            raise RuntimeError("falha na virada")

        with patch.object(TransacaoPostgres, "registrar_transicao", falhar):
            with self.assertRaises(RuntimeError):
                self.senhas.consultar_fila(self.fila_id, contrato.AGORA + timedelta(days=1))
        fila = self.filas.obter_fila(self.fila.id)
        self.assertEqual(fila.dia_operacional, self.fila.dia_operacional)
        self.assertEqual(fila.chamadas_prioritarias_consecutivas, 1)
        self.assertEqual(self.buscar(senha.id).estado, EstadoSenha.CHAMADA)
        self.assertEqual(self.uow.historico, historico)

    def test_bloqueio_de_uma_fila_nao_impede_outra(self):
        outra = self.filas.criar_fila("Outra", quando=contrato.AGORA)
        iniciou = Event()

        def consultar(fila_id):
            iniciou.set()
            return self.filas.obter_fila(fila_id)

        with ThreadPoolExecutor(max_workers=2) as pool:
            with self.uow.transacao(self.fila.id):
                bloqueada = pool.submit(consultar, self.fila.id)
                self.assertTrue(iniciou.wait(5))
                livre = pool.submit(consultar, outra.id)
                self.assertEqual(livre.result(timeout=5).id, outra.id)
                self.assertFalse(bloqueada.done())
            self.assertEqual(bloqueada.result(timeout=5).id, self.fila.id)

    def test_chamadas_em_pools_independentes(self):
        for _ in range(12):
            self.emitir(TipoSenha.PRIORITARIA)
        # Pools distintos representam instâncias independentes da API.
        engines = [criar_engine_postgres(self.url) for _ in range(2)]
        try:
            def chamar(i):
                uow = UnidadeDeTrabalhoPostgres(engines[i % 2])
                return GerenciadorDeSenhas(uow).chamar_proxima_senha(
                    fila_id=self.fila_id, atendente_id=f"a{i}", guiche_id=f"g{i}",
                    chamada_em=contrato.AGORA,
                )

            with ThreadPoolExecutor(max_workers=16) as pool:
                chamadas = [s for s in pool.map(chamar, range(16)) if s is not None]
        finally:
            for engine in engines:
                engine.dispose()
        self.assertEqual(len(chamadas), 12)
        self.assertEqual(len({s.id for s in chamadas}), 12)
        self.assertEqual(len(self.uow.eventos), 12)
        self.assertEqual(self.filas.obter_fila(self.fila.id).chamadas_prioritarias_consecutivas, 12)

    def test_migracoes_reproduziveis_e_coerentes_com_modelos(self):
        self.migrar("base", reverter=True)
        self.migrar("head")
        self.migrar("head")  # Reexecução não altera o esquema.
        cfg = Config(str(RAIZ / "alembic.ini"))
        with self.engine.begin() as conn:
            cfg.attributes["connection"] = conn
            command.check(cfg)

    def test_migracao_incremental_preserva_senhas_historico_e_outbox(self):
        senha = self.emitir(TipoSenha.PRIORITARIA)
        self.chamar()
        historico, eventos = self.uow.historico, self.uow.eventos
        self.migrar("0001", reverter=True)
        self.migrar("head")
        self.assertEqual(self.buscar(senha.id).estado, EstadoSenha.CHAMADA)
        self.assertEqual((self.uow.historico, self.uow.eventos), (historico, eventos))
        self.assertEqual(ProcessadorOutbox(self.uow, FakeNotificador(self.uow)).processar().sucessos, 1)


@unittest.skipUnless(TEST_DATABASE_URL, "Defina TEST_DATABASE_URL para testar PostgreSQL real.")
class ReinicioApiPostgresTest(BancoPostgresMixin, unittest.TestCase):
    def setUp(self):
        self.limpar()

    def iniciar_api(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            porta = sock.getsockname()[1]
        env = dict(os.environ, PERSISTENCIA="postgres", DATABASE_URL=self.url.render_as_string(hide_password=False))
        log = tempfile.TemporaryFile(mode="w+")
        self.addCleanup(log.close)
        processo = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "gestao_filas.api:app", "--host", "127.0.0.1",
             "--port", str(porta), "--log-level", "warning"],
            cwd=RAIZ, env=env, stdout=log, stderr=log,
        )

        def parar():
            if processo.poll() is None:
                processo.terminate()
                try:
                    processo.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    processo.kill()
                    processo.wait(timeout=5)

        self.addCleanup(parar)
        base = f"http://127.0.0.1:{porta}"
        limite = time.monotonic() + 15
        while time.monotonic() < limite and processo.poll() is None:
            try:
                with urlopen(base + "/health", timeout=1):
                    return base, parar
            except (URLError, TimeoutError):
                time.sleep(0.05)
        log.seek(0)
        self.fail(f"API não iniciou: {log.read()}")

    def requisitar(self, base, metodo, caminho, dados=None):
        corpo = json.dumps(dados).encode() if dados is not None else None
        req = Request(base + caminho, method=metodo, data=corpo, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=10) as resp:
            return resp.status, json.load(resp)

    def test_dados_historico_outbox_e_contadores_sobrevivem_ao_reinicio_do_processo(self):
        base, parar = self.iniciar_api()
        status, fila = self.requisitar(base, "POST", "/filas", {"nome": "Reinício"})
        self.assertEqual(status, 201)
        caminho = f'/filas/{fila["id"]}'
        _, senha = self.requisitar(base, "POST", caminho + "/senhas", {"usuario_id": "u", "tipo": "prioritaria"})
        _, chamada = self.requisitar(base, "POST", caminho + "/senhas/chamada", {"atendente_id": "a", "guiche_id": "g"})
        self.assertEqual(chamada["id"], senha["id"])
        uow = UnidadeDeTrabalhoPostgres(self.engine)
        historico, eventos = uow.historico, uow.eventos
        parar()

        base, _ = self.iniciar_api()
        _, fila = self.requisitar(base, "GET", caminho)
        self.assertEqual(fila["chamadas_prioritarias_consecutivas"], 1)
        _, senhas = self.requisitar(base, "GET", caminho + "/senhas")
        self.assertEqual([(s["id"], s["estado"]) for s in senhas], [(senha["id"], "chamada")])
        self.assertEqual((uow.historico, uow.eventos), (historico, eventos))
        _, nova = self.requisitar(base, "POST", caminho + "/senhas", {"usuario_id": "u", "tipo": "prioritaria"})
        self.assertEqual(nova["numero"], "P002")
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text("SELECT tentativas, processado_em FROM outbox")).one(), (0, None))

    def test_atendimento_historico_e_notificacoes_persistem_apos_reinicio(self):
        base, parar = self.iniciar_api()
        _, fila = self.requisitar(base, "POST", "/filas", {"nome": "Fluxo persistido"})
        caminho = f'/filas/{fila["id"]}'
        _, senha = self.requisitar(base, "POST", caminho + "/senhas", {"usuario_id": "u"})
        self.requisitar(base, "POST", caminho + "/senhas/chamada", {"atendente_id": "a", "guiche_id": "g"})
        _, falha = self.requisitar(base, "POST", "/notificacoes/processamento", {"simular_falha": True})
        self.assertEqual(falha["falhas"], 1)
        _, sucesso = self.requisitar(base, "POST", "/notificacoes/processamento", {})
        self.assertEqual(sucesso["sucessos"], 1)
        senha_path = f'/senhas/{senha["id"]}'
        self.requisitar(base, "POST", senha_path + "/atendimento/inicio")
        self.requisitar(base, "POST", senha_path + "/atendimento/finalizacao")
        _, cancelada = self.requisitar(base, "POST", caminho + "/senhas", {"usuario_id": "u"})
        self.requisitar(base, "POST", caminho + "/encerramento")
        _, eventos = self.requisitar(base, "GET", "/notificacoes")
        self.assertEqual(eventos["itens"][0]["tentativas"], 2)
        tentativas_path = f'/notificacoes/{eventos["itens"][0]["evento"]["id"]}/tentativas'
        caminhos = [senha_path, f'/senhas/{cancelada["id"]}', caminho + "/historico",
                    "/notificacoes", "/notificacoes/simuladas", tentativas_path]
        antes = [self.requisitar(base, "GET", p)[1] for p in caminhos]
        self.assertEqual(antes[0]["estado"], "finalizada")
        self.assertEqual(antes[1]["estado"], "cancelada")
        self.assertEqual(len(antes[4]["itens"]), 1)
        parar()

        base, _ = self.iniciar_api()
        depois = [self.requisitar(base, "GET", p)[1] for p in caminhos]
        self.assertEqual(depois, antes)
        _, resultado = self.requisitar(base, "POST", "/notificacoes/processamento", {})
        self.assertEqual(resultado["processadas"], 0)


@unittest.skipUnless(TEST_DATABASE_URL, "Defina TEST_DATABASE_URL para testar PostgreSQL real.")
class FluxoCompletoPostgresTest(BancoPostgresMixin, fluxo.FluxoCompletoTest):
    def criar_uow(self):
        self.limpar()
        return UnidadeDeTrabalhoPostgres(self.engine)
