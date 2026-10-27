// Prova de frontend/src/components/menuVisivel.js: Node puro, sem build.
//   node frontend/provas/prova_menu_por_permissao.js
//
// Caso de 2026-10-27: o analista entrava e o menu vinha vazio. O menu escolhia
// os itens pelo NOME do grupo (admin, gestor, usuario), e o grupo "analista"
// não estava em lista nenhuma. A regra passa a seguir a permissão efetiva que
// o /api/auth/me devolve, a mesma que o servidor usa nas rotas.

import { itemVisivel } from '../src/components/menuVisivel.js';
import { PRESETS } from '../src/permissoes.js';

let ok = 0, falhou = 0;
const eq = (nome, obtido, esperado) => {
  if (JSON.stringify(obtido) === JSON.stringify(esperado)) { ok++; console.log(`  ok  ${nome}`); }
  else { falhou++; console.log(`FALHA  ${nome}\n       obtido:   ${JSON.stringify(obtido)}\n       esperado: ${JSON.stringify(esperado)}`); }
};

const MENU = {
  dashboard: { acesso: { todos: true } },
  tarefas: { acesso: { perm: ['tarefas', 'ver'] } },
  evalidador: { acesso: { perm: ['evalidador', 'editar'] } },
  obrigacoes: { acesso: { perm: ['obrigacoes', 'editar'] } },
  usuarios: { acesso: { grupos: ['admin', 'gestor'] } },
  notificacoes: { acesso: { grupos: ['admin'] } },
};
const vistos = (user) => Object.keys(MENU).filter((k) => itemVisivel(MENU[k], user));
const quem = (grupo, extra = {}) => ({ grupo, permissoes_efetivas: { ...PRESETS[grupo], ...extra } });

eq('analista ve Dashboard e Tarefas (o caso do menu vazio)', vistos(quem('analista')), ['dashboard', 'tarefas']);
eq('estagiario ve Dashboard e Tarefas', vistos(quem('estagiario')), ['dashboard', 'tarefas']);
eq('admin ve tudo', vistos(quem('admin')), Object.keys(MENU));
eq('gestor ve tudo menos o que e so do admin', vistos(quem('gestor')),
  ['dashboard', 'tarefas', 'evalidador', 'obrigacoes', 'usuarios']);
eq('usuario legado continua com Dashboard e Tarefas', vistos(quem('usuario')), ['dashboard', 'tarefas']);
eq('grupo novo criado na tela segue a permissao, nao o nome',
  vistos({ grupo: 'fiscal_senior', permissoes_efetivas: { tarefas: 'editar', evalidador: 'editar', obrigacoes: 'editar' } }),
  ['dashboard', 'tarefas', 'evalidador', 'obrigacoes']);
eq('override no usuario vale (analista com e-validador editar)',
  vistos(quem('analista', { evalidador: 'editar' })), ['dashboard', 'tarefas', 'evalidador']);
eq('tarefas em nenhum some do menu', vistos(quem('analista', { tarefas: 'nenhum' })), ['dashboard']);
eq('sem permissoes_efetivas (resposta antiga), so o que e para todos',
  vistos({ grupo: 'analista' }), ['dashboard']);
eq('sem usuario, nada de restrito', vistos(null), ['dashboard']);

console.log(`\n${falhou ? 'PROVA FALHOU' : 'PROVA OK'}: ${ok} ok, ${falhou} falha(s)`);
if (falhou) process.exit(1);
