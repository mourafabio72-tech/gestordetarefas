// Prova de frontend/src/pages/filtroModelos.js — Node puro, sem build.
//   node frontend/provas/prova_filtro_modelos.js

import { filtrosVazios, temFiltroAtivo, filtrarModelos, valoresDe }
  from '../src/pages/filtroModelos.js';

let ok = 0, falhou = 0;
const eq = (nome, obtido, esperado) => {
  if (JSON.stringify(obtido) === JSON.stringify(esperado)) { ok++; console.log(`  ok  ${nome}`); }
  else { falhou++; console.log(`FALHA  ${nome}\n       obtido:   ${JSON.stringify(obtido)}\n       esperado: ${JSON.stringify(esperado)}`); }
};

const MODELOS = [
  { id: 1, nome_arquivo: 'a.pdf', empresa_nome: 'Mark Building', tipo_documento: 'guia',
    obrigacao_nome: 'apuracao_ipi', identificador: 'IPI 5123' },
  { id: 2, nome_arquivo: 'b.pdf', empresa_nome: 'TROPS', tipo_documento: 'guia',
    obrigacao_nome: 'apuracao_ipi', identificador: 'IPI - DEMAIS' },
  { id: 3, nome_arquivo: 'c.pdf', empresa_nome: 'Mark Building', tipo_documento: 'declaracao',
    obrigacao_nome: 'apuracao_ipi_extra', identificador: 'ECF 2025' },
  { id: 4, nome_arquivo: 'd.pdf', empresa_nome: 'TROPS', tipo_documento: 'relatorio',
    obrigacao_nome: null, identificador: null },
];
const ids = (f) => filtrarModelos(MODELOS, f).map((m) => m.id);

console.log('\n1) Sem filtro, tudo passa');
eq('lista inteira', ids(filtrosVazios()), [1, 2, 3, 4]);
eq('não tem filtro ativo', temFiltroAtivo(filtrosVazios()), false);
eq('um campo já conta', temFiltroAtivo({ ...filtrosVazios(), tipo: 'guia' }), true);

console.log('\n2) Empresa, tipo e obrigação casam por igualdade');
eq('empresa', ids({ ...filtrosVazios(), empresa: 'TROPS' }), [2, 4]);
eq('tipo', ids({ ...filtrosVazios(), tipo: 'guia' }), [1, 2]);
eq('obrigação', ids({ ...filtrosVazios(), obrigacao: 'apuracao_ipi' }), [1, 2]);
// Igualdade, não trecho: escolher "apuracao_ipi" não pode trazer "apuracao_ipi_extra".
eq('obrigação parecida NÃO entra', ids({ ...filtrosVazios(), obrigacao: 'apuracao_ipi' }).includes(3), false);

console.log('\n3) Identificador casa por trecho');
eq('parte do texto', ids({ ...filtrosVazios(), identificador: 'ipi' }), [1, 2]);
eq('sem acento e sem caixa', ids({ ...filtrosVazios(), identificador: 'DEMAIS' }), [2]);
eq('quem não tem identificador some', ids({ ...filtrosVazios(), identificador: 'x' }), []);
eq('espaço em volta é aparado', ids({ ...filtrosVazios(), identificador: '  ecf ' }), [3]);

console.log('\n4) Filtros somam');
eq('empresa + tipo', ids({ ...filtrosVazios(), empresa: 'Mark Building', tipo: 'guia' }), [1]);
eq('combinação sem resultado', ids({ ...filtrosVazios(), empresa: 'TROPS', tipo: 'declaracao' }), []);

console.log('\n5) Os selects só oferecem o que existe');
eq('empresas', valoresDe(MODELOS, 'empresa_nome'), ['Mark Building', 'TROPS']);
eq('tipos', valoresDe(MODELOS, 'tipo_documento'), ['declaracao', 'guia', 'relatorio']);
eq('obrigações — o nulo fica de fora', valoresDe(MODELOS, 'obrigacao_nome'),
   ['apuracao_ipi', 'apuracao_ipi_extra']);
eq('lista vazia não quebra', valoresDe([], 'empresa_nome'), []);
eq('nula também', valoresDe(null, 'empresa_nome'), []);

console.log('\n6) Bordas');
eq('modelos nulos', filtrarModelos(null, filtrosVazios()), []);
eq('filtros nulos devolvem tudo', filtrarModelos(MODELOS, null).length, 4);

console.log(`\n${falhou === 0 ? 'TUDO VERDE' : 'VERMELHO'} — ${ok} ok, ${falhou} falhou\n`);
process.exit(falhou === 0 ? 0 : 1);
