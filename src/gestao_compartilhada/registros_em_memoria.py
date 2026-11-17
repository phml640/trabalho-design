"""Histórico, outbox e notificações dentro do snapshot transacional de teste."""

from copy import deepcopy


def _filtrar(itens, fila_id, senha_id):
    return [i for i in itens if (fila_id is None or i.fila_id == fila_id)
            and (senha_id is None or i.senha_id == senha_id)]


class HistoricoEmMemoria:
    def __init__(self, estado):
        self._estado = estado

    def listar(self, fila_id, limite, offset, senha_id=None, estado=None):
        itens = _filtrar(self._estado.historico, fila_id, senha_id)
        if estado is not None:
            itens = [i for i in itens if i.estado == estado]
        return deepcopy(itens[offset:offset + limite])


class OutboxEmMemoria:
    def __init__(self, estado):
        self._estado = estado

    def buscar(self, evento_id):
        return deepcopy(self._estado.outbox.get(evento_id))

    def salvar(self, mensagem):
        self._estado.outbox[mensagem.evento.id] = deepcopy(mensagem)

    def listar(self, limite, offset, fila_id=None, senha_id=None):
        itens = [m for m in self._estado.outbox.values() if _filtrar([m.evento], fila_id, senha_id)]
        return deepcopy(itens[offset:offset + limite])

    def listar_pendentes(self, quando, limite):
        return deepcopy([m for m in self._estado.outbox.values()
                         if m.processado_em is None and (m.reservado_ate is None or m.reservado_ate <= quando)][:limite])

    def salvar_tentativa(self, tentativa):
        self._estado.tentativas[(tentativa.evento_id, tentativa.numero)] = deepcopy(tentativa)

    def buscar_tentativa(self, evento_id, numero):
        return deepcopy(self._estado.tentativas.get((evento_id, numero)))

    def listar_tentativas(self, evento_id, limite, offset):
        itens = sorted((t for t in self._estado.tentativas.values() if t.evento_id == evento_id),
                       key=lambda t: t.numero)
        return deepcopy(itens[offset:offset + limite])


class NotificacoesEmMemoria:
    def __init__(self, estado):
        self._estado = estado

    def registrar(self, notificacao):
        self._estado.notificacoes.setdefault(notificacao.evento_id, deepcopy(notificacao))

    def listar(self, limite, offset, fila_id=None, senha_id=None):
        itens = sorted(_filtrar(self._estado.notificacoes.values(), fila_id, senha_id),
                       key=lambda n: (n.criada_em, str(n.evento_id)))
        return deepcopy(itens[offset:offset + limite])
