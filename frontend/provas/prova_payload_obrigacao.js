// Prova do payload da obrigação: o "qual dia" tem de sair do navegador.
//
//     node provas/prova_payload_obrigacao.js
//
// O bug: a montagem do payload só enviava `regra_prazo_dia` quando a regra era
// `dia_fixo`. Com `dia_util` -- o N-ésimo dia útil, que é como SPED e
// EFD-Contribuições vencem -- o número digitado era DESCARTADO no navegador e
// ia null para a API. O cadastro salvava sem erro nenhum, e o cálculo caía no
// 1º dia útil: vencimento 01/09 onde deveria ser 14/09.

import assert from 'node:assert';
import { montarPayloadObrigacao } from '../src/pages/payloadObrigacao.js';

let n = 0;
const ok = (t) => { n += 1; console.log(`ok ${n}. ${t}`); };
const base = { nome: 'X', setor_id: '', responsavel_id: '', supervisor_id: '',
               tempo_previsto_min: '', lembrar_dias_antes: '5' };

// 1. PROVA POSITIVA
{
  const p = montarPayloadObrigacao({ ...base, regra_prazo_tipo: 'dia_fixo', regra_prazo_dia: '20' });
  assert.strictEqual(p.regra_prazo_dia, 20);
  ok('dia fixo envia o dia');
}

// 2. O BUG.
{
  const p = montarPayloadObrigacao({ ...base, regra_prazo_tipo: 'dia_util', regra_prazo_dia: '10' });
  assert.strictEqual(p.regra_prazo_dia, 10, 'N-ésimo dia útil tem de enviar o número');
  ok('N-ésimo dia útil envia o dia (era descartado)');
}

// 3. Regra que não usa número não manda lixo.
{
  for (const tipo of ['ultimo_dia_util', 'primeiro_dia_util']) {
    const p = montarPayloadObrigacao({ ...base, regra_prazo_tipo: tipo, regra_prazo_dia: '10' });
    assert.strictEqual(p.regra_prazo_dia, null, tipo);
  }
  ok('último e primeiro dia útil não enviam número');
}

// 4. Campo vazio vira null, não NaN.
{
  const p = montarPayloadObrigacao({ ...base, regra_prazo_tipo: 'dia_util', regra_prazo_dia: '' });
  assert.strictEqual(p.regra_prazo_dia, null);
  ok('campo vazio vira null');
}

// 5. Os outros numéricos seguem convertidos.
{
  const p = montarPayloadObrigacao({ ...base, setor_id: '3', tempo_previsto_min: '45',
                                     lembrar_dias_antes: '7', regra_prazo_tipo: 'dia_fixo',
                                     regra_prazo_dia: '20' });
  assert.strictEqual(p.setor_id, 3);
  assert.strictEqual(p.tempo_previsto_min, 45);
  assert.strictEqual(p.lembrar_dias_antes, 7);
  assert.strictEqual(p.responsavel_id, null, 'select vazio vira null, não NaN');
  ok('os demais campos numéricos continuam certos');
}

console.log(`\nPROVA OK: ${n} casos`);
