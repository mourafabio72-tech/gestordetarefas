// Colisão de identificador: quando é problema e quando é variação.
//
// Sem JSX e sem React, como os vizinhos, para provar em Node puro.
//
// O backend devolve, para cada candidato, a lista de obrigações cujo
// identificador se parece com ele. Mas parecer com a PRÓPRIA obrigação não é
// colisão — é exatamente o que se quer ao cadastrar o segundo layout do mesmo
// documento (Lucro Real e Lucro Presumido apontando para a mesma apuração).
//
// Sem essa distinção, a tela mostra aviso âmbar justamente quando a pessoa está
// fazendo a coisa certa, e ensina a evitar o que deveria fazer.

/**
 * Estado de um candidato diante da obrigação escolhida agora.
 *
 * 'livre'     — não parece com identificador de ninguém
 * 'variacao'  — parece só com a obrigação escolhida: é outro layout do mesmo documento
 * 'conflito'  — parece com OUTRA obrigação; aí o matcher ficaria ambíguo
 */
export function estadoDoCandidato(candidato, nomeObrigacaoEscolhida) {
  const colide = (candidato?.colide_com || []).filter(Boolean);
  if (!colide.length) return { estado: 'livre', outras: [] };

  const escolhida = (nomeObrigacaoEscolhida || '').trim().toLowerCase();
  const outras = colide.filter((n) => String(n).trim().toLowerCase() !== escolhida);
  if (!outras.length) return { estado: 'variacao', outras: [] };
  return { estado: 'conflito', outras };
}

/** Frase para o `title` do botão — o porquê, não só a cor. */
export function explicar(estado, outras) {
  if (estado === 'variacao') {
    return 'Já existe algo parecido NESTA obrigação. Serve como variação — '
         + 'outro layout do mesmo documento.';
  }
  if (estado === 'conflito') {
    return `Parecido com o identificador de: ${outras.join(', ')}. `
         + 'Usar assim deixaria o e-validador em dúvida entre as duas.';
  }
  return 'Livre: não parece com identificador de nenhuma obrigação.';
}
