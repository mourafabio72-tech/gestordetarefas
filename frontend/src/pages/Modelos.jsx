import { useState, useEffect } from 'react';
import { modelosAPI, empresasAPI, obrigacoesAPI } from '../services/api';
import { FileStack, Upload, Trash2, CheckCircle2, AlertTriangle, Building2, FileCheck2 } from 'lucide-react';

const TIPOS = {
  recibo_entrega: 'Recibo de entrega',
  comprovante_pagamento: 'Comprovante de pagamento',
  relatorio: 'Relatório',
  outro: 'Outro',
};
const TIPO_CLS = {
  recibo_entrega: 'bg-primary-100 text-primary-700',
  comprovante_pagamento: 'bg-amber-100 text-amber-700',
  relatorio: 'bg-sky-100 text-sky-700',
  outro: 'bg-gray-100 text-gray-600',
};

export default function Modelos() {
  const [modelos, setModelos] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [obrigacoes, setObrigacoes] = useState([]);
  const [analise, setAnalise] = useState(null);   // pré-visualização a revisar
  const [form, setForm] = useState(null);          // campos editáveis do modelo
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const carregar = async () => {
    const [m, e, o] = await Promise.all([modelosAPI.list(), empresasAPI.list(), obrigacoesAPI.list()]);
    setModelos(m.data);
    setEmpresas(e.data);
    setObrigacoes(o.data);
  };
  useEffect(() => { carregar(); }, []);

  const analisar = async (file) => {
    if (!file) return;
    setBusy(true); setAnalise(null); setForm(null);
    try {
      const { data } = await modelosAPI.analisar(file);
      setAnalise(data);
      setForm({
        nome_arquivo: data.nome_arquivo,
        cnpj: data.cnpj || '',
        razao_social_extraida: data.razao_social_extraida || '',
        empresa_id: data.empresa_id || '',
        obrigacao_id: data.obrigacao_sugerida_id || '',
        tipo_documento: data.tipo_documento || 'outro',
        identificador: data.candidatos?.[0]?.texto || '',
        competencia_exemplo: data.competencia_exemplo || '',
        protocolo_exemplo: data.protocolo_exemplo || '',
        texto_extraido: data.texto_extraido || '',
      });
    } catch (err) {
      alert(err.response?.data?.detail || 'Não consegui ler o arquivo.');
    } finally { setBusy(false); }
  };

  const onDrop = (ev) => {
    ev.preventDefault(); setDragOver(false);
    analisar(ev.dataTransfer.files?.[0]);
  };

  const salvar = async () => {
    setBusy(true);
    try {
      await modelosAPI.create({ ...form, empresa_id: form.empresa_id || null, obrigacao_id: form.obrigacao_id || null });
      setAnalise(null); setForm(null);
      await carregar();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao salvar o modelo.');
    } finally { setBusy(false); }
  };

  const excluir = async (id) => {
    if (!confirm('Remover este modelo do repositório?')) return;
    await modelosAPI.delete(id);
    await carregar();
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <FileStack className="text-primary-700" />
        <h1 className="text-2xl font-bold text-gray-800">Modelos</h1>
      </div>
      <p className="text-sm text-gray-600 mb-6 max-w-3xl">
        Suba um <strong>recibo, comprovante ou relatório</strong> de exemplo. O sistema lê o documento,
        identifica a <strong>empresa</strong> (pelo CNPJ) e o <strong>tipo</strong>, e liga a uma
        <strong> obrigação</strong>. Ao salvar, o identificador escolhido passa a treinar o e-validador.
      </p>

      {/* Upload */}
      <div className="card mb-6">
        <label
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={`block cursor-pointer border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
            dragOver ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-primary-400'}`}
        >
          <Upload size={28} className="mx-auto text-gray-400 mb-2" />
          <span className="text-sm text-gray-600 block">
            {busy ? 'Lendo o documento…' : 'Arraste um arquivo aqui ou clique para selecionar'}
          </span>
          <span className="text-xs text-gray-400">Aceita PDF, XLSX e XLS · um por vez</span>
          <input type="file" accept=".pdf,.xlsx,.xls" className="hidden"
            onChange={(e) => analisar(e.target.files?.[0])} />
        </label>
      </div>

      {/* Revisão da análise */}
      {form && (
        <div className="card mb-6">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 size={18} className="text-green-600" />
            <h2 className="font-semibold text-gray-800">Revisar e salvar — {analise.nome_arquivo}</h2>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Empresa</label>
              <select className="input-field" value={form.empresa_id}
                onChange={(e) => setForm({ ...form, empresa_id: e.target.value })}>
                <option value="">— não vinculada —</option>
                {empresas.map((e) => (
                  <option key={e.id} value={e.id}>{e.razao_social}</option>
                ))}
              </select>
              <p className="text-xs text-gray-400 mt-1">
                {analise.cnpj
                  ? (analise.empresa_id
                      ? <span className="text-green-600">CNPJ {analise.cnpj} reconhecido automaticamente.</span>
                      : <span className="text-amber-600 flex items-center gap-1"><AlertTriangle size={12} />CNPJ {analise.cnpj} não está cadastrado — selecione ou cadastre a empresa.</span>)
                  : 'CNPJ não encontrado no documento.'}
              </p>
              {analise.razao_social_extraida && (
                <p className="text-xs text-gray-500 mt-1">Lido no documento: <em>{analise.razao_social_extraida}</em></p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de documento</label>
              <select className="input-field" value={form.tipo_documento}
                onChange={(e) => setForm({ ...form, tipo_documento: e.target.value })}>
                {Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Obrigação</label>
              <select className="input-field" value={form.obrigacao_id}
                onChange={(e) => setForm({ ...form, obrigacao_id: e.target.value })}>
                <option value="">— não vinculada —</option>
                {obrigacoes.map((o) => <option key={o.id} value={o.id}>{o.nome}</option>)}
              </select>
              {analise.obrigacao_sugerida_id && (
                <p className="text-xs text-green-600 mt-1">Sugerida: {analise.obrigacao_sugerida_nome}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Identificador (treina o e-validador)
              </label>
              <input className="input-field" value={form.identificador}
                onChange={(e) => setForm({ ...form, identificador: e.target.value })}
                placeholder="trecho único do documento" />
              {analise.candidatos?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {analise.candidatos.map((c, i) => (
                    <button key={i} type="button"
                      onClick={() => setForm({ ...form, identificador: c.texto })}
                      className={`text-xs rounded-full px-2 py-1 border ${
                        c.colide_com?.length
                          ? 'border-amber-300 bg-amber-50 text-amber-700'
                          : 'border-gray-200 bg-gray-50 text-gray-600 hover:border-primary-400'}`}
                      title={c.colide_com?.length ? `Colide com: ${c.colide_com.join(', ')}` : 'Livre'}>
                      {c.texto}{c.colide_com?.length ? ' ⚠' : ''}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 mt-5">
            <button onClick={salvar} disabled={busy} className="btn-primary">
              {busy ? 'Salvando…' : 'Salvar modelo'}
            </button>
            <button onClick={() => { setForm(null); setAnalise(null); }} className="btn-secondary">
              Cancelar
            </button>
            {(form.competencia_exemplo || form.protocolo_exemplo) && (
              <span className="text-xs text-gray-400">
                {form.competencia_exemplo && <>Competência exemplo {form.competencia_exemplo}. </>}
                {form.protocolo_exemplo && <>Protocolo {String(form.protocolo_exemplo).slice(0, 14)}…</>}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Catálogo */}
      <div className="card">
        <h2 className="font-semibold text-gray-800 mb-4">Repositório ({modelos.length})</h2>
        {modelos.length === 0 ? (
          <p className="text-sm text-gray-500">Nenhum modelo ainda. Suba o primeiro documento acima.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-200">
                  <th className="py-2 pr-4 font-medium">Arquivo</th>
                  <th className="py-2 pr-4 font-medium">Empresa</th>
                  <th className="py-2 pr-4 font-medium">Tipo</th>
                  <th className="py-2 pr-4 font-medium">Obrigação</th>
                  <th className="py-2 pr-4 font-medium">Identificador</th>
                  <th className="py-2"></th>
                </tr>
              </thead>
              <tbody>
                {modelos.map((m) => (
                  <tr key={m.id} className="border-b border-gray-100">
                    <td className="py-2 pr-4 text-gray-700 max-w-[16rem] truncate" title={m.nome_arquivo}>{m.nome_arquivo}</td>
                    <td className="py-2 pr-4">
                      {m.empresa_nome
                        ? <span className="flex items-center gap-1 text-gray-700"><Building2 size={13} className="text-gray-400" />{m.empresa_nome}</span>
                        : <span className="text-amber-600 text-xs">{m.razao_social_extraida || m.cnpj || '—'}</span>}
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`text-xs rounded-full px-2 py-0.5 ${TIPO_CLS[m.tipo_documento] || TIPO_CLS.outro}`}>
                        {m.tipo_label}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-gray-700">
                      {m.obrigacao_nome
                        ? <span className="flex items-center gap-1"><FileCheck2 size={13} className="text-primary-500" />{m.obrigacao_nome}</span>
                        : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="py-2 pr-4 text-gray-500 max-w-[12rem] truncate" title={m.identificador}>{m.identificador || '—'}</td>
                    <td className="py-2 text-right">
                      <button onClick={() => excluir(m.id)} className="text-gray-400 hover:text-red-600" title="Remover">
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
