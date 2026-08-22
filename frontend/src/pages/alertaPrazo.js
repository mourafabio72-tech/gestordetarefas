// Semáforo de prazo do card de tarefa: verde em dia, amarelo chegando perto,
// vermelho atrasado.
//
// A cor sai do PRAZO INTERNO (`data_prazo`), não do vencimento legal. É o prazo
// que a equipe persegue, e é o que o card já mostrava; pintar pelo vencimento
// deixaria tudo verde até o dia em que já não dá mais tempo. Sem prazo interno,
// cai no vencimento; sem nenhum dos dois, fica neutro em vez de inventar risco.
//
// Sem JSX e sem React, como os vizinhos, para provar em Node puro.

/**
 * Cada nível traz a cor forte (borda e texto) e a suave (o degradê do fundo).
 * Tons da paleta Sage & Creme — o vermelho é a terracota da casa, não o
 * vermelho de sistema, que berraria no meio do creme.
 */
export const NIVEIS = {
  atrasada:  { forte: '#a24a3a', suave: '#f6ded7' },
  hoje:      { forte: '#b4622c', suave: '#fae6d6' },
  proximo:   { forte: '#8a6a2e', suave: '#f7eed8' },
  em_dia:    { forte: '#5f7057', suave: '#e6eee1' },
  concluida: { forte: '#4d8a3f', suave: '#e9f0e4' },
  neutro:    { forte: '#808a74', suave: '#efe9dc' },
};

/** "AAAA-MM-DD..." -> dia em UTC, para subtrair sem esbarrar em horário de verão. */
function diaUTC(iso) {
  const [a, m, d] = (iso || '').slice(0, 10).split('-').map(Number);
  if (!a || !m || !d) return null;
  return Date.UTC(a, m - 1, d);
}

/**
 * Diagnóstico do prazo de uma tarefa.
 *
 * Devolve `{ nivel, dias, rotulo, forte, suave }`. `dias` é positivo para o que
 * ainda vai vencer, negativo para o que passou, e null quando não há data.
 *
 * As faixas: atrasada (passou), hoje, até 7 dias (amarelo) e mais que isso
 * (verde). Sete dias porque a rotina do escritório é semanal — o que cabe na
 * semana é o que a pessoa precisa enxergar antes de escolher o que fazer hoje.
 *
 * Tarefa concluída sai do semáforo: ela não tem mais prazo a cumprir, e pintar
 * de vermelho uma entrega feita com atraso confundiria "fazer" com "fiz tarde".
 * Cancelada fica neutra.
 */
export function alertaDaTarefa(tarefa, hoje = new Date()) {
  const t = tarefa || {};
  if (t.status === 'concluida') return { nivel: 'concluida', dias: null, rotulo: 'concluída', ...NIVEIS.concluida };
  if (t.status === 'cancelada') return { nivel: 'neutro', dias: null, rotulo: 'cancelada', ...NIVEIS.neutro };

  const alvo = diaUTC(t.data_prazo) ?? diaUTC(t.data_vencimento);
  if (alvo === null) return { nivel: 'neutro', dias: null, rotulo: 'sem prazo', ...NIVEIS.neutro };

  const ref = Date.UTC(hoje.getFullYear(), hoje.getMonth(), hoje.getDate());
  const dias = Math.round((alvo - ref) / 86400000);

  if (dias < 0) {
    const n = Math.abs(dias);
    return { nivel: 'atrasada', dias, rotulo: `atrasada ${n === 1 ? 'há 1 dia' : `há ${n} dias`}`, ...NIVEIS.atrasada };
  }
  if (dias === 0) return { nivel: 'hoje', dias, rotulo: 'vence hoje', ...NIVEIS.hoje };
  if (dias <= 7) return { nivel: 'proximo', dias, rotulo: dias === 1 ? 'vence amanhã' : `vence em ${dias} dias`, ...NIVEIS.proximo };
  return { nivel: 'em_dia', dias, rotulo: `vence em ${dias} dias`, ...NIVEIS.em_dia };
}

/** Fundo do card: a cor do nível esmaecendo até o creme, na diagonal. */
export function fundoDoAlerta(alerta) {
  return `linear-gradient(135deg, ${alerta.suave} 0%, #fffdf9 62%)`;
}
