// Prova do seletor "O documento vai para que lado?" da tela de Obrigação.
//
//     node provas/prova_sentido_obrigacao.js
//
// A tela tinha a regra de documento escrita duas vezes, em JSX: quem vê os
// identificadores e quando o "Exige documento" aparece marcado. Com a quarta
// opção (Transmitir ao órgão), as duas precisam mudar juntas e bater com o
// servidor (`perfil_documento`, backend/app/models.py). Por isso moram num
// módulo sem JSX, provado aqui.

import assert from 'node:assert';
import { SENTIDOS, sentidoDoForm, mostraIdentificadores, exigeDocumentoMarcado }
  from '../src/pages/sentidoObrigacao.js';

let n = 0;
const ok = (t) => { n += 1; console.log(`ok ${n}. ${t}`); };

// 1. As quatro opções, na ordem decidida em 2026-09-15.
{
  assert.deepStrictEqual(SENTIDOS.map((s) => s.valor),
    ['receber', 'entregar', 'transmitir', 'interna']);
  ok('SENTIDOS tem as 4 opções, na ordem Receber, Entregar, Transmitir, Nenhum');
}

// 2. Cada opção com rótulo e dica, e a dica diz alguma coisa.
{
  for (const s of SENTIDOS) {
    assert.ok(s.rotulo && s.rotulo.trim(), `rótulo de ${s.valor}`);
    assert.ok(s.dica && s.dica.trim().length > 20, `dica de ${s.valor}`);
  }
  assert.strictEqual(SENTIDOS.find((s) => s.valor === 'transmitir').rotulo, 'Transmitir ao órgão');
  ok('cada opção tem rótulo e dica; transmitir se chama "Transmitir ao órgão"');
}

// 3. Texto de tela sem travessão nem en-dash.
{
  const tudo = SENTIDOS.map((s) => `${s.rotulo} ${s.dica}`).join(' ');
  assert.ok(!/[\u2014\u2013]/.test(tudo), 'travessão no texto');
  ok('rótulos e dicas sem travessão');
}

// 4. Legado: sentido nulo ou vazio se comporta como receber, igual ao servidor.
{
  for (const v of [null, undefined, '']) {
    assert.strictEqual(sentidoDoForm({ sentido: v }), 'receber', String(v));
  }
  assert.strictEqual(sentidoDoForm({ sentido: 'transmitir' }), 'transmitir');
  ok('sentido nulo, ausente ou vazio vira receber na tela');
}

// 5. Identificadores: receber e transmitir sempre mostram.
{
  for (const sentido of ['receber', 'transmitir', '', null]) {
    assert.strictEqual(mostraIdentificadores({ sentido, exige_documento: null }), true, String(sentido));
  }
  ok('receber e transmitir mostram os identificadores (inclusive legado vazio)');
}

// 6. O DEFEITO 2 DO LASTRO: interna com documento precisa dos identificadores,
//    senão a baixa trava e o e-validador nunca casa.
{
  assert.strictEqual(mostraIdentificadores({ sentido: 'interna', exige_documento: true }), true);
  ok('interna com "exige documento" marcado mostra os identificadores');
}

// 7. E o que continua escondido.
{
  assert.strictEqual(mostraIdentificadores({ sentido: 'interna', exige_documento: null }), false);
  assert.strictEqual(mostraIdentificadores({ sentido: 'interna', exige_documento: false }), false);
  ok('interna sem a flag não mostra os identificadores');
}

// 7b. Entregar mostra: as guias de imposto casam no e-validador pelo código.
{
  for (const flag of [null, true, false]) {
    assert.strictEqual(mostraIdentificadores({ sentido: 'entregar', exige_documento: flag }), true);
  }
  ok('entregar mostra os identificadores (código da guia)');
}

// 8. Oráculo escrito à mão, sem chamar o servidor: as 24 combinações.
//    Flag explícita vence; nula deriva dos identificadores; interna nula é falso.
//    Entregar segue a regra geral (decisão do usuário, 2026-09-19: a guia de
//    imposto sobe no e-validador pelo código dela).
{
  const esperado = (sentido, flag, ident) => {
    if (flag === true) return true;
    if (flag === false) return false;
    if (sentido === 'interna') return false;
    return ident !== '';
  };
  const erradas = [];
  for (const sentido of ['receber', 'entregar', 'interna', 'transmitir']) {
    for (const flag of [null, true, false]) {
      for (const ident of ['', 'EFD']) {
        const got = exigeDocumentoMarcado({ sentido, exige_documento: flag, identificadores: ident });
        if (got !== esperado(sentido, flag, ident)) erradas.push([sentido, flag, ident, got]);
      }
    }
  }
  assert.deepStrictEqual(erradas, [], JSON.stringify(erradas));
  ok('exigeDocumentoMarcado bate com a regra do servidor nas 24 combinações');
}

// 9. Identificador só com espaço não conta, como no `.strip()` do servidor.
{
  assert.strictEqual(exigeDocumentoMarcado({ sentido: 'transmitir', exige_documento: null, identificadores: '   ' }), false);
  assert.strictEqual(exigeDocumentoMarcado({ sentido: '', exige_documento: null, identificadores: 'EFD' }), true);
  ok('espaço em branco não conta como identificador; legado vazio segue receber');
}

console.log(`PROVA OK: ${n} checagens verdes`);
