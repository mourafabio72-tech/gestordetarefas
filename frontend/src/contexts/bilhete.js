// Bilhete de entrada vindo do Hub Zoaria, que chega como `?sso=` na URL.
//
// Fica em arquivo próprio, sem JSX e sem React, por dois motivos: a leitura da
// URL é a única lógica não trivial do consumo, e assim ela roda numa prova em
// Node puro (`frontend/provas/prova_sso_f4.js`) sem navegador e sem build.

/**
 * Tira o bilhete da URL e limpa o endereço na mesma passada.
 *
 * A limpeza acontece ANTES de qualquer chamada ao servidor, e não depois de o
 * consumo dar certo: o bilhete é credencial ao portador, e enquanto ele estiver
 * na barra ele vaza pelo histórico, pelo Referer da próxima página e por
 * qualquer captura de tela. Se o consumo falhar, o que se perdeu foi um bilhete
 * de 60 segundos e uso único, e a pessoa entra por e-mail e senha.
 *
 * Recebe `location` e `history` como parâmetro em vez de ler os globais, para
 * a prova poder passar objetos de mentira.
 *
 * @returns {string|null} o bilhete, ou null quando não veio nenhum
 */
export function colherBilhete(location, history) {
  const params = new URLSearchParams(location.search || '');
  if (!params.has('sso')) return null;

  const bilhete = params.get('sso') || '';
  params.delete('sso');

  // O resto da query e o hash são preservados: quem chega por um link do Hub
  // com outros parâmetros não pode perdê-los na limpeza.
  const resto = params.toString();
  const endereco = (location.pathname || '/') +
    (resto ? '?' + resto : '') +
    (location.hash || '');
  history.replaceState({}, '', endereco);

  return bilhete || null;
}
