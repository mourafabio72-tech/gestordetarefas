// Prova do alcance da obrigação: o check "aplicar a todas", o perfil e as
// empresas vinculadas.
//
// Roda em Node puro, sem navegador e sem build:
//     node provas/prova_alvo_check.js
//
// O buraco que isto fecha, medido na tela antes de mexer: o check era DERIVADO
// de `!aplica_regimes && !aplica_segmentos`, então ficava MARCADO mesmo com dez
// empresas vinculadas em "somente estas" — dizendo o contrário do que a tela
// fazia. E desmarcá-lo FORÇAVA o primeiro regime da lista, então não existia
// caminho por ali para "só estas empresas".

import assert from 'node:assert';
import {
  estadoDoAlvo, reduzirAlvo, aplicaTodas, aviso,
} from '../src/pages/alvoObrigacao.js';

let n = 0;
function ok(titulo) {
  n += 1;
  console.log(`ok ${n}. ${titulo}`);
}

const VAZIA = { empresa_ids: [], aplica_regimes: '', aplica_segmentos: '', alvo_modo: 'regra' };

// 1. PROVA POSITIVA. Sem ela, um estado que dissesse "não" a tudo passaria no resto.
{
  const e = estadoDoAlvo(VAZIA);
  assert.strictEqual(aplicaTodas(e), true);
  assert.strictEqual(aviso(e), 'A obrigação alcança todas as empresas.');
  ok('obrigação sem perfil e sem empresa alcança todas, e a tela diz isso');
}

// 2. O caso do pedido: vincular UMA empresa desmarca o check sozinho e troca o modo.
{
  let e = estadoDoAlvo(VAZIA);
  e = reduzirAlvo(e, { tipo: 'vincular', id: 7 });
  assert.deepStrictEqual(e.form.empresa_ids, [7]);
  assert.strictEqual(e.form.alvo_modo, 'vinculadas');
  assert.strictEqual(aplicaTodas(e), false, 'o check não pode continuar marcado');
  ok('vincular a primeira empresa desmarca "aplicar a todas" e vai para "somente estas"');
}

// 3. A segunda empresa não mexe mais no modo, e não sobrescreve o estado guardado.
{
  let e = estadoDoAlvo({ ...VAZIA, aplica_regimes: 'lucro_real' });
  e = reduzirAlvo(e, { tipo: 'vincular', id: 7 });
  const guardado = e.anterior;
  e = reduzirAlvo(e, { tipo: 'vincular', id: 9 });
  assert.deepStrictEqual(e.form.empresa_ids, [7, 9]);
  assert.deepStrictEqual(e.anterior, guardado, 'a segunda não pode regravar o "de onde viemos"');
  ok('a segunda empresa entra sem mexer no modo nem no estado guardado');
}

// 4. Desvincular a ÚLTIMA volta atrás. Sem isso, a obrigação fica em "somente
//    estas" com a lista vazia, e não gera para ninguém, em silêncio.
{
  let e = estadoDoAlvo({ ...VAZIA, aplica_regimes: 'lucro_real,simples_nacional' });
  e = reduzirAlvo(e, { tipo: 'vincular', id: 7 });
  e = reduzirAlvo(e, { tipo: 'desvincular', id: 7 });
  assert.deepStrictEqual(e.form.empresa_ids, []);
  assert.strictEqual(e.form.alvo_modo, 'regra');
  assert.strictEqual(e.form.aplica_regimes, 'lucro_real,simples_nacional', 'o perfil volta como estava');
  assert.strictEqual(e.restringe, true);
  ok('desvincular a última devolve o modo e o perfil que havia antes');
}

// 5. E desvincular do meio não devolve nada: ainda há empresa marcada.
{
  let e = estadoDoAlvo(VAZIA);
  e = reduzirAlvo(e, { tipo: 'vincular', id: 7 });
  e = reduzirAlvo(e, { tipo: 'vincular', id: 9 });
  e = reduzirAlvo(e, { tipo: 'desvincular', id: 7 });
  assert.deepStrictEqual(e.form.empresa_ids, [9]);
  assert.strictEqual(e.form.alvo_modo, 'vinculadas');
  ok('desvincular uma do meio mantém o modo, porque ainda há empresa marcada');
}

// 6. "Limpar" é o mesmo que desvincular todas: também volta atrás.
{
  let e = estadoDoAlvo(VAZIA);
  e = reduzirAlvo(e, { tipo: 'vincular', id: 7 });
  e = reduzirAlvo(e, { tipo: 'vincular', id: 9 });
  e = reduzirAlvo(e, { tipo: 'limpar-empresas' });
  assert.deepStrictEqual(e.form.empresa_ids, []);
  assert.strictEqual(e.form.alvo_modo, 'regra');
  assert.strictEqual(aplicaTodas(e), true);
  ok('limpar a lista inteira devolve o estado anterior, e o check volta');
}

// 7. "Selecionar todas" entra pelo mesmo caminho da primeira empresa.
{
  let e = estadoDoAlvo(VAZIA);
  e = reduzirAlvo(e, { tipo: 'vincular-varias', ids: [1, 2, 3] });
  assert.deepStrictEqual(e.form.empresa_ids, [1, 2, 3]);
  assert.strictEqual(e.form.alvo_modo, 'vinculadas');
  ok('selecionar várias de uma vez também troca o modo');
}

// 8. O bug que motivou tudo: desmarcar o check NÃO escolhe regime por você.
{
  let e = estadoDoAlvo(VAZIA);
  e = reduzirAlvo(e, { tipo: 'aplicar-todas', valor: false });
  assert.strictEqual(e.form.aplica_regimes, '', 'não pode forçar o primeiro regime da lista');
  assert.strictEqual(e.form.aplica_segmentos, '');
  assert.strictEqual(aplicaTodas(e), false, 'e mesmo assim o check fica desmarcado');
  ok('desmarcar o check não escolhe um regime que ninguém pediu');
}

// 9. E a tela diz o que falta, em vez de deixar a pessoa achando que restringiu.
{
  let e = estadoDoAlvo(VAZIA);
  e = reduzirAlvo(e, { tipo: 'aplicar-todas', valor: false });
  assert.ok(aviso(e).includes('Escolha ao menos um regime'), aviso(e));
  ok('com o check desmarcado e nada escolhido, o aviso diz o que fazer');
}

// 10. Marcar o check de volta limpa o perfil, que é o que ele promete.
{
  let e = estadoDoAlvo({ ...VAZIA, aplica_regimes: 'lucro_real' });
  e = reduzirAlvo(e, { tipo: 'aplicar-todas', valor: true });
  assert.strictEqual(e.form.aplica_regimes, '');
  assert.strictEqual(aplicaTodas(e), true);
  ok('marcar "aplicar a todas" limpa o perfil');
}

// 11. O estado que vai para a API bate com o que a tela mostra. É a checagem
//     que pega o desencontro original: check marcado com empresas vinculadas.
{
  let e = estadoDoAlvo(VAZIA);
  e = reduzirAlvo(e, { tipo: 'vincular', id: 7 });
  const mostrado = aplicaTodas(e);
  const gravado = (e.form.alvo_modo || 'regra') !== 'vinculadas'
    && !(e.form.aplica_regimes || '') && !(e.form.aplica_segmentos || '');
  assert.strictEqual(mostrado, gravado, 'a tela e o corpo do PUT têm que concordar');
  assert.strictEqual(mostrado, false);
  ok('o que a tela mostra é o que vai para a API');
}

// 12. Trocar para "somente estas" pelo radio também guarda o de onde veio.
{
  let e = estadoDoAlvo({ ...VAZIA, aplica_regimes: 'mei' });
  e = reduzirAlvo(e, { tipo: 'modo', valor: 'vinculadas' });
  e = reduzirAlvo(e, { tipo: 'vincular', id: 3 });
  e = reduzirAlvo(e, { tipo: 'desvincular', id: 3 });
  assert.strictEqual(e.form.aplica_regimes, 'mei');
  ok('o radio "somente estas" também tem caminho de volta');
}

// 13. Uma obrigação que JÁ está salva em "somente estas" abre coerente.
{
  const e = estadoDoAlvo({ empresa_ids: [4, 5], alvo_modo: 'vinculadas',
                           aplica_regimes: '', aplica_segmentos: '' });
  assert.strictEqual(aplicaTodas(e), false, 'não pode abrir dizendo "todas"');
  assert.ok(aviso(e).includes('Somente 2'), aviso(e));
  ok('obrigação salva em "somente estas" abre sem dizer que alcança todas');
}

// 14. O caso silencioso: "somente estas" com lista vazia não gera para ninguém.
{
  const e = estadoDoAlvo({ empresa_ids: [], alvo_modo: 'vinculadas' });
  assert.ok(aviso(e).includes('não gera para ninguém'), aviso(e));
  ok('a tela avisa quando a obrigação não alcançaria ninguém');
}

// 15. Evento desconhecido não muda nada.
{
  const e = estadoDoAlvo(VAZIA);
  assert.deepStrictEqual(reduzirAlvo(e, { tipo: 'inexistente' }), e);
  ok('evento desconhecido deixa o estado como estava');
}

console.log(`\n${n} casos, todos passaram.`);
