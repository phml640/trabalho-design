import type {
  EstadoSenha,
  Fila,
  Notificacao,
  Pagina,
  Processamento,
  Senha,
  Simulada,
  Tentativa,
  TipoSenha,
  Transicao,
} from './types';

const base = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  if (init.signal?.aborted) cancel();
  init.signal?.addEventListener('abort', cancel, { once: true });
  let timedOut = false;
  const timeout = setTimeout(() => {
    timedOut = true;
    cancel();
  }, 10000);
  try {
    const response = await fetch(`${base}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers },
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = typeof body?.detail === 'string' ? body.detail : null;
      throw new ApiError(
        response.status,
        detail ||
          (response.status === 422
            ? 'Confira os dados informados e tente novamente.'
            : 'Não foi possível concluir a solicitação. Tente novamente.'),
      );
    }
    if (body === null)
      throw new ApiError(
        response.status,
        'A API retornou uma resposta inesperada. Confira a configuração de conexão.',
      );
    return body as T;
  } catch (error) {
    if (init.signal?.aborted || error instanceof ApiError) throw error;
    throw new ApiError(
      0,
      timedOut
        ? 'A API demorou para responder. Tente novamente.'
        : 'Não foi possível acessar o serviço. Verifique se a API está em execução. Tentaremos atualizar novamente.',
    );
  } finally {
    clearTimeout(timeout);
    init.signal?.removeEventListener('abort', cancel);
  }
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, {
    method: 'POST',
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
const id = encodeURIComponent;
const query = (params: Record<string, string | number | undefined>) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.set(key, String(value));
  });
  return `?${search}`;
};

export const api = {
  filas: (signal?: AbortSignal) => request<Fila[]>('/filas', { signal }),
  fila: (fila: string, signal?: AbortSignal) => request<Fila>(`/filas/${id(fila)}`, { signal }),
  criarFila: (nome: string, descricao: string) =>
    post<Fila>('/filas', { nome, descricao: descricao || null }),
  encerrar: (fila: string) => post<Fila>(`/filas/${id(fila)}/encerramento`),
  reabrir: (fila: string) => post<Fila>(`/filas/${id(fila)}/reabertura`),
  emitir: (fila: string, tipo: TipoSenha) =>
    post<Senha>(`/filas/${id(fila)}/senhas`, {
      usuario_id: crypto.randomUUID(),
      tipo,
      canal: 'online',
    }),
  senha: (senha: string, signal?: AbortSignal) =>
    request<Senha>(`/senhas/${id(senha)}`, { signal }),
  senhas: (fila: string, signal?: AbortSignal) =>
    request<Senha[]>(`/filas/${id(fila)}/senhas`, { signal }),
  chamar: (fila: string, atendente_id: string, guiche_id: string) =>
    post<Senha>(`/filas/${id(fila)}/senhas/chamada`, { atendente_id, guiche_id }),
  iniciar: (senha: string) => post<Senha>(`/senhas/${id(senha)}/atendimento/inicio`),
  finalizar: (senha: string) => post<Senha>(`/senhas/${id(senha)}/atendimento/finalizacao`),
  historico: (fila: string, offset: number, estado?: EstadoSenha, signal?: AbortSignal) =>
    request<Pagina<Transicao>>(
      `/filas/${id(fila)}/historico${query({ limite: 10, offset, estado })}`,
      { signal },
    ),
  notificacoes: (fila: string, offset: number, signal?: AbortSignal) =>
    request<Pagina<Notificacao>>(`/notificacoes${query({ fila_id: fila, limite: 10, offset })}`, {
      signal,
    }),
  simuladas: (fila: string, offset: number, signal?: AbortSignal) =>
    request<Pagina<Simulada>>(
      `/notificacoes/simuladas${query({ fila_id: fila, limite: 10, offset })}`,
      { signal },
    ),
  tentativas: (evento: string, offset: number, signal?: AbortSignal) =>
    request<Pagina<Tentativa>>(
      `/notificacoes/${id(evento)}/tentativas${query({ limite: 10, offset })}`,
      { signal },
    ),
  processar: (simular_falha = false) =>
    post<Processamento>('/notificacoes/processamento', { limite: 20, simular_falha }),
};

// Rótulos de senha para páginas de histórico; o estado continua vindo da API.
export async function numerosDasSenhas(
  ids: string[],
  signal: AbortSignal,
): Promise<Record<string, string>> {
  const entries = await Promise.all(
    [...new Set(ids)].map(async (senhaId) => {
      try {
        return [senhaId, (await api.senha(senhaId, signal)).numero] as const;
      } catch {
        return [senhaId, `#${senhaId.slice(0, 8)}`] as const;
      }
    }),
  );
  return Object.fromEntries(entries);
}
