// Prova de frontend/src/pages/lotesModelos.js — Node puro, sem build.
//   node frontend/provas/prova_lotes_modelos.js

import { separarAceitos, emRemessas, juntarResultados, POR_REMESSA }
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

console.log(`\n${falhou === 0 ? 'TUDO VERDE' : 'VERMELHO'} — ${ok} ok, ${falhou} falhou\n`);
process.exit(falhou === 0 ? 0 : 1);
