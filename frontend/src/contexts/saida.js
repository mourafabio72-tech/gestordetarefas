// A saída do sistema, separada do React para poder ser provada.
//
// Parece uma função de três linhas, e é justamente por isso que ela existe
// como módulo: a ordem dessas três linhas foi um defeito em produção, e ordem
// não se prova olhando componente montado.
//
// O QUE ACONTECEU, em 2026-09-10. A primeira versão vivia dentro do
// `AuthContext` e era assim:
//
//     authAPI.logout().catch(() => {});   // dispara a chamada
//     localStorage.removeItem('token');   // síncrono, roda antes da requisição sair
//
// O interceptor de request do axios (`services/api.js`) lê o token do
// `localStorage` na hora de montar a requisição, e interceptor é assíncrono.
// Quando ele foi buscar, o token já tinha sido apagado pela linha de baixo: a
// requisição saiu sem `Authorization`, o servidor devolveu 401, e a linha
// `LOGOUT` nunca foi escrita. No log de produção aparecia
// `POST /api/auth/logout HTTP/1.1 401`.
//
// Nada disso foi pego pela prova do backend, e nem podia: lá a rota devolve
// 200 com token válido, e devolvia mesmo. O defeito estava entre o navegador e
// a rota.
//
// Por isso `armazenamento` e `chamarLogout` entram como parâmetro, no mesmo
// desenho do `colherBilhete`: dá para pôr objetos de mentira e conferir o que
// chegou na chamada, e não só o estado final.

/**
 * Encerra a sessão local e avisa o servidor.
 *
 * O token é lido ANTES de ser apagado e vai explícito na chamada, em vez de
 * ser buscado de novo no armazenamento lá na frente.
 *
 * A saída local acontece sempre: rede fora, servidor de pé mas recusando,
 * token vencido, nada disso pode prender a pessoa dentro do sistema. A falha
 * da chamada é engolida de propósito, e é o único lugar deste projeto onde
 * isso é o comportamento certo.
 */
export function sair({ armazenamento, chamarLogout }) {
  let token = null;
  try {
    token = armazenamento.getItem('token');
  } catch {
    // Safari em navegação privada estoura ao ler. Sem token não há o que
    // avisar, e a saída segue.
  }

  try {
    armazenamento.removeItem('token');
  } catch {
    // idem
  }

  // Sem token não existe sessão a encerrar, e a chamada só renderia um 401 no
  // log do servidor, que é ruído com cara de tentativa de acesso indevido.
  if (!token) return;

  try {
    const resultado = chamarLogout(token);
    if (resultado && typeof resultado.catch === 'function') {
      resultado.catch(() => {});
    }
  } catch {
    // A saída já aconteceu.
  }
}
