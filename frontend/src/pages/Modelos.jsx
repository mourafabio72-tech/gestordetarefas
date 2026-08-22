import { useState, useEffect } from 'react';
import { modelosAPI, empresasAPI, obrigacoesAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { FileStack, Upload, Trash2, CheckCircle2, AlertTriangle, Building2, FileCheck2, SkipForward } from 'lucide-react';
import { formatarRazaoSocial } from './razaoSocial';

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

// campos editáveis a partir de uma análise
const formDe = (a) => ({
  nome_arquivo: a.nome_arquivo,
  cnpj: a.cnpj || '',
  razao_social_extraida: a.razao_social_extraida || '',
  empresa_id: a.empresa_id || '',
  obrigacao_id: a.obrigacao_sugerida_id || '',
  tipo_documento: a.tipo_documento || 'outro',
  identificador: a.candidatos?.find((c) => !c.colide_com?.length)?.texto || a.candidatos?.[0]?.texto || '',
  competencia_exemplo: a.competencia_exemplo || '',
  protocolo_exemplo: a.protocolo_exemplo || '',
  texto_extraido: a.texto_extraido || '',
});

export default function Modelos() {
  const [modelos, setModelos] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [obrigacoes, setObrigacoes] = useState([]);
  const [fila, setFila] = useState([]);        // análises aguardando revisão (fila[0] = atual)
  const [form, setForm] = useState(null);       // campos editáveis do item atual
  const [resumo, setResumo] = useState(null);   // resultado do último lote
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const carregar = async () => {
    const [m, e, o] = await Promise.all([modelosAPI.list(), empresasAPI.list(), obrigacoesAPI.list()]);
    setModelos(m.data); setEmpresas(e.data); setObrigacoes(o.data);
  };
  useEffect(() => { carregar(); }, []);

  // sempre que o topo da fila muda, reinicializa o formulário
  const atual = fila[0] || null;
  useEffect(() => { setForm(atual ? formDe(atual) : null); }, [atual]);

  const processar = async (fileList) => {
    const files = Array.from(fileList || []).filter((f) => /\.(pdf|xlsx|xls)$/i.test(f.name));
    if (!files.length) return;
    setBusy(true); setResumo(null);
    try {
      if (files.length === 1) {
        const { data } = await modelosAPI.analisar(files[0]);
        setFila([data]);
      } else {
        const { data } = await modelosAPI.lote(files);
        setResumo(data);
        setFila(data.revisar || []);
        if (data.resumo.salvos) await carregar();  // já mostra os salvos automaticamente
      }
    } catch (err) {
      alert(mensagemDeErro(err, 'Não consegui ler os arquivos.'));
    } finally { setBusy(false); }
  };

  const onDrop = (ev) => { ev.preventDefault(); setDragOver(false); processar(ev.dataTransfer.files); };

  const salvar = async () => {
    setBusy(true);
    try {
      await modelosAPI.create({ ...form, empresa_id: form.empresa_id || null, obrigacao_id: form.obrigacao_id || null });
      setFila((f) => f.slice(1));
      await carregar();
    } catch (err) {
      alert(mensagemDeErro(err, 'Erro ao salvar o modelo.'));
    } finally { setBusy(false); }
  };

  const pular = () => setFila((f) => f.slice(1));

  const excluir = async (id) => {
    if (!confirm('Remover este modelo do repositório?')) return;
    await modelosAPI.delete(id); await carregar();
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <FileStack className="text-primary-700" />
        <h1 className="text-2xl font-bold text-gray-800">Modelos</h1>
      </div>
      <p className="text-sm text-gray-600 mb-6 max-w-3xl">
        Suba um ou <strong>vários</strong> recibos/comprovantes/relatórios de exemplo. O sistema lê,
        identifica a <strong>empresa</strong> (pelo CNPJ) e o <strong>tipo</strong>, e liga a uma
        <strong> obrigação</strong>. Em lote, os 100% reconhecidos são <strong>salvos sozinhos</strong> e
        só os pendentes entram na fila de revisão. Ao salvar, o identificador treina o e-validador.
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
            {busy ? 'Lendo os documentos…' : 'Arraste os arquivos aqui ou clique para selecionar'}
          </span>
          <span className="text-xs text-gray-400">Aceita PDF, XLSX e XLS · vários de uma vez</span>
          <input type="file" accept=".pdf,.xlsx,.xls" multiple className="hidden"
            onChange={(e) => processar(e.target.files)} />
        </label>
      </div>

      {/* Resumo do lote */}
      {resumo && (
        <div className="card mb-6">
          <div className="flex flex-wrap gap-2 mb-3">
            <span className="px-3 py-1 rounded-full text-sm bg-green-100 text-green-700">
              Salvos automaticamente: {resumo.resumo.salvos}
            </span>
            <span className="px-3 py-1 rounded-full text-sm bg-amber-100 text-amber-700">
              Para revisar: {resumo.resumo.revisar}
            </span>
            <span className="px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-600">
              Total: {resumo.resumo.total}
            </span>
          </div>
          {resumo.salvos?.length > 0 && (
            <ul className="text-xs text-gray-500 space-y-0.5">
              {resumo.salvos.map((s) => (
                <li key={s.id} className="flex items-center gap-1">
                  <CheckCircle2 size={12} className="text-green-600" />
                  <span className="truncate">{s.nome_arquivo} → {formatarRazaoSocial(s.empresa_nome)} · {s.obrigacao_nome}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Fila de revisão (item atual) */}
      {form && atual && (
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={18} className="text-green-600" />
              <h2 className="font-semibold text-gray-800 truncate">Revisar: {atual.nome_arquivo}</h2>
            </div>
            {fila.length > 1 && (
              <span className="text-xs text-gray-400 whitespace-nowrap">{fila.length} na fila</span>
            )}
          </div>

          {atual.motivo && (
            <div className="mb-4 text-xs bg-amber-50 text-amber-700 rounded-lg px-3 py-2 flex items-center gap-1">
              <AlertTriangle size={13} /> {atual.motivo}
            </div>
          )}
          {atual.erro && (
            <div className="mb-4 text-xs bg-red-50 text-red-600 rounded-lg px-3 py-2">{atual.erro}</div>
          )}

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Empresa</label>
              <select className="input-field" value={form.empresa_id}
                onChange={(e) => setForm({ ...form, empresa_id: e.target.value })}>
                <option value="">(não vinculada)</option>
                {empresas.map((e) => <option key={e.id} value={e.id}>{formatarRazaoSocial(e.razao_social)}</option>)}
              </select>
              <p className="text-xs text-gray-400 mt-1">
                {atual.cnpj
                  ? (atual.empresa_id
                      ? <span className="text-green-600">CNPJ {atual.cnpj} reconhecido automaticamente.</span>
                      : <span className="text-amber-600">CNPJ {atual.cnpj} não cadastrado: selecione ou cadastre a empresa.</span>)
                  : 'CNPJ não encontrado no documento.'}
              </p>
              {atual.razao_social_extraida && (
                <p className="text-xs text-gray-500 mt-1">Lido no documento: <em>{atual.razao_social_extraida}</em></p>
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
                <option value="">(não vinculada)</option>
                {obrigacoes.map((o) => <option key={o.id} value={o.id}>{o.nome}</option>)}
              </select>
              {atual.obrigacao_sugerida_id && (
                <p className="text-xs text-green-600 mt-1">Sugerida: {atual.obrigacao_sugerida_nome}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Identificador (treina o e-validador)
              </label>
              <input className="input-field" value={form.identificador}
                onChange={(e) => setForm({ ...form, identificador: e.target.value })}
                placeholder="trecho único do documento" />
              {atual.candidatos?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {atual.candidatos.map((c, i) => (
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
            <button onClick={pular} className="btn-secondary flex items-center gap-1">
              <SkipForward size={15} /> Pular
            </button>
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
            <table className="table-app">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-200">
                  <th className="pr-4 font-medium">Arquivo</th>
                  <th className="pr-4 font-medium">Empresa</th>
                  <th className="pr-4 font-medium">Tipo</th>
                  <th className="pr-4 font-medium">Obrigação</th>
                  <th className="pr-4 font-medium">Identificador</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {modelos.map((m) => (
                  <tr key={m.id} className="border-b border-gray-100">
                    <td className="pr-4 text-gray-700 max-w-[16rem] truncate" title={m.nome_arquivo}>{m.nome_arquivo}</td>
                    <td className="pr-4">
                      {m.empresa_nome
                        ? <span className="flex items-center gap-1 text-gray-700"><Building2 size={13} className="text-gray-400" />{formatarRazaoSocial(m.empresa_nome)}</span>
                        : <span className="text-amber-600 text-xs">{m.razao_social_extraida || m.cnpj || '-'}</span>}
                    </td>
                    <td className="pr-4">
                      <span className={`text-xs rounded-full px-2 py-0.5 ${TIPO_CLS[m.tipo_documento] || TIPO_CLS.outro}`}>
                        {m.tipo_label}
                      </span>
                    </td>
                    <td className="pr-4 text-gray-700">
                      {m.obrigacao_nome
                        ? <span className="flex items-center gap-1"><FileCheck2 size={13} className="text-primary-500" />{m.obrigacao_nome}</span>
                        : <span className="text-gray-400">-</span>}
                    </td>
                    <td className="pr-4 text-gray-500 max-w-[12rem] truncate" title={m.identificador}>{m.identificador || '-'}</td>
                    <td className="text-right">
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
