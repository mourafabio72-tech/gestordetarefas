// Mensagem legível a partir da resposta de erro da API.
//
// O FastAPI responde erro de validação (422) com `detail` sendo uma LISTA de
// objetos, um por campo. As telas mostram `error.response.data.detail` direto
// num alert, e uma lista de objetos vira "[object Object]" na tela -- que não
// diz à pessoa nem qual campo recusou, nem por quê.
//
// Fica em arquivo próprio, sem React, para rodar em prova Node pura
// (`frontend/provas/prova_erro_api.js`), como bilhete.js e entrada.js.

// Nomes que o backend usa nos campos × como a pessoa os conhece na tela.
const NOME_DO_CAMPO = {
  razao_social: 'Razão social',
  cnpj: 'CNPJ',
  nome_fantasia: 'Nome fantasia',
  regime_tributario: 'Regime tributário',
  segmento: 'Segmento',
  fechamento_tipo: 'Fechamento contábil',
  fechamento_dia: 'Dia do fechamento',
  data_prazo: 'Prazo interno',
  data_vencimento: 'Vencimento',
  competencia: 'Competência',
  regra_prazo_dia: 'Dia do prazo',
  ancora_dias_antes: 'Dias antes do fechamento',
  email: 'E-mail',
  senha: 'Senha',
  titulo: 'Título',
};

// Mensagens do Pydantic × português de gente.
function traduzir(msg) {
  const m = (msg || '').toLowerCase();
  if (m.includes('valid integer')) return 'precisa ser um número inteiro';
  if (m.includes('valid number')) return 'precisa ser um número';
  if (m.includes('valid email')) return 'não parece um e-mail válido';
  if (m.includes('valid date')) return 'não é uma data válida';
  if (m.includes('field required') || m.includes('missing')) return 'é obrigatório';
  if (m.includes('at least')) return 'está curto demais';
  if (m.includes('at most')) return 'está longo demais';
  return msg || 'valor inválido';
}

function nomeDoCampo(loc) {
  if (!Array.isArray(loc)) return '';
  // loc vem como ["body", "campo"] — o nome do campo é o último pedaço textual
  const campo = [...loc].reverse().find(p => typeof p === 'string' && p !== 'body');
  if (!campo) return '';
  return NOME_DO_CAMPO[campo] || campo.replace(/_/g, ' ');
}

/**
 * @param {*} erro   o objeto lançado pelo axios
 * @param {string} padrao  mensagem quando não dá para extrair nada
 * @returns {string} sempre uma string, nunca um objeto
 */
export function mensagemDeErro(erro, padrao = 'Não foi possível concluir. Tente de novo.') {
  const detail = erro?.response?.data?.detail;

  if (typeof detail === 'string' && detail.trim()) return detail;

  // 422: lista de erros por campo
  if (Array.isArray(detail) && detail.length) {
    const linhas = detail.map(d => {
      const campo = nomeDoCampo(d?.loc);
      const texto = traduzir(d?.msg);
      return campo ? `${campo}: ${texto}` : texto;
    });
    return linhas.length === 1
      ? linhas[0]
      : 'Confira estes campos:\n· ' + linhas.join('\n· ');
  }

  // detail como objeto solto, ou erro de rede sem resposta
  if (detail && typeof detail === 'object') {
    return detail.msg || detail.message || padrao;
  }
  if (erro?.response?.status === 403) return 'Você não tem permissão para isso.';
  if (erro?.response?.status === 404) return 'Não encontrado.';
  if (erro?.message === 'Network Error') return 'Sem conexão com o servidor.';
  return padrao;
}
