import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { tarefasAPI } from '../services/api';
import { format, isPast, isToday } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import {
  AlertTriangle, CheckCircle, Clock, AlertCircle, Calendar, TrendingUp,
} from 'lucide-react';

// Cores de STATUS (validadas): amarelo/azul/verde/vermelho. Ordem do donut deixa
// verde (concluídas) e vermelho (atrasadas) separados, nunca adjacentes.
const STATUS_DONUT = [
  { key: 'concluidas',   label: 'Concluídas',   color: '#4d8a3f', Icon: CheckCircle },
  { key: 'pendentes',    label: 'Pendentes',    color: '#b0813f', Icon: Clock },
  { key: 'em_andamento', label: 'Em Andamento', color: '#2f6fb0', Icon: AlertCircle },
  { key: 'atrasadas',    label: 'Atrasadas',    color: '#a24a3a', Icon: AlertTriangle },
];

// Geometria do donut a partir de um objeto de stats (mesmas chaves de status).
function useSegmentos(stats) {
  const dados = STATUS_DONUT.map((s) => ({ ...s, value: stats?.[s.key] || 0 }));
  const total = dados.reduce((acc, d) => acc + d.value, 0);
  const R = 52, C = 2 * Math.PI * R, GAP = total > 1 ? 4 : 0;
  let acumulado = 0;
  const segmentos = dados.filter((d) => d.value > 0).map((d) => {
    const frac = d.value / total;
    const seg = { ...d, len: Math.max(frac * C - GAP, 0), offset: acumulado * C };
    acumulado += frac;
    return seg;
  });
  return { dados, total, C, R, segmentos };
}

function Anel({ segmentos, C, R, centro, sub, className }) {
  return (
    <svg viewBox="0 0 120 120" className={className}>
      <circle cx="60" cy="60" r={R} fill="none" stroke="#efe7d8" strokeWidth="16" />
      {segmentos.map((s) => (
        <circle key={s.key} cx="60" cy="60" r={R} fill="none"
          stroke={s.color} strokeWidth="16" strokeLinecap="butt"
          strokeDasharray={`${s.len} ${C - s.len}`} strokeDashoffset={-s.offset}
          transform="rotate(-90 60 60)" />
      ))}
      <text x="60" y="56" textAnchor="middle" className="fill-gray-800" style={{ fontSize: 22, fontWeight: 700 }}>{centro}</text>
      <text x="60" y="72" textAnchor="middle" className="fill-gray-400" style={{ fontSize: 9 }}>{sub}</text>
    </svg>
  );
}

function Donut({ stats }) {
  const { dados, total, C, R, segmentos } = useSegmentos(stats);
  return (
    <div className="flex items-center gap-6">
      <Anel segmentos={segmentos} C={C} R={R} centro={stats?.total_tarefas || 0} sub="tarefas" className="w-40 h-40 shrink-0" />
      <ul className="flex-1 space-y-2">
        {dados.map((d) => {
          const pct = total > 0 ? Math.round((d.value / total) * 100) : 0;
          const Icon = d.Icon;
          return (
            <li key={d.key} className="flex items-center gap-2 text-sm">
              <Icon size={14} style={{ color: d.color }} />
              <span className="text-gray-600 flex-1">{d.label}</span>
              <span className="font-semibold text-gray-800 tabular-nums">{d.value}</span>
              <span className="text-gray-400 text-xs w-9 text-right tabular-nums">{pct}%</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function DonutSetor({ setor }) {
  const { dados, total, C, R, segmentos } = useSegmentos(setor);
  return (
    <Link to={`/tarefas?setor=${setor.setor_id}`}
      className="block rounded-xl border border-gray-200 bg-white p-4 hover:border-primary-400 hover:shadow-sm transition-colors">
      <h3 className="text-sm font-semibold text-gray-800 mb-2 truncate">{setor.setor_nome}</h3>
      <div className="flex justify-center">
        <Anel segmentos={segmentos} C={C} R={R} centro={total} sub="tarefas" className="w-28 h-28" />
      </div>
      <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
        {dados.map((d) => (
          <li key={d.key} className="flex items-center gap-1.5 text-xs">
            <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: d.color }} />
            <span className="text-gray-500 flex-1 truncate">{d.label}</span>
            <span className="font-semibold text-gray-800 tabular-nums">{d.value}</span>
          </li>
        ))}
      </ul>
    </Link>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [porSetor, setPorSetor] = useState([]);
  const [tarefasProximas, setTarefasProximas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadDashboard(); }, []);

  const loadDashboard = async () => {
    try {
      const [statsRes, setorRes, tarefasRes] = await Promise.all([
        tarefasAPI.dashboard(),
        tarefasAPI.dashboardPorSetor(),
        tarefasAPI.list({ status: 'pendente' }),
      ]);
      setStats(statsRes.data);
      setPorSetor(setorRes.data);
      setTarefasProximas(tarefasRes.data.slice(0, 8));
    } catch (error) {
      console.error('Erro ao carregar dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64">Carregando...</div>;

  const tiles = [
    { label: 'Total', value: stats?.total_tarefas || 0, icon: TrendingUp, cor: '#566450' },
    { label: 'Pendentes', value: stats?.pendentes || 0, icon: Clock, cor: '#b0813f' },
    { label: 'Em Andamento', value: stats?.em_andamento || 0, icon: AlertCircle, cor: '#2f6fb0' },
    { label: 'Concluídas', value: stats?.concluidas || 0, icon: CheckCircle, cor: '#4d8a3f' },
    { label: 'Atrasadas', value: stats?.atrasadas || 0, icon: AlertTriangle, cor: '#a24a3a' },
    { label: 'Vencendo Hoje', value: stats?.vencendo_hoje || 0, icon: Calendar, cor: '#c58a3a' },
  ];

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-800 mb-4">Dashboard</h1>

      {/* Cards compactos, uma linha só */}
      <div className="grid grid-cols-3 lg:grid-cols-6 gap-2 mb-6">
        {tiles.map((t) => {
          const Icon = t.icon;
          return (
            <div key={t.label} className="rounded-lg border border-gray-200 bg-white px-3 py-2 flex flex-col"
              style={{ borderLeft: `3px solid ${t.cor}` }}>
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-gray-500 leading-tight">{t.label}</span>
                <Icon size={13} style={{ color: t.cor }} />
              </div>
              <span className="text-xl font-bold text-gray-800 tabular-nums leading-tight">{t.value}</span>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <div className="card">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Distribuição por status</h2>
          <Donut stats={stats} />
        </div>

        <div className="card">
          <h2 className="text-base font-semibold text-gray-800 mb-3">Próximas do vencimento</h2>
          {tarefasProximas.length === 0 ? (
            <p className="text-gray-500 text-center py-4 text-sm">Nenhuma tarefa pendente</p>
          ) : (
            <div className="space-y-2">
              {tarefasProximas.map((tarefa) => {
                const prazoDate = new Date(tarefa.data_prazo);
                const atrasada = isPast(prazoDate) && !isToday(prazoDate);
                const venceHoje = isToday(prazoDate);
                return (
                  <div key={tarefa.id}
                    className={`px-3 py-2 rounded-lg border-l-4 flex justify-between items-center ${
                      atrasada ? 'border-red-500 bg-red-50'
                        : venceHoje ? 'border-orange-500 bg-orange-50'
                        : 'border-blue-500 bg-blue-50'}`}>
                    <div className="min-w-0">
                      <p className="font-medium text-gray-800 text-sm truncate">{tarefa.titulo}</p>
                      <p className="text-xs text-gray-500">{format(prazoDate, 'dd/MM/yyyy', { locale: ptBR })}</p>
                    </div>
                    <span className={`px-2 py-0.5 text-xs rounded-full whitespace-nowrap ${
                      atrasada ? 'bg-red-100 text-red-700'
                        : venceHoje ? 'bg-orange-100 text-orange-700'
                        : 'bg-blue-100 text-blue-700'}`}>
                      {atrasada ? 'Atrasada' : venceHoje ? 'Vence hoje' : 'Próximo'}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Um donut por setor */}
      {porSetor.length > 0 && (
        <div>
          <h2 className="text-base font-semibold text-gray-800 mb-3">Por setor</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {porSetor.map((s) => <DonutSetor key={s.setor_id} setor={s} />)}
          </div>
        </div>
      )}
    </div>
  );
}
