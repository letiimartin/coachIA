/**
 * Sistema visual de CoachIA (propuesta v3, aprobada en #23).
 *
 * Es el ÚNICO fichero de la app con colores, radios y familias tipográficas escritos a mano:
 * `scripts/check-design-tokens.mjs` lo comprueba en CI. Todo lo demás usa estos tokens.
 *
 * Sólo existe el modo claro. Los colores son semánticos y van agrupados en `Palette` para que un
 * modo oscuro sea otra paleta con las mismas claves (`palettes.dark`) sin rehacer componentes.
 */
import { createContext, useContext } from 'react';
import { Platform, type TextStyle } from 'react-native';

export type Palette = {
  /** Fondo de todas las pantallas. El contenido va directamente sobre él. */
  background: string;
  /** Única superficie destacada (celeste): el entreno del día y la sesión abierta. */
  surfaceHighlight: string;
  /** Superficie suave (lavanda): estado seleccionado, mensajes propios y botón secundario. */
  surfaceSoft: string;
  /** Texto principal y cifras. */
  text: string;
  /** Etiquetas, unidades, subtítulos y ejes. */
  textSecondary: string;
  /** Texto activo, enlaces y elementos seleccionados (contraste 5,7:1 sobre el fondo). */
  textActive: string;
  /** Texto deshabilitado, marcadores de posición y pestañas inactivas en reposo. */
  textDisabled: string;
  /** Filetes de 1 px entre filas y columnas. */
  separator: string;
  /** Filete más marcado (cabeceras de tabla, bordes de campos). */
  separatorStrong: string;
  /** Acento para elementos de interfaz que no son texto: subrayados, marcas, foco. */
  accent: string;
  /** Relleno del botón principal. */
  primary: string;
  /** Texto sobre `primary`. */
  onPrimary: string;
  /** Errores y acciones destructivas. */
  danger: string;
  dangerSurface: string;
  /** Avisos (p. ej. datos de prueba del contrato). */
  warning: string;
  warningSurface: string;
};

const light: Palette = {
  background: '#F7F8FB',
  surfaceHighlight: '#DFEAFB',
  surfaceSoft: '#ECE8FA',
  text: '#24283D',
  textSecondary: '#6A7089',
  textActive: '#5E58A3',
  textDisabled: '#A3A8BA',
  separator: '#D8DDE9',
  separatorStrong: '#C3C9D8',
  accent: '#8B85C9',
  primary: '#24283D',
  onPrimary: '#FFFFFF',
  danger: '#B23B2F',
  dangerSurface: '#F8E6E3',
  warning: '#7A5A10',
  warningSurface: '#F8EFD6',
};

export type ColorScheme = 'light';
export const palettes: Record<ColorScheme, Palette> = { light };

/**
 * Colores de zona, independientes de la paleta y del modo. Sólo en datos deportivos y siempre
 * acompañados de su etiqueta (Z1…Z7). Los modelos de 5 zonas usan Z1–Z5.
 */
export const zoneColors = {
  Z1: '#8C93A3',
  Z2: '#4A86D8',
  Z3: '#3FA772',
  Z4: '#E2B33A',
  Z5: '#EC7D3A',
  Z6: '#D9534A',
  Z7: '#8E3FC4',
} as const;
export type ZoneCode = keyof typeof zoneColors;
/** Texto sobre un color de zona. */
export const onZoneColor = '#1B1E2C';

/** Esquinas casi rectas (1–2 px). */
export const radius = { none: 0, sm: 1, md: 2 } as const;

export const spacing = { xxs: 2, xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32, xxxl: 48 } as const;

/** Grosor de los filetes y del subrayado de selección. */
export const lines = { hairline: 1, selection: 2 } as const;

/**
 * Arimo (mismas medidas que Arial, licencia libre) en 400 y 700. Con fuentes cargadas a mano, en
 * Android el peso no se sintetiza: cada peso es una familia, así que se usa `fonts.bold` en lugar de
 * `fontWeight: '700'`.
 */
export const fonts = {
  regular: 'Arimo_400Regular',
  bold: 'Arimo_700Bold',
} as const;

/** Escala tipográfica: 34 / 28 / 22 / 15 / 13 / 11 / 10. */
export const fontSize = { display: 34, title: 28, heading: 22, body: 15, small: 13, caption: 11, micro: 10 } as const;

export const typography = {
  display: { fontFamily: fonts.bold, fontSize: fontSize.display, lineHeight: 38, letterSpacing: -0.7 },
  title: { fontFamily: fonts.bold, fontSize: fontSize.title, lineHeight: 32, letterSpacing: -0.5 },
  heading: { fontFamily: fonts.bold, fontSize: fontSize.heading, lineHeight: 27, letterSpacing: -0.3 },
  body: { fontFamily: fonts.regular, fontSize: fontSize.body, lineHeight: 22 },
  bodyBold: { fontFamily: fonts.bold, fontSize: fontSize.body, lineHeight: 22 },
  small: { fontFamily: fonts.regular, fontSize: fontSize.small, lineHeight: 18 },
  smallBold: { fontFamily: fonts.bold, fontSize: fontSize.small, lineHeight: 18 },
  caption: { fontFamily: fonts.regular, fontSize: fontSize.caption, lineHeight: 15 },
  /** Etiqueta de sección: mayúsculas con espaciado. */
  label: { fontFamily: fonts.bold, fontSize: fontSize.micro, lineHeight: 14, letterSpacing: 1.2, textTransform: 'uppercase' },
} satisfies Record<string, TextStyle>;

/** Anchura máxima de la columna de contenido en web y punto a partir del cual hay barra lateral. */
export const layout = { contentMaxWidth: 720, formMaxWidth: 440, sidebarBreakpoint: 900, sidebarWidth: 220 } as const;

export const isWeb = Platform.OS === 'web';

export type Theme = {
  scheme: ColorScheme;
  colors: Palette;
  zoneColors: typeof zoneColors;
  radius: typeof radius;
  spacing: typeof spacing;
  fonts: typeof fonts;
  typography: typeof typography;
};

export const lightTheme: Theme = { scheme: 'light', colors: light, zoneColors, radius, spacing, fonts, typography };

/** Contexto preparado para un segundo modo; hoy sólo existe el claro. */
export const ThemeContext = createContext<Theme>(lightTheme);

export function useTheme(): Theme {
  return useContext(ThemeContext);
}

/**
 * Paleta del modo claro para estilos estáticos (`StyleSheet.create`). Cuando haya modo oscuro, los
 * componentes que la usan pasarán a leer `useTheme().colors`.
 */
export const colors = light;
