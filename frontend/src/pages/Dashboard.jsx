import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { painelAPI, empresasAPI, setoresAPI, usuariosAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { formatarRazaoSocial } from './razaoSocial';
import { SITUACOES, DIMENSOES, percentuais, linhasMapa, diaMes, pontualidade,
  haQuantosDias, filtrosVazios, paraConsulta, temFiltroAtivo } from './painelDados';
import { AlertTriangle, ChevronDown, ChevronRight, Inbox, Send, Flame } from 'lucide-react';

const ctrl = (ativo) =>
  `w-full h-8 px-2 text-xs border rounded-md bg-[#fffdf9] outline-none transition-colors
   focus:ring-2 focus:ring-primary-400 focus:border-transparent ${
     ativo ? 'border-primary-400 text-primary-800 font-medium' : 'border-gray-300 text-gray-800'}`;

function Campo({ rotulo, largura = '', children }) {
  return (
    <label className={`flex flex-col gap-1 ${largura}`}>
      <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 whitespace-nowrap text-center">
        {rotulo}
      </span>
      {children}
    </label>
  );
}

function Numero({ valor, texto, cor, icone: Icone, titulo, para }) {
  if (!valor) return null;
  const corpo = (
    <>
      {Icone && <Icone size={14} />}
      <strong className="text-xl tabular-nums">{valor}</strong> {texto}
    </>
  );
  const classe = 'text-sm flex items-center gap-1';
  return para
    ? <Link to={para} className={`${classe} hover:underline`} style={{ color: cor }} title={titulo}>{corpo}</Link>
    : <span className={classe} style={{ color: cor }} title={titulo}>{corpo}</span>;
}

// Uma barra só, com as situações lado a lado. Substitui a rosca: em rosca,
// comparar duas fatias exige girar a cabeça, e o número que interessa — quantas
// atrasadas — ficava numa legenda ao lado.
function Barra({ dados }) {
  const total = dados.reduce((s, d) => s + d.valor, 0);
  if (!total) return <div className="h-2 rounded-full bg-gray-200" />;
  return (
    <div className="flex h-2 rounded-full overflow-hidden">
      {dados.filter((d) => d.valor > 0).map((d) => (
        <div key={d.chave} style={{ width: `${d.pct}%`, background: d.cor }}
          title={`${d.rotulo}: ${d.valor} (${d.pct}%)`} />
      ))}
    </div>
  );
}

// Três dimensões em abas, não três blocos empilhados: a mesma pergunta ("onde
// dói") lida por setor, por pessoa e por cliente, sem triplicar a altura.
function MapaComAbas({ dados }) {
  const [dim, setDim] = useState('por_setor');
  const [tudo, setTudo] = useState(false);
  const linhas = linhasMapa(dados[dim] || []);
  const mostradas = tudo ? linhas : linhas.slice(0, 10);
  const nomeDe = (n) => (dim === 'por_empresa' ? formatarRazaoSocial(n) : n);

  return (
    <div className="card">
      <div className="flex items-center gap-1 mb-3">
        {DIMENSOES.map((d) => (
          <button key={d.chave} type="button" onClick={() => { setDim(d.chave); setTudo(false); }}
            className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
              dim === d.chave ? 'bg-primary-100 text-primary-800 font-semibold'
                              : 'text-gray-500 hover:bg-gray-100'}`}>
            {d.rotulo}
          </button>
        ))}
        <span className="ml-auto text-[10px] text-gray-400">
          {dim === 'por_colaborador' ? 'tarefa dividida conta para cada um' : `${linhas.length} linhas`}
        </span>
      </div>

      {linhas.length === 0 ? <p className="text-sm text-gray-500">Nada a mostrar com esses filtros.</p> : (
        <div className="space-y-1.5">
          {mostradas.map((l) => (
            <div key={l.nome} className="flex items-center gap-2">
              <span className="w-32 shrink-0 text-xs truncate text-gray-700" title={nomeDe(l.nome)}>
                {nomeDe(l.nome)}
              </span>
              {/* Cada célula é uma situação; a cor satura conforme o peso DELA
                  na linha, para cliente pequeno e grande serem comparáveis. */}
              <div className="flex gap-0.5 flex-1">
                {l.celulas.map((c) => (
                  <div key={c.chave} title={`${c.rotulo}: ${c.valor}`}
                    className="flex-1 h-6 rounded flex items-center justify-center text-[10px] font-medium"
                    style={{
                      background: c.valor ? c.cor : '#f0ece3',
                      opacity: c.valor ? 0.25 + c.intensidade * 0.75 : 1,
                      color: c.valor && c.intensidade > 0.45 ? '#fff' : '#55614e',
                    }}>
                    {c.valor || ''}
                  </div>
                ))}
              </div>
              <span className="w-9 shrink-0 text-right text-xs tabular-nums text-gray-500">{l.total}</span>
              <span className="w-8 shrink-0 text-right text-[11px] tabular-nums"
                style={{ color: '#a24a3a' }} title={l.multa ? `${l.multa} em aberto geram multa` : ''}>
                {l.multa > 0 ? `⚠${l.multa}` : ''}
              </span>
            </div>
          ))}
        </div>
      )}

      {linhas.length > 10 && (
        <button onClick={() => setTudo(!tudo)}
          className="mt-2 text-[11px] text-gray-500 underline hover:text-gray-700">
          {tudo ? 'mostrar só as 10 primeiras' : `mostrar todas as ${linhas.length}`}
        </button>
      )}

      <div className="flex flex-wrap gap-3 mt-3 pt-2 border-t border-gray-100">
        {SITUACOES.map((s) => (
          <span key={s.chave} className="flex items-center gap-1 text-[10px] text-gray-500">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ background: s.cor }} /> {s.rotulo}
          </span>
        ))}
      </div>
    </div>
  );
}

// As duas filas em que o escritório não avança sozinho.
function Empurrao({ aguardando, naoAbertas }) {
  const vazio = !aguardando.length && !naoAbertas.length;
  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-gray-800 mb-1">Depende de alguém</h2>
      <p className="text-[11px] text-gray-500 mb-3">
        Atraso aqui não se resolve trabalhando mais: se resolve cobrando.
      </p>

      {vazio && <p className="text-sm text-gray-500">Nada parado esperando o cliente.</p>}

      {aguardando.length > 0 && (
        <div className="mb-3">
          <h3 className="text-xs font-semibold text-gray-700 flex items-center gap-1.5 mb-1.5">
            <Inbox size={13} className="text-gray-400" />
            O documento não chegou
            <span className="text-gray-400 font-normal">{aguardando.length}</span>
          </h3>
          <ul className="space-y-1">
            {aguardando.map((t) => (
              <li key={t.id} className="flex items-center gap-2 text-xs">
                <span className="tabular-nums w-11 shrink-0"
                  style={{ color: t.atrasada ? '#a24a3a' : '#808a74' }}>{diaMes(t.data_prazo)}</span>
                <span className="truncate text-gray-700" title={t.titulo}>{t.titulo}</span>
                <span className="ml-auto text-gray-400 truncate max-w-[45%]"
                  title={formatarRazaoSocial(t.empresa)}>{formatarRazaoSocial(t.empresa)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {naoAbertas.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-700 flex items-center gap-1.5 mb-1.5">
            <Send size={13} className="text-gray-400" />
            Enviado e não aberto
            <span className="text-gray-400 font-normal">{naoAbertas.length}</span>
          </h3>
          {/* A guia entregue no prazo não protege ninguém se o cliente não
              baixou: quem leva a multa é ele, e a reclamação chega aqui. */}
          <ul className="space-y-1">
            {naoAbertas.map((t) => (
              <li key={t.id} className="flex items-center gap-2 text-xs">
                <span className="w-16 shrink-0 text-gray-500">{haQuantosDias(t.enviado_em)}</span>
                <span className="truncate text-gray-700" title={t.titulo}>{t.titulo}</span>
                <span className="ml-auto text-gray-400 truncate max-w-[45%]"
                  title={formatarRazaoSocial(t.empresa)}>{formatarRazaoSocial(t.empresa)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);
  const [filtros, setFiltros] = useState(filtrosVazios());
  const [empresas, setEmpresas] = useState([]);
  const [setores, setSetores] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [abertos, setAbertos] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const [e, s, u] = await Promise.all([empresasAPI.list(), setoresAPI.list(), usuariosAPI.list()]);
        setEmpresas(e.data); setSetores(s.data); setUsuarios(u.data);
      } catch { /* os filtros ficam vazios; o painel carrega mesmo assim */ }
    })();
  }, []);

  useEffect(() => { carregar(filtros); }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  const carregar = async (f) => {
    setErro(null);
    try {
      const { data } = await painelAPI.get(paraConsulta(f));
      setDados(data);
    } catch (err) {
      setErro(mensagemDeErro(err, 'Não foi possível carregar o painel'));
    }
  };

  const set = (k, v) => { const novo = { ...filtros, [k]: v }; setFiltros(novo); carregar(novo); };
  const limpar = () => { const v = filtrosVazios(); setFiltros(v); carregar(v); };
  const alternar = (setor) =>
    setAbertos((a) => (a.includes(setor) ? a.filter((x) => x !== setor) : [...a, setor]));

  if (erro) return <div className="px-4 py-3 rounded-lg text-sm bg-red-50 text-red-700">{erro}</div>;
  if (!dados) return <div className="flex items-center justify-center h-64">Carregando…</div>;

  const r = dados.resumo;
  const fatias = percentuais(r);
  const emAberto = r.atrasada + r.pendente + r.em_andamento;
  const pont = pontualidade(r);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Painel</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            O que está em aberto agora, por setor, por colaborador e por cliente.
          </p>
        </div>
        {temFiltroAtivo(filtros) && (
          <button onClick={limpar} className="text-[11px] text-gray-500 underline hover:text-gray-700">
            Limpar filtros
          </button>
        )}
      </div>

      <div className="rounded-xl border border-gray-200 p-3" style={{ background: '#faf7f0' }}>
        <div className="flex flex-wrap items-end gap-x-3 gap-y-2">
          {[
            { chave: 'empresa_id', rotulo: 'Empresa', vazio: 'Todas', largura: 'flex-[2] min-w-[150px]',
              opcoes: empresas.map((e) => ({ v: e.id, t: formatarRazaoSocial(e.razao_social) })) },
            { chave: 'setor_id', rotulo: 'Setor', vazio: 'Todos', largura: 'flex-1 min-w-[120px]',
              opcoes: setores.map((s) => ({ v: s.id, t: s.nome })) },
            { chave: 'usuario_id', rotulo: 'Colaborador', vazio: 'Todos', largura: 'flex-1 min-w-[130px]',
              opcoes: usuarios.filter((u) => !u.bloqueado).map((u) => ({ v: u.id, t: u.nome })) },
          ].map((f) => (
            <Campo key={f.chave} rotulo={f.rotulo} largura={f.largura}>
              <select value={filtros[f.chave]} onChange={(e) => set(f.chave, e.target.value)}
                className={ctrl(filtros[f.chave])}>
                <option value="">{f.vazio}</option>
                {f.opcoes.map((o) => <option key={o.v} value={o.v}>{o.t}</option>)}
              </select>
            </Campo>
          ))}
          <Campo rotulo="Competência" largura="w-[120px]">
            <input value={filtros.competencia} onChange={(e) => set('competencia', e.target.value)}
              placeholder="MM/AAAA" className={ctrl(filtros.competencia)} />
          </Campo>
          <label className="flex items-center gap-2 h-8 px-2 text-xs text-gray-700 cursor-pointer">
            <input type="checkbox" checked={filtros.so_multa}
              onChange={(e) => set('so_multa', e.target.checked)} className="h-4 w-4" />
            Só as que geram multa
          </label>
        </div>
      </div>

      {/* Uma faixa, não seis cartões. O que importa é a relação entre os
          números — quanto do que está aberto já atrasou —, e seis caixas
          grandes com um número cada obrigam a fazer essa conta de cabeça. */}
      <div className="card">
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2 mb-3">
          <span className="text-sm text-gray-600">
            <strong className="text-2xl text-gray-800 tabular-nums">{emAberto}</strong> em aberto
            <span className="text-gray-400"> de {r.total}</span>
          </span>
          <Numero valor={r.atrasada} texto={r.atrasada > 1 ? 'atrasadas' : 'atrasada'}
            cor="#a24a3a" para="/tarefas" />
          <Numero valor={r.vence_hoje} texto={r.vence_hoje > 1 ? 'vencem hoje' : 'vence hoje'} cor="#b4622c" />
          <Numero valor={r.vence_semana} texto="na semana" cor="#55614e" />
          <Numero valor={r.urgentes} texto="urgentes" cor="#8a3f2e" icone={Flame}
            titulo="Em aberto com prioridade alta ou urgente" />
          <Numero valor={r.multa} texto="geram multa" cor="#a24a3a" icone={AlertTriangle}
            titulo="Tarefas em aberto cuja obrigação gera multa se perder o prazo" />
          <Numero valor={r.aguardando_cliente} texto="esperam o cliente" cor="#7a6a3a" icone={Inbox}
            titulo="Em aberto sem o documento que o cliente precisa enviar" />
          <Numero valor={r.nao_abertas} texto="não abertas" cor="#7a6a3a" icone={Send}
            titulo="Documento enviado ao cliente e ainda não baixado" />
          {pont && (
            <span className="ml-auto text-sm text-gray-600"
              title={`${pont.dentro} de ${pont.base} concluídas dentro do prazo interno`}>
              <strong className="text-xl tabular-nums"
                style={{ color: pont.pct >= 90 ? '#4d8a3f' : pont.pct >= 70 ? '#8a6a2e' : '#a24a3a' }}>
                {pont.pct}%
              </strong> no prazo
            </span>
          )}
        </div>
        <Barra dados={fatias} />
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
          {fatias.filter((f) => f.valor > 0).map((f) => (
            <span key={f.chave} className="flex items-center gap-1 text-[11px] text-gray-600">
              <span className="w-2.5 h-2.5 rounded-sm" style={{ background: f.cor }} />
              {f.rotulo} <strong className="tabular-nums">{f.valor}</strong>
              <span className="text-gray-400">{f.pct}%</span>
            </span>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <MapaComAbas dados={dados} />
        <Empurrao aguardando={dados.aguardando || []} naoAbertas={dados.nao_abertas || []} />
      </div>

      {/* Por setor, com o detalhe atrás de uma seta: a lista corrida de 30
          tarefas empurrava tudo para baixo e não respondia "qual setor está
          pior", que é a pergunta de quem abre o painel. */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-800 mb-3">Próximas do vencimento</h2>
        {dados.proximas.length === 0 ? (
          <p className="text-sm text-gray-500">Nada em aberto com prazo definido.</p>
        ) : dados.proximas.map((g) => {
          const aberto = abertos.includes(g.setor);
          return (
            <div key={g.setor} className="border-b border-gray-100 last:border-0">
              <button type="button" onClick={() => alternar(g.setor)}
                className="w-full flex items-center gap-2 py-2 text-left hover:bg-gray-50 rounded">
                {aberto ? <ChevronDown size={15} className="text-gray-400" />
                        : <ChevronRight size={15} className="text-gray-400" />}
                <span className="text-sm font-medium text-gray-800">{g.setor}</span>
                <span className="text-xs text-gray-500">{g.total}</span>
                {g.atrasadas > 0 && (
                  <span className="text-[11px] px-1.5 py-0.5 rounded-full"
                    style={{ background: '#f6ded7', color: '#a24a3a' }}>
                    {g.atrasadas} atrasada{g.atrasadas > 1 ? 's' : ''}
                  </span>
                )}
              </button>
              {aberto && (
                <ul className="pb-2 pl-7 space-y-1">
                  {g.tarefas.map((t) => (
                    <li key={t.id} className="flex items-center gap-2 text-xs">
                      <span className="tabular-nums w-11 shrink-0"
                        style={{ color: t.atrasada ? '#a24a3a' : '#808a74' }}>{diaMes(t.data_prazo)}</span>
                      <span className="truncate text-gray-700" title={t.titulo}>{t.titulo}</span>
                      {t.multa && <AlertTriangle size={11} style={{ color: '#a24a3a' }} title="Gera multa" />}
                      <span className="text-gray-400 truncate max-w-[28%]"
                        title={formatarRazaoSocial(t.empresa)}>{formatarRazaoSocial(t.empresa)}</span>
                      <span className="ml-auto text-gray-400 truncate max-w-[30%]">
                        {t.responsaveis.join(', ')}
                      </span>
                    </li>
                  ))}
                  {g.total > g.tarefas.length && (
                    <li className="text-[11px] text-gray-400">
                      …e mais {g.total - g.tarefas.length}. Veja em Tarefas.
                    </li>
                  )}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
