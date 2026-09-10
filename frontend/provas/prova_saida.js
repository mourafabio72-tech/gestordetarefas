// Prova da Fase 25: a saída avisa o servidor, e leva o token junto.
//
//     node provas/prova_saida.js
//
// NASCEU DE UM DEFEITO EM PRODUÇÃO, e o defeito passou por tudo: a prova do
// backend estava verde (a rota devolve 200 com token válido), a suíte inteira
// passava, o carimbo batia com o HEAD, e mesmo assim o log de produção mostrou
// `POST /api/auth/logout 401`. A linha `LOGOUT` nunca foi escrita.
//
// A causa eram duas linhas na ordem errada. O interceptor de request do axios
// (`services/api.js`) lê o token do `localStorage` na hora de montar a
// requisição, e interceptor é assíncrono; a saída disparava a chamada e
// apagava o token na linha seguinte, de forma síncrona. Quando o interceptor
// ia buscar o token, ele já não existia.
//
// Por isso a função recebe o armazenamento e o chamador como parâmetro, igual
// ao `colherBilhete`: aqui eles são de mentira, e o que se confere é o que
// chegou na chamada, e em que ordem.

import assert from 'node:assert';
import { sair } from '../src/contexts/saida.js';

let n = 0;
function ok(titulo) {
  n += 1;
  console.log(`ok ${n}. ${titulo}`);
}

// Armazenamento de mentira que registra a ordem das operações, porque a ordem
// É o defeito: quem só olha o resultado final não vê nada de errado.
function cenario(tokenInicial) {
  const eventos = [];
  const dados = tokenInicial ? { token: tokenInicial } : {};
  return {
    eventos,
    armazenamento: {
      getItem: (k) => (k in dados ? dados[k] : null),
      removeItem: (k) => { delete dados[k]; eventos.push('apagou o token'); },
    },
    // O chamador vê o armazenamento no MOMENTO em que é chamado, que é
    // exatamente o que o interceptor do axios faz.
    chamarLogout: function (token) {
      eventos.push(`chamou com token=${token === undefined ? 'undefined' : token}`);
      this.tokenRecebido = token;
      this.tokenNoArmazenamento = dados.token ?? null;
      return Promise.resolve();
    },
    dados,
  };
}

// 1. PROVA POSITIVA. Sem ela, uma função que não fizesse nada passaria nos
// itens de "não quebra" e pareceria correta.
{
  const c = cenario('jwt-do-fabio');
  sair({ armazenamento: c.armazenamento, chamarLogout: c.chamarLogout.bind(c) });
  assert.strictEqual(c.tokenRecebido, 'jwt-do-fabio');
  ok('a chamada de saída recebe o token');
}

// 2. O DEFEITO DE PRODUÇÃO, em forma de item. O token tem de chegar na chamada
// mesmo tendo sido apagado do armazenamento: quem depende do armazenamento na
// hora da chamada manda a requisição sem credencial e leva 401.
{
  const c = cenario('jwt-do-fabio');
  sair({ armazenamento: c.armazenamento, chamarLogout: c.chamarLogout.bind(c) });
  assert.strictEqual(c.tokenNoArmazenamento, null,
    'o token já devia ter sido apagado quando a chamada acontece');
  assert.strictEqual(c.tokenRecebido, 'jwt-do-fabio',
    'e mesmo assim a chamada precisa levar o token, senão volta 401');
  ok('o token vai na chamada mesmo já tendo saído do armazenamento');
}

// 3. A sessão local acaba, aconteça o que acontecer com a rede.
{
  const c = cenario('jwt-do-fabio');
  sair({ armazenamento: c.armazenamento, chamarLogout: c.chamarLogout.bind(c) });
  assert.strictEqual(c.armazenamento.getItem('token'), null);
  ok('o token sai do armazenamento');
}

// 4. Chamada que estoura não pode prender ninguém dentro do sistema.
{
  const c = cenario('jwt-do-fabio');
  const quebrado = () => { throw new Error('rede caiu'); };
  assert.doesNotThrow(() =>
    sair({ armazenamento: c.armazenamento, chamarLogout: quebrado }));
  assert.strictEqual(c.armazenamento.getItem('token'), null);
  ok('chamada que estoura não impede a saída');
}

// 5. Promessa rejeitada também não, e sem deixar rejeição solta no processo.
{
  const c = cenario('jwt-do-fabio');
  const recusado = () => Promise.reject(new Error('502'));
  assert.doesNotThrow(() =>
    sair({ armazenamento: c.armazenamento, chamarLogout: recusado }));
  assert.strictEqual(c.armazenamento.getItem('token'), null);
  ok('promessa rejeitada não impede a saída nem vira erro solto');
}

// 6. Sem token não há sessão a encerrar, e uma chamada que só levaria 401 é
// ruído: um 401 no log do servidor parece tentativa de acesso indevido.
{
  const c = cenario(null);
  sair({ armazenamento: c.armazenamento, chamarLogout: c.chamarLogout.bind(c) });
  assert.strictEqual(c.tokenRecebido, undefined);
  assert.ok(!c.eventos.some((e) => e.startsWith('chamou')));
  ok('sem token, não chama o servidor');
}

// 7. Armazenamento que estoura ao ler (Safari em navegação privada faz isso)
// não pode derrubar a saída.
{
  const armazenamento = {
    getItem: () => { throw new Error('SecurityError'); },
    removeItem: () => {},
  };
  assert.doesNotThrow(() => sair({ armazenamento, chamarLogout: () => {} }));
  ok('armazenamento que estoura na leitura não derruba a saída');
}

console.log(`\nPROVA OK: ${n} checagens verdes`);
