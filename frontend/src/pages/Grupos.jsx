import { useState, useEffect } from 'react';
import { usuariosAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { ShieldCheck, ShieldAlert } from 'lucide-react';

const GRUPOS = [
  { value: 'admin', label: 'Admin', desc: 'Acesso total, incluindo grupos e permissões.' },
  { value: 'gestor', label: 'Gestor', desc: 'Gerencia tarefas, cadastros e usuários (não altera grupos).' },
  { value: 'usuario', label: 'Usuário', desc: 'Vê o dashboard e as tarefas; atualiza status.' },
];

const grupoBadge = {
  admin: 'bg-purple-100 text-purple-700',
  gestor: 'bg-blue-100 text-blue-700',
  usuario: 'bg-gray-100 text-gray-700',
};

export default function Grupos() {
  const { user } = useAuth();
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);

  useEffect(() => {
    loadUsuarios();
  }, []);

  const loadUsuarios = async () => {
    try {
      const res = await usuariosAPI.list();
      setUsuarios(res.data);
    } catch (error) {
      console.error('Erro ao carregar usuários:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = async (usuario, novoGrupo) => {
    setSavingId(usuario.id);
    try {
      await usuariosAPI.update(usuario.id, { grupo: novoGrupo });
      await loadUsuarios();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao alterar grupo');
    } finally {
      setSavingId(null);
    }
  };

  if (user?.grupo !== 'admin') {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <ShieldAlert size={48} className="mb-4 text-gray-300" />
        <p>Apenas administradores podem gerenciar grupos.</p>
      </div>
    );
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64">Carregando...</div>;
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-6">
        <ShieldCheck className="text-primary-700" />
        <h1 className="text-2xl font-bold text-gray-800">Grupo de usuários</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {GRUPOS.map((g) => (
          <div key={g.value} className="card">
            <span className={`px-2 py-1 rounded-full text-xs ${grupoBadge[g.value]}`}>{g.label}</span>
            <p className="text-sm text-gray-600 mt-2">{g.desc}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-600">Nome</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-600">Email</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-600">Grupo atual</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-600">Alterar para</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium">{u.nome}</td>
                  <td className="py-3 px-4 text-gray-500">{u.email}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs capitalize ${grupoBadge[u.grupo] || grupoBadge.usuario}`}>
                      {u.grupo || 'usuario'}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <select
                      value={u.grupo || 'usuario'}
                      disabled={savingId === u.id || u.id === user.id}
                      onChange={(e) => handleChange(u, e.target.value)}
                      className="text-sm border border-gray-300 rounded-lg px-2 py-1 disabled:opacity-50"
                    >
                      {GRUPOS.map((g) => (
                        <option key={g.value} value={g.value}>{g.label}</option>
                      ))}
                    </select>
                    {u.id === user.id && (
                      <span className="ml-2 text-xs text-gray-400">(você)</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
