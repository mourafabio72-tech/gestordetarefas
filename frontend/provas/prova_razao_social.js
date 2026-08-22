// Prova de frontend/src/pages/razaoSocial.js — Node puro, sem build.
//   node frontend/provas/prova_razao_social.js

import { formatarRazaoSocial as f } from '../src/pages/razaoSocial.js';

let ok = 0, falhou = 0;
const eq = (entrada, esperado) => {
  const obtido = f(entrada);
  if (obtido === esperado) { ok++; console.log(`  ok  ${JSON.stringify(entrada)} -> ${JSON.stringify(obtido)}`); }
  else { falhou++; console.log(`FALHA  ${JSON.stringify(entrada)}\n       obtido:   ${JSON.stringify(obtido)}\n       esperado: ${JSON.stringify(esperado)}`); }
};

console.log('\n1) Os três nomes do print, que era o caso concreto');
eq('Mark Building Gerenc. Predial Ltda.', 'Mark Building Gerenc. Predial Ltda.');
eq('RIO BRAVO COM. DE ARMAS MUNIÇÕES E ACESS. LTDA', 'Rio Bravo Com. de Armas Munições e Acess. Ltda');
eq('TROPS CENTRO DE ESP. E LAZER LTDA-ME', 'Trops Centro de Esp. e Lazer Ltda-ME');

console.log('\n2) Quem já tem minúscula fica intacto — só apara espaço sobrando');
eq('  Alpha   Serviços Ltda  ', 'Alpha Serviços Ltda');
eq('CW Administra Ltda.', 'CW Administra Ltda.');

console.log('\n3) Sigla do grupo continua sigla, palavra curta não vira sigla');
eq('MKB PARTICIPACOES LTDA', 'MKB Participacoes Ltda');
eq('IWC COMERCIO LTDA', 'IWC Comercio Ltda');
eq('RIO NEGRO TRANSPORTES', 'Rio Negro Transportes');
eq('CW ADMINISTRA LTDA', 'CW Administra Ltda');
eq('BPS4 OUTSOURCING LTDA', 'BPS4 Outsourcing Ltda');

console.log('\n4) Átona só perde a maiúscula longe do começo');
eq('DE PAULA E FILHOS LTDA', 'De Paula e Filhos Ltda');
eq('CASA DAS TINTAS DO NORTE', 'Casa das Tintas do Norte');

console.log('\n5) Forma jurídica com grafia própria');
eq('COMERCIAL XPTO S/A', 'Comercial Xpto S.A.');
eq('PADARIA CENTRAL EIRELI', 'Padaria Central Eireli');
eq('GRAFICA SOL LTDA-EPP', 'Grafica Sol Ltda-EPP');

console.log('\n6) Abreviação com ponto é palavra encurtada, não sigla');
eq('ESP. E LAZER', 'Esp. e Lazer');
eq('IND. E COM. DE PECAS', 'Ind. e Com. de Pecas');

console.log('\n7) Vazio e nulo não quebram o cabeçalho');
eq('', ''); eq(null, ''); eq(undefined, ''); eq('   ', '');

console.log(`\n${falhou === 0 ? 'TUDO VERDE' : 'VERMELHO'} — ${ok} ok, ${falhou} falhou\n`);
process.exit(falhou === 0 ? 0 : 1);
