import { useState, useEffect, useMemo } from 'react';
import { usuariosAPI, gruposAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { useAuth } from '../contexts/AuthContext';
import { ShieldCheck, ShieldAlert, SlidersHorizontal, Plus, Lock, Unlock, Trash2 } from 'lucide-react';
import {
  RECURSOS, NIVEIS, ESCOPOS, FLAGS, MATRIZ_VAZIA, resolverCom, overridesCom,
} from '../permissoes';

// Editor da matriz (recursos + escopo + ações sensíveis). Reutilizado nos 2 modais.
function MatrizEditor({ matriz, setCampo, disabled }) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Recursos</h3>
        <div className="space-y-2">
          {RECURSOS.map(([chave, label]) => (
            <div key={chave} className="flex items-center justify-between gap-3">
              <span className="text-sm text-gray-700">{label}</span>
              <select
                value={matriz[chave] || 'nenhum'}
                disabled={disabled}
                onChange={(e) => setCampo(chave, e.target.value)}
                className="text-sm border border-gray-300 rounded-lg px-2 py-1 w-36 disabled:opacity-50"
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
          disabled={disabled}
          onChange={(e) => setCampo('escopo_tarefas', e.target.value)}
          className="input-field disabled:opacity-50"
        >
          {ESCOPOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </div>
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Ações sensíveis</h3>
        <div className="space-y-1">
          {FLAGS.map(([chave, label]) => (
            <label key={chave} className={`flex items-center gap-2 py-1 ${disabled ? '' : 'cursor-pointer'}`}>
              <input
                type="checkbox"
                checked={!!matriz[chave]}
                disabled={disabled}
                onChange={(e) => setCampo(chave, e.target.checked)}
                className="w-4 h-4 accent-primary-600"
              />
              <span className="text-sm text-gray-700">{label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Grupos() {
  const { user } = useAuth();
  const [usuarios, setUsuarios] = useState([]);
  const [grupos, setGrupos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);

  // presetsMap: slug -> matriz efetiva (base do grupo, vinda do backend)
  const presetsMap = useMemo(
    () => Object.fromEntries(grupos.map((g) => [g.slug, g.permissoes])), [grupos]);
  const grupoLabel = (slug) => grupos.find((g) => g.slug === slug)?.label || slug;

  // --- Modal de GRUPO (cadastro + matriz) ---
  const [modalGrupo, setModalGrupo] = useState(null); // {novo:bool, slug, sistema}
  const [gLabel, setGLabel] = useState('');
  const [gDesc, setGDesc] = useState('');
  const [gMatriz, setGMatriz] = useState(MATRIZ_VAZIA);
  const [savingGrupo, setSavingGrupo] = useState(false);

  // --- Modal de USUÁRIO (exceção individual) ---
  const [modalUser, setModalUser] = useState(null);
  const [grupoSel, setGrupoSel] = useState('');
  const [matriz, setMatriz] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => { loadTudo(); }, []);

  const loadTudo = async () => {
    try {
      const [u, g] = await Promise.all([usuariosAPI.list(), gruposAPI.list()]);
      setUsuarios(u.data);
      setGrupos(g.data);
    } catch (error) {
      console.error('Erro ao carregar grupos/usuários:', error);
    } finally {
      setLoading(false);
    }
  };

  // ---- Grupo ----
  const abrirNovoGrupo = () => {
    setModalGrupo({ novo: true, slug: null, sistema: false });
    setGLabel(''); setGDesc(''); setGMatriz({ ...MATRIZ_VAZIA });
  };
  const abrirEditGrupo = (g) => {
    setModalGrupo({ novo: false, slug: g.slug, sistema: g.sistema });
    setGLabel(g.label); setGDesc(g.descricao || ''); setGMatriz({ ...g.permissoes });
  };
  const setCampoGrupo = (k, v) => setGMatriz((m) => ({ ...m, [k]: v }));

  const salvarGrupo = async () => {
    if (!gLabel.trim()) return alert('Informe o nome do grupo.');
    setSavingGrupo(true);
    try {
      const ehAdmin = modalGrupo.slug === 'admin';
      if (modalGrupo.novo) {
        await gruposAPI.create({ label: gLabel, descricao: gDesc, permissoes: gMatriz });
      } else {
        await gruposAPI.update(modalGrupo.slug, {
          label: gLabel, descricao: gDesc,
          ...(ehAdmin ? {} : { permissoes: gMatriz }),
        });
      }
      setModalGrupo(null);
      await loadTudo();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao salvar grupo'));
    } finally { setSavingGrupo(false); }
  };

  const alternarStatusGrupo = async (g) => {
    try {
      await gruposAPI.setAtivo(g.slug, !g.ativo);
      await loadTudo();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao alterar o grupo'));
    }
  };

  const excluirGrupo = async (g) => {
    if (!confirm(`Excluir o grupo "${g.label}"? Não dá para desfazer.`)) return;
    try {
      await gruposAPI.delete(g.slug);
      await loadTudo();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao excluir o grupo'));
    }
  };

  // ---- Usuário (papel + exceção) ----
  const handleChangeGrupo = async (usuario, novoGrupo) => {
    setSavingId(usuario.id);
    try {
      await usuariosAPI.update(usuario.id, { grupo: novoGrupo });
      await loadTudo();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao alterar papel'));
    } finally { setSavingId(null); }
  };

  const abrirMatrizUser = (u) => {
    const slug = u.grupo || 'usuario';
    setModalUser(u);
    setGrupoSel(slug);
    setMatriz(resolverCom(presetsMap[slug], u.permissoes));
  };
  const trocarPapelUser = (novo) => {
    setGrupoSel(novo);
    setMatriz({ ...(presetsMap[novo] || MATRIZ_VAZIA) });
  };
  const restaurarPresetUser = () => setMatriz({ ...(presetsMap[grupoSel] || MATRIZ_VAZIA) });
  const setCampoUser = (k, v) => setMatriz((m) => ({ ...m, [k]: v }));

  const salvarMatrizUser = async () => {
    setSaving(true);
    try {
      const overrides = overridesCom(presetsMap[grupoSel], matriz);
      await usuariosAPI.update(modalUser.id, { grupo: grupoSel, permissoes: overrides });
      setModalUser(null);
      await loadTudo();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao salvar permissões'));
    } finally { setSaving(false); }
  };

  if (user?.grupo !== 'admin') {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <ShieldAlert size={48} className="mb-4 text-gray-300" />
        <p>Apenas administradores podem gerenciar papéis e permissões.</p>
      </div>
    );
  }
  if (loading) return <div className="flex items-center justify-center h-64">Carregando...</div>;

  const gruposAtivos = grupos.filter((g) => g.ativo);
  const qtdOverridesUser = modalUser ? Object.keys(overridesCom(presetsMap[grupoSel], matriz)).length : 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <ShieldCheck className="text-primary-700" />
          <h1 className="text-2xl font-bold text-gray-800">Grupo de usuários</h1>
        </div>
        <button onClick={abrirNovoGrupo} className="btn-primary flex items-center gap-2">
          <Plus size={18} /> Novo grupo
        </button>
      </div>

      {/* Cadastro de grupos */}
      <div className="card mb-8">
        <div className="overflow-x-auto">
          <table className="table-app">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-600">
                <th className="font-semibold">Grupo</th>
                <th className="font-semibold">Descrição</th>
                <th className="font-semibold text-center">Usuários</th>
                <th className="font-semibold text-center">Situação</th>
                <th className="font-semibold text-right">Ações</th>
              </tr>
            </thead>
            <tbody>
              {grupos.map((g) => (
                <tr key={g.slug} className={`border-b border-gray-100 ${g.ativo ? '' : 'opacity-60'}`}>
                  <td>
                    <span className="font-medium text-gray-800">{g.label}</span>
                    {g.sistema && <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-500">nativo</span>}
                  </td>
                  <td className="text-gray-500 max-w-md">{g.descricao}</td>
                  <td className="text-center text-gray-600">{g.usuarios}</td>
                  <td className="text-center">
                    {g.ativo
                      ? <span className="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700">Ativo</span>
                      : <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700">Bloqueado</span>}
                  </td>
                  <td>
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => abrirEditGrupo(g)} title="Editar permissões"
                        className="p-1.5 text-primary-700 hover:bg-primary-50 rounded-lg">
                        <SlidersHorizontal size={16} />
                      </button>
                      {g.slug !== 'admin' && (
                        <button onClick={() => alternarStatusGrupo(g)}
                          title={g.ativo ? 'Bloquear' : 'Ativar'}
                          className="p-1.5 text-gray-600 hover:bg-gray-100 rounded-lg">
                          {g.ativo ? <Lock size={16} /> : <Unlock size={16} />}
                        </button>
                      )}
                      {!g.sistema && (
                        <button onClick={() => excluirGrupo(g)} title="Excluir"
                          className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg">
                          <Trash2 size={16} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Usuários */}
      <h2 className="text-xl font-semibold text-gray-800 mb-3">Usuários</h2>
      <div className="card">
        <div className="overflow-x-auto">
          <table className="table-app">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left font-semibold text-gray-600">Nome</th>
                <th className="text-left font-semibold text-gray-600">Email</th>
                <th className="text-left font-semibold text-gray-600">Papel</th>
                <th className="text-left font-semibold text-gray-600">Permissões</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => {
                const temOverride = u.permissoes && Object.keys(u.permissoes).length > 0;
                const ehVoce = u.id === user.id;
                const slug = u.grupo || 'usuario';
                const opts = gruposAtivos.some((g) => g.slug === slug)
                  ? gruposAtivos
                  : [...gruposAtivos, { slug, label: grupoLabel(slug) }];
                return (
                  <tr key={u.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="font-medium">
                      {u.nome}{ehVoce && <span className="ml-2 text-xs text-gray-400">(você)</span>}
                    </td>
                    <td className="text-gray-500">{u.email}</td>
                    <td>
                      <select
                        value={slug}
                        disabled={savingId === u.id || ehVoce}
                        onChange={(e) => handleChangeGrupo(u, e.target.value)}
                        className="text-sm border border-gray-300 rounded-lg px-2 py-1 disabled:opacity-50"
                      >
                        {opts.map((g) => <option key={g.slug} value={g.slug}>{g.label}</option>)}
                      </select>
                    </td>
                    <td>
                      <button onClick={() => abrirMatrizUser(u)} disabled={ehVoce}
                        className="inline-flex items-center gap-2 text-sm text-primary-700 hover:bg-primary-50 rounded-lg px-2 py-1 disabled:opacity-40">
                        <SlidersHorizontal size={15} /> Ajustar
                      </button>
                      {temOverride && (
                        <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-amber-100 text-amber-700">personalizado</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal do GRUPO */}
      {modalGrupo && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">{modalGrupo.novo ? 'Novo grupo' : `Editar grupo`}</h2>
              <p className="text-sm text-gray-500 mt-1">
                As permissões marcadas valem para todos os usuários deste grupo.
              </p>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome do grupo</label>
                <input value={gLabel} onChange={(e) => setGLabel(e.target.value)} className="input-field"
                  placeholder="Ex.: Supervisor Fiscal" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
                <input value={gDesc} onChange={(e) => setGDesc(e.target.value)} className="input-field"
                  placeholder="Para que serve este grupo" />
              </div>
              {modalGrupo.slug === 'admin' ? (
                <p className="text-sm bg-purple-50 text-purple-700 rounded-lg px-3 py-2">
                  O grupo Admin tem acesso total e não pode ser restringido.
                </p>
              ) : (
                <div className="border-t border-gray-100 pt-3">
                  <MatrizEditor matriz={gMatriz} setCampo={setCampoGrupo} disabled={false} />
                </div>
              )}
            </div>
            <div className="p-4 border-t border-gray-200 flex items-center gap-3 justify-end">
              <button type="button" onClick={() => setModalGrupo(null)} className="btn-secondary">Cancelar</button>
              <button type="button" onClick={salvarGrupo} disabled={savingGrupo} className="btn-primary">
                {savingGrupo ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal do USUÁRIO (exceção individual) */}
      {modalUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Permissões de {modalUser.nome}</h2>
              <p className="text-sm text-gray-500 mt-1">
                Parte do grupo. O que ficar igual ao grupo não é salvo (continua herdando).
              </p>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Papel (grupo base)</label>
                <select value={grupoSel} onChange={(e) => trocarPapelUser(e.target.value)} className="input-field">
                  {gruposAtivos.map((g) => <option key={g.slug} value={g.slug}>{g.label}</option>)}
                </select>
              </div>
              <div className="border-t border-gray-100 pt-3">
                <MatrizEditor matriz={matriz} setCampo={setCampoUser} disabled={false} />
              </div>
            </div>
            <div className="p-4 border-t border-gray-200 flex items-center gap-3">
              <span className="text-xs text-gray-500 mr-auto">
                {qtdOverridesUser === 0 ? 'Igual ao grupo' : `${qtdOverridesUser} ajuste(s) sobre o grupo`}
              </span>
              <button type="button" onClick={restaurarPresetUser} className="btn-secondary">Restaurar grupo</button>
              <button type="button" onClick={() => setModalUser(null)} className="btn-secondary">Cancelar</button>
              <button type="button" onClick={salvarMatrizUser} disabled={saving} className="btn-primary">
                {saving ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
