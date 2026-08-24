// Filtro da tela de Tarefas: empresa, setor, status, competência e faixa de
// vencimento.
//
// Também é o alvo dos links do Painel: cada número de lá abre esta tela já
// filtrada, e para o número bater com a lista o critério tem de ser o MESMO.
// Por isso "atrasada" e "vence hoje" saem de `alertaDaTarefa`, que lê o prazo
// interno — e não da faixa de vencimento, que lê o prazo legal.
//
// Fica em arquivo próprio, sem JSX e sem React, pelo mesmo motivo de
// `contexts/bilhete.js`: é a única lógica não trivial da tela, e assim ela roda
// numa prova em Node puro (`frontend/provas/prova_filtro_tarefas.js`), sem
// navegador e sem build.

import { alertaDaTarefa } from './alertaPrazo.js';   // com extensão: a prova roda em Node puro

/** Marca de "tarefa sem competência" no select — as avulsas, criadas à mão. */
export const SEM_COMPETENCIA = '_sem';

/** Recortes que o Painel manda por link, na chave `alerta` da URL. */
export const RECORTES = {
  aberta:   'em aberto',
  atrasada: 'atrasadas',
  hoje:     'vencem hoje',
  semana:   'vencem em até 7 dias',
};

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
export function filtrarTarefas(tarefas, filtros, hoje = new Date()) {
  const f = filtros || {};
  const termo = (f.texto || '').trim().toLowerCase();
  return (tarefas || []).filter(t => {
    // Busca pelo título da tarefa. Com centenas de tarefas no mês, achar "a
    // conciliação da Mark Building" pelos selects é caça ao tesouro.
    if (termo && !(t.titulo || '').toLowerCase().includes(termo)) return false;
    // Por pessoa: conta como dela se é responsável (um dos vários) ou supervisor.
    if (f.usuario_id) {
      const uid = parseInt(f.usuario_id);
      const ehResp = (t.responsaveis || []).some(r => r.id === uid);
      const ehSup = t.supervisor && t.supervisor.id === uid;
      if (!ehResp && !ehSup) return false;
    }
    if (f.empresa_id && t.empresa_id !== parseInt(f.empresa_id)) return false;
    if (f.status && t.status !== f.status) return false;
    if (f.setor_id && t.setor_id !== parseInt(f.setor_id)) return false;
    if (f.multa && !t.gera_multa) return false;

    // Prioridade: 'alta_urgente' junta as duas, porque na prática elas são a
    // mesma fila — o que não pode esperar.
    if (f.prioridade) {
      const aceitas = f.prioridade === 'alta_urgente' ? ['alta', 'urgente'] : [f.prioridade];
      if (!aceitas.includes(t.prioridade)) return false;
    }

    if (f.alerta === 'aberta') {
      // 'aberta' não sai do semáforo: tarefa SEM prazo também está aberta, e
      // no semáforo ela é 'neutro', igual à cancelada.
      if (t.status === 'concluida' || t.status === 'cancelada') return false;
    } else if (f.alerta) {
      const nivel = alertaDaTarefa(t, hoje).nivel;
      if (f.alerta === 'semana') {
        if (nivel !== 'hoje' && nivel !== 'proximo') return false;
      } else if (nivel !== f.alerta) {
        return false;
      }
    }

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
  // Rótulos curtos: a barra tem de caber numa linha só, e o nome por extenso
  // fica no `title` de cada botão.
  return [
    { rotulo: 'Vencidas', titulo: 'Vencimento já passou',
      de: '', ate: iso(new Date(ano, mes, hoje.getDate() - 1)) },
    { rotulo: '7 dias', titulo: 'Vence nos próximos 7 dias',
      de: iso(hoje), ate: iso(new Date(ano, mes, hoje.getDate() + 7)) },
    { rotulo: 'Mês', titulo: 'Vence dentro deste mês',
      de: iso(new Date(ano, mes, 1)), ate: iso(new Date(ano, mes + 1, 0)) },
  ];
}

/** Estado inicial (e o "Limpar filtros"). */
export function filtrosVazios(setor = '') {
  return { empresa_id: '', status: '', setor_id: setor,
           competencia: '', venc_de: '', venc_ate: '',
           texto: '', usuario_id: '', alerta: '', prioridade: '', multa: false };
}

/**
 * Filtro montado a partir da URL — é assim que o Painel entrega o recorte.
 *
 * Aceita URLSearchParams ou um objeto simples, para a prova rodar sem
 * navegador. Chave desconhecida é ignorada: link velho no favorito de alguém
 * abre a tela sem filtro, e não quebrada.
 */
export function filtrosDaUrl(params) {
  const ler = (k) => {
    const v = params && typeof params.get === 'function' ? params.get(k) : (params || {})[k];
    return v == null ? '' : String(v);
  };
  return {
    ...filtrosVazios(),
    empresa_id: ler('empresa'),
    setor_id: ler('setor'),
    usuario_id: ler('usuario'),
    status: ler('status'),
    competencia: ler('competencia'),
    alerta: RECORTES[ler('alerta')] ? ler('alerta') : '',
    prioridade: ler('prioridade'),
    multa: ler('multa') === '1',
  };
}

/** Como dizer, na tela, qual recorte veio do Painel. */
export function rotuloDoRecorte(filtros) {
  const f = filtros || {};
  const partes = [];
  if (f.alerta && RECORTES[f.alerta]) partes.push(RECORTES[f.alerta]);
  if (f.prioridade === 'alta_urgente') partes.push('prioridade alta ou urgente');
  else if (f.prioridade) partes.push(`prioridade ${f.prioridade}`);
  if (f.multa) partes.push('que geram multa');
  return partes.join(', ');
}

/** Algum filtro ativo? Comanda o botão de limpar. */
export function temFiltroAtivo(filtros) {
  const f = filtros || {};
  return Boolean(f.empresa_id || f.status || f.setor_id
    || f.competencia || f.venc_de || f.venc_ate
    || (f.texto || '').trim() || f.usuario_id
    || f.alerta || f.prioridade || f.multa);
}
