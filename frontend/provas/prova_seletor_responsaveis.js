// Prova do seletor de responsáveis: a lista, a busca, e o popover que fecha
// sozinho sem levar o modal junto.
//
// Roda em Node puro, sem navegador e sem build:
//     node provas/prova_seletor_responsaveis.js
//
// O que importa aqui, e que só se prova com a lógica fora do JSX:
// · a ORDEM da lista é a ordem de quem foi escolhido, porque o primeiro é o
//   principal e é dele que sai o supervisor da tarefa;
// · ESC e clique fora fecham o POPOVER, e nunca o modal de cadastro
//   (`Padrao_Modal_Nao_Fecha_Sozinho`: o modal sai pelo X ou pelo Cancelar, e
//   por mais nada).

import assert from 'node:assert';
import {
  alternar, normalizar, elegiveis, filtrar, escolhidos, resumo,
  reduzirPopover, escEhMeu, POPOVER_FECHADO,
} from '../src/pages/seletorResponsaveis.js';

let n = 0;
function ok(titulo) {
  n += 1;
  console.log(`ok ${n}. ${titulo}`);
}

const PESSOAS = [
  { id: 1, nome: 'Ana Paula', tipo: 'colaborador', bloqueado: false },
  { id: 2, nome: 'Bruno Sá', tipo: 'colaborador', bloqueado: false },
  { id: 3, nome: 'Carla', tipo: 'colaborador', bloqueado: true },
  { id: 4, nome: 'Cliente do Alfa', tipo: 'cliente', bloqueado: false },
  { id: 5, nome: 'Ântonio', tipo: 'colaborador', bloqueado: false },
];

// 1. PROVA POSITIVA. Sem ela, um seletor que não marcasse nada passaria no resto.
{
  assert.deepStrictEqual(alternar([], 2), [2]);
  assert.deepStrictEqual(alternar([2], 1), [2, 1]);
  ok('marcar duas pessoas devolve as duas');
}

// 2. A ordem é a da escolha, e não a do cadastro. O primeiro é o principal.
{
  const ids = alternar(alternar(alternar([], 5), 1), 2);
  assert.deepStrictEqual(ids, [5, 1, 2]);
  assert.strictEqual(ids[0], 5, 'o primeiro escolhido continua sendo o primeiro');
  ok('a ordem da lista é a ordem em que as pessoas foram escolhidas');
}

// 3. Desmarcar tira só quem foi clicado, e não bagunça o resto.
{
  assert.deepStrictEqual(alternar([5, 1, 2], 1), [5, 2]);
  ok('desmarcar do meio preserva os outros e a ordem');
}

// 4. Desmarcar o primeiro TROCA o principal. É a consequência que a tela precisa
//    mostrar, porque muda de quem sai o supervisor da tarefa.
{
  const depois = alternar([5, 1, 2], 5);
  assert.strictEqual(depois[0], 1);
  ok('desmarcar o primeiro promove o seguinte a principal');
}

// 5. Quem não pode responder por setor não aparece: cliente e bloqueado ficam
//    de fora, a mesma regra que o servidor aplica antes de gravar.
{
  const lista = elegiveis(PESSOAS).map((u) => u.id);
  assert.deepStrictEqual(lista, [1, 2, 5]);
  ok('cliente e pessoa bloqueada não entram na lista');
}

// 6. A busca ignora acento e caixa.
{
  assert.strictEqual(normalizar('Ântonio'), 'antonio');
  const achados = filtrar(elegiveis(PESSOAS), 'ANTONIO').map((u) => u.nome);
  assert.deepStrictEqual(achados, ['Ântonio']);
  ok('a busca acha "Ântonio" digitando "ANTONIO"');
}

// 7. Quem já está marcado não some com a busca. Se sumisse, não haveria como
//    desmarcar sem antes limpar o campo.
{
  const achados = filtrar(elegiveis(PESSOAS), 'bruno', [1]).map((u) => u.id);
  assert.ok(achados.includes(1), 'o já escolhido continua visível');
  assert.ok(achados.includes(2), 'e o resultado da busca também');
  ok('quem já foi escolhido continua visível durante a busca');
}

// 8. Busca vazia devolve todo mundo, e não lista vazia.
{
  assert.strictEqual(filtrar(elegiveis(PESSOAS), '').length, 3);
  assert.strictEqual(filtrar(elegiveis(PESSOAS), '   ').length, 3);
  ok('busca vazia não esconde ninguém');
}

// 9. Os chips saem na ordem da escolha, e id que não existe mais não quebra.
{
  const nomes = escolhidos([2, 1, 999], PESSOAS).map((u) => u.nome);
  assert.deepStrictEqual(nomes, ['Bruno Sá', 'Ana Paula']);
  ok('os chips seguem a ordem da escolha e ignoram id que sumiu');
}

// 10. O resumo do botão fechado.
{
  assert.strictEqual(resumo([], PESSOAS), 'sem responsável');
  assert.strictEqual(resumo([2], PESSOAS), 'Bruno Sá');
  assert.strictEqual(resumo([2, 1], PESSOAS), 'Bruno Sá e mais 1');
  ok('o botão fechado resume quem está escolhido');
}

// 11. Abrir e fechar pelo próprio botão, como todo menu.
{
  const aberto = reduzirPopover(POPOVER_FECHADO, { tipo: 'abrir', chave: 7 });
  assert.strictEqual(aberto.aberto, 7);
  const fechado = reduzirPopover(aberto, { tipo: 'abrir', chave: 7 });
  assert.strictEqual(fechado.aberto, null);
  ok('clicar no botão do popover aberto fecha ele');
}

// 12. Abrir outro setor troca de popover, sem deixar dois abertos.
{
  const a = reduzirPopover(POPOVER_FECHADO, { tipo: 'abrir', chave: 7 });
  const b = reduzirPopover(a, { tipo: 'abrir', chave: 9 });
  assert.strictEqual(b.aberto, 9);
  ok('abrir o popover de outro setor fecha o anterior');
}

// 13. ESC fecha o POPOVER. E nada aqui fecha o modal: quem devolvesse
//     `fechaModal` estaria contrariando a nota da vault.
{
  const aberto = reduzirPopover(POPOVER_FECHADO, { tipo: 'abrir', chave: 7 });
  const depois = reduzirPopover(aberto, { tipo: 'esc' });
  assert.strictEqual(depois.aberto, null);
  assert.ok(!('fechaModal' in depois), 'o seletor não tem opinião sobre o modal');
  ok('ESC fecha o popover, e o modal não é assunto dele');
}

// 14. Clique fora, idem.
{
  const aberto = reduzirPopover(POPOVER_FECHADO, { tipo: 'abrir', chave: 7 });
  assert.strictEqual(reduzirPopover(aberto, { tipo: 'clique-fora' }).aberto, null);
  ok('clique fora fecha o popover');
}

// 15. E o caso que faz o modal sobreviver: com o popover JÁ fechado, o ESC não
//     é meu. Se o seletor engolisse esse ESC, ele estaria decidindo por uma
//     tela que não é dele; se tratasse como "fechar", o modal iria junto.
{
  assert.strictEqual(escEhMeu(POPOVER_FECHADO), false);
  const aberto = reduzirPopover(POPOVER_FECHADO, { tipo: 'abrir', chave: 7 });
  assert.strictEqual(escEhMeu(aberto), true);
  assert.deepStrictEqual(reduzirPopover(POPOVER_FECHADO, { tipo: 'esc' }), POPOVER_FECHADO);
  ok('com o popover fechado, o ESC não é do seletor');
}

// 16. Abrir um popover limpa a busca do anterior, senão o próximo já nasce
//     filtrado por um texto que ninguém digitou nele.
{
  let e = reduzirPopover(POPOVER_FECHADO, { tipo: 'abrir', chave: 7 });
  e = reduzirPopover(e, { tipo: 'buscar', texto: 'ana' });
  assert.strictEqual(e.busca, 'ana');
  e = reduzirPopover(e, { tipo: 'abrir', chave: 9 });
  assert.strictEqual(e.busca, '');
  ok('o popover seguinte nasce com a busca limpa');
}

// 17. Fechar o modal fecha o popover junto, e limpa a busca. Sem isso, o
//     `setor_id` é o mesmo em toda empresa, e o popover reabriria sozinho na
//     PRÓXIMA empresa, com o texto que alguém digitou na anterior dentro.
{
  let e = reduzirPopover(POPOVER_FECHADO, { tipo: 'abrir', chave: 3 });
  e = reduzirPopover(e, { tipo: 'buscar', texto: 'ana' });
  const depois = reduzirPopover(e, { tipo: 'fechar' });
  assert.deepStrictEqual(depois, POPOVER_FECHADO);
  ok('fechar o modal apaga o popover e a busca dele');
}

// 18. Evento desconhecido não muda nada. A tela chama o reducer de vários
//     lugares, e um evento novo escrito errado não pode zerar a escolha.
{
  const aberto = reduzirPopover(POPOVER_FECHADO, { tipo: 'abrir', chave: 3 });
  assert.deepStrictEqual(reduzirPopover(aberto, { tipo: 'nao-existe' }), aberto);
  ok('evento desconhecido deixa o estado como estava');
}

console.log(`\n${n} casos, todos passaram.`);
