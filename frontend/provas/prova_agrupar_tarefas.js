// Prova de frontend/src/pages/agruparTarefas.js — Node puro, sem build.
//   node frontend/provas/prova_agrupar_tarefas.js

import { agruparTarefas, AGRUPAMENTOS, GRUPO_UNICO, SEM_GRUPO } from '../src/pages/agruparTarefas.js';

let ok = 0, falhou = 0;
const eq = (nome, obtido, esperado) => {
  const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
  if (a === b) { ok++; console.log(`  ok  ${nome}`); }
  else { falhou++; console.log(`FALHA  ${nome}\n       obtido:   ${a}\n       esperado: ${b}`); }
};

const nomes = {
  empresa: (id) => ({ 1: 'Mark Building', 2: 'Alpha Serviços', 3: 'TROPS' }[id] || ''),
  setor: (id) => ({ 10: 'Fiscal', 20: 'Contabilidade' }[id] || ''),
};

const T = [
  { id: 1, titulo: 'SPED', empresa_id: 3, setor_id: 10 },
  { id: 2, titulo: 'Balancete', empresa_id: 1, setor_id: 20 },
  { id: 3, titulo: 'DARF', empresa_id: 1, setor_id: 10 },
  { id: 4, titulo: 'Avulsa', empresa_id: 2, setor_id: null },
];

console.log('\n1) Sem modo, um grupo só com tudo dentro');
const plano = agruparTarefas(T, '', nomes);
eq('um grupo', plano.length, 1);
eq('chave do grupo único', plano[0].chave, GRUPO_UNICO);
eq('sem título', plano[0].titulo, '');
eq('todas as tarefas', plano[0].tarefas.length, 4);

console.log('\n2) Por empresa, em ordem alfabética de razão social');
const porEmp = agruparTarefas(T, 'empresa', nomes);
eq('títulos ordenados', porEmp.map(g => g.titulo), ['Alpha Serviços', 'Mark Building', 'TROPS']);
eq('Mark Building junta as duas', porEmp[1].tarefas.map(t => t.id), [2, 3]);

console.log('\n3) Ordem dentro do grupo é preservada (o backend manda por prazo)');
const prazos = [
  { id: 9, empresa_id: 1, data_prazo: '2026-09-05' },
  { id: 8, empresa_id: 1, data_prazo: '2026-09-14' },
  { id: 7, empresa_id: 1, data_prazo: '2026-09-20' },
];
eq('não reordena', agruparTarefas(prazos, 'empresa', nomes)[0].tarefas.map(t => t.id), [9, 8, 7]);

console.log('\n4) Por setor, e o sem setor cai em "Sem classificação" no fim');
const porSet = agruparTarefas(T, 'setor', nomes);
eq('ordem com o sem-grupo por último', porSet.map(g => g.titulo), ['Contabilidade', 'Fiscal', SEM_GRUPO]);
eq('a avulsa está no último', porSet[2].tarefas.map(t => t.id), [4]);

console.log('\n5) Razão social igual em ids diferentes não funde os grupos');
const homonimas = [
  { id: 1, empresa_id: 5 },
  { id: 2, empresa_id: 6 },
];
const iguais = agruparTarefas(homonimas, 'empresa', { empresa: () => 'Holding Participações' });
eq('dois grupos, não um', iguais.length, 2);

console.log('\n6) Empresa que sumiu do cadastro não deixa cabeçalho vazio');
eq('cai em Sem classificação',
   agruparTarefas([{ id: 1, empresa_id: 99 }], 'empresa', nomes)[0].titulo, SEM_GRUPO);

console.log('\n7) Lista vazia e entrada nula não quebram');
eq('vazia agrupada', agruparTarefas([], 'empresa', nomes), []);
eq('nula sem modo', agruparTarefas(null, '', nomes)[0].tarefas, []);

console.log('\n8) O seletor oferece as três opções, com "não agrupar" por último');
eq('valores', AGRUPAMENTOS.map(a => a.valor), ['empresa', 'setor', '']);

console.log(`\n${falhou === 0 ? 'TUDO VERDE' : 'VERMELHO'} — ${ok} ok, ${falhou} falhou\n`);
process.exit(falhou === 0 ? 0 : 1);
