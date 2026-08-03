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
  FileCheck2,
  ShieldCheck,
  Settings,
  UserCog,
  Bell,
  LogOut,
  LayoutGrid,
  Menu,
  X
} from 'lucide-react';

const HUB_URL = import.meta.env.VITE_HUB_URL || 'https://zoaria.com.br';
import { useState } from 'react';

const menuGroups = [
  {
    label: 'Operacional',
    items: [
      { path: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'gestor', 'usuario'] },
      { path: '/tarefas', label: 'Tarefas', icon: ListTodo, roles: ['admin', 'gestor', 'usuario'] },
      { path: '/relatorios', label: 'Relatórios', icon: BarChart3, roles: ['admin', 'gestor'] },
      { path: '/evalidador', label: 'e-validador', icon: FileCheck2, roles: ['admin', 'gestor'] },
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
    label: 'Configuração',
    items: [
      { path: '/substituicoes', label: 'Substituições', icon: UserCog, roles: ['admin', 'gestor'] },
      { path: '/notificacoes', label: 'Notificações', icon: Bell, roles: ['admin'] },
    ],
  },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const grupo = user?.grupo || 'usuario';

  return (
    <div className="flex h-screen bg-gray-100">
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-primary-800 text-white transform transition-transform duration-200 ease-in-out
        lg:relative lg:translate-x-0 flex flex-col
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex items-center justify-between p-4 border-b border-primary-700">
          <h1 className="text-xl font-bold">Tareffas</h1>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden">
            <X size={24} />
          </button>
        </div>

        <nav className="p-4 flex-1 overflow-y-auto">
          {menuGroups.map((group) => {
            const visibleItems = group.items.filter((item) => item.roles.includes(grupo));
            if (visibleItems.length === 0) return null;
            return (
              <div key={group.label} className="mb-4">
                <p className="px-4 mb-1 text-xs font-semibold uppercase tracking-wider text-primary-400">
                  {group.label}
                </p>
                {visibleItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      onClick={() => setSidebarOpen(false)}
                      className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-1 transition-colors ${
                        isActive
                          ? 'bg-primary-600 text-white'
                          : 'text-primary-200 hover:bg-primary-700'
                      }`}
                    >
                      <Icon size={20} />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            );
          })}
        </nav>

        <div className="w-full p-4 border-t border-primary-700">
          <div className="flex items-center gap-3 mb-3 px-4">
            <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
              {user?.nome?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.nome}</p>
              <p className="text-xs text-primary-300 truncate capitalize">{grupo}</p>
            </div>
          </div>
          <a
            href={HUB_URL}
            className="flex items-center gap-2 w-full px-4 py-2 mb-1 text-primary-200 hover:bg-primary-700 rounded-lg transition-colors"
          >
            <LayoutGrid size={18} />
            <span>Voltar ao Hub</span>
          </a>
          <button
            onClick={logout}
            className="flex items-center gap-2 w-full px-4 py-2 text-primary-200 hover:bg-primary-700 rounded-lg transition-colors"
          >
            <LogOut size={18} />
            <span>Sair</span>
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
