import { useState, useEffect } from 'react';
import { usuariosAPI } from '../services/api';
import { Plus, Edit2, Trash2, Users as UsersIcon } from 'lucide-react';

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingUsuario, setEditingUsuario] = useState(null);
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    senha: '',
    cargo: '',
    telefone: ''
  });

  useEffect(() => {
    loadUsuarios();
  }, []);

  const loadUsuarios = async () => {
    try {
      const response = await usuariosAPI.list();
      setUsuarios(response.data);
    } catch (error) {
      console.error('Erro ao carregar usuários:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingUsuario) {
        const data = { ...formData };
        if (!data.senha) delete data.senha;
        await usuariosAPI.update(editingUsuario.id, data);
      } else {
        await usuariosAPI.create(formData);
      }
      setShowModal(false);
      setEditingUsuario(null);
      setFormData({ nome: '', email: '', senha: '', cargo: '', telefone: '' });
      loadUsuarios();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao salvar usuário');
    }
  };

  const handleEdit = (usuario) => {
    setEditingUsuario(usuario);
    setFormData({
      nome: usuario.nome,
      email: usuario.email,
      senha: '',
      cargo: usuario.cargo || '',
      telefone: usuario.telefone || ''
    });
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (confirm('Tem certeza que deseja desativar este usuário?')) {
      try {
        await usuariosAPI.delete(id);
        loadUsuarios();
      } catch (error) {
        alert('Erro ao desativar usuário');
      }
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">Carregando...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Usuários</h1>
        <button
          onClick={() => {
            setEditingUsuario(null);
            setFormData({ nome: '', email: '', senha: '', cargo: '', telefone: '' });
            setShowModal(true);
          }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={18} />
          Novo Usuário
        </button>
      </div>

      <div className="card">
        {usuarios.length === 0 ? (
          <div className="text-center py-12">
            <UsersIcon size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">Nenhum usuário cadastrado</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Nome</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Email</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Cargo</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Telefone</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Status</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-600">Ações</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((usuario) => (
                  <tr key={usuario.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center font-medium">
                          {usuario.nome.charAt(0).toUpperCase()}
                        </div>
                        <span className="font-medium">{usuario.nome}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-gray-500">{usuario.email}</td>
                    <td className="py-3 px-4">{usuario.cargo || '-'}</td>
                    <td className="py-3 px-4">{usuario.telefone || '-'}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        usuario.ativo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {usuario.ativo ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleEdit(usuario)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          onClick={() => handleDelete(usuario.id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-md">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold">
                {editingUsuario ? 'Editar Usuário' : 'Novo Usuário'}
              </h2>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  className="input-field"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="input-field"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {editingUsuario ? 'Nova Senha (deixe vazio para manter)' : 'Senha *'}
                </label>
                <input
                  type="password"
                  value={formData.senha}
                  onChange={(e) => setFormData({ ...formData, senha: e.target.value })}
                  className="input-field"
                  required={!editingUsuario}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cargo</label>
                <input
                  type="text"
                  value={formData.cargo}
                  onChange={(e) => setFormData({ ...formData, cargo: e.target.value })}
                  className="input-field"
                  placeholder="Ex: Contador, Assistente"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Telefone WhatsApp</label>
                <input
                  type="tel"
                  value={formData.telefone}
                  onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
                  className="input-field"
                  placeholder="Ex: 11999998888"
                />
                <p className="text-xs text-gray-500 mt-1">Formato: DDD + Número (ex: 11999998888)</p>
              </div>
              <div className="flex gap-3 pt-4">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">
                  Cancelar
                </button>
                <button type="submit" className="btn-primary flex-1">
                  {editingUsuario ? 'Salvar' : 'Cadastrar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
