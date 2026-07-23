import { useState, useEffect } from 'react';
import { empresasAPI } from '../services/api';
import { Plus, Edit2, Trash2, Building2 } from 'lucide-react';

export default function Empresas() {
  const [empresas, setEmpresas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingEmpresa, setEditingEmpresa] = useState(null);
  const [formData, setFormData] = useState({
    razao_social: '',
    cnpj: '',
    nome_fantasia: '',
    email: '',
    telefone: '',
    endereco: ''
  });

  useEffect(() => {
    loadEmpresas();
  }, []);

  const loadEmpresas = async () => {
    try {
      const response = await empresasAPI.list();
      setEmpresas(response.data);
    } catch (error) {
      console.error('Erro ao carregar empresas:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingEmpresa) {
        await empresasAPI.update(editingEmpresa.id, formData);
      } else {
        await empresasAPI.create(formData);
      }
      setShowModal(false);
      setEditingEmpresa(null);
      setFormData({ razao_social: '', cnpj: '', nome_fantasia: '', email: '', telefone: '', endereco: '' });
      loadEmpresas();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao salvar empresa');
    }
  };

  const handleEdit = (empresa) => {
    setEditingEmpresa(empresa);
    setFormData({
      razao_social: empresa.razao_social,
      cnpj: empresa.cnpj || '',
      nome_fantasia: empresa.nome_fantasia || '',
      email: empresa.email || '',
      telefone: empresa.telefone || '',
      endereco: empresa.endereco || ''
    });
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (confirm('Tem certeza que deseja desativar esta empresa?')) {
      try {
        await empresasAPI.delete(id);
        loadEmpresas();
      } catch (error) {
        alert('Erro ao desativar empresa');
      }
    }
  };

  const formatCNPJ = (value) => {
    const nums = value.replace(/\D/g, '').slice(0, 14);
    return nums
      .replace(/^(\d{2})(\d)/, '$1.$2')
      .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
      .replace(/\.(\d{3})(\d)/, '.$1/$2')
      .replace(/(\d{4})(\d)/, '$1-$2');
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">Carregando...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Empresas</h1>
        <button
          onClick={() => {
            setEditingEmpresa(null);
            setFormData({ razao_social: '', cnpj: '', nome_fantasia: '', email: '', telefone: '', endereco: '' });
            setShowModal(true);
          }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={18} />
          Nova Empresa
        </button>
      </div>

      <div className="card">
        {empresas.length === 0 ? (
          <div className="text-center py-12">
            <Building2 size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">Nenhuma empresa cadastrada</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Razão Social</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">CNPJ</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Nome Fantasia</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Email</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Telefone</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-600">Ações</th>
                </tr>
              </thead>
              <tbody>
                {empresas.map((empresa) => (
                  <tr key={empresa.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">{empresa.razao_social}</td>
                    <td className="py-3 px-4">{empresa.cnpj || '-'}</td>
                    <td className="py-3 px-4">{empresa.nome_fantasia || '-'}</td>
                    <td className="py-3 px-4">{empresa.email || '-'}</td>
                    <td className="py-3 px-4">{empresa.telefone || '-'}</td>
                    <td className="py-3 px-4">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleEdit(empresa)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          onClick={() => handleDelete(empresa.id)}
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
                {editingEmpresa ? 'Editar Empresa' : 'Nova Empresa'}
              </h2>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Razão Social *</label>
                <input
                  type="text"
                  value={formData.razao_social}
                  onChange={(e) => setFormData({ ...formData, razao_social: e.target.value })}
                  className="input-field"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">CNPJ</label>
                <input
                  type="text"
                  value={formData.cnpj}
                  onChange={(e) => setFormData({ ...formData, cnpj: formatCNPJ(e.target.value) })}
                  className="input-field"
                  placeholder="00.000.000/0000-00"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome Fantasia</label>
                <input
                  type="text"
                  value={formData.nome_fantasia}
                  onChange={(e) => setFormData({ ...formData, nome_fantasia: e.target.value })}
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Telefone</label>
                <input
                  type="text"
                  value={formData.telefone}
                  onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Endereço</label>
                <textarea
                  value={formData.endereco}
                  onChange={(e) => setFormData({ ...formData, endereco: e.target.value })}
                  className="input-field"
                  rows={2}
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">
                  Cancelar
                </button>
                <button type="submit" className="btn-primary flex-1">
                  {editingEmpresa ? 'Salvar' : 'Cadastrar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}