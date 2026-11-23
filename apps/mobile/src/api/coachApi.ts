/**
 * Cliente del coach (contrato de #55). La respuesta llega completa (sin streaming). La memoria que
 * propone el coach se confirma, corrige o descarta aquí, con sus endpoints, nunca en el chat.
 *
 * Errores propios: 503 `coach_unavailable` (no hay proveedor de LLM configurado) y 502
 * `coach_llm_error` (el LLM ha fallado: el mensaje no se guarda y se puede reenviar).
 */
import { coachMock } from './coachMock';
import { request, withMock } from './http';
import type {
  CoachReplyOut,
  CoachStatusOut,
  ConversationCreatedOut,
  ConversationKind,
  ConversationOut,
  MemoryConfirm,
  MemoryCreate,
  MemoryOut,
  MemoryPatch,
  MemoryStatus,
  MessageOut,
} from './types';

const conversationPath = (id: string) => `/v1/coach/conversations/${encodeURIComponent(id)}`;
const memoryPath = (id: string) => `/v1/coach/memory/${encodeURIComponent(id)}`;

export const coachApi = {
  /** Disponibilidad, estado de la toma de contacto y presupuesto del mes (`ok|warning|exhausted`). */
  status: () => withMock(() => request<CoachStatusOut>('GET', '/v1/coach/status'), coachMock.status),

  /** Sin `kind`, toma de contacto si aún no se ha hecho ninguna (con `opening`); si no, conversación normal. */
  createConversation: (kind?: ConversationKind) =>
    withMock(
      () => request<ConversationCreatedOut>('POST', '/v1/coach/conversations', { body: { kind: kind ?? null } }),
      () => coachMock.createConversation(kind),
    ),

  /** De la más reciente a la más antigua. */
  listConversations: (limit = 50) =>
    withMock(
      () => request<ConversationOut[]>('GET', '/v1/coach/conversations', { query: { limit: String(limit) } }),
      coachMock.listConversations,
    ),

  getConversation: (id: string) =>
    withMock(
      () => request<ConversationOut>('GET', conversationPath(id)),
      () => coachMock.getConversation(id),
    ),

  /** Mensajes de la atleta y del coach, en orden. */
  listMessages: (id: string) =>
    withMock(
      () => request<MessageOut[]>('GET', `${conversationPath(id)}/messages`, { query: { limit: '500' } }),
      () => coachMock.listMessages(id),
    ),

  sendMessage: (id: string, content: string) =>
    withMock(
      () => request<CoachReplyOut>('POST', `${conversationPath(id)}/messages`, { body: { content } }),
      () => coachMock.sendMessage(id, content),
    ),

  /** Por defecto (sin `status`), sólo la memoria confirmada. */
  listMemory: (status?: MemoryStatus) =>
    withMock(
      () => request<MemoryOut[]>('GET', '/v1/coach/memory', { query: { status } }),
      () => coachMock.listMemory(status ?? 'confirmed'),
    ),

  /** La atleta añade algo: queda confirmado. */
  createMemory: (body: MemoryCreate) =>
    withMock(
      () => request<MemoryOut>('POST', '/v1/coach/memory', { body }),
      () => coachMock.createMemory(body),
    ),

  /** Confirma una propuesta, con la corrección si se envía. */
  confirmMemory: (id: string, body: MemoryConfirm = {}) =>
    withMock(
      () => request<MemoryOut>('POST', `${memoryPath(id)}/confirm`, { body }),
      () => coachMock.confirmMemory(id, body),
    ),

  rejectMemory: (id: string) =>
    withMock(
      () => request<MemoryOut>('POST', `${memoryPath(id)}/reject`),
      () => coachMock.rejectMemory(id),
    ),

  /** Corrige un elemento confirmado. */
  updateMemory: (id: string, body: MemoryPatch) =>
    withMock(
      () => request<MemoryOut>('PATCH', memoryPath(id), { body }),
      () => coachMock.updateMemory(id, body),
    ),

  deleteMemory: (id: string) =>
    withMock(
      () => request<void>('DELETE', memoryPath(id)),
      () => coachMock.deleteMemory(id),
    ),
};
