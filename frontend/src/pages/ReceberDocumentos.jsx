import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { publicoAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { Download, FileText, AlertTriangle, Loader2 } from 'lucide-react';

// Página que o cliente abre pelo link da mensagem quando a guia vai com
// documentos complementares (2026-10-28). Cada download passa pelo servidor,
// que registra o acesso; abrir a página não conta.
export default function ReceberDocumentos() {
  const { token } = useParams();
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    publicoAPI.documentos(token)
      .then((r) => setDados(r.data))
      .catch((e) => setErro(mensagemDeErro(e, 'Link inválido ou expirado.')));
  }, [token]);

  return (
    // O fundo creme vem do body (index.css): nenhuma cor escrita aqui.
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="text-primary-700" />
          <h1 className="text-lg font-bold text-gray-800">Seus documentos · BPS4</h1>
        </div>

        {erro && (
          <div className="flex items-center gap-2 text-sm bg-red-50 text-red-600 rounded-lg px-3 py-2">
            <AlertTriangle size={15} /> {erro}
          </div>
        )}

        {!erro && !dados && (
          <p className="flex items-center gap-2 text-sm text-gray-500">
            <Loader2 size={15} className="animate-spin" /> Carregando…
          </p>
        )}

        {dados && (
          <>
            <div className="text-sm text-gray-600 mb-4 space-y-0.5">
              {dados.empresa && <p><span className="text-gray-400">Empresa:</span> <strong>{dados.empresa}</strong></p>}
              <p><span className="text-gray-400">Guia:</span> {dados.guia}</p>
              {dados.competencia && <p><span className="text-gray-400">Competência:</span> {dados.competencia}</p>}
              {dados.vencimento && <p><span className="text-gray-400">Vencimento:</span> {dados.vencimento}</p>}
            </div>
            <ul className="space-y-2">
              {dados.arquivos.map((a) => (
                <li key={a.url}>
                  <a href={a.url} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-3 border border-gray-200 rounded-lg px-3 py-3 hover:border-primary-400 hover:bg-primary-50 transition-colors">
                    <Download size={18} className="text-primary-700 shrink-0" />
                    <span className="flex-1 min-w-0">
                      <span className="block text-sm text-gray-800 truncate">{a.nome}</span>
                      <span className="block text-xs text-gray-500">
                        {a.tipo === 'guia' ? 'Guia' : 'Documento complementar'}
                      </span>
                    </span>
                  </a>
                </li>
              ))}
            </ul>
            <p className="text-xs text-gray-500 mt-4">
              O link é exclusivo da sua mensagem. Qualquer dúvida, é só responder.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
