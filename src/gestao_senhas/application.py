"""Casos de uso transacionais do gerenciador de senhas."""

from datetime import datetime, timezone
from uuid import UUID

from gestao_compartilhada.application import UnidadeDeTrabalho
from gestao_compartilhada.domain import texto_obrigatorio, validar_instante
from gestao_compartilhada.operacoes import garantir_dia, obter_fila, registrar

from .domain import EstadoSenha, Senha, SenhaChamada, TipoSenha, selecionar_proxima


class GerenciadorDeSenhas:
    def __init__(self, unidade_de_trabalho: UnidadeDeTrabalho) -> None:
        self._uow = unidade_de_trabalho

    def emitir_senha(
        self, *, fila_id: str, usuario_id: str, tipo: TipoSenha, canal: str,
        emitida_em: datetime | None = None,
    ) -> Senha:
        fila_uuid = UUID(str(fila_id))
        agora = validar_instante(emitida_em or datetime.now(timezone.utc))
        tipo = TipoSenha(tipo)
        with self._uow.transacao(fila_uuid) as tx:
            fila = obter_fila(tx, fila_uuid)
            fila.exigir_aberta()
            garantir_dia(tx, fila, agora)
            senha = Senha(
                fila_id=str(fila_uuid),
                numero=tx.senhas.proximo_numero(fila_uuid, fila.dia_operacional, tipo),
                tipo=tipo, usuario_id=usuario_id, emitida_em=agora, canal=canal,
            )
            registrar(tx, senha, None, agora)
            return senha

    def consultar_fila(self, fila_id: str, quando: datetime | None = None) -> list[Senha]:
        fila_uuid = UUID(str(fila_id))
        agora = validar_instante(quando or datetime.now(timezone.utc))
        with self._uow.transacao(fila_uuid) as tx:
            fila = obter_fila(tx, fila_uuid)
            garantir_dia(tx, fila, agora)
            return [
                s for s in tx.senhas.listar(fila_uuid)
                if s.dia_operacional == fila.dia_operacional
                and s.estado not in (EstadoSenha.FINALIZADA, EstadoSenha.CANCELADA)
            ]

    def chamar_proxima_senha(
        self, *, fila_id: str, atendente_id: str, guiche_id: str,
        chamada_em: datetime | None = None,
    ) -> Senha | None:
        fila_uuid = UUID(str(fila_id))
        agora = validar_instante(chamada_em or datetime.now(timezone.utc))
        atendente_id = texto_obrigatorio(atendente_id, "Atendente")
        guiche_id = texto_obrigatorio(guiche_id, "Guichê")
        with self._uow.transacao(fila_uuid) as tx:
            fila = obter_fila(tx, fila_uuid)
            fila.exigir_aberta()
            garantir_dia(tx, fila, agora)
            senhas = [s for s in tx.senhas.listar(fila_uuid) if s.dia_operacional == fila.dia_operacional]
            senha = selecionar_proxima(senhas, fila.chamadas_prioritarias_consecutivas)
            if senha is None:
                return None
            senha.chamar(atendente_id=atendente_id, guiche_id=guiche_id, chamada_em=agora)
            if senha.tipo is TipoSenha.PRIORITARIA:
                fila.registrar_chamada_prioritaria()
            else:
                fila.registrar_chamada_normal()
            tx.filas.salvar(fila)
            registrar(tx, senha, EstadoSenha.AGUARDANDO, agora)
            tx.registrar_evento(SenhaChamada(senha_id=senha.id, fila_id=fila.id, chamada_em=agora))
            return senha

    def iniciar_atendimento(self, senha_id: str, quando: datetime | None = None) -> Senha:
        return self._transicionar_atendimento(senha_id, quando, iniciar=True)

    def consultar_senha(self, senha_id: str, quando: datetime | None = None) -> Senha:
        senha_uuid = UUID(str(senha_id))
        agora = validar_instante(quando or datetime.now(timezone.utc))
        fila_id = self._identificar_fila(senha_uuid)
        with self._uow.transacao(fila_id) as tx:
            fila = obter_fila(tx, fila_id)
            garantir_dia(tx, fila, agora)
            return tx.senhas.buscar(senha_uuid)

    def _identificar_fila(self, senha_id: UUID) -> UUID:
        with self._uow.transacao() as tx:
            senha = tx.senhas.buscar(senha_id)
            if senha is None:
                raise LookupError(f"Senha '{senha_id}' não encontrada.")
            return UUID(senha.fila_id)

    def finalizar_atendimento(self, senha_id: str, quando: datetime | None = None) -> Senha:
        return self._transicionar_atendimento(senha_id, quando, iniciar=False)

    def _transicionar_atendimento(
        self, senha_id: str, quando: datetime | None, *, iniciar: bool,
    ) -> Senha:
        senha_uuid = UUID(str(senha_id))
        agora = validar_instante(quando or datetime.now(timezone.utc))
        # A associação à fila é imutável. A senha é relida sob o bloqueio da fila.
        fila_id = self._identificar_fila(senha_uuid)
        with self._uow.transacao(fila_id) as tx:
            fila = obter_fila(tx, fila_id)
            senha = tx.senhas.buscar(senha_uuid)
            anterior = senha.estado
            if iniciar:
                fila.exigir_aberta()
                garantir_dia(tx, fila, agora)
                # A virada pode ter cancelado a senha carregada anteriormente.
                senha = tx.senhas.buscar(senha_uuid)
                anterior = senha.estado
                senha.iniciar_atendimento(agora)
            else:
                senha.finalizar_atendimento(agora)
            registrar(tx, senha, anterior, agora)
            return senha
