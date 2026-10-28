// Prova de frontend/src/pages/conferenciaTexto.js: Node puro, sem build.
//   node frontend/provas/prova_texto_conferencia.js
//
// Caso de 2026-10-27, guia de ISS em imagem: a janela de envio dizia "CNPJ e
// competência batem com a tarefa" quando só o CNPJ tinha sido lido no arquivo.
// A faixa passa a dizer o que foi lido, e o que falta conferir a olho.

import { textoConferencia } from '../src/pages/conferenciaTexto.js';

let ok = 0, falhou = 0;
const eq = (nome, obtido, esperado) => {
  if (JSON.stringify(obtido) === JSON.stringify(esperado)) { ok++; console.log(`  ok  ${nome}`); }
  else { falhou++; console.log(`FALHA  ${nome}\n       obtido:   ${JSON.stringify(obtido)}\n       esperado: ${JSON.stringify(esperado)}`); }
};
const tipo = (c) => textoConferencia(c)?.tipo;
const texto = (c) => textoConferencia(c)?.texto || '';

eq('sem conferencia, sem faixa', textoConferencia(null), null);
eq('os dois lidos e batendo: ok', tipo({ ok: true, leu_algo: true, cnpj_lido: '1', competencia_lida: '09/2026' }), 'ok');
const soCnpj = { ok: true, leu_algo: true, cnpj_lido: '1', competencia_lida: null };
eq('so o CNPJ lido: parcial', tipo(soCnpj), 'parcial');
eq('so o CNPJ lido: nao diz que a competencia bate', texto(soCnpj).includes('competência batem'), false);
eq('so o CNPJ lido: manda conferir o mes', /competência não foi lida/.test(texto(soCnpj)), true);
eq('so a competencia lida: manda conferir a empresa',
  /CNPJ não foi lido/.test(texto({ ok: true, leu_algo: true, cnpj_lido: null, competencia_lida: '09/2026' })), true);
eq('nada lido: aviso de arquivo sem texto', tipo({ ok: true, leu_algo: false }), 'nada');
eq('contradiz: os alertas mandam', tipo({ ok: false, leu_algo: true, alertas: ['outro CNPJ'] }), 'contradiz');

console.log(`\n${falhou ? 'PROVA FALHOU' : 'PROVA OK'}: ${ok} ok, ${falhou} falha(s)`);
if (falhou) process.exit(1);
