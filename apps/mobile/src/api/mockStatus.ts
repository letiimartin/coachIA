// Estado observable "se están mostrando datos de prueba", para avisar en pantalla.
import { useSyncExternalStore } from 'react';

let usingMock = false;
const listeners = new Set<() => void>();

export function setUsingMock(value: boolean): void {
  if (usingMock === value) return;
  usingMock = value;
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useUsingMock(): boolean {
  return useSyncExternalStore(subscribe, () => usingMock, () => usingMock);
}
