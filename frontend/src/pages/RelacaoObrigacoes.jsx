import { useState, useEffect, useMemo } from 'react';
import { obrigacoesAPI, empresasAPI, setoresAPI } from '../services/api';
import { FileStack, Download, Unlink } from 'lucide-react';

const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
// Rótulo da competência de referência. O campo aceita apelido (o formato
// antigo, ainda gravado nas obrigações existentes) ou deslocamento em meses --
// que é o que representa SPED e EFD-Contribuições, entregues no 2º mês
// subsequente ao fato gerador.
const COMP_APELIDOS = { mes_anterior: -1, mesmo_mes: 0, mes_seguinte: 1, ano_anterior: -12 };

function rotuloCompetencia(ref) {
  if (ref === null || ref === undefined || ref === '') return '-';
  const n = ref in COMP_APELIDOS ? COMP_APELIDOS[ref] : parseInt(ref, 10);
  if (Number.isNaN(n)) return '-';
  if (n === 0) return 'Mesmo mês';
  if (n === -12) return 'Ano anterior';
  if (n < 0) return n === -1 ? 'Mês anterior' : `${-n} meses antes`;
  return n === 1 ? 'Mês seguinte' : `${n} meses depois`;
}
const prazoLabel = (o) => {
  const t = o.regra_prazo_tipo;
  if (t === 'dia_util') return `${o.regra_prazo_dia || 1}º dia útil`;
  if (t === 'primeiro_dia_util') return 'Primeiro dia útil';
  if (t === 'dia_fixo') return `Dia ${o.regra_prazo_dia || '?'}`;
  return 'Último dia útil';
};
const mesesLabel = (csv) => {
  const n = (csv || '').split(',').map((x) => parseInt(x)).filter((x) => x >= 1 && x <= 12);
  return n.length >= 12 ? 'Todos' : n.sort((a, b) => a - b).map((x) => MESES[x - 1]).join(', ') || '-';
};

export default function RelacaoObrigacoes() {
  const [obrigacoes, setObrigacoes] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [setores, setSetores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({ obrigacao: '', empresa: '', setor: '', status: 'todas' });
  const [showDesvincular, setShowDesvincular] = useState(false);
  const [desvincEmpresa, setDesvincEmpresa] = useState('');
  const [desvinculando, setDesvinculando] = useState(false);

  const load = () =>
    Promise.all([obrigacoesAPI.list(), empresasAPI.list(true), setoresAPI.list()])
      .then(([o, e, s]) => { setObrigacoes(o.data); setEmpresas(e.data); setSetores(s.data); })
      .catch(() => {})
      .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

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
      setShowDesvincular(false); setDesvincEmpresa(''); load();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao desvincular');
    } finally { setDesvinculando(false); }
  };

  const empresaById = useMemo(() => Object.fromEntries(empresas.map((e) => [e.id, e])), [empresas]);
  const setorById = useMemo(() => Object.fromEntries(setores.map((s) => [s.id, s.nome])), [setores]);
  const so = (s) => (s || '').toString().toLowerCase();

  const lista = obrigacoes.filter((o) => {
    if (filtros.obrigacao && !`${so(o.nome)} ${so(o.mininome)}`.includes(so(filtros.obrigacao))) return false;
    if (filtros.empresa && !(o.empresa_ids || []).includes(parseInt(filtros.empresa))) return false;
    if (filtros.setor && String(o.setor_id) !== filtros.setor) return false;
    if (filtros.status === 'ativa' && !o.ativa) return false;
    if (filtros.status === 'inativa' && o.ativa) return false;
    return true;
  });

  const nomesEmpresas = (o) => (o.empresa_ids || []).map((id) => empresaById[id]?.razao_social).filter(Boolean);

  if (loading) return <div className="flex items-center justify-center h-64">Carregando...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <FileStack className="text-primary-700" />
          <h1 className="text-2xl font-bold text-gray-800">Relação de obrigações</h1>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowDesvincular(true)} className="btn-secondary flex items-center gap-2 text-red-600"
            title="Remove o vínculo de uma empresa das obrigações (não apaga nada além do vínculo)">
            <Unlink size={18} /> Desvincular empresa
          </button>
          <button onClick={() => obrigacoesAPI.baixarRelatorio()} className="btn-primary flex items-center gap-2">
            <Download size={18} /> Exportar Excel
          </button>
        </div>
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

      <div className="card mb-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <input className="input-field" placeholder="Obrigação (nome/mininome)"
            value={filtros.obrigacao} onChange={(e) => setFiltros({ ...filtros, obrigacao: e.target.value })} />
          <select className="input-field" value={filtros.empresa} onChange={(e) => setFiltros({ ...filtros, empresa: e.target.value })}>
            <option value="">Todas as empresas</option>
            {empresas.map((e) => <option key={e.id} value={e.id}>{e.razao_social}</option>)}
          </select>
          <select className="input-field" value={filtros.setor} onChange={(e) => setFiltros({ ...filtros, setor: e.target.value })}>
            <option value="">Todos os setores</option>
            {setores.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
          </select>
          <select className="input-field" value={filtros.status} onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}>
            <option value="todas">Todos os status</option>
            <option value="ativa">Ativas</option>
            <option value="inativa">Inativas</option>
          </select>
        </div>
      </div>

      <div className="card">
        <p className="text-sm text-gray-500 mb-3">{lista.length} obrigação(ões)</p>
        {lista.length === 0 ? (
          <p className="text-gray-500 text-center py-8">Nenhuma obrigação com esses filtros.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="table-app">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-200">
                  <th className="pr-3 font-medium">Obrigação</th>
                  <th className="pr-3 font-medium">Setor</th>
                  <th className="pr-3 font-medium">Empresas</th>
                  <th className="pr-3 font-medium">Prazo</th>
                  <th className="pr-3 font-medium">Competência</th>
                  <th className="pr-3 font-medium">Meses</th>
                  <th className="pr-3 font-medium text-center">Multa</th>
                  <th className="pr-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((o) => {
                  const emps = nomesEmpresas(o);
                  return (
                    <tr key={o.id} className="border-b border-gray-100">
                      <td className="pr-3 text-gray-800">{o.nome}{o.mininome ? <span className="text-gray-400"> · {o.mininome}</span> : null}</td>
                      <td className="pr-3 text-gray-600">{setorById[o.setor_id] || '-'}</td>
                      <td className="pr-3 text-gray-500 max-w-[16rem] truncate" title={emps.join(', ')}>
                        {emps.length ? (emps.length <= 2 ? emps.join(', ') : `${emps.slice(0, 2).join(', ')} +${emps.length - 2}`) : '-'}
                      </td>
                      <td className="pr-3 text-gray-600 whitespace-nowrap">{prazoLabel(o)}</td>
                      <td className="pr-3 text-gray-500 whitespace-nowrap">{rotuloCompetencia(o.competencia_ref)}</td>
                      <td className="pr-3 text-gray-500 whitespace-nowrap">{mesesLabel(o.meses_ativos)}</td>
                      <td className="pr-3 text-center">{o.passivel_multa ? '⚠️' : ''}</td>
                      <td className="pr-3">
                        <span className={`px-2 py-0.5 text-xs rounded-full ${o.ativa ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {o.ativa ? 'Ativa' : 'Inativa'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
