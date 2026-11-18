/** Número opcional desde un TextInput: '' → null, texto no numérico → NaN. */
export function parseOptionalNumber(text: string): number | null {
  const value = text.trim().replace(',', '.');
  if (!value) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : NaN;
}

export function numberToText(value: number | null | undefined): string {
  return value == null ? '' : String(value);
}

/**
 * FC umbral antigua (anterior al LTHR por disciplina) que aún no se ha asignado: existe y no
 * coincide con la de ciclismo ni con la de carrera. Es sólo informativa; la asignación se hace
 * en la API con autorización de la autora, nunca desde la app.
 */
export function unassignedLegacyLthr(t: {
  legacy_lthr_bpm: number | null;
  cycling_lthr_bpm: number | null;
  running_lthr_bpm: number | null;
}): number | null {
  const legacy = t.legacy_lthr_bpm;
  if (legacy == null || legacy === t.cycling_lthr_bpm || legacy === t.running_lthr_bpm) return null;
  return legacy;
}
