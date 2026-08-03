import { useState } from 'react';
import { evalidadorAPI } from '../services/api';
import { FileCheck2, Upload, CheckCircle2, AlertTriangle, XCircle, Clock } from 'lucide-react';

const STATUS = {
  baixada: { label: 'Baixada', cls: 'bg-green-100 text-green-700', Icon: CheckCircle2 },
  ja_baixada: { label: 'Já baixada', cls: 'bg-gray-100 text-gray-600', Icon: CheckCircle2 },
  sem_tarefa: { label: 'Sem tarefa', cls: 'bg-yellow-100 text-yellow-700', Icon: Clock },
  ambiguo: { label: 'Ambíguo', cls: 'bg-orange-100 text-orange-700', Icon: AlertTriangle },
  erro: { label: 'Erro', cls: 'bg-red-100 text-red-700', Icon: XCircle },
};

const ACEITA = '.pdf,.xlsx,.xls,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel';
const EXT_OK = /\.(pdf|xlsx|xls)$/i;

export default function EValidador() {
  const [files, setFiles] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const adicionar = (lista) => {
    const novos = Array.from(lista || []).filter((f) => EXT_OK.test(f.name));
    if (novos.length) { setFiles((atual) => [...atual, ...novos]); setResultado(null); }
  };

  const onDrop = (e) => {
    e.preventDefault(); setDragOver(false);
    adicionar(e.dataTransfer.files);
  };

  const processar = async () => {
    if (!files.length) return;
    setProcessing(true); setResultado(null);
    try {
      const r = await evalidadorAPI.processar(files);
      setResultado(r.data);
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao processar');
    } finally { setProcessing(false); }
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-6">
        <FileCheck2 className="text-primary-700" />
        <h1 className="text-2xl font-bold text-gray-800">e-validador</h1>
      </div>

      <div className="card mb-6">
        <p className="text-sm text-gray-600 mb-4">
          Envie os <strong>comprovantes de entrega</strong> (PDF ou Excel). O e-validador extrai
          CNPJ, competência e o tipo de obrigação, e dá baixa na tarefa correspondente.
        </p>
        <div className="flex items-center gap-4">
          <label
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={`flex-1 cursor-pointer border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
              dragOver ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-primary-400'}`}
          >
            <Upload size={28} className="mx-auto text-gray-400 mb-2" />
            <span className="text-sm text-gray-600 block">
              {files.length
                ? `${files.length} arquivo(s) selecionado(s)`
                : 'Arraste os arquivos aqui ou clique para selecionar'}
            </span>
            <span className="text-xs text-gray-400">Aceita PDF, XLSX e XLS · vários de uma vez</span>
            <input type="file" accept={ACEITA} multiple className="hidden"
              onChange={(e) => adicionar(e.target.files)} />
          </label>
          <div className="flex flex-col gap-2">
            <button onClick={processar} disabled={!files.length || processing} className="btn-primary h-fit">
              {processing ? 'Processando...' : 'Processar'}
            </button>
            {files.length > 0 && (
              <button onClick={() => { setFiles([]); setResultado(null); }} className="btn-secondary text-xs">
                Limpar
              </button>
            )}
          </div>
        </div>
        {files.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2">
            {files.map((f, i) => (
              <li key={i} className="text-xs bg-gray-100 text-gray-600 rounded-full px-2 py-1 flex items-center gap-1">
                {f.name}
                <button onClick={() => setFiles(files.filter((_, j) => j !== i))} className="text-gray-400 hover:text-red-600">×</button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {resultado && (
        <div className="card">
          <div className="flex flex-wrap gap-2 mb-4">
            {Object.entries(resultado.resumo).map(([k, v]) => {
              const s = STATUS[k] || STATUS.erro;
              return <span key={k} className={`px-3 py-1 rounded-full text-sm ${s.cls}`}>{s.label}: {v}</span>;
            })}
          </div>
          <div className="space-y-2">
            {resultado.resultados.map((r, i) => {
              const s = STATUS[r.status] || STATUS.erro;
              const Icon = s.Icon;
              return (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg border border-gray-200">
                  <Icon size={18} className={`mt-0.5 ${s.cls.split(' ')[1]}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-800 truncate">{r.arquivo}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs ${s.cls}`}>{s.label}</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-0.5">{r.detalhe}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {r.cnpj && <>CNPJ {r.cnpj} · </>}
                      {r.competencia && <>Competência {r.competencia} · </>}
                      {r.protocolo && <>Protocolo {String(r.protocolo).slice(0, 16)}…</>}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
