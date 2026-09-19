// Prova da regra do modal "Desvincular empresa" (fase 36).
//
//     node provas/prova_desvincular_empresa.js
//
// O servidor é quem recusa (422 sem obrigação marcada, motivo com menos de 3
// letras). A tela só não oferece o que vai ser recusado, e diz a mesma coisa
// que ele: duas opiniões sobre a mesma regra é como o usuário descobre que o
// sistema tem duas cabeças.

import assert from 'node:assert';
import {
  ETIQUETAS_VIA, podeDesvincular, motivoDoBloqueio, textoDoBotao, abertasMarcadas,
  resumoDoResultado, filtrarOpcoes,
} from '../src/pages/desvincularEmpresa.js';

let n = 0;
const ok = (t) => { n += 1; console.log(`ok ${n}. ${t}`); };

// 1. As três origens que o servidor devolve têm etiqueta e dica, e nada mais.
assert.deepStrictEqual(Object.keys(ETIQUETAS_VIA).sort(), ['ambos', 'regra', 'vinculo']);
for (const v of Object.values(ETIQUETAS_VIA)) {
  assert.ok(v.rotulo && v.dica, 'toda origem tem rótulo e dica');
}
assert.strictEqual(ETIQUETAS_VIA.regra.rotulo, 'pela regra');
assert.strictEqual(ETIQUETAS_VIA.vinculo.rotulo, 'vinculada');
ok('as três origens (regra, vínculo, ambos) têm rótulo e dica');

// 2. Só libera com obrigação marcada e motivo de 3 letras, contando sem espaço.
assert.strictEqual(podeDesvincular([], 'motivo bom'), false);
assert.strictEqual(podeDesvincular([1], ''), false);
assert.strictEqual(podeDesvincular([1], '  ab  '), false);
assert.strictEqual(podeDesvincular([1], 'abc'), true);
assert.strictEqual(podeDesvincular(null, 'abc'), false);
ok('libera só com obrigação marcada e motivo de 3 letras sem contar espaço');

// 3. O porquê do botão travado, um texto por causa.
assert.strictEqual(motivoDoBloqueio([], 'abc'), 'Marque ao menos uma obrigação.');
assert.strictEqual(motivoDoBloqueio([1], 'ab'), 'Escreva o motivo, com pelo menos 3 letras.');
assert.strictEqual(motivoDoBloqueio([1], 'abc'), undefined);
ok('o botão travado diz por quê, um texto por causa');

// 4. O botão diz quantas vão sair.
assert.strictEqual(textoDoBotao(0), 'Desvincular obrigações');
assert.strictEqual(textoDoBotao(1), 'Desvincular 1 obrigação');
assert.strictEqual(textoDoBotao(3), 'Desvincular 3 obrigações');
ok('o texto do botão é verbo + objeto, com a quantidade marcada');

// 5. Quantas tarefas em aberto saem, somando só as marcadas.
const lista = [
  { id: 1, abertas: 2 }, { id: 2, abertas: 3 }, { id: 3, abertas: 0 }, { id: 4 },
];
assert.strictEqual(abertasMarcadas(lista, [1, 2]), 5);
assert.strictEqual(abertasMarcadas(lista, [3, 4]), 0);
assert.strictEqual(abertasMarcadas(lista, []), 0);
assert.strictEqual(abertasMarcadas(null, [1]), 0);
ok('conta as tarefas em aberto só das obrigações marcadas');

// 6. O resultado em uma frase, com o plural certo.
assert.strictEqual(
  resumoDoResultado({ desvinculadas: 3, tarefas_canceladas: 8 }),
  '3 obrigações desvinculadas e 8 tarefas em aberto canceladas.');
assert.strictEqual(
  resumoDoResultado({ desvinculadas: 1, tarefas_canceladas: 0 }),
  '1 obrigação desvinculada. Nenhuma tarefa estava em aberto.');
assert.strictEqual(
  resumoDoResultado({ desvinculadas: 2, tarefas_canceladas: 1 }),
  '2 obrigações desvinculadas e 1 tarefa em aberto cancelada.');
ok('o resultado sai numa frase, com singular e plural certos');

// 7. A busca do SelectBusca ignora acento e caixa, e busca vazia devolve tudo.
const opcoes = [
  { valor: 1, rotulo: 'Trops Centro de Esp. e Lazer' },
  { valor: 2, rotulo: 'Padaria São João' },
  { valor: 3, rotulo: 'MKB Participações' },
];
assert.deepStrictEqual(filtrarOpcoes(opcoes, '').map((o) => o.valor), [1, 2, 3]);
assert.deepStrictEqual(filtrarOpcoes(opcoes, 'sao').map((o) => o.valor), [2]);
assert.deepStrictEqual(filtrarOpcoes(opcoes, 'PARTICIPA').map((o) => o.valor), [3]);
assert.deepStrictEqual(filtrarOpcoes(opcoes, 'xyz'), []);
assert.deepStrictEqual(filtrarOpcoes(null, 'a'), []);
ok('a busca ignora acento e caixa, e vazia devolve tudo');

console.log(`\nPROVA OK: ${n} checagens verdes`);
