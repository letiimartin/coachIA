/**
 * Iconos de la app con nombres semánticos. Es el único fichero que importa la biblioteca de iconos
 * (Lucide, trazo 1,5): cambiarla es tocar sólo este mapa. Sin destellos, robots ni emojis; el Coach
 * es un globo de conversación.
 */
import React from 'react';
import {
  ArrowUp,
  CalendarDays,
  ChartColumn,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Clock,
  FileText,
  Flag,
  Globe,
  House,
  Link,
  LogOut,
  MessageCircle,
  Plus,
  RefreshCw,
  Settings,
  Trash2,
  User,
  X,
  Zap,
  type LucideIcon,
} from 'lucide-react-native';
// Tipos de evento y detalle (fase 1a, #24).
import { CalendarX2, ExternalLink, HeartPulse, Plane, UserRound, Users } from 'lucide-react-native';
// Entrenos planificados y sesión de fuerza (Fuerza 2, #31).
import { Activity, Bike, Dumbbell, Footprints, History, Mountain, Square, SquareCheck, Waves } from 'lucide-react-native';
// Coach conectado (#56): conversaciones, memoria, nueva conversación y corregir.
import { BookUser, MessagesSquare, Pencil, SquarePen } from 'lucide-react-native';

import { colors } from './theme';

const ICONS = {
  eventSocial: Users,
  eventTravel: Plane,
  eventHealth: HeartPulse,
  eventPersonal: UserRound,
  eventUnavailable: CalendarX2,
  externalLink: ExternalLink,
  today: House,
  plan: CalendarDays,
  coach: MessageCircle,
  performance: ChartColumn,
  profile: User,
  back: ChevronLeft,
  forward: ChevronRight,
  add: Plus,
  close: X,
  check: Check,
  alert: CircleAlert,
  race: Flag,
  sync: RefreshCw,
  integrations: Link,
  settings: Settings,
  delete: Trash2,
  logout: LogOut,
  // Fase 1b (#25): filas de Perfil, Ajustes, Rendimiento y Coach.
  thresholds: Zap,
  availability: Clock,
  timezone: Globe,
  activities: FileText,
  send: ArrowUp,
  // Fuerza 2 (#31): disciplinas de los entrenos planificados y registro de series.
  sportStrength: Dumbbell,
  sportCycling: Bike,
  sportRunning: Footprints,
  sportTrail: Mountain,
  sportSwimming: Waves,
  sportOther: Activity,
  setPending: Square,
  setDone: SquareCheck,
  lastLog: History,
  // Coach conectado (#56).
  conversations: MessagesSquare,
  coachMemory: BookUser,
  newConversation: SquarePen,
  edit: Pencil,
} satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof ICONS;

type IconProps = {
  name: IconName;
  size?: number;
  color?: string;
  /** 1,5 por defecto; 1,25 en tamaños grandes. */
  strokeWidth?: number;
};

export function Icon({ name, size = 22, color = colors.text, strokeWidth }: IconProps) {
  const Component = ICONS[name];
  return <Component size={size} color={color} strokeWidth={strokeWidth ?? (size >= 32 ? 1.25 : 1.5)} />;
}
