import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { painelAPI, empresasAPI, setoresAPI, usuariosAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { formatarRazaoSocial } from './razaoSocial';
import { SITUACOES, percentuais, linhasMapa, diaMes, filtrosVazios, paraConsulta, temFiltroAtivo }
  from './painelDados';
import { AlertTriangle, ChevronDown, ChevronRight, Users, Layers } from 'lucide-react';

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

function Mapa({ titulo, icone: Icone, linhas, vazio }) {
  if (!linhas.length) return null;
  const maior = Math.max(...linhas.map((l) => l.total), 1);
  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-1.5">
        <Icone size={15} className="text-gray-400" /> {titulo}
      </h2>
      <div className="space-y-1.5">
        {linhas.map((l) => (
          <div key={l.nome} className="flex items-center gap-2">
            <span className="w-32 shrink-0 text-xs truncate text-gray-700" title={l.nome}>{l.nome}</span>
            {/* Cada célula é uma situação; a cor satura conforme o peso DELA na
                linha, para setor pequeno e grande serem comparáveis. */}
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
            <span className="w-10 shrink-0 text-right text-xs tabular-nums text-gray-500">{l.total}</span>
            {l.multa > 0 && (
              <span className="w-8 shrink-0 text-right text-[11px] tabular-nums text-red-700"
                title={`${l.multa} em aberto geram multa`}>⚠{l.multa}</span>
            )}
            {l.multa === 0 && <span className="w-8 shrink-0" />}
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-3 mt-3 pt-2 border-t border-gray-100">
        {SITUACOES.map((s) => (
          <span key={s.chave} className="flex items-center gap-1 text-[10px] text-gray-500">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ background: s.cor }} /> {s.rotulo}
          </span>
        ))}
      </div>
      {vazio}
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

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Painel</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            O que está em aberto agora, por setor e por colaborador.
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
          {r.atrasada > 0 && (
            <Link to="/tarefas" className="text-sm hover:underline" style={{ color: '#a24a3a' }}>
              <strong className="text-xl tabular-nums">{r.atrasada}</strong> atrasada{r.atrasada > 1 ? 's' : ''}
            </Link>
          )}
          {r.vence_hoje > 0 && (
            <span className="text-sm" style={{ color: '#b4622c' }}>
              <strong className="text-xl tabular-nums">{r.vence_hoje}</strong> vence{r.vence_hoje > 1 ? 'm' : ''} hoje
            </span>
          )}
          <span className="text-sm text-gray-600">
            <strong className="text-xl tabular-nums">{r.vence_semana}</strong> na semana
          </span>
          {r.multa > 0 && (
            <span className="text-sm flex items-center gap-1" style={{ color: '#a24a3a' }}
              title="Tarefas em aberto cuja obrigação gera multa se perder o prazo">
              <AlertTriangle size={15} />
              <strong className="text-xl tabular-nums">{r.multa}</strong> geram multa
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
        <Mapa titulo="Por setor" icone={Layers} linhas={linhasMapa(dados.por_setor)} />
        <Mapa titulo="Por colaborador" icone={Users} linhas={linhasMapa(dados.por_colaborador)}
          vazio={<p className="text-[10px] text-gray-400 mt-2">
            Tarefa com mais de um responsável conta para cada um, então a soma passa do total.
          </p>} />
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
                      <span className="ml-auto text-gray-400 truncate max-w-[40%]">
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
