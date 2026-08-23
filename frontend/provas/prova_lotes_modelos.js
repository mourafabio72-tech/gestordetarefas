// Prova de frontend/src/pages/lotesModelos.js — Node puro, sem build.
//   node frontend/provas/prova_lotes_modelos.js

import { separarAceitos, emRemessas, juntarResultados, enviarComDivisao, POR_REMESSA }
  from '../src/pages/lotesModelos.js';

let ok = 0, falhou = 0;
const eq = (nome, obtido, esperado) => {
  const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
  if (a === b) { ok++; console.log(`  ok  ${nome}`); }
  else { falhou++; console.log(`FALHA  ${nome}\n       obtido:   ${a}\n       esperado: ${b}`); }
};
const arq = (nome) => ({ name: nome });

console.log('\n1) O que o servidor sabe ler, e o que precisa ser dito');
const { aceitos, recusados } = separarAceitos(
  ['a.pdf', 'b.PDF', 'c.xlsx', 'd.xls', 'e.docx', 'f.png', 'sem-extensao'].map(arq));
eq('aceita pdf, xlsx e xls', aceitos.map((f) => f.name), ['a.pdf', 'b.PDF', 'c.xlsx', 'd.xls']);
eq('maiúscula na extensão não atrapalha', aceitos.some((f) => f.name === 'b.PDF'), true);
eq('o resto volta para ser AVISADO, não descartado calado',
   recusados.map((f) => f.name), ['e.docx', 'f.png', 'sem-extensao']);
eq('lista vazia não quebra', separarAceitos([]).aceitos, []);
eq('nula também', separarAceitos(null).recusados, []);

console.log('\n2) Remessas — 36 numa requisição não chegam ao servidor');
const trintaESeis = Array.from({ length: 36 }, (_, i) => arq(`d${i}.pdf`));
const remessas = emRemessas(trintaESeis);
eq('divide em grupos do tamanho certo', remessas.length, Math.ceil(36 / POR_REMESSA));
eq('nenhum grupo passa do limite', remessas.every((r) => r.length <= POR_REMESSA), true);
eq('nenhum arquivo se perde no caminho',
   remessas.reduce((n, r) => n + r.length, 0), 36);
eq('o último grupo leva o resto', remessas[remessas.length - 1].length, 36 % POR_REMESSA || POR_REMESSA);
eq('lista menor que a remessa vira um grupo só', emRemessas([arq('x.pdf')]).length, 1);
eq('lista vazia não vira remessa nenhuma', emRemessas([]).length, 0);

console.log('\n3) Somar as respostas como se fosse uma chamada só');
const juntou = juntarResultados([
  { total: 5, resultado: { resumo: { total: 5 }, salvos: [{ id: 1 }, { id: 2 }], revisar: [{ nome_arquivo: 'c.pdf' }] } },
  { total: 5, resultado: { resumo: { total: 5 }, salvos: [{ id: 3 }], revisar: [] } },
]);
eq('soma os salvos', juntou.salvos.length, 3);
eq('soma os que precisam de revisão', juntou.revisar.length, 1);
eq('e o total', juntou.resumo.total, 10);

console.log('\n4) Remessa que falhou inteira não pode evaporar');
const comFalha = juntarResultados([
  // Remessa que respondeu: 2 arquivos, 1 salvo e 1 para revisar.
  { total: 2, resultado: { resumo: { total: 2 }, salvos: [{ id: 1 }], revisar: [{ nome_arquivo: 'a.pdf' }] } },
  // Remessa que nem chegou ao servidor.
  { total: 3, erro: 'Erro 413: arquivo grande demais', nomes: ['x.pdf', 'y.pdf', 'z.pdf'] },
]);
eq('o total conta os que foram enviados', comFalha.resumo.total, 5);
eq('cada arquivo da remessa perdida vira uma linha', comFalha.revisar.length, 4);
eq('com o motivo em cada uma das perdidas',
   comFalha.revisar.filter((r) => r.erro).every((r) => r.erro.includes('413')), true);
eq('e o nome do arquivo, para saber qual refazer',
   comFalha.revisar.filter((r) => r.erro).map((r) => r.nome_arquivo), ['x.pdf', 'y.pdf', 'z.pdf']);
eq('a conta fecha: salvos + revisar = total',
   comFalha.resumo.salvos + comFalha.resumo.revisar, comFalha.resumo.total);
eq('lista vazia devolve resumo zerado', juntarResultados([]).resumo, { total: 0, salvos: 0, revisar: 0 });

console.log('\n5) Remessa que falha se divide e tenta de novo');
// O limite que derruba a requisição depende dos arquivos: cinco planilhas
// pesadas estouram onde cinco PDFs pequenos passam. Dividir na falha encontra
// o tamanho que passa sem punir o caso comum.
const cinco = ['a', 'b', 'c', 'd', 'e'].map(arq);
let chamadas = [];

// Servidor que só aceita remessas de até 2.
const ate2 = async (lista) => {
  chamadas.push(lista.length);
  if (lista.length > 2) throw new Error('413');
  return { resumo: { total: lista.length }, salvos: lista.map((f) => ({ id: f.name })), revisar: [] };
};
let andou = 0;
let partes = await enviarComDivisao(cinco, ate2, (n) => { andou += n; });
let juntas = juntarResultados(partes);
eq('todos acabam entrando', juntas.salvos.length, 5);
eq('nenhum vira erro', juntas.revisar.length, 0);
eq('a barra andou o total', andou, 5);
eq('tentou o grupo grande antes de dividir', chamadas[0], 5);
eq('e nenhuma chamada que passou tinha mais de 2',
   chamadas.filter((n) => n <= 2).length > 0, true);

// Servidor que recusa SEMPRE: a divisão para no arquivo sozinho.
chamadas = [];
const sempreFalha = async (lista) => { chamadas.push(lista.length); throw new Error('500'); };
partes = await enviarComDivisao(cinco, sempreFalha, () => {});
juntas = juntarResultados(partes);
eq('cada arquivo vira uma linha de erro', juntas.revisar.length, 5);
eq('com o nome de cada um',
   juntas.revisar.map((r) => r.nome_arquivo).sort(), ['a', 'b', 'c', 'd', 'e']);
eq('não insiste depois de chegar a um arquivo',
   chamadas.filter((n) => n === 1).length, 5);

// Tudo funcionando: uma chamada só, sem divisão.
chamadas = [];
const sempreOk = async (lista) => {
  chamadas.push(lista.length);
  return { resumo: { total: lista.length }, salvos: [], revisar: [] };
};
await enviarComDivisao(cinco, sempreOk, () => {});
eq('caso comum não paga pela retentativa', chamadas, [5]);

console.log(`\n${falhou === 0 ? 'TUDO VERDE' : 'VERMELHO'} — ${ok} ok, ${falhou} falhou\n`);
process.exit(falhou === 0 ? 0 : 1);
