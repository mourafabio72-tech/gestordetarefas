// Caixa "Pergunte à IA" (Painel e Tarefas): a parte sem React, para provar em
// Node puro (`frontend/provas/prova_pergunte_ia.js`).
//
// O servidor já devolve a lista pronta e no escopo de quem perguntou. Aqui só
// mora o que a tela faz com ela: o clique num resultado abre a tela de Tarefas
// filtrada naquela tarefa, pelo mesmo `filtrosDaUrl` que o Painel usa.

import { filtrosVazios, SEM_COMPETENCIA } from './filtroTarefas.js';

export const EXEMPLOS = [
  'O que vence hoje?',
  'O que está atrasado no Fiscal?',
  'Quantas DCTFWeb faltam?',
  'Minhas tarefas desta semana',
];

/** Filtro da tela de Tarefas que mostra esta tarefa. */
export function filtroDaTarefa(t) {
  return {
    ...filtrosVazios(),
    empresa_id: String(t.empresa_id ?? ''),
    texto: t.titulo || '',
    competencia: t.competencia || SEM_COMPETENCIA,
    // Cancelada some da tela sem situação escolhida; o clique tem de achá-la.
    status: t.status === 'cancelada' ? 'cancelada' : '',
  };
}

export function linkDaTarefa(t) {
  const f = filtroDaTarefa(t);
  const p = new URLSearchParams({ empresa: f.empresa_id, texto: f.texto, competencia: f.competencia });
  if (f.status) p.set('status', f.status);
  return `/tarefas?${p.toString()}`;
}

export function resumoDaResposta(r) {
  const total = r?.total || 0;
  if (!total) return 'Nenhuma tarefa encontrada.';
  const base = total === 1 ? '1 tarefa.' : `${total} tarefas.`;
  const mostradas = (r.tarefas || []).length;
  return mostradas < total ? `${base} Mostrando as ${mostradas} primeiras.` : base;
}

export function dataCurta(iso) {
  if (!iso) return '';
  const [, m, d] = String(iso).slice(0, 10).split('-');
  return `${d}/${m}`;
}
