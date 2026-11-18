// Comprueba que no haya colores, radios ni familias tipográficas escritos a mano fuera de
// src/ui/theme.ts, y que la biblioteca de iconos sólo se importe en src/ui/Icon.tsx (#23).
// Uso: npm run check:tokens. Lo ejecuta el CI.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const THEME = 'src/ui/theme.ts';
const ICON = 'src/ui/Icon.tsx';
// Código generado a partir del contrato: no contiene estilos.
const IGNORED_DIRS = new Set(['src/api']);

const RULES = [
  { name: 'color hexadecimal', re: /['"`]#[0-9a-fA-F]{3,8}['"`]/ },
  { name: 'color rgb()/hsl()', re: /\b(?:rgba?|hsla?)\(/ },
  { name: 'color con nombre', re: /\b\w*[cC]olor\s*[:=]\s*\{?\s*['"](?!transparent['"])[a-zA-Z]+['"]/ },
  { name: 'radio numérico', re: /\w*[rR]adius\s*:\s*-?\d/ },
  { name: 'familia tipográfica', re: /fontFamily\s*:\s*['"`]/ },
];

function* sourceFiles(dir) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const rel = relative(root, full).split(sep).join('/');
    if (statSync(full).isDirectory()) {
      if (!IGNORED_DIRS.has(rel)) yield* sourceFiles(full);
    } else if (/\.(jsx?|tsx?)$/.test(entry) && !entry.endsWith('.d.ts')) {
      yield rel;
    }
  }
}

const files = ['App.js', ...sourceFiles(join(root, 'src'))];
const problems = [];
for (const file of files) {
  const lines = readFileSync(join(root, file), 'utf8').split('\n');
  lines.forEach((line, i) => {
    if (/^\s*(\/\/|\*|\/\*)/.test(line)) return; // comentarios
    if (file !== THEME) {
      for (const rule of RULES) {
        if (rule.re.test(line)) problems.push(`${file}:${i + 1}: ${rule.name} fuera de ${THEME}: ${line.trim()}`);
      }
    }
    if (file !== ICON && /from\s+['"]lucide-react-native['"]/.test(line)) {
      problems.push(`${file}:${i + 1}: importa lucide-react-native directamente; usa <Icon> de ${ICON}.`);
    }
  });
}

if (problems.length) {
  console.error(problems.join('\n'));
  console.error(`\n${problems.length} problema(s). Usa los tokens de ${THEME}.`);
  process.exit(1);
}
console.log(`Tokens de diseño: ${files.length} ficheros sin valores escritos a mano.`);
