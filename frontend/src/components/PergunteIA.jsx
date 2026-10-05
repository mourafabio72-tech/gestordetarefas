import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, X, ChevronRight } from 'lucide-react';
import { iaAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { useAuth } from '../contexts/AuthContext';
import { EXEMPLOS, linkDaTarefa, resumoDaResposta, dataCurta } from '../pages/pergunteIA.js';

const SITUACAO = {
  pendente: 'pendente', em_andamento: 'em andamento', concluida: 'concluída',
  atrasada: 'atrasada', cancelada: 'cancelada',
};

// Caixa "Pergunte à IA" do topo do Painel e das Tarefas. A IA só traduz a
// pergunta em filtro; a lista vem do Tareffas, no escopo de quem perguntou.
// `aoEscolher` troca a navegação: na própria tela de Tarefas, mudar a URL não
// refaz o filtro, então ela aplica direto.
export default function PergunteIA({ aoEscolher }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [texto, setTexto] = useState('');
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');
  const [resp, setResp] = useState(null);

  useEffect(() => {
    iaAPI.status().then(({ data }) => setStatus(data)).catch(() => setStatus({ disponivel: false }));
  }, []);

  if (!status) return null;
  if (!status.disponivel) {
    // Só o admin pode resolver; para os outros a caixa simplesmente não existe.
    if (user?.grupo !== 'admin') return null;
    return (
      <p className="text-xs text-gray-500 flex items-center gap-1.5">
        <Sparkles size={14} className="text-primary-700" />
        Pergunte à IA está desligado.{' '}
        <Link to="/inteligencia-artificial" className="underline text-primary-700">Cadastrar a chave</Link>
      </p>
    );
  }

  const perguntar = async (pergunta) => {
    const p = (pergunta ?? texto).trim();
    if (!p || carregando) return;
    setTexto(p); setCarregando(true); setErro(''); setResp(null);
    try {
      const { data } = await iaAPI.perguntar(p);
      setResp(data);
    } catch (e) {
      setErro(mensagemDeErro(e, 'Não consegui responder agora.'));
    } finally { setCarregando(false); }
  };

  const escolher = (t) => (aoEscolher ? aoEscolher(t) : navigate(linkDaTarefa(t)));
  const limpar = () => { setResp(null); setErro(''); setTexto(''); };

  return (
    <section className="rounded-xl border border-[#d9d2bf] bg-[#fffdf9] px-3 py-2.5" aria-label="Pergunte à IA">
      <form onSubmit={(e) => { e.preventDefault(); perguntar(); }} className="flex items-center gap-2">
        <Sparkles size={18} className="text-primary-700 shrink-0" aria-hidden="true" />
        <label htmlFor="pergunte-ia" className="sr-only">Pergunte à IA</label>
        <input id="pergunte-ia" value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={300}
          placeholder="Pergunte à IA" className="input-field flex-1 min-w-0" />
        <button type="submit" className="btn-primary shrink-0" disabled={carregando || !texto.trim()}>
          {carregando ? 'Pensando...' : 'Perguntar'}
        </button>
        {(resp || erro) && (
          <button type="button" onClick={limpar} className="p-1.5 text-gray-500 hover:text-gray-800" title="Limpar resposta">
            <X size={16} />
          </button>
        )}
      </form>

      {!resp && !erro && !carregando && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {EXEMPLOS.map((ex) => (
            <button key={ex} type="button" onClick={() => perguntar(ex)}
              className="text-xs px-2.5 py-1 rounded-full border border-[#d9d2bf] text-gray-600 hover:bg-[#f3eedf]">
              {ex}
            </button>
          ))}
        </div>
      )}

      <div aria-live="polite">
        {erro && <p className="text-sm text-[#a24a3a] mt-2">{erro}</p>}
        {resp && (
          <div className="mt-2">
            <p className="text-xs text-gray-500">Entendi: {resp.entendi}</p>
            {resp.ignorados?.length > 0 && (
              <p className="text-xs text-gray-400">Parte da pergunta não virou filtro. Se faltar algo, pergunte de outro jeito.</p>
            )}
            {resp.contar ? (
              <p className="text-sm text-gray-800 mt-1"><span className="text-2xl font-bold mr-1.5">{resp.total}</span>
                {resp.total === 1 ? 'tarefa' : 'tarefas'}</p>
            ) : (
              <p className="text-sm font-medium text-gray-800 mt-1">{resumoDaResposta(resp)}</p>
            )}
            {resp.tarefas.length > 0 && (
              <ul className="mt-1.5 max-h-72 overflow-y-auto divide-y divide-[#ece6d6] rounded-lg border border-[#ece6d6] bg-white">
                {resp.tarefas.map((t) => (
                  <li key={t.id}>
                    <button type="button" onClick={() => escolher(t)}
                      className="w-full text-left px-3 py-2 hover:bg-[#faf7f0] flex items-center gap-3">
                      <span className="flex-1 min-w-0">
                        <span className="block text-sm text-gray-800 truncate">{t.titulo}</span>
                        <span className="block text-xs text-gray-500 truncate">
                          {[t.empresa, t.setor, SITUACAO[t.status]].filter(Boolean).join(' · ')}
                        </span>
                      </span>
                      <span className="text-xs text-gray-600 text-right shrink-0">
                        {t.data_prazo && <span className="block">prazo {dataCurta(t.data_prazo)}</span>}
                        {t.data_vencimento && <span className="block text-gray-400">venc. {dataCurta(t.data_vencimento)}</span>}
                      </span>
                      <ChevronRight size={16} className="text-gray-400 shrink-0" aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
