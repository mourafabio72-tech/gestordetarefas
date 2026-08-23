// Divisão do lote de modelos em remessas, e a soma dos resultados.
//
// Sem JSX e sem React, como os vizinhos, para provar em Node puro.
//
// Existe porque 36 arquivos numa requisição só não chegam ao servidor: o proxy
// corta por tamanho (413) ou por tempo, e o erro que volta não diz qual dos dois
// foi — a tela só mostrava "não consegui ler os arquivos", como se o problema
// fosse o conteúdo.

/** Arquivos por remessa na primeira tentativa. */
export const POR_REMESSA = 5;

/**
 * Envia uma remessa; se ela falhar, DIVIDE AO MEIO e tenta cada metade.
 *
 * O limite que derruba a requisição — tamanho ou tempo — depende dos arquivos,
 * e não dá para adivinhar um número que sirva para toda pasta. Cinco planilhas
 * pesadas estouram onde cinco PDFs pequenos passam. Dividir na falha encontra o
 * tamanho que passa, sem punir o caso comum com remessas minúsculas.
 *
 * Um arquivo sozinho que falha é o fim da linha: aí o problema é ele, não o
 * tamanho da remessa, e insistir só demoraria mais para dizer a mesma coisa.
 *
 * `enviar(lista)` faz a chamada. `aoProgredir(n)` recebe quantos arquivos já
 * foram resolvidos, para a barra andar mesmo durante as retentativas.
 */
export async function enviarComDivisao(remessa, enviar, aoProgredir = () => {}) {
  try {
    const resultado = await enviar(remessa);
    aoProgredir(remessa.length);
    return [{ total: remessa.length, resultado }];
  } catch (err) {
    if (remessa.length === 1) {
      aoProgredir(1);
      return [{ total: 1, erro: err?.mensagem || err?.message || 'Falhou ao enviar',
                nomes: [remessa[0]?.name] }];
    }
    const meio = Math.ceil(remessa.length / 2);
    const a = await enviarComDivisao(remessa.slice(0, meio), enviar, aoProgredir);
    const b = await enviarComDivisao(remessa.slice(meio), enviar, aoProgredir);
    return [...a, ...b];
  }
}

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
