// Agrupamento da lista de tarefas — por empresa, por setor, ou nenhum.
//
// Mesmo motivo dos vizinhos `filtroTarefas.js` e `payloadObrigacao.js`: sem
// JSX e sem React, para rodar em Node puro na prova, sem navegador e sem build.
//
// Por que agrupar: no mês fechado a tela traz centenas de cards, e a mesma
// obrigação aparece uma vez por empresa. Numa grade plana a razão social se
// repete em todo card e vira ruído; virando cabeçalho de seção, ela é escrita
// uma vez e o card fica com o que só ele tem.

/** Opções do seletor "Agrupar por". Valor vazio = grade plana. */
export const AGRUPAMENTOS = [
  { valor: 'empresa', rotulo: 'Empresa' },
  { valor: 'setor', rotulo: 'Setor' },
  { valor: '', rotulo: 'Não agrupar' },
];

/** Chave usada pelo grupo único da grade plana. */
export const GRUPO_UNICO = '_todas';

/** Rótulo dos que não têm o campo do agrupamento preenchido. */
export const SEM_GRUPO = 'Sem classificação';

/**
 * Devolve `[{ chave, titulo, tarefas }]` na ordem em que devem aparecer.
 *
 * `nomes` traduz o id em texto: `{ empresa: fn, setor: fn }`. A tela já tem
 * essas funções, e passá-las evita que este módulo saiba de API ou de estado.
 *
 * Ordena por título, com "Sem classificação" sempre por último — ele não é um
 * nome, é a ausência de um, e no meio da lista alfabética confundiria. A ordem
 * DENTRO do grupo é preservada: a lista chega ordenada por prazo do backend, e
 * reordenar aqui esconderia o que vence primeiro.
 */
export function agruparTarefas(tarefas, modo, nomes = {}) {
  const lista = tarefas || [];
  if (!modo) return [{ chave: GRUPO_UNICO, titulo: '', tarefas: lista }];

  const campo = modo === 'setor' ? 'setor_id' : 'empresa_id';
  const nomeDe = (modo === 'setor' ? nomes.setor : nomes.empresa) || (() => '');

  const grupos = new Map();
  for (const t of lista) {
    const id = t?.[campo] ?? null;
    // A chave é o id, não o nome: duas empresas de razão social parecida (ou
    // igual, que acontece em grupo econômico) continuam separadas.
    const chave = id === null || id === undefined ? '_sem' : String(id);
    if (!grupos.has(chave)) {
      grupos.set(chave, { chave, titulo: chave === '_sem' ? SEM_GRUPO : (nomeDe(id) || SEM_GRUPO), tarefas: [] });
    }
    grupos.get(chave).tarefas.push(t);
  }

  return [...grupos.values()].sort((a, b) => {
    if (a.chave === '_sem') return 1;
    if (b.chave === '_sem') return -1;
    return a.titulo.localeCompare(b.titulo, 'pt-BR');
  });
}
