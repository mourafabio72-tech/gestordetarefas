/**
 * A regra do modal "Desvincular empresa", fora do JSX.
 *
 * Mora aqui pelo mesmo motivo de `recorteGeracao.js`: roda em prova Node pura.
 * Quem recusa de verdade é o servidor (`DesvincularEmpresaRequest`); a tela só
 * não oferece o que vai ser recusado (lista vazia, motivo curto), e diz o que falta.
 */
import { normalizar } from './seletorResponsaveis.js';

/** Por onde a obrigação alcança a empresa, como o servidor responde em `via`. */
export const ETIQUETAS_VIA = {
  regra: {
    rotulo: 'pela regra',
    dica: 'Alcança pelo regime ou segmento da empresa. Sai por exceção, que fica na lista de exceções da obrigação.',
  },
  vinculo: {
    rotulo: 'vinculada',
    dica: 'Vinculada à mão a esta empresa. Sai o vínculo.',
  },
  ambos: {
    rotulo: 'pela regra e vinculada',
    dica: 'Alcança pela regra e também está vinculada à mão. Sai o vínculo e entra a exceção.',
  },
};

const MOTIVO_MINIMO = 3;

export function podeDesvincular(ids, motivo) {
  return Array.isArray(ids) && ids.length > 0
    && String(motivo || '').trim().length >= MOTIVO_MINIMO;
}

/** O `title` do botão travado: diz o que falta, uma causa por vez. */
export function motivoDoBloqueio(ids, motivo) {
  if (!Array.isArray(ids) || ids.length === 0) return 'Marque ao menos uma obrigação.';
  if (String(motivo || '').trim().length < MOTIVO_MINIMO) {
    return 'Escreva o motivo, com pelo menos 3 letras.';
  }
  return undefined;
}

export function textoDoBotao(n) {
  if (!n) return 'Desvincular obrigações';
  return `Desvincular ${n} ${n === 1 ? 'obrigação' : 'obrigações'}`;
}

/** Quantas tarefas em aberto saem junto, somando só as obrigações marcadas. */
export function abertasMarcadas(lista, ids) {
  const marcadas = new Set(ids || []);
  return (lista || []).reduce((soma, o) => soma + (marcadas.has(o.id) ? (o.abertas || 0) : 0), 0);
}

export function resumoDoResultado(r) {
  const d = r?.desvinculadas || 0;
  const t = r?.tarefas_canceladas || 0;
  const obrig = `${d} ${d === 1 ? 'obrigação desvinculada' : 'obrigações desvinculadas'}`;
  if (!t) return `${obrig}. Nenhuma tarefa estava em aberto.`;
  return `${obrig} e ${t} ${t === 1 ? 'tarefa em aberto cancelada' : 'tarefas em aberto canceladas'}.`;
}

/** A busca do SelectBusca: sem acento e sem caixa; busca vazia devolve tudo. */
export function filtrarOpcoes(opcoes, termo) {
  const alvo = normalizar(termo);
  if (!alvo) return opcoes || [];
  return (opcoes || []).filter((o) => normalizar(o.rotulo).includes(alvo));
}
