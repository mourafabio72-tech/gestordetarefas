// Montagem do que a tela de Obrigação envia à API.
//
// Fica em arquivo próprio, sem JSX, pelo mesmo motivo de contexts/bilhete.js:
// é a conversão que já errou em silêncio uma vez, e assim ela roda numa prova
// em Node puro (frontend/provas/prova_payload_obrigacao.js).

/** Regras de prazo que usam o campo numérico ao lado. */
const USAM_DIA = ['dia_fixo', 'dia_util'];

/** Inteiro, ou null quando o campo está vazio — nunca NaN. */
function numero(v) {
  if (v === null || v === undefined || `${v}`.trim() === '') return null;
  const n = parseInt(v, 10);
  return Number.isNaN(n) ? null : n;
}

/**
 * @param {object} form estado do formulário
 * @returns {object} corpo do POST/PUT
 */
export function montarPayloadObrigacao(form) {
  const f = form || {};
  return {
    ...f,
    setor_id: numero(f.setor_id),
    responsavel_id: numero(f.responsavel_id),
    supervisor_id: numero(f.supervisor_id),
    tempo_previsto_min: numero(f.tempo_previsto_min),
    // As DUAS regras usam o número: dia_fixo é o dia do mês, dia_util é qual
    // dia útil. A versão anterior só olhava dia_fixo -- escrita quando dia_util
    // não existia no select -- e descartava o valor digitado antes de sair do
    // navegador. Quem escolhia "10º dia útil" salvava sem o 10, sem erro
    // nenhum, e o cálculo caía no 1º dia útil.
    regra_prazo_dia: USAM_DIA.includes(f.regra_prazo_tipo) ? numero(f.regra_prazo_dia) : null,
    lembrar_dias_antes: numero(f.lembrar_dias_antes) || 0,
  };
}
