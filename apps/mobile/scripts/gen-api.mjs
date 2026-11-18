// Genera el cliente tipado a partir del contrato de la API (apps/api/openapi.json):
//  - src/api/schema.d.ts: tipos de paths y schemas (openapi-typescript).
//  - src/api/contractExamples.generated.ts: los `examples` del contrato, que se usan como
//    datos de prueba mientras el backend responda 501.
// Uso: npm run gen:api. El CI comprueba que los ficheros generados están al día.
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import openapiTS, { astToString } from 'openapi-typescript';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specPath = resolve(root, '../api/openapi.json');
const spec = JSON.parse(readFileSync(specPath, 'utf8'));

const HEADER = '// Generado por scripts/gen-api.mjs a partir de apps/api/openapi.json. No editar a mano.\n';

const ast = await openapiTS(pathToFileURL(specPath), { alphabetize: true });
writeFileSync(resolve(root, 'src/api/schema.d.ts'), HEADER + astToString(ast));

const examples = {};
for (const [name, schema] of Object.entries(spec.components?.schemas ?? {}).sort(([a], [b]) => a.localeCompare(b))) {
  if (Array.isArray(schema.examples) && schema.examples.length > 0) examples[name] = schema.examples;
}
const body =
  HEADER +
  '/* eslint-disable */\n' +
  '// Los ejemplos se exportan sin tipar: algunos omiten campos nulos (p. ej. `high` en la última zona),\n' +
  '// así que la capa de mock los normaliza antes de usarlos.\n' +
  `export const contractExamples: Record<string, unknown[]> = ${JSON.stringify(examples, null, 2)};\n`;
writeFileSync(resolve(root, 'src/api/contractExamples.generated.ts'), body);
console.log(`Tipos y ${Object.keys(examples).length} ejemplos generados desde ${specPath}`);
