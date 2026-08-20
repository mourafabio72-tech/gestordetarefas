// Filtro da tela de Tarefas: empresa, setor, status, competência e faixa de
// vencimento.
//
// Fica em arquivo próprio, sem JSX e sem React, pelo mesmo motivo de
// `contexts/bilhete.js`: é a única lógica não trivial da tela, e assim ela roda
// numa prova em Node puro (`frontend/provas/prova_filtro_tarefas.js`), sem
// navegador e sem build.

/** Marca de "tarefa sem competência" no select — as avulsas, criadas à mão. */
export const SEM_COMPETENCIA = '_sem';

/**
 * Competências presentes nas tarefas, da mais recente para a mais antiga.
 *
 * Sai dos próprios dados, e não de uma lista fixa de meses: o filtro só oferece
 * competência que existe, em vez de deixar escolher uma que devolveria a tela
 * vazia. A ordenação é por AAAA+MM, porque "MM/AAAA" ordenado como texto
 * colocaria 12/2025 na frente de 01/2026.
 */
export function competenciasDe(tarefas) {
  const vistas = new Set();
  for (const t of tarefas || []) {
    if (t && t.competencia) vistas.add(t.competencia);
  }
  return [...vistas].sort((a, b) => {
    const [ma, aa] = a.split('/');
    const [mb, ab] = b.split('/');
    return (ab + mb).localeCompare(aa + ma);
  });
}

/** Só a parte da data de um ISO com hora. */
function soData(iso) {
  return (iso || '').slice(0, 10);
}

/**
 * Aplica todos os filtros. Campo vazio não filtra nada.
 *
 * O vencimento é comparado só por DATA, nunca com a hora junto: o campo chega
 * como ISO com horário, e uma tarefa que vence no próprio dia escolhido em
 * "até" ficaria de fora se a hora entrasse na conta.
 *
 * Tarefa SEM vencimento não entra em faixa de vencimento -- ela não venceu nem
 * deixou de vencer, e apareceria em qualquer intervalo se fosse tratada como
 * data zero.
 */
export function filtrarTarefas(tarefas, filtros) {
  const f = filtros || {};
  return (tarefas || []).filter(t => {
    if (f.empresa_id && t.empresa_id !== parseInt(f.empresa_id)) return false;
    if (f.status && t.status !== f.status) return false;
    if (f.setor_id && t.setor_id !== parseInt(f.setor_id)) return false;

    if (f.competencia) {
      if (f.competencia === SEM_COMPETENCIA) {
        if (t.competencia) return false;
      } else if (t.competencia !== f.competencia) {
        return false;
      }
    }

    if (f.venc_de || f.venc_ate) {
      const v = soData(t.data_vencimento);
      if (!v) return false;
      if (f.venc_de && v < f.venc_de) return false;
      if (f.venc_ate && v > f.venc_ate) return false;
    }
    return true;
  });
}

/**
 * Atalhos de vencimento. O padrão de barra de filtros da casa pede presets de
 * período, e estas são as três perguntas que se faz olhando prazo: o que já
 * passou, o que vem agora, e o que fecha no mês.
 *
 * Recebe `hoje` como parâmetro para a prova poder fixar o dia.
 */
export function presetsVencimento(hoje = new Date()) {
  const iso = (d) => {
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${d.getFullYear()}-${mm}-${dd}`;     // local, não UTC: perto da
  };                                             // meia-noite o UTC vira outro dia
  const ano = hoje.getFullYear();
  const mes = hoje.getMonth();
  return [
    { rotulo: 'Vencidas', de: '', ate: iso(new Date(ano, mes, hoje.getDate() - 1)) },
    { rotulo: 'Próx. 7 dias', de: iso(hoje), ate: iso(new Date(ano, mes, hoje.getDate() + 7)) },
    { rotulo: 'Este mês', de: iso(new Date(ano, mes, 1)), ate: iso(new Date(ano, mes + 1, 0)) },
  ];
}

/** Estado inicial (e o "Limpar filtros"). */
export function filtrosVazios(setor = '') {
  return { empresa_id: '', status: '', setor_id: setor,
           competencia: '', venc_de: '', venc_ate: '' };
}

/** Algum filtro ativo? Comanda o botão de limpar. */
export function temFiltroAtivo(filtros) {
  const f = filtros || {};
  return Boolean(f.empresa_id || f.status || f.setor_id
    || f.competencia || f.venc_de || f.venc_ate);
}
