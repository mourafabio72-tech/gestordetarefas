import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { tarefasAPI, empresasAPI, setoresAPI, usuariosAPI, obrigacoesAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { format, isPast, isToday } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Plus, Edit2, Trash2, ListTodo, AlertTriangle, Clock, CheckCircle, ArrowRightLeft, Copy, Link2, Flag} from 'lucide-react';
import { filtrarTarefas, competenciasDe, presetsVencimento,
         filtrosVazios, temFiltroAtivo, SEM_COMPETENCIA } from './filtroTarefas';

const REGIMES_COPY = [
  { value: '', label: 'Todos os regimes' },
  { value: 'indefinido', label: 'Indefinido' },
  { value: 'lucro_real', label: 'Lucro Real' },
  { value: 'lucro_presumido', label: 'Lucro Presumido' },
  { value: 'mei', label: 'MEI' },
  { value: 'simples_nacional', label: 'Simples Nacional' },
  { value: 'terceiro_setor', label: 'Terceiro Setor' },
  { value: 'imune', label: 'Imune' },
  { value: 'isento', label: 'Isento' },
];
const SEGMENTOS_COPY = [
  { value: '', label: 'Todos os grupos' },
  { value: 'comercio', label: 'Comércio' },
  { value: 'servico', label: 'Serviço' },
  { value: 'comercio_servico', label: 'Comércio & Serviço' },
  { value: 'industria', label: 'Indústria' },
  { value: 'holding', label: 'Holding' },
  { value: 'imune', label: 'Imune' },
  { value: 'igreja', label: 'Igreja' },
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
  const { user } = useAuth();
  const ehAdmin = user?.grupo === 'admin';
  const [tarefas, setTarefas] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [setores, setSetores] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [obrigacoes, setObrigacoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingTarefa, setEditingTarefa] = useState(null);
  const [searchParams] = useSearchParams();
  const [filtros, setFiltros] = useState(filtrosVazios(searchParams.get('setor') || ''));
  const [showTransfer, setShowTransfer] = useState(null); // tarefa sendo transferida
  const [transferResp, setTransferResp] = useState('');
  const [showCopy, setShowCopy] = useState(false);
  const [copyOrigem, setCopyOrigem] = useState('');
  const [copyDestinos, setCopyDestinos] = useState([]);
  const [copyBusca, setCopyBusca] = useState('');
  const [copyRegime, setCopyRegime] = useState('');
  const [copyGrupo, setCopyGrupo] = useState('');
  const _hoje = new Date();
  const [showExcluirMes, setShowExcluirMes] = useState(false);
  const [exclMes, setExclMes] = useState(_hoje.getMonth() + 1);
  const [exclAno, setExclAno] = useState(_hoje.getFullYear());
  const [excluindoMes, setExcluindoMes] = useState(false);
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

  const competenciasDisponiveis = competenciasDe(tarefas);
  const filteredTarefas = filtrarTarefas(tarefas, filtros);
  const aplicarPreset = (p) => setFiltros({ ...filtros, venc_de: p.de, venc_ate: p.ate });
  const presetAtivo = (p) => filtros.venc_de === p.de && filtros.venc_ate === p.ate;
  const temFiltro = temFiltroAtivo(filtros);

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
      alert(mensagemDeErro(error, 'Erro ao salvar tarefa'));
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

  // Dois passos: cancelar (reversível) e, na tarefa já cancelada, excluir de vez.
  const handleDelete = async (tarefa) => {
    const cancelada = tarefa.status === 'cancelada';
    const pergunta = cancelada
      ? `Excluir "${tarefa.titulo}" definitivamente?\n\nIsso apaga a tarefa e o comprovante anexado, se houver. Não dá para desfazer.`
      : `Cancelar "${tarefa.titulo}"?\n\nEla continua na lista como cancelada. Para excluir de vez, use a lixeira de novo depois.`;
    if (!confirm(pergunta)) return;
    try {
      await tarefasAPI.delete(tarefa.id);
      loadData();
    } catch (error) {
      alert(mensagemDeErro(error, cancelada ? 'Erro ao excluir a tarefa.' : 'Erro ao cancelar a tarefa.'));
    }
  };

  const bloqueiaBaixaManual = (tarefa) => tarefa.exige_documento && !tarefa.anexo_nome;

  const handleStatusChange = async (tarefa, newStatus) => {
    if (newStatus === 'concluida' && bloqueiaBaixaManual(tarefa)) {
      alert('Esta tarefa exige validação de documento: baixe pelo e-validador. Baixa manual não é permitida.');
      return;
    }
    try {
      await tarefasAPI.update(tarefa.id, { status: newStatus });
      loadData();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao atualizar status'));
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
    if (!copyOrigem || copyDestinos.length === 0) return;
    try {
      for (const dest of copyDestinos) {
        await tarefasAPI.copiar(parseInt(copyOrigem), parseInt(dest));
      }
      alert(`Tarefas copiadas para ${copyDestinos.length} empresa(s).`);
      setShowCopy(false);
      setCopyOrigem(''); setCopyDestinos([]); setCopyBusca(''); setCopyRegime(''); setCopyGrupo('');
      loadData();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao copiar tarefas'));
    }
  };

  const MESES_NOME = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const handleExcluirMes = async () => {
    const comp = `${String(exclMes).padStart(2, '0')}/${exclAno}`;
    if (!confirm(`Excluir DEFINITIVAMENTE as tarefas geradas da competência ${comp} (${MESES_NOME[exclMes - 1]}/${exclAno})?\n\nApaga só as que vieram de obrigações: não mexe nas tarefas avulsas. Dá para regerar depois. Não dá para desfazer.`)) return;
    setExcluindoMes(true);
    try {
      const { data } = await tarefasAPI.excluirCompetencia(comp);
      alert(`${data.excluidas} tarefa(s) excluída(s) da competência ${comp}.`);
      setShowExcluirMes(false);
      loadData();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao excluir tarefas do mês.'));
    } finally { setExcluindoMes(false); }
  };

  const handleCopiarLink = async (tarefa) => {
    try {
      const { data } = await tarefasAPI.linkEnvio(tarefa.id);
      try {
        await navigator.clipboard.writeText(data.link);
        alert('Link de envio copiado:\n\n' + data.link);
      } catch {
        prompt('Copie o link de envio do comprovante:', data.link);
      }
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao gerar o link'));
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
      alert(mensagemDeErro(error, 'Erro ao transferir tarefa'));
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
          {ehAdmin && (
            <button
              onClick={() => setShowExcluirMes(true)}
              className="btn-secondary flex items-center gap-2 text-red-600"
              title="Apaga as tarefas geradas por obrigação de uma competência (desfaz o 'Gerar tarefas do mês'). Só admin."
            >
              <Trash2 size={18} />
              Excluir tarefas do mês
            </button>
          )}
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

      {/* Barra de filtros — uma faixa única de controles, lado a lado.
          O rótulo de cada select é a própria opção "Todas/Todos", em vez de um
          label acima: label empilhado dobra a altura da barra e é o que fazia
          ela ocupar dois andares. Os selects longos dividem a sobra entre si
          (é a razão social da empresa que estica e quebrava a linha); data e
          atalhos ficam fixos, porque não encolhem sem cortar conteúdo. */}
      <div className="flex items-center gap-1 mb-5 text-xs overflow-x-auto">
        <input
          type="search"
          value={filtros.texto}
          onChange={(e) => setFiltros({ ...filtros, texto: e.target.value })}
          placeholder="Buscar tarefa..."
          className={`flex-1 min-w-[120px] h-8 px-2 text-xs border rounded-md bg-[#fffdf9] outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent ${
            filtros.texto ? 'border-primary-400' : 'border-gray-300'}`}
        />
        <select
          value={filtros.usuario_id}
          onChange={(e) => setFiltros({ ...filtros, usuario_id: e.target.value })}
          title="Responsável ou supervisor da tarefa"
          className={`flex-1 min-w-[92px] h-8 pl-1.5 pr-0.5 text-xs border rounded-md bg-[#fffdf9] outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent ${
            filtros.usuario_id ? 'border-primary-400 text-primary-800' : 'border-gray-300'}`}
        >
          <option value="">Todas as pessoas</option>
          {usuarios.filter((u) => !u.bloqueado).map((u) => (
            <option key={u.id} value={u.id}>{u.nome}</option>
          ))}
        </select>
        {[
          { chave: 'empresa_id', vazio: 'Todas as empresas',
            opcoes: empresas.map(e => ({ v: e.id, t: e.razao_social })) },
          { chave: 'setor_id', vazio: 'Todos os setores',
            opcoes: setores.map(x => ({ v: x.id, t: x.nome })) },
          { chave: 'status', vazio: 'Todos os status',
            opcoes: Object.entries(statusLabels).map(([v, t]) => ({ v, t })) },
        ].map(f => (
          <select
            key={f.chave}
            value={filtros[f.chave]}
            onChange={(e) => setFiltros({ ...filtros, [f.chave]: e.target.value })}
            className={`flex-1 min-w-[92px] h-8 pl-1.5 pr-0.5 text-xs border rounded-md bg-[#fffdf9] outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent ${
              filtros[f.chave] ? 'border-primary-400 text-primary-800' : 'border-gray-300'}`}
          >
            <option value="">{f.vazio}</option>
            {f.opcoes.map(o => <option key={o.v} value={o.v}>{o.t}</option>)}
          </select>
        ))}

        <select
          value={filtros.competencia}
          onChange={(e) => setFiltros({ ...filtros, competencia: e.target.value })}
          className={`shrink-0 w-[118px] h-8 pl-1.5 pr-0.5 text-xs border rounded-md bg-[#fffdf9] outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent ${
            filtros.competencia ? 'border-primary-400 text-primary-800' : 'border-gray-300'}`}
          title="Competência do fato gerador — MM/AAAA"
        >
          <option value="">Toda competência</option>
          {competenciasDisponiveis.map(c => <option key={c} value={c}>{c}</option>)}
          <option value={SEM_COMPETENCIA}>— avulsas</option>
        </select>

        <span className="shrink-0 text-[11px] text-gray-500 pl-1">Vence</span>
        <input
          type="date"
          value={filtros.venc_de}
          onChange={(e) => setFiltros({ ...filtros, venc_de: e.target.value })}
          title="Vencimento a partir de"
          className={`shrink-0 w-[118px] h-8 px-1 text-xs border rounded-md bg-[#fffdf9] outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent ${
            filtros.venc_de ? 'border-primary-400' : 'border-gray-300'}`}
        />
        <span className="shrink-0 text-[11px] text-gray-500">a</span>
        <input
          type="date"
          value={filtros.venc_ate}
          onChange={(e) => setFiltros({ ...filtros, venc_ate: e.target.value })}
          title="Vencimento até"
          className={`shrink-0 w-[118px] h-8 px-1 text-xs border rounded-md bg-[#fffdf9] outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent ${
            filtros.venc_ate ? 'border-primary-400' : 'border-gray-300'}`}
        />

        <div className="flex shrink-0 ml-1">
          {presetsVencimento().map((p, i, arr) => (
            <button
              key={p.rotulo}
              type="button"
              onClick={() => aplicarPreset(p)}
              title={p.titulo}
              className={`h-8 px-2 text-[11px] font-medium border whitespace-nowrap transition
                ${i === 0 ? 'rounded-l-md' : '-ml-px'} ${i === arr.length - 1 ? 'rounded-r-md' : ''}
                ${presetAtivo(p)
                  ? 'bg-primary-100 border-primary-400 text-primary-800 relative z-10'
                  : 'bg-white border-gray-300 text-gray-600 hover:border-primary-300'}`}
            >
              {p.rotulo}
            </button>
          ))}
        </div>

        {temFiltro && (
          <button
            type="button"
            onClick={() => setFiltros(filtrosVazios())}
            title="Limpar todos os filtros"
            className="shrink-0 h-8 px-1.5 text-[11px] text-gray-500 underline hover:text-gray-700 whitespace-nowrap"
          >
            Limpar
          </button>
        )}
        <span className="shrink-0 text-[11px] text-gray-500 whitespace-nowrap tabular-nums pl-1">
          {filteredTarefas.length}/{tarefas.length}
        </span>
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
            // Fechamento do cliente naquele mês. `fechamento_cliente` vem como
            // "AAAA-MM-DD" puro: passar por new Date() o interpretaria como UTC
            // e mostraria o dia anterior aqui no fuso de Brasília.
            const fech = tarefa.fechamento_cliente || null;
            const fechBr = fech ? `${fech.slice(8, 10)}/${fech.slice(5, 7)}` : null;
            const venc = (tarefa.data_vencimento || '').slice(0, 10);
            const encerra = fech && venc && fech === venc;
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
                  {fechBr && (
                    encerra ? (
                      <p className="flex items-center gap-1 font-medium" style={{ color: '#5f7057' }}
                         title={`Esta tarefa vence no próprio dia do fechamento de ${getEmpresaNome(tarefa.empresa_id)} — é a última do processo.`}>
                        <Flag size={11} /> encerra o fechamento
                      </p>
                    ) : (
                      <p className="flex items-center gap-1" style={{ color: '#8a8378' }}
                         title={`${getEmpresaNome(tarefa.empresa_id)} fecha o mês em ${fechBr}. Esta tarefa vem antes.`}>
                        <Flag size={11} /> cliente fecha {fechBr}
                      </p>
                    )
                  )}
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
                      <option value="concluida" disabled={bloqueiaBaixaManual(tarefa)}>
                        {bloqueiaBaixaManual(tarefa) ? 'Concluída (só e-validador)' : 'Concluída'}
                      </option>
                    </select>
                  )}
                  {ativa && (
                    <button onClick={() => handleCopiarLink(tarefa)} title="Copiar link de envio do comprovante" className="p-1 rounded hover:bg-[#e7eef6]" style={{ color: '#2f6fb0' }}>
                      <Link2 size={14} />
                    </button>
                  )}
                  {ativa && (
                    <button onClick={() => { setShowTransfer(tarefa); setTransferResp(''); }} title="Transferir" className="p-1 rounded hover:bg-[#e2ebde]" style={{ color: '#8a6a2e' }}>
                      <ArrowRightLeft size={14} />
                    </button>
                  )}
                  <button onClick={() => handleEdit(tarefa)} title="Editar" className="p-1 rounded hover:bg-[#dcefed]" style={{ color: '#3a7d76' }}>
                    <Edit2 size={14} />
                  </button>
                  <button onClick={() => handleDelete(tarefa)}
                    title={tarefa.status === 'cancelada' ? 'Excluir definitivamente' : 'Cancelar'}
                    className="p-1 rounded hover:bg-[#f7e7e3]" style={{ color: '#a24a3a' }}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showExcluirMes && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-md">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Excluir tarefas do mês</h2>
              <p className="text-sm text-gray-500 mt-1">
                Apaga as tarefas <strong>geradas por obrigação</strong> da competência escolhida.
                Não mexe nas tarefas avulsas (criadas à mão). Dá para regerar depois.
              </p>
            </div>
            <div className="p-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Mês (competência)</label>
                  <select value={exclMes} onChange={(e) => setExclMes(parseInt(e.target.value))} className="input-field">
                    {MESES_NOME.map((m, i) => (
                      <option key={i + 1} value={i + 1}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Ano (competência)</label>
                  <input type="number" min="2000" max="2100" value={exclAno}
                    onChange={(e) => setExclAno(parseInt(e.target.value) || _hoje.getFullYear())}
                    className="input-field" />
                </div>
              </div>
              <p className="text-xs text-gray-500">
                Competência alvo: <strong>{String(exclMes).padStart(2, '0')}/{exclAno}</strong>.
                É a mesma competência que aparece na tarefa (não é o vencimento).
              </p>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowExcluirMes(false)} className="btn-secondary flex-1">Cancelar</button>
                <button type="button" onClick={handleExcluirMes} disabled={excluindoMes} className="btn-danger flex-1">
                  {excluindoMes ? 'Excluindo…' : 'Excluir definitivamente'}
                </button>
              </div>
            </div>
          </div>
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
                <select value={copyOrigem}
                  onChange={(e) => { setCopyOrigem(e.target.value); setCopyDestinos((ds) => ds.filter((x) => String(x) !== e.target.value)); }}
                  className="input-field">
                  <option value="">Selecione</option>
                  {empresas
                    .filter((e) => (!copyRegime || e.regime_tributario === copyRegime) && (!copyGrupo || e.segmento === copyGrupo))
                    .map((e) => <option key={e.id} value={e.id}>{e.razao_social}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Empresas de destino *</label>
                {(() => {
                  const termo = copyBusca.trim().toLowerCase();
                  const destinos = empresas.filter((e) => String(e.id) !== copyOrigem);
                  const filtradas = termo
                    ? destinos.filter((e) => `${e.razao_social} ${e.grupo || ''}`.toLowerCase().includes(termo))
                    : destinos;
                  const idsFiltrados = filtradas.map((e) => e.id);
                  return (
                    <>
                      <div className="flex items-center gap-2 mb-2">
                        <p className="text-xs text-gray-400 flex-1">{copyDestinos.length} selecionada(s)</p>
                        <button type="button" onClick={() => setCopyDestinos([...new Set([...copyDestinos, ...idsFiltrados])])}
                          className="text-xs text-primary-600 hover:underline">
                          {termo ? 'Selecionar filtradas' : 'Selecionar todas'}
                        </button>
                        <span className="text-gray-300">·</span>
                        <button type="button" onClick={() => setCopyDestinos([])} className="text-xs text-gray-500 hover:underline">Limpar</button>
                      </div>
                      <input type="text" value={copyBusca} onChange={(e) => setCopyBusca(e.target.value)}
                        placeholder="Buscar empresa ou grupo…" className="input-field mb-2 text-sm" />
                      <div className="max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-3 space-y-1">
                        {filtradas.length === 0 ? (
                          <p className="text-xs text-gray-400">Nenhuma empresa encontrada.</p>
                        ) : filtradas.map((e) => (
                          <label key={e.id} className="flex items-center gap-2 text-sm cursor-pointer">
                            <input type="checkbox"
                              checked={copyDestinos.includes(e.id)}
                              onChange={() => setCopyDestinos(copyDestinos.includes(e.id)
                                ? copyDestinos.filter((x) => x !== e.id)
                                : [...copyDestinos, e.id])}
                              className="h-4 w-4" />
                            {e.razao_social}
                            {e.grupo && <span className="text-xs text-gray-400">· {e.grupo}</span>}
                          </label>
                        ))}
                      </div>
                    </>
                  );
                })()}
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowCopy(false)} className="btn-secondary flex-1">
                  Cancelar
                </button>
                <button type="button" onClick={handleCopiar} disabled={!copyOrigem || copyDestinos.length === 0} className="btn-primary flex-1">
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
                  <p className="text-xs text-gray-400 mt-1">Limite da equipe: comanda os alertas.</p>
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