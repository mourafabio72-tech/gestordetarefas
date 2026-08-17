import { useState, useEffect } from 'react';
import { obrigacoesAPI, empresasAPI, setoresAPI, usuariosAPI } from '../services/api';
import { Plus, Edit2, Trash2, FileStack, Copy, CopyPlus, Unlink, Info, Upload, CheckCircle2, AlertTriangle, ChevronDown, ChevronRight, Ban, Zap } from 'lucide-react';

const AJUDA_IDENTIFICADORES =
  'Palavra ou expressão ÚNICA que só aparece neste tipo de comprovante (ex.: "EFD-Contribuições", "Sped Fiscal", "DAS-SIMPLES", ou o código de receita). ' +
  'É o que o e-validador procura no PDF para achar e baixar a tarefa. NÃO use o título inteiro do recibo (ele se repete entre tipos e causa "Ambíguo"). ' +
  'Separe por vírgula para aceitar mais de um termo.';

const REGIMES = [
  ['lucro_real', 'Lucro Real'],
  ['lucro_presumido', 'Lucro Presumido'],
  ['simples_nacional', 'Simples Nacional'],
  ['mei', 'MEI'],
  ['terceiro_setor', 'Terceiro Setor'],
  ['imune', 'Imune'],
  ['isento', 'Isento'],
];
const SEGMENTOS = [
  ['comercio', 'Comércio'],
  ['industria', 'Indústria'],
  ['servico', 'Serviço'],
  ['comercio_servico', 'Comércio & Serviço'],
  ['holding', 'Holding'],
  ['imune', 'Imune'],
  ['igreja', 'Igreja'],
];
const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

const emptyForm = {
  nome: '', mininome: '', identificadores: '',
  setor_id: '', responsavel_id: '', supervisor_id: '', tempo_previsto_min: '',
  regra_prazo_tipo: 'ultimo_dia_util', regra_prazo_dia: '',
  meses_ativos: '1,2,3,4,5,6,7,8,9,10,11,12',
  lembrar_dias_antes: 5, tipo_dias: 'corridos', ajuste_nao_util: 'antecipar',
  sabado_util: false, competencia_ref: 'mes_anterior',
  exige_robo: false, exige_documento: null, passivel_multa: false, alerta_guia_nao_lida: false, ativa: true,
  comentario_padrao: '', aplica_regimes: '', aplica_segmentos: '', empresa_ids: [],
};

const csvToSet = (s) => new Set((s || '').split(',').map((x) => x.trim()).filter(Boolean));
const toggleCsv = (csv, val) => {
  const set = csvToSet(csv);
  set.has(val) ? set.delete(val) : set.add(val);
  return [...set].join(',');
};

export default function Obrigacoes() {
  const [obrigacoes, setObrigacoes] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [setores, setSetores] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [buscaEmp, setBuscaEmp] = useState('');
  const [secoes, setSecoes] = useState({ recorrencia: true, publico: false, empresas: false, detalhes: false });
  const toggleSecao = (k) => setSecoes((s) => ({ ...s, [k]: !s[k] }));
  const [detalhes, setDetalhes] = useState([]);   // [{empresa_id, empresa_nome, observacao}]
  const [filtros, setFiltros] = useState({ obrigacao: '', empresa: '', setor: '', status: 'todas' });

  const so = (s) => (s || '').toString().toLowerCase();
  const setorNome = (id) => setores.find((s) => s.id === id)?.nome || '-';
  const obrigacoesFiltradas = obrigacoes.filter((o) => {
    if (filtros.obrigacao && !`${so(o.nome)} ${so(o.mininome)}`.includes(so(filtros.obrigacao))) return false;
    if (filtros.empresa && !(o.empresa_ids || []).includes(parseInt(filtros.empresa))) return false;
    if (filtros.setor && o.setor_id !== parseInt(filtros.setor)) return false;
    if (filtros.status === 'ativa' && !o.ativa) return false;
    if (filtros.status === 'inativa' && o.ativa) return false;
    return true;
  });

  const [selecionados, setSelecionados] = useState([]);
  const toggleSel = (id) => setSelecionados((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);
  const idsFiltrados = obrigacoesFiltradas.map((o) => o.id);
  const todasMarcadas = idsFiltrados.length > 0 && idsFiltrados.every((id) => selecionados.includes(id));
  const toggleTodas = () => setSelecionados(todasMarcadas ? [] : idsFiltrados);
  const excluirSelecionadas = async () => {
    if (!selecionados.length) return;
    if (!confirm(`Excluir DEFINITIVAMENTE ${selecionados.length} obrigação(ões)?\n\nApaga as obrigações e TAMBÉM as tarefas já geradas delas. Não dá para desfazer.`)) return;
    try { await obrigacoesAPI.excluirLote(selecionados, true); setSelecionados([]); loadData(); }
    catch { alert('Erro ao excluir em lote'); }
  };

  const limparTudo = async () => {
    const ids = obrigacoes.map((o) => o.id);
    if (!ids.length) return alert('Não há obrigações para limpar.');
    if (!confirm(`Excluir TODAS as ${ids.length} obrigações e as tarefas geradas delas?\n\nApaga tudo. Não dá para desfazer.`)) return;
    if (!confirm('Tem certeza? Esta ação é definitiva.')) return;
    try { await obrigacoesAPI.excluirLote(ids, true); setSelecionados([]); loadData(); alert(`${ids.length} obrigações excluídas.`); }
    catch { alert('Erro ao limpar'); }
  };
  const [gerando, setGerando] = useState(false);
  const MESES_NOME = ['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
  const gerarTarefas = async () => {
    const hoje = new Date();
    const mes = hoje.getMonth() + 1, ano = hoje.getFullYear();
    if (!confirm(`Gerar as tarefas de ${MESES_NOME[mes - 1]}/${ano} para TODAS as empresas, a partir das obrigações ativas?\n\nNão duplica o que já existe.`)) return;
    setGerando(true);
    try {
      const { data } = await obrigacoesAPI.gerar(mes, ano);
      alert(`Tarefas de ${data.mes_entrega}: ${data.criadas} criada(s), ${data.puladas} já existiam.`);
    } catch (e) {
      alert(e.response?.data?.detail || 'Erro ao gerar tarefas.');
    } finally { setGerando(false); }
  };
  const [showCopy, setShowCopy] = useState(false);
  const [copyOrigem, setCopyOrigem] = useState('');
  const [copyDestino, setCopyDestino] = useState('');
  const [showDesvincular, setShowDesvincular] = useState(false);
  const [desvincEmpresa, setDesvincEmpresa] = useState('');
  const [desvinculando, setDesvinculando] = useState(false);
  const [modelo, setModelo] = useState(null);       // resultado da análise do comprovante
  const [analisando, setAnalisando] = useState(false);

  const analisarModelo = async (file) => {
    if (!file) return;
    setAnalisando(true); setModelo(null);
    try {
      const { data } = await obrigacoesAPI.analisarModelo(file);
      setModelo(data);
    } catch (err) {
      alert(err.response?.data?.detail || 'Não consegui ler o PDF modelo');
    } finally { setAnalisando(false); }
  };

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [o, e, s, u] = await Promise.all([
        obrigacoesAPI.list(), empresasAPI.list(), setoresAPI.list(), usuariosAPI.list(),
      ]);
      setObrigacoes(o.data); setEmpresas(e.data); setSetores(s.data); setUsuarios(u.data);
    } catch (err) {
      console.error('Erro ao carregar:', err);
    } finally { setLoading(false); }
  };

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const abrirNovo = () => { setEditing(null); setForm(emptyForm); setModelo(null); setDetalhes([]); setShowModal(true); };
  const abrirEdicao = (o) => {
    setEditing(o);
    setForm({
      ...emptyForm, ...o,
      setor_id: o.setor_id || '', responsavel_id: o.responsavel_id || '',
      tempo_previsto_min: o.tempo_previsto_min ?? '', regra_prazo_dia: o.regra_prazo_dia ?? '',
      aplica_regimes: o.aplica_regimes || '', aplica_segmentos: o.aplica_segmentos || '',
      empresa_ids: o.empresa_ids || [],
    });
    setModelo(null);
    setDetalhes([]);
    obrigacoesAPI.getDetalhes(o.id).then((r) => setDetalhes(r.data)).catch(() => {});
    setShowModal(true);
  };
  const duplicar = (o) => {
    setEditing(null);   // cria uma NOVA (POST), não edita a original
    setForm({
      ...emptyForm, ...o,
      nome: `${o.nome} (cópia)`,
      setor_id: o.setor_id || '', responsavel_id: o.responsavel_id || '',
      supervisor_id: o.supervisor_id || '',
      tempo_previsto_min: o.tempo_previsto_min ?? '', regra_prazo_dia: o.regra_prazo_dia ?? '',
      aplica_regimes: o.aplica_regimes || '', aplica_segmentos: o.aplica_segmentos || '',
      empresa_ids: o.empresa_ids || [],
    });
    setModelo(null);
    setDetalhes([]);
    obrigacoesAPI.getDetalhes(o.id).then((r) => setDetalhes(r.data)).catch(() => {});
    setShowModal(true);
  };

  const salvar = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...form,
        setor_id: form.setor_id ? parseInt(form.setor_id) : null,
        responsavel_id: form.responsavel_id ? parseInt(form.responsavel_id) : null,
        supervisor_id: form.supervisor_id ? parseInt(form.supervisor_id) : null,
        tempo_previsto_min: form.tempo_previsto_min ? parseInt(form.tempo_previsto_min) : null,
        regra_prazo_dia: form.regra_prazo_tipo === 'dia_fixo' && form.regra_prazo_dia
          ? parseInt(form.regra_prazo_dia) : null,
        lembrar_dias_antes: parseInt(form.lembrar_dias_antes) || 0,
      };
      let obrigId;
      if (editing) { await obrigacoesAPI.update(editing.id, payload); obrigId = editing.id; }
      else { const r = await obrigacoesAPI.create(payload); obrigId = r.data.id; }
      // Detalhes fixos por empresa
      await obrigacoesAPI.setDetalhes(obrigId, detalhes.map((d) => ({ empresa_id: d.empresa_id, observacao: d.observacao })));
      setShowModal(false); loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao salvar obrigação');
    }
  };

  const excluir = async (o) => {
    if (!confirm(`Excluir DEFINITIVAMENTE a obrigação "${o.nome}"?\n\nApaga a obrigação e TAMBÉM as tarefas já geradas dela. Não dá para desfazer.`)) return;
    try { await obrigacoesAPI.delete(o.id, true); loadData(); }
    catch { alert('Erro ao excluir'); }
  };

  const alternarStatus = async (o) => {
    try { await obrigacoesAPI.setAtiva(o.id, !o.ativa); loadData(); }
    catch { alert('Erro ao mudar o status'); }
  };

  const copiar = async () => {
    if (!copyOrigem || !copyDestino) return;
    try {
      const r = await obrigacoesAPI.copiarEmpresa(parseInt(copyOrigem), parseInt(copyDestino));
      alert(r.data?.message || 'Copiado.');
      setShowCopy(false); setCopyOrigem(''); setCopyDestino(''); loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao copiar');
    }
  };

  const desvincularEmpresa = async () => {
    if (!desvincEmpresa) return;
    const eid = parseInt(desvincEmpresa);
    const nome = empresas.find((e) => e.id === eid)?.razao_social || `#${eid}`;
    const qtd = obrigacoes.filter((o) => (o.empresa_ids || []).includes(eid)).length;
    if (!qtd) return alert(`"${nome}" não está vinculada a nenhuma obrigação.`);
    if (!confirm(`Desvincular "${nome}" de ${qtd} obrigação(ões)?\n\nRemove só o vínculo: não apaga a obrigação nem a empresa, e não mexe nas tarefas já geradas.`)) return;
    setDesvinculando(true);
    try {
      const r = await obrigacoesAPI.desvincularEmpresa(eid);
      alert(r.data?.desvinculadas != null ? `${r.data.desvinculadas} obrigação(ões) desvinculada(s) de "${nome}".` : 'Desvinculado.');
      setShowDesvincular(false); setDesvincEmpresa(''); loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao desvincular');
    } finally { setDesvinculando(false); }
  };

  const nomeEmpresa = (id) => empresas.find((e) => e.id === id)?.razao_social || `#${id}`;

  if (loading) return <div className="flex items-center justify-center h-64">Carregando...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Obrigações</h1>
        <div className="flex gap-2">
          {selecionados.length > 0 && (
            <button onClick={excluirSelecionadas} className="btn-danger flex items-center gap-2">
              <Trash2 size={18} /> Excluir {selecionados.length}
            </button>
          )}
          <button onClick={limparTudo} className="text-sm text-red-600 hover:underline self-center px-2" title="Excluir todas as obrigações">
            Limpar todas
          </button>
          <button onClick={() => setShowCopy(true)} className="btn-secondary flex items-center gap-2">
            <Copy size={18} /> Copiar de outra empresa
          </button>
          <button onClick={() => setShowDesvincular(true)} className="btn-secondary flex items-center gap-2 text-red-600"
            title="Remove o vínculo de uma empresa das obrigações (não apaga nada além do vínculo)">
            <Unlink size={18} /> Desvincular empresa
          </button>
          <button onClick={gerarTarefas} disabled={gerando} className="btn-secondary flex items-center gap-2"
            title="Cria as tarefas do mês atual para todas as empresas, a partir das obrigações ativas">
            <Zap size={18} /> {gerando ? 'Gerando…' : 'Gerar tarefas do mês'}
          </button>
          <button onClick={abrirNovo} className="btn-primary flex items-center gap-2">
            <Plus size={18} /> Nova Obrigação
          </button>
        </div>
      </div>

      <div className="card mb-4 p-2">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <input className="input-field py-1.5 text-sm" placeholder="Obrigação (nome)"
            value={filtros.obrigacao} onChange={(e) => setFiltros({ ...filtros, obrigacao: e.target.value })} />
          <select className="input-field py-1.5 text-sm" value={filtros.empresa} onChange={(e) => setFiltros({ ...filtros, empresa: e.target.value })}>
            <option value="">Todas as empresas</option>
            {empresas.map((e) => <option key={e.id} value={e.id}>{e.razao_social}</option>)}
          </select>
          <select className="input-field py-1.5 text-sm" value={filtros.setor} onChange={(e) => setFiltros({ ...filtros, setor: e.target.value })}>
            <option value="">Todos os setores</option>
            {setores.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
          </select>
          <select className="input-field py-1.5 text-sm" value={filtros.status} onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}>
            <option value="todas">Todos os status</option>
            <option value="ativa">Ativas</option>
            <option value="inativa">Inativas</option>
          </select>
        </div>
      </div>

      <div className="card">
        {obrigacoesFiltradas.length === 0 ? (
          <div className="text-center py-12">
            <FileStack size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">{obrigacoes.length === 0 ? 'Nenhuma obrigação cadastrada' : 'Nenhuma obrigação com esses filtros'}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-gray-500">
                  <th className="py-2 px-2 w-8">
                    <input type="checkbox" className="h-4 w-4" checked={todasMarcadas} onChange={toggleTodas} title="Marcar todas (filtradas)" />
                  </th>
                  <th className="text-left py-2 px-2 font-medium">Obrigação</th>
                  <th className="text-left py-2 px-2 font-medium w-32">Setor</th>
                  <th className="text-left py-2 px-2 font-medium w-20">Empresas</th>
                  <th className="text-left py-2 px-2 font-medium w-20">Status</th>
                  <th className="text-right py-2 px-2 font-medium w-28">Ações</th>
                </tr>
              </thead>
              <tbody>
                {obrigacoesFiltradas.map((o) => (
                  <tr key={o.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-1.5 px-2">
                      <input type="checkbox" className="h-4 w-4" checked={selecionados.includes(o.id)} onChange={() => toggleSel(o.id)} />
                    </td>
                    <td className="py-1.5 px-2 font-medium text-gray-800">{o.nome}</td>
                    <td className="py-1.5 px-2 text-gray-600">{setorNome(o.setor_id)}</td>
                    <td className="py-1.5 px-2 text-gray-500">{(o.empresa_ids || []).length}</td>
                    <td className="py-1.5 px-2">
                      <span className={`px-2 py-0.5 text-xs rounded-full ${o.ativa ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {o.ativa ? 'Ativa' : 'Inativa'}
                      </span>
                    </td>
                    <td className="py-1.5 px-2">
                      <div className="flex justify-end gap-1">
                        <button onClick={() => abrirEdicao(o)} title="Editar" className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg">
                          <Edit2 size={15} />
                        </button>
                        <button onClick={() => duplicar(o)} title="Duplicar (criar nova a partir desta)" className="p-1.5 text-primary-600 hover:bg-primary-50 rounded-lg">
                          <CopyPlus size={15} />
                        </button>
                        <button onClick={() => alternarStatus(o)} title={o.ativa ? 'Inativar' : 'Ativar'}
                          className={`p-1.5 rounded-lg ${o.ativa ? 'text-amber-600 hover:bg-amber-50' : 'text-green-600 hover:bg-green-50'}`}>
                          {o.ativa ? <Ban size={15} /> : <CheckCircle2 size={15} />}
                        </button>
                        <button onClick={() => excluir(o)} title="Excluir definitivamente" className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg">
                          <Trash2 size={15} />
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

      {showDesvincular && (() => {
        const eid = parseInt(desvincEmpresa) || 0;
        const qtd = eid ? obrigacoes.filter((o) => (o.empresa_ids || []).includes(eid)).length : 0;
        return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-md">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Desvincular empresa das obrigações</h2>
              <p className="text-sm text-gray-500 mt-1">
                Remove o vínculo da empresa em <strong>todas</strong> as obrigações. Não apaga a
                obrigação nem a empresa, e não mexe nas tarefas já geradas.
              </p>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Empresa *</label>
                <select value={desvincEmpresa} onChange={(e) => setDesvincEmpresa(e.target.value)} className="input-field">
                  <option value="">Selecione</option>
                  {empresas.map((e) => <option key={e.id} value={e.id}>{e.razao_social}</option>)}
                </select>
                {eid > 0 && (
                  <p className="text-xs text-gray-500 mt-1">Vinculada a <strong>{qtd}</strong> obrigação(ões).</p>
                )}
              </div>
              <div className="flex gap-3 pt-2">
                <button onClick={() => { setShowDesvincular(false); setDesvincEmpresa(''); }} className="btn-secondary flex-1">Cancelar</button>
                <button onClick={desvincularEmpresa} disabled={!desvincEmpresa || !qtd || desvinculando} className="btn-danger flex-1">
                  {desvinculando ? 'Desvinculando…' : 'Desvincular'}
                </button>
              </div>
            </div>
          </div>
        </div>
        );
      })()}

      {showCopy && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Copiar obrigações de outra empresa</h2>
              <p className="text-sm text-gray-500 mt-1">
                Vincula a empresa destino a todas as obrigações que a empresa origem já tem.
              </p>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Empresa de origem *</label>
                <select value={copyOrigem} onChange={(e) => setCopyOrigem(e.target.value)} className="input-field">
                  <option value="">Selecione</option>
                  {empresas.map((e) => <option key={e.id} value={e.id}>{e.razao_social}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Empresa de destino *</label>
                <select value={copyDestino} onChange={(e) => setCopyDestino(e.target.value)} className="input-field">
                  <option value="">Selecione</option>
                  {empresas.filter((e) => String(e.id) !== copyOrigem).map((e) => (
                    <option key={e.id} value={e.id}>{e.razao_social}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3 pt-2">
                <button onClick={() => setShowCopy(false)} className="btn-secondary flex-1">Cancelar</button>
                <button onClick={copiar} disabled={!copyOrigem || !copyDestino} className="btn-primary flex-1">Copiar</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-xl w-full max-w-2xl my-8 max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">{editing ? 'Editar Obrigação' : 'Nova Obrigação'}</h2>
            </div>
            <form onSubmit={salvar} className="p-4 space-y-3">
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nome da obrigação *</label>
                  <input value={form.nome} onChange={(e) => set('nome', e.target.value)} className="input-field" required />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Mininome</label>
                  <input value={form.mininome} onChange={(e) => set('mininome', e.target.value)} className="input-field" placeholder="DARF 0220" />
                </div>
              </div>
              <div>
                <label className="flex items-center gap-1 text-sm font-medium text-gray-700 mb-1">
                  Identificadores (e-validador)
                  <span title={AJUDA_IDENTIFICADORES} className="text-gray-400 cursor-help">
                    <Info size={14} />
                  </span>
                </label>
                <input value={form.identificadores} onChange={(e) => set('identificadores', e.target.value)} className="input-field" placeholder="Ex.: EFD-Contribuições, 0220  (separados por vírgula)" />
                <p className="text-xs text-gray-400 mt-1">Palavra única que o e-validador procura no comprovante. Passe o mouse no ⓘ para a regra.</p>

                {/* Subir modelo -> sugerir identificador */}
                <div className="mt-2 border border-dashed border-gray-300 rounded-lg p-3 bg-gray-50/50">
                  <label className="flex items-center gap-2 text-sm text-primary-700 cursor-pointer w-fit">
                    <Upload size={15} />
                    {analisando ? 'Lendo o modelo...' : 'Subir modelo de comprovante (PDF) e sugerir'}
                    <input type="file" accept="application/pdf" className="hidden"
                      onChange={(e) => analisarModelo(e.target.files?.[0])} />
                  </label>

                  {modelo && (
                    <div className="mt-3 text-sm">
                      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2 text-xs">
                        <span className={modelo.cnpj ? 'text-green-700' : 'text-red-600'}>
                          {modelo.cnpj ? `✓ CNPJ ${modelo.cnpj}` : '✗ CNPJ não encontrado'}
                        </span>
                        <span className={modelo.competencia ? 'text-green-700' : 'text-red-600'}>
                          {modelo.competencia ? `✓ Competência ${modelo.competencia}` : '✗ Competência não encontrada'}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mb-1">Sugestões de identificador (clique para usar):</p>
                      <div className="space-y-1">
                        {modelo.candidatos.map((cnd, i) => (
                          <button type="button" key={i} onClick={() => set('identificadores', cnd.texto)}
                            className="w-full text-left flex items-center justify-between gap-2 px-2 py-1 rounded border border-gray-200 hover:bg-primary-50">
                            <span className="truncate">{cnd.texto}</span>
                            {cnd.colide_com.length > 0 ? (
                              <span className="flex items-center gap-1 text-amber-600 text-xs whitespace-nowrap">
                                <AlertTriangle size={12} /> colide: {cnd.colide_com.join(', ')}
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 text-green-600 text-xs whitespace-nowrap">
                                <CheckCircle2 size={12} /> livre
                              </span>
                            )}
                          </button>
                        ))}
                      </div>
                      <p className="text-xs text-gray-400 mt-1">Prefira uma opção "livre" e curta. "Colide" = já usada em outra obrigação (daria Ambíguo).</p>
                    </div>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Setor</label>
                  <select value={form.setor_id} onChange={(e) => set('setor_id', e.target.value)} className="input-field">
                    <option value="">-</option>
                    {setores.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Responsável padrão</label>
                  <select value={form.responsavel_id} onChange={(e) => set('responsavel_id', e.target.value)} className="input-field">
                    <option value="">-</option>
                    {usuarios.filter((u) => u.tipo !== 'cliente' && !u.bloqueado).map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Supervisor padrão</label>
                  <select value={form.supervisor_id} onChange={(e) => set('supervisor_id', e.target.value)} className="input-field">
                    <option value="">-</option>
                    {usuarios.filter((u) => u.tipo !== 'cliente' && !u.bloqueado).map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tempo previsto (min)</label>
                  <input type="number" value={form.tempo_previsto_min} onChange={(e) => set('tempo_previsto_min', e.target.value)} className="input-field" />
                </div>
              </div>

              <div className="border-t border-gray-100 pt-3">
                <button type="button" onClick={() => toggleSecao('recorrencia')} className="w-full flex items-center gap-1.5 text-sm font-semibold text-gray-700 mb-2">
                  {secoes.recorrencia ? <ChevronDown size={15} /> : <ChevronRight size={15} />} Recorrência e prazo
                </button>
                {secoes.recorrencia && (<div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Regra de prazo</label>
                    <select value={form.regra_prazo_tipo} onChange={(e) => set('regra_prazo_tipo', e.target.value)} className="input-field">
                      <option value="ultimo_dia_util">Último dia útil</option>
                      <option value="primeiro_dia_util">Primeiro dia útil</option>
                      <option value="dia_fixo">Dia fixo</option>
                    </select>
                  </div>
                  {form.regra_prazo_tipo === 'dia_fixo' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Dia do mês</label>
                      <input type="number" min="1" max="31" value={form.regra_prazo_dia} onChange={(e) => set('regra_prazo_dia', e.target.value)} className="input-field" placeholder="20" />
                    </div>
                  )}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Competência referente a</label>
                    <select value={form.competencia_ref} onChange={(e) => set('competencia_ref', e.target.value)} className="input-field">
                      <option value="mes_anterior">Mês anterior</option>
                      <option value="mesmo_mes">Mesmo mês</option>
                      <option value="mes_seguinte">Mês seguinte</option>
                      <option value="ano_anterior">Ano anterior</option>
                    </select>
                  </div>
                </div>
                <div className="mt-3">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Meses ativos</label>
                  <div className="flex flex-wrap gap-2">
                    {MESES.map((m, i) => {
                      const num = String(i + 1);
                      const on = csvToSet(form.meses_ativos).has(num);
                      return (
                        <button type="button" key={num}
                          onClick={() => set('meses_ativos', toggleCsv(form.meses_ativos, num))}
                          className={`px-2 py-1 rounded text-xs border ${on ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-600 border-gray-300'}`}>
                          {m}
                        </button>
                      );
                    })}
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-4 mt-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Lembrar (dias antes)</label>
                    <input type="number" value={form.lembrar_dias_antes} onChange={(e) => set('lembrar_dias_antes', e.target.value)} className="input-field" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Tipo dos dias</label>
                    <select value={form.tipo_dias} onChange={(e) => set('tipo_dias', e.target.value)} className="input-field">
                      <option value="corridos">Corridos</option>
                      <option value="uteis">Úteis</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Dia não-útil</label>
                    <select value={form.ajuste_nao_util} onChange={(e) => set('ajuste_nao_util', e.target.value)} className="input-field">
                      <option value="antecipar">Antecipar</option>
                      <option value="postergar">Postergar</option>
                      <option value="nenhum">Nenhum</option>
                    </select>
                  </div>
                  <div className="flex items-end pb-2">
                    <label className="flex items-center gap-2 text-sm text-gray-700">
                      <input type="checkbox" checked={form.sabado_util} onChange={(e) => set('sabado_util', e.target.checked)} className="h-4 w-4" />
                      Sábado é útil
                    </label>
                  </div>
                </div>
                </div>)}
              </div>

              <div className="border-t border-gray-100 pt-3">
                <button type="button" onClick={() => toggleSecao('publico')} className="w-full flex items-center gap-1.5 text-sm font-semibold text-gray-700 mb-2">
                  {secoes.publico ? <ChevronDown size={15} /> : <ChevronRight size={15} />} Dados empresariais
                </button>
                {secoes.publico && (() => {
                  const aplicaTodas = !form.aplica_regimes && !form.aplica_segmentos;
                  return (
                <div className="space-y-3">
                  <label className="flex items-center gap-2 text-sm cursor-pointer bg-gray-50 rounded px-3 py-2">
                    <input type="checkbox" checked={aplicaTodas} className="h-4 w-4"
                      onChange={(e) => { if (e.target.checked) { set('aplica_regimes', ''); set('aplica_segmentos', ''); } else { set('aplica_regimes', REGIMES[0][0]); } }} />
                    <span className="font-medium text-gray-700">Aplicar a todas as empresas</span>
                    <span className="text-gray-400 text-xs">(desmarque para restringir por regime/segmento)</span>
                  </label>
                  {!aplicaTodas && (
                  <div className="grid grid-cols-2 gap-6">
                  <div>
                    <p className="text-sm text-gray-600 mb-2">Regimes <span className="text-gray-400">(vazio = todos)</span></p>
                    <div className="space-y-1">
                      {REGIMES.map(([v, l]) => (
                        <label key={v} className="flex items-center gap-2 text-sm cursor-pointer">
                          <input type="checkbox" checked={csvToSet(form.aplica_regimes).has(v)} onChange={() => set('aplica_regimes', toggleCsv(form.aplica_regimes, v))} className="h-4 w-4" />
                          {l}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-2">Segmentos <span className="text-gray-400">(vazio = todos)</span></p>
                    <div className="space-y-1">
                      {SEGMENTOS.map(([v, l]) => (
                        <label key={v} className="flex items-center gap-2 text-sm cursor-pointer">
                          <input type="checkbox" checked={csvToSet(form.aplica_segmentos).has(v)} onChange={() => set('aplica_segmentos', toggleCsv(form.aplica_segmentos, v))} className="h-4 w-4" />
                          {l}
                        </label>
                      ))}
                    </div>
                  </div>
                  </div>
                  )}
                </div>
                  );
                })()}
              </div>

              <div className="border-t border-gray-100 pt-3">
                <button type="button" onClick={() => toggleSecao('detalhes')} className="w-full flex items-center gap-1.5 text-sm font-semibold text-gray-700 mb-1">
                  {secoes.detalhes ? <ChevronDown size={15} /> : <ChevronRight size={15} />} Detalhe por empresa <span className="text-gray-400 font-normal ml-1">(complemento fixo, ex.: banco do empréstimo)</span>
                </button>
                {secoes.detalhes && (
                  <div className="space-y-2">
                    {detalhes.map((d, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span className="text-sm text-gray-600 w-40 shrink-0 pt-1 truncate" title={d.empresa_nome}>{d.empresa_nome}</span>
                        <input value={d.observacao}
                          onChange={(e) => setDetalhes((arr) => arr.map((x, j) => j === i ? { ...x, observacao: e.target.value } : x))}
                          className="input-field py-1 text-sm flex-1" placeholder="Ex.: Empréstimo do Banco Itaú, conta 123" />
                        <button type="button" onClick={() => setDetalhes((arr) => arr.filter((_, j) => j !== i))}
                          className="text-gray-400 hover:text-red-600 pt-1">×</button>
                      </div>
                    ))}
                    <select value=""
                      onChange={(e) => {
                        const id = parseInt(e.target.value); e.target.value = '';
                        if (!id) return;
                        const emp = empresas.find((x) => x.id === id);
                        if (emp && !detalhes.some((d) => d.empresa_id === id))
                          setDetalhes([...detalhes, { empresa_id: id, empresa_nome: emp.razao_social, observacao: '' }]);
                      }}
                      className="input-field py-1 text-sm">
                      <option value="">+ adicionar empresa…</option>
                      {empresas.filter((e) => !detalhes.some((d) => d.empresa_id === e.id))
                        .map((e) => <option key={e.id} value={e.id}>{e.razao_social}</option>)}
                    </select>
                    <p className="text-xs text-gray-500">O texto entra na descrição de toda tarefa gerada dessa obrigação para a empresa.</p>
                  </div>
                )}
              </div>

              <div className="border-t border-gray-100 pt-3">
                <button type="button" onClick={() => toggleSecao('empresas')} className="w-full flex items-center gap-1.5 text-sm font-semibold text-gray-700 mb-1">
                  {secoes.empresas ? <ChevronDown size={15} /> : <ChevronRight size={15} />} Empresas vinculadas <span className="text-gray-400 font-normal ml-1">(exceções/inclusões diretas)</span>
                </button>
                {secoes.empresas && (() => {
                  const termo = buscaEmp.trim().toLowerCase();
                  const filtradas = termo
                    ? empresas.filter((e) => `${e.razao_social} ${e.grupo || ''}`.toLowerCase().includes(termo))
                    : empresas;
                  const idsFiltrados = filtradas.map((e) => e.id);
                  const marcarTodas = () => set('empresa_ids', [...new Set([...form.empresa_ids, ...idsFiltrados])]);
                  return (
                    <>
                      <div className="flex items-center gap-2 mb-2">
                        <p className="text-xs text-gray-400 flex-1">{form.empresa_ids.length} selecionada(s)</p>
                        <button type="button" onClick={marcarTodas}
                          className="text-xs text-primary-600 hover:underline">
                          {termo ? 'Selecionar filtradas' : 'Selecionar todas'}
                        </button>
                        <span className="text-gray-300">·</span>
                        <button type="button" onClick={() => set('empresa_ids', [])}
                          className="text-xs text-gray-500 hover:underline">Limpar</button>
                      </div>
                      <input type="text" value={buscaEmp} onChange={(e) => setBuscaEmp(e.target.value)}
                        placeholder="Buscar empresa ou grupo…" className="input-field mb-2 text-sm" />
                      <div className="max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-3 space-y-1">
                        {filtradas.length === 0 ? (
                          <p className="text-xs text-gray-400">Nenhuma empresa encontrada.</p>
                        ) : filtradas.map((e) => (
                          <label key={e.id} className="flex items-center gap-2 text-sm cursor-pointer">
                            <input type="checkbox"
                              checked={form.empresa_ids.includes(e.id)}
                              onChange={() => set('empresa_ids', form.empresa_ids.includes(e.id)
                                ? form.empresa_ids.filter((x) => x !== e.id)
                                : [...form.empresa_ids, e.id])}
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

              <div className="border-t border-gray-100 pt-4 flex flex-wrap gap-4">
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" checked={form.passivel_multa} onChange={(e) => set('passivel_multa', e.target.checked)} className="h-4 w-4" /> Passível de multa
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" checked={form.exige_robo} onChange={(e) => set('exige_robo', e.target.checked)} className="h-4 w-4" /> Exige robô
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700"
                  title="Ligado: a baixa só acontece pelo e-validador (documento). Desligado: pode baixar manual.">
                  <input type="checkbox"
                    checked={form.exige_documento ?? !!(form.identificadores || '').trim()}
                    onChange={(e) => set('exige_documento', e.target.checked)} className="h-4 w-4" /> Exige documento (baixa só pelo e-validador)
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" checked={form.alerta_guia_nao_lida} onChange={(e) => set('alerta_guia_nao_lida', e.target.checked)} className="h-4 w-4" /> Alerta guia não-lida
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" checked={form.ativa} onChange={(e) => set('ativa', e.target.checked)} className="h-4 w-4" /> Ativa
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Comentário padrão</label>
                <textarea value={form.comentario_padrao} onChange={(e) => set('comentario_padrao', e.target.value)} className="input-field" rows={2} />
              </div>

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancelar</button>
                <button type="submit" className="btn-primary flex-1">{editing ? 'Salvar' : 'Cadastrar'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
