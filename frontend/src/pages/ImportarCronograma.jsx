import { useState, useEffect, useMemo } from 'react';
import { cronogramaAPI, empresasAPI, setoresAPI } from '../services/api';
import { CalendarClock, Upload, CheckCircle2, AlertTriangle } from 'lucide-react';

const SETORES_PADRAO = ['Contabilidade', 'Fiscal', 'DP', 'Financeiro'];
const primeiroToken = (s) => ((s || '').toUpperCase().match(/[A-Z0-9]+/) || [''])[0];
const normTxt = (s) => (s || '').normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
const baseCnpj = (s) => (s || '').replace(/\D/g, '').slice(0, 8);  // raiz do CNPJ (matriz + filiais)
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
  const [setores, setSetores] = useState([]);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [paraTodas, setParaTodas] = useState(true);

  useEffect(() => {
    empresasAPI.list().then((r) => setEmpresas(r.data)).catch(() => {});
    setoresAPI.list().then((r) => setSetores(r.data)).catch(() => {});
  }, []);

  // opções do dropdown de setor: os 4 padrão + os setores cadastrados (inclui novos)
  const setorOptions = useMemo(() => {
    const nomes = new Set(SETORES_PADRAO);
    setores.forEach((s) => s?.nome && nomes.add(s.nome));
    return [...nomes].sort((a, b) => a.localeCompare(b, 'pt'));
  }, [setores]);

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
      // Pré-preenche empresas por linha:
      //  1) pelo CNPJ -> casa a base (raiz), pegando matriz + todas as filiais cadastradas;
      //  2) pelo código/nome da coluna Empresa (1º termo da razão social).
      const pre = (data.itens || []).map((it) => {
        const ids = new Set();
        (it.cnpjs || []).forEach((cn) => {
          const raiz = baseCnpj(cn);
          if (raiz.length === 8) empresas.forEach((e) => { if (baseCnpj(e.cnpj) === raiz) ids.add(e.id); });
        });
        (it.entidades || []).forEach((cod) => {
          empresas.forEach((e) => { if (primeiroToken(e.razao_social) === cod) ids.add(e.id); });
        });
        // setor: casa o texto do arquivo com um setor cadastrado; senão mantém o chute
        const setorMatch = it.setor_raw
          ? setores.find((s) => normTxt(s.nome) === normTxt(it.setor_raw))?.nome
          : null;
        return { ...it, setor: setorMatch || it.setor, empresa_ids: [...ids] };
      });
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
      const { data } = await cronogramaAPI.importar(grupo, itens, {}, paraTodas);
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
        <h1 className="text-2xl font-bold text-gray-800">Importar obrigações</h1>
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
            <h2 className="font-semibold">Importado: grupo {resultado.grupo}</h2>
          </div>
          <p className="text-sm text-gray-600">
            {resultado.criadas} obrigação(ões) criada(s) · {resultado.atualizadas} atualizada(s) ·
            empresas: {(resultado.empresas || []).join(', ')}
          </p>
        </div>
      )}

      {!itens && (
        <div className="card">
          <div className="flex items-end justify-between gap-3 mb-4 flex-wrap">
            <div className="max-w-xs flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Grupo econômico</label>
              <input className="input-field" value={grupo} onChange={(e) => setGrupo(e.target.value)}
                placeholder="ex.: GRABER" />
            </div>
            <button onClick={() => cronogramaAPI.baixarModelo()} className="btn-secondary">Baixar modelo</button>
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
            <span className="text-xs text-gray-400">Excel (.xlsx/.xls) · colunas: Descrição da tarefa, Competência, Vencimento, Empresa, CNPJ, Gera multa, Setor</span>
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
              {!paraTodas && semEmpresa > 0 && (
                <span className="px-3 py-1 rounded-full text-sm bg-amber-100 text-amber-700 flex items-center gap-1">
                  <AlertTriangle size={13} /> {semEmpresa} sem empresa
                </span>
              )}
              <label className="px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-700 flex items-center gap-1.5 cursor-pointer"
                title="A obrigação vale para todas as empresas (sem grudar CNPJ). Desmarque só para obrigações específicas de certas empresas.">
                <input type="checkbox" checked={paraTodas} onChange={(e) => setParaTodas(e.target.checked)} />
                Aplicar a todas as empresas
              </label>
              <select value="" title="Aplicar um setor a todas as linhas"
                onChange={(e) => { if (e.target.value) setItens((arr) => arr.map((it) => ({ ...it, setor: e.target.value }))); e.target.value = ''; }}
                className="input-field py-1 text-xs w-auto">
                <option value="">Setor de todas…</option>
                {setorOptions.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setItens(null)} className="btn-secondary">Cancelar</button>
              <button onClick={importar} disabled={busy} className="btn-primary">
                {busy ? 'Importando…' : `Importar ${itens.length}`}
              </button>
            </div>
          </div>

          <div className="overflow-x-auto max-h-[62vh] overflow-y-auto">
            <table className="table-app">
              <thead className="sticky top-0 bg-white">
                <tr className="text-left text-gray-500 border-b border-gray-200">
                  <th className="py-2 pr-3 font-medium">Atividade</th>
                  <th className="py-2 pr-3 font-medium">Setor</th>
                  {!paraTodas && <th className="py-2 pr-3 font-medium w-[20rem]">Empresas</th>}
                  <th className="py-2 pr-3 font-medium">Prazo</th>
                  <th className="py-2 pr-3 font-medium">Competência</th>
                  <th className="py-2 pr-3 font-medium text-center">Multa</th>
                </tr>
              </thead>
              <tbody>
                {itens.map((it, idx) => (
                  <tr key={idx} className="border-b border-gray-100 align-top">
                    <td className="py-1.5 pr-3 text-gray-700 max-w-[20rem]">{it.nome}</td>
                    <td className="py-1.5 pr-3">
                      <select value={it.setor} onChange={(e) => patch(idx, 'setor', e.target.value)}
                        className={`input-field py-1 text-xs ${!it.setor ? 'border-amber-400' : ''}`}>
                        <option value="">(escolher)</option>
                        {setorOptions.map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </td>
                    {!paraTodas && (
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
                    )}
                    <td className="py-1.5 pr-3 text-gray-600 text-xs whitespace-nowrap">{it.prazo_label}</td>
                    <td className="py-1.5 pr-3 text-gray-400 text-xs whitespace-nowrap">
                      {it.competencia_ref === 'mes_anterior' ? 'mês anterior' : 'mesmo mês'}
                    </td>
                    <td className="py-1.5 pr-3 text-center">
                      <input type="checkbox" className="h-4 w-4" checked={!!it.gera_multa}
                        onChange={(e) => patch(idx, 'gera_multa', e.target.checked)} />
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
