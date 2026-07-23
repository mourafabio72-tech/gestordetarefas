import { useState, useEffect } from 'react';
import { setoresAPI, empresasAPI } from '../services/api';
import { Plus, Edit2, Trash2, FolderOpen } from 'lucide-react';

export default function Setores() {
  const [setores, setSetores] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingSetor, setEditingSetor] = useState(null);
  const [filtroEmpresa, setFiltroEmpresa] = useState('');
  const [formData, setFormData] = useState({
    nome: '',
    descricao: '',
    empresa_id: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [setoresRes, empresasRes] = await Promise.all([
        setoresAPI.list(),
        empresasAPI.list()
      ]);
      setSetores(setoresRes.data);
      setEmpresas(empresasRes.data);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredSetores = filtroEmpresa
    ? setores.filter(s => s.empresa_id === parseInt(filtroEmpresa))
    : setores;

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = { ...formData, empresa_id: parseInt(formData.empresa_id) };
      if (editingSetor) {
        await setoresAPI.update(editingSetor.id, data);
      } else {
        await setoresAPI.create(data);
      }
      setShowModal(false);
      setEditingSetor(null);
      setFormData({ nome: '', descricao: '', empresa_id: '' });
      loadData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao salvar setor');
    }
  };

  const handleEdit = (setor) => {
    setEditingSetor(setor);
    setFormData({
      nome: setor.nome,
      descricao: setor.descricao || '',
      empresa_id: setor.empresa_id
    });
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (confirm('Tem certeza que deseja desativar este setor?')) {
      try {
        await setoresAPI.delete(id);
        loadData();
      } catch (error) {
        alert('Erro ao desativar setor');
      }
    }
  };

  const getEmpresaNome = (empresaId) => {
    const empresa = empresas.find(e => e.id === empresaId);
    return empresa?.razao_social || '-';
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">Carregando...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Setores</h1>
        <button
          onClick={() => {
            setEditingSetor(null);
            setFormData({ nome: '', descricao: '', empresa_id: '' });
            setShowModal(true);
          }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={18} />
          Novo Setor
        </button>
      </div>

      <div className="mb-4">
        <select
          value={filtroEmpresa}
          onChange={(e) => setFiltroEmpresa(e.target.value)}
          className="input-field w-auto"
        >
          <option value="">Todas as empresas</option>
          {empresas.map((empresa) => (
            <option key={empresa.id} value={empresa.id}>
              {empresa.razao_social}
            </option>
          ))}
        </select>
      </div>

      <div className="card">
        {filteredSetores.length === 0 ? (
          <div className="text-center py-12">
            <FolderOpen size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">Nenhum setor cadastrado</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Nome</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Empresa</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Descrição</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-600">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filteredSetores.map((setor) => (
                  <tr key={setor.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 font-medium">{setor.nome}</td>
                    <td className="py-3 px-4">{getEmpresaNome(setor.empresa_id)}</td>
                    <td className="py-3 px-4 text-gray-500">{setor.descricao || '-'}</td>
                    <td className="py-3 px-4">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleEdit(setor)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          onClick={() => handleDelete(setor.id)}
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
                {editingSetor ? 'Editar Setor' : 'Novo Setor'}
              </h2>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Empresa *</label>
                <select
                  value={formData.empresa_id}
                  onChange={(e) => setFormData({ ...formData, empresa_id: e.target.value })}
                  className="input-field"
                  required
                >
                  <option value="">Selecione uma empresa</option>
                  {empresas.map((empresa) => (
                    <option key={empresa.id} value={empresa.id}>
                      {empresa.razao_social}
                    </option>
                  ))}
                </select>
              </div>
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
                <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
                <textarea
                  value={formData.descricao}
                  onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                  className="input-field"
                  rows={3}
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">
                  Cancelar
                </button>
                <button type="submit" className="btn-primary flex-1">
                  {editingSetor ? 'Salvar' : 'Cadastrar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}