import { useState, useEffect } from 'react';
import { usuariosAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { ShieldCheck, ShieldAlert, SlidersHorizontal } from 'lucide-react';
import {
  GRUPOS, RECURSOS, NIVEIS, ESCOPOS, FLAGS, PRESETS, resolver, calcularOverrides,
} from '../permissoes';

const grupoBadge = {
  admin: 'bg-purple-100 text-purple-700',
  gestor: 'bg-blue-100 text-blue-700',
  analista: 'bg-teal-100 text-teal-700',
  consulta: 'bg-gray-100 text-gray-700',
  usuario: 'bg-gray-100 text-gray-700',
};

export default function Grupos() {
  const { user } = useAuth();
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);

  const [modalUser, setModalUser] = useState(null);
  const [grupoSel, setGrupoSel] = useState('usuario');
  const [matriz, setMatriz] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => { loadUsuarios(); }, []);

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

  const handleChangeGrupo = async (usuario, novoGrupo) => {
    setSavingId(usuario.id);
    try {
      await usuariosAPI.update(usuario.id, { grupo: novoGrupo });
      await loadUsuarios();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao alterar papel');
    } finally {
      setSavingId(null);
    }
  };

  const abrirMatriz = (u) => {
    setModalUser(u);
    setGrupoSel(u.grupo || 'usuario');
    setMatriz(resolver(u.grupo || 'usuario', u.permissoes));
  };

  // Trocar o papel dentro do modal reinicia a matriz para o preset do papel.
  const trocarPapel = (novo) => {
    setGrupoSel(novo);
    setMatriz({ ...(PRESETS[novo] || PRESETS.consulta) });
  };

  const restaurarPreset = () => setMatriz({ ...(PRESETS[grupoSel] || PRESETS.consulta) });

  const setCampo = (chave, valor) => setMatriz((m) => ({ ...m, [chave]: valor }));

  const salvarMatriz = async () => {
    setSaving(true);
    try {
      const overrides = calcularOverrides(grupoSel, matriz);
      await usuariosAPI.update(modalUser.id, { grupo: grupoSel, permissoes: overrides });
      setModalUser(null);
      await loadUsuarios();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao salvar permissões');
    } finally {
      setSaving(false);
    }
  };

  if (user?.grupo !== 'admin') {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <ShieldAlert size={48} className="mb-4 text-gray-300" />
        <p>Apenas administradores podem gerenciar papéis e permissões.</p>
      </div>
    );
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64">Carregando...</div>;
  }

  const qtdOverrides = Object.keys(calcularOverrides(grupoSel, matriz)).length;

  return (
    <div>
      <div className="flex items-center gap-2 mb-6">
        <ShieldCheck className="text-primary-700" />
        <h1 className="text-2xl font-bold text-gray-800">Grupo de usuários</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {GRUPOS.filter((g) => g.value !== 'usuario').map((g) => (
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
                <th className="text-left py-3 px-4 font-semibold text-gray-600">Papel</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-600">Permissões</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => {
                const temOverride = u.permissoes && Object.keys(u.permissoes).length > 0;
                const ehVoce = u.id === user.id;
                return (
                  <tr key={u.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 font-medium">
                      {u.nome}{ehVoce && <span className="ml-2 text-xs text-gray-400">(você)</span>}
                    </td>
                    <td className="py-3 px-4 text-gray-500">{u.email}</td>
                    <td className="py-3 px-4">
                      <select
                        value={u.grupo || 'usuario'}
                        disabled={savingId === u.id || ehVoce}
                        onChange={(e) => handleChangeGrupo(u, e.target.value)}
                        className="text-sm border border-gray-300 rounded-lg px-2 py-1 disabled:opacity-50"
                      >
                        {GRUPOS.map((g) => (
                          <option key={g.value} value={g.value}>{g.label}</option>
                        ))}
                      </select>
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => abrirMatriz(u)}
                        disabled={ehVoce}
                        className="inline-flex items-center gap-2 text-sm text-primary-700 hover:bg-primary-50 rounded-lg px-2 py-1 disabled:opacity-40"
                      >
                        <SlidersHorizontal size={15} />
                        Ajustar
                      </button>
                      {temOverride && (
                        <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-amber-100 text-amber-700">
                          personalizado
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {modalUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Permissões de {modalUser.nome}</h2>
              <p className="text-sm text-gray-500 mt-1">
                A matriz parte do preset do papel. O que ficar igual ao preset não é salvo
                (o usuário continua herdando o papel).
              </p>
            </div>

            <div className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Papel (preset base)</label>
                <select
                  value={grupoSel}
                  onChange={(e) => trocarPapel(e.target.value)}
                  className="input-field"
                >
                  {GRUPOS.map((g) => (
                    <option key={g.value} value={g.value}>{g.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Recursos</h3>
                <div className="space-y-2">
                  {RECURSOS.map(([chave, label]) => (
                    <div key={chave} className="flex items-center justify-between gap-3">
                      <span className="text-sm text-gray-700">{label}</span>
                      <select
                        value={matriz[chave] || 'nenhum'}
                        onChange={(e) => setCampo(chave, e.target.value)}
                        className="text-sm border border-gray-300 rounded-lg px-2 py-1 w-36"
                      >
                        {NIVEIS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                      </select>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Escopo das tarefas</h3>
                <select
                  value={matriz.escopo_tarefas || 'todas'}
                  onChange={(e) => setCampo('escopo_tarefas', e.target.value)}
                  className="input-field"
                >
                  {ESCOPOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Ações sensíveis</h3>
                <div className="space-y-1">
                  {FLAGS.map(([chave, label]) => (
                    <label key={chave} className="flex items-center gap-2 py-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={!!matriz[chave]}
                        onChange={(e) => setCampo(chave, e.target.checked)}
                        className="w-4 h-4 accent-primary-600"
                      />
                      <span className="text-sm text-gray-700">{label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-gray-200 flex items-center gap-3">
              <span className="text-xs text-gray-500 mr-auto">
                {qtdOverrides === 0 ? 'Igual ao preset' : `${qtdOverrides} ajuste(s) sobre o preset`}
              </span>
              <button type="button" onClick={restaurarPreset} className="btn-secondary">
                Restaurar preset
              </button>
              <button type="button" onClick={() => setModalUser(null)} className="btn-secondary">
                Cancelar
              </button>
              <button type="button" onClick={salvarMatriz} disabled={saving} className="btn-primary">
                {saving ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
