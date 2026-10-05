// Prova dos `pattern` dos campos de formulário: o navegador tem de aceitar o
// valor certo.
//
//     node provas/prova_pattern_campos.js
//
// O bug (2026-10-05): o campo Competência da tarefa tinha
// pattern="\\d{2}/\\d{4}". Em atributo JSX entre aspas a barra invertida NÃO é
// escape: o navegador recebia `\\d`, que exige uma barra invertida literal, e
// recusava "09/2026" com "Corresponda ao formato solicitado". Toda tarefa com
// competência ficava impossível de salvar, inclusive para mudar o prazo interno.
//
// A prova lê o atributo como o navegador lê (texto cru entre aspas) e compila
// do mesmo jeito: ancorado e com a flag `v`, que é a dos navegadores atuais.

import assert from 'node:assert';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = fileURLToPath(new URL('../src/', import.meta.url));
const arquivos = (dir) => readdirSync(dir).flatMap((nome) => {
  const c = join(dir, nome);
  if (statSync(c).isDirectory()) return arquivos(c);
  return /\.jsx$/.test(nome) ? [c] : [];
});

const comoNavegador = (p) => new RegExp(`^(?:${p})$`, 'v');

let n = 0;
const ok = (t) => { n += 1; console.log(`ok ${n}. ${t}`); };

// 1. Nenhum pattern em JSX com barra invertida dobrada (a forma do bug).
const patterns = [];
for (const f of arquivos(RAIZ)) {
  const texto = readFileSync(f, 'utf8');
  for (const m of texto.matchAll(/pattern="([^"]*)"/g)) patterns.push({ f, p: m[1] });
}
{
  const dobrados = patterns.filter(({ p }) => p.includes('\\\\'));
  assert.deepStrictEqual(dobrados.map((x) => x.p), [], 'pattern com \\\\ recusa tudo no navegador');
  ok(`nenhum pattern com barra invertida dobrada (${patterns.length} no total)`);
}

// 2. Todo pattern compila como o navegador compila.
{
  for (const { f, p } of patterns) assert.doesNotThrow(() => comoNavegador(p), `${f}: ${p}`);
  ok('todos compilam com a flag v');
}

// 3. O campo Competência da tarefa aceita MM/AAAA e recusa o resto.
{
  const tarefas = readFileSync(join(RAIZ, 'pages', 'Tarefas.jsx'), 'utf8');
  const m = tarefas.match(/value=\{formData\.competencia\}[\s\S]{0,300}?pattern="([^"]*)"/);
  assert.ok(m, 'campo de competência com pattern');
  const re = comoNavegador(m[1]);
  for (const bom of ['09/2026', '01/2025', '12/2030']) assert.ok(re.test(bom), `devia aceitar ${bom}`);
  for (const ruim of ['9/2026', '13/2026', '00/2026', '09-2026', '092026', '09/26']) {
    assert.ok(!re.test(ruim), `devia recusar ${ruim}`);
  }
  ok('Competência aceita 09/2026 e recusa 13/2026, 9/2026 e 09-2026');
}

console.log(`\nPROVA OK: ${n} checagens verdes`);
