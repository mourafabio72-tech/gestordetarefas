// Divisão do lote de modelos em remessas, e a soma dos resultados.
//
// Sem JSX e sem React, como os vizinhos, para provar em Node puro.
//
// Existe porque 36 arquivos numa requisição só não chegam ao servidor: o proxy
// corta por tamanho (413) ou por tempo, e o erro que volta não diz qual dos dois
// foi — a tela só mostrava "não consegui ler os arquivos", como se o problema
// fosse o conteúdo.

/** Arquivos por remessa. Baixo o bastante para não estourar limite de proxy. */
export const POR_REMESSA = 5;

/** Extensões que o leitor do servidor entende. */
export const EXTENSOES_ACEITAS = ['pdf', 'xlsx', 'xls'];

/**
 * Separa o que dá para enviar do que não dá.
 *
 * O descarte por extensão era silencioso: quem arrastava uma pasta com .docx e
 * .png no meio via "nada aconteceu" e não sabia por quê.
 */
export function separarAceitos(arquivos) {
  const aceitos = [], recusados = [];
  for (const f of Array.from(arquivos || [])) {
    const ext = (f.name || '').split('.').pop().toLowerCase();
    (EXTENSOES_ACEITAS.includes(ext) ? aceitos : recusados).push(f);
  }
  return { aceitos, recusados };
}

/** Quebra a lista em remessas de no máximo `tamanho`. */
export function emRemessas(arquivos, tamanho = POR_REMESSA) {
  const lista = Array.from(arquivos || []);
  const remessas = [];
  for (let i = 0; i < lista.length; i += tamanho) {
    remessas.push(lista.slice(i, i + tamanho));
  }
  return remessas;
}

/**
 * Junta os resultados das remessas num só, como se tivesse sido uma chamada.
 *
 * Remessa que falhou inteira vira uma linha de revisão POR ARQUIVO, com o
 * motivo. Some-la faria a conta não fechar — 36 enviados, 30 respondidos, e
 * nenhuma pista dos 6 que evaporaram.
 */
export function juntarResultados(partes) {
  const salvos = [], revisar = [];
  let total = 0;
  for (const p of partes || []) {
    total += p.total ?? (p.resultado?.resumo?.total || 0);
    if (p.erro) {
      for (const nome of p.nomes || []) {
        revisar.push({ nome_arquivo: nome, erro: p.erro, motivo: p.erro,
                       cnpj: null, candidatos: [] });
      }
      continue;
    }
    salvos.push(...(p.resultado?.salvos || []));
    revisar.push(...(p.resultado?.revisar || []));
  }
  return { resumo: { total, salvos: salvos.length, revisar: revisar.length },
           salvos, revisar };
}
