// Prova de frontend/src/pages/identificador.js — Node puro, sem build.
//   node frontend/provas/prova_identificador.js

import { conferirIdentificador, normalizar, trechoMovel } from '../src/pages/identificador.js';

let ok = 0, falhou = 0;
const eq = (nome, obtido, esperado) => {
  if (JSON.stringify(obtido) === JSON.stringify(esperado)) { ok++; console.log(`  ok  ${nome}`); }
  else { falhou++; console.log(`FALHA  ${nome}\n       obtido:   ${JSON.stringify(obtido)}\n       esperado: ${JSON.stringify(esperado)}`); }
};

const DOC = `RELATÓRIO CONTÁBIL
Apuração do IRPJ e CSLL — Lucro Presumido
CONTA   DESCRIÇÃO   SALDO
1.1.01  Caixa       1.000,00`;

const est = (id, texto = DOC) => conferirIdentificador(id, texto).estado;

console.log('\n1) O erro que motivou tudo: descrição inventada');
// "planilha de apuração de irpj e csll" descreve o documento, mas não está
// escrito nele. Gravado assim, o e-validador nunca casa e ninguém descobre.
eq('texto que NÃO está no documento é acusado', est('planilha de apuração de irpj e csll'), 'nao_achou');
eq('o aviso explica o mecanismo',
   conferirIdentificador('planilha de apuração', DOC).aviso.includes('procurado'), true);

console.log('\n2) Texto que está no documento passa');
eq('trecho literal', est('Apuração do IRPJ e CSLL'), 'achou');
eq('acento não atrapalha', est('APURACAO DO IRPJ E CSLL'), 'achou');
eq('caixa não atrapalha', est('relatório contábil'), 'achou');
eq('espaço a mais no meio não atrapalha', est('Apuração   do   IRPJ'), 'achou');
eq('cabeçalho de coluna também está lá', est('CONTA'), 'achou');

console.log('\n3) Curto demais distingue pouco');
eq('três letras avisa', est('IRP'), 'curto');
eq('quatro já passa', est('IRPJ'), 'achou');

console.log('\n3b) Trecho que muda a cada documento');
// O candidato sugerido para um DARF veio "2089 IRPJ - LUCRO PRESUMIDO 45.410,58
// 45.410,58": o valor do imposto está dentro. Casaria com a guia de abril e com
// nenhuma outra — pior que não casar, porque passa no teste e falha no uso.
const COM_VALOR = 'Documento 2089 IRPJ - LUCRO PRESUMIDO 45.410,58 45.410,58 vencimento 30/04/2026';
eq('valor em reais é acusado', est('2089 IRPJ - LUCRO PRESUMIDO 45.410,58', COM_VALOR), 'volatil');
eq('e o aviso diz o que é', conferirIdentificador('45.410,58', COM_VALOR).aviso.includes('valor em reais'), true);
eq('data completa idem', est('vencimento 30/04/2026', COM_VALOR), 'volatil');
eq('competência idem', trechoMovel('apuração 07/2026'), 'uma competência');
eq('sem número móvel passa', est('LUCRO PRESUMIDO', COM_VALOR), 'achou');
eq('código de receita sozinho não é valor', trechoMovel('DARF codigo 2089'), null);
eq('nada móvel devolve null', trechoMovel('Memória de Cálculo do IRPJ'), null);
eq('vazio não quebra', [trechoMovel(''), trechoMovel(null)], [null, null]);

console.log('\n4) Casos de borda');
eq('vazio não acusa nada', est(''), 'vazio');
eq('só espaços idem', est('   '), 'vazio');
eq('nulo idem', est(null), 'vazio');
eq('documento sem texto extraído avisa que não deu para conferir',
   est('qualquer coisa', ''), 'sem_texto');
eq('e diz que não conseguiu ler',
   conferirIdentificador('x', '').aviso.includes('não dá para conferir'), true);

console.log('\n5) Normalização — a mesma do backend');
eq('acento, caixa e espaço', normalizar('  APURAÇÃO   do  IRPJ '), 'apuracao do irpj');
eq('vazio e nulo', [normalizar(''), normalizar(null)], ['', '']);

console.log(`\n${falhou === 0 ? 'TUDO VERDE' : 'VERMELHO'} — ${ok} ok, ${falhou} falhou\n`);
process.exit(falhou === 0 ? 0 : 1);
