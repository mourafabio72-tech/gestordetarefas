// Prova de frontend/src/pages/filtroDocumentos.js — Node puro, sem build.
//   node frontend/provas/prova_filtro_documentos.js

import { filtrosVazios, paraConsulta, temFiltroAtivo, periodos, dataBr, dataHoraBr, paraCSV }
  from '../src/pages/filtroDocumentos.js';

let ok = 0, falhou = 0;
const eq = (nome, obtido, esperado) => {
  const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
  if (a === b) { ok++; console.log(`  ok  ${nome}`); }
  else { falhou++; console.log(`FALHA  ${nome}\n       obtido:   ${a}\n       esperado: ${b}`); }
};

console.log('\n1) Campo vazio não vira parâmetro — é o que devolve 422');
// `tipo` sempre acompanha: é o acervo que se está olhando, não um filtro.
eq('só o acervo, nada mais', paraConsulta(filtrosVazios()), { tipo: 'recebidos' });
eq('só o que tem valor', paraConsulta({ ...filtrosVazios(), empresa_id: '7', texto: '' }),
   { tipo: 'recebidos', empresa_id: '7' });
eq('espaço em branco não conta', paraConsulta({ ...filtrosVazios(), texto: '   ' }), { tipo: 'recebidos' });
eq('texto é aparado', paraConsulta({ ...filtrosVazios(), texto: '  darf ' }),
   { tipo: 'recebidos', texto: 'darf' });
eq('zero é valor legítimo, não vazio', paraConsulta({ usuario_id: 0 }), { usuario_id: 0 });
eq('limite entra quando pedido', paraConsulta({}, 500), { limite: 500 });
eq('entrada nula não quebra', paraConsulta(null), {});

console.log('\n2) Saber se há filtro comanda o limpar e o aviso de corte');
eq('vazio não tem filtro', temFiltroAtivo(filtrosVazios()), false);
eq('um campo já conta', temFiltroAtivo({ ...filtrosVazios(), competencia: '07/2026' }), true);
// `tipo` escolhe o acervo, não filtra dentro dele: contá-lo faria o "Limpar"
// aparecer sempre, e limpar não pode trocar de acervo debaixo de quem olha.
eq('trocar de acervo não conta como filtro', temFiltroAtivo(filtrosVazios('entregues')), false);
eq('mas vai para a consulta', paraConsulta(filtrosVazios('entregues')), { tipo: 'entregues' });
eq('só não baixados', paraConsulta({ ...filtrosVazios('entregues'), baixado: 'nao' }),
   { tipo: 'entregues', baixado: 'nao' });

console.log('\n3) Períodos de entrega');
const p = periodos(new Date(2026, 8, 17));            // 17/09/2026
eq('este mês', [p[0].de, p[0].ate], ['2026-09-01', '2026-09-30']);
eq('mês passado', [p[1].de, p[1].ate], ['2026-08-01', '2026-08-31']);
eq('este ano', [p[2].de, p[2].ate], ['2026-01-01', '2026-12-31']);
const v = periodos(new Date(2026, 0, 15));
eq('em janeiro, o mês passado é dezembro do ano anterior',
   [v[1].de, v[1].ate], ['2025-12-01', '2025-12-31']);

console.log('\n4) Data sem passar por new Date, que jogaria para o dia anterior');
eq('ISO com hora', dataBr('2026-09-14T21:00:00'), '14/09/2026');
eq('ISO puro', dataBr('2026-09-14'), '14/09/2026');
eq('vazio e nulo', [dataBr(''), dataBr(null), dataBr('xx')], ['', '', '']);

console.log('\n4b) Hora do servidor no fuso de quem lê');
// O backend grava em UTC. Sem o "Z", o JavaScript lê a string como hora local
// e a hora do acesso aparecia 3 horas adiantada.
const emBrasilia = (iso) => {
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
};
eq('ISO sem fuso é tratado como UTC', dataHoraBr('2026-08-23T18:16:00'), emBrasilia('2026-08-23T18:16:00'));
eq('ISO com Z dá o mesmo resultado', dataHoraBr('2026-08-23T18:16:00Z'), emBrasilia('2026-08-23T18:16:00'));
eq('ISO com offset explícito é respeitado',
   dataHoraBr('2026-08-23T15:16:00-03:00'), emBrasilia('2026-08-23T18:16:00'));
eq('as três formas do mesmo instante viram a mesma hora',
   new Set([dataHoraBr('2026-08-23T18:16:00'), dataHoraBr('2026-08-23T18:16:00Z'),
            dataHoraBr('2026-08-23T15:16:00-03:00')]).size, 1);
eq('vazio e lixo não quebram', [dataHoraBr(''), dataHoraBr(null), dataHoraBr('abacaxi')], ['', '', '']);

console.log('\n5) CSV para entregar a um auditor');
const csv = paraCSV([{ empresa: 'Alfa, Beta Ltda', obrigacao: 'DARF', titulo: 'T',
                       competencia: '07/2026', data_entrega: '2026-09-14T10:00:00',
                       protocolo: 'ABC "123"', responsaveis: ['Ana', 'Bia'],
                       arquivo: 'darf.pdf', no_volume: true }]);
const linhas = csv.split('\n');
eq('tem cabeçalho e uma linha', linhas.length, 2);
eq('razão social com vírgula não parte a coluna',
   linhas[1].startsWith('"Alfa, Beta Ltda"'), true);
eq('aspas do protocolo são escapadas', linhas[1].includes('"ABC ""123"""'), true);
eq('responsáveis juntos numa célula', linhas[1].includes('"Ana / Bia"'), true);
eq('data em formato brasileiro', linhas[1].includes('"14/09/2026"'), true);
eq('arquivo fora do volume é marcado', paraCSV([{ no_volume: false }]).includes('"NÃO"'), true);
// No acervo de entregues as colunas mudam: o que interessa é se o cliente pegou.
const csvE = paraCSV([{ empresa: 'X', downloads: 0, baixado_em: null, arquivo: 'g.pdf' }], 'entregues');
eq('coluna de download no lugar do protocolo', csvE.split('\n')[0].includes('"Downloads"'), true);
eq('quem não pegou aparece dito', csvE.split('\n')[1].includes('"não baixou"'), true);
eq('lista vazia devolve só o cabeçalho', paraCSV([]).split('\n').length, 1);
eq('nula não quebra', paraCSV(null).split('\n').length, 1);

console.log(`\n${falhou === 0 ? 'TUDO VERDE' : 'VERMELHO'} — ${ok} ok, ${falhou} falhou\n`);
process.exit(falhou === 0 ? 0 : 1);
