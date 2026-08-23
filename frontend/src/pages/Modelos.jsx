import { useState, useEffect, useRef } from 'react';
import { modelosAPI, empresasAPI, obrigacoesAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { separarAceitos, emRemessas, juntarResultados, enviarComDivisao, EXTENSOES_ACEITAS }
  from './lotesModelos';
import { conferirIdentificador, trechoMovel } from './identificador';
import { estadoDoCandidato, explicar } from './colisaoIdentificador';
import { FileStack, Upload, Trash2, CheckCircle2, AlertTriangle, Building2, FileCheck2, SkipForward, Pencil } from 'lucide-react';
import { formatarRazaoSocial } from './razaoSocial';

// A guia é o documento A PAGAR que o escritório entrega; o comprovante é a
// prova de que foi pago, que o cliente devolve. Papéis opostos no fluxo.
// A guia é o documento A PAGAR que o escritório entrega; o comprovante é a
// prova de que foi pago. A declaração é o documento transmitido; o recibo é a
// prova de que ela foi entregue. Dois pares que se confundem fácil.
const TIPOS = {
  guia: 'Guia a pagar (DARF, DAS, GPS…)',
  comprovante_pagamento: 'Comprovante de pagamento',
  declaracao: 'Declaração (ECF, ECD, DCTF, DEFIS…)',
  recibo_entrega: 'Recibo de entrega',
  relatorio: 'Relatório',
  outro: 'Outro',
};
const TIPO_CLS = {
  guia: 'bg-orange-100 text-orange-700',
  comprovante_pagamento: 'bg-amber-100 text-amber-700',
  declaracao: 'bg-violet-100 text-violet-700',
  recibo_entrega: 'bg-primary-100 text-primary-700',
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
  const [progresso, setProgresso] = useState(null);   // { feitos, total }
  const [editandoId, setEditandoId] = useState(null); // modelo em edição, se houver
  // Arquivos cuja remessa não chegou ao servidor, por nome, para reenviar.
  const naoEnviados = useRef(new Map());
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
    const { aceitos, recusados } = separarAceitos(fileList);
    // Descarte por extensão era silencioso: quem arrastava uma pasta com .docx
    // no meio via "nada aconteceu" e não sabia por quê.
    if (recusados.length) {
      alert(`${recusados.length} arquivo(s) ignorado(s) — só leio ${EXTENSOES_ACEITAS.join(', ')}:\n\n`
            + recusados.slice(0, 10).map((f) => f.name).join('\n')
            + (recusados.length > 10 ? `\n… e mais ${recusados.length - 10}` : ''));
    }
    if (!aceitos.length) return;
    setBusy(true); setResumo(null); setProgresso(null);
    try {
      if (aceitos.length === 1) {
        const { data } = await modelosAPI.analisar(aceitos[0]);
        setFila([data]);
      } else {
        // Em remessas: 36 arquivos numa requisição só não chegam ao servidor —
        // o proxy corta por tamanho ou por tempo, e o erro não diz qual foi.
        const remessas = emRemessas(aceitos);
        naoEnviados.current.clear();
        const partes = [];
        let feitos = 0;
        setProgresso({ feitos: 0, total: aceitos.length });
        for (const remessa of remessas) {
          // Falhou? Divide ao meio e tenta cada metade. O limite que derruba a
          // requisição depende dos arquivos, e assim não é preciso adivinhá-lo.
          const resultados = await enviarComDivisao(
            remessa,
            async (lista) => {
              try {
                const { data } = await modelosAPI.lote(lista);
                return data;
              } catch (err) {
                const e = new Error('falhou');
                e.mensagem = mensagemDeErro(err, 'Falhou ao enviar');
                throw e;
              }
            },
            (n) => { feitos += n; setProgresso({ feitos, total: aceitos.length }); },
          );
          partes.push(...resultados);
          // Guarda os File dos que não entraram, para o botão de tentar de novo.
          for (const r of resultados) {
            if (!r.erro) continue;
            for (const nome of r.nomes || []) {
              const f = remessa.find((x) => x.name === nome);
              if (f) naoEnviados.current.set(nome, f);
            }
          }
        }
        const data = juntarResultados(partes);
        setResumo(data);
        setFila(data.revisar || []);
        if (data.resumo.salvos) await carregar();  // já mostra os salvos automaticamente
      }
    } catch (err) {
      alert(mensagemDeErro(err, 'Não consegui ler os arquivos.'));
    } finally { setBusy(false); setProgresso(null); }
  };

  const onDrop = (ev) => { ev.preventDefault(); setDragOver(false); processar(ev.dataTransfer.files); };

  // Confere o identificador digitado contra o texto extraído do documento.
  const conferencia = conferirIdentificador(form?.identificador, atual?.texto_extraido);
  // Nome da obrigação escolhida agora: é o que separa "variação do mesmo
  // documento" de "conflito com outra obrigação".
  const nomeObrigacaoEscolhida =
    obrigacoes.find((o) => String(o.id) === String(form?.obrigacao_id))?.nome || '';

  // Abre um modelo salvo no mesmo formulário da revisão. O texto extraído não é
  // devolvido na listagem, então a conferência do identificador fica sem base —
  // e dizer isso é melhor do que checar contra vazio e acusar que "não está no
  // documento".
  const editar = (m) => {
    setEditandoId(m.id);
    setResumo(null);
    setFila([{
      nome_arquivo: m.nome_arquivo, cnpj: m.cnpj,
      razao_social_extraida: m.razao_social_extraida,
      empresa_id: m.empresa_id, obrigacao_sugerida_id: m.obrigacao_id,
      tipo_documento: m.tipo_documento, competencia_exemplo: m.competencia_exemplo,
      protocolo_exemplo: m.protocolo_exemplo, texto_extraido: null,
      candidatos: [], identificador_atual: m.identificador,
    }]);
    setForm({
      nome_arquivo: m.nome_arquivo, cnpj: m.cnpj || '',
      razao_social_extraida: m.razao_social_extraida || '',
      empresa_id: m.empresa_id || '', obrigacao_id: m.obrigacao_id || '',
      tipo_documento: m.tipo_documento || 'outro',
      identificador: m.identificador || '',
      competencia_exemplo: m.competencia_exemplo || '',
      protocolo_exemplo: m.protocolo_exemplo || '',
      texto_extraido: null,
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const salvar = async () => {
    setBusy(true);
    try {
      const corpo = { ...form, empresa_id: form.empresa_id || null,
                      obrigacao_id: form.obrigacao_id || null };
      if (editandoId) {
        await modelosAPI.update(editandoId, corpo);
        setEditandoId(null);
      } else {
        await modelosAPI.create(corpo);
      }
      setFila((f) => f.slice(1));
      await carregar();
    } catch (err) {
      alert(mensagemDeErro(err, 'Erro ao salvar o modelo.'));
    } finally { setBusy(false); }
  };

  const pular = () => { setEditandoId(null); setFila((f) => f.slice(1)); };

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
        todos entram na fila com a sugestão já preenchida. Ao salvar, o identificador treina o e-validador —
        por isso cada um passa pela sua conferência antes.
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

      {/* Progresso das remessas. Sem isto, 36 arquivos em grupos de 5 parecem
          uma tela travada por quase um minuto. */}
      {progresso && (
        <div className="card mb-6">
          <p className="text-sm text-gray-700 mb-2">
            Lendo os documentos… <strong>{progresso.feitos}</strong> de {progresso.total}
          </p>
          <div className="h-2 rounded-full bg-gray-200 overflow-hidden">
            <div className="h-full bg-primary-500 transition-all duration-300"
                 style={{ width: `${Math.round((progresso.feitos / progresso.total) * 100)}%` }} />
          </div>
        </div>
      )}

      {/* Resumo do lote */}
      {resumo && (
        <div className="card mb-6">
          <div className="flex flex-wrap gap-2 mb-3">
            {resumo.resumo.salvos > 0 && (
              <span className="px-3 py-1 rounded-full text-sm bg-green-100 text-green-700">
                Salvos: {resumo.resumo.salvos}
              </span>
            )}
            <span className="px-3 py-1 rounded-full text-sm bg-amber-100 text-amber-700">
              Para conferir: {resumo.resumo.revisar}
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

          {atual.motivo === 'Reconhecido — confira e salve' ? (
            <div className="mb-4 text-xs bg-green-50 text-green-800 rounded-lg px-3 py-2">
              ✓ Empresa e obrigação reconhecidas. Confira o identificador — é ele que treina o
              e-validador — e salve.
            </div>
          ) : atual.motivo && (
            <div className="mb-4 text-xs bg-amber-50 text-amber-700 rounded-lg px-3 py-2 flex items-center gap-1">
              <AlertTriangle size={13} /> {atual.motivo}
            </div>
          )}
          {/* Item cuja remessa não chegou ao servidor: não há CNPJ, texto nem
              candidatos para revisar — o formulário abaixo só produziria a
              recusa "documento sem CNPJ nem razão social". O que cabe é
              reenviar o arquivo. */}
          {atual.erro && (
            <div className="mb-4 bg-red-50 text-red-700 rounded-lg px-3 py-3">
              <p className="text-sm font-medium">Este arquivo não chegou a ser lido.</p>
              <p className="text-xs mt-1">{atual.erro}</p>
              <div className="flex gap-2 mt-2">
                {naoEnviados.current.has(atual.nome_arquivo) && (
                  <button type="button" className="btn-secondary text-xs"
                    onClick={() => processar([naoEnviados.current.get(atual.nome_arquivo)])}>
                    Tentar este de novo
                  </button>
                )}
                <button type="button" className="btn-secondary text-xs"
                  onClick={() => setFila((f) => f.slice(1))}>
                  Pular
                </button>
              </div>
            </div>
          )}

          <div className={`grid md:grid-cols-2 gap-4 ${atual.erro ? 'hidden' : ''}`}>
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
                Identificador — um trecho que EXISTE no documento
              </label>
              <p className="text-xs text-gray-500 mb-1">
                É o texto que o e-validador vai procurar dentro do arquivo para saber que ele é
                deste tipo. Não é uma descrição: copie um título ou cabeçalho escrito no documento.
              </p>
              <input className={`input-field ${
                conferencia.estado === 'nao_achou' ? 'border-red-400' :
                conferencia.estado === 'volatil' ? 'border-amber-400' :
                conferencia.estado === 'achou' ? 'border-green-500' : ''}`}
                value={form.identificador}
                onChange={(e) => setForm({ ...form, identificador: e.target.value })}
                placeholder="ex.: Apuração do IRPJ e CSLL" />
              {/* O erro aqui é silencioso: identificador que não está no texto
                  nunca casa, e a descoberta vem meses depois. */}
              {conferencia.aviso && (
                <p className={`text-xs mt-1 ${
                  conferencia.estado === 'nao_achou' ? 'text-red-700' : 'text-amber-700'}`}>
                  {conferencia.aviso}
                </p>
              )}
              {conferencia.estado === 'achou' && (
                <p className="text-xs mt-1 text-green-700">✓ Encontrei este trecho no documento.</p>
              )}
              {atual.candidatos?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {atual.candidatos.map((c, i) => {
                    // Parecer com a PRÓPRIA obrigação não é colisão: é o segundo
                    // layout do mesmo documento (Lucro Real e Presumido caindo
                    // na mesma apuração). Só outra obrigação é problema.
                    const { estado, outras } = estadoDoCandidato(c, nomeObrigacaoEscolhida);
                    // Candidato com valor ou data dentro casa só com ESTE
                    // arquivo. O sistema sugere assim quando o documento não
                    // tem título limpo, e clicar sem reparar é fácil.
                    const movel = trechoMovel(c.texto);
                    const cor = estado === 'conflito' || movel
                      ? 'border-amber-300 bg-amber-50 text-amber-700'
                      : estado === 'variacao'
                        ? 'border-blue-200 bg-blue-50 text-blue-700'
                        : 'border-gray-200 bg-gray-50 text-gray-600 hover:border-primary-400';
                    return (
                      <button key={i} type="button"
                        onClick={() => setForm({ ...form, identificador: c.texto })}
                        className={`text-xs rounded-full px-2 py-1 border ${cor}`}
                        title={movel
                          ? `Contém ${movel}: casaria só com este arquivo.`
                          : explicar(estado, outras)}>
                        {c.texto}{estado === 'conflito' || movel ? ' ⚠' : ''}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          <div className={`flex items-center gap-3 mt-5 ${atual.erro ? 'hidden' : ''}`}>
            <button onClick={salvar} disabled={busy} className="btn-primary">
              {busy ? 'Salvando…' : editandoId ? 'Salvar alteração' : 'Salvar modelo'}
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
                    <td className="text-right whitespace-nowrap">
                      <button onClick={() => editar(m)} className="text-gray-400 hover:text-primary-700 mr-2"
                        title="Editar este modelo">
                        <Pencil size={16} />
                      </button>
                      <button onClick={() => excluir(m.id)} className="text-gray-400 hover:text-red-600"
                        title="Remover — o identificador sai da obrigação junto">
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
