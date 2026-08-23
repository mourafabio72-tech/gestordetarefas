// Prova de frontend/src/services/api.js — Node puro, sem build.
//   node frontend/provas/prova_upload_multipart.js
//
// Verificação ESTÁTICA, e é o único jeito de pegar isto: a instância do axios
// tem `Content-Type: application/json` como padrão, e um POST com FormData que
// não sobrescreva esse cabeçalho sai como JSON. O build passa, o lint passa, e
// só o servidor reclama — "arquivo: é obrigatório" — depois de a pessoa ter
// escolhido o arquivo.
//
// Aconteceu com o upload do documento de saída em 2026-08-22. Os outros seis
// uploads do projeto estavam certos; o novo tinha ficado de fora.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = path.dirname(fileURLToPath(import.meta.url));
const fonte = fs.readFileSync(path.join(RAIZ, '../src/services/api.js'), 'utf8');

let ok = 0, falhou = 0;
const check = (nome, cond, extra = '') => {
  if (cond) { ok++; console.log(`  ok  ${nome}`); }
  else { falhou++; console.log(`FALHA  ${nome}${extra ? '\n       ' + extra : ''}`); }
};

console.log('\n1) A instância declara JSON como padrão — é a origem da armadilha');
check('o padrão é application/json', /headers:\s*\{\s*'Content-Type':\s*'application\/json'/.test(fonte));

console.log('\n2) Todo upload com FormData declara multipart');
// Cada bloco entre "new FormData()" e o próximo ".post(...)" é um upload.
const blocos = fonte.split('new FormData()').slice(1);
check('há uploads para conferir', blocos.length > 0, `(achei ${blocos.length})`);

function uploadsSemMultipart(codigo) {
  const faltando = [];
  for (const bloco of codigo.split('new FormData()').slice(1)) {
    // Do FormData até o fim da chamada de post daquele bloco.
    const chamada = bloco.split(/\n\s*\},?\s*\n/)[0];
    const post = chamada.match(/\.post\([^;]*/s);
    if (!post) continue;
    if (!post[0].includes('multipart/form-data')) {
      // Guarda a rota, para o erro dizer QUAL upload está errado.
      const rota = post[0].match(/`([^`]+)`|'([^']+)'/);
      faltando.push(rota ? (rota[1] || rota[2]) : post[0].slice(0, 60));
    }
  }
  return faltando;
}

const semMultipart = uploadsSemMultipart(fonte);
check('nenhum upload esqueceu o cabeçalho', semMultipart.length === 0,
      semMultipart.length ? `sem multipart: ${semMultipart.join(', ')}` : '');

console.log('\n3) A verificação PEGA o erro — sem isto ela poderia estar sempre verde');
const erradoDeProposito = `
  enviar: (id, arquivo) => {
    const fd = new FormData();
    fd.append('arquivo', arquivo);
    return api.post(\`/tarefas/\${id}/saida\`, fd);
  },`;
const pegou = uploadsSemMultipart(erradoDeProposito);
check('acusa um upload sem o cabeçalho', pegou.length === 1, JSON.stringify(pegou));
check('e diz qual é a rota', String(pegou[0]).includes('/saida'), String(pegou[0]));

console.log('\n4) O upload que quebrou está coberto');
check('anexarSaida manda multipart',
      /anexarSaida[\s\S]*?multipart\/form-data/.test(fonte.slice(fonte.indexOf('anexarSaida'),
                                                                  fonte.indexOf('anexarSaida') + 900)));

console.log(`\n${falhou === 0 ? 'TUDO VERDE' : 'VERMELHO'} — ${ok} ok, ${falhou} falhou\n`);
process.exit(falhou === 0 ? 0 : 1);
