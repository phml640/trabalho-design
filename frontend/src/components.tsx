import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import type { EstadoSenha, Pagina } from './types';

const paths = {
  ticket: 'M4 5h16v5a2 2 0 0 0 0 4v5H4v-5a2 2 0 0 0 0-4V5Zm10 2v2m0 3v2m0 3v-1',
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  users:
    'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  grid: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  clock: 'M12 8v4l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  check: 'm5 12 4 4L19 6',
  plus: 'M12 5v14M5 12h14',
  refresh: 'M20 7v5h-5M4 17v-5h5m10.5-4a8 8 0 0 0-13-3M4.5 16a8 8 0 0 0 13 3',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9m-11 9h10m-7 3h4',
  close: 'm6 6 12 12M6 18 18 6',
  chevron: 'm9 5 7 7-7 7',
  history: 'M3 11a9 9 0 1 1 2 7M3 4v7h7m2-4v5l3 2',
  info: 'M12 11v6m0-10v.01m9 5a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  play: 'm8 5 11 7-11 7V5Z',
  stop: 'M5 5h14v14H5z',
  home: 'm3 10 9-7 9 7v11h-7v-7h-4v7H3V10Z',
  star: 'm12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2-5.5-2.9-5.5 2.9 1-6.2L2 9.6l6.2-.9L12 3Z',
} as const;
export function Icon({ name, size = 20 }: { name: keyof typeof paths; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  );
}

export const labels: Record<string, string> = {
  aguardando: 'Aguardando',
  chamada: 'Chamada',
  em_atendimento: 'Em atendimento',
  finalizada: 'Finalizada',
  cancelada: 'Cancelada',
  aberta: 'Aberta',
  encerrada: 'Encerrada',
  pendente: 'Pendente',
  em_processamento: 'Em processamento',
  falha: 'Falha no envio',
  processada: 'Processada',
};
export function Badge({ value }: { value: string }) {
  return (
    <span className={`badge badge-${value}`}>
      <span className="badge-dot" />
      {labels[value] || value}
    </span>
  );
}
export function Kind({ value }: { value: string }) {
  return (
    <span className={`kind kind-${value}`}>
      {value === 'prioritaria' && <Icon name="star" size={13} />}
      {value === 'prioritaria' ? 'Prioritária' : 'Normal'}
    </span>
  );
}
export function Feedback({
  kind,
  text,
  dismiss,
}: {
  kind: 'success' | 'error';
  text: string;
  dismiss?: () => void;
}) {
  return (
    <div className={`feedback feedback-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <Icon name={kind === 'error' ? 'info' : 'check'} />
      <span>{text}</span>
      {dismiss && (
        <button
          className="icon-button"
          type="button"
          aria-label="Fechar mensagem"
          onClick={dismiss}
        >
          <Icon name="close" size={17} />
        </button>
      )}
    </div>
  );
}
export function Empty({
  title,
  children,
  icon = 'ticket',
}: {
  title: string;
  children?: ReactNode;
  icon?: keyof typeof paths;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon name={icon} size={27} />
      </span>
      <h3>{title}</h3>
      {children && <p>{children}</p>}
    </div>
  );
}
export function Sync({
  updatedAt,
  loading,
  refresh,
  error,
}: {
  updatedAt?: Date;
  loading: boolean;
  refresh: () => void;
  error?: Error;
}) {
  return (
    <div className="sync">
      <span className={`sync-dot ${error ? 'is-offline' : ''}`} />
      <span>
        {error
          ? 'Atualização indisponível'
          : updatedAt
            ? `Atualizado às ${updatedAt.toLocaleTimeString('pt-BR')}`
            : 'Consultando atendimento…'}
        <small>Atualização automática a cada 3 s</small>
      </span>
      <button
        className={`icon-button ${loading ? 'is-loading' : ''}`}
        onClick={refresh}
        aria-label="Atualizar agora"
        title="Atualizar agora"
        disabled={loading}
      >
        <Icon name="refresh" size={17} />
      </button>
    </div>
  );
}
export function Pagination({
  page,
  offset,
  change,
  busy = false,
}: {
  page?: Pick<Pagina<unknown>, 'itens' | 'tem_mais' | 'limite'>;
  offset: number;
  change: (offset: number) => void;
  busy?: boolean;
}) {
  return (
    <nav className="pagination" aria-label="Paginação">
      <span>
        {page?.itens.length
          ? `Registros ${offset + 1}–${offset + page.itens.length}`
          : 'Nenhum registro nesta página'}
      </span>
      <div>
        <button
          className="button button-small button-ghost"
          onClick={() => change(Math.max(0, offset - (page?.limite || 10)))}
          disabled={busy || offset === 0}
        >
          Anterior
        </button>
        <button
          className="button button-small button-ghost"
          onClick={() => change(offset + (page?.limite || 10))}
          disabled={busy || !page?.tem_mais}
        >
          Próxima <Icon name="chevron" size={14} />
        </button>
      </div>
    </nav>
  );
}
export function ConfirmClose({
  name,
  cancel,
  confirm,
  busy,
}: {
  name: string;
  cancel: () => void;
  confirm: () => void;
  busy: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="confirm-dialog"
      aria-labelledby="confirm-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) cancel();
      }}
    >
      <span className="empty-icon danger-icon">
        <Icon name="stop" />
      </span>
      <h2 id="confirm-title">Encerrar {name}?</h2>
      <p>
        As senhas aguardando ou chamadas serão canceladas. Atendimentos em andamento poderão ser
        finalizados.
      </p>
      <p className="muted">Reabrir a fila não reativa as senhas canceladas.</p>
      <div className="dialog-actions">
        <button className="button button-ghost" autoFocus onClick={cancel} disabled={busy}>
          Voltar
        </button>
        <button className="button button-danger" onClick={confirm} disabled={busy}>
          {busy ? 'Encerrando…' : 'Encerrar fila'}
        </button>
      </div>
    </dialog>
  );
}
export function Layout({ children, view }: { children: ReactNode; view?: 'usuario' | 'admin' }) {
  return (
    <>
      <a className="skip-link" href="#conteudo">
        Ir para o conteúdo
      </a>
      <header className="app-header">
        <a className="brand" href="/" aria-label="Em fila, início">
          <span className="brand-mark">
            <Icon name="ticket" size={25} />
          </span>
          <span>
            Em fila<small>ATENDIMENTO PRESENCIAL</small>
          </span>
        </a>
        <div className="header-right">
          <span className="demo-label">
            <span />
            Demonstração local
          </span>
          <nav className="view-nav" aria-label="Escolher visão">
            <a href="/usuario" aria-current={view === 'usuario' ? 'page' : undefined}>
              <Icon name="users" size={17} />
              Usuário
            </a>
            <a href="/admin" aria-current={view === 'admin' ? 'page' : undefined}>
              <Icon name="grid" size={17} />
              Atendimento
            </a>
          </nav>
        </div>
      </header>
      <main id="conteudo">{children}</main>
      <footer className="app-footer">
        <span>
          <Icon name="ticket" size={15} />
          Em fila · Projeto acadêmico de Design de Software
        </span>
        <span>Visões demonstrativas, sem controle de acesso.</span>
      </footer>
    </>
  );
}
export const formatTime = (date: string | null) =>
  date
    ? new Date(date).toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—';
export function ticketMessage(estado: EstadoSenha, guiche: string | null, motivo: string | null) {
  switch (estado) {
    case 'aguardando':
      return 'Pode ficar à vontade. Sua senha será atualizada aqui quando chegar a sua vez.';
    case 'chamada':
      return `É a sua vez! ${guiche ? `Dirija-se ao guichê ${guiche}.` : 'Procure o atendente para começar.'}`;
    case 'em_atendimento':
      return 'Seu atendimento está em andamento.';
    case 'finalizada':
      return 'Atendimento concluído. Obrigado pela visita!';
    case 'cancelada':
      return motivo === 'encerramento_diario'
        ? 'Sua senha foi cancelada porque o dia de atendimento foi encerrado.'
        : 'Sua senha foi cancelada porque a fila foi encerrada.';
  }
}
