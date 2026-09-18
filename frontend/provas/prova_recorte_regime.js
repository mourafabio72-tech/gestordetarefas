// Prova do recorte por regime no modal "Gerar tarefas do mês".
//
//     node provas/prova_recorte_regime.js
//
// O pedido: além de "Todas as empresas" e "Somente as escolhidas", gerar para
// as empresas de um ou mais regimes tributários. A tela converte os regimes
// marcados em ids de empresa e chama a rota que já existe: o backend continua
// decidindo quem cada obrigação alcança (interseção, gerador.py).
//
// A armadilha que esta prova guarda: o backend lê `empresa_ids: []` como
// "todas". Regime marcado sem nenhuma empresa, ou nenhum regime marcado, não
// pode sair da tela como lista vazia, senão o botão gera o escritório inteiro
// dizendo que gerou para um recorte.

import assert from 'node:assert';
import {
  REGIMES_GERACAO, empresasDosRegimes, idsDoRecorte, podeGerar, nomesDosRegimes,
} from '../src/pages/recorteGeracao.js';

let n = 0;
const ok = (t) => { n += 1; console.log(`ok ${n}. ${t}`); };

const empresas = [
  { id: 1, regime_tributario: 'lucro_real' },
  { id: 2, regime_tributario: 'lucro_real' },
  { id: 3, regime_tributario: 'lucro_presumido' },
  { id: 4, regime_tributario: 'simples_nacional' },
  { id: 5, regime_tributario: 'indefinido' },
  { id: 6, regime_tributario: null },
  { id: 7 },
];

// (a) a lista: 7 regimes, na ordem decidida, com os valores do banco
{
  assert.deepStrictEqual(REGIMES_GERACAO.map((r) => r.valor), [
    'simples_nacional', 'lucro_real', 'lucro_presumido', 'mei',
    'isento', 'imune', 'terceiro_setor',
  ]);
  ok('7 regimes, na ordem Simples, Real, Presumido, MEI, Isento, Imune, Terceiro Setor');
}
{
  assert.deepStrictEqual(REGIMES_GERACAO.map((r) => r.rotulo), [
    'Simples Nacional', 'Lucro Real', 'Lucro Presumido', 'MEI',
    'Isento', 'Imune', 'Terceiro Setor',
  ]);
  ok('rótulos iguais aos da tela de Empresas');
}
{
  assert.ok(!REGIMES_GERACAO.some((r) => r.valor === 'indefinido'));
  ok('"indefinido" fora da lista (decisão 2b)');
}

// (b) empresas dos regimes
{
  assert.deepStrictEqual(empresasDosRegimes(empresas, ['lucro_real']), [1, 2]);
  ok('um regime devolve as empresas dele');
}
{
  assert.deepStrictEqual(empresasDosRegimes(empresas, ['lucro_real', 'lucro_presumido']), [1, 2, 3]);
  ok('dois regimes somam');
}
{
  assert.deepStrictEqual(empresasDosRegimes(empresas, ['indefinido']), []);
  assert.deepStrictEqual(empresasDosRegimes(empresas, []), []);
  const todas = empresasDosRegimes(empresas, REGIMES_GERACAO.map((r) => r.valor));
  assert.ok(![5, 6, 7].some((id) => todas.includes(id)));
  ok('empresa indefinida ou sem regime nunca entra, nem com os 7 marcados');
}
{
  assert.deepStrictEqual(empresasDosRegimes(null, ['lucro_real']), []);
  ok('lista de empresas ainda não carregada não quebra');
}

// (c) ids do recorte, por modo
{
  assert.strictEqual(idsDoRecorte('todas', [4], ['lucro_real'], empresas), null);
  ok('"todas" manda null, e ignora o que estiver marcado nos outros modos');
}
{
  assert.deepStrictEqual(idsDoRecorte('escolhidas', [4, 1], ['lucro_real'], empresas), [4, 1]);
  ok('"escolhidas" manda as escolhidas, e ignora os regimes');
}
{
  assert.deepStrictEqual(idsDoRecorte('regime', [4], ['lucro_real'], empresas), [1, 2]);
  ok('"regime" manda os ids do regime, e ignora as escolhidas');
}

// (d) a armadilha: recorte vazio nunca sai da tela
{
  assert.strictEqual(podeGerar('regime', [], ['mei'], empresas), false);
  ok('regime marcado sem nenhuma empresa bloqueia');
}
{
  assert.strictEqual(podeGerar('regime', [], [], empresas), false);
  ok('nenhum regime marcado bloqueia');
}
{
  assert.strictEqual(podeGerar('regime', [], ['simples_nacional'], empresas), true);
  assert.strictEqual(podeGerar('todas', [], [], empresas), true);
  assert.strictEqual(podeGerar('escolhidas', [3], [], empresas), true);
  ok('recorte com empresa libera, e "todas" libera sempre');
}

{
  assert.strictEqual(podeGerar('qualquer', [1], ['lucro_real'], empresas), false);
  assert.deepStrictEqual(idsDoRecorte(undefined, [1], [], empresas), []);
  ok('modo desconhecido falha fechado: bloqueia, e nunca vira null');
}

// (e) não-regressão: "escolhidas" com lista vazia continua bloqueado
{
  assert.strictEqual(podeGerar('escolhidas', [], ['lucro_real'], empresas), false);
  ok('"escolhidas" sem empresa continua bloqueado, mesmo com regime marcado');
}

// (g) empresa bloqueada ou inativa não conta: o gerador não gera para ela
// (gerador.py, empresas_alvo), e a contagem "Lucro Real (8)" não pode prometer
// tarefa que não sai. Achado do verificador de evidência da fase 33.
{
  const com = [...empresas,
    { id: 8, regime_tributario: 'lucro_real', bloqueado: true },
    { id: 9, regime_tributario: 'lucro_real', ativo: false }];
  assert.deepStrictEqual(empresasDosRegimes(com, ['lucro_real']), [1, 2]);
  assert.strictEqual(podeGerar('regime', [], ['mei'],
    [{ id: 10, regime_tributario: 'mei', bloqueado: true }]), false);
  ok('bloqueada e inativa ficam fora da contagem e do recorte');
}

// (f) o texto da faixa de resumo, na ordem da lista e em português
{
  assert.strictEqual(nomesDosRegimes(['lucro_real']), 'Lucro Real');
  assert.strictEqual(nomesDosRegimes(['lucro_presumido', 'lucro_real']), 'Lucro Real e Lucro Presumido');
  assert.strictEqual(nomesDosRegimes(['mei', 'lucro_real', 'simples_nacional']),
    'Simples Nacional, Lucro Real e MEI');
  assert.strictEqual(nomesDosRegimes(['indefinido']), '');
  ok('nomes dos regimes na ordem da lista, com "e" antes do último');
}

console.log(`PROVA OK: ${n} checagens verdes`);
