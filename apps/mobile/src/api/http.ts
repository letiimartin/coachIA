import { supabase } from '../lib/supabase';
import { apiConfig } from './config';
import { ApiError, toApiError } from './errors';
import { setUsingMock } from './mockStatus';

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
type Query = Record<string, string | undefined>;

async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Petición JSON a la API. Lanza ApiError con el formato del contrato si la respuesta no es 2xx. */
export async function request<T>(method: Method, path: string, options: { query?: Query; body?: unknown } = {}): Promise<T> {
  const params = Object.entries(options.query ?? {}).filter((e): e is [string, string] => e[1] !== undefined);
  const qs = params.length ? `?${new URLSearchParams(params).toString()}` : '';
  const headers: Record<string, string> = { Accept: 'application/json', ...(await authHeader()) };
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';

  let response: Response;
  try {
    response = await fetch(`${apiConfig.baseUrl}${path}${qs}`, {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError(0, 'network_error', 'No se ha podido conectar con el servidor.');
  }

  if (response.status === 204) return undefined as T;
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }
  if (!response.ok) throw toApiError(response.status, body);
  return body as T;
}

/**
 * Ejecuta la llamada real o, según `EXPO_PUBLIC_API_MOCK`, la de prueba con los ejemplos del contrato.
 * En modo `auto` sólo se recurre al mock si la API responde 501 (endpoint sin implementar).
 */
export async function withMock<T>(real: () => Promise<T>, mock: () => Promise<T>): Promise<T> {
  const { mockMode, baseUrl } = apiConfig;
  if (mockMode === 'on' || (mockMode === 'auto' && !baseUrl)) {
    setUsingMock(true);
    return mock();
  }
  try {
    const result = await real();
    setUsingMock(false);
    return result;
  } catch (error) {
    if (mockMode === 'auto' && error instanceof ApiError && error.status === 501) {
      setUsingMock(true);
      return mock();
    }
    throw error;
  }
}
