import { useState, useEffect } from 'react';
import { setoresAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { Plus, Edit2, Trash2, FolderOpen, Ban, CheckCircle2 } from 'lucide-react';

export default function Setores() {
  const [setores, setSetores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingSetor, setEditingSetor] = useState(null);
  const [formData, setFormData] = useState({ nome: '', descricao: '' });
  const [mostrarInativos, setMostrarInativos] = useState(false);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const res = await setoresAPI.list(true);
      setSetores(res.data);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingSetor) {
        await setoresAPI.update(editingSetor.id, formData);
      } else {
        await setoresAPI.create(formData);
      }
      setShowModal(false);
      setEditingSetor(null);
      setFormData({ nome: '', descricao: '' });
      loadData();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao salvar setor'));
    }
  };

  const handleEdit = (setor) => {
    setEditingSetor(setor);
    setFormData({ nome: setor.nome, descricao: setor.descricao || '' });
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (!confirm('Excluir este setor? Se tiver obrigações/tarefas vinculadas, ele será apenas inativado.')) return;
    try {
      const { data } = await setoresAPI.delete(id);
      if (data?.message) alert(data.message);
      loadData();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao excluir setor'));
    }
  };

  const alternarStatus = async (s) => {
    try { await setoresAPI.setAtiva(s.id, s.ativo === false); loadData(); }
    catch { alert('Erro ao mudar o status do setor'); }
  };

  const setoresFiltrados = mostrarInativos ? setores : setores.filter((s) => s.ativo !== false);

  if (loading) {
    return <div className="flex items-center justify-center h-64">Carregando...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Setores</h1>
          <p className="text-sm text-gray-500">Departamentos internos do escritório (Fiscal, Contábil, DP…).</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={mostrarInativos} onChange={(e) => setMostrarInativos(e.target.checked)} className="h-4 w-4" />
            Mostrar inativos
          </label>
          <button
            onClick={() => {
              setEditingSetor(null);
              setFormData({ nome: '', descricao: '' });
              setShowModal(true);
            }}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={18} />
            Novo Setor
          </button>
        </div>
      </div>

      <div className="card">
        {setores.length === 0 ? (
          <div className="text-center py-12">
            <FolderOpen size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">Nenhum setor cadastrado</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table-app">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left font-semibold text-gray-600">Nome</th>
                  <th className="text-left font-semibold text-gray-600">Descrição</th>
                  <th className="text-left font-semibold text-gray-600">Situação</th>
                  <th className="text-right font-semibold text-gray-600">Ações</th>
                </tr>
              </thead>
              <tbody>
                {setoresFiltrados.map((setor) => (
                  <tr key={setor.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="font-medium">{setor.nome}</td>
                    <td className="text-gray-500">{setor.descricao || '-'}</td>
                    <td>
                      <span className={`px-2 py-0.5 text-xs rounded-full ${setor.ativo === false ? 'bg-gray-200 text-gray-600' : 'bg-green-100 text-green-700'}`}>
                        {setor.ativo === false ? 'Inativo' : 'Ativo'}
                      </span>
                    </td>
                    <td>
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleEdit(setor)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Editar"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          onClick={() => alternarStatus(setor)} title={setor.ativo === false ? 'Ativar' : 'Inativar'}
                          className={`p-2 rounded-lg transition-colors ${setor.ativo === false ? 'text-green-600 hover:bg-green-50' : 'text-amber-600 hover:bg-amber-50'}`}
                        >
                          {setor.ativo === false ? <CheckCircle2 size={16} /> : <Ban size={16} />}
                        </button>
                        <button
                          onClick={() => handleDelete(setor.id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Excluir"
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
          <div className="bg-white rounded-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">
                {editingSetor ? 'Editar Setor' : 'Novo Setor'}
              </h2>
            </div>
            <form onSubmit={handleSubmit} className="p-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  className="input-field"
                  placeholder="Ex: Fiscal, Contábil, DP"
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
