import { useCallback, useState } from 'react';
import { api, numerosDasSenhas } from './api';
import { Badge, Empty, Feedback, Icon, Pagination, formatTime, labels } from './components';
import { useAction, usePolling } from './hooks';
import type { EstadoSenha } from './types';

const motivoLabel = (motivo: string | null) =>
  motivo === 'encerramento_diario'
    ? 'Encerramento diário'
    : motivo === 'encerramento_administrativo'
      ? 'Encerramento da fila'
      : motivo || '—';

export function HistoryPanel({ filaId, revision }: { filaId: string; revision: number }) {
  const [offset, setOffset] = useState(0);
  const [estado, setEstado] = useState<EstadoSenha | ''>('');
  const load = useCallback(
    async (signal: AbortSignal) => {
      const page = await api.historico(filaId, offset, estado || undefined, signal);
      return {
        page,
        numeros: await numerosDasSenhas(
          page.itens.map((t) => t.senha_id),
          signal,
        ),
      };
    },
    [filaId, offset, estado],
  );
  const resource = usePolling(`historico:${filaId}:${offset}:${estado}:${revision}`, load);
  return (
    <section className="panel data-panel" aria-labelledby="history-title">
      <div className="panel-toolbar">
        <div>
          <h2 id="history-title">Histórico da fila</h2>
          <p>Todas as etapas, inclusive atendimentos concluídos e cancelamentos.</p>
        </div>
        <label className="filter-label">
          Mostrar
          <select
            value={estado}
            onChange={(event) => {
              setEstado(event.target.value as EstadoSenha | '');
              setOffset(0);
            }}
            aria-label="Filtrar histórico por estado"
          >
            <option value="">Todas as transições</option>
            {Object.entries(labels)
              .filter(([key]) =>
                ['aguardando', 'chamada', 'em_atendimento', 'finalizada', 'cancelada'].includes(
                  key,
                ),
              )
              .map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
          </select>
        </label>
      </div>
      {resource.error && <Feedback kind="error" text={resource.error.message} />}
      {!resource.data && !resource.error ? (
        <p className="loading-text">Consultando histórico…</p>
      ) : resource.data?.page.itens.length === 0 ? (
        <Empty title="Nenhuma transição encontrada" icon="history">
          Os registros aparecerão aqui conforme o atendimento acontecer.
        </Empty>
      ) : (
        resource.data && (
          <div className="table-wrap">
            <table>
              <caption className="sr-only">Histórico de transições de senha</caption>
              <thead>
                <tr>
                  <th scope="col">Senha</th>
                  <th scope="col">Transição</th>
                  <th scope="col">Quando</th>
                  <th scope="col">Atendente / guichê</th>
                  <th scope="col">Motivo</th>
                </tr>
              </thead>
              <tbody>
                {resource.data.page.itens.map((t) => (
                  <tr key={t.id}>
                    <td>
                      <strong className="table-ticket" title={t.senha_id}>
                        {resource.data!.numeros[t.senha_id]}
                      </strong>
                    </td>
                    <td>
                      <div className="transition">
                        {t.estado_anterior ? (
                          <>
                            <span>{labels[t.estado_anterior]}</span>
                            <Icon name="arrow" size={13} />
                          </>
                        ) : (
                          <span>Emissão</span>
                        )}
                        <Badge value={t.estado} />
                      </div>
                    </td>
                    <td className="nowrap">{formatTime(t.quando)}</td>
                    <td>
                      <span>{t.atendente_id || '—'}</span>
                      <small>{t.guiche_id ? `Guichê ${t.guiche_id}` : '—'}</small>
                    </td>
                    <td className="muted">{motivoLabel(t.motivo)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
      <Pagination
        page={resource.data?.page}
        offset={offset}
        change={setOffset}
        busy={resource.loading}
      />
    </section>
  );
}

export function NotificationsPanel({ filaId }: { filaId: string }) {
  const [offset, setOffset] = useState(0);
  const [messageOffset, setMessageOffset] = useState(0);
  const [eventoId, setEventoId] = useState('');
  const [attemptOffset, setAttemptOffset] = useState(0);
  const action = useAction();
  const load = useCallback(
    async (signal: AbortSignal) => {
      const [events, messages] = await Promise.all([
        api.notificacoes(filaId, offset, signal),
        api.simuladas(filaId, messageOffset, signal),
      ]);
      return {
        events,
        messages,
        numeros: await numerosDasSenhas(
          events.itens.map((e) => e.evento.senha_id),
          signal,
        ),
      };
    },
    [filaId, offset, messageOffset],
  );
  const resource = usePolling(`notificacoes:${filaId}:${offset}:${messageOffset}`, load);
  const attempts = usePolling(
    `tentativas:${eventoId}:${attemptOffset}`,
    useCallback(
      (signal) => api.tentativas(eventoId, attemptOffset, signal),
      [eventoId, attemptOffset],
    ),
    !!eventoId,
  );
  function processar(falhar: boolean) {
    void action.run(async () => {
      const result = await api.processar(falhar);
      resource.refresh();
      attempts.refresh();
      action.setFeedback({
        kind: result.falhas ? 'error' : 'success',
        text: result.processadas
          ? `${result.processadas} tentativa(s): ${result.sucessos} com sucesso e ${result.falhas} com falha. ${result.falhas ? 'As chamadas foram preservadas; você pode tentar novamente.' : 'Consulte as mensagens simuladas abaixo.'}`
          : 'Nenhuma pendência disponível para processar neste momento.',
      });
    });
  }
  return (
    <div className="notifications-stack">
      <section className="panel data-panel" aria-labelledby="notification-title">
        <div className="panel-toolbar">
          <div>
            <h2 id="notification-title">Notificações de chamada</h2>
            <p>Acompanhe a solicitação e o resultado de cada envio.</p>
          </div>
          <span className="subtle-tag">
            <Icon name="bell" size={15} />
            Envio simulado
          </span>
        </div>
        <div className="notification-actions">
          <div>
            <button
              className="button button-primary button-small"
              onClick={() => processar(false)}
              disabled={action.busy}
            >
              <Icon name="play" size={15} />
              {action.busy ? 'Processando…' : 'Processar notificações'}
            </button>
            <button
              className="button button-ghost button-small"
              onClick={() => processar(true)}
              disabled={action.busy}
            >
              Simular falha no envio
            </button>
          </div>
          <p>Processa até 20 pendências de todas as filas. Nenhuma mensagem real é enviada.</p>
        </div>
        {action.feedback && (
          <Feedback {...action.feedback} dismiss={() => action.setFeedback(undefined)} />
        )}
        {resource.error && <Feedback kind="error" text={resource.error.message} />}
        {!resource.data && !resource.error ? (
          <p className="loading-text">Consultando notificações…</p>
        ) : resource.data?.events.itens.length === 0 ? (
          <Empty title="Nenhuma notificação solicitada" icon="bell">
            Chame uma senha para registrar uma solicitação de notificação.
          </Empty>
        ) : (
          resource.data && (
            <div className="table-wrap">
              <table>
                <caption className="sr-only">Solicitações de notificação</caption>
                <thead>
                  <tr>
                    <th scope="col">Senha</th>
                    <th scope="col">Situação</th>
                    <th scope="col">Tentativas</th>
                    <th scope="col">Último resultado</th>
                    <th scope="col">
                      <span className="sr-only">Detalhes</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {resource.data.events.itens.map((n) => (
                    <tr key={n.evento.id}>
                      <td>
                        <strong className="table-ticket">
                          {resource.data!.numeros[n.evento.senha_id]}
                        </strong>
                        <small>{formatTime(n.evento.chamada_em)}</small>
                      </td>
                      <td>
                        <Badge value={n.status} />
                      </td>
                      <td>{n.tentativas}</td>
                      <td>
                        <span className={n.ultimo_erro ? 'error-text' : 'muted'}>
                          {n.ultimo_erro ||
                            (n.processado_em
                              ? `Processada em ${formatTime(n.processado_em)}`
                              : 'Aguardando processamento')}
                        </span>
                      </td>
                      <td>
                        <button
                          className="text-button"
                          onClick={() => {
                            setEventoId(n.evento.id);
                            setAttemptOffset(0);
                          }}
                          aria-label={`Ver tentativas da senha ${resource.data!.numeros[n.evento.senha_id]}`}
                        >
                          Ver tentativas
                          <Icon name="chevron" size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
        <Pagination
          page={resource.data?.events}
          offset={offset}
          change={setOffset}
          busy={resource.loading}
        />
      </section>
      {eventoId && (
        <section className="panel attempt-panel" aria-labelledby="attempt-title">
          <div className="inline-heading">
            <h2 id="attempt-title">Tentativas de envio</h2>
            <button
              className="icon-button"
              onClick={() => setEventoId('')}
              aria-label="Fechar tentativas"
            >
              <Icon name="close" />
            </button>
          </div>
          {attempts.error && <Feedback kind="error" text={attempts.error.message} />}
          {attempts.data?.itens.map((t) => (
            <div className="attempt-row" key={t.id}>
              <strong>Tentativa {t.numero}</strong>
              <Badge
                value={!t.finalizada_em ? 'em_processamento' : t.erro ? 'falha' : 'processada'}
              />
              <span>{formatTime(t.iniciada_em)}</span>
              <small>
                {t.erro || (t.finalizada_em ? 'Envio simulado concluído' : 'Aguardando conclusão')}
              </small>
            </div>
          ))}
          {attempts.data?.itens.length === 0 && (
            <p className="muted">Este evento ainda não teve tentativas.</p>
          )}
          <Pagination
            page={attempts.data}
            offset={attemptOffset}
            change={setAttemptOffset}
            busy={attempts.loading}
          />
        </section>
      )}
      <section className="panel data-panel" aria-labelledby="simulated-title">
        <div className="panel-toolbar">
          <div>
            <h2 id="simulated-title">Mensagens simuladas</h2>
            <p>O que foi registrado pelo notificador de demonstração.</p>
          </div>
          <Icon name="check" />
        </div>
        {resource.data?.messages.itens.length === 0 ? (
          <Empty title="Nenhuma mensagem registrada" icon="bell">
            Processe uma notificação com sucesso para visualizar a mensagem.
          </Empty>
        ) : (
          <div className="simulated-messages">
            {resource.data?.messages.itens.map((n) => (
              <article key={n.evento_id} className="simulated-message">
                <span className="message-icon">
                  <Icon name="bell" size={19} />
                </span>
                <div>
                  <strong>{n.mensagem}</strong>
                  <small>{formatTime(n.criada_em)} · Entrega simulada</small>
                </div>
                <span className="message-check">
                  <Icon name="check" size={18} />
                </span>
              </article>
            ))}
          </div>
        )}
        <Pagination
          page={resource.data?.messages}
          offset={messageOffset}
          change={setMessageOffset}
          busy={resource.loading}
        />
      </section>
    </div>
  );
}
