/**
 * Pestaña Coach conectada (#56), con la composición de la propuesta v3: mensajes sin contenedores
 * (los propios en `surfaceSoft`), caja de texto abajo y el globo de conversación como icono.
 *
 * - Primera vez: si la toma de contacto no ha empezado, se crea y el coach escribe primero.
 * - Al enviar, «pensando» y después la respuesta completa (sin streaming). Si falla, el mensaje
 *   queda marcado con el error y se puede reintentar o editar (la API no lo guarda).
 * - Lo que el coach propone recordar se revisa bajo su mensaje: confirmar, corregir o descartar.
 * - Si el coach no puede responder (sin proveedor, presupuesto agotado o respuesta fija por
 *   presupuesto), sólo un mensaje neutro y la caja de texto deshabilitada. El presupuesto no se
 *   muestra a la atleta: es cosa de los desarrolladores.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, type NavigationProp, type ParamListBase, type RouteProp } from '@react-navigation/native';

import { coachApi } from '../../api/coachApi';
import { ApiError, errorText } from '../../api/errors';
import type { CoachStatusOut, ConversationKind, ConversationOut, MemoryKind, MemoryOut, MessageOut } from '../../api/types';
import type { MainTabParamList } from '../../navigation/types';
import { COACH_UNAVAILABLE_TEXT, ChatDayLabel, ChatMessage, ComposeBar, FailedMessage, Suggestions, ThinkingRow, chatDayLabel, startsNewDay } from '../../ui/Chat';
import { MemoryProposals } from '../../ui/CoachMemory';
import { Button, ErrorBanner, IconButton, Loading, MockBanner, styles as base } from '../../ui/components';
import { Icon } from '../../ui/Icon';
import { colors, spacing, typography } from '../../ui/theme';

type Props = { navigation: NavigationProp<ParamListBase>; route: RouteProp<MainTabParamList, 'Coach'> };

/** Conversación elegida: un id, `new` (nueva, se crea al enviar) o null (la que toque). */
type Target = string | 'new' | null;

/** Mensaje enviado esperando respuesta (`error` null) o que no se ha podido enviar. */
type Pending = { content: string; error: string | null };

const SUGGESTIONS = ['¿Qué hago hoy?', 'Sólo tengo 1 h', 'Estoy cansada', 'Cambio de agenda'];

type ChatRole = 'user' | 'assistant';
const isChatMessage = (m: MessageOut): m is MessageOut & { role: ChatRole } => m.role === 'user' || m.role === 'assistant';

export default function CoachChatScreen({ navigation, route }: Props) {
  const requested = route.params?.conversationId;
  const [status, setStatus] = useState<CoachStatusOut | null>(null);
  const [conversation, setConversation] = useState<ConversationOut | null>(null);
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [proposals, setProposals] = useState<MemoryOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [opening, setOpening] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const [draft, setDraft] = useState('');

  const target = useRef<Target>(null);
  const loadToken = useRef(0);
  const creatingIntake = useRef(false);
  const busy = useRef(false);
  // Abriendo la toma de contacto o esperando una respuesta (un envío fallido no bloquea).
  busy.current = opening || (pending !== null && pending.error === null);
  const scroll = useRef<ScrollView>(null);

  const show = useCallback((conv: ConversationOut | null, msgs: MessageOut[], pend: MemoryOut[]) => {
    setConversation(conv);
    setMessages(msgs);
    setProposals(conv ? pend.filter((p) => p.conversation_id === conv.id) : []);
  }, []);

  /** Crea una toma de contacto: el coach lee los datos y escribe primero (`opening`). */
  const startIntake = useCallback(
    async (kind?: ConversationKind) => {
      if (creatingIntake.current) return;
      creatingIntake.current = true;
      setOpening(true);
      setError(null);
      try {
        const created = await coachApi.createConversation(kind);
        target.current = created.conversation.id;
        loadToken.current += 1; // lo que estuviera cargando ya no vale
        show(created.conversation, created.opening ? [created.opening.reply] : [], created.opening?.memory_proposals ?? []);
        const budget = created.opening?.budget;
        if (budget) setStatus((s) => s && { ...s, budget });
        setStatus((s) => s && { ...s, intake: { ...s.intake, state: 'in_progress', conversation_id: created.conversation.id } });
      } catch (e) {
        setError(errorText(e));
        if (e instanceof ApiError && e.code === 'coach_unavailable') setStatus((s) => s && { ...s, available: false });
      } finally {
        creatingIntake.current = false;
        setOpening(false);
        setLoading(false);
      }
    },
    [show],
  );

  const load = useCallback(
    async (wanted: Target) => {
      const token = ++loadToken.current;
      const current = () => token === loadToken.current;
      setLoading(true);
      setLoadError(null);
      try {
        const st = await coachApi.status();
        if (!current()) return;
        setStatus(st);
        let id: string | null = wanted === 'new' ? null : wanted;
        if (!id && wanted !== 'new') {
          if (st.intake.state === 'in_progress') id = st.intake.conversation_id;
          else if (st.intake.state === 'completed') id = (await coachApi.listConversations(1))[0]?.id ?? null;
          else if (st.available) {
            // Primera vez: Coach empieza la toma de contacto.
            await startIntake();
            return;
          }
        }
        if (!id) {
          if (current()) show(null, [], []);
          return;
        }
        const [conv, msgs, pend] = await Promise.all([coachApi.getConversation(id), coachApi.listMessages(id), coachApi.listMemory('proposed')]);
        if (current()) show(conv, msgs, pend);
      } catch (e) {
        if (current()) setLoadError(errorText(e));
      } finally {
        if (current()) setLoading(false);
      }
    },
    [show, startIntake],
  );

  // Conversación pedida desde la lista de conversaciones.
  useEffect(() => {
    if (!requested || requested === target.current) return;
    target.current = requested;
    setPending(null);
    void load(requested);
  }, [requested, load]);

  // Al volver a la pestaña (p. ej. tras confirmar memoria en otra pantalla), se recarga.
  useFocusEffect(
    useCallback(() => {
      if (!busy.current) void load(target.current);
    }, [load]),
  );

  /** Estado y conversación al día (tras revisar la memoria de la toma de contacto). */
  const refreshMeta = useCallback(async (id: string) => {
    try {
      const [st, conv] = await Promise.all([coachApi.status(), coachApi.getConversation(id)]);
      setStatus(st);
      setConversation((c) => (c?.id === conv.id ? conv : c));
    } catch {
      // No es imprescindible: se actualiza en la próxima carga.
    }
  }, []);

  const send = useCallback(
    async (content: string) => {
      if (!content || busy.current) return;
      busy.current = true;
      setPending({ content, error: null });
      setError(null);
      try {
        let conv = conversation;
        if (!conv) {
          conv = (await coachApi.createConversation('chat')).conversation;
          target.current = conv.id;
          navigation.setParams({ conversationId: conv.id });
          setConversation(conv);
        }
        const reply = await coachApi.sendMessage(conv.id, content);
        setMessages((ms) => [...ms, ...(reply.user_message ? [reply.user_message] : []), reply.reply]);
        setStatus((s) => s && { ...s, budget: reply.budget });
        setPending(null);
        if (reply.memory_proposals.length) {
          // Una propuesta nueva puede sustituir a otra anterior: se piden las pendientes.
          const id = conv.id;
          setProposals((ps) => [...ps.filter((p) => !reply.memory_proposals.some((n) => n.id === p.id)), ...reply.memory_proposals]);
          coachApi
            .listMemory('proposed')
            .then((pend) => setProposals(pend.filter((p) => p.conversation_id === id)))
            .catch(() => undefined);
        }
        // El título lo pone la API con el primer mensaje.
        if (!conv.title) void refreshMeta(conv.id);
      } catch (e) {
        if (e instanceof ApiError && e.code === 'coach_unavailable') setStatus((s) => s && { ...s, available: false });
        setPending({ content, error: errorText(e) });
      }
    },
    [conversation, navigation, refreshMeta],
  );

  const onSend = () => {
    const content = draft.trim();
    if (!content) return;
    setDraft('');
    void send(content);
  };

  const reviewed = (item: MemoryOut) => {
    setProposals((ps) => ps.filter((p) => p.id !== item.id));
    if (conversation?.kind === 'intake') void refreshMeta(conversation.id);
  };

  const confirmProposal = async (item: MemoryOut, correction?: { content: string; kind: MemoryKind }) => {
    setError(null);
    try {
      await coachApi.confirmMemory(item.id, correction ?? {});
      reviewed(item);
    } catch (e) {
      setError(errorText(e));
      throw e;
    }
  };

  const rejectProposal = async (item: MemoryOut) => {
    setError(null);
    try {
      await coachApi.rejectMemory(item.id);
      reviewed(item);
    } catch (e) {
      setError(errorText(e));
      throw e;
    }
  };

  const confirmAll = async (items: MemoryOut[]) => {
    for (const item of items) await confirmProposal(item);
  };

  const startNew = () => {
    target.current = 'new';
    setPending(null);
    setError(null);
    navigation.setParams({ conversationId: undefined });
    void load('new');
  };

  const chat = messages.filter(isChatMessage);
  // Sin proveedor, con el presupuesto agotado o si la última respuesta es la fija por presupuesto.
  const available =
    (status?.available ?? true) && status?.budget.state !== 'exhausted' && chat[chat.length - 1]?.origin !== 'budget_limit';
  const attached = new Set(chat.map((m) => m.id));
  const loose = proposals.filter((p) => !p.source_message_id || !attached.has(p.source_message_id));
  const intakeDone = conversation?.kind === 'intake' && !!conversation.intake_completed_at;
  const emptyIntake = conversation?.kind === 'intake' && chat.length === 0 && !opening && !pending;
  const showEmpty = !loading && !loadError && !opening && !emptyIntake && chat.length === 0 && !pending && available;
  const subtitle = conversation?.title ?? (conversation?.kind === 'intake' ? 'Toma de contacto' : conversation ? 'Conversación' : 'Nueva conversación');

  const proposalsFor = (items: MemoryOut[]) =>
    items.length ? (
      <MemoryProposals items={items} onConfirm={confirmProposal} onReject={rejectProposal} onConfirmAll={() => confirmAll(items)} />
    ) : null;

  return (
    <SafeAreaView style={base.safe} edges={['top']}>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={[base.column, styles.header]}>
          <View style={styles.headerText}>
            <Text style={styles.title} accessibilityRole="header">
              Coach
            </Text>
            <Text style={base.muted} numberOfLines={1}>
              {subtitle}
            </Text>
          </View>
          <View style={base.topBarRight}>
            <IconButton icon="conversations" label="Conversaciones anteriores" onPress={() => navigation.navigate('CoachConversations')} />
            <IconButton icon="coachMemory" label="Lo que el coach sabe de mí" onPress={() => navigation.navigate('CoachMemory')} />
            <IconButton icon="newConversation" label="Nueva conversación" onPress={startNew} />
          </View>
        </View>
        <ScrollView
          ref={scroll}
          style={styles.flex}
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => scroll.current?.scrollToEnd({ animated: true })}
        >
          <View style={[base.column, styles.content]}>
            <View style={styles.notices}>
              <MockBanner />
              {!available ? (
                <View style={[base.banner, base.warning]} accessibilityRole="alert">
                  <Text style={base.warningText}>{COACH_UNAVAILABLE_TEXT}</Text>
                </View>
              ) : null}
              <ErrorBanner message={error} onDismiss={() => setError(null)} />
            </View>

            {loadError ? (
              <View style={styles.block}>
                <ErrorBanner message={loadError} />
                <Button title="Reintentar" variant="secondary" onPress={() => void load(target.current)} />
              </View>
            ) : null}

            {loading && !opening && chat.length === 0 && !loadError ? <Loading /> : null}

            {showEmpty ? (
              <View style={styles.empty}>
                <Icon name="coach" size={40} color={colors.textSecondary} />
                <Text style={styles.emptyTitle}>¿En qué te ayudo?</Text>
                <Text style={[base.muted, styles.center]}>
                  Cuéntale cómo te encuentras o qué ha cambiado en tu agenda. Conoce tu plan, tu calendario y tus sensaciones.
                </Text>
                <Suggestions items={SUGGESTIONS} onPick={setDraft} />
              </View>
            ) : null}

            {emptyIntake && !loading && available ? (
              <View style={styles.empty}>
                <Icon name="coach" size={40} color={colors.textSecondary} />
                <Text style={styles.emptyTitle}>Toma de contacto</Text>
                <Text style={[base.muted, styles.center]}>
                  El coach empieza leyendo lo que ya sabe de ti y te hace una o dos preguntas cada vez.
                </Text>
                <Button title="Empezar la toma de contacto" onPress={() => void startIntake('intake')} />
              </View>
            ) : null}

            {chat.map((m, i) => (
              <React.Fragment key={m.id}>
                {startsNewDay(m.created_at, chat[i - 1]?.created_at) ? <ChatDayLabel label={chatDayLabel(m.created_at)} /> : null}
                <ChatMessage role={m.role} content={m.content} origin={m.origin}>
                  {m.role === 'assistant' ? proposalsFor(proposals.filter((p) => p.source_message_id === m.id)) : null}
                </ChatMessage>
              </React.Fragment>
            ))}
            {proposalsFor(loose)}

            {intakeDone && proposals.length === 0 ? (
              <Pressable onPress={() => navigation.navigate('CoachMemory')} accessibilityRole="link" style={styles.doneNote}>
                <Icon name="check" size={16} color={colors.textActive} />
                <Text style={styles.doneText}>
                  Toma de contacto hecha. Lo que has confirmado está en <Text style={styles.link}>Lo que el coach sabe de mí</Text>.
                </Text>
              </Pressable>
            ) : null}

            {opening ? <ThinkingRow label="El coach está leyendo tus datos…" /> : null}
            {pending && pending.error === null ? (
              <>
                <ChatMessage role="user" content={pending.content} />
                <ThinkingRow />
              </>
            ) : null}
            {pending && pending.error !== null ? (
              <FailedMessage
                content={pending.content}
                error={pending.error}
                onRetry={() => void send(pending.content)}
                onEdit={() => {
                  setDraft(pending.content);
                  setPending(null);
                }}
              />
            ) : null}
          </View>
        </ScrollView>
        <ComposeBar
          value={draft}
          onChangeText={setDraft}
          onSend={onSend}
          editable={available && !loadError}
          busy={opening || pending?.error === null || (loading && chat.length === 0)}
          placeholder={available ? 'Cuéntame qué ha cambiado…' : 'El coach no está disponible'}
        />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.md, paddingTop: spacing.lg, paddingBottom: spacing.sm },
  headerText: { flexShrink: 1, gap: spacing.xxs },
  title: { ...typography.heading, color: colors.text },
  scroll: { flexGrow: 1, paddingBottom: spacing.xl },
  content: { flexGrow: 1 },
  notices: { gap: spacing.sm },
  block: { gap: spacing.md, paddingTop: spacing.lg },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.md, paddingHorizontal: spacing.lg, paddingVertical: spacing.xxxl },
  emptyTitle: { ...typography.bodyBold, color: colors.text, textAlign: 'center' },
  center: { textAlign: 'center' },
  doneNote: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.sm, paddingTop: spacing.lg },
  doneText: { ...typography.small, color: colors.textSecondary, flexShrink: 1 },
  link: { ...typography.smallBold, color: colors.textActive },
});
