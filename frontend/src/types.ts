export type TipoSenha = 'normal' | 'prioritaria';
export type EstadoSenha = 'aguardando' | 'chamada' | 'em_atendimento' | 'finalizada' | 'cancelada';
export interface Fila {
  id: string;
  nome: string;
  descricao: string | null;
  estado: 'aberta' | 'encerrada';
  dia_operacional: string;
  chamadas_prioritarias_consecutivas: number;
}
export interface Senha {
  id: string;
  fila_id: string;
  numero: string;
  tipo: TipoSenha;
  estado: EstadoSenha;
  emitida_em: string;
  dia_operacional: string;
  canal: 'online' | 'totem';
  chamada_em: string | null;
  atendimento_iniciado_em: string | null;
  atendimento_finalizado_em: string | null;
  guiche_id: string | null;
  atendente_id?: string | null;
  motivo_cancelamento: string | null;
}
export interface Transicao {
  id: string;
  senha_id: string;
  estado_anterior: EstadoSenha | null;
  estado: EstadoSenha;
  quando: string;
  atendente_id: string | null;
  guiche_id: string | null;
  motivo: string | null;
}
export interface Pagina<T> {
  itens: T[];
  limite: number;
  offset: number;
  tem_mais: boolean;
}
export interface Notificacao {
  evento: { id: string; senha_id: string; fila_id: string; chamada_em: string };
  status: 'pendente' | 'em_processamento' | 'falha' | 'processada';
  tentativas: number;
  processado_em: string | null;
  ultimo_erro: string | null;
}
export interface Simulada {
  evento_id: string;
  senha_id: string;
  mensagem: string;
  criada_em: string;
}
export interface Tentativa {
  id: string;
  numero: number;
  iniciada_em: string;
  finalizada_em: string | null;
  erro: string | null;
}
export interface Processamento {
  processadas: number;
  sucessos: number;
  falhas: number;
}
