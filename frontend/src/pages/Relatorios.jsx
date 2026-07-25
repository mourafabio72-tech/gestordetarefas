import { BarChart3 } from 'lucide-react';

export default function Relatorios() {
  return (
    <div>
      <div className="flex items-center gap-2 mb-6">
        <BarChart3 className="text-primary-700" />
        <h1 className="text-2xl font-bold text-gray-800">Relatórios</h1>
      </div>
      <div className="card text-center py-16">
        <BarChart3 size={48} className="mx-auto text-gray-300 mb-4" />
        <p className="text-gray-500">Módulo de relatórios em construção.</p>
        <p className="text-sm text-gray-400 mt-1">
          Em breve: tarefas por status, responsável e empresa, atrasadas e vencimentos com multa.
        </p>
      </div>
    </div>
  );
}
