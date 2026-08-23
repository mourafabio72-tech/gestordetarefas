import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// instância pública (sem token, sem redirect em 401) para a página de envio do cliente
const apiPublico = axios.create({ baseURL: '/api' });
export const publicoAPI = {
  contexto: (token) => apiPublico.get(`/publico/tarefa/${token}`),
  enviar: (token, file) => {
    const fd = new FormData();
    fd.append('arquivo', file);
    return apiPublico.post(`/publico/tarefa/${token}`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  ativarContexto: (token) => apiPublico.get(`/publico/ativar/${token}`),
  ativar: (token, senha) => apiPublico.post(`/publico/ativar/${token}`, { senha }),
};

export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  // Entrada pelo card do Hub. Vai pela instância pública de propósito: a recusa
  // é 404 e o limite por IP é 429, e nenhum dos dois pode cair no interceptor de
  // 401 que apaga o token e redireciona.
  sso: (bilhete) => apiPublico.post('/auth/sso', { bilhete }),
  register: (data) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
};

export const empresasAPI = {
  list: (todas) => api.get('/empresas', { params: todas ? { todas: true } : {} }),
  get: (id) => api.get(`/empresas/${id}`),
  create: (data) => api.post('/empresas', data),
  update: (id, data) => api.put(`/empresas/${id}`, data),
  delete: (id) => api.delete(`/empresas/${id}`),
  bloquear: (id, bloqueado) => api.post(`/empresas/${id}/bloquear`, { bloqueado }),
  getResponsaveisSetor: (id) => api.get(`/empresas/${id}/responsaveis-setor`),
  setResponsaveisSetor: (id, itens) => api.put(`/empresas/${id}/responsaveis-setor`, { itens }),
  importarResponsaveis: (file) => {
    const fd = new FormData();
    fd.append('arquivo', file);
    return api.post('/empresas/importar-responsaveis', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  baixarModeloResponsaveis: async () => {
    const { data } = await api.get('/empresas/modelo-responsaveis', { responseType: 'blob' });
    const url = URL.createObjectURL(data);
    const a = document.createElement('a');
    a.href = url; a.download = 'modelo_responsaveis_setor.xlsx'; a.click();
    URL.revokeObjectURL(url);
  },
  importar: (file) => {
    const fd = new FormData();
    fd.append('arquivo', file);
    return api.post('/empresas/importar', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  baixarModelo: async () => {
    const { data } = await api.get('/empresas/modelo-importacao', { responseType: 'blob' });
    const url = URL.createObjectURL(data);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'modelo_importacao_empresas.xlsx';
    a.click();
    URL.revokeObjectURL(url);
  },
};

export const setoresAPI = {
  list: (todas) => api.get('/setores', { params: todas ? { todas: true } : {} }),
  get: (id) => api.get(`/setores/${id}`),
  create: (data) => api.post('/setores', data),
  update: (id, data) => api.put(`/setores/${id}`, data),
  delete: (id) => api.delete(`/setores/${id}`),
  setAtiva: (id, ativo) => api.post(`/setores/${id}/status`, { ativo }),
};

export const usuariosAPI = {
  list: () => api.get('/usuarios'),
  get: (id) => api.get(`/usuarios/${id}`),
  create: (data) => api.post('/usuarios', data),
  update: (id, data) => api.put(`/usuarios/${id}`, data),
  delete: (id) => api.delete(`/usuarios/${id}`),
  carga: (id) => api.get(`/usuarios/${id}/carga`),
  bloquear: (id, bloqueado, substituto_id) => api.post(`/usuarios/${id}/bloquear`, { bloqueado, substituto_id }),
  importar: (file) => {
    const fd = new FormData();
    fd.append('arquivo', file);
    return api.post('/usuarios/importar', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  baixarModelo: async () => {
    const { data } = await api.get('/usuarios/modelo-importacao', { responseType: 'blob' });
    const url = URL.createObjectURL(data);
    const a = document.createElement('a');
    a.href = url; a.download = 'modelo_importacao_usuarios.xlsx'; a.click();
    URL.revokeObjectURL(url);
  },
  convite: (id) => api.post(`/usuarios/${id}/convite`),
  conviteLote: (ids) => api.post('/usuarios/convite-lote', { ids: ids || null }),
};

export const tarefasAPI = {
  list: (params) => api.get('/tarefas', { params }),
  get: (id) => api.get(`/tarefas/${id}`),
  create: (data) => api.post('/tarefas', data),
  // O comprovante exige o cabeçalho de sessão, então não dá para apontar um
  // <a href> para ele: vem como blob e a tela abre a partir daí.
  anexo: (id, baixar) => api.get(`/tarefas/${id}/anexo`, {
    params: baixar ? { baixar: true } : {}, responseType: 'blob',
  }),
  // Documento que o escritório ENTREGA ao cliente (guia, boleto, relatório).
  anexarSaida: (id, arquivo) => {
    const fd = new FormData();
    fd.append('arquivo', arquivo);
    // O `Content-Type: application/json` é padrão desta instância do axios, e
    // sem sobrescrever aqui o FormData sai como JSON — o FastAPI não encontra o
    // campo e responde "arquivo: é obrigatório". Todos os outros uploads do
    // projeto fazem o mesmo; este tinha ficado de fora.
    return api.post(`/tarefas/${id}/saida`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  saida: (id, baixar) => api.get(`/tarefas/${id}/saida`, {
    params: baixar ? { baixar: true } : {}, responseType: 'blob',
  }),
  enviarCliente: (id, ensaio) => api.post(`/tarefas/${id}/enviar-cliente`, null,
    { params: ensaio ? { ensaio: true } : {} }),
  envios: (id) => api.get(`/tarefas/${id}/envios`),
  acessos: (id) => api.get(`/tarefas/${id}/acessos`),
  // Exige a flag `apagar_anexo`, decidida no cadastro de Grupos.
  excluirDocumento: (id, tipo) => api.delete(`/tarefas/${id}/documento`, { params: { tipo } }),
  update: (id, data) => api.put(`/tarefas/${id}`, data),
  delete: (id) => api.delete(`/tarefas/${id}`),
  dashboard: (empresaId) => api.get('/tarefas/dashboard/stats', { params: empresaId ? { empresa_id: empresaId } : {} }),
  dashboardPorSetor: () => api.get('/tarefas/dashboard/stats-por-setor'),
  transferir: (id, responsavel_id) => api.post(`/tarefas/${id}/transferir`, { responsavel_id }),
  linkEnvio: (id) => api.get(`/tarefas/${id}/link-envio`),
  copiar: (origem_empresa_id, destino_empresa_id) => api.post('/tarefas/copiar', { origem_empresa_id, destino_empresa_id }),
  excluirCompetencia: (competencia) => api.post('/tarefas/excluir-competencia', { competencia }),
};

export const obrigacoesAPI = {
  list: () => api.get('/obrigacoes'),
  get: (id) => api.get(`/obrigacoes/${id}`),
  create: (data) => api.post('/obrigacoes', data),
  update: (id, data) => api.put(`/obrigacoes/${id}`, data),
  delete: (id, definitivo) => api.delete(`/obrigacoes/${id}`, { params: definitivo ? { definitivo: true } : {} }),
  setAtiva: (id, ativa) => api.post(`/obrigacoes/${id}/status`, { ativa }),
  gerar: (mes, ano, obrigacao_ids) => api.post('/obrigacoes/gerar', { mes, ano, obrigacao_ids }),
  getDetalhes: (id) => api.get(`/obrigacoes/${id}/detalhes-empresa`),
  setDetalhes: (id, itens) => api.put(`/obrigacoes/${id}/detalhes-empresa`, { itens }),
  excluirLote: (ids, definitivo = true) => api.post('/obrigacoes/excluir-lote', { ids, definitivo }),
  baixarRelatorio: async () => {
    const { data } = await api.get('/obrigacoes/relatorio', { responseType: 'blob' });
    const url = URL.createObjectURL(data);
    const a = document.createElement('a');
    a.href = url; a.download = 'relacao_obrigacoes.xlsx'; a.click();
    URL.revokeObjectURL(url);
  },
  copiarEmpresa: (origem_empresa_id, destino_empresa_id) =>
    api.post('/obrigacoes/copiar-empresa', { origem_empresa_id, destino_empresa_id }),
  desvincularEmpresa: (empresa_id, obrigacao_ids = null) =>
    api.post('/obrigacoes/desvincular-empresa', { empresa_id, obrigacao_ids }),
  analisarModelo: (file) => {
    const fd = new FormData();
    fd.append('arquivo', file);
    return api.post('/obrigacoes/analisar-modelo', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
};

export const evalidadorAPI = {
  processar: (files) => {
    const fd = new FormData();
    Array.from(files).forEach((f) => fd.append('arquivos', f));
    return api.post('/evalidador/processar', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
};

export const modelosAPI = {
  list: () => api.get('/modelos'),
  analisar: (file) => {
    const fd = new FormData();
    fd.append('arquivo', file);
    return api.post('/modelos/analisar', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  lote: (files) => {
    const fd = new FormData();
    Array.from(files).forEach((f) => fd.append('arquivos', f));
    return api.post('/modelos/lote', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  create: (data) => api.post('/modelos', data),
  delete: (id) => api.delete(`/modelos/${id}`),
  update: (id, data) => api.put(`/modelos/${id}`, data),
};

export const cronogramaAPI = {
  analisar: (file) => {
    const fd = new FormData();
    fd.append('arquivo', file);
    return api.post('/cronograma/analisar', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  importar: (grupo, itens, mapa, para_todas = true) => api.post('/cronograma/importar', { grupo, itens, mapa, para_todas }),
  baixarModelo: async () => {
    const { data } = await api.get('/cronograma/modelo-importacao', { responseType: 'blob' });
    const url = URL.createObjectURL(data);
    const a = document.createElement('a');
    a.href = url; a.download = 'modelo_importacao_obrigacoes.xlsx'; a.click();
    URL.revokeObjectURL(url);
  },
};

export const substituicoesAPI = {
  list: () => api.get('/substituicoes'),
  create: (data) => api.post('/substituicoes', data),
  encerrar: (id) => api.delete(`/substituicoes/${id}`),
};

export const configuracaoAPI = {
  getNotificacoes: () => api.get('/configuracao/notificacoes'),
  putNotificacoes: (data) => api.put('/configuracao/notificacoes', data),
  testarEmail: (para) => api.post('/configuracao/notificacoes/testar-email', { para }),
  testarWhatsapp: (para) => api.post('/configuracao/notificacoes/testar-whatsapp', { para }),
  testarIA: () => api.post('/configuracao/notificacoes/testar-ia'),
  zapUsuarios: () => api.get('/configuracao/notificacoes/zap-usuarios'),
};

export const gruposAPI = {
  list: () => api.get('/grupos'),
  create: (data) => api.post('/grupos', data),
  update: (slug, data) => api.put(`/grupos/${slug}`, data),
  setAtivo: (slug, ativo) => api.post(`/grupos/${slug}/status`, { ativo }),
  delete: (slug) => api.delete(`/grupos/${slug}`),
};

export const documentosAPI = {
  list: (params) => api.get('/documentos', { params }),
  competencias: () => api.get('/documentos/competencias'),
};

export const alertasAPI = {
  // Sem `ensaio: false` explícito o backend só simula — o alerta de verdade sai
  // para o WhatsApp e o e-mail do cliente, e essa chamada não pode disparar sem
  // querer.
  verificar: (params = { ensaio: true }) => api.post('/alertas/verificar', null, { params }),
  enviar: (usuarioId) => api.post(`/alertas/enviar/${usuarioId}`),
};

export default api;
