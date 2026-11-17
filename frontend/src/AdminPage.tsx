import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { api } from './api';
import { HistoryPanel, NotificationsPanel } from './AdminPanels';
import {
  Badge,
  ConfirmClose,
  Empty,
  Feedback,
  Icon,
  Kind,
  Layout,
  Sync,
  formatTime,
} from './components';
import { useAction, usePolling } from './hooks';

type Tab = 'fila' | 'historico' | 'notificacoes';
export function AdminPage() {
  const filas = usePolling('filas', api.filas);
  const [filaId, setFilaId] = useState('');
  const [focusedId, setFocusedId] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [showClose, setShowClose] = useState(false);
  const [nome, setNome] = useState('');
  const [descricao, setDescricao] = useState('');
  const [atendente, setAtendente] = useState('');
  const [guiche, setGuiche] = useState('');
  const [tab, setTab] = useState<Tab>('fila');
  const [revision, setRevision] = useState(0);
  const action = useAction();
  const senhas = usePolling(
    `fila:${filaId}`,
    useCallback((signal) => api.senhas(filaId, signal), [filaId]),
    !!filaId,
  );
  const automaticId =
    senhas.data?.find((s) => s.estado === 'chamada')?.id ||
    senhas.data?.find((s) => s.estado === 'em_atendimento')?.id ||
    '';
  const selectedId = focusedId || automaticId;
  const selected = usePolling(
    `selecionada:${selectedId}`,
    useCallback((signal) => api.senha(selectedId, signal), [selectedId]),
    !!selectedId,
  );
  useEffect(() => {
    if (!filaId && filas.data?.length) setFilaId(filas.data[0].id);
  }, [filaId, filas.data]);
  const fila = filas.data?.find((f) => f.id === filaId);
  const aberta = fila?.estado === 'aberta';
  const error = filas.error || senhas.error || selected.error;
  const refresh = () => {
    filas.refresh();
    senhas.refresh();
    selected.refresh();
    setRevision((value) => value + 1);
  };
  const selectQueue = (value: string) => {
    setFilaId(value);
    setFocusedId('');
    setShowClose(false);
    action.setFeedback(undefined);
  };

  function criar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void action.run(async () => {
      const criada = await api.criarFila(nome.trim(), descricao.trim());
      selectQueue(criada.id);
      setNome('');
      setDescricao('');
      setShowCreate(false);
      refresh();
    }, 'Fila criada. Ela já está disponível para emissão de senhas.');
  }
  function chamar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void action.run(async () => {
      const chamada = await api.chamar(filaId, atendente.trim(), guiche.trim());
      setFocusedId(chamada.id);
      refresh();
    }, 'Senha chamada. A solicitação de notificação foi registrada.');
  }
  function transicionar(iniciar: boolean) {
    void action.run(
      async () => {
        await (iniciar ? api.iniciar(selectedId) : api.finalizar(selectedId));
        refresh();
      },
      iniciar ? 'Atendimento iniciado.' : 'Atendimento finalizado e registrado no histórico.',
    );
  }

  return (
    <Layout view="admin">
      <div className="admin-layout">
        <aside className="queue-sidebar" aria-labelledby="queues-title">
          <div className="sidebar-label">
            <p className="eyebrow">ESPAÇO DO ATENDENTE</p>
            <h2 id="queues-title">Filas de atendimento</h2>
            <p>Selecione a fila que deseja gerenciar.</p>
          </div>
          <button
            className="button button-primary button-full"
            onClick={() => setShowCreate((value) => !value)}
            aria-expanded={showCreate}
            disabled={action.busy}
          >
            <Icon name={showCreate ? 'close' : 'plus'} size={18} />
            {showCreate ? 'Fechar formulário' : 'Nova fila'}
          </button>
          {showCreate && (
            <form className="create-form" onSubmit={criar}>
              <label>
                Nome da fila
                <input
                  value={nome}
                  onChange={(event) => setNome(event.target.value)}
                  maxLength={120}
                  required
                  placeholder="Ex.: Atendimento geral"
                />
              </label>
              <label>
                Descrição <span className="muted">(opcional)</span>
                <textarea
                  value={descricao}
                  onChange={(event) => setDescricao(event.target.value)}
                  maxLength={500}
                  rows={2}
                  placeholder="Como podemos ajudar?"
                />
              </label>
              <button
                className="button button-primary button-full button-small"
                disabled={action.busy || !nome.trim()}
              >
                {action.busy ? 'Salvando…' : 'Criar fila'}
              </button>
            </form>
          )}
          <div className="sidebar-queues">
            {!filas.data && !filas.error && <p className="muted">Carregando filas…</p>}
            {filas.data?.length === 0 && (
              <p className="sidebar-empty">Crie a primeira fila para começar a atender.</p>
            )}
            {filas.data?.map((f) => (
              <button
                key={f.id}
                className={`sidebar-queue ${filaId === f.id ? 'is-selected' : ''}`}
                onClick={() => selectQueue(f.id)}
                disabled={action.busy}
                aria-pressed={filaId === f.id}
              >
                <span className="sidebar-queue-icon">
                  <Icon name="ticket" size={20} />
                </span>
                <span>
                  <strong>{f.nome}</strong>
                  <Badge value={f.estado} />
                </span>
                <Icon name="chevron" size={16} />
              </button>
            ))}
          </div>
          <div className="sidebar-bottom">
            <Icon name="info" size={18} />
            <p>
              Ambiente de demonstração.
              <br />
              Esta visão não exige login.
            </p>
          </div>
        </aside>
        <div className="admin-main">
          <div className="page-heading">
            <div>
              <p className="eyebrow">PAINEL DE ATENDIMENTO</p>
              <h1>{fila?.nome || 'Vamos organizar a fila.'}</h1>
              <p>{fila?.descricao || 'Da primeira chamada ao atendimento concluído.'}</p>
            </div>
            <Sync
              updatedAt={senhas.updatedAt || filas.updatedAt}
              loading={filas.loading || senhas.loading}
              refresh={refresh}
              error={error}
            />
          </div>
          {error && <Feedback kind="error" text={error.message} />}
          {action.feedback && (
            <Feedback {...action.feedback} dismiss={() => action.setFeedback(undefined)} />
          )}
          {!fila ? (
            <section className="panel">
              <Empty
                title={
                  filas.data?.length === 0
                    ? 'Tudo pronto para a primeira fila.'
                    : 'Selecione uma fila para começar.'
                }
                icon="grid"
              >
                Use o botão “Nova fila” ou escolha uma das filas disponíveis.
              </Empty>
            </section>
          ) : (
            <>
              <div className="admin-summary">
                <div className="summary-state">
                  <Badge value={fila.estado} />
                  <span>
                    {aberta
                      ? 'Emissão e chamadas disponíveis'
                      : 'Novas emissões e chamadas suspensas'}
                  </span>
                </div>
                <div className="summary-counts">
                  <span>
                    <strong>
                      {senhas.data
                        ? senhas.data.filter((s) => s.estado === 'aguardando').length
                        : '—'}
                    </strong>{' '}
                    aguardando
                  </span>
                  <span>
                    <strong>
                      {senhas.data
                        ? senhas.data.filter((s) => s.estado === 'em_atendimento').length
                        : '—'}
                    </strong>{' '}
                    em atendimento
                  </span>
                </div>
                <button
                  className={`button button-small ${aberta ? 'button-ghost' : 'button-primary'}`}
                  disabled={action.busy}
                  onClick={() =>
                    aberta
                      ? setShowClose(true)
                      : void action.run(async () => {
                          await api.reabrir(filaId);
                          refresh();
                        }, 'Fila reaberta. As senhas canceladas permanecem no histórico.')
                  }
                >
                  <Icon name={aberta ? 'stop' : 'play'} size={14} />
                  {aberta ? 'Encerrar fila' : 'Reabrir fila'}
                </button>
              </div>
              <section className="admin-attendance" aria-labelledby="attendance-title">
                <div className="attendance-current">
                  <div className="inline-heading">
                    <p className="eyebrow" id="attendance-title">
                      ATENDIMENTO SELECIONADO
                    </p>
                    <Icon name="ticket" size={21} />
                  </div>
                  <div className="attendance-number-row">
                    <div className="attendance-number" data-testid="admin-ticket-number">
                      {selected.data?.numero || '—'}
                    </div>
                    <div className="attendance-guiche">
                      <span>GUICHÊ</span>
                      <strong>{selected.data?.guiche_id || '—'}</strong>
                    </div>
                  </div>
                  <div className="attendance-status">
                    {selected.data ? (
                      <>
                        <Badge value={selected.data.estado} />
                        <Kind value={selected.data.tipo} />
                      </>
                    ) : (
                      <p>Chame a próxima senha para começar.</p>
                    )}
                  </div>
                  <div className="attendance-buttons">
                    <button
                      className="button button-light"
                      disabled={
                        action.busy ||
                        selected.loading ||
                        !aberta ||
                        selected.data?.estado !== 'chamada'
                      }
                      onClick={() => transicionar(true)}
                    >
                      <Icon name="play" size={16} />
                      Iniciar atendimento
                    </button>
                    <button
                      className="button button-outline-light"
                      disabled={
                        action.busy ||
                        selected.loading ||
                        selected.data?.estado !== 'em_atendimento'
                      }
                      onClick={() => transicionar(false)}
                    >
                      <Icon name="check" size={17} />
                      Finalizar atendimento
                    </button>
                  </div>
                </div>
                <form className="call-form" onSubmit={chamar}>
                  <h2>Próxima chamada</h2>
                  <p>A ordem de atendimento é definida automaticamente pela fila.</p>
                  <div className="call-fields">
                    <label>
                      Atendente
                      <input
                        value={atendente}
                        onChange={(event) => setAtendente(event.target.value)}
                        placeholder="Sua identificação"
                        required
                      />
                    </label>
                    <label>
                      Guichê
                      <input
                        value={guiche}
                        onChange={(event) => setGuiche(event.target.value)}
                        placeholder="Identificação do guichê"
                        required
                      />
                    </label>
                  </div>
                  <button
                    className="button button-primary button-full"
                    disabled={
                      action.busy ||
                      !aberta ||
                      !senhas.data?.some((s) => s.estado === 'aguardando') ||
                      !atendente.trim() ||
                      !guiche.trim()
                    }
                  >
                    <Icon name="bell" size={18} />
                    {action.busy ? 'Aguarde…' : 'Chamar próxima senha'}
                    <Icon name="arrow" size={18} />
                  </button>
                  <p className="field-help">
                    {!aberta
                      ? 'Reabra a fila para realizar uma nova chamada.'
                      : senhas.data?.some((s) => s.estado === 'aguardando')
                        ? 'A senha será destacada ao lado e atualizada na visão do usuário.'
                        : 'Nenhuma senha aguardando nesta fila.'}
                  </p>
                </form>
              </section>
              <nav className="content-tabs" aria-label="Informações da fila">
                {(
                  [
                    ['fila', 'Senhas da fila', 'users'],
                    ['historico', 'Histórico', 'history'],
                    ['notificacoes', 'Notificações', 'bell'],
                  ] as const
                ).map(([value, label, icon]) => (
                  <button
                    key={value}
                    className={tab === value ? 'is-active' : ''}
                    aria-current={tab === value ? 'page' : undefined}
                    onClick={() => setTab(value)}
                  >
                    <Icon name={icon} size={18} />
                    {label}
                    {value === 'fila' && senhas.data && (
                      <span className="tab-count">{senhas.data.length}</span>
                    )}
                  </button>
                ))}
              </nav>
              {tab === 'fila' && (
                <section className="panel data-panel" aria-labelledby="active-title">
                  <div className="panel-toolbar">
                    <div>
                      <h2 id="active-title">Senhas ativas</h2>
                      <p>Selecione uma senha chamada para acompanhar seu atendimento.</p>
                    </div>
                    <span className="subtle-tag">
                      <Icon name="refresh" size={14} />
                      Atualização automática
                    </span>
                  </div>
                  {senhas.data?.length === 0 ? (
                    <Empty title="A fila está tranquila por aqui.">
                      As senhas emitidas pelos usuários aparecerão nesta lista.
                    </Empty>
                  ) : !senhas.data ? (
                    <p className="loading-text">Consultando senhas…</p>
                  ) : (
                    <div className="table-wrap">
                      <table>
                        <caption className="sr-only">Senhas ativas na fila selecionada</caption>
                        <thead>
                          <tr>
                            <th scope="col">Senha</th>
                            <th scope="col">Tipo</th>
                            <th scope="col">Estado</th>
                            <th scope="col">Emissão</th>
                            <th scope="col">Guichê</th>
                            <th scope="col">
                              <span className="sr-only">Selecionar</span>
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {senhas.data.map((s) => (
                            <tr key={s.id} className={selectedId === s.id ? 'selected-row' : ''}>
                              <td>
                                <strong className="table-ticket">{s.numero}</strong>
                              </td>
                              <td>
                                <Kind value={s.tipo} />
                              </td>
                              <td>
                                <Badge value={s.estado} />
                              </td>
                              <td className="nowrap">{formatTime(s.emitida_em)}</td>
                              <td>{s.guiche_id || '—'}</td>
                              <td>
                                <button
                                  className="text-button"
                                  onClick={() => setFocusedId(s.id)}
                                  aria-label={`Selecionar senha ${s.numero}`}
                                  aria-pressed={selectedId === s.id}
                                >
                                  Selecionar
                                  <Icon name="chevron" size={14} />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
              )}
              {tab === 'historico' && (
                <HistoryPanel key={filaId} filaId={filaId} revision={revision} />
              )}
              {tab === 'notificacoes' && <NotificationsPanel key={filaId} filaId={filaId} />}
            </>
          )}
        </div>
      </div>
      {showClose && fila && (
        <ConfirmClose
          name={fila.nome}
          busy={action.busy}
          cancel={() => setShowClose(false)}
          confirm={() =>
            void action.run(async () => {
              await api.encerrar(filaId);
              setShowClose(false);
              refresh();
            }, 'Fila encerrada. As pendências foram canceladas e registradas no histórico.')
          }
        />
      )}
    </Layout>
  );
}
