import { useState, useEffect, useMemo } from 'react';
import { cronogramaAPI, empresasAPI } from '../services/api';
import { CalendarClock, Upload, CheckCircle2, AlertTriangle } from 'lucide-react';

const SETORES = ['Contabilidade', 'Fiscal', 'DP', 'Financeiro'];
const primeiroToken = (s) => ((s || '').toUpperCase().match(/[A-Z0-9]+/) || [''])[0];
const fmtCnpj = (c) => {
  const d = (c || '').replace(/\D/g, '');
  return d.length === 14 ? d.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5') : (c || '');
};
// rótulo sem razão social: nome curto (fantasia ou código) + CNPJ
const rotuloEmpresa = (e) => {
  if (!e) return '?';
  const nome = (e.nome_fantasia || '').trim() || primeiroToken(e.razao_social);
  const cnpj = fmtCnpj(e.cnpj);
  return cnpj ? `${nome} · ${cnpj}` : nome;
};

export default function ImportarCronograma() {
  const [grupo, setGrupo] = useState('GRABER');
  const [itens, setItens] = useState(null);
  const [entidades, setEntidades] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [resultado, setResultado] = useState(null);

  useEffect(() => { empresasAPI.list().then((r) => setEmpresas(r.data)).catch(() => {}); }, []);

  const empresasOrdenadas = useMemo(
    () => [...empresas].sort((a, b) => (a.razao_social || '').localeCompare(b.razao_social || '', 'pt')),
    [empresas]);
  const empresaById = useMemo(() => Object.fromEntries(empresas.map((e) => [e.id, e])), [empresas]);

  const analisar = async (file) => {
    if (!file) return;
    setBusy(true); setResultado(null); setItens(null);
    try {
      const { data } = await cronogramaAPI.analisar(file);
      if (data.erro) { alert(data.erro); return; }
      // pré-preenche empresas por linha: casa o código do arquivo (FOS/SL/SLS)
      // com a empresa cujo 1º termo da razão social é igual (ex.: "FOS - FAST ONE...").
      const idsPorCodigo = {};
      (data.entidades || []).forEach((cod) => {
        idsPorCodigo[cod] = empresas.filter((e) => primeiroToken(e.razao_social) === cod).map((e) => e.id);
      });
      const pre = (data.itens || []).map((it) => ({
        ...it,
        empresa_ids: [...new Set((it.entidades || []).flatMap((c) => idsPorCodigo[c] || []))],
      }));
      setItens(pre);
      setEntidades(data.entidades || []);
    } catch (e) {
      alert(e.response?.data?.detail || 'Não consegui ler o cronograma.');
    } finally { setBusy(false); }
  };

  const onDrop = (e) => { e.preventDefault(); setDragOver(false); analisar(e.dataTransfer.files?.[0]); };
  const patch = (idx, campo, v) => setItens((arr) => arr.map((it, i) => i === idx ? { ...it, [campo]: v } : it));
  const addEmp = (idx, id) => { if (id) patch(idx, 'empresa_ids', [...new Set([...(itens[idx].empresa_ids || []), Number(id)])]); };
  const remEmp = (idx, id) => patch(idx, 'empresa_ids', (itens[idx].empresa_ids || []).filter((x) => x !== id));

  const importar = async () => {
    setBusy(true);
    try {
      const { data } = await cronogramaAPI.importar(grupo, itens, {});
      setResultado(data);
      setItens(null);
    } catch (e) {
      alert(e.response?.data?.detail || 'Erro ao importar.');
    } finally { setBusy(false); }
  };

  const semSetor = itens ? itens.filter((i) => !i.setor).length : 0;
  const semEmpresa = itens ? itens.filter((i) => !(i.empresa_ids || []).length).length : 0;

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <CalendarClock className="text-primary-700" />
        <h1 className="text-2xl font-bold text-gray-800">Importar cronograma</h1>
      </div>
      <p className="text-sm text-gray-600 mb-6 max-w-3xl">
        Suba a planilha do <strong>cronograma de fechamento</strong>. Cada atividade vira uma
        <strong> obrigação recorrente</strong>, com <strong>prazo em dia útil</strong> (convertido das datas).
        Revise o <strong>setor</strong> e as <strong>empresas</strong> de cada uma antes de salvar.
      </p>

      {resultado && (
        <div className="card mb-6">
          <div className="flex items-center gap-2 text-green-700 mb-1">
            <CheckCircle2 size={18} />
            <h2 className="font-semibold">Importado — grupo {resultado.grupo}</h2>
          </div>
          <p className="text-sm text-gray-600">
            {resultado.criadas} obrigação(ões) criada(s) · {resultado.atualizadas} atualizada(s) ·
            empresas: {(resultado.empresas || []).join(', ')}
          </p>
        </div>
      )}

      {!itens && (
        <div className="card">
          <div className="mb-4 max-w-xs">
            <label className="block text-sm font-medium text-gray-700 mb-1">Grupo econômico</label>
            <input className="input-field" value={grupo} onChange={(e) => setGrupo(e.target.value)}
              placeholder="ex.: GRABER" />
          </div>
          <label
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={`block cursor-pointer border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
              dragOver ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-primary-400'}`}
          >
            <Upload size={28} className="mx-auto text-gray-400 mb-2" />
            <span className="text-sm text-gray-600 block">
              {busy ? 'Lendo o cronograma…' : 'Arraste a planilha aqui ou clique para selecionar'}
            </span>
            <span className="text-xs text-gray-400">Excel (.xlsx/.xls) · colunas Atividade, Empresa, Prazo</span>
            <input type="file" accept=".xlsx,.xls" className="hidden"
              onChange={(e) => analisar(e.target.files?.[0])} />
          </label>
        </div>
      )}

      {itens && (
        <div className="card">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div className="flex flex-wrap gap-2">
              <span className="px-3 py-1 rounded-full text-sm bg-primary-100 text-primary-700">{itens.length} obrigações</span>
              {semSetor > 0 && (
                <span className="px-3 py-1 rounded-full text-sm bg-amber-100 text-amber-700 flex items-center gap-1">
                  <AlertTriangle size={13} /> {semSetor} sem setor
                </span>
              )}
              {semEmpresa > 0 && (
                <span className="px-3 py-1 rounded-full text-sm bg-amber-100 text-amber-700 flex items-center gap-1">
                  <AlertTriangle size={13} /> {semEmpresa} sem empresa
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <button onClick={() => setItens(null)} className="btn-secondary">Cancelar</button>
              <button onClick={importar} disabled={busy} className="btn-primary">
                {busy ? 'Importando…' : `Importar ${itens.length}`}
              </button>
            </div>
          </div>

          <div className="overflow-x-auto max-h-[62vh] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white">
                <tr className="text-left text-gray-500 border-b border-gray-200">
                  <th className="py-2 pr-3 font-medium">Atividade</th>
                  <th className="py-2 pr-3 font-medium">Setor</th>
                  <th className="py-2 pr-3 font-medium w-[20rem]">Empresas</th>
                  <th className="py-2 pr-3 font-medium">Prazo</th>
                  <th className="py-2 pr-3 font-medium">Competência</th>
                </tr>
              </thead>
              <tbody>
                {itens.map((it, idx) => (
                  <tr key={idx} className="border-b border-gray-100 align-top">
                    <td className="py-1.5 pr-3 text-gray-700 max-w-[20rem]">{it.nome}</td>
                    <td className="py-1.5 pr-3">
                      <select value={it.setor} onChange={(e) => patch(idx, 'setor', e.target.value)}
                        className={`input-field py-1 text-xs ${!it.setor ? 'border-amber-400' : ''}`}>
                        <option value="">— escolher —</option>
                        {SETORES.map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </td>
                    <td className="py-1.5 pr-3">
                      <div className="flex flex-wrap gap-1 items-center">
                        {(it.empresa_ids || []).map((id) => (
                          <span key={id} title={empresaById[id]?.razao_social}
                            className="inline-flex items-center gap-1 text-xs bg-primary-50 text-primary-700 rounded-full px-2 py-0.5">
                            {rotuloEmpresa(empresaById[id])}
                            <button type="button" onClick={() => remEmp(idx, id)} className="text-primary-400 hover:text-red-600">×</button>
                          </span>
                        ))}
                        <select value="" onChange={(e) => { addEmp(idx, e.target.value); e.target.value = ''; }}
                          className={`input-field py-1 text-xs w-48 ${!(it.empresa_ids || []).length ? 'border-amber-400' : ''}`}>
                          <option value="">+ empresa</option>
                          {empresasOrdenadas.filter((e) => !(it.empresa_ids || []).includes(e.id))
                            .map((e) => <option key={e.id} value={e.id}>{rotuloEmpresa(e)}</option>)}
                        </select>
                      </div>
                    </td>
                    <td className="py-1.5 pr-3 text-gray-600 text-xs whitespace-nowrap">{it.prazo_label}</td>
                    <td className="py-1.5 pr-3 text-gray-400 text-xs whitespace-nowrap">
                      {it.competencia_ref === 'mes_anterior' ? 'mês anterior' : 'mesmo mês'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
