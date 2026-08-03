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

export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
};

export const empresasAPI = {
  list: () => api.get('/empresas'),
  get: (id) => api.get(`/empresas/${id}`),
  create: (data) => api.post('/empresas', data),
  update: (id, data) => api.put(`/empresas/${id}`, data),
  delete: (id) => api.delete(`/empresas/${id}`),
  bloquear: (id, bloqueado) => api.post(`/empresas/${id}/bloquear`, { bloqueado }),
};

export const setoresAPI = {
  list: () => api.get('/setores'),
  get: (id) => api.get(`/setores/${id}`),
  create: (data) => api.post('/setores', data),
  update: (id, data) => api.put(`/setores/${id}`, data),
  delete: (id) => api.delete(`/setores/${id}`),
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
  transferir: (id, responsavel_id) => api.post(`/tarefas/${id}/transferir`, { responsavel_id }),
  copiar: (origem_empresa_id, destino_empresa_id) => api.post('/tarefas/copiar', { origem_empresa_id, destino_empresa_id }),
};

export const obrigacoesAPI = {
  list: () => api.get('/obrigacoes'),
  get: (id) => api.get(`/obrigacoes/${id}`),
  create: (data) => api.post('/obrigacoes', data),
  update: (id, data) => api.put(`/obrigacoes/${id}`, data),
  delete: (id) => api.delete(`/obrigacoes/${id}`),
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
};

export const alertasAPI = {
  verificar: () => api.post('/alertas/verificar'),
  enviar: (usuarioId) => api.post(`/alertas/enviar/${usuarioId}`),
};

export default api;
