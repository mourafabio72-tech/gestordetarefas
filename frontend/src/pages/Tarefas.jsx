import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { tarefasAPI, empresasAPI, setoresAPI, usuariosAPI, obrigacoesAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Plus, Edit2, Trash2, ListTodo, AlertTriangle, Clock, CheckCircle, ArrowRightLeft, Copy, Link2, Flag, ChevronDown, MoreHorizontal, Paperclip, Download,
         Send, Upload, X, MessageCircle, Mail } from 'lucide-react';
import { filtrarTarefas, competenciasDe, presetsVencimento, filtrosVazios,
         temFiltroAtivo, filtrosDaUrl, rotuloDoRecorte, SEM_COMPETENCIA } from './filtroTarefas';
import { agruparTarefas, AGRUPAMENTOS } from './agruparTarefas';
import { alertaDaTarefa, fundoDoAlerta } from './alertaPrazo';
import { formatarRazaoSocial } from './razaoSocial';

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

// Um controle da barra de filtros. Verde na borda quando está filtrando algo:
// com oito campos numa faixa só, é o que responde "por que a lista está assim?"
// sem obrigar a ler campo por campo.
const ctrl = (ativo) =>
  `w-full h-8 px-2 text-xs border rounded-md bg-[#fffdf9] outline-none transition-colors
   focus:ring-2 focus:ring-primary-400 focus:border-transparent ${
     ativo ? 'border-primary-400 text-primary-800 font-medium' : 'border-gray-300 text-gray-800'}`;

// Uma linha do menu de ações do card.
function ItemMenu({ icone: Icone, children, onClick, perigo }) {
  return (
    <button type="button" onClick={onClick}
      className={`w-full flex items-center gap-2 px-2.5 py-1.5 text-[11px] text-left whitespace-nowrap
        ${perigo ? 'text-[#a24a3a] hover:bg-[#f7e7e3]' : 'text-[#55614e] hover:bg-[#e2ebde]'}`}>
      <Icone size={13} className="shrink-0" />
      {children}
    </button>
  );
}

// Campo com rótulo fixo por cima. O desenho anterior usava a opção vazia do
// próprio select como nome ("Todas as empresas"), e o nome sumia no instante em
// que você escolhia uma empresa -- restava um select com uma razão social e
// nenhuma pista do que ele filtra.
function Campo({ rotulo, dica, largura = '', children }) {
  return (
    <label className={`flex flex-col gap-1 ${largura}`} title={dica}>
      <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 whitespace-nowrap text-center">
        {rotulo}
      </span>
      {children}
    </label>
  );
}

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
  // A tela abre já filtrada quando vem de um link do Painel. Lê a URL inteira,
  // não só o setor: clicar em "2 atrasadas" tem de trazer as 2, e não a lista
  // toda para a pessoa procurar quais eram.
  const [filtros, setFiltros] = useState(() => filtrosDaUrl(searchParams));
  const recorte = rotuloDoRecorte(filtros);
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
    competencia: '',
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

  // Como a lista se organiza. Guardado no navegador porque é preferência de
  // quem abre a tela todo dia -- o fiscal quer por setor, o gestor por empresa
  // -- e reescolher a cada visita é atrito à toa.
  const [agrupar, setAgrupar] = useState(() => {
    try { const v = localStorage.getItem('tarefas.agrupar'); return v === null ? 'empresa' : v; }
    catch { return 'empresa'; }
  });
  useEffect(() => {
    try { localStorage.setItem('tarefas.agrupar', agrupar); } catch { /* modo anônimo */ }
  }, [agrupar]);
  const [recolhidos, setRecolhidos] = useState([]);
  // Qual card está com o menu de ações aberto (um por vez).
  const [menuAberto, setMenuAberto] = useState(null);
  // Entrega ao cliente: uma tarefa por vez, com o ensaio carregado antes.
  const [entrega, setEntrega] = useState(null);   // { tarefa, ensaio, enviando, resultado }
  useEffect(() => {
    if (menuAberto === null) return;
    const fechar = () => setMenuAberto(null);
    // Clique em qualquer lugar fecha; o próprio menu para a propagação. Também
    // fecha no Esc, que é o reflexo de quem abriu sem querer.
    const tecla = (e) => { if (e.key === 'Escape') setMenuAberto(null); };
    document.addEventListener('click', fechar);
    document.addEventListener('keydown', tecla);
    return () => { document.removeEventListener('click', fechar); document.removeEventListener('keydown', tecla); };
  }, [menuAberto]);
  const alternarGrupo = (chave) =>
    setRecolhidos((r) => (r.includes(chave) ? r.filter((c) => c !== chave) : [...r, chave]));

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = {
        ...formData,
        empresa_id: parseInt(formData.empresa_id),
        setor_id: formData.setor_id ? parseInt(formData.setor_id) : null,
        obrigacao_id: formData.obrigacao_id ? parseInt(formData.obrigacao_id) : null,
        competencia: formData.competencia.trim() || null,
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
      competencia: tarefa.competencia || '',
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

  // Abre o comprovante numa aba (PDF e imagem) ou salva em disco.
  //
  // Passa por blob porque a rota exige `Authorization`, e um <a href> não manda
  // cabeçalho. O objeto de URL é revogado depois de um minuto: revogar na hora
  // fecharia a aba que acabou de abrir, e nunca revogar seguraria o arquivo
  // inteiro na memória da aba enquanto ela estivesse viva.
  const abrirAnexo = async (tarefa, baixar = false) => {
    try {
      const { data } = await tarefasAPI.anexo(tarefa.id, baixar);
      const url = URL.createObjectURL(data);
      if (baixar) {
        const a = document.createElement('a');
        a.href = url;
        a.download = tarefa.anexo_nome ? tarefa.anexo_nome.split('_').slice(1).join('_') : 'comprovante';
        a.click();
      } else {
        window.open(url, '_blank', 'noopener');
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (error) {
      // O corpo do erro vem como blob por causa do responseType; sem ler o
      // texto, o 410 de "arquivo sumiu" viraria um alerta genérico.
      let texto = '';
      try { texto = JSON.parse(await error?.response?.data?.text()).detail; } catch { /* não era JSON */ }
      alert(texto || mensagemDeErro(error, 'Não foi possível abrir o comprovante'));
    }
  };

  // ── Entrega de documento ao cliente ───────────────────────────────────────
  // Conferir o que vai sair antes de mandar. Mesmo caminho por blob do
  // comprovante: a rota exige cabeçalho de sessão, e <a href> não manda.
  const abrirSaida = async (tarefa) => {
    try {
      const { data } = await tarefasAPI.saida(tarefa.id, false);
      const url = URL.createObjectURL(data);
      window.open(url, '_blank', 'noopener');
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (error) {
      alert(mensagemDeErro(error, 'Não foi possível abrir o documento'));
    }
  };

  const abrirEntrega = async (tarefa) => {
    setEntrega({ tarefa, ensaio: null, enviando: false, resultado: null, erro: null });
    try {
      const { data } = await tarefasAPI.enviarCliente(tarefa.id, true);
      setEntrega((e) => (e && e.tarefa.id === tarefa.id ? { ...e, ensaio: data } : e));
    } catch (error) {
      // Sem documento anexado ou empresa sem contato: o backend explica o quê.
      setEntrega((e) => (e && e.tarefa.id === tarefa.id
        ? { ...e, erro: mensagemDeErro(error, 'Não foi possível preparar o envio') } : e));
    }
  };

  const anexarSaida = async (arquivo) => {
    if (!arquivo || !entrega) return;
    setEntrega((e) => ({ ...e, enviando: true, erro: null }));
    try {
      const { data: anexo } = await tarefasAPI.anexarSaida(entrega.tarefa.id, arquivo);
      const { data } = await tarefasAPI.enviarCliente(entrega.tarefa.id, true);
      setEntrega((e) => ({ ...e, ensaio: data, enviando: false, erro: null,
                           conferencia: anexo?.conferencia || null,
                           exigeConfirmar: false }));
    } catch (error) {
      setEntrega((e) => ({ ...e, enviando: false,
        erro: mensagemDeErro(error, 'Não foi possível anexar o documento') }));
    }
  };

  // Documento que CONTRADIZ a tarefa não sai com um clique. Não é bloqueio:
  // CNPJ diferente pode ser matriz e filial, e travar de vez atrapalharia caso
  // legítimo. É um segundo passo — o suficiente para o envio errado não
  // acontecer por reflexo, que é como ele acontece.
  const confirmarEnvio = async (forcado = false) => {
    const contradiz = entrega?.conferencia && !entrega.conferencia.ok;
    if (contradiz && !forcado) {
      setEntrega((e) => ({ ...e, exigeConfirmar: true }));
      return;
    }
    setEntrega((e) => ({ ...e, enviando: true, erro: null, exigeConfirmar: false }));
    try {
      const { data } = await tarefasAPI.enviarCliente(entrega.tarefa.id, false);
      setEntrega((e) => ({ ...e, enviando: false, resultado: data }));
      loadData();
    } catch (error) {
      setEntrega((e) => ({ ...e, enviando: false,
        erro: mensagemDeErro(error, 'Falha ao enviar') }));
    }
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

  // Razão social sempre no padrão da MKB (Caixa de Título). O cadastro chega
  // misturado -- uns em caixa alta, outros não -- e empilhados como cabeçalho
  // de seção a diferença salta aos olhos.
  const getEmpresaNome = (id) =>
    formatarRazaoSocial(empresas.find(e => e.id === id)?.razao_social) || '-';
  const getSetorNome = (id) => setores.find(s => s.id === id)?.nome || '-';
  const getUsuarioNome = (id) => usuarios.find(u => u.id === id)?.nome || '-';

  if (loading) {
    return <div className="flex items-center justify-center h-64">Carregando...</div>;
  }

  // Nome para o cabeçalho de grupo. Devolve vazio (e não "-") quando o cadastro
  // sumiu: o agrupador troca isso por "Sem classificação", que é o que a pessoa
  // entende num título de seção.
  const grupos = agruparTarefas(filteredTarefas, agrupar, {
    empresa: (id) => formatarRazaoSocial(empresas.find((e) => e.id === id)?.razao_social),
    setor: (id) => setores.find((x) => x.id === id)?.nome || '',
  });

  // Um card. Extraído do JSX da lista porque agora ele é desenhado dentro de
  // cada grupo, e aninhado em dois maps o bloco ficava ilegível.
  // Some do card o que já está no cabeçalho do grupo: agrupando por empresa, a
  // razão social não se repete em cada um dos cards dela; por setor, idem.
  const cartao = (tarefa) => {
    const prazoDate = tarefa.data_prazo ? new Date(tarefa.data_prazo) : null;
    // Fechamento do cliente naquele mês. `fechamento_cliente` vem como
    // "AAAA-MM-DD" puro: passar por new Date() o interpretaria como UTC e
    // mostraria o dia anterior aqui no fuso de Brasília.
    const fech = tarefa.fechamento_cliente || null;
    const fechBr = fech ? `${fech.slice(8, 10)}/${fech.slice(5, 7)}` : null;
    const venc = (tarefa.data_vencimento || '').slice(0, 10);
    const encerra = fech && venc && fech === venc;
    // Semáforo: verde em dia, amarelo na semana, laranja hoje, vermelho atrasado.
    const alerta = alertaDaTarefa(tarefa);
    const atrasada = alerta.nivel === 'atrasada';
    const st = statusSage[tarefa.status] || statusSage.pendente;
    const pr = prioSage[tarefa.prioridade] || prioSage.media;
    const ativa = tarefa.status !== 'concluida' && tarefa.status !== 'cancelada';
    // O nome vem na própria tarefa. A listagem de setores só traz os ATIVOS, e
    // desativar um setor apagava o badge de todas as tarefas dele — o dado
    // estava no banco, só não chegava na tela. A lista fica como reserva, para
    // registro antigo que ainda não traga o campo.
    const setorAchado = tarefa.setor_nome || (tarefa.setor_id ? getSetorNome(tarefa.setor_id) : null);
    const setorNome = setorAchado && setorAchado !== '-' ? setorAchado : null;
    const corSet = corDoSetor(setorNome);
    const empresaNome = getEmpresaNome(tarefa.empresa_id);
    const entregaCliente = tarefa.sentido === 'entregar';
    return (
      <div key={tarefa.id} className="rounded-lg border p-2 flex flex-col transition-shadow hover:shadow-sm"
        style={{ background: fundoDoAlerta(alerta), borderColor: SAGE.border,
                 borderLeft: `4px solid ${alerta.forte}` }}>
        <div className="flex items-start gap-1 mb-1">
          {atrasada && <AlertTriangle size={12} className="mt-0.5 shrink-0" style={{ color: '#a24a3a' }} />}
          <h3 className="text-[13px] font-medium leading-tight line-clamp-2" style={{ color: SAGE.txt }} title={tarefa.titulo}>
            {tarefa.titulo}
          </h3>
        </div>
        {/* Setor à esquerda, situação e prioridade à direita, na mesma linha.
            Eram três linhas empilhadas -- setor em cima, os dois selos lá
            embaixo -- e o card ficava alto sem precisar. */}
        <div className="flex items-center justify-between gap-1.5 mb-1">
          {setorNome && agrupar !== 'setor' ? (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium truncate"
              style={{ background: corSet + '22', color: corSet }} title={setorNome}>{setorNome}</span>
          ) : <span />}
          <div className="flex items-center gap-1 shrink-0">
            <span className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: st.bg, color: st.fg }}>{statusLabels[tarefa.status]}</span>
            <span className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: pr.bg, color: pr.fg }}>{prioridadeLabels[tarefa.prioridade]}</span>
          </div>
        </div>
        <div className="text-[10px] leading-snug space-y-px mb-1.5" style={{ color: SAGE.txt3 }}>
          {agrupar !== 'empresa' && (
            <p className="truncate" title={empresaNome}>{empresaNome}</p>
          )}
          {/* Responsável e competência dividem a linha. A competência vai
              encostada à direita (ml-auto) para ficar na mesma coluna em todos
              os cards, mesmo quando o nome do responsável varia de tamanho. */}
          {(tarefa.responsaveis?.length > 0 || tarefa.competencia) && (
            <p className="flex items-baseline gap-x-2 min-w-0">
              {tarefa.responsaveis?.length > 0 && (
                <span className="truncate" title={tarefa.responsaveis.map(r => r.nome).join(', ')}>
                  Resp.: {tarefa.responsaveis.map(r => r.nome).join(', ')}
                </span>
              )}
              {tarefa.competencia && (
                <span className="shrink-0 ml-auto tabular-nums" title="Competência do fato gerador">
                  Comp. {tarefa.competencia}
                </span>
              )}
            </p>
          )}
          {/* A data sozinha obriga a pessoa a fazer a conta de cabeça; o card diz
              quantos dias faltam, e a cor repete o recado para quem só bate o olho. */}
          <p className="flex flex-wrap items-center gap-x-1 font-medium" style={{ color: alerta.forte }}>
            <Clock size={10} />
            {prazoDate && format(prazoDate, "dd/MM/yy", { locale: ptBR })}
            <span>{prazoDate ? `· ${alerta.rotulo}` : alerta.rotulo}</span>
            {tarefa.gera_multa && <AlertTriangle size={10} style={{ color: '#a24a3a' }} title="Gera multa" />}
            {tarefa.anexo_nome && (
              <button type="button" onClick={() => abrirAnexo(tarefa)}
                title="Ver o comprovante que baixou esta tarefa"
                className="inline-flex items-center hover:underline" style={{ color: '#2f6fb0' }}>
                <Paperclip size={10} />
              </button>
            )}
          </p>
          {/* Tarefa de ENTREGA: o que importa é se a guia já saiu e se o
              cliente pegou. "Enviado mas não baixado" é a linha que vira
              cobrança no fim do mês. */}
          {entregaCliente && (
            <p className="flex items-center gap-1 font-medium"
               style={{ color: tarefa.saida_downloads ? '#4d8a3f' : (tarefa.saida_nome ? '#8a6a2e' : '#808a74') }}>
              <Send size={10} />
              {tarefa.saida_downloads
                ? `cliente baixou${tarefa.saida_baixada_em ? ' ' + tarefa.saida_baixada_em.slice(8, 10) + '/' + tarefa.saida_baixada_em.slice(5, 7) : ''}`
                : tarefa.saida_nome ? 'guia anexada, não enviada' : 'guia a anexar'}
            </p>
          )}
          {fechBr && (
            encerra ? (
              <p className="flex items-center gap-1 font-medium" style={{ color: '#5f7057' }}
                 title={`Esta tarefa vence no próprio dia do fechamento de ${empresaNome} — é a última do processo.`}>
                <Flag size={10} /> encerra o fechamento
              </p>
            ) : (
              <p className="flex items-center gap-1" style={{ color: '#8a8378' }}
                 title={`${empresaNome} fecha o mês em ${fechBr}. Esta tarefa vem antes.`}>
                <Flag size={10} /> cliente fecha {fechBr}
              </p>
            )
          )}
        </div>
        {/* Rodapé: só o que se usa em série -- mudar a situação -- fica à mostra.
            Copiar link, transferir, editar e excluir eram quatro ícones lado a
            lado no card estreito; viraram um menu, e o select coube num tamanho
            que não disputa mais espaço com eles. */}
        <div className="mt-auto flex items-center gap-1">
          {ativa && entregaCliente ? (
            // Na tarefa de entrega, enviar É a ação principal — deixá-la no
            // menu de três pontos esconderia justamente o que se faz ali.
            <button type="button" onClick={() => abrirEntrega(tarefa)}
              className="flex-1 min-w-0 flex items-center justify-center gap-1 text-[10px] font-medium
                         border rounded px-1 py-0.5 transition-colors"
              style={{ borderColor: '#5f7057', color: '#3f4a3c', background: '#e6eee1' }}>
              <Send size={11} /> Enviar ao cliente
            </button>
          ) : ativa && (
            <select value={tarefa.status} onChange={(e) => handleStatusChange(tarefa, e.target.value)}
              className="w-[6.6rem] text-[10px] border rounded px-1 py-0.5 bg-white"
              style={{ borderColor: SAGE.border, color: '#55614e' }}>
              <option value="pendente">Pendente</option>
              <option value="em_andamento">Em Andamento</option>
              <option value="concluida" disabled={bloqueiaBaixaManual(tarefa)}>
                {bloqueiaBaixaManual(tarefa) ? 'Concluída (só e-validador)' : 'Concluída'}
              </option>
            </select>
          )}
          <div className="relative ml-auto shrink-0" onClick={(e) => e.stopPropagation()}>
            <button type="button" title="Ações"
              onClick={() => setMenuAberto(menuAberto === tarefa.id ? null : tarefa.id)}
              className="p-1 rounded hover:bg-[#e2ebde]" style={{ color: SAGE.txt3 }}>
              <MoreHorizontal size={14} />
            </button>
            {menuAberto === tarefa.id && (
              <div className="absolute right-0 bottom-full mb-1 z-20 rounded-lg border py-1 shadow-lg"
                style={{ background: SAGE.cardBg, borderColor: SAGE.border }}>
                {tarefa.anexo_nome && (
                  <ItemMenu icone={Paperclip} onClick={() => { setMenuAberto(null); abrirAnexo(tarefa); }}>
                    Ver comprovante
                  </ItemMenu>
                )}
                {tarefa.anexo_nome && (
                  <ItemMenu icone={Download} onClick={() => { setMenuAberto(null); abrirAnexo(tarefa, true); }}>
                    Baixar comprovante
                  </ItemMenu>
                )}
                {ativa && (
                  <ItemMenu icone={Send} onClick={() => { setMenuAberto(null); abrirEntrega(tarefa); }}>
                    Enviar documento ao cliente
                  </ItemMenu>
                )}
                {ativa && (
                  <ItemMenu icone={Link2} onClick={() => { setMenuAberto(null); handleCopiarLink(tarefa); }}>
                    Copiar link de envio
                  </ItemMenu>
                )}
                {ativa && (
                  <ItemMenu icone={ArrowRightLeft} onClick={() => { setMenuAberto(null); setShowTransfer(tarefa); setTransferResp(''); }}>
                    Transferir
                  </ItemMenu>
                )}
                <ItemMenu icone={Edit2} onClick={() => { setMenuAberto(null); handleEdit(tarefa); }}>
                  Editar
                </ItemMenu>
                <ItemMenu icone={Trash2} perigo onClick={() => { setMenuAberto(null); handleDelete(tarefa); }}>
                  {tarefa.status === 'cancelada' ? 'Excluir definitivamente' : 'Cancelar tarefa'}
                </ItemMenu>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="flex justify-between items-start gap-4 mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Tarefas</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            As obrigações do mês, por empresa. O prazo mostrado é o interno.
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
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

      {/* Filtros — painel em duas faixas: em cima O QUE se procura, embaixo
          QUANDO vence. Antes era uma fita única de doze controles com rolagem
          lateral: cabia na linha, mas o nome de cada filtro era a opção vazia
          dentro dele ("Todas as empresas") e sumia no instante em que você
          escolhia alguma coisa -- restava um select com uma razão social e
          nenhuma pista do que ele filtrava. Agora o rótulo fica fixo por cima. */}
      <div className="mb-5 rounded-xl border border-gray-200 p-3" style={{ background: '#faf7f0' }}>
        <div className="flex flex-wrap items-end gap-x-3 gap-y-2">
          <Campo rotulo="Tarefa" largura="flex-[2] min-w-[150px]">
            <input
              type="search"
              value={filtros.texto}
              onChange={(e) => setFiltros({ ...filtros, texto: e.target.value })}
              placeholder="parte do nome"
              className={ctrl(filtros.texto)}
            />
          </Campo>
          {[
            { chave: 'empresa_id', rotulo: 'Empresa', vazio: 'Todas', largura: 'flex-[2] min-w-[150px]',
              opcoes: empresas.map((e) => ({ v: e.id, t: formatarRazaoSocial(e.razao_social) })) },
            { chave: 'setor_id', rotulo: 'Setor', vazio: 'Todos', largura: 'flex-1 min-w-[110px]',
              opcoes: setores.map((x) => ({ v: x.id, t: x.nome })) },
            { chave: 'usuario_id', rotulo: 'Colaborador', vazio: 'Todos', largura: 'flex-1 min-w-[130px]',
              dica: 'Responsável ou supervisor da tarefa',
              opcoes: usuarios.filter((u) => !u.bloqueado).map((u) => ({ v: u.id, t: u.nome })) },
            { chave: 'status', rotulo: 'Situação', vazio: 'Todas', largura: 'flex-1 min-w-[110px]',
              opcoes: Object.entries(statusLabels).map(([v, t]) => ({ v, t })) },
          ].map((f) => (
            <Campo key={f.chave} rotulo={f.rotulo} dica={f.dica} largura={f.largura}>
              <select
                value={filtros[f.chave]}
                onChange={(e) => setFiltros({ ...filtros, [f.chave]: e.target.value })}
                className={ctrl(filtros[f.chave])}
              >
                <option value="">{f.vazio}</option>
                {f.opcoes.map((o) => <option key={o.v} value={o.v}>{o.t}</option>)}
              </select>
            </Campo>
          ))}
        </div>

        <div className="mt-2.5 flex flex-wrap items-end gap-x-3 gap-y-2">
          <Campo rotulo="Competência" dica="Mês do fato gerador — MM/AAAA. Não é o vencimento." largura="w-[124px]">
            <select
              value={filtros.competencia}
              onChange={(e) => setFiltros({ ...filtros, competencia: e.target.value })}
              className={ctrl(filtros.competencia)}
            >
              <option value="">Todas</option>
              {competenciasDisponiveis.map((c) => <option key={c} value={c}>{c}</option>)}
              <option value={SEM_COMPETENCIA}>— avulsas</option>
            </select>
          </Campo>
          <Campo rotulo="Vence de" largura="w-[130px]">
            <input
              type="date"
              value={filtros.venc_de}
              onChange={(e) => setFiltros({ ...filtros, venc_de: e.target.value })}
              className={ctrl(filtros.venc_de)}
            />
          </Campo>
          <Campo rotulo="até" largura="w-[130px]">
            <input
              type="date"
              value={filtros.venc_ate}
              onChange={(e) => setFiltros({ ...filtros, venc_ate: e.target.value })}
              className={ctrl(filtros.venc_ate)}
            />
          </Campo>
          <Campo rotulo="Atalhos" largura="shrink-0">
            <div className="flex h-8">
              {presetsVencimento().map((p, i, arr) => (
                <button
                  key={p.rotulo}
                  type="button"
                  onClick={() => aplicarPreset(p)}
                  title={p.titulo}
                  className={`h-8 px-2.5 text-[11px] font-medium border whitespace-nowrap transition
                    ${i === 0 ? 'rounded-l-md' : '-ml-px'} ${i === arr.length - 1 ? 'rounded-r-md' : ''}
                    ${presetAtivo(p)
                      ? 'bg-primary-100 border-primary-400 text-primary-800 relative z-10'
                      : 'bg-white border-gray-300 text-gray-600 hover:border-primary-300'}`}
                >
                  {p.rotulo}
                </button>
              ))}
            </div>
          </Campo>
          <Campo rotulo="Agrupar por" dica="Como a lista se organiza. Fica guardado neste navegador." largura="w-[124px]">
            <select value={agrupar} onChange={(e) => setAgrupar(e.target.value)} className={ctrl(false)}>
              {AGRUPAMENTOS.map((a) => <option key={a.valor} value={a.valor}>{a.rotulo}</option>)}
            </select>
          </Campo>

          <div className="ml-auto flex items-center gap-3 pb-1">
            <span className="text-[11px] text-gray-500 whitespace-nowrap tabular-nums">
              {temFiltro
                ? <><strong className="text-gray-700">{filteredTarefas.length}</strong> de {tarefas.length}</>
                : <>{tarefas.length} {tarefas.length === 1 ? 'tarefa' : 'tarefas'}</>}
            </span>
            {recorte && (
              /* Dizer QUAL recorte veio do Painel. Sem isto, a tela abre com
                 menos tarefas do que a pessoa esperava e parece que sumiram. */
              <span className="text-[11px] px-2 py-0.5 rounded-full whitespace-nowrap"
                style={{ background: '#ede2d1', color: '#55614e' }}>
                mostrando: {recorte}
              </span>
            )}
            {temFiltro && (
              <button
                type="button"
                onClick={() => setFiltros(filtrosVazios())}
                className="text-[11px] text-gray-500 underline hover:text-gray-700 whitespace-nowrap"
              >
                Limpar filtros
              </button>
            )}
          </div>
        </div>
      </div>

      {filteredTarefas.length === 0 ? (
        <div className="card text-center py-12">
          <ListTodo size={48} className="mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500">Nenhuma tarefa encontrada</p>
          {temFiltro && (
            <button type="button" onClick={() => setFiltros(filtrosVazios())}
              className="mt-2 text-xs text-primary-700 underline">
              Limpar os filtros
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {grupos.map((g) => {
            const aberto = !recolhidos.includes(g.chave);
            return (
              <section key={g.chave}>
                {g.titulo && (
                  <button
                    type="button"
                    onClick={() => alternarGrupo(g.chave)}
                    className="w-full flex items-center gap-2 mb-2 py-1 rounded-lg text-left transition-colors hover:bg-[#e4dac6]"
                  >
                    <ChevronDown size={15} className={`shrink-0 transition-transform ${aberto ? '' : '-rotate-90'}`}
                      style={{ color: SAGE.txt3 }} />
                    <h2 className="text-sm font-semibold truncate min-w-0" style={{ color: SAGE.txt }} title={g.titulo}>
                      {g.titulo}
                    </h2>
                    <span className="shrink-0 px-1.5 py-0.5 rounded-full text-[10px] font-medium tabular-nums"
                      style={{ background: '#e2ebde', color: '#566450' }}>
                      {g.tarefas.length}
                    </span>
                    <span className="flex-1 border-b" style={{ borderColor: '#d8ccb4' }} />
                  </button>
                )}
                {aberto && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-2">
                    {g.tarefas.map(cartao)}
                  </div>
                )}
              </section>
            );
          })}
        </div>
      )}

      {/* Entrega ao cliente. Anexar e enviar são dois passos de propósito:
          documento que sai para cliente não volta, e o intervalo entre um e
          outro é onde se confere o arquivo e a lista de quem vai receber. */}
      {entrega && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-gray-200 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">Enviar ao cliente</h2>
                <p className="text-sm text-gray-500 mt-1">
                  {entrega.tarefa.titulo}
                  {entrega.tarefa.competencia && <> · {entrega.tarefa.competencia}</>}
                  <br />{getEmpresaNome(entrega.tarefa.empresa_id)}
                </p>
              </div>
              <button onClick={() => setEntrega(null)} className="text-gray-400 hover:text-gray-700">
                <X size={18} />
              </button>
            </div>

            <div className="p-4 space-y-3">
              {entrega.erro && (
                <div className="px-3 py-2 rounded-lg text-sm bg-red-50 text-red-700">{entrega.erro}</div>
              )}
              {/* Conferência do documento contra a tarefa. Avisa, não bloqueia:
                  guia escaneada não tem texto, e recusar por falta de prova
                  travaria trabalho legítimo. O que não pode é passar em
                  silêncio um documento que diz OUTRO CNPJ. */}
              {entrega.conferencia && !entrega.conferencia.ok && (
                <div className="px-3 py-2 rounded-lg text-sm bg-red-50 text-red-800">
                  <strong>Confira antes de enviar:</strong>
                  <ul className="list-disc ml-4 mt-1">
                    {entrega.conferencia.alertas.map((a, i) => <li key={i}>{a}</li>)}
                  </ul>
                  {entrega.exigeConfirmar && (
                    <p className="mt-2 font-medium">
                      O botão mudou. Confirme só se souber que este documento é o certo —
                      matriz e filial têm CNPJ diferente, por exemplo.
                    </p>
                  )}
                </div>
              )}
              {entrega.conferencia?.ok && entrega.conferencia.leu_algo && (
                <div className="px-3 py-2 rounded-lg text-xs bg-green-50 text-green-800">
                  ✓ O documento confere: CNPJ e competência batem com a tarefa.
                </div>
              )}
              {entrega.conferencia && !entrega.conferencia.leu_algo && (
                <div className="px-3 py-2 rounded-lg text-xs bg-gray-100 text-gray-600">
                  Não consegui ler CNPJ nem competência neste arquivo (escaneado ou sem texto).
                  Confira você antes de enviar.
                </div>
              )}

              {entrega.resultado ? (
                <>
                  <div className={`px-3 py-2 rounded-lg text-sm ${
                    entrega.resultado.concluiu ? 'bg-green-50 text-green-800' : 'bg-amber-50 text-amber-800'}`}>
                    {entrega.resultado.message}
                  </div>
                  <ul className="text-xs space-y-1">
                    {entrega.resultado.resultados.map((r, i) => (
                      <li key={i} className="flex items-center gap-1.5">
                        {r.canal === 'whatsapp'
                          ? <MessageCircle size={12} className="text-green-600" /> : <Mail size={12} className="text-blue-600" />}
                        <span className={r.enviado ? 'text-gray-700' : 'text-red-700 line-through'}>
                          {r.nome} · {r.endereco}
                        </span>
                        {!r.enviado && <span className="text-red-700">falhou</span>}
                      </li>
                    ))}
                  </ul>
                  <button onClick={() => setEntrega(null)} className="btn-secondary w-full">Fechar</button>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Documento</label>
                    {entrega.tarefa.saida_nome || entrega.ensaio?.arquivo ? (
                      <p className="text-sm flex items-center gap-2 text-gray-700">
                        <Paperclip size={14} className="text-primary-700" />
                        {entrega.ensaio?.arquivo || entrega.tarefa.saida_nome}
                        <button type="button" onClick={() => abrirSaida(entrega.tarefa)}
                          className="text-xs text-primary-700 underline">conferir</button>
                      </p>
                    ) : (
                      <p className="text-xs text-gray-500">Nenhum documento anexado ainda.</p>
                    )}
                    <label className="btn-secondary inline-flex items-center gap-2 mt-2 cursor-pointer text-sm">
                      <Upload size={15} />
                      {entrega.ensaio?.arquivo ? 'Trocar documento' : 'Anexar documento'}
                      <input type="file" className="hidden"
                        onChange={(e) => anexarSaida(e.target.files?.[0])} />
                    </label>
                  </div>

                  <div className="border-t border-gray-100 pt-3">
                    <p className="text-sm font-medium text-gray-700 mb-1">Vai para</p>
                    {entrega.ensaio ? (
                      <ul className="text-xs space-y-1">
                        {entrega.ensaio.destinatarios.map((d, i) => (
                          <li key={i} className="flex items-center gap-1.5 text-gray-600">
                            {d.canal === 'whatsapp'
                              ? <MessageCircle size={12} className="text-green-600" /> : <Mail size={12} className="text-blue-600" />}
                            {d.nome} <span className="text-gray-400">{d.endereco}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-gray-500">
                        {entrega.erro ? '—' : 'Carregando…'}
                      </p>
                    )}
                    <p className="text-[11px] text-gray-400 mt-2">
                      Contatos da empresa e usuários do tipo cliente ligados a ela. Enviar conclui a tarefa.
                    </p>
                  </div>

                  <div className="flex gap-3 pt-1">
                    <button type="button" onClick={() => setEntrega(null)} className="btn-secondary flex-1">
                      Cancelar
                    </button>
                    {entrega.exigeConfirmar ? (
                      <button type="button" onClick={() => confirmarEnvio(true)}
                        disabled={entrega.enviando}
                        className="flex-1 flex items-center justify-center gap-2 rounded-lg px-3.5 py-1.5
                                   font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-40">
                        <AlertTriangle size={16} />
                        {entrega.enviando ? 'Enviando…' : 'Enviar mesmo assim'}
                      </button>
                    ) : (
                      <button type="button" onClick={() => confirmarEnvio(false)}
                        disabled={entrega.enviando || !entrega.ensaio?.destinatarios?.length}
                        className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-40">
                        <Send size={16} /> {entrega.enviando ? 'Enviando…' : 'Enviar agora'}
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
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
                    .map((e) => <option key={e.id} value={e.id}>{formatarRazaoSocial(e.razao_social)}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Empresas de destino *</label>
                {(() => {
                  const termo = copyBusca.trim().toLowerCase();
                  const destinos = empresas.filter((e) => String(e.id) !== copyOrigem);
                  const filtradas = termo
                    ? destinos.filter((e) => `${e.razao_social} ${formatarRazaoSocial(e.razao_social)} ${e.grupo || ''}`.toLowerCase().includes(termo))
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
                            {formatarRazaoSocial(e.razao_social)}
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
                      <option key={e.id} value={e.id}>{formatarRazaoSocial(e.razao_social)}</option>
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
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Competência</label>
                <input
                  type="text"
                  value={formData.competencia}
                  onChange={(e) => setFormData({ ...formData, competencia: e.target.value })}
                  className="input-field"
                  placeholder="MM/AAAA"
                  pattern="\\d{2}/\\d{4}"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Mês do fato gerador — julho é <code>07/2026</code>. É por ela que o e-validador
                  encontra a tarefa ao ler o comprovante. Em tarefa gerada por obrigação, vem
                  calculada; em tarefa avulsa, fica em branco.
                </p>
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