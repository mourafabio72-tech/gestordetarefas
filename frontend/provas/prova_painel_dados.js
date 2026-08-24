// Prova de frontend/src/pages/painelDados.js — Node puro, sem build.
//   node frontend/provas/prova_painel_dados.js

import { percentuais, linhasMapa, diaMes, filtrosVazios, paraConsulta, temFiltroAtivo,
         pontualidade, haQuantosDias, SITUACOES, DIMENSOES }
  from '../src/pages/painelDados.js';

let ok = 0, falhou = 0;
const eq = (nome, obtido, esperado) => {
  if (JSON.stringify(obtido) === JSON.stringify(esperado)) { ok++; console.log(`  ok  ${nome}`); }
  else { falhou++; console.log(`FALHA  ${nome}\n       obtido:   ${JSON.stringify(obtido)}\n       esperado: ${JSON.stringify(esperado)}`); }
};
const soma = (p) => p.reduce((s, x) => s + x.pct, 0);

console.log('\n1) Os percentuais somam 100 — foi o 101% que motivou tudo');
// O painel antigo mostrava 24 + 67 + 0 + 10 = 101.
const p1 = percentuais({ concluida: 5, pendente: 14, em_andamento: 0, atrasada: 2, cancelada: 0 });
eq('soma exata', soma(p1), 100);
const casos = [
  { atrasada: 1, pendente: 1, em_andamento: 1, concluida: 0, cancelada: 0 },   // três terços
  { atrasada: 1, pendente: 2, em_andamento: 0, concluida: 0, cancelada: 0 },
  { atrasada: 7, pendente: 11, em_andamento: 13, concluida: 17, cancelada: 19 },
  { atrasada: 1, pendente: 0, em_andamento: 0, concluida: 0, cancelada: 0 },
];
eq('soma 100 em todos os casos difíceis', casos.map((c) => soma(percentuais(c))), [100, 100, 100, 100]);
eq('a sobra vai para a MAIOR fatia',
   percentuais({ atrasada: 1, pendente: 1, em_andamento: 1, concluida: 0, cancelada: 0 })
     .find((x) => x.pct === 34) !== undefined, true);
eq('tudo zero devolve zero, não NaN', percentuais({}).map((x) => x.pct), [0, 0, 0, 0, 0]);
eq('resumo nulo não quebra', soma(percentuais(null)), 0);
eq('a ordem começa pelo que corre mais', SITUACOES[0].chave, 'atrasada');

console.log('\n2) Heatmap: proporção DENTRO da linha');
const linhas = linhasMapa([
  { nome: 'Fiscal', total: 3, atrasada: 3, pendente: 0, em_andamento: 0, concluida: 0, cancelada: 0 },
  { nome: 'Contab', total: 300, atrasada: 3, pendente: 297, em_andamento: 0, concluida: 0, cancelada: 0 },
]);
const cel = (i, chave) => linhas[i].celulas.find((c) => c.chave === chave);
eq('setor pequeno todo atrasado fica no máximo', cel(0, 'atrasada').intensidade, 1);
eq('setor grande com 3 atrasadas fica fraco', cel(1, 'atrasada').intensidade < 0.2, true);
// Comparar contra o total geral pintaria o Fiscal de cinza e esconderia o pior caso.
eq('mas nunca invisível — 3 em 300 ainda aparece', cel(1, 'atrasada').intensidade >= 0.12, true);
eq('zero é zero mesmo', cel(1, 'concluida').intensidade, 0);
eq('lista vazia não quebra', linhasMapa([]), []);
eq('nula também', linhasMapa(null), []);

console.log('\n3) Data curta sem passar por new Date');
eq('ISO com hora', diaMes('2026-09-14T21:00:00'), '14/09');
eq('ISO puro', diaMes('2026-09-14'), '14/09');
eq('vazio', [diaMes(''), diaMes(null)], ['', '']);

console.log('\n4) Filtros');
eq('vazio não vira parâmetro', paraConsulta(filtrosVazios()), {});
eq('so_multa só entra quando ligado', paraConsulta({ ...filtrosVazios(), so_multa: true }), { so_multa: true });
eq('desligado não entra', paraConsulta({ ...filtrosVazios(), so_multa: false }), {});
eq('texto é aparado', paraConsulta({ competencia: ' 07/2026 ' }), { competencia: '07/2026' });
eq('sem filtro', temFiltroAtivo(filtrosVazios()), false);
eq('com filtro', temFiltroAtivo({ ...filtrosVazios(), setor_id: '3' }), true);

console.log('\n6) Pontualidade — o único número que olha para trás');
// Sem base, devolve null em vez de 0%: "0% no prazo" e "nada concluído ainda"
// são coisas diferentes, e a segunda não é notícia ruim.
eq('sem concluída com prazo, não há índice',
  pontualidade({ concluidas_com_prazo: 0, no_prazo: 0 }), null);
eq('6 de 8 dá 75%', pontualidade({ concluidas_com_prazo: 8, no_prazo: 6 }).pct, 75);
eq('e diz quantas ficaram fora', pontualidade({ concluidas_com_prazo: 8, no_prazo: 6 }).fora, 2);
eq('tudo no prazo dá 100', pontualidade({ concluidas_com_prazo: 3, no_prazo: 3 }).pct, 100);
eq('nada no prazo dá 0', pontualidade({ concluidas_com_prazo: 3, no_prazo: 0 }).pct, 0);
eq('resumo ausente não quebra', pontualidade(undefined), null);

console.log('\n7) Há quantos dias o documento está parado');
const agoraFixo = new Date('2026-08-20T12:00:00Z');
eq('mesmo dia é "hoje"', haQuantosDias('2026-08-20T09:00:00Z', agoraFixo), 'hoje');
eq('um dia é singular', haQuantosDias('2026-08-19T09:00:00Z', agoraFixo), 'há 1 dia');
eq('vários dias é plural', haQuantosDias('2026-08-14T09:00:00Z', agoraFixo), 'há 6 dias');
eq('data vazia não quebra a tela', haQuantosDias(null, agoraFixo), '');
eq('data inválida também não', haQuantosDias('nao-e-data', agoraFixo), '');

console.log('\n8) Dimensões do mapa');
eq('são três, e batem com as chaves da API',
  DIMENSOES.map((d) => d.chave), ['por_setor', 'por_colaborador', 'por_empresa']);

console.log(`\n${falhou === 0 ? 'TUDO VERDE' : 'VERMELHO'} — ${ok} ok, ${falhou} falhou\n`);
process.exit(falhou === 0 ? 0 : 1);
