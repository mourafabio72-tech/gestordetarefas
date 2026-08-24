// Prova do filtro da tela de Tarefas: competência e faixa de vencimento.
//
// Roda em Node puro, sem navegador e sem build:
//     node provas/prova_filtro_tarefas.js

import assert from 'node:assert';
import {
  filtrarTarefas, competenciasDe, presetsVencimento,
  filtrosVazios, temFiltroAtivo, filtrosDaUrl, rotuloDoRecorte,
  SEM_COMPETENCIA,
} from '../src/pages/filtroTarefas.js';

let n = 0;
function ok(titulo) {
  n += 1;
  console.log(`ok ${n}. ${titulo}`);
}

const TAREFAS = [
  { id: 1, empresa_id: 1, setor_id: 1, status: 'pendente',  competencia: '07/2026', data_vencimento: '2026-09-14T00:00:00' },
  { id: 2, empresa_id: 1, setor_id: 2, status: 'concluida', competencia: '07/2026', data_vencimento: '2026-09-20T12:30:00' },
  { id: 3, empresa_id: 2, setor_id: 1, status: 'pendente',  competencia: '08/2026', data_vencimento: '2026-10-10T00:00:00' },
  { id: 4, empresa_id: 2, setor_id: 1, status: 'pendente',  competencia: '12/2025', data_vencimento: '2026-01-20T00:00:00' },
  { id: 5, empresa_id: 1, setor_id: 1, status: 'pendente',  competencia: null,      data_vencimento: null },
];

// Conjunto próprio para título e pessoa, para não deslocar as contagens acima.
const COM_GENTE = [
  { id: 6, empresa_id: 1, setor_id: 1, status: 'pendente', titulo: 'balancete teste',
    responsaveis: [{ id: 7, nome: 'Ana' }] },
  { id: 7, empresa_id: 2, setor_id: 1, status: 'pendente', titulo: 'conciliar banco',
    responsaveis: [{ id: 7, nome: 'Ana' }, { id: 8, nome: 'Bia' }],
    supervisor: { id: 9, nome: 'Carlos' } },
  { id: 8, empresa_id: 2, setor_id: 1, status: 'pendente', titulo: 'lançar notas',
    responsaveis: [] },
];
const ids = (lista) => lista.map(t => t.id);

// 1. PROVA POSITIVA. Sem ela, um filtro que devolvesse [] passaria no resto.
{
  const r = filtrarTarefas(TAREFAS, filtrosVazios());
  assert.deepStrictEqual(ids(r), [1, 2, 3, 4, 5]);
  ok('sem filtro nenhum, vêm todas');
}

// 2. Competência.
{
  const r = filtrarTarefas(TAREFAS, { ...filtrosVazios(), competencia: '07/2026' });
  assert.deepStrictEqual(ids(r), [1, 2]);
  ok('competência 07/2026 traz só as do fato gerador de julho');
}

// 3. As avulsas, que não têm competência, têm entrada própria.
{
  const r = filtrarTarefas(TAREFAS, { ...filtrosVazios(), competencia: SEM_COMPETENCIA });
  assert.deepStrictEqual(ids(r), [5]);
  ok('"sem competência" traz as avulsas');
}

// 4. Faixa de vencimento, inclusiva nas duas pontas.
{
  const r = filtrarTarefas(TAREFAS, { ...filtrosVazios(), venc_de: '2026-09-14', venc_ate: '2026-09-20' });
  assert.deepStrictEqual(ids(r), [1, 2]);
  ok('faixa de vencimento inclui os dois extremos');
}

// 5. O BUG que a comparação por data evita: a tarefa 2 vence 20/09 às 12:30. Se
// a hora entrasse na conta, "até 20/09" (que vira 20/09 00:00) a deixaria fora.
{
  const r = filtrarTarefas(TAREFAS, { ...filtrosVazios(), venc_ate: '2026-09-20' });
  assert.ok(ids(r).includes(2), 'tarefa que vence no próprio dia "até" tem de entrar');
  ok('vencimento com hora não escapa do último dia da faixa');
}

// 6. Só um lado da faixa também filtra.
{
  assert.deepStrictEqual(ids(filtrarTarefas(TAREFAS, { ...filtrosVazios(), venc_de: '2026-10-01' })), [3]);
  assert.deepStrictEqual(ids(filtrarTarefas(TAREFAS, { ...filtrosVazios(), venc_ate: '2026-01-31' })), [4]);
  ok('faixa aberta de um lado só funciona');
}

// 7. Tarefa sem vencimento não pertence a intervalo nenhum.
{
  const r = filtrarTarefas(TAREFAS, { ...filtrosVazios(), venc_de: '2020-01-01', venc_ate: '2030-12-31' });
  assert.ok(!ids(r).includes(5), 'sem data de vencimento não entra em faixa de vencimento');
  ok('tarefa sem vencimento fica fora da faixa, não em toda faixa');
}

// 8. Os filtros se somam, não se substituem.
{
  const r = filtrarTarefas(TAREFAS, {
    ...filtrosVazios(), empresa_id: '1', status: 'pendente', competencia: '07/2026',
  });
  assert.deepStrictEqual(ids(r), [1]);
  ok('empresa + status + competência combinam');
}

// 9. Ordem das competências: 01/2026 é mais recente que 12/2025, e ordenar
// "MM/AAAA" como texto puro inverteria isso.
{
  assert.deepStrictEqual(competenciasDe(TAREFAS), ['08/2026', '07/2026', '12/2025']);
  ok('competências saem da mais recente para a mais antiga, com a virada de ano certa');
}

// 10. Lista vazia e campos ausentes não quebram.
{
  assert.deepStrictEqual(competenciasDe([]), []);
  assert.deepStrictEqual(filtrarTarefas([], filtrosVazios()), []);
  assert.deepStrictEqual(filtrarTarefas(TAREFAS, {}).length, 5);
  ok('lista vazia e filtro ausente não quebram');
}

// 11. Presets, com o dia fixado. 15/09/2026 é uma terça.
{
  const [vencidas, prox7, mes] = presetsVencimento(new Date(2026, 8, 15));
  assert.strictEqual(vencidas.de, '');
  assert.strictEqual(vencidas.ate, '2026-09-14', 'vencida = até ontem');
  assert.strictEqual(prox7.de, '2026-09-15');
  assert.strictEqual(prox7.ate, '2026-09-22');
  assert.strictEqual(mes.de, '2026-09-01');
  assert.strictEqual(mes.ate, '2026-09-30', 'setembro fecha no dia 30');
  ok('atalhos de vencimento calculam as datas certas');
}

// 12. Fevereiro bissexto: o "este mês" tem de fechar em 29.
{
  const [, , mes] = presetsVencimento(new Date(2028, 1, 10));
  assert.strictEqual(mes.ate, '2028-02-29');
  ok('"este mês" acerta o último dia de fevereiro bissexto');
}

// 13. O botão de limpar só aparece quando há o que limpar.
{
  assert.strictEqual(temFiltroAtivo(filtrosVazios()), false);
  assert.strictEqual(temFiltroAtivo({ ...filtrosVazios(), competencia: '07/2026' }), true);
  assert.strictEqual(temFiltroAtivo({ ...filtrosVazios(), venc_ate: '2026-09-20' }), true);
  ok('"limpar filtros" só aparece com filtro ativo');
}

// 14. Busca pelo título — com centenas de tarefas no mês, os selects não bastam.
{
  const r = filtrarTarefas(COM_GENTE, { ...filtrosVazios(), texto: 'balan' });
  assert.deepStrictEqual(ids(r), [6]);
  assert.deepStrictEqual(ids(filtrarTarefas(COM_GENTE, { ...filtrosVazios(), texto: 'BALAN' })), [6],
    'busca não pode diferenciar maiúscula');
  assert.deepStrictEqual(ids(filtrarTarefas(COM_GENTE, { ...filtrosVazios(), texto: '  ' })), ids(COM_GENTE),
    'só espaço não filtra nada');
  ok('busca por parte do título, sem diferenciar maiúscula');
}

// 15. Por pessoa: conta responsável E supervisor, porque as duas são "minhas".
{
  const porResp = filtrarTarefas(COM_GENTE, { ...filtrosVazios(), usuario_id: '7' });
  assert.deepStrictEqual(ids(porResp), [6, 7], 'um dos vários responsáveis conta');
  const porSup = filtrarTarefas(COM_GENTE, { ...filtrosVazios(), usuario_id: '9' });
  assert.deepStrictEqual(ids(porSup), [7], 'supervisor também vê como sua');
  ok('filtro por pessoa pega responsável e supervisor');
}

// 16. Os dois novos somam com os que já existiam.
{
  const r = filtrarTarefas(COM_GENTE, { ...filtrosVazios(), texto: 'balan', usuario_id: '9' });
  assert.deepStrictEqual(ids(r), [], 'balancete não é do usuário 9');
  assert.strictEqual(temFiltroAtivo({ ...filtrosVazios(), texto: 'x' }), true);
  assert.strictEqual(temFiltroAtivo({ ...filtrosVazios(), usuario_id: '3' }), true);
  ok('texto e pessoa combinam com o resto e acendem o "limpar"');
}

// 17. O recorte que vem do Painel por link.
//
// O número do Painel e a lista daqui TÊM de bater. O Painel classifica pelo
// prazo interno (`data_prazo`), então o recorte aqui também: usar a faixa de
// vencimento, que lê o prazo legal, mostraria uma quantidade diferente da que
// a pessoa acabou de clicar.
{
  const HOJE = new Date(2026, 7, 24);        // 24/08/2026, local
  const T = [
    { id: 1, status: 'pendente',     data_prazo: '2026-08-20T00:00:00', prioridade: 'media',   gera_multa: true },
    { id: 2, status: 'pendente',     data_prazo: '2026-08-24T00:00:00', prioridade: 'urgente', gera_multa: false },
    { id: 3, status: 'em_andamento', data_prazo: '2026-08-28T00:00:00', prioridade: 'alta',    gera_multa: false },
    { id: 4, status: 'pendente',     data_prazo: '2026-10-30T00:00:00', prioridade: 'baixa',   gera_multa: false },
    { id: 5, status: 'concluida',    data_prazo: '2026-08-01T00:00:00', prioridade: 'alta',    gera_multa: true },
    { id: 6, status: 'cancelada',    data_prazo: '2026-08-01T00:00:00', prioridade: 'media',   gera_multa: false },
    { id: 7, status: 'pendente',     data_prazo: null,                  prioridade: 'media',   gera_multa: false },
  ];
  const rec = (alerta, extra = {}) =>
    ids(filtrarTarefas(T, { ...filtrosVazios(), alerta, ...extra }, HOJE));

  assert.deepStrictEqual(rec('atrasada'), [1], 'atrasada é só a de prazo vencido');
  assert.deepStrictEqual(rec('hoje'), [2], 'vence hoje');
  assert.deepStrictEqual(rec('semana'), [2, 3], 'hoje e os próximos 7 dias');
  // 'aberta' não pode sair do semáforo: a 7 não tem prazo, e no semáforo isso
  // é 'neutro' — o mesmo balaio da cancelada. Ela está aberta do mesmo jeito.
  assert.deepStrictEqual(rec('aberta'), [1, 2, 3, 4, 7], 'aberta inclui a sem prazo');
  assert.deepStrictEqual(rec('aberta', { prioridade: 'alta_urgente' }), [2, 3],
    'urgentes do painel = em aberto com prioridade alta ou urgente');
  // A concluída de prioridade alta não entra: já não é fila.
  assert.ok(!rec('aberta', { prioridade: 'alta_urgente' }).includes(5));
  assert.deepStrictEqual(ids(filtrarTarefas(T, { ...filtrosVazios(), multa: true }, HOJE)), [1, 5],
    'multa filtra pelas que geram');
  ok('os recortes do Painel batem com o que o Painel conta');
}

// 18. A URL vira filtro, e link velho não quebra a tela.
{
  const f = filtrosDaUrl(new URLSearchParams('empresa=3&setor=2&alerta=atrasada&multa=1'));
  assert.strictEqual(f.empresa_id, '3');
  assert.strictEqual(f.setor_id, '2');
  assert.strictEqual(f.alerta, 'atrasada');
  assert.strictEqual(f.multa, true);
  assert.strictEqual(temFiltroAtivo(f), true, 'o "limpar" tem de acender');

  const lixo = filtrosDaUrl(new URLSearchParams('alerta=coisanenhuma&naoexiste=1'));
  assert.strictEqual(lixo.alerta, '', 'recorte desconhecido é ignorado');
  assert.strictEqual(temFiltroAtivo(lixo), false, 'link velho abre a tela sem filtro, não quebrada');

  assert.strictEqual(filtrosDaUrl({ alerta: 'hoje' }).alerta, 'hoje', 'aceita objeto simples');
  assert.strictEqual(rotuloDoRecorte({ alerta: 'atrasada', prioridade: 'alta_urgente' }),
    'atrasadas, prioridade alta ou urgente');
  assert.strictEqual(rotuloDoRecorte(filtrosVazios()), '', 'sem recorte, sem rótulo');
  ok('a URL do Painel vira filtro, e link inválido não derruba a tela');
}

console.log(`\nPROVA OK: ${n} casos`);
