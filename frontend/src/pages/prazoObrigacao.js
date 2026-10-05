// Seção de prazo da tela de Obrigação: vencimento e prazo interno da equipe.
//
// Sem JSX, no molde de periodicidade.js, para rodar numa prova em Node puro
// (frontend/provas/prova_prazo_obrigacao.js). As contas de data são do
// servidor (gerador.calc_datas); aqui só se monta o pedido e o texto.

/** De onde vem o vencimento: um ou outro. Não é coluna: é o `ancora`. */
export const ORIGENS_PRAZO = [
  { valor: 'fechamento', rotulo: 'Fechamento do cliente',
    dica: 'Etapas do processo (lançar, conciliar, balancete): vence antes do fechamento de cada empresa.' },
  { valor: 'legal', rotulo: 'Prazo legal',
    dica: 'Obrigação acessória com data em lei, igual para todas as empresas (SPED, DCTFWeb, ECD).' },
];

export const origemDe = (f) => (f?.ancora === 'fechamento' ? 'fechamento' : 'legal');

/** Troca a origem mexendo só no `ancora`. A regra legal fica guardada: no
 *  fechamento ela é a reserva para empresa sem fechamento cadastrado. */
export function aplicarOrigem(f, origem) {
  return origem === 'fechamento' ? { ancora: 'fechamento' } : { ancora: '', ancora_dias_antes: 0 };
}

const sem = (t) => (t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

/** O que o setor costuma usar. Só sugere: a tela não trava. */
export function sugestaoOrigem(setorNome, nome, mininome) {
  if (/\b(ecd|ecf)\b/.test(sem(`${nome || ''} ${mininome || ''}`).replace(/_/g, ' '))) return 'legal';
  const setor = sem(setorNome);
  if (setor === 'fiscal') return 'legal';
  if (setor === 'contabilidade') return 'fechamento';
  return null;
}

/** Os três modos do prazo interno, na ordem do seletor. */
export const MODOS_INTERNO = [
  { valor: 'antes_vencimento', rotulo: 'Antes do vencimento',
    dica: 'Alguns dias antes do vencimento. É o cálculo de sempre.' },
  { valor: 'antes_fechamento', rotulo: 'Antes do fechamento',
    dica: 'Alguns dias antes do fechamento de cada cliente. Empresa sem fechamento cadastrado conta do vencimento.' },
  { valor: 'regra', rotulo: 'Regra própria',
    dica: 'Data própria no mês (primeiro dia útil, dia fixo...). Nunca passa do vencimento.' },
];

/** Regras de dia do mês: as mesmas do vencimento e do interno (RegraDia no servidor). */
export const REGRAS_DIA = [
  { valor: 'ultimo_dia_util', rotulo: 'Último dia útil' },
  { valor: 'primeiro_dia_util', rotulo: 'Primeiro dia útil' },
  { valor: 'dia_fixo', rotulo: 'Dia fixo' },
  { valor: 'dia_util', rotulo: 'N-ésimo dia útil' },
];

const USAM_DIA = ['dia_fixo', 'dia_util'];
export const usaDia = (tipo) => USAM_DIA.includes(tipo);

/** O que se escreve depois do número de dias, conforme o modo. */
export function rotuloRecuo(modo) {
  if (modo === 'antes_vencimento') return 'antes do vencimento';
  if (modo === 'antes_fechamento') return 'antes do fechamento do cliente';
  return null;
}

/** Inteiro, ou null quando o campo está vazio: nunca NaN. */
export function numero(v) {
  if (v === null || v === undefined || `${v}`.trim() === '') return null;
  const n = parseInt(v, 10);
  return Number.isNaN(n) ? null : n;
}

/** Campos do interno que vão para a API: tipo e dia só na regra própria. */
export function camposInterno(f) {
  const modo = f.interno_modo || 'antes_vencimento';
  const regra = modo === 'regra';
  const tipo = regra ? (f.interno_regra_tipo || null) : null;
  return {
    interno_modo: modo,
    interno_regra_tipo: tipo,
    interno_regra_dia: usaDia(tipo) ? numero(f.interno_regra_dia) : null,
  };
}

/** O que falta no formulário para a prévia ter o que calcular, ou null. */
export function faltaParaPrevia(f) {
  if ((f?.interno_modo || 'antes_vencimento') !== 'regra') return null;
  if (!f.interno_regra_tipo) return 'Escolha a regra do prazo interno para ver as datas.';
  if (usaDia(f.interno_regra_tipo) && numero(f.interno_regra_dia) === null) {
    return 'Informe o dia do prazo interno para ver as datas.';
  }
  return null;
}

/** Corpo do POST /obrigacoes/previa-prazo: só o que mexe nas datas. */
export function corpoPrevia(form) {
  const f = form || {};
  return {
    regra_prazo_tipo: f.regra_prazo_tipo || 'ultimo_dia_util',
    regra_prazo_dia: usaDia(f.regra_prazo_tipo) ? numero(f.regra_prazo_dia) : null,
    ajuste_nao_util: f.ajuste_nao_util || 'antecipar',
    sabado_util: Boolean(f.sabado_util),
    lembrar_dias_antes: numero(f.lembrar_dias_antes) || 0,
    tipo_dias: f.tipo_dias || 'corridos',
    ancora: f.ancora === 'fechamento' ? 'fechamento' : null,
    ancora_dias_antes: numero(f.ancora_dias_antes) || 0,
    ancora_tipo_dias: f.ancora_tipo_dias || 'uteis',
    ...camposInterno(f),
    meses_ativos: f.meses_ativos || null,
  };
}

const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
  'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
const SEMANA = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];

/** '2026-10-20' -> '20/10 (terça)'. Conta em UTC: sem escorregar de fuso. */
function diaComSemana(iso) {
  const [a, m, d] = iso.split('-').map(Number);
  const semana = SEMANA[new Date(Date.UTC(a, m - 1, d)).getUTCDay()];
  return `${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')} (${semana})`;
}

/** Resposta da prévia vira a linha que a tela mostra, mais exemplo e aviso. */
export function textoPrevia(r) {
  return {
    linha: `Tarefas de ${MESES[r.mes - 1]}/${r.ano}: vencimento ${diaComSemana(r.vencimento)}, `
      + `prazo interno ${diaComSemana(r.prazo_interno)}.`,
    exemplo: r.fechamento_exemplo ? `Exemplo: cliente que fecha dia ${r.fechamento_exemplo}.` : null,
    aviso: r.interno_limitado
      ? 'O prazo interno cairia depois do vencimento e fica no vencimento.'
      : null,
  };
}

/** Campos do interno de uma obrigação lida da API, prontos para o formulário. */
export function prazoDoRegistro(o) {
  return {
    interno_modo: o?.interno_modo || 'antes_vencimento',
    interno_regra_tipo: o?.interno_regra_tipo || '',
    interno_regra_dia: o?.interno_regra_dia ?? '',
  };
}
