import { useState, useEffect } from 'react';
import { usuariosAPI, empresasAPI, setoresAPI, gruposAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { Plus, Edit2, Trash2, Users as UsersIcon, Lock, Unlock, Upload, Download, Send } from 'lucide-react';
import { CARGOS } from '../permissoes';
import { useAuth } from '../contexts/AuthContext';

const FORM_VAZIO = {
  nome: '', email: '', senha: '', cargo: '', grupo: 'analista', telefone: '',
  tipo: 'colaborador', empresa_id: '', gestor_id: '', setor_id: '',
};

const cargoInfo = (cargo) => CARGOS.find((c) => c.value === cargo) || CARGOS[2]; // fallback Analista
const grupoParaCargo = (grupo) => (CARGOS.find((c) => c.grupo === grupo)?.value) || 'Analista';

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [setores, setSetores] = useState([]);
  const [grupos, setGrupos] = useState([]);
  const [filtros, setFiltros] = useState({ nome: '', email: '', cargo: '', status: '' });

  const statusDe = (u) => (u.bloqueado ? 'bloqueado' : u.ativado === false ? 'pendente' : (u.ativo ? 'ativo' : 'inativo'));
  const usuariosFiltrados = usuarios.filter((u) => {
    const c = (s) => (s || '').toLowerCase();
    if (filtros.nome && !c(u.nome).includes(c(filtros.nome))) return false;
    if (filtros.email && !c(u.email).includes(c(filtros.email))) return false;
    if (filtros.cargo && !c(u.cargo).includes(c(filtros.cargo))) return false;
    if (filtros.status && statusDe(u) !== filtros.status) return false;
    return true;
  });
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingUsuario, setEditingUsuario] = useState(null);
  const [formData, setFormData] = useState(FORM_VAZIO);
  const [bloqModal, setBloqModal] = useState(null);      // { usuario, carga }
  const [bloqSubstituto, setBloqSubstituto] = useState('');
  const { user } = useAuth();

  // Bloquear/desbloquear a partir do modal de edição (fecha o modal e roda o fluxo padrão).
  const bloquearDoModal = () => {
    const u = editingUsuario;
    setShowModal(false);
    handleBloquear(u);
  };

  const [importando, setImportando] = useState(false);
  const importarArquivo = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setImportando(true);
    try {
      const { data } = await usuariosAPI.importar(file);
      if (data.erro) { alert(data.erro); return; }
      const r = data.resumo || {};
      const temps = (data.detalhes || []).filter((d) => d.detalhe && d.detalhe.startsWith('senha temporária'));
      let msg = `Importação: ${r.criadas} criado(s), ${r.atualizadas} atualizado(s), ${r.erros} erro(s).`;
      if (temps.length) {
        msg += `\n\nSenhas temporárias (anote e repasse, o usuário troca depois):\n` +
          temps.map((d) => `• ${d.linha}: ${d.detalhe.replace('senha temporária: ', '')}`).join('\n');
      }
      const avisos = (data.detalhes || []).filter((d) => d.status === 'erro' || d.status === 'aviso');
      if (avisos.length) msg += `\n\nAvisos:\n` + avisos.map((d) => `• ${d.linha}: ${d.detalhe}`).join('\n');
      alert(msg);
      loadUsuarios();
    } catch (err) {
      alert(mensagemDeErro(err, 'Erro ao importar usuários.'));
    } finally { setImportando(false); }
  };

  const [convidandoId, setConvidandoId] = useState(null);
  const [convidandoLote, setConvidandoLote] = useState(false);
  const enviarConvite = async (usuario) => {
    setConvidandoId(usuario.id);
    try {
      const { data } = await usuariosAPI.convite(usuario.id);
      alert(`Convite enviado a ${usuario.nome} por ${data.canal === 'whatsapp' ? 'WhatsApp' : 'e-mail'}.`);
      loadUsuarios();
    } catch (err) {
      alert(mensagemDeErro(err, 'Não consegui enviar o convite.'));
    } finally { setConvidandoId(null); }
  };
  const convidarPendentes = async () => {
    if (!confirm('Enviar convite de primeiro acesso para todos os usuários pendentes?')) return;
    setConvidandoLote(true);
    try {
      const { data } = await usuariosAPI.conviteLote(null);
      let msg = `${data.enviados}/${data.total} convite(s) enviado(s).`;
      if (data.falhas?.length) msg += `\n\nFalhas:\n` + data.falhas.map((f) => `• ${f.nome}: ${f.erro}`).join('\n');
      alert(msg);
      loadUsuarios();
    } catch (err) {
      alert(mensagemDeErro(err, 'Erro ao enviar convites.'));
    } finally { setConvidandoLote(false); }
  };

  useEffect(() => {
    loadUsuarios();
  }, []);

  const loadUsuarios = async () => {
    try {
      const [u, e, s, g] = await Promise.all([
        usuariosAPI.list(), empresasAPI.list(), setoresAPI.list(), gruposAPI.list().catch(() => ({ data: [] })),
      ]);
      setUsuarios(u.data);
      setEmpresas(e.data);
      setSetores(s.data);
      setGrupos(g.data);
    } catch (error) {
      console.error('Erro ao carregar usuários:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const cliente = formData.tipo === 'cliente';
      const payload = {
        ...formData,
        empresa_id: cliente && formData.empresa_id ? parseInt(formData.empresa_id) : null,
        gestor_id: (cliente || !formData.gestor_id) ? null : parseInt(formData.gestor_id),
        setor_id: (cliente || !formData.setor_id) ? null : parseInt(formData.setor_id),
      };
      if (editingUsuario) {
        if (!payload.senha) delete payload.senha;
        await usuariosAPI.update(editingUsuario.id, payload);
      } else {
        await usuariosAPI.create(payload);
      }
      setShowModal(false);
      setEditingUsuario(null);
      setFormData(FORM_VAZIO);
      loadUsuarios();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao salvar usuário'));
    }
  };

  const handleEdit = (usuario) => {
    setEditingUsuario(usuario);
    setFormData({
      nome: usuario.nome,
      email: usuario.email,
      senha: '',
      cargo: usuario.cargo || '',
      grupo: usuario.grupo || 'analista',
      telefone: usuario.telefone || '',
      tipo: usuario.tipo || 'colaborador',
      empresa_id: usuario.empresa_id || '',
      gestor_id: usuario.gestor_id || '',
      setor_id: usuario.setor_id || '',
    });
    setShowModal(true);
  };

  const handleBloquear = async (usuario) => {
    if (usuario.bloqueado) {
      if (!confirm('Desbloquear este usuário?')) return;
      try { await usuariosAPI.bloquear(usuario.id, false); loadUsuarios(); }
      catch (error) { alert(mensagemDeErro(error, 'Erro ao desbloquear')); }
      return;
    }
    // Bloqueando: verifica se há carga em aberto para oferecer transferência.
    try {
      const { data } = await usuariosAPI.carga(usuario.id);
      if (data.abertas > 0) {
        setBloqSubstituto('');
        setBloqModal({ usuario, carga: data.abertas });
      } else {
        if (!confirm('Bloquear este usuário? Ele não conseguirá logar e sai das seleções.')) return;
        await usuariosAPI.bloquear(usuario.id, true);
        loadUsuarios();
      }
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao verificar carga do usuário'));
    }
  };

  const confirmarBloqueio = async (comTransferencia) => {
    const sub = comTransferencia ? parseInt(bloqSubstituto) : null;
    if (comTransferencia && !sub) return;
    try {
      await usuariosAPI.bloquear(bloqModal.usuario.id, true, sub);
      setBloqModal(null);
      loadUsuarios();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao bloquear usuário'));
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Excluir este usuário? Se tiver obrigações/tarefas/empresas vinculadas, ele será apenas inativado.')) return;
    try {
      const { data } = await usuariosAPI.delete(id);
      if (data?.message) alert(data.message);
      loadUsuarios();
    } catch (error) {
      alert(mensagemDeErro(error, 'Erro ao excluir usuário'));
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">Carregando...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Usuários</h1>
        <div className="flex gap-2">
          {usuarios.some((u) => u.ativado === false && !u.bloqueado) && (
            <button onClick={convidarPendentes} disabled={convidandoLote}
              className="btn-secondary flex items-center gap-2"
              title="Enviar convite de primeiro acesso a todos os pendentes">
              <Send size={18} /> {convidandoLote ? 'Enviando…' : 'Convidar pendentes'}
            </button>
          )}
          <button onClick={() => usuariosAPI.baixarModelo()} className="btn-secondary flex items-center gap-2"
            title="Baixar planilha-modelo para importação de usuários">
            <Download size={18} /> Baixar modelo
          </button>
          <label className={`btn-secondary flex items-center gap-2 cursor-pointer ${importando ? 'opacity-60 pointer-events-none' : ''}`}
            title="Importar usuários de uma planilha (upsert por e-mail)">
            <Upload size={18} /> {importando ? 'Importando…' : 'Importar'}
            <input type="file" accept=".xlsx,.xls" className="hidden" onChange={importarArquivo} />
          </label>
          <button
            onClick={() => {
              setEditingUsuario(null);
              setFormData(FORM_VAZIO);
              setShowModal(true);
            }}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={18} />
            Novo Usuário
          </button>
        </div>
      </div>

      <div className="card mb-4 p-2">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <input className="input-field py-1.5 text-sm" placeholder="Nome"
            value={filtros.nome} onChange={(e) => setFiltros({ ...filtros, nome: e.target.value })} />
          <input className="input-field py-1.5 text-sm" placeholder="E-mail"
            value={filtros.email} onChange={(e) => setFiltros({ ...filtros, email: e.target.value })} />
          <input className="input-field py-1.5 text-sm" placeholder="Cargo"
            value={filtros.cargo} onChange={(e) => setFiltros({ ...filtros, cargo: e.target.value })} />
          <select className="input-field py-1.5 text-sm" value={filtros.status}
            onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}>
            <option value="">Todos os status</option>
            <option value="ativo">Ativo</option>
            <option value="pendente">Pendente</option>
            <option value="bloqueado">Bloqueado</option>
            <option value="inativo">Inativo</option>
          </select>
        </div>
      </div>

      <div className="card">
        {usuarios.length === 0 ? (
          <div className="text-center py-12">
            <UsersIcon size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">Nenhum usuário cadastrado</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table-app">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left font-semibold text-gray-600">Nome</th>
                  <th className="text-left font-semibold text-gray-600">Email</th>
                  <th className="text-left font-semibold text-gray-600">Cargo</th>
                  <th className="text-left font-semibold text-gray-600">Status</th>
                  <th className="text-right font-semibold text-gray-600">Ações</th>
                </tr>
              </thead>
              <tbody>
                {usuariosFiltrados.map((usuario) => (
                  <tr key={usuario.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center font-medium">
                          {usuario.nome.charAt(0).toUpperCase()}
                        </div>
                        <span className="font-medium">{usuario.nome}</span>
                      </div>
                    </td>
                    <td className="text-gray-500">{usuario.email}</td>
                    <td>{usuario.cargo || '-'}</td>
                    <td>
                      {usuario.bloqueado ? (
                        <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-700">Bloqueado</span>
                      ) : usuario.ativado === false ? (
                        <span className="px-2 py-1 text-xs rounded-full bg-amber-100 text-amber-700">Pendente</span>
                      ) : (
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          usuario.ativo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                        }`}>
                          {usuario.ativo ? 'Ativo' : 'Inativo'}
                        </span>
                      )}
                    </td>
                    <td>
                      <div className="flex justify-end gap-2">
                        {usuario.ativado === false && !usuario.bloqueado && (
                          <button
                            onClick={() => enviarConvite(usuario)}
                            disabled={convidandoId === usuario.id}
                            title="Enviar convite de primeiro acesso"
                            className="p-2 text-primary-700 hover:bg-primary-50 rounded-lg transition-colors disabled:opacity-50"
                          >
                            <Send size={16} />
                          </button>
                        )}
                        <button
                          onClick={() => handleBloquear(usuario)}
                          title={usuario.bloqueado ? 'Desbloquear' : 'Bloquear'}
                          className={`p-2 rounded-lg transition-colors ${usuario.bloqueado ? 'text-green-600 hover:bg-green-50' : 'text-amber-600 hover:bg-amber-50'}`}
                        >
                          {usuario.bloqueado ? <Unlock size={16} /> : <Lock size={16} />}
                        </button>
                        <button
                          onClick={() => handleEdit(usuario)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          onClick={() => handleDelete(usuario.id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">
                {editingUsuario ? 'Editar Usuário' : 'Novo Usuário'}
              </h2>
            </div>
            <form onSubmit={handleSubmit} className="p-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  className="input-field"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="input-field"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {editingUsuario ? 'Nova Senha (deixe vazio para manter)' : 'Senha *'}
                </label>
                <input
                  type="password"
                  value={formData.senha}
                  onChange={(e) => setFormData({ ...formData, senha: e.target.value })}
                  className="input-field"
                  required={!editingUsuario}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nível</label>
                <select
                  value={formData.tipo === 'cliente' ? '__cliente__' : (formData.grupo || '')}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (v === '__cliente__') {
                      setFormData({ ...formData, tipo: 'cliente', grupo: 'consulta' });
                    } else {
                      setFormData({ ...formData, tipo: 'colaborador', grupo: v, empresa_id: '' });
                    }
                  }}
                  className="input-field"
                >
                  {grupos
                    .filter((g) => g.ativo && (g.slug !== 'usuario' || formData.grupo === 'usuario'))
                    .map((g) => (
                      <option key={g.slug} value={g.slug}>{g.label}</option>
                    ))}
                  {/* fallback: grupo atual não listado (lista ainda não carregou) */}
                  {formData.tipo !== 'cliente' && formData.grupo
                    && !grupos.some((g) => g.slug === formData.grupo) && (
                    <option value={formData.grupo}>{formData.grupo}</option>
                  )}
                  <option value="__cliente__">Cliente (acesso externo)</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  {formData.tipo === 'cliente'
                    ? 'Cliente: alerta por WhatsApp + e-mail (contatos da empresa).'
                    : 'Colaborador: alerta por e-mail. O nível define as permissões.'}
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cargo</label>
                <input
                  value={formData.cargo}
                  onChange={(e) => setFormData({ ...formData, cargo: e.target.value })}
                  className="input-field"
                  placeholder="Função, ex.: Assistente, Coordenadora, Sócio"
                />
              </div>
              {formData.tipo === 'cliente' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Empresa do cliente *</label>
                  <select
                    value={formData.empresa_id}
                    onChange={(e) => setFormData({ ...formData, empresa_id: e.target.value })}
                    className="input-field"
                    required
                  >
                    <option value="">Selecione</option>
                    {empresas.map((e) => (
                      <option key={e.id} value={e.id}>{e.razao_social}</option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">Os alertas usam o WhatsApp e o e-mail cadastrados nesta empresa.</p>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Telefone WhatsApp</label>
                <input
                  type="tel"
                  value={formData.telefone}
                  onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
                  className="input-field"
                  placeholder="Ex: 11999998888"
                />
                <p className="text-xs text-gray-500 mt-1">Formato: DDD + Número</p>
              </div>
              {formData.tipo !== 'cliente' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Setor</label>
                  <select
                    value={formData.setor_id}
                    onChange={(e) => setFormData({ ...formData, setor_id: e.target.value })}
                    className="input-field"
                  >
                    <option value="">Sem setor</option>
                    {setores.filter((s) => s.ativo !== false).map((s) => (
                      <option key={s.id} value={s.id}>{s.nome}</option>
                    ))}
                  </select>
                </div>
              )}
              {formData.tipo !== 'cliente' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Gestor direto</label>
                  <select
                    value={formData.gestor_id}
                    onChange={(e) => setFormData({ ...formData, gestor_id: e.target.value })}
                    className="input-field"
                  >
                    <option value="">Sem gestor</option>
                    {usuarios
                      .filter(u => u.id !== editingUsuario?.id && u.tipo !== 'cliente' && !u.bloqueado)
                      .map(u => (
                        <option key={u.id} value={u.id}>{u.nome}{u.cargo ? ` (${u.cargo})` : ''}</option>
                      ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">Recebe cópia dos alertas. O gestor do gestor (2º nível) também é avisado.</p>
                </div>
              )}
              {editingUsuario && editingUsuario.id !== user?.id && (
                <div className="border-t border-gray-100 pt-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-gray-700">Situação do acesso</p>
                      <p className="text-xs text-gray-500">
                        {editingUsuario.bloqueado
                          ? 'Bloqueado: não loga e as tarefas dele somem.'
                          : 'Ativo: pode logar e receber tarefas.'}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={bloquearDoModal}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${
                        editingUsuario.bloqueado
                          ? 'text-green-700 bg-green-50 hover:bg-green-100'
                          : 'text-red-700 bg-red-50 hover:bg-red-100'}`}
                    >
                      {editingUsuario.bloqueado ? <Unlock size={16} /> : <Lock size={16} />}
                      {editingUsuario.bloqueado ? 'Desbloquear' : 'Bloquear'}
                    </button>
                  </div>
                </div>
              )}
              <div className="flex gap-3 pt-4">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">
                  Cancelar
                </button>
                <button type="submit" className="btn-primary flex-1">
                  {editingUsuario ? 'Salvar' : 'Cadastrar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {bloqModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Bloquear {bloqModal.usuario.nome}</h2>
              <p className="text-sm text-gray-500 mt-1">
                Esta pessoa tem <strong>{bloqModal.carga} tarefa(s) em aberto</strong>. Transferir para quem antes de bloquear?
              </p>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Transferir carga para</label>
                <select value={bloqSubstituto} onChange={(e) => setBloqSubstituto(e.target.value)} className="input-field">
                  <option value="">Selecione o substituto</option>
                  {usuarios
                    .filter((u) => u.id !== bloqModal.usuario.id && u.tipo !== 'cliente' && !u.bloqueado)
                    .map((u) => <option key={u.id} value={u.id}>{u.nome}{u.cargo ? ` (${u.cargo})` : ''}</option>)}
                </select>
                <p className="text-xs text-gray-500 mt-1">Reatribui as tarefas em aberto + o padrão de empresas/obrigações (substituição definitiva).</p>
              </div>
              <div className="flex flex-col gap-2 pt-2">
                <button type="button" onClick={() => confirmarBloqueio(true)} disabled={!bloqSubstituto} className="btn-primary">
                  Transferir e bloquear
                </button>
                <button type="button" onClick={() => confirmarBloqueio(false)} className="btn-secondary text-red-600">
                  Bloquear sem transferir (as tarefas somem)
                </button>
                <button type="button" onClick={() => setBloqModal(null)} className="btn-secondary">
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
