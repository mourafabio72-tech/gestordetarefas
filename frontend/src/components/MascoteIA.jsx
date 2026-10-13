import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { X } from 'lucide-react';
import { iaAPI } from '../services/api';
import PergunteIA from './PergunteIA';
import { linkDaTarefa } from '../pages/pergunteIA.js';
import logoBps4 from '../assets/bps4-logo.png';
import './mascote.css';

// O MASCOTE DO PERGUNTE À IA (2026-10-13). O mesmo robô do TeamHub, pela nota
// "Mascote do assistente - robo com logo BPS4" (B03 Resources, CLAUDE_FABIO).
// Fica no canto de toda tela logada; o clique abre a caixa Pergunte à IA num
// painel flutuante. Só existe com a IA disponível: sem chave, nada aparece (o
// aviso para o admin cadastrar a chave continua na caixa do Painel).
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

export default function MascoteIA() {
  const navigate = useNavigate();
  const location = useLocation();
  const [disponivel, setDisponivel] = useState(false);
  const [aberto, setAberto] = useState(false);
  const [saudando, setSaudando] = useState(false);

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
    const fecharNoEsc = (e) => { if (e.key === 'Escape') setAberto(false); };
    document.addEventListener('keydown', fecharNoEsc);
    return () => document.removeEventListener('keydown', fecharNoEsc);
  }, [aberto]);

  if (!disponivel) return null;

  const abrir = () => { setSaudando(false); setAberto(true); };

  // Na própria tela de Tarefas o filtro nasce da URL só na montagem, então ali
  // a troca de endereço recarrega a página; nas outras, navega normal.
  const escolher = (t) => {
    setAberto(false);
    const link = linkDaTarefa(t);
    if (location.pathname === '/tarefas') window.location.assign(link);
    else navigate(link);
  };

  return (
    <>
      {aberto && (
        <div className="ia-painel-flutuante" role="dialog" aria-labelledby="iaMascoteTitulo">
          <div className="ia-painel-cab">
            <Robo className="rb-cab" />
            <h2 id="iaMascoteTitulo">Pergunte à IA</h2>
            <button type="button" onClick={() => setAberto(false)} aria-label="Fechar" className="ia-painel-x">
              <X size={18} />
            </button>
          </div>
          <PergunteIA aoEscolher={escolher} />
        </div>
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
