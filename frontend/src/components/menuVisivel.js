// Quem vê cada item do menu. Separado do Layout para a prova rodar em Node.
//
// Até 2026-10-27 o menu escolhia pelo NOME do grupo (admin, gestor, usuario),
// e o analista entrava com o menu vazio: o grupo dele não estava em lista
// nenhuma. Agora a regra é a permissão efetiva do /api/auth/me, a mesma que o
// servidor confere nas rotas, então grupo criado na tela e override por
// usuário também valem. Isto é só conforto visual: quem barra é o servidor.
//
// `acesso` de cada item:
//   { todos: true }               qualquer pessoa logada
//   { perm: [recurso, nivel] }    permissão efetiva no recurso, nível mínimo
//   { grupos: [...] }             só para rota que o servidor trava pelo grupo
//                                 (require_admin, require_gestor_ou_admin)

const ORDEM = { nenhum: 0, ver: 1, editar: 2 };

export function itemVisivel(item, user) {
  const a = item.acesso || {};
  if (a.todos) return true;
  if (!user) return false;
  if (a.grupos) return a.grupos.includes(user.grupo);
  if (a.perm) {
    const [recurso, nivel] = a.perm;
    const tem = user.permissoes_efetivas?.[recurso] || 'nenhum';
    return (ORDEM[tem] ?? 0) >= (ORDEM[nivel] ?? 99);
  }
  return false;
}
