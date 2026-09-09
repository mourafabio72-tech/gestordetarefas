/**
 * A lógica do seletor de responsáveis, fora do JSX.
 *
 * Mora aqui pelo mesmo motivo de `contexts/bilhete.js` e `pages/filtroTarefas.js`:
 * assim ela roda em prova Node pura, sem navegador e sem montar componente. O
 * JSX fica só com o que é desenho.
 */

/** Marca ou desmarca uma pessoa, preservando a ordem de quem entrou primeiro.
 *
 * A ordem importa: o PRIMEIRO da lista é o principal, e é dele que sai o
 * supervisor da tarefa. Reordenar por id ou por nome mudaria o principal sem
 * ninguém pedir.
 */
export function alternar(ids, id) {
  const atuais = Array.isArray(ids) ? ids : [];
  return atuais.includes(id) ? atuais.filter((x) => x !== id) : [...atuais, id];
}

/** Texto comparável: sem acento e sem caixa. */
export function normalizar(texto) {
  return String(texto || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

/** Quem pode responder por um setor de uma empresa.
 *
 * Mesma regra que o servidor aplica antes de gravar: pessoa do tipo cliente e
 * pessoa bloqueada ficam de fora. A tela não é o controle de acesso, é o
 * conforto de não oferecer o que vai ser recusado.
 */
export function elegiveis(usuarios) {
  return (usuarios || []).filter((u) => u && !u.bloqueado && u.tipo !== 'cliente');
}

/** Filtra pelo que foi digitado na busca, e mantém marcado quem já foi escolhido.
 *
 * Escolhido some da lista quando a busca não casa com o nome dele, e some
 * junto a chance de desmarcar sem limpar a busca. Por isso quem está marcado
 * fica sempre visível.
 */
export function filtrar(pessoas, termo, marcados = []) {
  const alvo = normalizar(termo);
  if (!alvo) return pessoas || [];
  return (pessoas || []).filter(
    (u) => marcados.includes(u.id) || normalizar(u.nome).includes(alvo)
  );
}

/** Os escolhidos, na ordem em que foram escolhidos, prontos para virar chip. */
export function escolhidos(ids, pessoas) {
  const porId = new Map((pessoas || []).map((u) => [u.id, u]));
  return (ids || []).map((id) => porId.get(id)).filter(Boolean);
}

/** O rótulo do botão quando a lista está fechada. */
export function resumo(ids, pessoas) {
  const nomes = escolhidos(ids, pessoas).map((u) => u.nome);
  if (nomes.length === 0) return 'sem responsável';
  if (nomes.length === 1) return nomes[0];
  return `${nomes[0]} e mais ${nomes.length - 1}`;
}

/**
 * O estado do popover, como máquina.
 *
 * Existe para provar em Node o que a nota `Padrao_Modal_Nao_Fecha_Sozinho`
 * cobra: ESC e clique fora fecham o POPOVER, e o modal de cadastro continua
 * aberto. Quem devolve `fechaModal: true` em algum caso está errado.
 */
export const POPOVER_FECHADO = { aberto: null, busca: '' };

export function reduzirPopover(estado, evento) {
  const atual = estado || POPOVER_FECHADO;
  switch (evento.tipo) {
    case 'abrir':
      // Clicar no botão do popover já aberto fecha, como todo menu.
      return atual.aberto === evento.chave
        ? POPOVER_FECHADO
        : { aberto: evento.chave, busca: '' };
    case 'buscar':
      return { ...atual, busca: evento.texto };
    case 'esc':
    case 'clique-fora':
      // Nunca fecha o modal: só o popover. Com o popover já fechado, o evento
      // não faz nada, em vez de virar um "fechar" que sobe para o modal.
      return atual.aberto ? POPOVER_FECHADO : atual;
    case 'fechar':
      return POPOVER_FECHADO;
    default:
      return atual;
  }
}

/** O ESC deve ser engolido aqui? Só quando há popover aberto para fechar. */
export function escEhMeu(estado) {
  return Boolean((estado || POPOVER_FECHADO).aberto);
}
