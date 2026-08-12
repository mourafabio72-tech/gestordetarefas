// Espelho dos presets do backend (app/permissoes.py). MANTER EM SINCRONIA.
// Usado só para a UI mostrar a permissão efetiva e calcular os overrides.

export const RECURSOS = [
  ['empresas', 'Empresas'],
  ['setores', 'Setores / departamentos'],
  ['tarefas', 'Tarefas / demandas'],
  ['obrigacoes', 'Obrigações (modelos)'],
  ['usuarios', 'Usuários'],
  ['relatorios', 'Relatórios'],
  ['evalidador', 'e-validador'],
];

export const NIVEIS = [
  ['nenhum', 'Sem acesso'],
  ['ver', 'Visualizar'],
  ['editar', 'Editar'],
];

export const ESCOPOS = [
  ['proprias', 'Só as próprias'],
  ['setor', 'Minha equipe'],
  ['todas', 'Todas'],
];

export const FLAGS = [
  ['alterar_prazo_legal', 'Alterar prazo legal (vencimento)'],
  ['alterar_prazo_tecnico', 'Alterar prazo técnico'],
  ['dispensar_demanda', 'Dispensar / cancelar demanda'],
  ['apagar_anexo', 'Apagar anexos'],
  ['alocar_obrigacao', 'Alocar obrigação em empresa'],
  ['disparar_emails', 'Disparar e-mails agendados'],
];

export const PRESETS = {
  admin: {
    empresas: 'editar', setores: 'editar', tarefas: 'editar', obrigacoes: 'editar',
    usuarios: 'editar', relatorios: 'editar', evalidador: 'editar', escopo_tarefas: 'todas',
    alterar_prazo_legal: true, alterar_prazo_tecnico: true, dispensar_demanda: true,
    apagar_anexo: true, alocar_obrigacao: true, disparar_emails: true,
  },
  gestor: {
    empresas: 'editar', setores: 'editar', tarefas: 'editar', obrigacoes: 'editar',
    usuarios: 'ver', relatorios: 'ver', evalidador: 'editar', escopo_tarefas: 'todas',
    alterar_prazo_legal: true, alterar_prazo_tecnico: true, dispensar_demanda: true,
    apagar_anexo: false, alocar_obrigacao: true, disparar_emails: true,
  },
  analista: {
    empresas: 'ver', setores: 'ver', tarefas: 'editar', obrigacoes: 'nenhum',
    usuarios: 'nenhum', relatorios: 'ver', evalidador: 'ver', escopo_tarefas: 'proprias',
    alterar_prazo_legal: false, alterar_prazo_tecnico: true, dispensar_demanda: false,
    apagar_anexo: false, alocar_obrigacao: false, disparar_emails: true,
  },
  estagiario: {
    empresas: 'ver', setores: 'ver', tarefas: 'editar', obrigacoes: 'nenhum',
    usuarios: 'nenhum', relatorios: 'ver', evalidador: 'nenhum', escopo_tarefas: 'proprias',
    alterar_prazo_legal: false, alterar_prazo_tecnico: false, dispensar_demanda: false,
    apagar_anexo: false, alocar_obrigacao: false, disparar_emails: false,
  },
  consulta: {
    empresas: 'ver', setores: 'ver', tarefas: 'ver', obrigacoes: 'ver',
    usuarios: 'nenhum', relatorios: 'ver', evalidador: 'nenhum', escopo_tarefas: 'todas',
    alterar_prazo_legal: false, alterar_prazo_tecnico: false, dispensar_demanda: false,
    apagar_anexo: false, alocar_obrigacao: false, disparar_emails: false,
  },
  usuario: {
    empresas: 'ver', setores: 'ver', tarefas: 'ver', obrigacoes: 'ver',
    usuarios: 'nenhum', relatorios: 'ver', evalidador: 'nenhum', escopo_tarefas: 'todas',
    alterar_prazo_legal: false, alterar_prazo_tecnico: false, dispensar_demanda: false,
    apagar_anexo: false, alocar_obrigacao: false, disparar_emails: false,
  },
};

export const GRUPOS = [
  { value: 'admin', label: 'Admin', desc: 'Acesso total, incluindo papéis e permissões.' },
  { value: 'gestor', label: 'Gestor', desc: 'Gerencia cadastros, tarefas (todas) e usuários.' },
  { value: 'analista', label: 'Analista', desc: 'Edita só as próprias tarefas; cadastros só leitura.' },
  { value: 'estagiario', label: 'Estagiário', desc: 'Edita só as próprias tarefas; não mexe em prazos.' },
  { value: 'consulta', label: 'Consulta', desc: 'Só visualiza; não altera nada.' },
  { value: 'usuario', label: 'Usuário (legado)', desc: 'Papel antigo — só leitura, vê tudo.' },
];

// Cargos escolhíveis no cadastro de usuário → mapeiam papel (grupo) + tipo.
export const CARGOS = [
  { value: 'Admin', grupo: 'admin', tipo: 'colaborador' },
  { value: 'Gestor', grupo: 'gestor', tipo: 'colaborador' },
  { value: 'Analista', grupo: 'analista', tipo: 'colaborador' },
  { value: 'Estagiário', grupo: 'estagiario', tipo: 'colaborador' },
  { value: 'Cliente', grupo: 'consulta', tipo: 'cliente' },
];

// Permissão efetiva = preset do papel + overrides (dict) por cima.
export function resolver(grupo, overrides) {
  const base = { ...(PRESETS[grupo] || PRESETS.consulta) };
  if (overrides && typeof overrides === 'object') {
    for (const k of Object.keys(overrides)) {
      if (k in base) base[k] = overrides[k];
    }
  }
  return base;
}

// Diferenças entre a matriz editada e o preset do papel → overrides mínimos.
export function calcularOverrides(grupo, efetiva) {
  const base = PRESETS[grupo] || PRESETS.consulta;
  const ov = {};
  for (const k of Object.keys(base)) {
    if (efetiva[k] !== base[k]) ov[k] = efetiva[k];
  }
  return ov;
}

// Versões que recebem o preset do grupo já resolvido (vindo do backend).
export function resolverCom(preset, overrides) {
  const base = { ...(preset || PRESETS.consulta) };
  if (overrides && typeof overrides === 'object') {
    for (const k of Object.keys(overrides)) {
      if (k in base) base[k] = overrides[k];
    }
  }
  return base;
}

export function overridesCom(preset, efetiva) {
  const base = preset || PRESETS.consulta;
  const ov = {};
  for (const k of Object.keys(base)) {
    if (efetiva[k] !== base[k]) ov[k] = efetiva[k];
  }
  return ov;
}

// Matriz "vazia" completa (tudo no mais restrito) para criar grupo do zero.
export const MATRIZ_VAZIA = {
  ...Object.fromEntries(RECURSOS.map(([k]) => [k, 'nenhum'])),
  escopo_tarefas: 'proprias',
  ...Object.fromEntries(FLAGS.map(([k]) => [k, false])),
};
