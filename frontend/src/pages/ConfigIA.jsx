import { useEffect, useState } from 'react';
import { Sparkles, Save, PlugZap, ShieldCheck } from 'lucide-react';
import { configuracaoAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';

// Chaves de IA (OpenAI e NVIDIA) e o provedor do "Pergunte à IA".
// A chave nunca volta do servidor: a tela só sabe se ela está guardada, e
// campo vazio no salvar mantém a que já existe.
const PROVEDORES = [
  { id: 'openai', nome: 'OpenAI', chave: 'openai_api_key', modelo: 'openai_model',
    phChave: 'sk-...', phModelo: 'gpt-4o-mini', onde: 'platform.openai.com, em API keys' },
  { id: 'nvidia', nome: 'NVIDIA', chave: 'nvidia_api_key', modelo: 'nvidia_model',
    phChave: 'nvapi-...', phModelo: 'nvidia/llama-3.1-nemotron-70b-instruct', onde: 'build.nvidia.com, em Get API Key' },
];
const CAMPOS = ['ia_provedor', 'openai_api_key', 'openai_model', 'nvidia_api_key', 'nvidia_model'];

export default function ConfigIA() {
  const [cfg, setCfg] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [testando, setTestando] = useState('');
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    configuracaoAPI.getNotificacoes()
      .then(({ data }) => setCfg(data))
      .catch((e) => setMsg({ ok: false, txt: mensagemDeErro(e, 'Não consegui carregar a configuração') }));
  }, []);

  const set = (k, v) => setCfg((c) => ({ ...c, [k]: v }));

  // Manda só os campos desta tela, e segredo só se foi digitado.
  const gravar = async () => {
    const payload = {};
    for (const k of CAMPOS) {
      if (k.endsWith('_api_key') && !cfg[k]) continue;
      payload[k] = cfg[k];
    }
    const { data } = await configuracaoAPI.putNotificacoes(payload);
    setCfg(data);
  };

  const salvar = async () => {
    setSalvando(true); setMsg(null);
    try {
      await gravar();
      setMsg({ ok: true, txt: 'Configuração salva.' });
    } catch (e) {
      setMsg({ ok: false, txt: mensagemDeErro(e, 'Erro ao salvar') });
    } finally { setSalvando(false); }
  };

  // Salva antes de testar: o teste usa a chave guardada, que é a que vai rodar.
  const testar = async (p) => {
    setTestando(p.id); setMsg(null);
    try {
      await gravar();
      const { data } = await configuracaoAPI.testarProvedorIA(p.id);
      setMsg(data.ok
        ? { ok: true, txt: `${p.nome} respondeu. Modelo ${data.modelo}, conexão funcionando.` }
        : { ok: false, txt: `${p.nome} não respondeu: ${data.erro}` });
    } catch (e) {
      setMsg({ ok: false, txt: mensagemDeErro(e, `Erro ao testar a ${p.nome}`) });
    } finally { setTestando(''); }
  };

  if (!cfg) {
    return msg ? <p className="text-sm text-[#a24a3a]">{msg.txt}</p>
      : <div className="flex items-center justify-center h-64">Carregando...</div>;
  }
  const escolhido = cfg.ia_provedor === 'nvidia' ? 'nvidia' : 'openai';

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-2 mb-6">
        <Sparkles className="text-primary-700" />
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Inteligência artificial</h1>
          <p className="text-sm text-gray-500">Chaves da OpenAI e da NVIDIA, e qual delas responde o Pergunte à IA.</p>
        </div>
      </div>

      {msg && (
        <div role="status" className={`mb-4 rounded-lg px-4 py-3 text-sm ${msg.ok ? 'bg-[#e3eedc] text-[#3d5a32]' : 'bg-[#f6ddd5] text-[#8a3a2c]'}`}>
          {msg.txt}
        </div>
      )}

      <div className="space-y-6">
        <div className="card">
          <h2 className="font-semibold mb-1">Quem responde o Pergunte à IA</h2>
          <p className="text-xs text-gray-500 mb-3">A caixa fica no topo do Painel e das Tarefas, para toda a equipe.</p>
          <div className="flex flex-wrap gap-4">
            {PROVEDORES.map((p) => (
              <label key={p.id} className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="ia_provedor" value={p.id} checked={escolhido === p.id}
                  onChange={() => set('ia_provedor', p.id)} className="h-4 w-4" />
                <span className="text-sm text-gray-700">{p.nome}</span>
                <span className={`text-[11px] px-2 py-0.5 rounded-full ${cfg[p.chave + '_set'] ? 'bg-[#e3eedc] text-[#3d5a32]' : 'bg-[#efe9da] text-gray-500'}`}>
                  {cfg[p.chave + '_set'] ? 'chave guardada' : 'sem chave'}
                </span>
              </label>
            ))}
          </div>
        </div>

        {PROVEDORES.map((p) => (
          <div key={p.id} className="card">
            <h2 className="font-semibold mb-1">{p.nome}</h2>
            <p className="text-xs text-gray-500 mb-3">Gere a chave em {p.onde}.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor={p.chave} className="block text-sm font-medium text-gray-700 mb-1">Chave de API</label>
                <input id={p.chave} type="password" autoComplete="off" value={cfg[p.chave] ?? ''}
                  onChange={(e) => set(p.chave, e.target.value)} className="input-field"
                  placeholder={cfg[p.chave + '_set'] ? '•••••• guardada. Deixe vazio para manter' : p.phChave} />
              </div>
              <div>
                <label htmlFor={p.modelo} className="block text-sm font-medium text-gray-700 mb-1">Modelo</label>
                <input id={p.modelo} value={cfg[p.modelo] ?? ''} onChange={(e) => set(p.modelo, e.target.value)}
                  className="input-field" placeholder={p.phModelo} />
              </div>
            </div>
            <div className="border-t border-gray-100 mt-4 pt-4 flex flex-wrap items-center gap-3">
              <button type="button" onClick={() => testar(p)} disabled={!!testando}
                className="btn-secondary flex items-center gap-2">
                <PlugZap size={16} /> {testando === p.id ? 'Testando...' : 'Testar conexão'}
              </button>
              <span className="text-xs text-gray-400">Salva e faz uma chamada curta na {p.nome}.</span>
            </div>
          </div>
        ))}

        <div className="card flex gap-3 items-start">
          <ShieldCheck size={18} className="text-primary-700 shrink-0 mt-0.5" />
          <p className="text-xs text-gray-600">
            Para a IA vai só a pergunta e a data de hoje. Nome de cliente, CNPJ e tarefas não saem do Tareffas:
            a IA devolve um filtro, e quem busca as tarefas é o próprio Tareffas, mostrando a cada pessoa só o que ela já vê.
            O reforço do e-validador continua na OpenAI e liga em Configuração &gt; Notificações.
          </p>
        </div>

        <div className="flex justify-end">
          <button type="button" onClick={salvar} disabled={salvando} className="btn-primary flex items-center gap-2">
            <Save size={16} /> {salvando ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  );
}
