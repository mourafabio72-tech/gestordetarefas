// Prova de frontend/src/pages/colisaoIdentificador.js — Node puro, sem build.
//   node frontend/provas/prova_colisao_identificador.js

import { estadoDoCandidato, explicar } from '../src/pages/colisaoIdentificador.js';

let ok = 0, falhou = 0;
const eq = (nome, obtido, esperado) => {
  if (JSON.stringify(obtido) === JSON.stringify(esperado)) { ok++; console.log(`  ok  ${nome}`); }
  else { falhou++; console.log(`FALHA  ${nome}\n       obtido:   ${JSON.stringify(obtido)}\n       esperado: ${JSON.stringify(esperado)}`); }
};
const est = (colide, escolhida) => estadoDoCandidato({ colide_com: colide }, escolhida).estado;

console.log('\n1) O caso que motivou: dois layouts, uma obrigação');
// Lucro Real e Lucro Presumido são documentos diferentes que baixam a MESMA
// apuração. O segundo parece com o primeiro, e isso é o certo.
eq('parecido só com a obrigação escolhida é VARIAÇÃO',
   est(['apuração_irpj_csll'], 'apuração_irpj_csll'), 'variacao');
eq('e não deve assustar quem está certo',
   explicar('variacao', []).includes('Serve como variação'), true);

console.log('\n2) Parecido com OUTRA obrigação é conflito de verdade');
eq('outra obrigação', est(['sped_fiscal'], 'apuração_irpj_csll'), 'conflito');
eq('a mesma e outra junto: continua conflito',
   est(['apuração_irpj_csll', 'sped_fiscal'], 'apuração_irpj_csll'), 'conflito');
eq('o aviso nomeia a outra',
   explicar('conflito', ['sped_fiscal']).includes('sped_fiscal'), true);
eq('e diz o efeito',
   explicar('conflito', ['x']).includes('dúvida'), true);
eq('só as OUTRAS aparecem no aviso',
   estadoDoCandidato({ colide_com: ['apuração_irpj_csll', 'sped_fiscal'] }, 'apuração_irpj_csll').outras,
   ['sped_fiscal']);

console.log('\n3) Sem colisão nenhuma');
eq('lista vazia', est([], 'apuração_irpj_csll'), 'livre');
eq('campo ausente', estadoDoCandidato({}, 'x').estado, 'livre');
eq('candidato nulo', estadoDoCandidato(null, 'x').estado, 'livre');

console.log('\n4) Bordas da comparação de nome');
eq('caixa diferente não vira conflito', est(['APURAÇÃO_IRPJ_CSLL'], 'apuração_irpj_csll'), 'variacao');
eq('espaço em volta idem', est(['  apuração_irpj_csll  '], 'apuração_irpj_csll'), 'variacao');
eq('sem obrigação escolhida, tudo é conflito', est(['apuração_irpj_csll'], ''), 'conflito');
eq('nome nulo na lista é ignorado', est([null, 'sped_fiscal'], 'sped_fiscal'), 'variacao');

console.log(`\n${falhou === 0 ? 'TUDO VERDE' : 'VERMELHO'} — ${ok} ok, ${falhou} falhou\n`);
process.exit(falhou === 0 ? 0 : 1);
