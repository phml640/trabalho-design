"""Aceitação HTTP e contrato do processador, reutilizados com PostgreSQL real."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
import unittest
from uuid import uuid4

from gestao_compartilhada.infrastructure import UnidadeDeTrabalhoEmMemoria
from gestao_compartilhada.notificacoes import ProcessadorOutbox
from gestao_compartilhada.notificador import FakeNotificador
from gestao_filas.api import criar_app
from gestao_senhas.application import GerenciadorDeSenhas

from test_integracao import AGORA, requisitar


class FluxoCompletoTest(unittest.TestCase):
    def criar_uow(self):
        return UnidadeDeTrabalhoEmMemoria()

    def setUp(self):
        self.uow = self.criar_uow()
        self.app = criar_app(self.uow)

    def req(self, metodo, caminho, dados=None, status=200):
        recebido, corpo = asyncio.run(requisitar(self.app, metodo, caminho, dados))
        self.assertEqual(recebido, status, corpo)
        return corpo

    def criar(self, nome="Caixa"):
        return self.req("POST", "/filas", {"nome": nome}, status=201)

    def emitir(self, fila, tipo="normal"):
        return self.req("POST", f'/filas/{fila["id"]}/senhas', {
            "usuario_id": "identificacao-privada", "tipo": tipo, "canal": "totem",
        }, status=201)

    def chamar(self, fila):
        return self.req("POST", f'/filas/{fila["id"]}/senhas/chamada', {
            "atendente_id": "atendente", "guiche_id": "g1",
        })

    def test_fluxo_prioridade_atendimento_historico_e_notificacao(self):
        fila = self.criar()
        normal = self.emitir(fila)
        p1, p2 = self.emitir(fila, "prioritaria"), self.emitir(fila, "prioritaria")
        senha_path = f'/senhas/{p1["id"]}'
        self.req("POST", senha_path + "/atendimento/inicio", status=409)
        self.req("POST", senha_path + "/atendimento/finalizacao", status=409)
        self.assertEqual([self.chamar(fila)["id"] for _ in range(3)], [p1["id"], p2["id"], normal["id"]])
        self.req("POST", senha_path + "/atendimento/inicio")
        self.req("POST", senha_path + "/atendimento/inicio", status=409)
        finalizada = self.req("POST", senha_path + "/atendimento/finalizacao")
        self.assertEqual(finalizada["estado"], "finalizada")
        self.req("POST", senha_path + "/atendimento/finalizacao", status=409)
        publica = self.req("GET", senha_path)
        self.assertNotIn("usuario_id", publica)
        self.assertNotIn("atendente_id", publica)
        self.assertIsNotNone(publica["atendimento_finalizado_em"])
        self.assertNotIn("usuario_id", self.req("GET", f'/filas/{fila["id"]}/senhas')[0])

        caminho = f'/filas/{fila["id"]}/historico?senha_id={p1["id"]}'
        primeira = self.req("GET", caminho + "&limite=2")
        segunda = self.req("GET", caminho + "&limite=2&offset=2")
        self.assertTrue(primeira["tem_mais"])
        self.assertFalse(segunda["tem_mais"])
        itens = primeira["itens"] + segunda["itens"]
        self.assertEqual([t["estado"] for t in itens], ["aguardando", "chamada", "em_atendimento", "finalizada"])
        self.assertEqual([t["estado_anterior"] for t in itens], [None, "aguardando", "chamada", "em_atendimento"])
        self.assertEqual(itens[-1]["atendente_id"], "atendente")
        self.assertEqual(itens[-1]["guiche_id"], "g1")
        self.assertEqual([t["quando"] for t in itens], sorted(t["quando"] for t in itens))
        self.assertEqual(len(self.req("GET", caminho + "&estado=finalizada")["itens"]), 1)

        eventos = self.req("GET", "/notificacoes")["itens"]
        self.assertEqual(len(eventos), 3)
        self.assertTrue(all(e["status"] == "pendente" and e["tentativas"] == 0 for e in eventos))
        self.assertEqual(self.req("POST", "/notificacoes/processamento"), {"processadas": 3, "sucessos": 3, "falhas": 0})
        self.assertEqual(self.req("POST", "/notificacoes/processamento")["processadas"], 0)
        simuladas = self.req("GET", "/notificacoes/simuladas")["itens"]
        self.assertEqual(len(simuladas), 3)
        self.assertIn("guichê g1", simuladas[0]["mensagem"])
        self.assertNotIn("identificacao-privada", str(simuladas))
        self.assertTrue(all(e["status"] == "processada" for e in self.req("GET", "/notificacoes")["itens"]))
        tentativas = self.req("GET", f'/notificacoes/{eventos[0]["evento"]["id"]}/tentativas')["itens"]
        self.assertEqual(len(tentativas), 1)
        self.assertIsNone(tentativas[0]["erro"])
        self.assertIsNotNone(tentativas[0]["finalizada_em"])

    def test_falha_e_retentativa_nao_desfazem_chamada(self):
        fila = self.criar()
        senha = self.emitir(fila)
        self.chamar(fila)
        resultado = self.req("POST", "/notificacoes/processamento", {"simular_falha": True})
        self.assertEqual(resultado, {"processadas": 1, "sucessos": 0, "falhas": 1})
        self.assertEqual(self.req("GET", f'/senhas/{senha["id"]}')["estado"], "chamada")
        evento = self.req("GET", "/notificacoes")["itens"][0]
        self.assertEqual(evento["status"], "falha")
        self.assertEqual(evento["tentativas"], 1)
        self.assertIn("FalhaSimulada", evento["ultimo_erro"])
        self.assertEqual(self.req("GET", "/notificacoes/simuladas")["itens"], [])
        self.assertEqual(self.req("POST", "/notificacoes/processamento")["sucessos"], 1)
        atual = self.req("GET", "/notificacoes")["itens"][0]
        self.assertEqual(atual["tentativas"], 2)
        self.assertIsNone(atual["ultimo_erro"])
        tentativas = self.req("GET", f'/notificacoes/{evento["evento"]["id"]}/tentativas')["itens"]
        self.assertEqual([t["numero"] for t in tentativas], [1, 2])
        self.assertIn("FalhaSimulada", tentativas[0]["erro"])
        self.assertIsNone(tentativas[1]["erro"])

    def test_encerramento_historico_canceladas_e_reabertura(self):
        fila = self.criar()
        andamento = self.emitir(fila)
        self.chamar(fila)
        self.req("POST", f'/senhas/{andamento["id"]}/atendimento/inicio')
        chamada = self.emitir(fila)
        self.chamar(fila)
        aguardando = self.emitir(fila)
        caminho = f'/filas/{fila["id"]}'
        self.req("POST", caminho + "/encerramento")
        self.req("POST", caminho + "/senhas", {"usuario_id": "u"}, status=409)
        self.req("POST", caminho + "/senhas/chamada", {"atendente_id": "a", "guiche_id": "g"}, status=409)
        for senha in (chamada, aguardando):
            self.assertEqual(self.req("GET", f'/senhas/{senha["id"]}')["estado"], "cancelada")
            self.req("POST", f'/senhas/{senha["id"]}/atendimento/inicio', status=409)
        self.req("POST", f'/senhas/{andamento["id"]}/atendimento/finalizacao')
        canceladas = self.req("GET", caminho + "/historico?estado=cancelada")["itens"]
        self.assertEqual({t["senha_id"] for t in canceladas}, {chamada["id"], aguardando["id"]})
        self.assertTrue(all(t["motivo"] == "encerramento_administrativo" for t in canceladas))
        self.req("POST", caminho + "/reabertura")
        self.assertEqual(self.req("GET", caminho + "/senhas"), [])
        self.assertEqual(self.req("GET", "/filas")[0]["estado"], "aberta")

    def test_erros_http_filtros_e_paginacao(self):
        fila, outra = self.criar(), self.criar("Outra")
        senha = self.emitir(fila)
        self.chamar(fila)
        self.assertEqual(self.req("GET", f'/filas/{outra["id"]}/historico')["itens"], [])
        self.assertEqual(self.req("GET", f'/notificacoes?fila_id={outra["id"]}')["itens"], [])
        self.assertEqual(len(self.req("GET", f'/notificacoes?senha_id={senha["id"]}')["itens"]), 1)
        for caminho in (f'/senhas/{uuid4()}', f'/filas/{uuid4()}/historico', f'/notificacoes/{uuid4()}/tentativas'):
            self.req("GET", caminho, status=404)
        for caminho in ("/senhas/invalido", "/notificacoes?limite=0", "/notificacoes?limite=101",
                        "/notificacoes/simuladas?offset=-1", f'/filas/{fila["id"]}/historico?estado=invalido'):
            self.req("GET", caminho, status=422)
        self.req("POST", "/notificacoes/processamento", {"limite": 0}, status=422)
        self.req("POST", f'/senhas/{uuid4()}/atendimento/inicio', status=404)

    def test_notificador_substituivel_e_idempotencia_apos_envio_sem_confirmacao(self):
        fake = FakeNotificador(self.uow)

        class EnvioSemConfirmacao:
            chamadas = 0

            def notificar(self, evento):
                fake.notificar(evento)
                self.chamadas += 1
                if self.chamadas == 1:
                    raise TimeoutError("confirmação perdida")

        self.app = criar_app(self.uow, notificador=EnvioSemConfirmacao())
        fila = self.criar()
        self.emitir(fila)
        self.chamar(fila)
        self.assertEqual(self.req("POST", "/notificacoes/processamento")["falhas"], 1)
        primeira = self.req("GET", "/notificacoes/simuladas")["itens"]
        self.assertEqual(self.req("POST", "/notificacoes/processamento")["sucessos"], 1)
        self.assertEqual(self.req("GET", "/notificacoes/simuladas")["itens"], primeira)
        self.assertEqual(len(primeira), 1)

    def test_processadores_concorrentes_e_envio_sem_bloqueio_de_fila(self):
        fila = self.criar()
        senha = self.emitir(fila)
        self.chamar(fila)
        iniciou, liberar = Event(), Event()
        fake = FakeNotificador(self.uow)

        class NotificadorBloqueado:
            def notificar(self, evento):
                iniciou.set()
                if not liberar.wait(5):
                    raise TimeoutError("teste não liberou o envio")
                fake.notificar(evento)

        with ThreadPoolExecutor(max_workers=2) as pool:
            processamento = pool.submit(ProcessadorOutbox(self.uow, NotificadorBloqueado()).processar)
            try:
                self.assertTrue(iniciou.wait(5))
                inicio = pool.submit(GerenciadorDeSenhas(self.uow).iniciar_atendimento, senha["id"])
                self.assertEqual(inicio.result(timeout=3).estado, "em_atendimento")
                self.assertEqual(ProcessadorOutbox(self.uow, fake).processar().processadas, 0)
            finally:
                liberar.set()
            self.assertEqual(processamento.result(timeout=5).sucessos, 1)
        self.assertEqual(self.req("GET", "/notificacoes")["itens"][0]["tentativas"], 1)

    def test_reserva_expirada_pode_ser_retomada_apos_interrupcao(self):
        fila = self.criar()
        self.emitir(fila)
        self.chamar(fila)

        class ProcessoInterrompido:
            def notificar(self, evento):
                raise KeyboardInterrupt("queda do processo")

        with self.assertRaises(KeyboardInterrupt):
            ProcessadorOutbox(self.uow, ProcessoInterrompido(), relogio=lambda: AGORA).processar()
        fake = FakeNotificador(self.uow)
        self.assertEqual(ProcessadorOutbox(self.uow, fake, relogio=lambda: AGORA).processar().processadas, 0)
        resultado = ProcessadorOutbox(self.uow, fake, relogio=lambda: AGORA + timedelta(seconds=31)).processar()
        self.assertEqual(resultado.sucessos, 1)
        evento = self.req("GET", "/notificacoes")["itens"][0]
        tentativas = self.req("GET", f'/notificacoes/{evento["evento"]["id"]}/tentativas')["itens"]
        self.assertEqual([t["numero"] for t in tentativas], [1, 2])
        self.assertEqual(tentativas[0]["erro"], "reserva_expirada")
        self.assertIsNone(tentativas[1]["erro"])

    def test_consulta_individual_executa_virada_e_preserva_historico(self):
        from gestao_filas.application import GestaoDeFilas
        from gestao_senhas.domain import TipoSenha

        fila = GestaoDeFilas(self.uow).criar_fila("Ontem", quando=AGORA)
        senhas = GerenciadorDeSenhas(self.uow)
        senha = senhas.emitir_senha(fila_id=str(fila.id), usuario_id="u", tipo=TipoSenha.NORMAL,
                                   canal="totem", emitida_em=AGORA)
        atual = senhas.consultar_senha(str(senha.id), AGORA + timedelta(days=1))
        self.assertEqual(atual.estado, "cancelada")
        historico = self.req("GET", f'/filas/{fila.id}/historico')["itens"]
        self.assertEqual([t["estado"] for t in historico], ["aguardando", "cancelada"])
        self.assertEqual(historico[-1]["motivo"], "encerramento_diario")

    def test_openapi_descreve_respostas_publicas_e_erros(self):
        schema = self.app.openapi()
        propriedades = schema["components"]["schemas"]["SenhaResposta"]["properties"]
        self.assertNotIn("usuario_id", propriedades)
        self.assertNotIn("atendente_id", propriedades)
        inicio = schema["paths"]["/senhas/{senha_id}/atendimento/inicio"]["post"]
        self.assertTrue({"200", "404", "409", "422"}.issubset(inicio["responses"]))
        historico = schema["paths"]["/filas/{fila_id}/historico"]["get"]
        self.assertTrue({"limite", "offset", "senha_id", "estado"}.issubset({p["name"] for p in historico["parameters"]}))
