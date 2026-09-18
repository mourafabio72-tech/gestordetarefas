// Recorte de empresas do modal "Gerar tarefas do mês".
//
// Fica em arquivo próprio, sem JSX, no molde de payloadObrigacao.js, para rodar
// numa prova em Node puro (frontend/provas/prova_recorte_regime.js).
//
// A tela converte o recorte em ids de empresa e chama a rota de sempre. Quem
// decide o que cada obrigação alcança continua sendo o backend (interseção em
// gerador.py): escolher um regime aqui não inscreve empresa em obrigação.

/** Os 7 regimes do modal, com os valores de `Empresa.regime_tributario`.
 *  "indefinido" fica de fora: empresa sem regime cadastrado não entra por regime. */
export const REGIMES_GERACAO = [
  { valor: 'simples_nacional', rotulo: 'Simples Nacional' },
  { valor: 'lucro_real', rotulo: 'Lucro Real' },
  { valor: 'lucro_presumido', rotulo: 'Lucro Presumido' },
  { valor: 'mei', rotulo: 'MEI' },
  { valor: 'isento', rotulo: 'Isento' },
  { valor: 'imune', rotulo: 'Imune' },
  { valor: 'terceiro_setor', rotulo: 'Terceiro Setor' },
];

const VALIDOS = new Set(REGIMES_GERACAO.map((r) => r.valor));

/** Ids das empresas cujo regime está entre os marcados. Bloqueada e inativa
 *  ficam fora, como no gerador (`empresas_alvo`, gerador.py): a contagem do
 *  modal não pode prometer tarefa que não sai. */
export function empresasDosRegimes(empresas, regimes) {
  const marcados = new Set((regimes || []).filter((r) => VALIDOS.has(r)));
  return (empresas || [])
    .filter((e) => e.ativo !== false && !e.bloqueado)
    .filter((e) => marcados.has(e.regime_tributario))
    .map((e) => e.id);
}

/** O que vai em `empresa_ids`: null em "todas", a lista nos outros modos. */
export function idsDoRecorte(modo, escolhidas, regimes, empresas) {
  if (modo === 'escolhidas') return [...(escolhidas || [])];
  if (modo === 'regime') return empresasDosRegimes(empresas, regimes);
  // Só "todas" vira null. Modo desconhecido falha fechado, com lista vazia,
  // e o podeGerar bloqueia: nunca gera o escritório inteiro por engano.
  return modo === 'todas' ? null : [];
}

/** Falso quando o recorte sairia vazio. O backend lê `[]` como "todas", então
 *  lista vazia fora do modo "todas" nunca pode chegar à rota. */
export function podeGerar(modo, escolhidas, regimes, empresas) {
  const ids = idsDoRecorte(modo, escolhidas, regimes, empresas);
  return ids === null || ids.length > 0;
}

/** "Simples Nacional, Lucro Real e MEI": os marcados, na ordem da lista. */
export function nomesDosRegimes(regimes) {
  const marcados = new Set(regimes || []);
  const nomes = REGIMES_GERACAO.filter((r) => marcados.has(r.valor)).map((r) => r.rotulo);
  if (nomes.length <= 1) return nomes.join('');
  return `${nomes.slice(0, -1).join(', ')} e ${nomes[nomes.length - 1]}`;
}
