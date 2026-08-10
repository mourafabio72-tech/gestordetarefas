import { useState, useEffect } from 'react';
import { cronogramaAPI, empresasAPI } from '../services/api';
import { CalendarClock, Upload, CheckCircle2, AlertTriangle } from 'lucide-react';

const SETORES = ['Contabilidade', 'Fiscal', 'DP', 'Financeiro'];

export default function ImportarCronograma() {
  const [grupo, setGrupo] = useState('GRABER');
  const [itens, setItens] = useState(null);
  const [entidades, setEntidades] = useState([]);
  const [mapa, setMapa] = useState({});          // { codigo: empresa_id }
  const [empresas, setEmpresas] = useState([]);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [resultado, setResultado] = useState(null);

  useEffect(() => { empresasAPI.list().then((r) => setEmpresas(r.data)).catch(() => {}); }, []);

  const analisar = async (file) => {
    if (!file) return;
    setBusy(true); setResultado(null); setItens(null);
    try {
      const { data } = await cronogramaAPI.analisar(file);
      if (data.erro) { alert(data.erro); return; }
      setItens(data.itens);
      setEntidades(data.entidades || []);
      setMapa({});
    } catch (e) {
      alert(e.response?.data?.detail || 'Não consegui ler o cronograma.');
    } finally { setBusy(false); }
  };

  const onDrop = (e) => { e.preventDefault(); setDragOver(false); analisar(e.dataTransfer.files?.[0]); };
  const setSetor = (idx, v) => setItens((arr) => arr.map((it, i) => i === idx ? { ...it, setor: v } : it));

  const importar = async () => {
    setBusy(true);
    try {
      const { data } = await cronogramaAPI.importar(grupo, itens, mapa);
      setResultado(data);
      setItens(null);
    } catch (e) {
      alert(e.response?.data?.detail || 'Erro ao importar.');
    } finally { setBusy(false); }
  };

  const semSetor = itens ? itens.filter((i) => !i.setor).length : 0;

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <CalendarClock className="text-primary-700" />
        <h1 className="text-2xl font-bold text-gray-800">Importar cronograma</h1>
      </div>
      <p className="text-sm text-gray-600 mb-6 max-w-3xl">
        Suba a planilha do <strong>cronograma de fechamento</strong>. Cada atividade vira uma
        <strong> obrigação recorrente</strong>, vinculada às empresas do grupo, com o
        <strong> prazo em dia útil</strong> (convertido das datas). Revise o setor de cada uma antes de salvar.
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
            <p className="text-xs text-gray-400 mt-1">As empresas (FOS, SL, SLS…) entram neste grupo.</p>
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
              <span className="px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-600">Empresas: {entidades.join(', ')}</span>
              {semSetor > 0 && (
                <span className="px-3 py-1 rounded-full text-sm bg-amber-100 text-amber-700 flex items-center gap-1">
                  <AlertTriangle size={13} /> {semSetor} sem setor
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
          <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 p-3">
            <p className="text-sm font-medium text-gray-700 mb-2">Vincular cada entidade do arquivo a uma empresa cadastrada</p>
            <div className="flex flex-wrap gap-3">
              {entidades.map((cod) => (
                <div key={cod} className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-gray-600 w-10">{cod}</span>
                  <select value={mapa[cod] || ''} onChange={(e) => setMapa((m) => ({ ...m, [cod]: e.target.value }))}
                    className="input-field py-1 text-xs w-56">
                    <option value="">— criar como “{cod}” —</option>
                    {empresas.map((emp) => (
                      <option key={emp.id} value={emp.id}>
                        {emp.razao_social}{emp.grupo ? ` · ${emp.grupo}` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Deixe em “criar como…” só se ainda não cadastrou a empresa. O ideal é apontar para a empresa real (com CNPJ).
            </p>
          </div>
          <div className="overflow-x-auto max-h-[60vh] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white">
                <tr className="text-left text-gray-500 border-b border-gray-200">
                  <th className="py-2 pr-3 font-medium">Atividade</th>
                  <th className="py-2 pr-3 font-medium">Setor</th>
                  <th className="py-2 pr-3 font-medium">Empresas</th>
                  <th className="py-2 pr-3 font-medium">Prazo</th>
                  <th className="py-2 pr-3 font-medium">Competência</th>
                </tr>
              </thead>
              <tbody>
                {itens.map((it, idx) => (
                  <tr key={idx} className="border-b border-gray-100">
                    <td className="py-1.5 pr-3 text-gray-700 max-w-[22rem]">{it.nome}</td>
                    <td className="py-1.5 pr-3">
                      <select value={it.setor} onChange={(e) => setSetor(idx, e.target.value)}
                        className={`input-field py-1 text-xs ${!it.setor ? 'border-amber-400' : ''}`}>
                        <option value="">— escolher —</option>
                        {SETORES.map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </td>
                    <td className="py-1.5 pr-3 text-gray-500 text-xs">{(it.entidades || []).join('+')}</td>
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
