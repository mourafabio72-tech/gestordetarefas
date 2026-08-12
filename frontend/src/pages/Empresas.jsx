import { useState, useEffect } from 'react';
import { empresasAPI, usuariosAPI, setoresAPI } from '../services/api';
import { Plus, Edit2, Trash2, Building2, Lock, Unlock, Upload, Download, X } from 'lucide-react';

const EMPRESA_VAZIA = {
  razao_social: '', cnpj: '', nome_fantasia: '', email: '', telefone: '',
  endereco: '', regime_tributario: 'indefinido', segmento: '', grupo: '',
  ativo: true, responsavel_id: '', supervisor_id: '',
};

const REGIMES = [
  { value: 'indefinido', label: 'Indefinido' },
  { value: 'lucro_real', label: 'Lucro Real' },
  { value: 'lucro_presumido', label: 'Lucro Presumido' },
  { value: 'mei', label: 'MEI' },
  { value: 'simples_nacional', label: 'Simples Nacional' },
  { value: 'terceiro_setor', label: 'Terceiro Setor' },
  { value: 'imune', label: 'Imune' },
  { value: 'isento', label: 'Isento' },
];

const SEGMENTOS = [
  { value: '', label: '—' },
  { value: 'comercio', label: 'Comércio' },
  { value: 'servico', label: 'Serviço' },
  { value: 'comercio_servico', label: 'Comércio & Serviço' },
  { value: 'industria', label: 'Indústria' },
  { value: 'holding', label: 'Holding' },
  { value: 'imune', label: 'Imune' },
  { value: 'igreja', label: 'Igreja' },
];

const labelDe = (lista, val) => lista.find((o) => o.value === val)?.label || '-';

export default function Empresas() {
  const [empresas, setEmpresas] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [setores, setSetores] = useState([]);
  const [respSetor, setRespSetor] = useState([]);   // [{setor_id, setor_nome, responsavel_id}]
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingEmpresa, setEditingEmpresa] = useState(null);
  const [formData, setFormData] = useState(EMPRESA_VAZIA);
  const [importResult, setImportResult] = useState(null);
  const [importing, setImporting] = useState(false);
  const [filtros, setFiltros] = useState({ razao: '', cnpj: '', regime: '', grupo: '', situacao: 'ativa' });

  const so = (s) => (s || '').toString().toLowerCase();
  const empresasFiltradas = empresas.filter((e) => {
    if (filtros.razao && !so(e.razao_social).includes(so(filtros.razao))) return false;
    if (filtros.cnpj && !(e.cnpj || '').replace(/\D/g, '').includes(filtros.cnpj.replace(/\D/g, ''))) return false;
    if (filtros.regime && e.regime_tributario !== filtros.regime) return false;
    if (filtros.grupo && !so(e.grupo).includes(so(filtros.grupo))) return false;
    if (filtros.situacao === 'ativa' && e.ativo === false) return false;
    if (filtros.situacao === 'inativa' && e.ativo !== false) return false;
    return true;
  });

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';  // permite reimportar o mesmo arquivo
    if (!file) return;
    setImporting(true); setImportResult(null);
    try {
      const { data } = await empresasAPI.importar(file);
      setImportResult(data);
      loadEmpresas();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao importar a planilha.');
    } finally {
      setImporting(false);
    }
  };

  const [importandoResp, setImportandoResp] = useState(false);
  const handleImportResp = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setImportandoResp(true);
    try {
      const { data } = await empresasAPI.importarResponsaveis(file);
      if (data.erro) { alert(data.erro); return; }
      const r = data.resumo || {};
      let msg = `${r.empresas} empresa(s): ${r.marcados} setor(es) marcado(s), ${r.desmarcados} desmarcado(s), ${r.erros} erro(s).`;
      const avisos = (data.detalhes || []).filter((d) => d.status !== 'ok');
      if (avisos.length) msg += `\n\n` + avisos.slice(0, 30).map((d) => `• ${d.linha}: ${d.detalhe}`).join('\n');
      alert(msg);
      loadEmpresas();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao importar responsáveis.');
    } finally {
      setImportandoResp(false);
    }
  };

  useEffect(() => {
    loadEmpresas();
  }, []);

  const loadEmpresas = async () => {
    try {
      const [emp, us, st] = await Promise.all([empresasAPI.list(true), usuariosAPI.list(), setoresAPI.list()]);
      setEmpresas(emp.data);
      setUsuarios(us.data);
      setSetores(st.data);
    } catch (error) {
      console.error('Erro ao carregar empresas:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        responsavel_id: formData.responsavel_id ? parseInt(formData.responsavel_id) : null,
        supervisor_id: formData.supervisor_id ? parseInt(formData.supervisor_id) : null,
      };
      let empresaId;
      if (editingEmpresa) {
        await empresasAPI.update(editingEmpresa.id, payload);
        empresaId = editingEmpresa.id;
      } else {
        const resp = await empresasAPI.create(payload);
        empresaId = resp.data.id;
        const n = parseInt(resp?.headers?.['x-tarefas-geradas'] || '0', 10);
        if (n > 0) alert(`Empresa cadastrada. ${n} tarefa(s) do mês gerada(s) automaticamente pelas obrigações que se aplicam.`);
      }
      // Grava a matriz — só os setores que a empresa ATENDE
      const itens = respSetor.filter((r) => r.atende).map((r) => ({
        setor_id: r.setor_id,
        responsavel_id: r.responsavel_id ? parseInt(r.responsavel_id) : null,
      }));
      await empresasAPI.setResponsaveisSetor(empresaId, itens);
      setShowModal(false);
      setEditingEmpresa(null);
      setFormData(EMPRESA_VAZIA);
      loadEmpresas();
    } catch (error) {
      console.error('Erro empresa:', error.response?.data || error.message);
      alert(error.response?.data?.detail || error.response?.data?.message || JSON.stringify(error.response?.data) || 'Erro ao salvar empresa');
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
      endereco: empresa.endereco || '',
      regime_tributario: empresa.regime_tributario || 'indefinido',
      segmento: empresa.segmento || '',
      grupo: empresa.grupo || '',
      ativo: empresa.ativo !== false,
      responsavel_id: empresa.responsavel_id || '',
      supervisor_id: empresa.supervisor_id || '',
    });
    setRespSetor(setores.map((s) => ({ setor_id: s.id, setor_nome: s.nome, atende: true, responsavel_id: '' })));
    empresasAPI.getResponsaveisSetor(empresa.id)
      .then((r) => setRespSetor(r.data.map((x) => ({ ...x, atende: x.atende !== false, responsavel_id: x.responsavel_id || '' }))))
      .catch(() => {});
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

  const handleBloquear = async (empresa) => {
    const nova = !empresa.bloqueado;
    const msg = nova
      ? 'Bloquear esta empresa? As tarefas/demandas dela vão sumir das listas e o gerador vai ignorá-la.'
      : 'Desbloquear esta empresa? As tarefas dela voltam a aparecer.';
    if (!confirm(msg)) return;
    try {
      await empresasAPI.bloquear(empresa.id, nova);
      loadEmpresas();
    } catch (error) {
      alert('Erro ao bloquear empresa');
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
        <div className="flex items-center gap-2">
          <button onClick={() => empresasAPI.baixarModelo()} className="btn-secondary flex items-center gap-2">
            <Download size={16} />
            Baixar modelo
          </button>
          <label className="btn-secondary flex items-center gap-2 cursor-pointer">
            <Upload size={16} />
            {importing ? 'Importando…' : 'Importar Excel'}
            <input type="file" accept=".xlsx,.xls" className="hidden" onChange={handleImport} disabled={importing} />
          </label>
          <button onClick={() => empresasAPI.baixarModeloResponsaveis()} className="btn-secondary flex items-center gap-2"
            title="Modelo p/ importar responsável por setor (CNPJ + colunas de setor)">
            <Download size={16} /> Modelo resp.
          </button>
          <label className={`btn-secondary flex items-center gap-2 cursor-pointer ${importandoResp ? 'opacity-60 pointer-events-none' : ''}`}
            title="Importar responsável por setor: célula preenchida marca; vazia desmarca">
            <Upload size={16} /> {importandoResp ? 'Importando…' : 'Importar resp.'}
            <input type="file" accept=".xlsx,.xls" className="hidden" onChange={handleImportResp} />
          </label>
          <button
            onClick={() => {
              setEditingEmpresa(null);
              setFormData(EMPRESA_VAZIA);
              setRespSetor(setores.map((s) => ({ setor_id: s.id, setor_nome: s.nome, atende: true, responsavel_id: '' })));
              setShowModal(true);
            }}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={18} />
            Nova Empresa
          </button>
        </div>
      </div>

      {importResult && (
        <div className="card mb-4">
          <div className="flex items-start justify-between">
            <div className="flex flex-wrap gap-2">
              <span className="px-3 py-1 rounded-full text-sm bg-green-100 text-green-700">Criadas: {importResult.resumo?.criadas ?? 0}</span>
              <span className="px-3 py-1 rounded-full text-sm bg-sky-100 text-sky-700">Atualizadas: {importResult.resumo?.atualizadas ?? 0}</span>
              {importResult.resumo?.erros > 0 && (
                <span className="px-3 py-1 rounded-full text-sm bg-red-100 text-red-700">Erros: {importResult.resumo.erros}</span>
              )}
              <span className="px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-600">Total: {importResult.resumo?.total ?? 0}</span>
            </div>
            <button onClick={() => setImportResult(null)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
          </div>
          {importResult.erro && <p className="text-sm text-red-600 mt-2">{importResult.erro}</p>}
          {importResult.detalhes?.some((d) => d.status === 'erro') && (
            <ul className="text-xs text-red-600 mt-3 space-y-0.5">
              {importResult.detalhes.filter((d) => d.status === 'erro').map((d, i) => (
                <li key={i}>{d.linha}: {d.detalhe}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="card mb-4">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          <input className="input-field" placeholder="Razão social"
            value={filtros.razao} onChange={(e) => setFiltros({ ...filtros, razao: e.target.value })} />
          <input className="input-field" placeholder="CNPJ"
            value={filtros.cnpj} onChange={(e) => setFiltros({ ...filtros, cnpj: e.target.value })} />
          <select className="input-field" value={filtros.regime} onChange={(e) => setFiltros({ ...filtros, regime: e.target.value })}>
            <option value="">Todos os regimes</option>
            {REGIMES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
          <input className="input-field" placeholder="Grupo econômico"
            value={filtros.grupo} onChange={(e) => setFiltros({ ...filtros, grupo: e.target.value })} />
          <select className="input-field" value={filtros.situacao} onChange={(e) => setFiltros({ ...filtros, situacao: e.target.value })}>
            <option value="ativa">Ativas</option>
            <option value="inativa">Inativas</option>
            <option value="todas">Todas</option>
          </select>
        </div>
      </div>

      <div className="card">
        {empresasFiltradas.length === 0 ? (
          <div className="text-center py-12">
            <Building2 size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">{empresas.length === 0 ? 'Nenhuma empresa cadastrada' : 'Nenhuma empresa com esses filtros'}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Código</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Razão Social</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">CNPJ</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Regime</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Grupo</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Situação</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-600">Ações</th>
                </tr>
              </thead>
              <tbody>
                {empresasFiltradas.map((empresa) => (
                  <tr key={empresa.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 text-gray-500 font-mono">#{empresa.id}</td>
                    <td className="py-3 px-4">
                      {empresa.razao_social}
                      {empresa.bloqueado && (
                        <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700">Bloqueada</span>
                      )}
                    </td>
                    <td className="py-3 px-4">{empresa.cnpj || '-'}</td>
                    <td className="py-3 px-4">{labelDe(REGIMES, empresa.regime_tributario)}</td>
                    <td className="py-3 px-4">{empresa.grupo || '-'}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 text-xs rounded-full ${
                        empresa.ativo === false ? 'bg-gray-200 text-gray-600' : 'bg-green-100 text-green-700'}`}>
                        {empresa.ativo === false ? 'Inativa' : 'Ativa'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleBloquear(empresa)}
                          title={empresa.bloqueado ? 'Desbloquear' : 'Bloquear'}
                          className={`p-2 rounded-lg transition-colors ${empresa.bloqueado ? 'text-green-600 hover:bg-green-50' : 'text-amber-600 hover:bg-amber-50'}`}
                        >
                          {empresa.bloqueado ? <Unlock size={16} /> : <Lock size={16} />}
                        </button>
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
          <div className="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">
                {editingEmpresa ? 'Editar Empresa' : 'Nova Empresa'}
              </h2>
            </div>
            <form onSubmit={handleSubmit} className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="sm:col-span-2">
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
                <label className="block text-sm font-medium text-gray-700 mb-1">Regime tributário</label>
                <select
                  value={formData.regime_tributario}
                  onChange={(e) => setFormData({ ...formData, regime_tributario: e.target.value })}
                  className="input-field"
                >
                  {REGIMES.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Segmento</label>
                <select
                  value={formData.segmento}
                  onChange={(e) => setFormData({ ...formData, segmento: e.target.value })}
                  className="input-field"
                >
                  {SEGMENTOS.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Grupo de empresas</label>
                <input
                  type="text"
                  value={formData.grupo}
                  onChange={(e) => setFormData({ ...formData, grupo: e.target.value })}
                  className="input-field"
                  placeholder="ex.: Markbuilding"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Situação</label>
                <select
                  value={formData.ativo ? 'ativa' : 'inativa'}
                  onChange={(e) => setFormData({ ...formData, ativo: e.target.value === 'ativa' })}
                  className="input-field"
                >
                  <option value="ativa">Ativa</option>
                  <option value="inativa">Inativa</option>
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Responsável por setor</label>
                <div className="border border-gray-200 rounded-lg divide-y divide-gray-100">
                  {respSetor.length === 0 && (
                    <p className="text-xs text-gray-400 px-3 py-2">Cadastre setores para definir os responsáveis.</p>
                  )}
                  {respSetor.map((r, i) => (
                    <div key={r.setor_id} className="flex items-center gap-2 px-3 py-1.5">
                      <label className="flex items-center gap-1.5 w-36 shrink-0 cursor-pointer" title="A empresa contratou este serviço?">
                        <input type="checkbox" checked={r.atende}
                          onChange={(e) => setRespSetor((arr) => arr.map((x, j) => j === i ? { ...x, atende: e.target.checked } : x))}
                          className="h-4 w-4" />
                        <span className="text-sm text-gray-600">{r.setor_nome}</span>
                      </label>
                      <select
                        value={r.responsavel_id}
                        disabled={!r.atende}
                        onChange={(e) => setRespSetor((arr) => arr.map((x, j) => j === i ? { ...x, responsavel_id: e.target.value } : x))}
                        className="input-field py-1 text-sm flex-1 disabled:bg-gray-50 disabled:text-gray-400"
                      >
                        <option value="">{r.atende ? '— sem responsável —' : 'não atende'}</option>
                        {usuarios.filter((u) => u.tipo !== 'cliente' && !u.bloqueado).map((u) => (
                          <option key={u.id} value={u.id}>{u.nome}</option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-1">Marque só os setores que a empresa contratou. Setor desmarcado não gera tarefa. O gestor sai automático do gestor do responsável.</p>
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Endereço</label>
                <textarea
                  value={formData.endereco}
                  onChange={(e) => setFormData({ ...formData, endereco: e.target.value })}
                  className="input-field"
                  rows={2}
                />
              </div>
              <div className="flex gap-3 pt-2 sm:col-span-2">
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