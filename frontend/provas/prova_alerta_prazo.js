// Prova de frontend/src/pages/alertaPrazo.js — Node puro, sem build.
//   node frontend/provas/prova_alerta_prazo.js

import { alertaDaTarefa, fundoDoAlerta, NIVEIS } from '../src/pages/alertaPrazo.js';

let ok = 0, falhou = 0;
const eq = (nome, obtido, esperado) => {
  const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
  if (a === b) { ok++; console.log(`  ok  ${nome}`); }
  else { falhou++; console.log(`FALHA  ${nome}\n       obtido:   ${a}\n       esperado: ${b}`); }
};

// Segunda-feira, 21 de setembro de 2026, meio-dia local.
const HOJE = new Date(2026, 8, 21, 12, 0, 0);
const a = (t) => alertaDaTarefa(t, HOJE);

console.log('\n1) As faixas do semáforo');
eq('venceu ontem -> vermelho', a({ data_prazo: '2026-09-20' }).nivel, 'atrasada');
eq('vence hoje -> laranja', a({ data_prazo: '2026-09-21' }).nivel, 'hoje');
eq('vence amanhã -> amarelo', a({ data_prazo: '2026-09-22' }).nivel, 'proximo');
eq('vence em 7 dias -> ainda amarelo', a({ data_prazo: '2026-09-28' }).nivel, 'proximo');
eq('vence em 8 dias -> verde', a({ data_prazo: '2026-09-29' }).nivel, 'em_dia');

console.log('\n2) O rótulo é a frase que vai no card');
eq('1 dia de atraso no singular', a({ data_prazo: '2026-09-20' }).rotulo, 'atrasada há 1 dia');
eq('3 dias de atraso', a({ data_prazo: '2026-09-18' }).rotulo, 'atrasada há 3 dias');
eq('hoje', a({ data_prazo: '2026-09-21' }).rotulo, 'vence hoje');
eq('amanhã não vira "em 1 dias"', a({ data_prazo: '2026-09-22' }).rotulo, 'vence amanhã');
eq('em 5 dias', a({ data_prazo: '2026-09-26' }).rotulo, 'vence em 5 dias');

console.log('\n3) A contagem é de dia inteiro, não de hora');
eq('ISO com hora, mesmo dia, ainda é hoje', a({ data_prazo: '2026-09-21T23:59:00' }).dias, 0);
eq('ISO com hora zero de amanhã é 1 dia', a({ data_prazo: '2026-09-22T00:00:00' }).dias, 1);

console.log('\n4) Concluída sai do semáforo, mesmo entregue com atraso');
eq('não fica vermelha', a({ data_prazo: '2026-01-10', status: 'concluida' }).nivel, 'concluida');
eq('rótulo próprio', a({ data_prazo: '2026-01-10', status: 'concluida' }).rotulo, 'concluída');
eq('cancelada é neutra', a({ data_prazo: '2026-01-10', status: 'cancelada' }).nivel, 'neutro');

console.log('\n5) Sem prazo interno usa o vencimento; sem nenhum, neutro');
eq('cai no vencimento', a({ data_vencimento: '2026-09-20T00:00:00' }).nivel, 'atrasada');
eq('prazo interno tem precedência',
   a({ data_prazo: '2026-10-30', data_vencimento: '2026-09-01' }).nivel, 'em_dia');
eq('sem data nenhuma', a({}).nivel, 'neutro');
eq('rótulo de quem não tem data', a({}).rotulo, 'sem prazo');
eq('data podre não vira 1970', a({ data_prazo: 'abacaxi' }).nivel, 'neutro');
eq('tarefa nula não quebra', alertaDaTarefa(null, HOJE).nivel, 'neutro');

console.log('\n6) Virada de ano e de mês contam certo');
eq('31/12 para 01/01', alertaDaTarefa({ data_prazo: '2027-01-01' }, new Date(2026, 11, 31, 23, 0)).dias, 1);
eq('atravessa fevereiro', alertaDaTarefa({ data_prazo: '2026-03-01' }, new Date(2026, 1, 27, 8, 0)).dias, 2);

console.log('\n7) O fundo é degradê da cor do nível para o creme');
eq('gradiente do vermelho',
   fundoDoAlerta(a({ data_prazo: '2026-09-20' })),
   `linear-gradient(135deg, ${NIVEIS.atrasada.suave} 0%, #fffdf9 78%)`);

console.log(`\n${falhou === 0 ? 'TUDO VERDE' : 'VERMELHO'} — ${ok} ok, ${falhou} falhou\n`);
process.exit(falhou === 0 ? 0 : 1);
