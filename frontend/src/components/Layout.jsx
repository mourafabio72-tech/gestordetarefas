import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  LayoutDashboard,
  Building2,
  Users,
  FolderOpen,
  ListTodo,
  FileStack,
  Library,
  BarChart3,
  FileCheck2, FileArchive,
  ShieldCheck,
  Settings,
  UserCog,
  Bell,
  CalendarClock,
  LogOut,
  LayoutGrid,
  Menu,
  X,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
} from 'lucide-react';

const HUB_URL = import.meta.env.VITE_HUB_URL || 'https://zoaria.com.br';
import { useState } from 'react';

const menuGroups = [
  {
    label: 'Operacional',
    items: [
      { path: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'gestor', 'usuario'] },
      { path: '/tarefas', label: 'Tarefas', icon: ListTodo, roles: ['admin', 'gestor', 'usuario'] },
      { path: '/evalidador', label: 'e-validador', icon: FileCheck2, roles: ['admin', 'gestor'] },
      // Consulta do acervo. Fica no Operacional, junto de Tarefas: é ali que se
      // procura comprovante no dia a dia, e não em Relatórios.
      { path: '/documentos', label: 'Documentos', icon: FileArchive, roles: ['admin', 'gestor', 'usuario'] },
    ],
  },
  {
    label: 'Cadastro',
    items: [
      { path: '/obrigacoes', label: 'Obrigações', icon: FileStack, roles: ['admin', 'gestor'] },
      { path: '/modelos', label: 'Modelos', icon: Library, roles: ['admin', 'gestor'] },
      { path: '/setores', label: 'Setores', icon: FolderOpen, roles: ['admin', 'gestor'] },
      { path: '/empresas', label: 'Empresas', icon: Building2, roles: ['admin', 'gestor'] },
      { path: '/usuarios', label: 'Usuários', icon: Users, roles: ['admin', 'gestor'] },
      { path: '/grupos', label: 'Grupo de usuários', icon: ShieldCheck, roles: ['admin'] },
    ],
  },
  {
    label: 'Relatórios',
    items: [
      { path: '/relatorios/obrigacoes', label: 'Relação de obrigações', icon: BarChart3, roles: ['admin', 'gestor'] },
    ],
  },
  {
    label: 'Configuração',
    items: [
      { path: '/substituicoes', label: 'Substituições', icon: UserCog, roles: ['admin', 'gestor'] },
      { path: '/importar-cronograma', label: 'Importar obrigações', icon: CalendarClock, roles: ['admin', 'gestor'] },
      { path: '/notificacoes', label: 'Notificações', icon: Bell, roles: ['admin'] },
    ],
  },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [recolhidos, setRecolhidos] = useState(() => {
    try { return JSON.parse(localStorage.getItem('menuRecolhidos') || '{}'); }
    catch { return {}; }
  });
  const grupo = user?.grupo || 'usuario';

  const toggleGrupo = (label) => setRecolhidos((r) => {
    const novo = { ...r, [label]: !r[label] };
    localStorage.setItem('menuRecolhidos', JSON.stringify(novo));
    return novo;
  });

  const [colapsado, setColapsado] = useState(() => localStorage.getItem('menuColapsado') === '1');
  const toggleColapsado = () => setColapsado((c) => {
    localStorage.setItem('menuColapsado', c ? '0' : '1');
    return !c;
  });

  return (
    <div className="flex h-screen bg-gray-100">
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-[#2f3b2f] text-white transform transition-all duration-200 ease-in-out
        lg:relative lg:translate-x-0 flex flex-col ${colapsado ? 'lg:w-16' : ''}
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex items-center justify-between border-b border-white/10 p-4">
          <h1 className={`text-xl font-bold ${colapsado ? 'lg:hidden' : ''}`}>Tareffas</h1>
          {colapsado && <span className="hidden lg:block text-xl font-bold mx-auto">T</span>}
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden">
            <X size={24} />
          </button>
          {/* recolher/expandir barra, só desktop */}
          <button onClick={toggleColapsado}
            className={`hidden lg:block text-white/50 hover:text-white ${colapsado ? 'lg:hidden' : ''}`}
            title="Recolher menu">
            <ChevronLeft size={18} />
          </button>
        </div>
        {colapsado && (
          <button onClick={toggleColapsado} title="Expandir menu"
            className="hidden lg:flex justify-center py-2 text-white/50 hover:text-white border-b border-white/10">
            <ChevronRight size={18} />
          </button>
        )}

        <nav className="px-2 py-3 flex-1 overflow-y-auto">
          {menuGroups.map((group) => {
            const visibleItems = group.items.filter((item) => item.roles.includes(grupo));
            if (visibleItems.length === 0) return null;
            const recolhido = recolhidos[group.label];
            return (
              <div key={group.label} className="mb-2">
                <button
                  onClick={() => toggleGrupo(group.label)}
                  className={`w-full flex items-center gap-1 px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-white/40 hover:text-white/70 transition-colors ${colapsado ? 'lg:hidden' : ''}`}
                >
                  {recolhido ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                  <span>{group.label}</span>
                </button>
                <div className={`mx-2 my-1 border-t border-white/10 ${colapsado ? 'hidden lg:block' : 'hidden'}`} />
                <div className={`${recolhido ? 'hidden' : ''} ${colapsado ? 'lg:block' : ''}`}>
                  {visibleItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = location.pathname === item.path;
                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        onClick={() => setSidebarOpen(false)}
                        title={item.label}
                        className={`flex items-center gap-2.5 px-3 py-1.5 rounded-lg mb-0.5 text-sm transition-colors ${
                          colapsado ? 'lg:gap-0 lg:justify-center lg:px-2' : ''
                        } ${
                          isActive ? 'bg-white/[0.14] text-white' : 'text-white/70 hover:bg-white/10'
                        }`}
                      >
                        <Icon size={16} />
                        <span className={colapsado ? 'lg:hidden' : ''}>{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>

        {/* Rodapé com as MESMAS medidas dos itens do menu: ícone 16, gap-2.5,
            py-1.5, text-sm. Antes eram quatro diferenças acumuladas — ícone 18,
            gap-2, py-2 e a fonte herdada de 16px — e o resultado é que "Voltar
            ao Hub" e "Sair" pareciam de outro menu, colados no fim deste. */}
        <div className="w-full border-t border-white/10 p-2">
          {/* O avatar é maior que os ícones do menu, então o texto nunca vai
              cair na mesma coluna. Em vez de fingir alinhamento, o bloco vira
              um card: fica claro que é outra coisa, e não um item torto. */}
          <div className={`flex items-center gap-2.5 mb-2 p-2 rounded-lg bg-white/[0.06] ${
            colapsado ? 'lg:hidden' : ''}`}>
            <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center shrink-0 text-sm">
              {user?.nome?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate leading-tight">{user?.nome}</p>
              <p className="text-xs text-primary-300 truncate capitalize leading-tight">{grupo}</p>
            </div>
          </div>
          <a
            href={HUB_URL}
            title="Voltar ao Hub"
            className={`flex items-center gap-2.5 px-3 py-1.5 mb-0.5 rounded-lg text-sm text-white/70 hover:bg-white/10 transition-colors ${
              colapsado ? 'lg:gap-0 lg:justify-center lg:px-2' : ''}`}
          >
            <LayoutGrid size={16} />
            <span className={colapsado ? 'lg:hidden' : ''}>Voltar ao Hub</span>
          </a>
          <button
            onClick={logout}
            title="Sair"
            className={`flex items-center w-full gap-2.5 px-3 py-1.5 rounded-lg text-sm text-white/70 hover:bg-white/10 transition-colors ${
              colapsado ? 'lg:gap-0 lg:justify-center lg:px-2' : ''}`}
          >
            <LogOut size={16} />
            <span className={colapsado ? 'lg:hidden' : ''}>Sair</span>
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white shadow-sm px-4 py-3 flex items-center gap-4 lg:hidden">
          <button onClick={() => setSidebarOpen(true)}>
            <Menu size={24} />
          </button>
          <h1 className="text-lg font-semibold">Tareffas</h1>
        </header>

        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
