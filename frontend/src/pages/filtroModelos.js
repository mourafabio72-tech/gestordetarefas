// Filtro da lista de modelos: empresa, tipo, obrigação e identificador.
//
// Sem JSX e sem React, como os vizinhos, para provar em Node puro.
//
// Filtra a lista que já está na tela, sem ida ao servidor: o repositório de
// modelos é da ordem de dezenas, e uma rota com filtros para isso seria
// resposta grande demais para o problema.

/** Estado inicial, e o que o "Limpar" devolve. */
export function filtrosVazios() {
  return { empresa: '', tipo: '', obrigacao: '', identificador: '' };
}

/** Algum filtro ativo? Comanda o botão de limpar e o contador. */
export function temFiltroAtivo(filtros) {
  return Object.values(filtros || {}).some((v) => String(v || '').trim() !== '');
}

/** minúsculo e sem acento — quem procura "irpj" acha "IRPJ". */
function normalizar(texto) {
  return String(texto || '')
    .normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().trim();
}

/**
 * Aplica os filtros. Campo vazio não filtra nada.
 *
 * Empresa, tipo e obrigação casam por IGUALDADE (vêm de select, e igualdade
 * parcial faria "apuração_ipi" ser escolhida e trazer "apuração_ipi_extra").
 * Identificador casa por TRECHO, porque é texto livre e quem procura lembra de
 * um pedaço.
 */
export function filtrarModelos(modelos, filtros) {
  const f = filtros || {};
  const trecho = normalizar(f.identificador);
  return (modelos || []).filter((m) => {
    if (f.empresa && String(m.empresa_nome || '') !== f.empresa) return false;
    if (f.tipo && String(m.tipo_documento || '') !== f.tipo) return false;
    if (f.obrigacao && String(m.obrigacao_nome || '') !== f.obrigacao) return false;
    // Modelo sem identificador some quando se procura por um: quem digitou algo
    // ali quer os que TÊM aquilo.
    if (trecho && !normalizar(m.identificador).includes(trecho)) return false;
    return true;
  });
}

/**
 * Valores presentes na lista, para o select não oferecer o que devolveria tela
 * vazia. Ordenado como texto, com os sem-valor de fora.
 */
export function valoresDe(modelos, campo) {
  const vistos = new Set();
  for (const m of modelos || []) {
    const v = m?.[campo];
    if (v) vistos.add(String(v));
  }
  return [...vistos].sort((a, b) => a.localeCompare(b, 'pt-BR'));
}
