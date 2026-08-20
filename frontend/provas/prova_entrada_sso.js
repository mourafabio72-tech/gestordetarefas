// Prova da decisão de entrada: bilhete do Hub × sessão guardada no navegador.
//
// Roda em Node puro, sem navegador e sem build:
//     node provas/prova_entrada_sso.js
//
// O caso que originou esta prova: quem clicava no card do Hub tendo um token
// VENCIDO no localStorage caía na tela de senha. O código antigo olhava o token
// primeiro e descartava o bilhete -- que era válido e tinha acabado de ser
// emitido. Como o JWT dura 8 horas, isso acontecia com quem usa o sistema todo
// dia, uma vez por dia, parecendo intermitente.

import assert from 'node:assert';
import { decidirEntrada } from '../src/contexts/entrada.js';

let n = 0;
function ok(titulo) {
  n += 1;
  console.log(`ok ${n}. ${titulo}`);
}

// 1. PROVA POSITIVA. Sem ela, uma função que devolvesse 'anonimo' sempre
// passaria nos itens seguintes parecendo correta.
{
  const e = decidirEntrada({ bilhete: 'abc123', token: null });
  assert.strictEqual(e.via, 'sso');
  assert.strictEqual(e.bilhete, 'abc123');
  ok('bilhete sem sessão guardada entra pelo SSO');
}

// 2. O BUG. Token no navegador não pode mais engolir o bilhete: era exatamente
// assim que a pessoa acabava na tela de senha vinda do Hub.
{
  const e = decidirEntrada({ bilhete: 'abc123', token: 'jwt-de-ontem' });
  assert.strictEqual(e.via, 'sso', 'bilhete tem de vencer a sessão guardada');
  assert.strictEqual(e.bilhete, 'abc123');
  ok('bilhete vence token guardado (o bug do token vencido)');
}

// 3. Mas a sessão de quem já estava dentro não pode ser perdida se o bilhete
// for recusado: ela volta como reserva.
{
  const e = decidirEntrada({ bilhete: 'abc123', token: 'jwt-valido' });
  assert.strictEqual(e.tokenReserva, 'jwt-valido');
  ok('token anterior volta como reserva, para bilhete recusado não custar a sessão');
}

// 4. Sem bilhete, quem tem sessão entra por ela, sem passar pelo SSO.
{
  const e = decidirEntrada({ bilhete: null, token: 'jwt-valido' });
  assert.strictEqual(e.via, 'sessao');
  assert.strictEqual(e.bilhete, null);
  assert.strictEqual(e.tokenReserva, null, 'sem SSO não há o que reservar');
  ok('sessão guardada sozinha entra direto');
}

// 5. Sem nada, tela de login.
{
  const e = decidirEntrada({ bilhete: null, token: null });
  assert.strictEqual(e.via, 'anonimo');
  ok('sem bilhete e sem sessão vai para o login');
}

// 6. Vazio e undefined são "não veio nada", não credencial. localStorage devolve
// null, mas a URL pode trazer `?sso=` sem valor.
{
  assert.strictEqual(decidirEntrada({ bilhete: '', token: '' }).via, 'anonimo');
  assert.strictEqual(decidirEntrada({}).via, 'anonimo');
  assert.strictEqual(decidirEntrada({ bilhete: '', token: 'jwt' }).via, 'sessao');
  ok('string vazia e ausente não valem como credencial');
}

// 7. Máquina compartilhada: bilhete de outra pessoa troca a conta em vez de
// deixar quem chegou trabalhando na sessão de quem saiu.
{
  const e = decidirEntrada({ bilhete: 'bilhete-da-maria', token: 'jwt-do-joao' });
  assert.strictEqual(e.via, 'sso', 'quem clicou no card entra como si mesmo');
  assert.strictEqual(e.tokenReserva, 'jwt-do-joao');
  ok('bilhete de outra pessoa troca a sessão, não é ignorado');
}

console.log(`\nPROVA OK: ${n} casos`);
