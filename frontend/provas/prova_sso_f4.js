// Prova da Fase 4: a leitura do bilhete na URL.
//
// Roda em Node puro, sem navegador e sem build:
//     node provas/prova_sso_f4.js
//
// `colherBilhete` recebe location e history como parâmetro justamente para isto:
// aqui eles são objetos de mentira, e o que se confere é o endereço com que o
// replaceState foi chamado.

import assert from 'node:assert';
import { colherBilhete } from '../src/contexts/bilhete.js';

let n = 0;
function ok(titulo) {
  n += 1;
  console.log(`ok ${n}. ${titulo}`);
}

// Fabrica um par location/history de mentira, guardando o endereço reescrito.
function cenario(url) {
  const u = new URL(url, 'https://gestordetarefas.zoaria.com.br');
  const chamadas = [];
  return {
    location: { search: u.search, pathname: u.pathname, hash: u.hash },
    history: { replaceState: (_e, _t, endereco) => chamadas.push(endereco) },
    chamadas,
  };
}

// 1. PROVA POSITIVA. Sem ela, uma função que devolvesse null sempre passaria em
// todos os outros itens parecendo correta.
{
  const c = cenario('/?sso=abc123');
  assert.strictEqual(colherBilhete(c.location, c.history), 'abc123');
  ok('bilhete presente na URL é devolvido');
}

// 2. O caminho normal de quem entra digitando o endereço não pode ser tocado.
{
  const c = cenario('/tarefas');
  assert.strictEqual(colherBilhete(c.location, c.history), null);
  assert.strictEqual(c.chamadas.length, 0, 'URL sem bilhete não deve ser reescrita');
  ok('URL sem bilhete devolve null e não é reescrita');
}

// 3. A regra da nota de impersonação: o bilhete não fica na barra.
{
  const c = cenario('/?sso=abc123');
  colherBilhete(c.location, c.history);
  assert.strictEqual(c.chamadas.length, 1);
  assert.ok(!c.chamadas[0].includes('sso'), `endereço ainda tem o bilhete: ${c.chamadas[0]}`);
  assert.strictEqual(c.chamadas[0], '/');
  ok('a URL é limpa e o bilhete some do endereço');
}

// 4. Limpar não pode levar junto o que não é do SSO.
{
  const c = cenario('/tarefas?empresa=3&sso=abc123&setor=7#lista');
  assert.strictEqual(colherBilhete(c.location, c.history), 'abc123');
  assert.strictEqual(c.chamadas[0], '/tarefas?empresa=3&setor=7#lista');
  ok('outros parâmetros e o hash sobrevivem à limpeza');
}

// 5. `?sso=` sem valor não é bilhete, e mesmo assim não fica sujando a barra.
{
  const c = cenario('/?sso=');
  assert.strictEqual(colherBilhete(c.location, c.history), null);
  assert.strictEqual(c.chamadas[0], '/');
  ok('parâmetro vazio devolve null e a URL é limpa do mesmo jeito');
}

// 6. O bilhete do itsdangerous carrega ponto e traço, e a URL pode trazer valor
// codificado. Quem chega ao servidor tem de ser o valor original.
{
  const bilhete = 'eyJlbWFpbCI6ICJhQGIuYyJ9.aK9x-Q.abc_DEF-123';
  const c = cenario('/?sso=' + encodeURIComponent(bilhete));
  assert.strictEqual(colherBilhete(c.location, c.history), bilhete);
  ok('bilhete codificado na URL volta decodificado');
}

// 7. Bilhete que chega numa rota interna funciona igual, e a rota é preservada.
{
  const c = cenario('/tarefas?sso=abc123');
  assert.strictEqual(colherBilhete(c.location, c.history), 'abc123');
  assert.strictEqual(c.chamadas[0], '/tarefas');
  ok('bilhete em rota interna é lido e a rota é preservada');
}

console.log(`\nPROVA OK: ${n} casos`);
