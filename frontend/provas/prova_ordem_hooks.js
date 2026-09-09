// Prova de ordem de declaração nos componentes — Node puro, sem build.
//   node frontend/provas/prova_ordem_hooks.js
//
// O que ela pega: dependência de useEffect, useMemo ou useCallback que aparece
// ANTES do `const` que a cria. O array de dependências é avaliado no corpo do
// render, então a variável cai na zona morta do `let`/`const` e o React nem
// chega a montar: `ReferenceError: Cannot access 'X' before initialization`,
// tela branca ao abrir o menu. Foi o que derrubou a tela de Empresas em
// 2026-09-09, e build não pega, porque compila igual.

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const RAIZ = new URL('../src/', import.meta.url).pathname;

const arquivos = (dir) => readdirSync(dir).flatMap((nome) => {
  const caminho = join(dir, nome);
  if (statSync(caminho).isDirectory()) return arquivos(caminho);
  return /\.jsx?$/.test(nome) ? [caminho] : [];
});

const nascimentos = (linhas) => {
  const onde = {};
  linhas.forEach((linha, i) => {
    const m = linha.match(/^\s*const \[(\w+)(?:,\s*(\w+))?\]/) || linha.match(/^\s*const (\w+)\s*=/);
    if (!m) return;
    for (const nome of m.slice(1)) if (nome && !(nome in onde)) onde[nome] = i + 1;
  });
  return onde;
};

let achados = 0;
for (const caminho of arquivos(RAIZ)) {
  const texto = readFileSync(caminho, 'utf8');
  const onde = nascimentos(texto.split('\n'));
  for (const m of texto.matchAll(/\}\s*,\s*\[([^\]]*)\]\s*\)/g)) {
    const linha = texto.slice(0, m.index).split('\n').length;
    for (const dep of m[1].match(/\w+/g) || []) {
      if (onde[dep] && onde[dep] > linha) {
        achados++;
        console.log(`FALHA  ${caminho.replace(RAIZ, 'src/')}:${linha} usa '${dep}', que só nasce na linha ${onde[dep]}`);
      }
    }
  }
}

if (achados) {
  console.log(`\n${achados} dependência(s) usada(s) antes de existir. A tela quebra ao abrir.`);
  process.exit(1);
}
console.log('  ok  nenhuma dependência de hook é usada antes da declaração que a cria');
