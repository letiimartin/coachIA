/**
 * Datos de prueba del coach (contrato de #55), sólo en memoria: se pierden al recargar.
 *
 * El contrato sólo trae ejemplos de `BudgetOut` (al 80 %, `warning`) y `MessageCreate`; el
 * presupuesto sale tal cual del primero. Los textos del coach están escritos a mano a partir de los
 * ejemplos del perfil, el umbral y la carrera del contrato; no los genera ningún LLM ni la app
 * calcula nada (el gasto del mes no cambia en el mock).
 *
 * Flujo: la primera conversación es la toma de contacto; el coach abre con una o dos preguntas y,
 * tras la segunda respuesta de la atleta, cierra con un resumen y tres propuestas de memoria. Para
 * probar los errores: un mensaje con «error» responde 502 `coach_llm_error` (no se guarda) y uno
 * con «mareo» pasa por el filtro de seguridad y uno con «agotado» recibe la respuesta fija por
 * presupuesto agotado (`origin = budget_limit`), que la app sustituye por un mensaje neutro.
 */
import { contractExamples } from './contractExamples.generated';
import { ApiError } from './errors';
import type {
  BudgetOut,
  CoachReplyOut,
  CoachStatusOut,
  ConversationCreatedOut,
  ConversationKind,
  ConversationOut,
  MemoryConfirm,
  MemoryCreate,
  MemoryKind,
  MemoryOut,
  MemoryPatch,
  MemoryStatus,
  MessageOrigin,
  MessageOut,
} from './types';

const MODEL = 'claude-haiku-5-5';

function clone<T>(value: T): T {
  return value === undefined ? value : (JSON.parse(JSON.stringify(value)) as T);
}

function later<T>(value: T, ms = 250): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(clone(value)), ms));
}

function fail(error: ApiError, ms = 250): Promise<never> {
  return new Promise((_, reject) => setTimeout(() => reject(error), ms));
}

function uuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.floor(Math.random() * 16);
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

const nowIso = () => new Date().toISOString();

const notFound = () => new ApiError(404, 'not_found', 'Recurso no encontrado (datos de prueba).');

const budget = (contractExamples.BudgetOut?.[0] ?? {
  limit_eur: 4,
  month: '2026-11-01',
  spent_eur: 0,
  state: 'ok',
  warning_eur: 3.2,
}) as BudgetOut;

const OPENING =
  'Hola, Leti. Soy tu coach. Antes de escribirte he mirado lo que ya hay en la app: entrenas ciclismo y trail, ' +
  'tu FTP vigente es de 230 W (test del 1 de noviembre) y tu objetivo marcado es el Trail de la Sierra, ' +
  'el 18 de abril: 42 km y 2400 m+, con prioridad A.\n\n' +
  '¿Qué esperas de esa carrera, además de terminarla por debajo de 6 h? ¿Y cuántos días a la semana puedes entrenar de verdad?';

const SECOND =
  'Gracias. Una cosa más: ¿hay algo que debamos tener en cuenta, como molestias, horarios fijos o sesiones que no te gusten?';

const SUMMARY =
  'Perfecto, con esto ya tengo lo necesario. Resumen de lo que me has contado:\n\n' +
  '- Objetivo: el Trail de la Sierra (18 de abril), por debajo de 6 h y llegando con buenas piernas a las bajadas.\n' +
  '- Entrenas cuatro días: dos de bici entre semana y trail el fin de semana.\n' +
  '- Prefieres entrenar por la mañana temprano.\n\n' +
  'Revísalo abajo: corrige lo que no esté bien y confirma lo que quieres que recuerde.';

const SUMMARY_PROPOSALS: { kind: MemoryKind; content: string }[] = [
  { kind: 'goal', content: 'Trail de la Sierra (18 de abril): terminar por debajo de 6 h y llegar con buenas piernas a las bajadas.' },
  { kind: 'other', content: 'Entrena cuatro días a la semana: dos de bici entre semana y trail el fin de semana.' },
  { kind: 'preference', content: 'Prefiere entrenar por la mañana temprano.' },
];

const CHAT_REPLY =
  'Respuesta de prueba: con la API real, aquí llega la respuesta completa del coach, que lee tu plan, ' +
  'tu forma y tu calendario antes de contestar.';

const SAFETY_REPLY =
  'Lo que describes puede necesitar una valoración médica. No entrenes hoy y consulta con un profesional sanitario; ' +
  'si los síntomas son intensos o empeoran, llama al 112.';

const BUDGET_REPLY = 'Se ha alcanzado el presupuesto del mes. El coach volverá a responder el mes que viene.';

const SAFETY_WORDS = /mareo|desmay|dolor (en el|de) pecho|torácic/i;

type MockConversation = ConversationOut & { messages: MessageOut[] };

const state = {
  conversations: [] as MockConversation[],
  memory: [] as MemoryOut[],
};

function findConversation(id: string): MockConversation {
  const c = state.conversations.find((x) => x.id === id);
  if (!c) throw notFound();
  return c;
}

function toConversationOut({ messages: _messages, ...c }: MockConversation): ConversationOut {
  return c;
}

function addMessage(c: MockConversation, role: 'user' | 'assistant', content: string, origin: MessageOrigin | null = null): MessageOut {
  const assistant = role === 'assistant';
  const message: MessageOut = {
    id: uuid(),
    seq: c.messages.length + 1,
    role,
    content,
    origin: assistant ? (origin ?? 'llm') : null,
    model: assistant && (origin ?? 'llm') === 'llm' ? MODEL : null,
    tokens_in: null,
    tokens_out: null,
    cost_eur: null,
    created_at: nowIso(),
  };
  c.messages.push(message);
  c.last_message_at = message.created_at;
  c.updated_at = message.created_at;
  if (!c.title && role === 'user') c.title = content.length > 48 ? `${content.slice(0, 47)}…` : content;
  return message;
}

function propose(c: MockConversation, source: MessageOut, items: { kind: MemoryKind; content: string }[]): MemoryOut[] {
  const created = items.map<MemoryOut>((item) => ({
    id: uuid(),
    kind: item.kind,
    content: item.content,
    source: 'coach',
    status: 'proposed',
    conversation_id: c.id,
    source_message_id: source.id,
    confirmed_at: null,
    created_at: source.created_at,
    updated_at: source.created_at,
  }));
  state.memory.push(...created);
  return created;
}

/** Como la API: la última toma de contacto manda; una repetida y sin terminar cuenta como en curso. */
function intakeStatus(): CoachStatusOut['intake'] {
  const intakes = state.conversations.filter((c) => c.kind === 'intake');
  const completedAt = intakes.map((c) => c.intake_completed_at).filter((d): d is string => !!d).sort().pop() ?? null;
  const latest = intakes[0];
  if (!latest) return { state: 'not_started', completed_at: null, conversation_id: null };
  return { state: latest.intake_completed_at ? 'completed' : 'in_progress', completed_at: completedAt, conversation_id: latest.id };
}

/** La toma de contacto queda hecha cuando ya no hay propuestas pendientes en ella (y hubo alguna). */
function checkIntakeDone(conversationId: string | null) {
  if (!conversationId) return;
  const c = state.conversations.find((x) => x.id === conversationId);
  if (!c || c.kind !== 'intake' || c.intake_completed_at) return;
  const mine = state.memory.filter((m) => m.conversation_id === c.id);
  if (mine.length && !mine.some((m) => m.status === 'proposed')) c.intake_completed_at = nowIso();
}

function findMemory(id: string): MemoryOut {
  const m = state.memory.find((x) => x.id === id);
  if (!m) throw notFound();
  return m;
}

const conflict = (message: string) => new ApiError(409, 'conflict', message);

export const coachMock = {
  status: (): Promise<CoachStatusOut> => later({ available: true, model: MODEL, intake: intakeStatus(), budget }),

  createConversation: (kind?: ConversationKind): Promise<ConversationCreatedOut> => {
    const resolved: ConversationKind = kind ?? (intakeStatus().completed_at ? 'chat' : 'intake');
    const c: MockConversation = {
      id: uuid(),
      kind: resolved,
      channel: 'app',
      title: resolved === 'intake' ? 'Toma de contacto' : null,
      summary: null,
      intake_completed_at: null,
      created_at: nowIso(),
      updated_at: nowIso(),
      last_message_at: null,
      messages: [],
    };
    state.conversations.unshift(c);
    if (resolved !== 'intake') return later({ conversation: toConversationOut(c), opening: null });
    const reply = addMessage(c, 'assistant', OPENING);
    return later({ conversation: toConversationOut(c), opening: { user_message: null, reply, memory_proposals: [], budget } }, 1200);
  },

  listConversations: () =>
    later(
      [...state.conversations]
        .sort((a, b) => (b.last_message_at ?? b.created_at).localeCompare(a.last_message_at ?? a.created_at))
        .map(toConversationOut),
    ),

  getConversation: (id: string) => {
    try {
      return later(toConversationOut(findConversation(id)));
    } catch (e) {
      return fail(e as ApiError);
    }
  },

  listMessages: (id: string) => {
    try {
      return later(findConversation(id).messages);
    } catch (e) {
      return fail(e as ApiError);
    }
  },

  sendMessage: (id: string, content: string): Promise<CoachReplyOut> => {
    let c: MockConversation;
    try {
      c = findConversation(id);
    } catch (e) {
      return fail(e as ApiError);
    }
    if (/\berror\b/i.test(content)) {
      return fail(new ApiError(502, 'coach_llm_error', 'El coach no ha podido responder. Inténtalo de nuevo.', 'mock-request-id'), 1200);
    }
    const user_message = addMessage(c, 'user', content);
    if (SAFETY_WORDS.test(content)) {
      const reply = addMessage(c, 'assistant', SAFETY_REPLY, 'safety_filter');
      return later({ user_message, reply, memory_proposals: [], budget }, 400);
    }
    if (/agotado/i.test(content)) {
      const reply = addMessage(c, 'assistant', BUDGET_REPLY, 'budget_limit');
      return later({ user_message, reply, memory_proposals: [], budget: { ...budget, state: 'exhausted' } }, 400);
    }
    const userTurns = c.messages.filter((m) => m.role === 'user').length;
    if (c.kind === 'intake' && !c.intake_completed_at) {
      if (userTurns === 1) {
        const reply = addMessage(c, 'assistant', SECOND);
        return later({ user_message, reply, memory_proposals: [], budget }, 1500);
      }
      if (!state.memory.some((m) => m.conversation_id === c.id)) {
        const reply = addMessage(c, 'assistant', SUMMARY);
        return later({ user_message, reply, memory_proposals: propose(c, reply, SUMMARY_PROPOSALS), budget }, 2000);
      }
    }
    const reply = addMessage(c, 'assistant', CHAT_REPLY);
    return later({ user_message, reply, memory_proposals: [], budget }, 1500);
  },

  listMemory: (status: MemoryStatus) => later(state.memory.filter((m) => m.status === status)),

  createMemory: (body: MemoryCreate): Promise<MemoryOut> => {
    const now = nowIso();
    const m: MemoryOut = {
      id: uuid(),
      kind: body.kind,
      content: body.content.trim(),
      source: 'athlete',
      status: 'confirmed',
      conversation_id: null,
      source_message_id: null,
      confirmed_at: now,
      created_at: now,
      updated_at: now,
    };
    state.memory.push(m);
    return later(m);
  },

  confirmMemory: (id: string, body: MemoryConfirm): Promise<MemoryOut> => {
    try {
      const m = findMemory(id);
      if (m.status !== 'proposed') return fail(conflict('La propuesta ya no está pendiente.'));
      const now = nowIso();
      Object.assign(m, {
        status: 'confirmed',
        content: body.content?.trim() || m.content,
        kind: body.kind ?? m.kind,
        confirmed_at: now,
        updated_at: now,
      });
      checkIntakeDone(m.conversation_id);
      return later(m);
    } catch (e) {
      return fail(e as ApiError);
    }
  },

  rejectMemory: (id: string): Promise<MemoryOut> => {
    try {
      const m = findMemory(id);
      if (m.status !== 'proposed') return fail(conflict('La propuesta ya no está pendiente.'));
      Object.assign(m, { status: 'rejected', updated_at: nowIso() });
      checkIntakeDone(m.conversation_id);
      return later(m);
    } catch (e) {
      return fail(e as ApiError);
    }
  },

  updateMemory: (id: string, body: MemoryPatch): Promise<MemoryOut> => {
    try {
      const m = findMemory(id);
      if (m.status !== 'confirmed') return fail(conflict('Sólo se puede corregir lo confirmado.'));
      Object.assign(m, { content: body.content?.trim() || m.content, kind: body.kind ?? m.kind, updated_at: nowIso() });
      return later(m);
    } catch (e) {
      return fail(e as ApiError);
    }
  },

  deleteMemory: (id: string): Promise<void> => {
    const before = state.memory.length;
    state.memory = state.memory.filter((m) => m.id !== id);
    return before === state.memory.length ? fail(notFound()) : later(undefined);
  },
};
