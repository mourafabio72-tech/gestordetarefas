import { useState, useEffect } from 'react';
import { tarefasAPI } from '../services/api';
import { format, isPast, isToday, addDays } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  AlertCircle,
  Calendar,
  TrendingUp
} from 'lucide-react';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [tarefasProximas, setTarefasProximas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const [statsRes, tarefasRes] = await Promise.all([
        tarefasAPI.dashboard(),
        tarefasAPI.list({ status: 'pendente' })
      ]);
      setStats(statsRes.data);
      setTarefasProximas(tarefasRes.data.slice(0, 10));
    } catch (error) {
      console.error('Erro ao carregar dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">Carregando...</div>;
  }

  const statCards = [
    { label: 'Total de Tarefas', value: stats?.total_tarefas || 0, icon: TrendingUp, color: 'bg-primary-500' },
    { label: 'Pendentes', value: stats?.pendentes || 0, icon: Clock, color: 'bg-[#b0813f]' },
    { label: 'Em Andamento', value: stats?.em_andamento || 0, icon: AlertCircle, color: 'bg-[#3a7d76]' },
    { label: 'Concluídas', value: stats?.concluidas || 0, icon: CheckCircle, color: 'bg-[#4d8a3f]' },
    { label: 'Atrasadas', value: stats?.atrasadas || 0, icon: AlertTriangle, color: 'bg-[#a24a3a]' },
    { label: 'Vencendo Hoje', value: stats?.vencendo_hoje || 0, icon: Calendar, color: 'bg-[#c58a3a]' },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="card flex items-center gap-4">
              <div className={`${card.color} p-3 rounded-lg`}>
                <Icon size={24} className="text-white" />
              </div>
              <div>
                <p className="text-sm text-gray-500">{card.label}</p>
                <p className="text-2xl font-bold text-gray-800">{card.value}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Tarefas Próximas do Vencimento</h2>
          {tarefasProximas.length === 0 ? (
            <p className="text-gray-500 text-center py-4">Nenhuma tarefa pendente</p>
          ) : (
            <div className="space-y-3">
              {tarefasProximas.map((tarefa) => {
                const prazoDate = new Date(tarefa.data_prazo);
                const atrasada = isPast(prazoDate) && !isToday(prazoDate);
                const venceHoje = isToday(prazoDate);
                const venceEmBreve = !isPast(prazoDate) && isToday(addDays(prazoDate, -1));

                return (
                  <div
                    key={tarefa.id}
                    className={`p-3 rounded-lg border-l-4 ${
                      atrasada
                        ? 'border-red-500 bg-red-50'
                        : venceHoje
                        ? 'border-orange-500 bg-orange-50'
                        : 'border-blue-500 bg-blue-50'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium text-gray-800">{tarefa.titulo}</p>
                        <p className="text-sm text-gray-500">
                          {format(prazoDate, "dd/MM/yyyy", { locale: ptBR })}
                        </p>
                      </div>
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          atrasada
                            ? 'bg-red-100 text-red-700'
                            : venceHoje
                            ? 'bg-orange-100 text-orange-700'
                            : 'bg-blue-100 text-blue-700'
                        }`}
                      >
                        {atrasada ? 'Atrasada' : venceHoje ? 'Vence Hoje' : 'Próximo'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Resumo por Status</h2>
          <div className="space-y-4">
            {[
              { label: 'Pendentes', value: stats?.pendentes || 0, total: stats?.total_tarefas || 0, color: 'bg-[#b0813f]' },
              { label: 'Em Andamento', value: stats?.em_andamento || 0, total: stats?.total_tarefas || 0, color: 'bg-[#3a7d76]' },
              { label: 'Concluídas', value: stats?.concluidas || 0, total: stats?.total_tarefas || 0, color: 'bg-[#4d8a3f]' },
              { label: 'Atrasadas', value: stats?.atrasadas || 0, total: stats?.total_tarefas || 0, color: 'bg-[#a24a3a]' },
            ].map((item) => {
              const percentual = item.total > 0 ? (item.value / item.total) * 100 : 0;
              return (
                <div key={item.label}>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm text-gray-600">{item.label}</span>
                    <span className="text-sm font-medium text-gray-800">{item.value}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`${item.color} h-2 rounded-full`}
                      style={{ width: `${percentual}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}