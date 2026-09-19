// Prova do seletor "Periodicidade" da tela de Obrigação.
//
//     node provas/prova_periodicidade.js
//
// Não há coluna de periodicidade: ela se deduz dos meses marcados e só
// preenche `meses_ativos` e `competencia_ref`. A competência da anual e da
// trimestral é o início do período, que é o que o recibo traz (LOG da fase 38:
// DEFIS e ECF em 01/AAAA). O item 6 confere a conta contra um oráculo escrito
// à mão, sem chamar o módulo, com a mesma aritmética do servidor
// (`calc_competencia`, backend/app/services/gerador.py).

import assert from 'node:assert';
import {
  PERIODICIDADES, periodicidadeDe, mesesDe, competenciaRefDe,
  rotuloCompetenciaCalculada, aplicarPeriodicidade, competenciaDiverge, clicarMesNaSerie,
  aoTrocarSentido,
} from '../src/pages/periodicidade.js';

let n = 0;
const ok = (t) => { n += 1; console.log(`ok ${n}. ${t}`); };

// Cópia de calc_competencia do servidor, escrita aqui de propósito.
const competencia = (mes, ano, desloc) => {
  const total = ano * 12 + (mes - 1) + desloc;
  const a = Math.floor(total / 12);
  const m = total - a * 12;
  return `${String(m + 1).padStart(2, '0')}/${a}`;
};

// 1. As quatro opções, na ordem decidida.
{
  assert.deepStrictEqual(PERIODICIDADES.map((p) => p.valor),
    ['mensal', 'trimestral', 'anual', 'personalizada']);
  for (const p of PERIODICIDADES) {
    assert.ok(p.rotulo && p.rotulo.trim(), `rótulo de ${p.valor}`);
    assert.ok(p.dica && p.dica.trim().length > 10, `dica de ${p.valor}`);
  }
  ok('PERIODICIDADES: Mensal, Trimestral, Anual, Personalizada, com rótulo e dica');
}

// 2. Dedução a partir dos meses.
{
  assert.strictEqual(periodicidadeDe('1,2,3,4,5,6,7,8,9,10,11,12'), 'mensal');
  assert.strictEqual(periodicidadeDe('12,1,2,3,4,5,6,7,8,9,10,11'), 'mensal');
  assert.strictEqual(periodicidadeDe('3'), 'anual');
  assert.strictEqual(periodicidadeDe('7'), 'anual');
  assert.strictEqual(periodicidadeDe('1,4,7,10'), 'trimestral');
  assert.strictEqual(periodicidadeDe('2,5,8,11'), 'trimestral');
  assert.strictEqual(periodicidadeDe('11,2,8,5'), 'trimestral');
  ok('periodicidadeDe: 12 meses mensal, 1 mês anual, 4 de 3 em 3 trimestral');
}

// 3. O que não se encaixa é personalizada, inclusive vazio.
{
  for (const v of ['', null, undefined, '1,2', '1,4,7', '1,4,7,11', '1,2,3,4,5,6,7,8,9,10,11']) {
    assert.strictEqual(periodicidadeDe(v), 'personalizada', `valor ${v}`);
  }
  ok('periodicidadeDe: qualquer outra coisa é personalizada, inclusive vazio');
}

// 4. Os meses que cada periodicidade marca.
{
  assert.strictEqual(mesesDe('mensal'), '1,2,3,4,5,6,7,8,9,10,11,12');
  assert.strictEqual(mesesDe('anual', 3), '3');
  assert.strictEqual(mesesDe('trimestral', 5), '2,5,8,11');
  assert.strictEqual(mesesDe('trimestral', 1), '1,4,7,10');
  assert.strictEqual(mesesDe('trimestral', 12), '3,6,9,12');
  assert.strictEqual(mesesDe('personalizada', 3), null);
  ok('mesesDe: anual marca 1 mês, trimestral marca de 3 em 3 dando a volta no ano');
}

// 5. O deslocamento.
{
  assert.strictEqual(competenciaRefDe('anual', 3), '-14');
  assert.strictEqual(competenciaRefDe('anual', 7), '-18');
  assert.strictEqual(competenciaRefDe('anual', 12), '-23');
  assert.strictEqual(competenciaRefDe('trimestral', 4), '-3');
  assert.strictEqual(competenciaRefDe('trimestral', 5), '-4');
  assert.strictEqual(competenciaRefDe('trimestral', 1), '-3');
  assert.strictEqual(competenciaRefDe('mensal', 3), null);
  assert.strictEqual(competenciaRefDe('personalizada', 3), null);
  ok('competenciaRefDe: anual -(M+11), trimestral -(((M-1)%3)+3), mensal e personalizada livres');
}

// 6. Oráculo: a competência que sai bate com o início do período, mês a mês.
{
  const esperado = {
    anual: (mes, ano) => `01/${ano - 1}`,
    trimestral: (mes, ano) => {
      const ini = Math.floor((mes - 1) / 3) * 3 + 1;   // início do trimestre da entrega
      const anterior = ini - 3;                          // início do trimestre anterior
      return anterior >= 1 ? `${String(anterior).padStart(2, '0')}/${ano}` : `${String(anterior + 12).padStart(2, '0')}/${ano - 1}`;
    },
  };
  const erradas = [];
  for (const per of ['anual', 'trimestral']) {
    for (let mes = 1; mes <= 12; mes += 1) {
      const got = competencia(mes, 2026, parseInt(competenciaRefDe(per, mes), 10));
      if (got !== esperado[per](mes, 2026)) erradas.push([per, mes, got]);
    }
  }
  assert.deepStrictEqual(erradas, []);
  ok('oráculo: anual dá janeiro do ano anterior e trimestral dá o início do trimestre anterior, nos 12 meses');
}

// 7. O texto no lugar do select.
{
  assert.strictEqual(rotuloCompetenciaCalculada('anual'), 'Janeiro do ano anterior');
  assert.strictEqual(rotuloCompetenciaCalculada('trimestral'), 'Primeiro mês do trimestre anterior');
  assert.strictEqual(rotuloCompetenciaCalculada('mensal'), null);
  ok('rotuloCompetenciaCalculada: texto só na anual e na trimestral');
}

// 8. Escolher a periodicidade preenche o formulário.
{
  const f = { meses_ativos: '1,2,3,4,5,6,7,8,9,10,11,12', competencia_ref: 'mes_anterior' };
  assert.deepStrictEqual(aplicarPeriodicidade(f, 'mensal', 'anual', 3),
    { meses_ativos: '3', competencia_ref: '-14' });
  assert.deepStrictEqual(aplicarPeriodicidade(f, 'mensal', 'trimestral', 5),
    { meses_ativos: '2,5,8,11', competencia_ref: '-4' });
  ok('aplicarPeriodicidade: anual em março e trimestral em maio');
}

// 9. Voltar da anual para mensal ou personalizada não deixa -14 preso.
{
  const anual = { meses_ativos: '3', competencia_ref: '-14' };
  assert.deepStrictEqual(aplicarPeriodicidade(anual, 'anual', 'mensal'),
    { meses_ativos: '1,2,3,4,5,6,7,8,9,10,11,12', competencia_ref: 'mes_anterior' });
  assert.deepStrictEqual(aplicarPeriodicidade(anual, 'anual', 'personalizada'),
    { meses_ativos: '3', competencia_ref: 'mes_anterior' });
  ok('saindo da anual, a competência volta a mês anterior');
}

// 10. Não-regressão: mensal e personalizada não mexem na competência escolhida à mão.
{
  const sped = { meses_ativos: '1,2,3,4,5,6,7,8,9,10,11,12', competencia_ref: '-2' };
  assert.strictEqual(aplicarPeriodicidade(sped, 'mensal', 'mensal').competencia_ref, '-2');
  assert.strictEqual(aplicarPeriodicidade(sped, 'mensal', 'personalizada').competencia_ref, '-2');
  ok('mensal e personalizada preservam a competência escolhida à mão (SPED -2)');
}

// 11. Sem mês marcado, a anual cai em janeiro, e não em NaN.
{
  assert.deepStrictEqual(aplicarPeriodicidade({ meses_ativos: '', competencia_ref: '' }, 'personalizada', 'anual'),
    { meses_ativos: '1', competencia_ref: '-12' });
  ok('anual sem mês marcado começa em janeiro');
}

// 12. Obrigação gravada antes da periodicidade: a ECF tinha ano_anterior, e a tela avisa.
{
  assert.strictEqual(competenciaDiverge({ meses_ativos: '7', competencia_ref: 'ano_anterior' }, 'anual'), true);
  assert.strictEqual(competenciaDiverge({ meses_ativos: '7', competencia_ref: '-18' }, 'anual'), false);
  assert.strictEqual(competenciaDiverge({ meses_ativos: '2,5,8,11', competencia_ref: '-4' }, 'trimestral'), false);
  assert.strictEqual(competenciaDiverge({ meses_ativos: '2,5,8,11', competencia_ref: 'mes_anterior' }, 'trimestral'), true);
  assert.strictEqual(competenciaDiverge({ meses_ativos: '1,2,3', competencia_ref: 'x' }, 'mensal'), false);
  ok('competenciaDiverge: acusa a anual e a trimestral gravadas com outra competência');
}
// 13. Achado do verificador funcional: na anual e na trimestral, clicar no mês
// que já está escolhido (ou em outro da mesma série) reescrevia a competência
// divergente calada, sem o usuário tocar no "Usar ...". Agora é nada.
{
  const ecf = { meses_ativos: '7', competencia_ref: 'ano_anterior' };
  assert.strictEqual(clicarMesNaSerie(ecf, 'anual', 7), null);
  const tri = { meses_ativos: '2,5,8,11', competencia_ref: 'mes_anterior' };
  assert.strictEqual(clicarMesNaSerie(tri, 'trimestral', 8), null);
  assert.deepStrictEqual(clicarMesNaSerie(ecf, 'anual', 3), { meses_ativos: '3', competencia_ref: '-14' });
  assert.deepStrictEqual(clicarMesNaSerie(tri, 'trimestral', 4), { meses_ativos: '1,4,7,10', competencia_ref: '-3' });
  ok('clicar no mês já escolhido não mexe em nada; outro mês aplica a regra');
}
// 14 a 18. Decisão (b) de 2026-09-19: a GUIA trimestral (DARF) diz o último
// dia do período ("Período de apuração 31/03/2026"), e o recibo diz o início.
// Trimestral de "entregar" usa o ÚLTIMO mês do trimestre anterior.
{
  assert.strictEqual(competenciaRefDe('trimestral', 4, 'entregar'), '-1');
  assert.strictEqual(competenciaRefDe('trimestral', 5, 'entregar'), '-2');
  assert.strictEqual(competenciaRefDe('trimestral', 1, 'entregar'), '-1');
  assert.strictEqual(competenciaRefDe('trimestral', 4, 'transmitir'), '-3');
  assert.strictEqual(competenciaRefDe('trimestral', 4, 'receber'), '-3');
  assert.strictEqual(competenciaRefDe('trimestral', 4), '-3');
  assert.strictEqual(competenciaRefDe('anual', 3, 'entregar'), '-14');
  ok('trimestral de entregar usa o último mês; recibo e anual não mudam');
}
{
  const erradas = [];
  for (let mes = 1; mes <= 12; mes += 1) {
    const ini = Math.floor((mes - 1) / 3) * 3 + 1;
    let ult = ini - 1;                        // último mês do trimestre anterior
    const ano = ult >= 1 ? 2026 : 2025;
    if (ult < 1) ult += 12;
    const esperado = `${String(ult).padStart(2, '0')}/${ano}`;
    const got = competencia(mes, 2026, parseInt(competenciaRefDe('trimestral', mes, 'entregar'), 10));
    if (got !== esperado) erradas.push([mes, got, esperado]);
  }
  assert.deepStrictEqual(erradas, []);
  ok('oráculo da guia trimestral: abril dá 03, janeiro dá 12 do ano anterior, nos 12 meses');
}
{
  assert.strictEqual(rotuloCompetenciaCalculada('trimestral', 'entregar'), 'Último mês do trimestre anterior');
  assert.strictEqual(rotuloCompetenciaCalculada('trimestral', 'transmitir'), 'Primeiro mês do trimestre anterior');
  assert.deepStrictEqual(
    aplicarPeriodicidade({ meses_ativos: '1,2,3,4,5,6,7,8,9,10,11,12', competencia_ref: 'mes_anterior', sentido: 'entregar' },
      'mensal', 'trimestral', 4),
    { meses_ativos: '1,4,7,10', competencia_ref: '-1' });
  ok('rótulo e aplicação da trimestral de guia');
}
{
  // A DARF do Presumido com "mes_anterior" gravado: é -1, e não diverge.
  assert.strictEqual(competenciaDiverge({ meses_ativos: '1,4,7,10', competencia_ref: 'mes_anterior', sentido: 'entregar' }, 'trimestral'), false);
  assert.strictEqual(competenciaDiverge({ meses_ativos: '1,4,7,10', competencia_ref: '-3', sentido: 'entregar' }, 'trimestral'), true);
  assert.strictEqual(competenciaDiverge({ meses_ativos: '7', competencia_ref: 'ano_anterior' }, 'anual'), true);
  ok('divergência compara o deslocamento: mes_anterior é -1');
}
{
  const tri = { meses_ativos: '1,4,7,10', competencia_ref: '-3', sentido: 'transmitir' };
  assert.deepStrictEqual(aoTrocarSentido(tri, 'trimestral', 'entregar'), { sentido: 'entregar', competencia_ref: '-1' });
  assert.deepStrictEqual(aoTrocarSentido(tri, 'mensal', 'entregar'), { sentido: 'entregar' });
  const legado = { meses_ativos: '1,4,7,10', competencia_ref: '-6', sentido: 'transmitir' };
  assert.deepStrictEqual(aoTrocarSentido(legado, 'trimestral', 'entregar'), { sentido: 'entregar' });
  ok('trocar o sentido na trimestral recalcula a competência; gravada fora da regra fica como está');
}

console.log(`\nPROVA OK: ${n} checagens verdes`);
