import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { X, SendHorizontal, ChevronRight, Sparkles } from 'lucide-react';
import { iaAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { EXEMPLOS, linkDaTarefa, resumoDaResposta, dataCurta } from '../pages/pergunteIA.js';
import logoBps4 from '../assets/bps4-logo.png';
import './mascote.css';

// O MASCOTE DO PERGUNTE À IA (2026-10-13). O mesmo robô do TeamHub, pela nota
// "Mascote do assistente - robo com logo BPS4" (B03 Resources, CLAUDE_FABIO).
// Fica no canto de toda tela logada; o clique abre uma janela lateral de
// conversa, como a do TeamHub e a do FinHub (pedido do Fábio, 2026-10-13: "faz
// o mesmo no tareffas"). A pergunta vai ao mesmo /ia/perguntar da caixa antiga:
// a IA só traduz em filtro, e a lista vem do Tareffas, no escopo de quem
// pergunta. Só existe com a IA disponível: sem chave, nada aparece (o aviso
// para o admin cadastrar a chave continua no Painel).
// Cores e movimento em mascote.css; nenhuma cor mora aqui.

const CHAVE_SAUDOU = 'tareffas-ia-saudou';

export function Robo({ corpo = false, className = '' }) {
  return (
    <svg className={`rb ${className}`} viewBox={`0 0 64 ${corpo ? 98 : 58}`} aria-hidden="true" focusable="false">
      {corpo && <ellipse className="rb-chao" cx="32" cy="95" rx="20" ry="3" />}
      <g className={corpo ? 'rb-todo' : undefined}>
        {corpo && (
          <g className="rb-corpo">
            <rect className="rb-braco rb-braco-e" x="1" y="63" width="9" height="22" rx="4.5" />
            <rect className="rb-braco rb-braco-d" x="54" y="63" width="9" height="22" rx="4.5" />
            <rect className="rb-pescoco" x="26" y="53" width="12" height="7" rx="2" />
            <rect className="rb-cabeca" x="9" y="58" width="46" height="33" rx="13" />
            <ellipse className="rb-brilho" cx="20" cy="62.5" rx="6" ry="2" />
            <rect className="rb-peito" x="14" y="64" width="36" height="22" rx="8" />
            <image className="rb-logo" href={logoBps4} x="17" y="67" width="30" height="16.8"
              preserveAspectRatio="xMidYMid meet" />
          </g>
        )}
        <line className="rb-haste" x1="32" y1="5" x2="32" y2="15" />
        <circle className="rb-luz" cx="32" cy="5" r="4" />
        <rect className="rb-orelha" x="4" y="29" width="7" height="13" rx="3.5" />
        <rect className="rb-orelha" x="53" y="29" width="7" height="13" rx="3.5" />
        <rect className="rb-cabeca" x="9" y="14" width="46" height="42" rx="20" />
        <ellipse className="rb-brilho" cx="22" cy="20" rx="8" ry="3" />
        <rect className="rb-visor" x="15" y="24" width="34" height="23" rx="11.5" />
        <g className="rb-olhos">
          <circle className="rb-olho" cx="25" cy="33.5" r="3.6" />
          <circle className="rb-olho" cx="39" cy="33.5" r="3.6" />
        </g>
        <path className="rb-boca" d="M27 40.5 Q32 44 37 40.5" />
        <circle className="rb-bochecha" cx="18.5" cy="43" r="2.2" />
        <circle className="rb-bochecha" cx="45.5" cy="43" r="2.2" />
      </g>
    </svg>
  );
}

const SITUACAO = {
  pendente: 'pendente', em_andamento: 'em andamento', concluida: 'concluída',
  atrasada: 'atrasada', cancelada: 'cancelada',
};

// Uma resposta da IA na conversa: o "Entendi", a contagem ou o resumo, e a
// lista clicável. Todo texto entra como texto do React (nunca HTML).
function Resposta({ resp, aoEscolher }) {
  return (
    <>
      <p className="ia-entendi"><span className="ia-tag"><Sparkles size={11} aria-hidden="true" /> IA</span> {resp.entendi}</p>
      {resp.ignorados?.length > 0 && (
        <p className="ia-msg-sub">Parte da pergunta não virou filtro. Se faltar algo, pergunte de outro jeito.</p>
      )}
      {resp.contar ? (
        <p className="ia-contagem"><strong>{resp.total}</strong> {resp.total === 1 ? 'tarefa' : 'tarefas'}</p>
      ) : (
        <p className="ia-resumo">{resumoDaResposta(resp)}</p>
      )}
      {resp.tarefas?.length > 0 && (
        <ul className="ia-lista">
          {resp.tarefas.map((t) => (
            <li key={t.id}>
              <button type="button" onClick={() => aoEscolher(t)}>
                <span className="ia-lista-txt">
                  <span className="ia-lista-titulo">{t.titulo}</span>
                  <span className="ia-lista-sub">{[t.empresa, t.setor, SITUACAO[t.status]].filter(Boolean).join(' · ')}</span>
                </span>
                <span className="ia-lista-data">
                  {t.data_prazo && <span>prazo {dataCurta(t.data_prazo)}</span>}
                  {t.data_vencimento && <span className="ia-lista-venc">venc. {dataCurta(t.data_vencimento)}</span>}
                </span>
                <ChevronRight size={15} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export default function MascoteIA() {
  const navigate = useNavigate();
  const location = useLocation();
  const [disponivel, setDisponivel] = useState(false);
  const [aberto, setAberto] = useState(false);
  const [saudando, setSaudando] = useState(false);
  const [mensagens, setMensagens] = useState([]);   // {papel: 'pessoa'|'ia', texto?, resp?, erro?}
  const [texto, setTexto] = useState('');
  const [carregando, setCarregando] = useState(false);
  const conversaRef = useRef(null);
  const campoRef = useRef(null);

  useEffect(() => {
    iaAPI.status().then(({ data }) => setDisponivel(!!data?.disponivel)).catch(() => setDisponivel(false));
  }, []);

  // O "Oi!": uma vez por sessão do navegador; some sozinho em 9 s. Sem
  // sessionStorage (aba anônima, bloqueio), cumprimenta toda vez: nada quebra.
  useEffect(() => {
    if (!disponivel) return undefined;
    let saudou = false;
    try { saudou = sessionStorage.getItem(CHAVE_SAUDOU) === '1'; } catch { saudou = false; }
    if (saudou) return undefined;
    try { sessionStorage.setItem(CHAVE_SAUDOU, '1'); } catch { /* sem armazenamento, segue */ }
    const mostra = setTimeout(() => setSaudando(true), 1200);
    const esconde = setTimeout(() => setSaudando(false), 9000);
    return () => { clearTimeout(mostra); clearTimeout(esconde); };
  }, [disponivel]);

  useEffect(() => {
    if (!aberto) return undefined;
    campoRef.current?.focus();
    const fecharNoEsc = (e) => { if (e.key === 'Escape') setAberto(false); };
    document.addEventListener('keydown', fecharNoEsc);
    return () => document.removeEventListener('keydown', fecharNoEsc);
  }, [aberto]);

  useEffect(() => {
    const c = conversaRef.current;
    if (c) c.scrollTop = c.scrollHeight;
  }, [mensagens, carregando]);

  if (!disponivel) return null;

  const abrir = () => { setSaudando(false); setAberto(true); };

  const perguntar = async (pergunta) => {
    const p = (pergunta ?? texto).trim();
    if (!p || carregando) return;
    setTexto('');
    setMensagens((m) => [...m, { papel: 'pessoa', texto: p }]);
    setCarregando(true);
    try {
      const { data } = await iaAPI.perguntar(p);
      setMensagens((m) => [...m, { papel: 'ia', resp: data }]);
    } catch (e) {
      setMensagens((m) => [...m, { papel: 'ia', erro: mensagemDeErro(e, 'Não consegui responder agora.') }]);
    } finally {
      setCarregando(false);
      campoRef.current?.focus();
    }
  };

  // Na própria tela de Tarefas o filtro nasce da URL só na montagem, então ali
  // a troca de endereço recarrega a página; nas outras, navega normal. A
  // janela fica aberta, com a conversa, para a pessoa seguir perguntando.
  const escolher = (t) => {
    const link = linkDaTarefa(t);
    if (location.pathname === '/tarefas') window.location.assign(link);
    else navigate(link);
  };

  const cabeca = <Robo />;

  return (
    <>
      {aberto && (
        <aside className="ia-janela" aria-labelledby="iaJanelaTitulo">
          <div className="ia-janela-cab">
            <div>
              <h2 id="iaJanelaTitulo"><Robo className="rb-cab" /> Pergunte à IA</h2>
              <span className="ia-janela-sub">A IA traduz sua pergunta em filtro. A lista vem do Tareffas, no que você pode ver.</span>
            </div>
            <button type="button" onClick={() => setAberto(false)} aria-label="Fechar" className="ia-janela-x">
              <X size={18} />
            </button>
          </div>

          <div className="ia-janela-conversa" ref={conversaRef} aria-live="polite">
            {mensagens.length === 0 && (
              <div className="ia-janela-sugestoes">
                {EXEMPLOS.map((ex) => (
                  <button key={ex} type="button" onClick={() => perguntar(ex)}>{ex}</button>
                ))}
              </div>
            )}
            {mensagens.map((m, i) => (m.papel === 'pessoa' ? (
              <div key={i} className="ia-msg ia-msg-pessoa">{m.texto}</div>
            ) : (
              <div key={i} className="ia-linha">
                {cabeca}
                <div className={`ia-msg ia-msg-ia${m.erro ? ' ia-msg-erro' : ''}`}>
                  {m.erro ? m.erro : <Resposta resp={m.resp} aoEscolher={escolher} />}
                </div>
              </div>
            )))}
            {carregando && (
              <div className="ia-linha">
                {cabeca}
                <div className="ia-msg ia-msg-ia ia-msg-pensando">Pensando...</div>
              </div>
            )}
          </div>

          <form className="ia-janela-entrada" onSubmit={(e) => { e.preventDefault(); perguntar(); }}>
            <label htmlFor="iaJanelaTexto" className="sr-only">Sua pergunta</label>
            <textarea id="iaJanelaTexto" ref={campoRef} rows={2} maxLength={300} value={texto}
              placeholder="Escreva sua pergunta" onChange={(e) => setTexto(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); perguntar(); } }} />
            <button type="submit" className="ia-janela-enviar" disabled={carregando || !texto.trim()} aria-label="Enviar">
              <SendHorizontal size={18} />
            </button>
          </form>
          <p className="ia-janela-nota">Clique numa tarefa para abri-la. A conversa fica aqui enquanto a página estiver aberta.</p>
        </aside>
      )}
      {!aberto && (
        <div className="ia-mascote">
          {saudando && (
            <button type="button" className="ia-saudacao" onClick={abrir}>Oi! Quer saber algo das tarefas?</button>
          )}
          <button type="button" className="ia-mascote-botao" onClick={abrir}
            aria-label="Abrir o Pergunte à IA" title="Pergunte à IA sobre as tarefas">
            <Robo corpo className="rb-flutua" />
          </button>
        </div>
      )}
    </>
  );
}
