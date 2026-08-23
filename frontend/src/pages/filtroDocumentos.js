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
export function filtrosVazios(tipo = 'recebidos') {
  return { tipo, baixado: '', empresa_id: '', setor_id: '', obrigacao_id: '', competencia: '',
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

/**
 * Algum filtro ativo? Comanda o botão de limpar e o aviso de resultado parcial.
 *
 * `tipo` não conta: ele escolhe QUAL acervo se olha, não filtra dentro dele.
 * Contá-lo faria o "Limpar" aparecer sempre, e limpar não deveria trocar de
 * acervo debaixo de quem está olhando.
 */
export function temFiltroAtivo(filtros) {
  const { tipo, ...resto } = filtros || {};
  return Object.keys(paraConsulta(resto)).length > 0;
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
 * Data e hora de um instante gravado pelo servidor, no fuso de quem lê.
 *
 * O backend grava em UTC. O ISO chega de duas formas conforme o banco: com
 * offset ("...+00:00") no Postgres, e sem nada no SQLite. Sem offset, o
 * JavaScript interpreta a string como hora LOCAL — e a hora do acesso aparecia
 * 3 horas adiantada, porque 18:16 UTC virava 18:16 de Brasília em vez de 15:16.
 *
 * Por isso o "Z" é acrescentado quando falta: diz ao navegador que aquilo é
 * UTC, e a conversão para o fuso de quem lê passa a ser dele.
 */
export function dataHoraBr(iso) {
  if (!iso) return '';
  const texto = String(iso);
  const temFuso = /(Z|[+-]\d{2}:?\d{2})$/.test(texto);
  const d = new Date(temFuso ? texto : texto + 'Z');
  if (Number.isNaN(d.getTime())) return '';
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} `
       + `${p(d.getHours())}:${p(d.getMinutes())}`;
}

/**
 * CSV do que está na tela, para quem precisa entregar a lista a um auditor.
 *
 * Aspas duplicadas e campo entre aspas: razão social com vírgula é comum, e sem
 * isso a planilha abriria com as colunas trocadas de lugar.
 */
export function paraCSV(documentos, tipo = 'recebidos') {
  const entregues = tipo === 'entregues';
  const col = ['Empresa', 'Obrigação', 'Tarefa', 'Competência',
               entregues ? 'Baixado em' : 'Entrega',
               ...(entregues ? ['Downloads'] : ['Protocolo']),
               'Responsáveis', 'Arquivo', 'No armazenamento'];
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const linhas = (documentos || []).map((d) => [
    d.empresa, d.obrigacao, d.titulo, d.competencia,
    entregues ? (dataBr(d.baixado_em) || 'não baixou') : dataBr(d.data_entrega),
    entregues ? (d.downloads ?? 0) : d.protocolo,
    (d.responsaveis || []).join(' / '), d.arquivo,
    d.no_volume ? 'sim' : 'NÃO',
  ].map(esc).join(','));
  return [col.map(esc).join(','), ...linhas].join('\n');
}
