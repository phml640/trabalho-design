import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from './api';
import {
  Badge,
  Empty,
  Feedback,
  Icon,
  Kind,
  Layout,
  Sync,
  formatTime,
  ticketMessage,
} from './components';
import { useAction, usePolling } from './hooks';
import type { TipoSenha } from './types';

const STORAGE_KEY = 'em-fila:senha-id';
function savedId() {
  try {
    return localStorage.getItem(STORAGE_KEY) || '';
  } catch {
    return '';
  }
}
function saveId(value: string) {
  try {
    if (value) localStorage.setItem(STORAGE_KEY, value);
    else localStorage.removeItem(STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}

export function UserPage() {
  const filas = usePolling('filas', api.filas);
  const [filaId, setFilaId] = useState('');
  const [tipo, setTipo] = useState<TipoSenha>('normal');
  const [senhaId, setSenhaId] = useState(savedId);
  const action = useAction();
  const ticketRef = useRef<HTMLElement>(null);
  const requestRef = useRef<HTMLElement>(null);
  const senha = usePolling(
    `senha:${senhaId}`,
    useCallback((signal) => api.senha(senhaId, signal), [senhaId]),
    !!senhaId,
  );
  const senhas = usePolling(
    `fila:${filaId}`,
    useCallback((signal) => api.senhas(filaId, signal), [filaId]),
    !!filaId,
  );
  const currentTicketId = senha.data?.id;
  useEffect(() => {
    if (currentTicketId && window.matchMedia('(max-width: 660px)').matches)
      ticketRef.current?.scrollIntoView({ block: 'start' });
  }, [currentTicketId]);
  const restauradaFilaId = senha.data?.fila_id;
  useEffect(() => {
    if (restauradaFilaId) setFilaId(restauradaFilaId);
  }, [restauradaFilaId]);
  useEffect(() => {
    if (!filaId && !senhaId && filas.data?.length)
      setFilaId((filas.data.find((f) => f.estado === 'aberta') || filas.data[0]).id);
  }, [filaId, senhaId, filas.data]);
  const fila = filas.data?.find((f) => f.id === filaId);
  const error = filas.error || senha.error || senhas.error;
  const missing = senha.error instanceof ApiError && [404, 422].includes(senha.error.status);
  const final = senha.data?.estado === 'finalizada' || senha.data?.estado === 'cancelada';
  const forget = () => {
    saveId('');
    setSenhaId('');
    action.setFeedback(undefined);
    requestRef.current?.scrollIntoView({ block: 'start' });
  };

  async function emitir() {
    await action.run(async () => {
      const emitida = await api.emitir(filaId, tipo);
      setSenhaId(emitida.id);
      const remembered = saveId(emitida.id);
      action.setFeedback({
        kind: 'success',
        text: remembered
          ? 'Senha emitida! Acompanhe seu atendimento nesta página.'
          : 'Senha emitida! Mantenha esta página aberta: o armazenamento deste navegador está indisponível.',
      });
      senhas.refresh();
    });
  }

  return (
    <Layout view="usuario">
      <div className="page-shell user-shell">
        <div className="page-heading">
          <div>
            <p className="eyebrow">SEU ATENDIMENTO</p>
            <h1>Sua vez, sem complicação.</h1>
            <p>Escolha uma fila, retire sua senha e acompanhe por aqui.</p>
          </div>
          <Sync
            updatedAt={senha.data ? senha.updatedAt : filas.updatedAt}
            loading={filas.loading || senha.loading}
            refresh={() => {
              filas.refresh();
              senhas.refresh();
              senha.refresh();
            }}
            error={error}
          />
        </div>
        {error && (
          <Feedback
            kind="error"
            text={
              missing
                ? 'A senha salva não está disponível nesta API. Remova o identificador deste navegador para solicitar outra.'
                : error.message
            }
          />
        )}
        {action.feedback && (
          <Feedback {...action.feedback} dismiss={() => action.setFeedback(undefined)} />
        )}
        <div className="user-grid">
          <section ref={requestRef} className="panel request-panel" aria-labelledby="emitir-title">
            <div className="section-heading">
              <span className="section-icon">
                <Icon name="ticket" />
              </span>
              <div>
                <h2 id="emitir-title">Retirar uma senha</h2>
                <p>Seu atendimento começa aqui.</p>
              </div>
            </div>
            <div className="form-step">
              <span>01</span>
              <h3>Escolha a fila</h3>
            </div>
            <div className="queue-choices">
              {!filas.data && !filas.error && <p className="muted">Carregando filas…</p>}
              {filas.data?.length === 0 && (
                <Empty title="Nenhuma fila disponível">
                  Aguarde a abertura de uma fila pelo atendente.
                </Empty>
              )}
              {filas.data?.map((f) => (
                <button
                  key={f.id}
                  className={`queue-choice ${filaId === f.id ? 'is-selected' : ''}`}
                  onClick={() => setFilaId(f.id)}
                  disabled={action.busy}
                  aria-pressed={filaId === f.id}
                >
                  <span className="radio-dot" />
                  <span className="queue-choice-text">
                    <strong>{f.nome}</strong>
                    <small>
                      {f.descricao ||
                        (f.estado === 'aberta'
                          ? 'Disponível para atendimento'
                          : 'Emissão indisponível')}
                    </small>
                  </span>
                  <Badge value={f.estado} />
                </button>
              ))}
            </div>
            <div className="form-step">
              <span>02</span>
              <h3>Selecione o tipo de atendimento</h3>
            </div>
            <fieldset className="type-selector" disabled={action.busy || !!senhaId}>
              <legend className="sr-only">Tipo de atendimento</legend>
              <label className={tipo === 'normal' ? 'is-selected' : ''}>
                <input
                  type="radio"
                  name="tipo"
                  value="normal"
                  checked={tipo === 'normal'}
                  onChange={() => setTipo('normal')}
                />
                <Icon name="users" />
                <span>Normal</span>
              </label>
              <label className={tipo === 'prioritaria' ? 'is-selected' : ''}>
                <input
                  type="radio"
                  name="tipo"
                  value="prioritaria"
                  checked={tipo === 'prioritaria'}
                  onChange={() => setTipo('prioritaria')}
                />
                <Icon name="star" />
                <span>Prioritário</span>
              </label>
            </fieldset>
            <p className="field-help">
              Classificação demonstrativa. A elegibilidade para prioridade não é verificada.
            </p>
            <button
              className="button button-primary button-full"
              onClick={() => void emitir()}
              disabled={action.busy || !fila || fila.estado !== 'aberta' || !!senhaId}
            >
              {action.busy ? 'Emitindo senha…' : 'Emitir minha senha'}
              <Icon name="arrow" size={18} />
            </button>
            <p className="request-note">
              <Icon name="info" size={15} />
              {senhaId
                ? 'Sua senha já está registrada. Acompanhe no cartão ao lado.'
                : fila?.estado === 'encerrada'
                  ? 'Esta fila está encerrada. Escolha outra fila disponível.'
                  : 'Não é necessário informar dados pessoais para a demonstração.'}
            </p>
          </section>
          <div className="ticket-column">
            <section
              ref={ticketRef}
              className={`ticket-card ${senha.data ? `ticket-${senha.data.estado}` : ''}`}
              aria-labelledby="sua-senha"
            >
              <div className="ticket-top">
                <span>
                  <Icon name="ticket" size={18} />
                  SEU COMPROVANTE DE ATENDIMENTO
                </span>
                <span className="ticket-live">
                  <span />
                  {error ? 'Sem conexão' : 'Ao vivo'}
                </span>
              </div>
              {senha.data ? (
                <>
                  <div className="ticket-main">
                    <p id="sua-senha" className="ticket-label">
                      Sua senha
                    </p>
                    <div className="ticket-number" data-testid="user-ticket-number">
                      {senha.data.numero}
                    </div>
                    <div className="ticket-tags">
                      <Kind value={senha.data.tipo} />
                      <span className="ticket-fila">
                        {filas.data?.find((f) => f.id === senha.data?.fila_id)?.nome ||
                          'Fila de atendimento'}
                      </span>
                    </div>
                  </div>
                  <div className="ticket-divider" />
                  <div className="ticket-bottom">
                    <Badge value={senha.data.estado} />
                    <p className="ticket-message" role="status">
                      {ticketMessage(
                        senha.data.estado,
                        senha.data.guiche_id,
                        senha.data.motivo_cancelamento,
                      )}
                    </p>
                    {senha.data.guiche_id && (
                      <div className="guiche-label">
                        <Icon name="grid" size={17} />
                        Guichê <strong>{senha.data.guiche_id}</strong>
                      </div>
                    )}
                    <small>
                      Emitida em {formatTime(senha.data.emitida_em)} ·{' '}
                      {senha.data.canal === 'totem' ? 'Totem' : 'Online'}
                    </small>
                    {final && (
                      <button className="button button-ghost button-full" onClick={forget}>
                        Solicitar outra senha
                        <Icon name="plus" size={17} />
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <div className="ticket-placeholder">
                  <span className="ticket-placeholder-icon">
                    <Icon name="ticket" size={46} />
                  </span>
                  <h2 id="sua-senha">Sua senha aparece aqui.</h2>
                  <p>
                    {missing
                      ? 'O identificador salvo não foi encontrado.'
                      : senhaId
                        ? 'Recuperando seu atendimento…'
                        : 'Retire uma senha e acompanhe cada etapa do atendimento, sem atualizar a página.'}
                  </p>
                </div>
              )}
              {missing && (
                <div className="ticket-bottom">
                  <button className="button button-ghost button-full" onClick={forget}>
                    Remover identificador salvo
                  </button>
                  <p className="field-help">
                    Isso apenas remove o vínculo local; não cancela nenhuma senha no servidor.
                  </p>
                </div>
              )}
            </section>
            <section className="panel queue-summary">
              <div className="inline-heading">
                <h2>
                  <Icon name="users" size={19} />
                  Situação da fila
                </h2>
                {fila && <Badge value={fila.estado} />}
              </div>
              <p className="muted">{fila?.nome || 'Selecione uma fila para acompanhar.'}</p>
              <div className="queue-stat-grid">
                {[
                  ['aguardando', 'Aguardando'],
                  ['chamada', 'Chamadas'],
                  ['em_atendimento', 'Em atendimento'],
                ].map(([state, label]) => (
                  <div key={state}>
                    <strong>
                      {senhas.data ? senhas.data.filter((s) => s.estado === state).length : '—'}
                    </strong>
                    <span>{label}</span>
                  </div>
                ))}
              </div>
              <p className="field-help">
                <Icon name="clock" size={14} />
                Acompanhe as atualizações; não é necessário recarregar a página.
              </p>
            </section>
          </div>
        </div>
      </div>
    </Layout>
  );
}
