/** Integraciones (Wahoo). Endpoints ya implementados en la API; sin `examples` en el contrato. */
import { apiConfig } from './config';
import { ApiError } from './errors';
import { request, withMock } from './http';
import type { IntegrationOut, SyncOut } from './types';

const notInMock = () =>
  Promise.reject(
    new ApiError(0, 'mock_unavailable', 'Conectar y sincronizar Wahoo necesita la API real (desactiva EXPO_PUBLIC_API_MOCK).'),
  );

export const integrationsApi = {
  /** En modo de datos de prueba no hay integraciones conectadas. */
  list: () =>
    withMock(
      () => request<IntegrationOut[]>('GET', '/v1/integrations'),
      () => Promise.resolve([] as IntegrationOut[]),
    ),

  wahooAuthorizeUrl: (platform: 'mobile' | 'web') =>
    withMock(
      () => request<{ authorize_url: string }>('GET', '/v1/integrations/wahoo/authorize-url', { query: { platform } }),
      notInMock,
    ),

  wahooSync: () => withMock(() => request<SyncOut>('POST', '/v1/integrations/wahoo/sync'), notInMock),

  wahooDisconnect: () => withMock(() => request<void>('DELETE', '/v1/integrations/wahoo'), notInMock),
};

export const integrationsAvailable = () => apiConfig.mockMode !== 'on' && !!apiConfig.baseUrl;
