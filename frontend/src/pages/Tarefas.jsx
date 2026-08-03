import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { tarefasAPI, empresasAPI, setoresAPI, usuariosAPI, obrigacoesAPI } from '../services/api';
import { format, isPast, isToday } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Plus, Edit2, Trash2, ListTodo, AlertTriangle, Clock, CheckCircle, ArrowRightLeft, Copy } from 'lucide-react';

const REGIMES_COPY = [
  { value: '', label: 'Todos os regimes' },
  { value: 'indefinido', label: 'Indefinido' },
  { value: 'lucro_real', label: 'Lucro Real' },
  { value: 'lucro_presumido', label: 'Lucro Presumido' },
  { value: 'mei', label: 'MEI' },
  { value: 'simples_nacional', label: 'Simples Nacional' },
  { value: 'terceiro_setor', label: 'Terceiro Setor' },
];
const SEGMENTOS_COPY = [
  { value: '', label: 'Todos os grupos' },
  { value: 'comercio', label: 'Comércio' },
  { value: 'servico', label: 'Serviço' },
  { value: 'comercio_servico', label: 'Comércio & Serviço' },
  { value: 'industria', label: 'Indústria' },
];

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

// Paleta Sage & Creme (padrão Zoaria/BPS4)
const SAGE = { cardBg: '#fffdf9', border: '#dccdb6', atrasBorder: '#d9b3aa', txt: '#2f3b2f', txt3: '#808a74' };
const statusSage = {
  pendente:     { bg: '#f6efdd', fg: '#8a6a2e' },
  em_andamento: { bg: '#dcefed', fg: '#3a7d76' },
  concluida:    { bg: '#e2ebde', fg: '#4d8a3f' },
  atrasada:     { bg: '#f7e7e3', fg: '#a24a3a' },
  cancelada:    { bg: '#eee7da', fg: '#808a74' },
};
const prioSage = {
  baixa:   { bg: '#eee7da', fg: '#808a74' },
  media:   { bg: '#e2ebde', fg: '#566450' },
  alta:    { bg: '#f6efdd', fg: '#8a6a2e' },
  urgente: { bg: '#f7e7e3', fg: '#a24a3a' },
};

// Cor de acento por setor (borda esquerda do card)
const setorCores = [
  { re: /contab|cont[áa]b/i, cor: '#3a7d76' },   // Contabilidade -> teal
  { re: /fiscal/i,           cor: '#6e7f63' },   // Fiscal -> oliva
  { re: /financ/i,           cor: '#8a6a2e' },   // Financeiro -> tan/dourado
  { re: /\bdp\b|pessoal/i,   cor: '#a24a3a' },   // DP -> terracota
];
const corDoSetor = (nome) => (setorCores.find((s) => s.re.test(nome || ''))?.cor) || '#c9bfa8';

export default function Tarefas() {
  const [tarefas, setTarefas] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [setores, setSetores] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [obrigacoes, setObrigacoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingTarefa, setEditingTarefa] = useState(null);
  const [searchParams] = useSearchParams();
  const [filtros, setFiltros] = useState({
    empresa_id: '', status: '', setor_id: searchParams.get('setor') || '',
  });
  const [showTransfer, setShowTransfer] = useState(null); // tarefa sendo transferida
  const [transferResp, setTransferResp] = useState('');
  const [showCopy, setShowCopy] = useState(false);
  const [copyOrigem, setCopyOrigem] = useState('');
  const [copyDestino, setCopyDestino] = useState('');
  const [copyRegime, setCopyRegime] = useState('');
  const [copyGrupo, setCopyGrupo] = useState('');
  const [formData, setFormData] = useState({
    titulo: '',
    descricao: '',
    empresa_id: '',
    setor_id: '',
    obrigacao_id: '',
    responsavel_ids: [],
    supervisor_id: '',
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
      const [tarefasRes, empresasRes, setoresRes, usuariosRes, obrigacoesRes] = await Promise.all([
        tarefasAPI.list(),
        empresasAPI.list(),
        setoresAPI.list(),
        usuariosAPI.list(),
        obrigacoesAPI.list()
      ]);
      setTarefas(tarefasRes.data);
      setEmpresas(empresasRes.data);
      setSetores(setoresRes.data);
      setUsuarios(usuariosRes.data);
      setObrigacoes(obrigacoesRes.data);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredTarefas = tarefas.filter(t => {
    if (filtros.empresa_id && t.empresa_id !== parseInt(filtros.empresa_id)) return false;
    if (filtros.status && t.status !== filtros.status) return false;
    if (filtros.setor_id && t.setor_id !== parseInt(filtros.setor_id)) return false;
    return true;
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = {
        ...formData,
        empresa_id: parseInt(formData.empresa_id),
        setor_id: formData.setor_id ? parseInt(formData.setor_id) : null,
        obrigacao_id: formData.obrigacao_id ? parseInt(formData.obrigacao_id) : null,
        responsavel_ids: (formData.responsavel_ids || []).map(Number),
        supervisor_id: formData.supervisor_id ? parseInt(formData.supervisor_id) : null,
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
      obrigacao_id: tarefa.obrigacao_id || '',
      responsavel_ids: (tarefa.responsaveis || []).map((r) => r.id),
      supervisor_id: tarefa.supervisor?.id || '',
      prioridade: tarefa.prioridade,
      data_prazo: tarefa.data_prazo ? format(new Date(tarefa.data_prazo), "yyyy-MM-dd'T'HH:mm") : '',
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
      obrigacao_id: '',
      responsavel_ids: [],
      supervisor_id: '',
      prioridade: 'media',
      data_prazo: '',
      data_vencimento: '',
      gera_multa: false,
      observacoes: ''
    });
  };

  // Ao escolher uma obrigação, puxa setor/responsável/supervisor dela.
  const aoEscolherObrigacao = (id) => {
    const o = obrigacoes.find((x) => String(x.id) === String(id));
    setFormData((f) => ({
      ...f,
      obrigacao_id: id,
      titulo: f.titulo || (o?.nome ?? ''),
      setor_id: o?.setor_id || f.setor_id,
      responsavel_ids: o?.responsavel_id ? [o.responsavel_id] : f.responsavel_ids,
      supervisor_id: o?.supervisor_id || f.supervisor_id,
    }));
  };

  const handleCopiar = async () => {
    if (!copyOrigem || !copyDestino) return;
    try {
      const res = await tarefasAPI.copiar(parseInt(copyOrigem), parseInt(copyDestino));
      alert(res.data?.message || 'Tarefas copiadas.');
      setShowCopy(false);
      setCopyOrigem(''); setCopyDestino(''); setCopyRegime(''); setCopyGrupo('');
      loadData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao copiar tarefas');
    }
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
        <div className="flex gap-2">
          <button
            onClick={() => { setShowCopy(true); }}
            className="btn-secondary flex items-center gap-2"
          >
            <Copy size={18} />
            Copiar tarefas
          </button>
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
          value={filtros.setor_id}
          onChange={(e) => setFiltros({ ...filtros, setor_id: e.target.value })}
          className="input-field w-auto"
        >
          <option value="">Todos os setores</option>
          {setores.map(s => (
            <option key={s.id} value={s.id}>{s.nome}</option>
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

      {filteredTarefas.length === 0 ? (
        <div className="card text-center py-12">
          <ListTodo size={48} className="mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500">Nenhuma tarefa encontrada</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
          {filteredTarefas.map((tarefa) => {
            const prazoDate = tarefa.data_prazo ? new Date(tarefa.data_prazo) : null;
            const atrasada = prazoDate && isPast(prazoDate) && tarefa.status !== 'concluida' && tarefa.status !== 'cancelada';
            const st = statusSage[tarefa.status] || statusSage.pendente;
            const pr = prioSage[tarefa.prioridade] || prioSage.media;
            const ativa = tarefa.status !== 'concluida' && tarefa.status !== 'cancelada';
            const setorNome = tarefa.setor_id ? getSetorNome(tarefa.setor_id) : null;
            const corSet = corDoSetor(setorNome);
            return (
              <div key={tarefa.id} className="rounded-lg border p-2.5 flex flex-col"
                style={{ background: SAGE.cardBg, borderColor: atrasada ? SAGE.atrasBorder : SAGE.border, borderLeft: `4px solid ${corSet}` }}>
                <div className="flex items-start gap-1 mb-1">
                  {atrasada && <AlertTriangle size={13} className="mt-0.5 shrink-0" style={{ color: '#a24a3a' }} />}
                  <h3 className="text-[13px] font-medium leading-tight line-clamp-2" style={{ color: SAGE.txt }} title={tarefa.titulo}>
                    {tarefa.titulo}
                  </h3>
                </div>
                {setorNome && (
                  <span className="self-start px-1.5 py-0.5 rounded text-[10px] font-medium mb-1"
                    style={{ background: corSet + '22', color: corSet }}>{setorNome}</span>
                )}
                <div className="text-[11px] leading-snug space-y-0.5 mb-1.5" style={{ color: SAGE.txt3 }}>
                  <p className="truncate" title={getEmpresaNome(tarefa.empresa_id)}>{getEmpresaNome(tarefa.empresa_id)}</p>
                  {tarefa.responsaveis?.length > 0 && (
                    <p className="truncate" title={tarefa.responsaveis.map(r => r.nome).join(', ')}>
                      Resp.: {tarefa.responsaveis.map(r => r.nome).join(', ')}
                    </p>
                  )}
                  <p className="flex items-center gap-1">
                    <Clock size={11} />
                    {prazoDate ? format(prazoDate, "dd/MM/yy", { locale: ptBR }) : 'sem prazo'}
                    {tarefa.gera_multa && <AlertTriangle size={11} style={{ color: '#a24a3a' }} title="Gera multa" />}
                  </p>
                </div>
                <div className="flex flex-wrap gap-1 mb-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: st.bg, color: st.fg }}>{statusLabels[tarefa.status]}</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: pr.bg, color: pr.fg }}>{prioridadeLabels[tarefa.prioridade]}</span>
                </div>
                <div className="mt-auto flex items-center gap-1">
                  {ativa && (
                    <select value={tarefa.status} onChange={(e) => handleStatusChange(tarefa, e.target.value)}
                      className="flex-1 text-[11px] border rounded px-1 py-1 bg-white" style={{ borderColor: SAGE.border, color: '#55614e' }}>
                      <option value="pendente">Pendente</option>
                      <option value="em_andamento">Em Andamento</option>
                      <option value="concluida">Concluída</option>
                    </select>
                  )}
                  {ativa && (
                    <button onClick={() => { setShowTransfer(tarefa); setTransferResp(''); }} title="Transferir" className="p-1 rounded hover:bg-[#e2ebde]" style={{ color: '#8a6a2e' }}>
                      <ArrowRightLeft size={14} />
                    </button>
                  )}
                  <button onClick={() => handleEdit(tarefa)} title="Editar" className="p-1 rounded hover:bg-[#dcefed]" style={{ color: '#3a7d76' }}>
                    <Edit2 size={14} />
                  </button>
                  <button onClick={() => handleDelete(tarefa.id)} title="Cancelar" className="p-1 rounded hover:bg-[#f7e7e3]" style={{ color: '#a24a3a' }}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showCopy && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Copiar tarefas</h2>
              <p className="text-sm text-gray-500 mt-1">
                Copia as tarefas em aberto de uma empresa para outra, como modelo (sem datas).
              </p>
            </div>
            <div className="p-4 space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Filtrar por regime</label>
                  <select value={copyRegime} onChange={(e) => { setCopyRegime(e.target.value); setCopyOrigem(''); }} className="input-field">
                    {REGIMES_COPY.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Filtrar por grupo</label>
                  <select value={copyGrupo} onChange={(e) => { setCopyGrupo(e.target.value); setCopyOrigem(''); }} className="input-field">
                    {SEGMENTOS_COPY.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Empresa de origem *</label>
                <select value={copyOrigem} onChange={(e) => setCopyOrigem(e.target.value)} className="input-field">
                  <option value="">Selecione</option>
                  {empresas
                    .filter((e) => (!copyRegime || e.regime_tributario === copyRegime) && (!copyGrupo || e.segmento === copyGrupo))
                    .map((e) => <option key={e.id} value={e.id}>{e.razao_social}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Empresa de destino *</label>
                <select value={copyDestino} onChange={(e) => setCopyDestino(e.target.value)} className="input-field">
                  <option value="">Selecione</option>
                  {empresas
                    .filter((e) => String(e.id) !== copyOrigem)
                    .map((e) => <option key={e.id} value={e.id}>{e.razao_social}</option>)}
                </select>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowCopy(false)} className="btn-secondary flex-1">
                  Cancelar
                </button>
                <button type="button" onClick={handleCopiar} disabled={!copyOrigem || !copyDestino} className="btn-primary flex-1">
                  Copiar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showTransfer && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Transferir tarefa</h2>
              <p className="text-sm text-gray-500 mt-1">{showTransfer.titulo}</p>
            </div>
            <div className="p-4 space-y-3">
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
          <div className="bg-white rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">
                {editingTarefa ? 'Editar Tarefa' : 'Nova Tarefa'}
              </h2>
            </div>
            <form onSubmit={handleSubmit} className="p-4 space-y-3">
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
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Obrigação (opcional)</label>
                <select
                  value={formData.obrigacao_id}
                  onChange={(e) => aoEscolherObrigacao(e.target.value)}
                  className="input-field"
                >
                  <option value="">Nenhuma (tarefa avulsa)</option>
                  {obrigacoes.map(o => (
                    <option key={o.id} value={o.id}>{o.nome}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-400 mt-1">Vincula à obrigação e puxa setor/responsáveis/supervisor dela.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Responsáveis</label>
                <div className="max-h-32 overflow-y-auto border border-gray-200 rounded-lg p-2 space-y-1">
                  {usuarios.filter(u => !u.bloqueado && (u.tipo !== 'cliente' || String(u.empresa_id) === String(formData.empresa_id))).map(u => (
                    <label key={u.id} className="flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.responsavel_ids.includes(u.id)}
                        onChange={() => setFormData(f => ({
                          ...f,
                          responsavel_ids: f.responsavel_ids.includes(u.id)
                            ? f.responsavel_ids.filter(x => x !== u.id)
                            : [...f.responsavel_ids, u.id],
                        }))}
                        className="h-4 w-4"
                      />
                      {u.nome}
                    </label>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-1">{formData.responsavel_ids.length} selecionado(s)</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Supervisor</label>
                  <select
                    value={formData.supervisor_id}
                    onChange={(e) => setFormData({ ...formData, supervisor_id: e.target.value })}
                    className="input-field"
                  >
                    <option value="">Sem supervisor</option>
                    {usuarios.filter(u => u.tipo !== 'cliente' && !u.bloqueado).map(u => (
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