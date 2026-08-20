// Como se entra no Tareffas quando a página abre: pelo bilhete que veio do Hub,
// pela sessão já guardada no navegador, ou por ninguém (tela de login).
//
// Fica em arquivo próprio, sem JSX e sem React, pelo mesmo motivo de
// `bilhete.js`: é a única decisão não trivial da abertura, e assim ela roda numa
// prova em Node puro (`frontend/provas/prova_entrada_sso.js`), sem navegador e
// sem build.

/**
 * Decide por onde entrar.
 *
 * O BILHETE VENCE a sessão guardada, e isso não é detalhe: quem clicou no card
 * do Hub quer entrar como a pessoa que está logada no Hub, agora. A sessão que
 * estava aqui pode ser de ontem (o JWT dura 8 horas e vence de um dia para o
 * outro) ou de outra pessoa, na máquina que várias usam.
 *
 * A ordem anterior era o contrário -- token primeiro, e o bilhete descartado --
 * e produzia o pior desfecho possível: quem clicava no card com um token
 * vencido no navegador caía na tela de senha segurando um bilhete válido, que
 * tinha acabado de ser jogado fora.
 *
 * O token anterior volta junto como RESERVA. Bilhete recusado (vencido, já
 * usado) não pode custar a sessão de quem já estava dentro e trabalhando.
 *
 * @param {{bilhete: string|null, token: string|null}} estado
 * @returns {{via: 'sso'|'sessao'|'anonimo', bilhete: string|null, tokenReserva: string|null}}
 */
export function decidirEntrada({ bilhete, token }) {
  if (bilhete) {
    return { via: 'sso', bilhete, tokenReserva: token || null };
  }
  if (token) {
    return { via: 'sessao', bilhete: null, tokenReserva: null };
  }
  return { via: 'anonimo', bilhete: null, tokenReserva: null };
}
