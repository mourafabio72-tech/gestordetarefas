// Prova da mensagem de erro da API.
//
//     node provas/prova_erro_api.js
//
// O caso que originou: ao trocar o segmento de uma empresa, a tela mostrava
// "[object Object]". O formulário envia TODOS os campos, o "Fechamento contábil"
// ia em branco, o backend recusava com 422, e o 422 do FastAPI traz `detail`
// como LISTA de objetos -- que as telas jogavam direto num alert.

import assert from 'node:assert';
import { mensagemDeErro } from '../src/services/erroApi.js';

let n = 0;
const ok = (t) => { n += 1; console.log(`ok ${n}. ${t}`); };
const erro422 = (lista) => ({ response: { status: 422, data: { detail: lista } } });

// 1. PROVA POSITIVA. Sem ela, uma função que devolvesse sempre o padrão passaria.
{
  const m = mensagemDeErro({ response: { data: { detail: 'CNPJ inválido.' } } });
  assert.strictEqual(m, 'CNPJ inválido.');
  ok('detail em texto passa direto');
}

// 2. O BUG. Lista de objetos tem de virar frase, nunca "[object Object]".
{
  const m = mensagemDeErro(erro422([
    { loc: ['body', 'fechamento_dia'], msg: 'Input should be a valid integer, unable to parse string as an integer' },
  ]));
  assert.ok(!m.includes('[object'), 'não pode vazar objeto para a tela');
  assert.ok(m.includes('Dia do fechamento'), 'nomeia o campo como a pessoa o vê');
  assert.ok(m.includes('número inteiro'), 'diz o que está errado, em português');
  ok('erro de validação vira frase com o nome do campo');
}

// 3. Vários campos de uma vez: lista legível, não um parágrafo colado.
{
  const m = mensagemDeErro(erro422([
    { loc: ['body', 'razao_social'], msg: 'Field required' },
    { loc: ['body', 'email'], msg: 'value is not a valid email address' },
  ]));
  assert.ok(m.includes('Razão social'));
  assert.ok(m.includes('E-mail'));
  assert.ok(m.includes('\n·'), 'mais de um erro vira lista');
  ok('vários campos viram uma lista');
}

// 4. Campo sem tradução cadastrada continua legível.
{
  const m = mensagemDeErro(erro422([{ loc: ['body', 'campo_novo_qualquer'], msg: 'Field required' }]));
  assert.ok(m.includes('campo novo qualquer'), 'troca o sublinhado por espaço');
  assert.ok(m.includes('obrigatório'));
  ok('campo desconhecido não quebra nem vaza snake_case');
}

// 5. O que não é 422.
{
  assert.strictEqual(mensagemDeErro({ response: { status: 403, data: {} } }),
    'Você não tem permissão para isso.');
  assert.strictEqual(mensagemDeErro({ response: { status: 404, data: {} } }), 'Não encontrado.');
  assert.strictEqual(mensagemDeErro({ message: 'Network Error' }), 'Sem conexão com o servidor.');
  ok('403, 404 e queda de rede têm mensagem própria');
}

// 6. Sempre string, mesmo com entrada estranha — é o que vai para o alert.
{
  for (const caso of [undefined, null, {}, { response: {} }, { response: { data: {} } },
                      { response: { data: { detail: [] } } },
                      { response: { data: { detail: {} } } }]) {
    assert.strictEqual(typeof mensagemDeErro(caso), 'string', JSON.stringify(caso));
  }
  ok('nunca devolve objeto, seja qual for a entrada');
}

// 7. O padrão de cada tela é respeitado quando não há detail.
{
  assert.strictEqual(mensagemDeErro({ response: { data: {} } }, 'Erro ao salvar o modelo.'),
    'Erro ao salvar o modelo.');
  ok('mensagem específica da tela prevalece sobre a genérica');
}

console.log(`\nPROVA OK: ${n} casos`);
