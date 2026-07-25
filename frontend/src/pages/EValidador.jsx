import { FileCheck2 } from 'lucide-react';

export default function EValidador() {
  return (
    <div>
      <div className="flex items-center gap-2 mb-6">
        <FileCheck2 className="text-primary-700" />
        <h1 className="text-2xl font-bold text-gray-800">e-validador</h1>
      </div>
      <div className="card text-center py-16">
        <FileCheck2 size={48} className="mx-auto text-gray-300 mb-4" />
        <p className="text-gray-500">Módulo e-validador em construção.</p>
        <p className="text-sm text-gray-400 mt-1">
          Aguardando definição do que será validado (ex.: XML de NF-e/NFS-e, certidões, certificado digital).
        </p>
      </div>
    </div>
  );
}
