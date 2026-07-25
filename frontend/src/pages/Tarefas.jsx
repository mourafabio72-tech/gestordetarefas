import { useState, useEffect } from 'react';
import { tarefasAPI, empresasAPI, setoresAPI, usuariosAPI } from '../services/api';
import { format, isPast, isToday } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Plus, Edit2, Trash2, ListTodo, AlertTriangle, Clock, CheckCircle, ArrowRightLeft } from 'lucide-react';

const statusColors = {
  pendente: 'bg-yellow-100 text-yellow-700',
  em_andamento: 'bg-indigo-100 text-indigo-700',
  concluida: 'bg-green-100 text-green-700',
  atrasada: 'bg-red-100 text-red-700',
  cancelada: 'bg-gray-100 text-gray-700'
};

const prioridadeColors = {
  baixa: 'bg-gray-100 text-gray-700',
  media: 'bg-blue-100 text-blue-700',
  alta: 'bg-orange-100 text-orange-700',
  urgente: 'bg-red-100 text-red-700'
};

const statusLabels = {
  pendente: 'Pendente',
  em_andamento: 'Em Andamento',
  concluida: 'Concluída',
  atrasada: 'Atrasada',
  cancelada: 'Cancelada'
};

const prioridadeLabels = {
  baixa: 'Baixa',
  media: 'Média',
  alta: 'Alta',
  urgente: 'Urgente'
};

export default function Tarefas() {
  const [tarefas, setTarefas] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [setores, setSetores] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingTarefa, setEditingTarefa] = useState(null);
  const [filtros, setFiltros] = useState({ empresa_id: '', status: '' });
  const [showTransfer, setShowTransfer] = useState(null); // tarefa sendo transferida
  const [transferResp, setTransferResp] = useState('');
  const [formData, setFormData] = useState({
    titulo: '',
    descricao: '',
    empresa_id: '',
    setor_id: '',
    responsavel_id: '',
    prioridade: 'media',
    data_prazo: '',
    data_vencimento: '',
    gera_multa: false,
    observacoes: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [tarefasRes, empresasRes, setoresRes, usuariosRes] = await Promise.all([
        tarefasAPI.list(),
        empresasAPI.list(),
        setoresAPI.list(),
        usuariosAPI.list()
      ]);
      setTarefas(tarefasRes.data);
      setEmpresas(empresasRes.data);
      setSetores(setoresRes.data);
      setUsuarios(usuariosRes.data);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredTarefas = tarefas.filter(t => {
    if (filtros.empresa_id && t.empresa_id !== parseInt(filtros.empresa_id)) return false;
    if (filtros.status && t.status !== filtros.status) return false;
    return true;
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = {
        ...formData,
        empresa_id: parseInt(formData.empresa_id),
        setor_id: formData.setor_id ? parseInt(formData.setor_id) : null,
        responsavel_id: formData.responsavel_id ? parseInt(formData.responsavel_id) : null,
        data_prazo: new Date(formData.data_prazo).toISOString(),
        data_vencimento: formData.data_vencimento ? new Date(formData.data_vencimento).toISOString() : null,
        gera_multa: !!formData.gera_multa
      };

      if (editingTarefa) {
        await tarefasAPI.update(editingTarefa.id, data);
      } else {
        await tarefasAPI.create(data);
      }
      setShowModal(false);
      setEditingTarefa(null);
      resetForm();
      loadData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao salvar tarefa');
    }
  };

  const handleEdit = (tarefa) => {
    setEditingTarefa(tarefa);
    setFormData({
      titulo: tarefa.titulo,
      descricao: tarefa.descricao || '',
      empresa_id: tarefa.empresa_id,
      setor_id: tarefa.setor_id || '',
      responsavel_id: tarefa.responsavel_id || '',
      prioridade: tarefa.prioridade,
      data_prazo: format(new Date(tarefa.data_prazo), "yyyy-MM-dd'T'HH:mm"),
      data_vencimento: tarefa.data_vencimento ? format(new Date(tarefa.data_vencimento), "yyyy-MM-dd'T'HH:mm") : '',
      gera_multa: !!tarefa.gera_multa,
      observacoes: tarefa.observacoes || ''
    });
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (confirm('Tem certeza que deseja cancelar esta tarefa?')) {
      try {
        await tarefasAPI.delete(id);
        loadData();
      } catch (error) {
        alert('Erro ao cancelar tarefa');
      }
    }
  };

  const handleStatusChange = async (tarefa, newStatus) => {
    try {
      await tarefasAPI.update(tarefa.id, { status: newStatus });
      loadData();
    } catch (error) {
      alert('Erro ao atualizar status');
    }
  };

  const resetForm = () => {
    setFormData({
      titulo: '',
      descricao: '',
      empresa_id: '',
      setor_id: '',
      responsavel_id: '',
      prioridade: 'media',
      data_prazo: '',
      data_vencimento: '',
      gera_multa: false,
      observacoes: ''
    });
  };

  const handleTransfer = async () => {
    if (!transferResp) return;
    try {
      await tarefasAPI.transferir(showTransfer.id, parseInt(transferResp));
      setShowTransfer(null);
      setTransferResp('');
      loadData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao transferir tarefa');
    }
  };

  const getEmpresaNome = (id) => empresas.find(e => e.id === id)?.razao_social || '-';
  const getSetorNome = (id) => setores.find(s => s.id === id)?.nome || '-';
  const getUsuarioNome = (id) => usuarios.find(u => u.id === id)?.nome || '-';

  if (loading) {
    return <div className="flex items-center justify-center h-64">Carregando...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Tarefas</h1>
        <button
          onClick={() => {
            setEditingTarefa(null);
            resetForm();
            setShowModal(true);
          }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={18} />
          Nova Tarefa
        </button>
      </div>

      <div className="flex gap-4 mb-6">
        <select
          value={filtros.empresa_id}
          onChange={(e) => setFiltros({ ...filtros, empresa_id: e.target.value })}
          className="input-field w-auto"
        >
          <option value="">Todas as empresas</option>
          {empresas.map(e => (
            <option key={e.id} value={e.id}>{e.razao_social}</option>
          ))}
        </select>
        <select
          value={filtros.status}
          onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}
          className="input-field w-auto"
        >
          <option value="">Todos os status</option>
          {Object.entries(statusLabels).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>

      <div className="card">
        {filteredTarefas.length === 0 ? (
          <div className="text-center py-12">
            <ListTodo size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">Nenhuma tarefa encontrada</p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredTarefas.map((tarefa) => {
              const prazoDate = new Date(tarefa.data_prazo);
              const atrasada = isPast(prazoDate) && tarefa.status !== 'concluida' && tarefa.status !== 'cancelada';

              return (
                <div
                  key={tarefa.id}
                  className={`p-4 rounded-lg border ${
                    atrasada ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        {atrasada && <AlertTriangle size={16} className="text-red-500" />}
                        <h3 className="font-semibold text-gray-800">{tarefa.titulo}</h3>
                      </div>

                      {tarefa.descricao && (
                        <p className="text-sm text-gray-600 mb-2">{tarefa.descricao}</p>
                      )}

                      <div className="flex flex-wrap gap-2 text-sm text-gray-500">
                        <span>Empresa: {getEmpresaNome(tarefa.empresa_id)}</span>
                        {tarefa.setor_id && <span>• Setor: {getSetorNome(tarefa.setor_id)}</span>}
                        {tarefa.responsavel_id && <span>• Responsável: {getUsuarioNome(tarefa.responsavel_id)}</span>}
                      </div>

                      <div className="flex items-center gap-4 mt-3 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs ${statusColors[tarefa.status]}`}>
                          {statusLabels[tarefa.status]}
                        </span>
                        <span className={`px-2 py-1 rounded-full text-xs ${prioridadeColors[tarefa.prioridade]}`}>
                          {prioridadeLabels[tarefa.prioridade]}
                        </span>
                        <span className="flex items-center gap-1 text-gray-500">
                          <Clock size={14} />
                          Prazo: {format(prazoDate, "dd/MM/yyyy HH:mm", { locale: ptBR })}
                        </span>
                        {tarefa.data_vencimento && (
                          <span className="text-gray-500">
                            • Venc.: {format(new Date(tarefa.data_vencimento), "dd/MM/yyyy", { locale: ptBR })}
                          </span>
                        )}
                        {tarefa.gera_multa && (
                          <span className="px-2 py-1 rounded-full text-xs bg-red-100 text-red-700">⚠️ Gera multa</span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {tarefa.status !== 'concluida' && tarefa.status !== 'cancelada' && (
                        <select
                          value={tarefa.status}
                          onChange={(e) => handleStatusChange(tarefa, e.target.value)}
                          className="text-sm border border-gray-300 rounded-lg px-2 py-1"
                        >
                          <option value="pendente">Pendente</option>
                          <option value="em_andamento">Em Andamento</option>
                          <option value="concluida">Concluída</option>
                        </select>
                      )}
                      {tarefa.status !== 'concluida' && tarefa.status !== 'cancelada' && (
                        <button
                          onClick={() => { setShowTransfer(tarefa); setTransferResp(''); }}
                          title="Transferir responsável"
                          className="p-2 text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                        >
                          <ArrowRightLeft size={16} />
                        </button>
                      )}
                      <button
                        onClick={() => handleEdit(tarefa)}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      >
                        <Edit2 size={16} />
                      </button>
                      <button
                        onClick={() => handleDelete(tarefa.id)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {showTransfer && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-md">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Transferir tarefa</h2>
              <p className="text-sm text-gray-500 mt-1">{showTransfer.titulo}</p>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Novo responsável *</label>
                <select
                  value={transferResp}
                  onChange={(e) => setTransferResp(e.target.value)}
                  className="input-field"
                >
                  <option value="">Selecione</option>
                  {usuarios.filter(u => u.id !== showTransfer.responsavel_id).map(u => (
                    <option key={u.id} value={u.id}>{u.nome}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowTransfer(null)} className="btn-secondary flex-1">
                  Cancelar
                </button>
                <button type="button" onClick={handleTransfer} disabled={!transferResp} className="btn-primary flex-1">
                  Transferir
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-xl w-full max-w-lg">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold">
                {editingTarefa ? 'Editar Tarefa' : 'Nova Tarefa'}
              </h2>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Título *</label>
                <input
                  type="text"
                  value={formData.titulo}
                  onChange={(e) => setFormData({ ...formData, titulo: e.target.value })}
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
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Empresa *</label>
                  <select
                    value={formData.empresa_id}
                    onChange={(e) => setFormData({ ...formData, empresa_id: e.target.value })}
                    className="input-field"
                    required
                  >
                    <option value="">Selecione</option>
                    {empresas.map(e => (
                      <option key={e.id} value={e.id}>{e.razao_social}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Setor</label>
                  <select
                    value={formData.setor_id}
                    onChange={(e) => setFormData({ ...formData, setor_id: e.target.value })}
                    className="input-field"
                  >
                    <option value="">Selecione</option>
                    {setores.map(s => (
                      <option key={s.id} value={s.id}>{s.nome}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Responsável</label>
                  <select
                    value={formData.responsavel_id}
                    onChange={(e) => setFormData({ ...formData, responsavel_id: e.target.value })}
                    className="input-field"
                  >
                    <option value="">Selecione</option>
                    {usuarios.map(u => (
                      <option key={u.id} value={u.id}>{u.nome}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Prioridade</label>
                  <select
                    value={formData.prioridade}
                    onChange={(e) => setFormData({ ...formData, prioridade: e.target.value })}
                    className="input-field"
                  >
                    {Object.entries(prioridadeLabels).map(([key, label]) => (
                      <option key={key} value={key}>{label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Prazo interno *</label>
                  <input
                    type="datetime-local"
                    value={formData.data_prazo}
                    onChange={(e) => setFormData({ ...formData, data_prazo: e.target.value })}
                    className="input-field"
                    required
                  />
                  <p className="text-xs text-gray-400 mt-1">Limite da equipe — comanda os alertas.</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Vencimento</label>
                  <input
                    type="datetime-local"
                    value={formData.data_vencimento}
                    onChange={(e) => setFormData({ ...formData, data_vencimento: e.target.value })}
                    className="input-field"
                  />
                  <p className="text-xs text-gray-400 mt-1">Data fiscal/legal.</p>
                </div>
              </div>
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                  <input
                    type="checkbox"
                    checked={formData.gera_multa}
                    onChange={(e) => setFormData({ ...formData, gera_multa: e.target.checked })}
                    className="h-4 w-4"
                  />
                  Esta tarefa gera multa se o vencimento for perdido
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
                <textarea
                  value={formData.observacoes}
                  onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
                  className="input-field"
                  rows={2}
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">
                  Cancelar
                </button>
                <button type="submit" className="btn-primary flex-1">
                  {editingTarefa ? 'Salvar' : 'Cadastrar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}