// Filtros da tela de Documentos: o que vai para a URL da consulta e o que a
// tela mostra sobre o estado deles.
//
// Sem JSX e sem React, como os vizinhos, para rodar em prova Node pura. Aqui
// isso vale por um motivo concreto: campo vazio NÃO pode virar parâmetro. Um
// `empresa_id=` em branco chega ao backend como string vazia e derruba a
// consulta com 422 — foi assim que o formulário de empresa quebrou antes.

export const EXTENSOES = [
  { valor: '', rotulo: 'Qualquer tipo' },
  { valor: 'pdf', rotulo: 'PDF' },
  { valor: 'xlsx', rotulo: 'Excel (xlsx)' },
  { valor: 'xls', rotulo: 'Excel (xls)' },
  { valor: 'png', rotulo: 'Imagem (png)' },
  { valor: 'jpg', rotulo: 'Imagem (jpg)' },
];

/** Estado inicial, e o que o "Limpar" devolve. */
export function filtrosVazios() {
  return { empresa_id: '', setor_id: '', obrigacao_id: '', competencia: '',
           entrega_de: '', entrega_ate: '', usuario_id: '', texto: '', extensao: '' };
}

/** Só os campos preenchidos viram parâmetro da consulta. */
export function paraConsulta(filtros, limite) {
  const saida = {};
  for (const [chave, valor] of Object.entries(filtros || {})) {
    const v = typeof valor === 'string' ? valor.trim() : valor;
    if (v !== '' && v !== null && v !== undefined) saida[chave] = v;
  }
  if (limite) saida.limite = limite;
  return saida;
}

/** Algum filtro ativo? Comanda o botão de limpar e o aviso de resultado parcial. */
export function temFiltroAtivo(filtros) {
  return Object.keys(paraConsulta(filtros)).length > 0;
}

/** Atalhos de período de ENTREGA — as três perguntas que se faz num acervo. */
export function periodos(hoje = new Date()) {
  const iso = (d) => {
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${d.getFullYear()}-${mm}-${dd}`;          // local, não UTC
  };
  const a = hoje.getFullYear(), m = hoje.getMonth();
  return [
    { rotulo: 'Este mês', de: iso(new Date(a, m, 1)), ate: iso(new Date(a, m + 1, 0)) },
    { rotulo: 'Mês passado', de: iso(new Date(a, m - 1, 1)), ate: iso(new Date(a, m, 0)) },
    { rotulo: 'Este ano', de: iso(new Date(a, 0, 1)), ate: iso(new Date(a, 11, 31)) },
  ];
}

/** Data ISO -> DD/MM/AAAA, sem passar por new Date (que jogaria para o dia anterior). */
export function dataBr(iso) {
  const d = (iso || '').slice(0, 10);
  if (d.length !== 10) return '';
  return `${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(0, 4)}`;
}

/**
 * CSV do que está na tela, para quem precisa entregar a lista a um auditor.
 *
 * Aspas duplicadas e campo entre aspas: razão social com vírgula é comum, e sem
 * isso a planilha abriria com as colunas trocadas de lugar.
 */
export function paraCSV(documentos) {
  const col = ['Empresa', 'Obrigação', 'Tarefa', 'Competência', 'Entrega',
               'Protocolo', 'Responsáveis', 'Arquivo', 'No armazenamento'];
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const linhas = (documentos || []).map((d) => [
    d.empresa, d.obrigacao, d.titulo, d.competencia, dataBr(d.data_entrega),
    d.protocolo, (d.responsaveis || []).join(' / '), d.arquivo,
    d.no_volume ? 'sim' : 'NÃO',
  ].map(esc).join(','));
  return [col.map(esc).join(','), ...linhas].join('\n');
}
