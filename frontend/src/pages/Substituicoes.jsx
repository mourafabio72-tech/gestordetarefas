import { useState, useEffect } from 'react';
import { substituicoesAPI, usuariosAPI } from '../services/api';
import { UserCog, Plus, X, Plane, LogOut } from 'lucide-react';

const FORM_VAZIO = {
  usuario_id: '', substituto_id: '', tipo: 'temporaria',
  data_inicio: '', data_fim: '', motivo: '',
};

const fmt = (d) => (d ? new Date(d + 'T00:00').toLocaleDateString('pt-BR') : '-');

export default function Substituicoes() {
  const [subs, setSubs] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(FORM_VAZIO);
  const [saving, setSaving] = useState(false);

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      const [s, u] = await Promise.all([substituicoesAPI.list(), usuariosAPI.list()]);
      setSubs(s.data);
      setUsuarios(u.data.filter((x) => x.tipo !== 'cliente' && !x.bloqueado));
    } catch (e) {
      console.error('Erro ao carregar:', e);
    } finally { setLoading(false); }
  };

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const salvar = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        usuario_id: parseInt(form.usuario_id),
        substituto_id: parseInt(form.substituto_id),
        tipo: form.tipo,
        data_inicio: form.tipo === 'temporaria' ? form.data_inicio || null : null,
        data_fim: form.tipo === 'temporaria' ? form.data_fim || null : null,
        motivo: form.motivo || null,
      };
      if (form.tipo === 'definitiva' &&
        !confirm('A substituição DEFINITIVA reatribui agora todas as tarefas em aberto, o padrão das empresas e das obrigações. Confirmar?')) {
        setSaving(false); return;
      }
      await substituicoesAPI.create(payload);
      setShowModal(false); setForm(FORM_VAZIO); load();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao salvar substituição');
    } finally { setSaving(false); }
  };

  const encerrar = async (s) => {
    if (!confirm('Encerrar esta substituição?')) return;
    try { await substituicoesAPI.encerrar(s.id); load(); }
    catch { alert('Erro ao encerrar'); }
  };

  if (loading) return <div className="flex items-center justify-center h-64">Carregando...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-2">
          <UserCog className="text-primary-700" />
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Substituições</h1>
            <p className="text-sm text-gray-500">Troque o responsável por férias/doença (temporária) ou de forma definitiva.</p>
          </div>
        </div>
        <button onClick={() => { setForm(FORM_VAZIO); setShowModal(true); }} className="btn-primary flex items-center gap-2">
          <Plus size={18} /> Nova Substituição
        </button>
      </div>

      <div className="card">
        {subs.length === 0 ? (
          <div className="text-center py-12">
            <UserCog size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">Nenhuma substituição cadastrada</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Ausente</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Substituto</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Tipo</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Período</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Motivo</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-600">Situação</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-600">Ações</th>
                </tr>
              </thead>
              <tbody>
                {subs.map((s) => (
                  <tr key={s.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 font-medium">{s.usuario?.nome}</td>
                    <td className="py-3 px-4">{s.substituto?.nome}</td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${
                        s.tipo === 'definitiva' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}`}>
                        {s.tipo === 'definitiva' ? <LogOut size={12} /> : <Plane size={12} />}
                        {s.tipo === 'definitiva' ? 'Definitiva' : 'Temporária'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-500">
                      {s.tipo === 'temporaria' ? `${fmt(s.data_inicio)} → ${fmt(s.data_fim)}` : '-'}
                    </td>
                    <td className="py-3 px-4 text-gray-500">{s.motivo || '-'}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${s.ativa ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {s.ativa ? 'Ativa' : 'Encerrada'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      {s.ativa && s.tipo === 'temporaria' && (
                        <button onClick={() => encerrar(s)} title="Encerrar" className="p-2 text-red-600 hover:bg-red-50 rounded-lg">
                          <X size={16} />
                        </button>
                      )}
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
              <h2 className="text-xl font-semibold">Nova Substituição</h2>
            </div>
            <form onSubmit={salvar} className="p-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Pessoa ausente *</label>
                <select value={form.usuario_id} onChange={(e) => set('usuario_id', e.target.value)} className="input-field" required>
                  <option value="">Selecione</option>
                  {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nome}{u.cargo ? ` (${u.cargo})` : ''}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Substituto *</label>
                <select value={form.substituto_id} onChange={(e) => set('substituto_id', e.target.value)} className="input-field" required>
                  <option value="">Selecione</option>
                  {usuarios.filter((u) => String(u.id) !== form.usuario_id).map((u) => (
                    <option key={u.id} value={u.id}>{u.nome}{u.cargo ? ` (${u.cargo})` : ''}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo *</label>
                <select value={form.tipo} onChange={(e) => set('tipo', e.target.value)} className="input-field">
                  <option value="temporaria">Temporária (férias/doença): reverte no fim</option>
                  <option value="definitiva">Definitiva: reatribui tudo agora</option>
                </select>
              </div>
              {form.tipo === 'temporaria' && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Início *</label>
                    <input type="date" value={form.data_inicio} onChange={(e) => set('data_inicio', e.target.value)} className="input-field" required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Fim</label>
                    <input type="date" value={form.data_fim} onChange={(e) => set('data_fim', e.target.value)} className="input-field" />
                  </div>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Motivo</label>
                <input type="text" value={form.motivo} onChange={(e) => set('motivo', e.target.value)} className="input-field" placeholder="Ex: Férias, Licença médica" />
              </div>
              <p className="text-xs text-gray-500">
                {form.tipo === 'temporaria'
                  ? 'Durante o período, o substituto assume as tarefas e recebe os alertas (o gestor do ausente segue na cópia).'
                  : 'Reatribui imediatamente todas as tarefas em aberto e o padrão de empresas/obrigações.'}
              </p>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancelar</button>
                <button type="submit" disabled={saving} className="btn-primary flex-1">{saving ? 'Salvando...' : 'Salvar'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
