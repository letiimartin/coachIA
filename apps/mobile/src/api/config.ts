/**
 * Configuración del cliente de la API (variables públicas de Expo).
 *
 * - `EXPO_PUBLIC_API_URL`: URL base de la API (p. ej. https://letismartcoach.onrender.com).
 * - `EXPO_PUBLIC_API_MOCK`: cuándo usar los `examples` del contrato como datos de prueba.
 *     - `auto` (por defecto): se llama a la API y, si responde 501 (sin implementar), se usa el mock.
 *     - `on`: siempre mock, sin llamar a la API.
 *     - `off`: nunca mock; un 501 se muestra como error.
 *   Sin `EXPO_PUBLIC_API_URL`, el modo `auto` usa el mock.
 */
export type MockMode = 'auto' | 'on' | 'off';

function parseMode(value: string | undefined): MockMode {
  return value === 'on' || value === 'off' ? value : 'auto';
}

export const apiConfig = {
  baseUrl: (process.env.EXPO_PUBLIC_API_URL ?? '').replace(/\/+$/, ''),
  mockMode: parseMode(process.env.EXPO_PUBLIC_API_MOCK),
};
