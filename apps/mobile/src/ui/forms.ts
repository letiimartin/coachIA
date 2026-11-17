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
