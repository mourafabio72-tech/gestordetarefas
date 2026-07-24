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
  login: (data) => api.post('/auth/login/', data),
  register: (data) => api.post('/auth/register/', data),
  me: () => api.get('/auth/me/'),
};

export const empresasAPI = {
  list: () => api.get('/empresas/'),
  get: (id) => api.get(`/empresas/${id}`),
  create: (data) => api.post('/empresas/', data),
  update: (id, data) => api.put(`/empresas/${id}`, data),
  delete: (id) => api.delete(`/empresas/${id}`),
};

export const setoresAPI = {
  list: (empresaId) => api.get('/setores/', { params: empresaId ? { empresa_id: empresaId } : {} }),
  get: (id) => api.get(`/setores/${id}`),
  create: (data) => api.post('/setores/', data),
  update: (id, data) => api.put(`/setores/${id}`, data),
  delete: (id) => api.delete(`/setores/${id}`),
};

export const usuariosAPI = {
  list: () => api.get('/usuarios/'),
  get: (id) => api.get(`/usuarios/${id}`),
  create: (data) => api.post('/usuarios/', data),
  update: (id, data) => api.put(`/usuarios/${id}`, data),
  delete: (id) => api.delete(`/usuarios/${id}`),
};

export const tarefasAPI = {
  list: (params) => api.get('/tarefas/', { params }),
  get: (id) => api.get(`/tarefas/${id}`),
  create: (data) => api.post('/tarefas/', data),
  update: (id, data) => api.put(`/tarefas/${id}`, data),
  delete: (id) => api.delete(`/tarefas/${id}`),
  dashboard: (empresaId) => api.get('/tarefas/dashboard/stats', { params: empresaId ? { empresa_id: empresaId } : {} }),
};

export const alertasAPI = {
  verificar: () => api.post('/alertas/verificar/'),
  enviar: (usuarioId) => api.post(`/alertas/enviar/${usuarioId}`),
};

export default api;
