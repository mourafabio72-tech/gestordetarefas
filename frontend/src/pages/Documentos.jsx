import { useState, useEffect } from 'react';
import { documentosAPI, tarefasAPI, empresasAPI, setoresAPI, usuariosAPI, obrigacoesAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { formatarRazaoSocial } from './razaoSocial';
import { filtrosVazios, paraConsulta, temFiltroAtivo, periodos, dataBr, paraCSV, EXTENSOES }
  from './filtroDocumentos';
import { FileArchive, Search, Paperclip, Download, AlertTriangle, FileDown } from 'lucide-react';

// Mesmo desenho da barra de filtros de Tarefas: rótulo fixo por cima, borda
// verde quando o campo está filtrando. Duas telas de consulta que se parecem
// custam menos de aprender do que duas que cada uma inventa a sua.
const ctrl = (ativo) =>
  `w-full h-8 px-2 text-xs border rounded-md bg-[#fffdf9] outline-none transition-colors
   focus:ring-2 focus:ring-primary-400 focus:border-transparent ${
     ativo ? 'border-primary-400 text-primary-800 font-medium' : 'border-gray-300 text-gray-800'}`;

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

export default function Documentos() {
  const [filtros, setFiltros] = useState(filtrosVazios());
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const [empresas, setEmpresas] = useState([]);
  const [setores, setSetores] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [obrigacoes, setObrigacoes] = useState([]);
  const [competencias, setCompetencias] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const [e, s, u, o, c] = await Promise.all([
          empresasAPI.list(), setoresAPI.list(), usuariosAPI.list(),
          obrigacoesAPI.list(), documentosAPI.competencias(),
        ]);
        setEmpresas(e.data); setSetores(s.data); setUsuarios(u.data);
        setObrigacoes(o.data); setCompetencias(c.data);
      } catch (err) { console.error(err); }
      buscar(filtrosVazios());
    })();
  }, []);

  const buscar = async (f = filtros) => {
    setCarregando(true); setErro(null);
    try {
      const { data } = await documentosAPI.list(paraConsulta(f));
      setDados(data);
    } catch (err) {
      setErro(mensagemDeErro(err, 'Erro ao consultar os documentos'));
    } finally { setCarregando(false); }
  };

  const set = (k, v) => setFiltros((f) => ({ ...f, [k]: v }));
  const limpar = () => { const vazio = filtrosVazios(); setFiltros(vazio); buscar(vazio); };
  const aplicarPeriodo = (p) => {
    const novo = { ...filtros, entrega_de: p.de, entrega_ate: p.ate };
    setFiltros(novo); buscar(novo);
  };

  const abrir = async (doc, baixar = false) => {
    try {
      const { data } = await tarefasAPI.anexo(doc.tarefa_id, baixar);
      const url = URL.createObjectURL(data);
      if (baixar) {
        const a = document.createElement('a');
        a.href = url; a.download = doc.arquivo; a.click();
      } else {
        window.open(url, '_blank', 'noopener');
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (err) {
      let texto = '';
      try { texto = JSON.parse(await err?.response?.data?.text()).detail; } catch { /* não era JSON */ }
      alert(texto || mensagemDeErro(err, 'Não foi possível abrir o comprovante'));
    }
  };

  // O CSV é do que está NA TELA, não da consulta inteira: exportar o que a
  // pessoa não viu esconderia o corte de resultados dentro do arquivo.
  const exportar = () => {
    const csv = '﻿' + paraCSV(dados?.documentos || []);   // BOM: Excel abre com acento certo
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url; a.download = 'documentos.csv'; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  };

  const ativo = temFiltroAtivo(filtros);
  const docs = dados?.documentos || [];

  return (
    <div>
      <div className="flex justify-between items-start gap-4 mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Documentos</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Os comprovantes que baixaram tarefas. Aqui se procura pelo documento, sem saber de qual tarefa veio.
          </p>
        </div>
        <button onClick={exportar} disabled={!docs.length}
          className="btn-secondary flex items-center gap-2 shrink-0 disabled:opacity-40">
          <FileDown size={18} /> Exportar CSV
        </button>
      </div>

      <div className="mb-5 rounded-xl border border-gray-200 p-3" style={{ background: '#faf7f0' }}>
        <div className="flex flex-wrap items-end gap-x-3 gap-y-2">
          <Campo rotulo="Buscar" dica="Nome da tarefa, protocolo ou nome do arquivo" largura="flex-[2] min-w-[160px]">
            <input type="search" value={filtros.texto} onChange={(e) => set('texto', e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && buscar()}
              placeholder="tarefa, protocolo ou arquivo" className={ctrl(filtros.texto)} />
          </Campo>
          {[
            { chave: 'empresa_id', rotulo: 'Empresa', vazio: 'Todas', largura: 'flex-[2] min-w-[150px]',
              opcoes: empresas.map((e) => ({ v: e.id, t: formatarRazaoSocial(e.razao_social) })) },
            { chave: 'obrigacao_id', rotulo: 'Obrigação', vazio: 'Todas', largura: 'flex-1 min-w-[130px]',
              opcoes: obrigacoes.map((o) => ({ v: o.id, t: o.mininome || o.nome })) },
            { chave: 'setor_id', rotulo: 'Setor', vazio: 'Todos', largura: 'flex-1 min-w-[110px]',
              opcoes: setores.map((s) => ({ v: s.id, t: s.nome })) },
            { chave: 'usuario_id', rotulo: 'Colaborador', vazio: 'Todos', largura: 'flex-1 min-w-[130px]',
              dica: 'Responsável ou supervisor da tarefa',
              opcoes: usuarios.filter((u) => !u.bloqueado).map((u) => ({ v: u.id, t: u.nome })) },
          ].map((f) => (
            <Campo key={f.chave} rotulo={f.rotulo} dica={f.dica} largura={f.largura}>
              <select value={filtros[f.chave]} onChange={(e) => set(f.chave, e.target.value)}
                className={ctrl(filtros[f.chave])}>
                <option value="">{f.vazio}</option>
                {f.opcoes.map((o) => <option key={o.v} value={o.v}>{o.t}</option>)}
              </select>
            </Campo>
          ))}
        </div>

        <div className="mt-2.5 flex flex-wrap items-end gap-x-3 gap-y-2">
          <Campo rotulo="Competência" dica="Mês do fato gerador" largura="w-[124px]">
            <select value={filtros.competencia} onChange={(e) => set('competencia', e.target.value)}
              className={ctrl(filtros.competencia)}>
              <option value="">Todas</option>
              {competencias.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Campo>
          <Campo rotulo="Entregue de" largura="w-[130px]">
            <input type="date" value={filtros.entrega_de} onChange={(e) => set('entrega_de', e.target.value)}
              className={ctrl(filtros.entrega_de)} />
          </Campo>
          <Campo rotulo="até" largura="w-[130px]">
            <input type="date" value={filtros.entrega_ate} onChange={(e) => set('entrega_ate', e.target.value)}
              className={ctrl(filtros.entrega_ate)} />
          </Campo>
          <Campo rotulo="Atalhos" largura="shrink-0">
            <div className="flex h-8">
              {periodos().map((p, i, arr) => (
                <button key={p.rotulo} type="button" onClick={() => aplicarPeriodo(p)}
                  className={`h-8 px-2.5 text-[11px] font-medium border whitespace-nowrap transition
                    ${i === 0 ? 'rounded-l-md' : '-ml-px'} ${i === arr.length - 1 ? 'rounded-r-md' : ''}
                    ${filtros.entrega_de === p.de && filtros.entrega_ate === p.ate
                      ? 'bg-primary-100 border-primary-400 text-primary-800 relative z-10'
                      : 'bg-white border-gray-300 text-gray-600 hover:border-primary-300'}`}>
                  {p.rotulo}
                </button>
              ))}
            </div>
          </Campo>
          <Campo rotulo="Tipo" largura="w-[124px]">
            <select value={filtros.extensao} onChange={(e) => set('extensao', e.target.value)}
              className={ctrl(filtros.extensao)}>
              {EXTENSOES.map((e) => <option key={e.valor} value={e.valor}>{e.rotulo}</option>)}
            </select>
          </Campo>

          <div className="ml-auto flex items-center gap-2 pb-0.5">
            {ativo && (
              <button type="button" onClick={limpar}
                className="text-[11px] text-gray-500 underline hover:text-gray-700 whitespace-nowrap">
                Limpar
              </button>
            )}
            <button type="button" onClick={() => buscar()} disabled={carregando}
              className="btn-primary flex items-center gap-2 h-8 text-xs">
              <Search size={15} /> {carregando ? 'Buscando…' : 'Buscar'}
            </button>
          </div>
        </div>
      </div>

      {erro && <div className="mb-4 px-4 py-3 rounded-lg text-sm bg-red-50 text-red-700">{erro}</div>}

      {dados && (
        <>
          <p className="text-xs text-gray-500 mb-2">
            <strong className="text-gray-700">{dados.mostrando}</strong> documento(s)
            {dados.cortou && <> de <strong className="text-gray-700">{dados.total}</strong></>}
            {/* Corte declarado: uma lista truncada em silêncio faria a pessoa
                concluir que o resto não existe. */}
            {dados.cortou && (
              <span className="text-amber-700"> — a consulta passa de {dados.limite} linhas.
                Estreite os filtros para ver o resto.</span>
            )}
          </p>

          {docs.length === 0 ? (
            <div className="card text-center py-12">
              <FileArchive size={48} className="mx-auto text-gray-300 mb-4" />
              <p className="text-gray-500">Nenhum documento encontrado</p>
              {ativo && (
                <button type="button" onClick={limpar} className="mt-2 text-xs text-primary-700 underline">
                  Limpar os filtros
                </button>
              )}
            </div>
          ) : (
            <div className="card overflow-x-auto">
              <table className="table-app">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-gray-500">
                    <th>Empresa</th><th>Obrigação</th><th>Tarefa</th>
                    <th className="whitespace-nowrap">Comp.</th>
                    <th className="whitespace-nowrap">Entrega</th>
                    <th>Protocolo</th><th>Arquivo</th><th className="px-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map((d) => (
                    <tr key={d.tarefa_id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="max-w-[220px] truncate" title={d.empresa}>{d.empresa}</td>
                      <td className="text-gray-600">{d.obrigacao || '—'}</td>
                      <td className="max-w-[200px] truncate" title={d.titulo}>{d.titulo}</td>
                      <td className="tabular-nums whitespace-nowrap">{d.competencia || '—'}</td>
                      <td className="tabular-nums whitespace-nowrap">{dataBr(d.data_entrega) || '—'}</td>
                      <td className="max-w-[160px] truncate text-gray-600" title={d.protocolo}>{d.protocolo || '—'}</td>
                      <td className="max-w-[200px] truncate" title={d.arquivo}>
                        {d.no_volume ? d.arquivo : (
                          <span className="inline-flex items-center gap-1 text-amber-700"
                            title="O arquivo não está mais no armazenamento — some ao restaurar backup sem o volume.">
                            <AlertTriangle size={12} /> {d.arquivo}
                          </span>
                        )}
                      </td>
                      <td className="px-2 whitespace-nowrap">
                        <button onClick={() => abrir(d)} disabled={!d.no_volume} title="Ver"
                          className="p-1 rounded hover:bg-[#e7eef6] disabled:opacity-30" style={{ color: '#2f6fb0' }}>
                          <Paperclip size={14} />
                        </button>
                        <button onClick={() => abrir(d, true)} disabled={!d.no_volume} title="Baixar"
                          className="p-1 rounded hover:bg-[#e2ebde] disabled:opacity-30" style={{ color: '#566450' }}>
                          <Download size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
