import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { publicoAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { KeyRound, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function AtivarAcesso() {
  const { token } = useParams();
  const [ctx, setCtx] = useState(null);
  const [erro, setErro] = useState('');
  const [senha, setSenha] = useState('');
  const [senha2, setSenha2] = useState('');
  const [salvando, setSalvando] = useState(false);
  const [pronto, setPronto] = useState(false);

  useEffect(() => {
    publicoAPI.ativarContexto(token)
      .then((r) => setCtx(r.data))
      .catch((e) => setErro(mensagemDeErro(e, 'Convite inválido ou já utilizado.')));
  }, [token]);

  const ativar = async (e) => {
    e.preventDefault();
    setErro('');
    if (senha.length < 6) return setErro('A senha precisa ter ao menos 6 caracteres.');
    if (senha !== senha2) return setErro('As senhas não conferem.');
    setSalvando(true);
    try {
      await publicoAPI.ativar(token, senha);
      setPronto(true);
    } catch (e) {
      setErro(mensagemDeErro(e, 'Não consegui ativar o acesso.'));
    } finally { setSalvando(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: '#ede2d1' }}>
      <div className="w-full max-w-md bg-white rounded-2xl border border-gray-200 p-6"
        style={{ boxShadow: '0 1px 3px rgba(86,100,80,0.08)' }}>
        <div className="flex items-center gap-2 mb-4">
          <KeyRound className="text-primary-700" />
          <h1 className="text-lg font-bold text-gray-800">Ativar acesso · Tareffas</h1>
        </div>

        {erro && !ctx && (
          <div className="flex items-center gap-2 text-sm bg-red-50 text-red-600 rounded-lg px-3 py-2">
            <AlertTriangle size={15} /> {erro}
          </div>
        )}

        {ctx && !pronto && (
          <>
            <div className="text-sm text-gray-600 mb-4">
              <p>Olá, <strong>{ctx.nome}</strong>.</p>
              <p className="text-gray-500">Defina sua senha para acessar com <strong>{ctx.email}</strong>.</p>
            </div>
            <form onSubmit={ativar} className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nova senha</label>
                <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)}
                  className="input-field" placeholder="Mínimo 6 caracteres" autoFocus />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Repita a senha</label>
                <input type="password" value={senha2} onChange={(e) => setSenha2(e.target.value)}
                  className="input-field" />
              </div>
              {erro && <p className="text-sm text-red-600 flex items-center gap-1"><AlertTriangle size={14} />{erro}</p>}
              <button type="submit" disabled={salvando} className="btn-primary w-full">
                {salvando ? 'Ativando…' : 'Ativar e definir senha'}
              </button>
            </form>
          </>
        )}

        {pronto && (
          <div className="flex items-start gap-2 bg-green-50 text-green-700 rounded-lg px-3 py-3 text-sm">
            <CheckCircle2 size={18} className="shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Acesso ativado!</p>
              <p className="text-green-600 text-xs mt-0.5">
                Já pode entrar. <Link to="/login" className="underline font-medium">Ir para o login</Link>.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
