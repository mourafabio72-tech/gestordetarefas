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
};

export const authAPI = {
  login: (data) => api.post('/auth/login', data),
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
};

export const tarefasAPI = {
  list: (params) => api.get('/tarefas', { params }),
  get: (id) => api.get(`/tarefas/${id}`),
  create: (data) => api.post('/tarefas', data),
  update: (id, data) => api.put(`/tarefas/${id}`, data),
  delete: (id) => api.delete(`/tarefas/${id}`),
  dashboard: (empresaId) => api.get('/tarefas/dashboard/stats', { params: empresaId ? { empresa_id: empresaId } : {} }),
  dashboardPorSetor: () => api.get('/tarefas/dashboard/stats-por-setor'),
  transferir: (id, responsavel_id) => api.post(`/tarefas/${id}/transferir`, { responsavel_id }),
  linkEnvio: (id) => api.get(`/tarefas/${id}/link-envio`),
  copiar: (origem_empresa_id, destino_empresa_id) => api.post('/tarefas/copiar', { origem_empresa_id, destino_empresa_id }),
};

export const obrigacoesAPI = {
  list: () => api.get('/obrigacoes'),
  get: (id) => api.get(`/obrigacoes/${id}`),
  create: (data) => api.post('/obrigacoes', data),
  update: (id, data) => api.put(`/obrigacoes/${id}`, data),
  delete: (id, definitivo) => api.delete(`/obrigacoes/${id}`, { params: definitivo ? { definitivo: true } : {} }),
  setAtiva: (id, ativa) => api.post(`/obrigacoes/${id}/status`, { ativa }),
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
};

export const cronogramaAPI = {
  analisar: (file) => {
    const fd = new FormData();
    fd.append('arquivo', file);
    return api.post('/cronograma/analisar', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  importar: (grupo, itens, mapa) => api.post('/cronograma/importar', { grupo, itens, mapa }),
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
};

export const alertasAPI = {
  verificar: () => api.post('/alertas/verificar'),
  enviar: (usuarioId) => api.post(`/alertas/enviar/${usuarioId}`),
};

export default api;
