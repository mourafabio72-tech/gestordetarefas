import { useState, useEffect } from 'react';
import { documentosAPI, tarefasAPI, empresasAPI, setoresAPI, usuariosAPI, obrigacoesAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { formatarRazaoSocial } from './razaoSocial';
import { filtrosVazios, paraConsulta, temFiltroAtivo, periodos, dataBr, dataHoraBr, paraCSV, EXTENSOES }
  from './filtroDocumentos';
import { FileArchive, Search, Paperclip, Download, AlertTriangle, FileDown,
         Inbox, Send, CheckCircle2, Clock, Trash2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

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
  const { user } = useAuth();
  // Quem apaga é decidido no cadastro de Grupos, pela flag `apagar_anexo`. O
  // botão nem aparece para quem não tem — mas quem chamar a API direto leva 403
  // do mesmo jeito: esconder na tela é conveniência, não é a trava.
  const podeApagar = Boolean(user?.permissoes_efetivas?.apagar_anexo);
  const [confirmando, setConfirmando] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [acessos, setAcessos] = useState(null);   // { doc, linhas }
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
      const { data } = filtros.tipo === 'entregues'
        ? await tarefasAPI.saida(doc.tarefa_id, baixar)
        : await tarefasAPI.anexo(doc.tarefa_id, baixar);
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
    const csv = '\ufeff' + paraCSV(dados?.documentos || [], filtros.tipo);   // BOM: Excel abre com acento certo
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url; a.download = `documentos-${filtros.tipo}.csv`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  };

  // Duas etapas, não um confirm(): o primeiro clique arma a lixeira, o segundo
  // apaga. Documento apagado não volta, e diálogo do navegador se aceita no
  // reflexo. Passa o efeito em 4 segundos, para a lixeira não ficar armada.
  const excluir = async (doc) => {
    if (confirmando !== doc.tarefa_id) {
      setConfirmando(doc.tarefa_id);
      setTimeout(() => setConfirmando((c) => (c === doc.tarefa_id ? null : c)), 4000);
      return;
    }
    setConfirmando(null);
    try {
      const { data } = await tarefasAPI.excluirDocumento(doc.tarefa_id,
        filtros.tipo === 'entregues' ? 'entregue' : 'recebido');
      // A reabertura é efeito colateral e precisa ser dita: sem isso, a tarefa
      // reaparece na fila de alguém e ninguém liga uma coisa à outra.
      setAviso(data?.tarefa_reaberta
        ? `“${doc.titulo}” voltou para pendente — era este documento que a concluía.`
        : 'Documento excluído.');
      setTimeout(() => setAviso(null), 8000);
      buscar();
    } catch (err) {
      setErro(mensagemDeErro(err, 'Não foi possível excluir o documento'));
    }
  };

  // Quem abriu, quando e por qual link. O contador diz quantas vezes; isto diz
  // de quem foi cada uma — o sócio que paga ou o e-mail geral que ninguém lê.
  const verAcessos = async (doc) => {
    setAcessos({ doc, linhas: null });
    try {
      const { data } = await tarefasAPI.acessos(doc.tarefa_id);
      setAcessos({ doc, linhas: data });
    } catch (err) {
      setAcessos(null);
      setErro(mensagemDeErro(err, 'Não foi possível ler as aberturas'));
    }
  };

  const ativo = temFiltroAtivo(filtros);
  const docs = dados?.documentos || [];

  return (
    <div>
      <div className="flex justify-between items-start gap-4 mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Documentos</h1>
          {/* O subtítulo segue a aba: na de entregues, falar em "comprovantes
              que baixaram tarefas" descreve o acervo errado. */}
          <p className="text-xs text-gray-500 mt-0.5">
            {filtros.tipo === 'entregues'
              ? 'As guias e documentos que o escritório entregou. Mostra se o cliente abriu o link.'
              : 'Os comprovantes que baixaram tarefas. Aqui se procura pelo documento, sem saber de qual tarefa veio.'}
          </p>
        </div>
        <button onClick={exportar} disabled={!docs.length}
          className="btn-secondary flex items-center gap-2 shrink-0 disabled:opacity-40">
          <FileDown size={18} /> Exportar CSV
        </button>
      </div>

      {/* Dois acervos, não um. O que o cliente MANDOU e o que o escritório
          ENTREGOU respondem perguntas diferentes, e a coluna "arquivo"
          significaria coisas distintas em linhas vizinhas se fossem uma lista só. */}
      <div className="flex gap-1 mb-3">
        {[
          { valor: 'recebidos', rotulo: 'Recebidos do cliente', icone: Inbox },
          { valor: 'entregues', rotulo: 'Entregues ao cliente', icone: Send },
        ].map((t) => (
          <button key={t.valor} type="button"
            onClick={() => { const novo = { ...filtros, tipo: t.valor, baixado: '' }; setFiltros(novo); buscar(novo); }}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors
              ${filtros.tipo === t.valor
                ? 'bg-primary-100 border-primary-400 text-primary-800'
                : 'bg-white border-gray-300 text-gray-600 hover:border-primary-300'}`}>
            <t.icone size={14} /> {t.rotulo}
          </button>
        ))}
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
          {filtros.tipo === 'entregues' && (
            <Campo rotulo="O cliente pegou?" dica="A pergunta do fim do mês" largura="w-[150px]">
              <select value={filtros.baixado} onChange={(e) => set('baixado', e.target.value)}
                className={ctrl(filtros.baixado)}>
                <option value="">Tanto faz</option>
                <option value="nao">Ainda não baixou</option>
                <option value="sim">Já baixou</option>
              </select>
            </Campo>
          )}
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
      {aviso && <div className="mb-4 px-4 py-3 rounded-lg text-sm bg-amber-50 text-amber-800">{aviso}</div>}

      {/* Detalhe das aberturas. Fica num painel e não numa coluna porque são
          várias linhas por documento, com nome, horário e o que NÃO contou. */}
      {acessos && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
             onClick={() => setAcessos(null)}>
          <div className="bg-white rounded-xl w-full max-w-2xl max-h-[80vh] overflow-y-auto"
               onClick={(e) => e.stopPropagation()}>
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Aberturas do documento</h2>
              <p className="text-sm text-gray-500 mt-1">
                {acessos.doc.titulo} · {acessos.doc.empresa}
              </p>
            </div>
            <div className="p-4">
              {!acessos.linhas ? <p className="text-sm text-gray-500">Carregando…</p> : (
                <table className="table-app">
                  <thead>
                    <tr className="border-b border-gray-200 text-left text-gray-500">
                      <th>Quem</th><th>Quando</th><th>Contou?</th><th>Origem</th>
                    </tr>
                  </thead>
                  <tbody>
                    {acessos.linhas.map((a, i) => (
                      <tr key={i} className="border-b border-gray-100">
                        <td>
                          {a.quem ? (
                            <>
                              {a.quem}
                              <span className="block text-[11px] text-gray-500">{a.endereco}</span>
                            </>
                          ) : <span className="text-gray-400">link antigo, sem dono</span>}
                        </td>
                        <td className="tabular-nums whitespace-nowrap">{dataHoraBr(a.quando)}</td>
                        <td className="whitespace-nowrap">
                          {a.contado
                            ? <span className="text-green-700">contou</span>
                            : <span className="text-gray-500">
                                {a.robo ? 'prévia do app' : 'mesma abertura'}
                              </span>}
                        </td>
                        <td className="text-[11px] text-gray-400 max-w-[220px] truncate"
                            title={a.user_agent}>{a.ip}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {acessos.linhas?.length === 0 && (
                <p className="text-sm text-gray-500">Ninguém abriu ainda.</p>
              )}
              <button onClick={() => setAcessos(null)} className="btn-secondary w-full mt-3">Fechar</button>
            </div>
          </div>
        </div>
      )}

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
                    {filtros.tipo === 'entregues' ? (
                      <><th className="whitespace-nowrap">O cliente pegou?</th><th>Aberturas</th></>
                    ) : (
                      <><th className="whitespace-nowrap">Entrega</th><th>Protocolo</th></>
                    )}
                    <th>Arquivo</th><th className="px-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map((d) => (
                    <tr key={d.tarefa_id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="max-w-[220px] truncate" title={d.empresa}>{d.empresa}</td>
                      <td className="text-gray-600">{d.obrigacao || '—'}</td>
                      <td className="max-w-[200px] truncate" title={d.titulo}>{d.titulo}</td>
                      <td className="tabular-nums whitespace-nowrap">{d.competencia || '—'}</td>
                      {filtros.tipo === 'entregues' ? (
                        <>
                          <td className="whitespace-nowrap">
                            {d.downloads ? (
                              <span className="inline-flex items-center gap-1 text-green-700">
                                <CheckCircle2 size={13} /> {dataBr(d.baixado_em) || 'sim'}
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-amber-700">
                                <Clock size={13} /> ainda não
                              </span>
                            )}
                          </td>
                          <td className="tabular-nums text-gray-600">
                            {d.downloads ? (
                              <button type="button" onClick={() => verAcessos(d)}
                                className="underline hover:text-primary-700" title="Ver quem abriu e quando">
                                {d.downloads}×
                              </button>
                            ) : '—'}
                          </td>
                        </>
                      ) : (
                        <>
                          <td className="tabular-nums whitespace-nowrap">{dataBr(d.data_entrega) || '—'}</td>
                          <td className="max-w-[160px] truncate text-gray-600" title={d.protocolo}>{d.protocolo || '—'}</td>
                        </>
                      )}
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
                        {podeApagar && (
                          <button onClick={() => excluir(d)}
                            title={confirmando === d.tarefa_id
                              ? 'Clique de novo para excluir de vez — a tarefa volta a pendente'
                              : 'Excluir este documento (reabre a tarefa)'}
                            className={`p-1 rounded transition-colors ${
                              confirmando === d.tarefa_id
                                ? 'bg-red-600 text-white'
                                : 'hover:bg-[#f7e7e3] text-[#a24a3a]'}`}>
                            <Trash2 size={14} />
                          </button>
                        )}
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
