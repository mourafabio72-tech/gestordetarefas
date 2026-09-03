import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { painelAPI, empresasAPI, setoresAPI, usuariosAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { formatarRazaoSocial } from './razaoSocial';
import { SITUACOES, DIMENSOES, percentuais, linhasMapa, barras, arcosRosca, diaMes,
  pontualidade, haQuantosDias, roscasPorLinha, urlTarefas, fundoDoTom, corDoSetor, TONS,
  filtrosVazios, paraConsulta, temFiltroAtivo } from './painelDados';
import { AlertTriangle, Inbox, Send, Flame,
  BarChart3, AlignLeft, PieChart } from 'lucide-react';

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

// Cada número é uma porta para a lista, não um enfeite: quem lê "2 atrasadas"
// quer ver QUAIS são as duas. O recorte viaja na URL e a tela de Tarefas abre
// já filtrada pelo mesmo critério que o painel usou para contar.
function CardNum({ valor, texto, tom = 'base', icone: Icone, titulo, para }) {
  if (!valor) return null;
  const cor = (TONS[tom] || TONS.base).forte;
  const corpo = (
    <>
      <span className="flex items-baseline gap-1">
        <strong className="text-xl tabular-nums leading-none" style={{ color: cor }}>{valor}</strong>
        {Icone && <Icone size={12} style={{ color: cor }} />}
      </span>
      <span className="block text-[10px] leading-tight mt-0.5" style={{ color: '#55614e' }}>{texto}</span>
    </>
  );
  const base = 'min-w-[88px] px-2.5 py-2 rounded-lg border';
  const estilo = { background: fundoDoTom(tom), borderColor: (TONS[tom] || TONS.base).suave || '#e6dfd0' };
  return para ? (
    <Link to={para} title={titulo || `Ver ${texto}`} style={estilo}
      className={`${base} hover:shadow-sm hover:brightness-[0.985] transition`}>
      {corpo}
    </Link>
  ) : (
    // Sem link quando não há lista equivalente para abrir — melhor um cartão
    // parado que um link que leva ao lugar errado.
    <span className={base} style={estilo} title={titulo}>{corpo}</span>
  );
}

// O número do miolo cresce com a contagem, e o buraco da rosca não: com 4
// dígitos em fonte fixa o total encostava no anel e a rosca virava moldura de
// número. A fonte passa a sair do vão que existe, não de um palpite.
function fonteDoCentro(centro, raio, largura) {
  const vao = (raio - largura / 2) * 2 * 0.78;
  const chars = String(centro ?? '').length || 1;
  return Math.min(26, Math.round(vao / (chars * 0.62)));
}

// Só o desenho, para servir à rosca grande da faixa e às pequenas por setor.
function Donut({ fatias, centro, legenda, tamanho = 84, raio = 42, largura = 16, anel = null }) {
  const arcos = arcosRosca(fatias, raio);
  return (
    <svg viewBox="0 0 120 120" style={{ width: tamanho, height: tamanho }} className="shrink-0">
      {anel && <circle cx="60" cy="60" r={raio + largura / 2 + 3} fill="none"
        stroke={anel} strokeWidth="3" />}
      <g transform="rotate(-90 60 60)">
        <circle cx="60" cy="60" r={raio} fill="none" stroke="#eee8db" strokeWidth={largura} />
        {arcos.map((a) => (
          <circle key={a.chave} cx="60" cy="60" r={raio} fill="none" stroke={a.cor}
            strokeWidth={largura} strokeDasharray={`${a.dash} ${a.gap}`} strokeDashoffset={a.offset}>
            <title>{`${a.rotulo}: ${a.valor} (${a.pct}%)`}</title>
          </circle>
        ))}
      </g>
      <text x="60" y={legenda ? 58 : 66} textAnchor="middle" className="fill-gray-800"
        style={{ fontSize: fonteDoCentro(centro, raio, largura), fontWeight: 700 }}>{centro}</text>
      {legenda && (
        <text x="60" y="75" textAnchor="middle" className="fill-gray-500" style={{ fontSize: 12 }}>
          {legenda}
        </text>
      )}
    </svg>
  );
}

function Rosca({ fatias, centro, legenda }) {
  return (
    <div className="flex items-center gap-2.5 shrink-0">
      <Donut fatias={fatias} centro={centro} legenda={legenda} />
      <div className="space-y-px">
        {fatias.filter((f) => f.valor > 0).map((f) => (
          <div key={f.chave} className="flex items-center gap-1.5 text-[10px] text-gray-600">
            <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: f.cor }} />
            <span className="w-[72px]">{f.rotulo}</span>
            <strong className="tabular-nums w-9 text-right">{f.valor}</strong>
            <span className="text-gray-400 tabular-nums">{f.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Três dimensões em abas, não três blocos empilhados: a mesma pergunta ("onde
// dói") lida por setor, por pessoa e por cliente, sem triplicar a altura.
function GraficoComAbas({ dados }) {
  const [dim, setDim] = useState('por_setor');
  const [modo, setModo] = useState('pizza');
  const [tudo, setTudo] = useState(false);
  const itens = dados[dim] || [];
  const corte = (l) => (tudo ? l : l.slice(0, 10));
  const nomeDe = (n) => (dim === 'por_empresa' ? formatarRazaoSocial(n) : n);
  // A etiqueta de cor só vale para setor: em colaborador e empresa a lista é
  // longa e aberta, e cor demais deixa de distinguir.
  const etiqueta = (n) => (dim === 'por_setor'
    ? <span className="w-2 h-2 rounded-full shrink-0" style={{ background: corDoSetor(n) }} />
    : null);
  const linhasBarra = corte(barras(itens));
  const linhasMapaV = corte(linhasMapa(itens));
  const roscas = corte(roscasPorLinha(itens));

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
        {/* Os dois modos respondem a perguntas diferentes: a barra empilhada
            compara VOLUME entre linhas, a barra por situação compara a
            COMPOSIÇÃO de cada linha. Em vez de escolher por você, um clique. */}
        <div className="ml-auto flex items-center gap-0.5">
          {[{ v: 'pizza', Icone: PieChart, t: 'Pizza — uma por linha' },
            { v: 'barras', Icone: BarChart3, t: 'Barra empilhada — volume entre linhas' },
            { v: 'mapa', Icone: AlignLeft, t: 'Barra por situação — composição da linha' }].map(({ v, Icone, t }) => (
            <button key={v} type="button" onClick={() => setModo(v)} title={t}
              className={`p-1.5 rounded-md transition-colors ${
                modo === v ? 'bg-primary-100 text-primary-800' : 'text-gray-400 hover:bg-gray-100'}`}>
              <Icone size={14} />
            </button>
          ))}
        </div>
      </div>

      {itens.length === 0 && <p className="text-sm text-gray-500">Nada a mostrar com esses filtros.</p>}

      {modo === 'pizza' && itens.length > 0 && (
        /* Uma pizza por linha. A rosca mostra composição e só isso — duas do
           mesmo diâmetro não dizem qual tem mais trabalho —, por isso o total
           fica no miolo de cada uma. */
        /* Grade que se estica: com o quadro ocupando a largura toda, uma fila
           encostada à esquerda deixava meio metro de vazio à direita. As
           colunas se dividem o espaço, e sobra vira tamanho, não buraco. */
        <div className="grid gap-y-4 justify-items-center"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
          {roscas.map((r) => (
            <div key={r.nome} className="flex flex-col items-center gap-1.5">
              {/* Anel externo na cor do setor: a rosca por dentro continua
                  contando situação, e a borda diz de quem ela é. */}
              <Donut fatias={r.fatias} centro={r.total} tamanho={132} raio={44} largura={19}
                anel={dim === 'por_setor' ? corDoSetor(r.nome) : null} />
              <span className={`text-xs text-center leading-tight flex items-center gap-1.5 max-w-[140px] ${
                r.derivado ? 'italic text-gray-500' : 'text-gray-700'}`} title={nomeDe(r.nome)}>
                {etiqueta(r.nome)}<span className="truncate">{nomeDe(r.nome)}</span>
              </span>
              {r.multa > 0 && (
                <span className="text-[10px] tabular-nums" style={{ color: '#a24a3a' }}
                  title={`${r.multa} em aberto geram multa`}>⚠{r.multa}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {modo === 'barras' && itens.length > 0 && (
        <div className="space-y-1.5">
          {linhasBarra.map((l) => (
            <div key={l.nome} className="flex items-center gap-2">
              <span className="w-32 shrink-0 text-xs truncate text-gray-700 flex items-center gap-1.5"
                title={nomeDe(l.nome)}>
                {etiqueta(l.nome)}<span className="truncate">{nomeDe(l.nome)}</span>
              </span>
              <div className="flex-1 h-5 rounded bg-[#f3efe6] overflow-hidden">
                {/* Largura = volume ante o maior; divisão interna = composição. */}
                <div className="flex h-full rounded overflow-hidden" style={{ width: `${l.largura}%` }}>
                  {l.segmentos.map((sg) => (
                    <div key={sg.chave} style={{ width: `${sg.pct}%`, background: sg.cor }}
                      title={`${sg.rotulo}: ${sg.valor}`} />
                  ))}
                </div>
              </div>
              <span className="w-9 shrink-0 text-right text-xs tabular-nums text-gray-600">{l.total}</span>
              <span className="w-8 shrink-0 text-right text-[11px] tabular-nums" style={{ color: '#a24a3a' }}
                title={l.multa ? `${l.multa} em aberto geram multa` : ''}>
                {l.multa > 0 ? `⚠${l.multa}` : ''}
              </span>
            </div>
          ))}
        </div>
      )}

      {modo === 'mapa' && itens.length > 0 && (
        <div className="space-y-1.5">
          {/* Cabeçalho das colunas: cinco barrinhas sem rótulo obrigariam a
              conferir a cor na legenda a cada leitura. */}
          <div className="flex items-center gap-2">
            <span className="w-32 shrink-0" />
            <div className="flex gap-2 flex-1">
              {SITUACOES.map((sg) => (
                <div key={sg.chave} className="flex-1 flex items-center gap-1">
                  <span className="flex-1 text-[9px] uppercase tracking-wide text-gray-400 truncate">
                    {sg.curto}
                  </span>
                  <span className="w-5 shrink-0" />
                </div>
              ))}
            </div>
            <span className="w-9 shrink-0 text-right text-[9px] uppercase tracking-wide text-gray-400">
              Total
            </span>
            <span className="w-8 shrink-0" />
          </div>
          {linhasMapaV.map((l) => (
            <div key={l.nome} className="flex items-center gap-2">
              <span className="w-32 shrink-0 text-xs truncate text-gray-700 flex items-center gap-1.5"
                title={nomeDe(l.nome)}>
                {etiqueta(l.nome)}<span className="truncate">{nomeDe(l.nome)}</span>
              </span>
              {/* Uma barrinha por situação, comprimento relativo À LINHA: é o
                  que torna setor de 8 tarefas e setor de 300 comparáveis
                  quanto ao que os aflige. Antes isto era cor de célula, e cor
                  se estima; barra se mede. */}
              <div className="flex gap-2 flex-1">
                {l.celulas.map((c) => (
                  <div key={c.chave} className="flex-1 flex items-center gap-1"
                    title={`${c.rotulo}: ${c.valor}`}>
                    <div className="flex-1 h-3.5 rounded-sm bg-[#f0ece3] overflow-hidden">
                      <div className="h-full rounded-sm"
                        style={{ width: `${Math.round(c.intensidade * 100)}%`, background: c.cor }} />
                    </div>
                    <span className="w-5 shrink-0 text-[10px] tabular-nums text-right"
                      style={{ color: c.valor ? '#55614e' : '#c3bda9' }}>
                      {c.valor || '·'}
                    </span>
                  </div>
                ))}
              </div>
              <span className="w-9 shrink-0 text-right text-xs tabular-nums text-gray-500">{l.total}</span>
              <span className="w-8 shrink-0 text-right text-[11px] tabular-nums" style={{ color: '#a24a3a' }}
                title={l.multa ? `${l.multa} em aberto geram multa` : ''}>
                {l.multa > 0 ? `⚠${l.multa}` : ''}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center gap-3 mt-3 pt-2 border-t border-gray-100 flex-wrap">
        {SITUACOES.map((sg) => (
          <span key={sg.chave} className="flex items-center gap-1 text-[10px] text-gray-500">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ background: sg.cor }} /> {sg.rotulo}
          </span>
        ))}
        {dim === 'por_colaborador' && (
          <span className="text-[10px] text-gray-400">tarefa dividida conta para cada um</span>
        )}
        {itens.some((i) => i.derivado) && (
          <span className="text-[10px] text-gray-400 italic">
            Cliente repete tarefas já contadas nos setores
          </span>
        )}
        {itens.length > 10 && (
          <button onClick={() => setTudo(!tudo)}
            className="ml-auto text-[11px] text-gray-500 underline hover:text-gray-700">
            {tudo ? 'só as 10 primeiras' : `mostrar todas as ${itens.length}`}
          </button>
        )}
      </div>
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

  if (erro) return <div className="px-4 py-3 rounded-lg text-sm bg-red-50 text-red-700">{erro}</div>;
  if (!dados) return <div className="flex items-center justify-center h-64">Carregando…</div>;

  const r = dados.resumo;
  const fatias = percentuais(r);
  const emAberto = r.atrasada + r.pendente + r.em_andamento;
  const pont = pontualidade(r);
  const link = (recorte) => urlTarefas(filtros, recorte);

  return (
    // Teto de largura: em monitor largo o conteúdo esticava de ponta a ponta e
    // o olho tinha de atravessar meio metro entre um número e o seguinte.
    <div className="space-y-3 max-w-[1180px]">
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
      <div className="card flex flex-wrap items-center gap-x-5 gap-y-3 py-3">
        <Rosca fatias={fatias} centro={emAberto} legenda={`de ${r.total}`} />
        <div className="flex flex-wrap gap-1.5">
          <CardNum valor={emAberto} texto="em aberto" tom="base"
            para={link({ alerta: 'aberta' })} titulo="Tudo que ainda não foi concluído nem cancelado" />
          <CardNum valor={r.atrasada} texto={r.atrasada > 1 ? 'atrasadas' : 'atrasada'} tom="atrasada"
            para={link({ alerta: 'atrasada' })} titulo="Passou do prazo interno" />
          <CardNum valor={r.vence_hoje} texto="vence hoje" tom="hoje"
            para={link({ alerta: 'hoje' })} />
          <CardNum valor={r.vence_semana} texto="a vencer em 7 dias" tom="a_vencer"
            para={link({ alerta: 'semana' })} titulo="Vence de hoje até daqui a 7 dias" />
          <CardNum valor={r.urgentes} texto="urgentes" tom="urgente" icone={Flame}
            para={link({ alerta: 'aberta', prioridade: 'alta_urgente' })}
            titulo="Em aberto com prioridade alta ou urgente" />
          <CardNum valor={r.multa} texto="geram multa" tom="atrasada" icone={AlertTriangle}
            para={link({ alerta: 'aberta', multa: '1' })}
            titulo="Em aberto cuja obrigação gera multa se perder o prazo" />
          <CardNum valor={r.aguardando_cliente} texto="esperam doc." tom="base" icone={Inbox}
            titulo="Sem o documento que o cliente precisa enviar — some na coluna Cliente do gráfico" />
          <CardNum valor={r.nao_abertas} texto="não abertas" tom="base" icone={Send}
            titulo="Enviado ao cliente e ainda não baixado — some na coluna Cliente do gráfico" />
          {pont && (
            <span className="min-w-[86px] px-2.5 py-1.5 rounded-lg border border-transparent"
              title={`${pont.dentro} de ${pont.base} concluídas dentro do prazo interno`}>
              <strong className="text-lg tabular-nums leading-none"
                style={{ color: pont.pct >= 90 ? '#4d8a3f' : pont.pct >= 70 ? '#8a6a2e' : '#a24a3a' }}>
                {pont.pct}%
              </strong>
              <span className="block text-[10px] text-gray-500 leading-tight mt-0.5">no prazo</span>
            </span>
          )}
        </div>
      </div>

      <GraficoComAbas dados={dados} />

      {/* Tabela, não mais grupos com seta. A seta escondia justamente o que se
          procura aqui — qual tarefa, de quem, para quando —, e obrigava a
          abrir setor por setor para varrer a semana. O setor virou coluna. */}
      <div className="card py-3">
        <div className="flex items-baseline gap-2 mb-2">
          <h2 className="text-sm font-semibold text-gray-800">Próximas do vencimento</h2>
          <span className="text-[11px] text-gray-400">
            {dados.abertas_total} em aberto com prazo
          </span>
        </div>
        {dados.proximas.length === 0 ? (
          <p className="text-xs text-gray-500">Nada em aberto com prazo definido.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wide text-gray-400
                               border-b border-gray-200">
                  <th className="py-1.5 pr-2 font-semibold">Tarefa</th>
                  <th className="py-1.5 px-2 font-semibold w-[74px]">Prazo</th>
                  <th className="py-1.5 px-2 font-semibold w-[86px]">Vencimento</th>
                  <th className="py-1.5 px-2 font-semibold w-[26%]">Empresa</th>
                  <th className="py-1.5 px-2 font-semibold w-[110px]">Setor</th>
                  <th className="py-1.5 pl-2 font-semibold w-[150px]">Analista</th>
                </tr>
              </thead>
              <tbody>
                {dados.proximas.map((t) => (
                  <tr key={t.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                    <td className="py-1.5 pr-2 text-gray-700">
                      <span className="flex items-center gap-1">
                        <span className="truncate" title={t.titulo}>{t.titulo}</span>
                        {t.multa && (
                          <AlertTriangle size={10} style={{ color: '#a24a3a' }} title="Gera multa" />
                        )}
                      </span>
                    </td>
                    {/* Prazo interno e vencimento legal são datas diferentes, e
                        é a diferença entre elas que dá o fôlego: atrasou aqui
                        dentro mas ainda dá tempo de entregar ao Fisco. */}
                    <td className="py-1.5 px-2 tabular-nums"
                      style={{ color: t.atrasada ? '#a24a3a' : '#55614e' }}>
                      {diaMes(t.data_prazo)}
                    </td>
                    <td className="py-1.5 px-2 tabular-nums text-gray-500">
                      {diaMes(t.data_vencimento) || '—'}
                    </td>
                    <td className="py-1.5 px-2 text-gray-600">
                      <span className="block truncate" title={formatarRazaoSocial(t.empresa)}>
                        {formatarRazaoSocial(t.empresa)}
                      </span>
                    </td>
                    <td className="py-1.5 px-2 text-gray-500">
                      {/* Mesma cor do gráfico: quem viu a pizza do Fiscal acha
                          as linhas do Fiscal aqui sem ler coluna nenhuma. */}
                      <span className="flex items-center gap-1.5 min-w-0" title={t.setor}>
                        <span className="w-2 h-2 rounded-full shrink-0"
                          style={{ background: corDoSetor(t.setor) }} />
                        <span className="truncate">{t.setor}</span>
                      </span>
                    </td>
                    <td className="py-1.5 pl-2 text-gray-500">
                      <span className="block truncate" title={t.responsaveis.join(', ')}>
                        {t.responsaveis.join(', ') || '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {dados.abertas_total > dados.proximas.length && (
              <p className="text-[10px] text-gray-400 mt-1.5">
                Mostrando as {dados.proximas.length} de prazo mais curto, de {dados.abertas_total}.{' '}
                <Link to={link({ alerta: 'aberta' })} className="underline">Ver todas em Tarefas</Link>
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
