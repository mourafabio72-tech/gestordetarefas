// "Periodicidade" da tela de Obrigação: Mensal, Trimestral, Anual, Personalizada.
//
// Não existe coluna de periodicidade (decisão de 2026-09-19): ela se deduz dos
// meses marcados, e escolher uma periodicidade só preenche `meses_ativos` e
// `competencia_ref`. Arquivo sem JSX, no molde de sentidoObrigacao.js, para a
// prova rodar em Node puro (frontend/provas/prova_periodicidade.js).
//
// A competência da anual e da trimestral é o INÍCIO do período, porque é isso
// que o recibo traz e o que o e-validador lê: "01/01/2025 a 31/12/2025" vira
// 01/2025 (backend/app/services/validador.py). Medido em produção em 19/09:
// DEFIS e ECF em 01/AAAA.

export const PERIODICIDADES = [
  { valor: 'mensal', rotulo: 'Mensal', dica: 'Gera todo mês.' },
  {
    valor: 'trimestral',
    rotulo: 'Trimestral',
    dica: 'Escolha o primeiro mês de entrega: os outros saem de 3 em 3. '
      + 'A competência é o primeiro mês do trimestre anterior.',
  },
  {
    valor: 'anual',
    rotulo: 'Anual',
    dica: 'Escolha o mês de entrega. A competência é janeiro do ano anterior, '
      + 'que é o que o recibo da declaração traz.',
  },
  { valor: 'personalizada', rotulo: 'Personalizada', dica: 'Você marca os meses um a um.' },
];

const TODOS = '1,2,3,4,5,6,7,8,9,10,11,12';

/** Meses marcados, como números de 1 a 12, sem repetição e em ordem. */
export function mesesDoCsv(csv) {
  const nums = String(csv || '').split(',').map((x) => parseInt(x.trim(), 10))
    .filter((n) => n >= 1 && n <= 12);
  return [...new Set(nums)].sort((a, b) => a - b);
}

/** Qual periodicidade os meses marcados descrevem. */
export function periodicidadeDe(csv) {
  const m = mesesDoCsv(csv);
  if (m.length === 12) return 'mensal';
  if (m.length === 1) return 'anual';
  if (m.length === 4 && m.every((x) => x % 3 === m[0] % 3)) return 'trimestral';
  return 'personalizada';
}

/** Meses que a periodicidade marca a partir do mês de entrega escolhido. */
export function mesesDe(periodicidade, mes) {
  if (periodicidade === 'mensal') return TODOS;
  if (periodicidade === 'anual') return String(mes);
  if (periodicidade === 'trimestral') {
    return [0, 3, 6, 9].map((d) => ((mes - 1 + d) % 12) + 1).sort((a, b) => a - b).join(',');
  }
  return null;
}

/** Deslocamento da competência que a periodicidade impõe, ou null se é escolha livre. */
export function competenciaRefDe(periodicidade, mes) {
  if (periodicidade === 'anual') return String(-(mes + 11));
  if (periodicidade === 'trimestral') return String(-(((mes - 1) % 3) + 3));
  return null;
}

/** Texto da competência calculada, para o lugar do select na anual e na trimestral. */
export function rotuloCompetenciaCalculada(periodicidade) {
  if (periodicidade === 'anual') return 'Janeiro do ano anterior';
  if (periodicidade === 'trimestral') return 'Primeiro mês do trimestre anterior';
  return null;
}

/**
 * O que muda no formulário ao escolher a periodicidade ou o mês de entrega.
 * `atual` é a periodicidade que estava escolhida: saindo da anual ou da
 * trimestral, a competência volta a "mês anterior", porque o deslocamento
 * calculado (-14, por exemplo) não é opção da lista da mensal.
 */
export function aplicarPeriodicidade(form, atual, nova, mes) {
  const marcados = mesesDoCsv(form.meses_ativos);
  const base = mes || marcados[0] || 1;
  const calculada = atual === 'anual' || atual === 'trimestral';
  if (nova === 'mensal') {
    return { meses_ativos: TODOS, competencia_ref: calculada ? 'mes_anterior' : form.competencia_ref };
  }
  if (nova === 'personalizada') {
    return {
      meses_ativos: form.meses_ativos,
      competencia_ref: calculada ? 'mes_anterior' : form.competencia_ref,
    };
  }
  return { meses_ativos: mesesDe(nova, base), competencia_ref: competenciaRefDe(nova, base) };
}

/**
 * Obrigação anual ou trimestral gravada antes da periodicidade pode ter outra
 * competência (a ECF tinha "ano_anterior", que dá julho, e não janeiro). A tela
 * mostra isso em vez de exibir a calculada como se fosse a gravada.
 */
export function competenciaDiverge(form, periodicidade) {
  const m = mesesDoCsv(form.meses_ativos);
  const esperada = m.length ? competenciaRefDe(periodicidade, m[0]) : null;
  return esperada !== null && String(form.competencia_ref ?? '') !== esperada;
}

/**
 * Clique num mês na anual ou na trimestral. Se a série não muda (o mês já
 * escolhido, ou outro mês da mesma trimestral), devolve null e nada se grava:
 * senão a competência divergente seria reescrita calada, sem o "Usar ...".
 */
export function clicarMesNaSerie(form, periodicidade, mes) {
  const novos = mesesDe(periodicidade, mes);
  if (novos === mesesDoCsv(form.meses_ativos).join(',')) return null;
  return aplicarPeriodicidade(form, periodicidade, periodicidade, mes);
}
