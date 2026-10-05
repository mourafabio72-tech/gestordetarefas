// Prova da seção de prazo da tela de Obrigação (fase 57).
//
//     node provas/prova_prazo_obrigacao.js
//
// O prazo interno ganhou três modos no servidor (fase 56): antes do
// vencimento, antes do fechamento do cliente e regra própria. Esta prova cobre
// o que a tela faz sem JSX: as opções do seletor, o corpo da prévia e o texto
// que a prévia mostra. As datas do item 5 em diante são um oráculo escrito à
// mão (20/10/2026 é terça, 01/11/2026 é domingo, conferido fora do módulo).

// A prévia lê datas ISO ('2026-11-01'). Com fuso de São Paulo, `new Date(iso)`
// cai no dia anterior; a prova roda nesse fuso para pegar esse erro.
process.env.TZ = 'America/Sao_Paulo';

import assert from 'node:assert';
import {
  MODOS_INTERNO, REGRAS_DIA, usaDia, rotuloRecuo, corpoPrevia, textoPrevia, prazoDoRegistro,
  faltaParaPrevia, ORIGENS_PRAZO, origemDe, aplicarOrigem, sugestaoOrigem,
} from '../src/pages/prazoObrigacao.js';

let n = 0;
const ok = (t) => { n += 1; console.log(`ok ${n}. ${t}`); };

// 1. Os três modos, na ordem do seletor, com rótulo e dica.
{
  assert.deepStrictEqual(MODOS_INTERNO.map((m) => m.valor),
    ['antes_vencimento', 'antes_fechamento', 'regra']);
  assert.deepStrictEqual(MODOS_INTERNO.map((m) => m.rotulo),
    ['Antes do vencimento', 'Antes do fechamento', 'Regra própria']);
  for (const m of MODOS_INTERNO) assert.ok(m.dica && m.dica.length > 10, m.valor);
  ok('três modos do prazo interno, com rótulo e dica');
}

// 2. As regras de dia têm os mesmos valores que o servidor aceita (RegraDia).
{
  assert.deepStrictEqual(REGRAS_DIA.map((r) => r.valor).sort(),
    ['dia_fixo', 'dia_util', 'primeiro_dia_util', 'ultimo_dia_util']);
  assert.ok(REGRAS_DIA.every((r) => r.rotulo));
  assert.ok(REGRAS_DIA.some((r) => r.rotulo === 'N-ésimo dia útil'));
  ok('regras de dia com os valores do servidor');
}

// 3. Só dia fixo e N-ésimo dia útil pedem o número.
{
  assert.strictEqual(usaDia('dia_fixo'), true);
  assert.strictEqual(usaDia('dia_util'), true);
  assert.strictEqual(usaDia('primeiro_dia_util'), false);
  assert.strictEqual(usaDia('ultimo_dia_util'), false);
  assert.strictEqual(usaDia(''), false);
  ok('usaDia');
}

// 4. O texto ao lado do número diz de onde se conta; a regra própria não tem.
{
  assert.strictEqual(rotuloRecuo('antes_vencimento'), 'antes do vencimento');
  assert.strictEqual(rotuloRecuo('antes_fechamento'), 'antes do fechamento do cliente');
  assert.strictEqual(rotuloRecuo('regra'), null);
  ok('rótulo do recuo por modo');
}

// 5. Texto da prévia, com o exemplo do plano.
{
  const t = textoPrevia({ mes: 10, ano: 2026, vencimento: '2026-10-20',
    prazo_interno: '2026-10-13', interno_limitado: false, fechamento_exemplo: null });
  assert.strictEqual(t.linha, 'Tarefas de outubro/2026: vencimento 20/10 (terça), prazo interno 13/10 (terça).');
  assert.strictEqual(t.exemplo, null);
  assert.strictEqual(t.aviso, null);
  ok('prévia: mês por extenso, dd/mm e dia da semana');
}

// 6. Data ISO não escorrega para o dia anterior no fuso de São Paulo.
{
  const t = textoPrevia({ mes: 11, ano: 2026, vencimento: '2026-11-01',
    prazo_interno: '2026-11-01', interno_limitado: false, fechamento_exemplo: null });
  assert.strictEqual(t.linha, 'Tarefas de novembro/2026: vencimento 01/11 (domingo), prazo interno 01/11 (domingo).');
  ok('sem deslocamento de fuso');
}

// 7. Ancorada ou "antes do fechamento": a prévia diz que o fechamento é exemplo.
{
  const t = textoPrevia({ mes: 10, ano: 2026, vencimento: '2026-10-15',
    prazo_interno: '2026-10-05', interno_limitado: false, fechamento_exemplo: 15 });
  assert.strictEqual(t.exemplo, 'Exemplo: cliente que fecha dia 15.');
  ok('fechamento de exemplo');
}

// 8. Regra própria cortada no vencimento: a prévia avisa (LASTRO, regra local 1).
{
  const t = textoPrevia({ mes: 10, ano: 2026, vencimento: '2026-10-20',
    prazo_interno: '2026-10-20', interno_limitado: true, fechamento_exemplo: null });
  assert.ok(t.aviso && t.aviso.includes('vencimento'), t.aviso);
  // O corte vale para os três modos ("antes do fechamento" com fechamento
  // depois do vencimento também é cortado): o aviso não pode citar um modo só.
  assert.ok(!/regra própria/i.test(t.aviso), t.aviso);
  ok('aviso quando o interno foi limitado ao vencimento');
}

// 9. Corpo da prévia: só os campos de prazo, números convertidos, sem lixo.
{
  const form = {
    nome: 'Depreciação', setor_id: '3', identificadores: 'x',
    regra_prazo_tipo: 'dia_fixo', regra_prazo_dia: '20', ajuste_nao_util: 'antecipar',
    sabado_util: false, lembrar_dias_antes: '', tipo_dias: 'uteis',
    ancora: '', ancora_dias_antes: '0', ancora_tipo_dias: 'uteis',
    interno_modo: 'regra', interno_regra_tipo: 'dia_fixo', interno_regra_dia: '5',
    meses_ativos: '1,2,3,4,5,6,7,8,9,10,11,12',
  };
  const c = corpoPrevia(form);
  assert.ok(!('nome' in c) && !('setor_id' in c) && !('identificadores' in c));
  assert.strictEqual(c.regra_prazo_dia, 20);
  assert.strictEqual(c.lembrar_dias_antes, 0);
  assert.strictEqual(c.ancora, null);
  assert.strictEqual(c.ancora_dias_antes, 0);
  assert.strictEqual(c.interno_regra_tipo, 'dia_fixo');
  assert.strictEqual(c.interno_regra_dia, 5);
  assert.strictEqual(c.meses_ativos, '1,2,3,4,5,6,7,8,9,10,11,12');
  ok('corpo da prévia com os campos de prazo');
}

// 10. Fora da regra própria, tipo e dia do interno não vão (o servidor
//     recusaria regra sem tipo; aqui o resto do formulário não pode vazar).
{
  const c = corpoPrevia({ interno_modo: 'antes_vencimento', interno_regra_tipo: 'dia_fixo',
    interno_regra_dia: '5', regra_prazo_tipo: 'primeiro_dia_util', regra_prazo_dia: '9',
    lembrar_dias_antes: '3' });
  assert.strictEqual(c.interno_regra_tipo, null);
  assert.strictEqual(c.interno_regra_dia, null);
  assert.strictEqual(c.regra_prazo_dia, null, 'primeiro dia útil não manda número');
  assert.strictEqual(c.lembrar_dias_antes, 3);
  ok('fora da regra própria, tipo e dia do interno ficam nulos');
}

// 11. Obrigação gravada antes da fase 56 (campos nulos) abre em "antes do
//     vencimento", e os campos vazios não viram "null" escrito no input.
{
  assert.deepStrictEqual(prazoDoRegistro({ interno_modo: null, interno_regra_tipo: null, interno_regra_dia: null }),
    { interno_modo: 'antes_vencimento', interno_regra_tipo: '', interno_regra_dia: '' });
  assert.deepStrictEqual(prazoDoRegistro({}),
    { interno_modo: 'antes_vencimento', interno_regra_tipo: '', interno_regra_dia: '' });
  assert.deepStrictEqual(prazoDoRegistro({ interno_modo: 'regra', interno_regra_tipo: 'dia_util', interno_regra_dia: 3 }),
    { interno_modo: 'regra', interno_regra_tipo: 'dia_util', interno_regra_dia: 3 });
  ok('registro legado abre em antes do vencimento');
}

// 12. Regra própria incompleta não vai ao servidor: a prévia pede o que falta,
//     em vez de mostrar como erro o que é só o formulário pela metade.
{
  assert.strictEqual(faltaParaPrevia({ interno_modo: 'regra', interno_regra_tipo: '' }),
    'Escolha a regra do prazo interno para ver as datas.');
  assert.strictEqual(faltaParaPrevia({ interno_modo: 'regra', interno_regra_tipo: 'dia_fixo', interno_regra_dia: '' }),
    'Informe o dia do prazo interno para ver as datas.');
  assert.strictEqual(faltaParaPrevia({ interno_modo: 'regra', interno_regra_tipo: 'dia_fixo', interno_regra_dia: '5' }), null);
  assert.strictEqual(faltaParaPrevia({ interno_modo: 'regra', interno_regra_tipo: 'primeiro_dia_util', interno_regra_dia: '' }), null);
  assert.strictEqual(faltaParaPrevia({ interno_modo: 'antes_vencimento', interno_regra_tipo: '' }), null);
  ok('regra própria incompleta pede o que falta, sem chamar o servidor');
}

// 13 a 16. Fase 57b: "De onde vem o prazo", fechamento do cliente OU prazo
//          legal. Não é coluna nova: é o `ancora` que já existe.
{
  assert.deepStrictEqual(ORIGENS_PRAZO.map((o) => o.valor), ['fechamento', 'legal']);
  assert.deepStrictEqual(ORIGENS_PRAZO.map((o) => o.rotulo), ['Fechamento do cliente', 'Prazo legal']);
  for (const o of ORIGENS_PRAZO) assert.ok(o.dica && o.dica.length > 10, o.valor);
  ok('duas origens de prazo, com rótulo e dica');
}
{
  assert.strictEqual(origemDe({ ancora: 'fechamento' }), 'fechamento');
  assert.strictEqual(origemDe({ ancora: '' }), 'legal');
  assert.strictEqual(origemDe({ ancora: null }), 'legal');
  ok('origem lida do ancora');
}
{
  const f = { ancora: 'fechamento', ancora_dias_antes: '5', regra_prazo_tipo: 'dia_fixo', regra_prazo_dia: '20' };
  assert.deepStrictEqual(aplicarOrigem(f, 'legal'), { ancora: '', ancora_dias_antes: 0 });
  assert.deepStrictEqual(aplicarOrigem({ ancora: '' }, 'fechamento'), { ancora: 'fechamento' });
  // Voltar ao fechamento não apaga a regra legal: ela é a reserva da empresa sem fechamento.
  assert.ok(!('regra_prazo_tipo' in aplicarOrigem(f, 'fechamento')));
  ok('trocar a origem mexe só no ancora');
}
{
  assert.strictEqual(sugestaoOrigem('Fiscal', 'entrega_sped_fiscal', 'sped_fiscal'), 'legal');
  assert.strictEqual(sugestaoOrigem('Contabilidade', 'conferencia saldos bancários', ''), 'fechamento');
  assert.strictEqual(sugestaoOrigem('Contabilidade', 'entrega_ecd', 'ECD'), 'legal');
  assert.strictEqual(sugestaoOrigem('contabilidade', 'Entrega ECF', ''), 'legal');
  assert.strictEqual(sugestaoOrigem('Dp', 'folha', ''), null);
  assert.strictEqual(sugestaoOrigem('', 'x', ''), null);
  // "ecd" dentro de outra palavra não conta.
  assert.strictEqual(sugestaoOrigem('Contabilidade', 'conferencia saldos', 'decd'), 'fechamento');
  ok('sugestão por setor: Fiscal e ECD/ECF legal, Contabilidade fechamento, outros nada');
}

console.log(`\nPROVA OK: ${n} checagens verdes`);
