// Prova da caixa "Pergunte à IA": o clique num resultado abre a tela de
// Tarefas mostrando aquela tarefa, e o resumo diz o número certo.
//
//     node provas/prova_pergunte_ia.js

import assert from 'node:assert';
import { EXEMPLOS, filtroDaTarefa, linkDaTarefa, resumoDaResposta, dataCurta } from '../src/pages/pergunteIA.js';
import { filtrosDaUrl, filtrarTarefas, SEM_COMPETENCIA } from '../src/pages/filtroTarefas.js';

let n = 0;
const ok = (t) => { n += 1; console.log(`ok ${n}. ${t}`); };

assert.ok(EXEMPLOS.length >= 3 && EXEMPLOS.some(e => /hoje/i.test(e)) && EXEMPLOS.some(e => /DCTFWeb/.test(e)));
ok('exemplos prontos: vence hoje e DCTFWeb');

const t = { id: 9, titulo: 'DCTFWeb MKB 09/2026', empresa_id: 3, competencia: '09/2026', status: 'pendente', data_prazo: '2026-10-05' };
const f = filtroDaTarefa(t);
assert.deepStrictEqual([f.empresa_id, f.texto, f.competencia, f.status], ['3', 'DCTFWeb MKB 09/2026', '09/2026', '']);
ok('filtro da tarefa: empresa, título e competência');

// O mesmo recorte pela URL (é assim que o Painel abre a tela de Tarefas).
const pelaUrl = filtrosDaUrl(new URLSearchParams(linkDaTarefa(t).split('?')[1]));
assert.deepStrictEqual([pelaUrl.empresa_id, pelaUrl.texto, pelaUrl.competencia], ['3', 'DCTFWeb MKB 09/2026', '09/2026']);
assert.ok(linkDaTarefa(t).startsWith('/tarefas?'));
ok('link da tarefa volta pelo filtrosDaUrl com o título');

// E a tela, com esse filtro, mostra a tarefa.
const lista = [t, { ...t, id: 10, titulo: 'Reinf MKB 09/2026' }, { ...t, id: 11, empresa_id: 4 }];
assert.deepStrictEqual(filtrarTarefas(lista, f, new Date(2026, 9, 5)).map(x => x.id), [9]);
ok('filtrarTarefas com o filtro do clique acha só aquela tarefa');

// Sem competência e cancelada: o filtro precisa dizer, senão a tela esconde.
const avulsa = { id: 12, titulo: 'Avulsa', empresa_id: 3, competencia: null, status: 'cancelada' };
const fa = filtroDaTarefa(avulsa);
assert.strictEqual(fa.competencia, SEM_COMPETENCIA);
assert.strictEqual(fa.status, 'cancelada');
assert.deepStrictEqual(filtrarTarefas([avulsa], fa).map(x => x.id), [12]);
ok('avulsa cancelada continua visível no clique');

assert.strictEqual(resumoDaResposta({ total: 0, tarefas: [] }), 'Nenhuma tarefa encontrada.');
assert.strictEqual(resumoDaResposta({ total: 1, tarefas: [t] }), '1 tarefa.');
assert.strictEqual(resumoDaResposta({ total: 70, tarefas: new Array(50).fill(t) }), '70 tarefas. Mostrando as 50 primeiras.');
ok('resumo: nenhuma, singular e lista cortada');

assert.strictEqual(dataCurta('2026-10-05'), '05/10');
assert.strictEqual(dataCurta(null), '');
ok('data curta dd/mm');

console.log(`\nPROVA OK: ${n} checagens`);
