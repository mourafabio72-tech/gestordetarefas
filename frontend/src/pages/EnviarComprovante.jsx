import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { publicoAPI } from '../services/api';
import { Upload, CheckCircle2, FileCheck2, AlertTriangle } from 'lucide-react';

export default function EnviarComprovante() {
  const { token } = useParams();
  const [ctx, setCtx] = useState(null);
  const [erro, setErro] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    publicoAPI.contexto(token)
      .then((r) => { setCtx(r.data); setEnviado(r.data.ja_enviado); })
      .catch((e) => setErro(e.response?.data?.detail || 'Link inválido ou expirado.'));
  }, [token]);

  const enviar = async (file) => {
    if (!file) return;
    setEnviando(true); setErro('');
    try {
      await publicoAPI.enviar(token, file);
      setEnviado(true);
    } catch (e) {
      setErro(e.response?.data?.detail || 'Não consegui enviar o arquivo.');
    } finally { setEnviando(false); }
  };

  const onDrop = (e) => { e.preventDefault(); setDragOver(false); enviar(e.dataTransfer.files?.[0]); };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: '#ede2d1' }}>
      <div className="w-full max-w-md bg-white rounded-2xl border border-gray-200 p-6"
        style={{ boxShadow: '0 1px 3px rgba(86,100,80,0.08)' }}>
        <div className="flex items-center gap-2 mb-4">
          <FileCheck2 className="text-primary-700" />
          <h1 className="text-lg font-bold text-gray-800">Envio de comprovante · Tareffas</h1>
        </div>

        {erro && !ctx && (
          <div className="flex items-center gap-2 text-sm bg-red-50 text-red-600 rounded-lg px-3 py-2">
            <AlertTriangle size={15} /> {erro}
          </div>
        )}

        {ctx && (
          <>
            <div className="text-sm text-gray-600 mb-4 space-y-0.5">
              <p><span className="text-gray-400">Empresa:</span> <strong>{ctx.empresa || '-'}</strong></p>
              <p><span className="text-gray-400">Obrigação:</span> {ctx.obrigacao || ctx.titulo}</p>
              {ctx.competencia && <p><span className="text-gray-400">Competência:</span> {ctx.competencia}</p>}
            </div>

            {enviado ? (
              <div className="flex items-start gap-2 bg-green-50 text-green-700 rounded-lg px-3 py-3 text-sm">
                <CheckCircle2 size={18} className="shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Comprovante recebido. Obrigado!</p>
                  <p className="text-green-600 text-xs mt-0.5">A tarefa foi marcada como concluída. Você pode fechar esta página.</p>
                </div>
              </div>
            ) : (
              <>
                <label
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={onDrop}
                  className={`block cursor-pointer border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                    dragOver ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-primary-400'}`}
                >
                  <Upload size={28} className="mx-auto text-gray-400 mb-2" />
                  <span className="text-sm text-gray-600 block">
                    {enviando ? 'Enviando…' : 'Arraste o comprovante aqui ou clique para selecionar'}
                  </span>
                  <span className="text-xs text-gray-400">PDF, Excel ou imagem · até 15 MB</span>
                  <input type="file" accept=".pdf,.xlsx,.xls,.png,.jpg,.jpeg" className="hidden"
                    disabled={enviando} onChange={(e) => enviar(e.target.files?.[0])} />
                </label>
                {erro && <p className="text-sm text-red-600 mt-3 flex items-center gap-1"><AlertTriangle size={14} />{erro}</p>}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
