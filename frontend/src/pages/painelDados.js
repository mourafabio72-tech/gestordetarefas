// Preparo dos números do painel para a tela.
//
// Sem JSX e sem React, como os vizinhos, para provar em Node puro.

/** As cinco situações, na ordem em que se lê: o que corre primeiro. */
export const SITUACOES = [
  { chave: 'atrasada', rotulo: 'Atrasadas', curto: 'Atras.', cor: '#a24a3a' },
  { chave: 'pendente', rotulo: 'Pendentes', curto: 'Pend.', cor: '#8a6a2e' },
  { chave: 'em_andamento', rotulo: 'Em andamento', curto: 'Andam.', cor: '#3a7d76' },
  { chave: 'concluida', rotulo: 'Concluídas', curto: 'Concl.', cor: '#4d8a3f' },
  { chave: 'cancelada', rotulo: 'Canceladas', curto: 'Canc.', cor: '#a99e88' },
];

/**
 * Percentual de cada situação, somando exatamente 100.
 *
 * Arredondar cada fatia por conta própria faz a soma dar 99 ou 101 — foi o que
 * a rosca antiga mostrava. Aqui a maior fatia absorve a diferença: é a que
 * menos sente um ponto a mais, e o total continua verdadeiro.
 */
export function percentuais(resumo, situacoes = SITUACOES) {
  const total = situacoes.reduce((s, x) => s + (resumo?.[x.chave] || 0), 0);
  if (!total) return situacoes.map((s) => ({ ...s, valor: 0, pct: 0 }));

  const bruto = situacoes.map((s) => {
    const valor = resumo?.[s.chave] || 0;
    return { ...s, valor, exato: (valor / total) * 100 };
  });
  const arred = bruto.map((b) => ({ ...b, pct: Math.round(b.exato) }));
  const sobra = 100 - arred.reduce((s, x) => s + x.pct, 0);
  if (sobra !== 0) {
    let maior = 0;
    for (let i = 1; i < arred.length; i++) if (arred[i].valor > arred[maior].valor) maior = i;
    arred[maior] = { ...arred[maior], pct: arred[maior].pct + sobra };
  }
  return arred.map(({ exato, ...r }) => r);
}

/**
 * Linhas do heatmap: a proporção de cada situação dentro da própria linha.
 *
 * Proporção da LINHA, não do total geral: um setor com 3 tarefas e outro com
 * 300 têm de ser comparáveis quanto ao que os aflige. Comparar contra o total
 * pintaria o setor pequeno de cinza sempre, escondendo que ele está todo
 * atrasado.
 */
export function linhasMapa(itens, situacoes = SITUACOES) {
  return (itens || []).map((i) => {
    const total = i.total || 0;
    return {
      nome: i.nome,
      total,
      multa: i.multa || 0,
      celulas: situacoes.map((s) => ({
        ...s,
        valor: i[s.chave] || 0,
        // Intensidade relativa à linha, com piso visível: 1 em 300 precisa
        // aparecer, senão o mapa esconde justamente o caso raro e grave.
        intensidade: total ? Math.max((i[s.chave] || 0) / total, (i[s.chave] || 0) ? 0.12 : 0) : 0,
      })),
    };
  });
}

/** DD/MM, sem passar por new Date (que jogaria para o dia anterior). */
export function diaMes(iso) {
  const d = (iso || '').slice(0, 10);
  return d.length === 10 ? `${d.slice(8, 10)}/${d.slice(5, 7)}` : '';
}

/** Estado inicial dos filtros do painel. */
export function filtrosVazios() {
  return { empresa_id: '', setor_id: '', usuario_id: '', competencia: '', so_multa: false };
}

/** Só o que está preenchido vira parâmetro — vazio derruba a consulta com 422. */
export function paraConsulta(filtros) {
  const saida = {};
  for (const [k, v] of Object.entries(filtros || {})) {
    if (k === 'so_multa') { if (v) saida.so_multa = true; continue; }
    const t = typeof v === 'string' ? v.trim() : v;
    if (t !== '' && t !== null && t !== undefined) saida[k] = t;
  }
  return saida;
}

/** Algum filtro ativo? */
export function temFiltroAtivo(filtros) {
  return Object.keys(paraConsulta(filtros)).length > 0;
}

/** As três dimensões do mapa. Abas, e não três blocos: a página já era longa. */
export const DIMENSOES = [
  { chave: 'por_setor', rotulo: 'Setor' },
  { chave: 'por_colaborador', rotulo: 'Colaborador' },
  { chave: 'por_empresa', rotulo: 'Empresa' },
];

/**
 * Pontualidade do que já foi entregue.
 *
 * Todo o resto do painel é foto do agora: quanto falta, o que atrasou. Este é
 * o único número que olha para trás e diz se o escritório entrega no prazo.
 * Só conta tarefa concluída que tinha prazo — sem prazo não há o que cumprir,
 * e incluí-la inflaria o índice de graça.
 */
export function pontualidade(resumo) {
  const base = resumo?.concluidas_com_prazo || 0;
  if (!base) return null;
  const dentro = resumo?.no_prazo || 0;
  return { base, dentro, fora: base - dentro, pct: Math.round((dentro / base) * 100) };
}

/**
 * "há 3 dias", a partir de uma data ISO. Usado no documento que saiu e não foi
 * aberto: o que assusta ali não é a data, é o tempo parado.
 */
export function haQuantosDias(iso, agora = new Date()) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d)) return '';
  const dias = Math.floor((agora - d) / 86400000);
  if (dias <= 0) return 'hoje';
  return dias === 1 ? 'há 1 dia' : `há ${dias} dias`;
}

/**
 * Segmentos da rosca, em SVG puro (o projeto não tem biblioteca de gráfico e
 * não precisa de uma para desenhar cinco arcos).
 *
 * Cada fatia vira um traço no mesmo círculo: `dash` é o comprimento do arco,
 * `gap` o resto da volta, `offset` onde ele começa. Usa os percentuais já
 * fechados em 100 por `percentuais`, então a volta fecha exata — desenhar a
 * partir dos valores crus deixaria uma fresta ou uma sobreposição.
 */
export function arcosRosca(fatias, raio = 42) {
  const volta = 2 * Math.PI * raio;
  let andado = 0;
  return (fatias || []).filter((f) => f.pct > 0).map((f) => {
    const dash = (f.pct / 100) * volta;
    const arco = { ...f, dash, gap: volta - dash, offset: -andado, volta };
    andado += dash;
    return arco;
  });
}

/**
 * Barras empilhadas: uma por setor, colaborador ou empresa.
 *
 * A LARGURA da barra é o volume relativo ao maior — é o que responde "quem tem
 * mais trabalho". A divisão DENTRO dela é a composição — "e como esse trabalho
 * está". O heatmap responde só a segunda; junto com a largura, o gráfico diz
 * as duas coisas de uma vez.
 */
export function barras(itens, situacoes = SITUACOES) {
  const lista = itens || [];
  const maior = Math.max(1, ...lista.map((i) => i.total || 0));
  return lista.map((i) => {
    const total = i.total || 0;
    return {
      nome: i.nome,
      total,
      multa: i.multa || 0,
      // Piso de 2%: linha com uma tarefa só some ao lado de outra com 300, e
      // sumir é pior que exagerar — quem tem 1 precisa aparecer para ser clicado.
      largura: total ? Math.max((total / maior) * 100, 2) : 0,
      segmentos: situacoes
        .map((s) => ({ ...s, valor: i[s.chave] || 0 }))
        .filter((s) => s.valor > 0)
        .map((s) => ({ ...s, pct: (s.valor / total) * 100 })),
    };
  });
}
