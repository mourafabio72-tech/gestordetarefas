import { useState, useEffect } from 'react';
import { configuracaoAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { Bell, Mail, MessageCircle, Clock, Save, Send, Sparkles } from 'lucide-react';

export default function Notificacoes() {
  const [cfg, setCfg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testEmail, setTestEmail] = useState('');
  const [msg, setMsg] = useState(null);

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      const { data } = await configuracaoAPI.getNotificacoes();
      setCfg(data);
    } catch (e) {
      console.error('Erro ao carregar config:', e);
    } finally { setLoading(false); }
  };

  const set = (k, v) => setCfg((c) => ({ ...c, [k]: v }));
  const bool = (v) => String(v) === '1' || v === true;

  const salvar = async () => {
    setSaving(true); setMsg(null);
    try {
      // Só envia segredos se o usuário digitou algo (senão mantém o guardado).
      const payload = { ...cfg };
      if (!payload.smtp_pass) delete payload.smtp_pass;
      if (!payload.zap_api_key) delete payload.zap_api_key;
      if (!payload.openai_api_key) delete payload.openai_api_key;
      const { data } = await configuracaoAPI.putNotificacoes(payload);
      setCfg(data);
      setMsg({ ok: true, txt: 'Configuração salva. Os horários já valem para os próximos disparos.' });
    } catch (e) {
      setMsg({ ok: false, txt: mensagemDeErro(e, 'Erro ao salvar') });
    } finally { setSaving(false); }
  };

  const enviarTeste = async () => {
    // Lê do campo também (o autofill do navegador não dispara o onChange do React).
    const email = (testEmail || document.getElementById('teste-email')?.value || '').trim();
    if (!email) {
      setMsg({ ok: false, txt: 'Informe um e-mail no campo "Testar envio para".' });
      return;
    }
    setMsg(null);
    try {
      // Salva o que está na tela ANTES de testar (o teste usa a config salva).
      const payload = { ...cfg };
      if (!payload.smtp_pass) delete payload.smtp_pass;
      if (!payload.zap_api_key) delete payload.zap_api_key;
      if (!payload.openai_api_key) delete payload.openai_api_key;
      const { data: salvo } = await configuracaoAPI.putNotificacoes(payload);
      setCfg(salvo);
      const { data } = await configuracaoAPI.testarEmail(email);
      setMsg(data.success
        ? { ok: true, txt: `E-mail de teste enviado para ${email}. Confira a caixa de entrada (e o spam).` }
        : { ok: false, txt: `Não enviou: ${data.error || 'verifique o SMTP'}` });
    } catch (e) {
      setMsg({ ok: false, txt: mensagemDeErro(e, 'Erro ao testar') });
    }
  };

  const enviarTesteIA = async () => {
    setMsg(null);
    try {
      const payload = { ...cfg };
      if (!payload.smtp_pass) delete payload.smtp_pass;
      if (!payload.zap_api_key) delete payload.zap_api_key;
      if (!payload.openai_api_key) delete payload.openai_api_key;
      const { data: salvo } = await configuracaoAPI.putNotificacoes(payload);
      setCfg(salvo);
      const { data } = await configuracaoAPI.testarIA();
      setMsg(data.ok
        ? { ok: true, txt: `IA respondeu (${data.modelo}): "${data.resposta}". Chave OK ✅` }
        : { ok: false, txt: `IA não respondeu: ${data.erro || 'verifique a chave/modelo'}` });
    } catch (e) {
      setMsg({ ok: false, txt: mensagemDeErro(e, 'Erro ao testar IA') });
    }
  };

  const enviarTesteWhats = async () => {
    const numero = (document.getElementById('teste-whats')?.value || '').trim();
    if (!numero) {
      setMsg({ ok: false, txt: 'Informe um número (ex.: 5521999998888) no teste de WhatsApp.' });
      return;
    }
    setMsg(null);
    try {
      const payload = { ...cfg };
      if (!payload.smtp_pass) delete payload.smtp_pass;
      if (!payload.zap_api_key) delete payload.zap_api_key;
      if (!payload.openai_api_key) delete payload.openai_api_key;
      await configuracaoAPI.putNotificacoes(payload);
      const { data } = await configuracaoAPI.testarWhatsapp(numero);
      setMsg(data.success
        ? { ok: true, txt: `WhatsApp de teste enviado para ${numero}.` }
        : { ok: false, txt: `Não enviou: ${data.error || 'verifique o WhatsApp/ZAP'}` });
    } catch (e) {
      setMsg({ ok: false, txt: mensagemDeErro(e, 'Erro ao testar WhatsApp') });
    }
  };

  if (loading || !cfg) return <div className="flex items-center justify-center h-64">Carregando...</div>;

  const Toggle = ({ chave, label }) => (
    <label className="flex items-center gap-2 cursor-pointer">
      <input type="checkbox" checked={bool(cfg[chave])} onChange={(e) => set(chave, e.target.checked ? '1' : '0')} className="h-4 w-4" />
      <span className="text-sm text-gray-700">{label}</span>
    </label>
  );
  const Campo = ({ chave, label, tipo = 'text', ph = '', hint = '' }) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input type={tipo} value={cfg[chave] ?? ''} onChange={(e) => set(chave, e.target.value)} className="input-field" placeholder={ph} />
      {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
    </div>
  );

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-2 mb-6">
        <Bell className="text-primary-700" />
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Notificações</h1>
          <p className="text-sm text-gray-500">Configure os canais, os horários e as regras dos alertas de tarefas.</p>
        </div>
      </div>

      {msg && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm ${msg.ok ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {msg.txt}
        </div>
      )}

      <div className="space-y-6">
        {/* Regras / agendamento */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4"><Clock size={18} className="text-primary-700" /><h2 className="font-semibold">Agendamento e regras</h2></div>
          <div className="grid grid-cols-2 gap-4">
            <Campo chave="horarios_principal" label="Horários principais" ph="09:30,17:45" hint="Avisam N dias antes, 1 dia antes, no dia e atrasadas." />
            <Campo chave="horarios_extra" label="Horários extras" ph="14:30,16:00" hint="Avisam só no dia do prazo e atrasadas." />
            <Campo chave="alert_dias_antes" label="Antecedência (dias antes)" tipo="number" hint="Quantos dias antes do prazo começar a avisar." />
            <Campo chave="alert_gestor_niveis" label="Níveis de gestor na cópia" tipo="number" hint="Ex.: 2 = gestor direto + gestor do gestor." />
          </div>
        </div>

        {/* E-mail */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2"><Mail size={18} className="text-primary-700" /><h2 className="font-semibold">E-mail (SMTP)</h2></div>
            <Toggle chave="email_ativo" label="Envio de e-mail ativo" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Campo chave="smtp_host" label="Servidor (host)" ph="smtp.gmail.com" />
            <Campo chave="smtp_port" label="Porta" ph="587" />
            <Campo chave="smtp_user" label="Usuário" ph="conta@dominio.com" />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
              <input type="password" value={cfg.smtp_pass ?? ''} onChange={(e) => set('smtp_pass', e.target.value)} className="input-field"
                placeholder={cfg.smtp_pass_set ? '•••••• (guardada, deixe vazio p/ manter)' : 'senha do SMTP'} />
            </div>
            <Campo chave="smtp_from" label="Remetente (From)" ph="Gestor <no-reply@dominio.com>" />
            <div className="flex items-end pb-2"><Toggle chave="smtp_tls" label="Usar TLS (recomendado)" /></div>
          </div>
          <div className="border-t border-gray-100 mt-4 pt-4 flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Testar envio para</label>
              <input id="teste-email" type="email" value={testEmail} onChange={(e) => setTestEmail(e.target.value)} className="input-field" placeholder="seu@email.com" />
            </div>
            <button onClick={enviarTeste} className="btn-secondary flex items-center gap-2 h-fit">
              <Send size={16} /> Enviar teste
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2">Salve as configurações antes de testar.</p>
        </div>

        {/* WhatsApp */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2"><MessageCircle size={18} className="text-primary-700" /><h2 className="font-semibold">WhatsApp (ZapContábil)</h2></div>
            <Toggle chave="whatsapp_ativo" label="Envio de WhatsApp ativo" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Campo chave="zap_url" label="URL da API" ph="https://api-bps4.zapcontabil.chat" />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
              <input type="password" value={cfg.zap_api_key ?? ''} onChange={(e) => set('zap_api_key', e.target.value)} className="input-field"
                placeholder={cfg.zap_api_key_set ? '•••••• (guardada, deixe vazio p/ manter)' : 'token da API'} />
            </div>
            <Campo chave="zap_phone" label="Número de envio" ph="5521999998888" />
            <Campo chave="zap_connection_from" label="Conexão (connectionFrom)" ph="0" />
          </div>
          <div className="border-t border-gray-100 mt-4 pt-4 flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Testar envio para (número)</label>
              <input id="teste-whats" type="text" className="input-field" placeholder="5521999998888" />
            </div>
            <button onClick={enviarTesteWhats} className="btn-secondary flex items-center gap-2 h-fit">
              <Send size={16} /> Enviar teste
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2">Envia uma mensagem de teste ao número informado (formato 55 + DDD + número).</p>
        </div>

        {/* IA (e-validador) */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2"><Sparkles size={18} className="text-primary-700" /><h2 className="font-semibold">IA: reforço do e-validador (OpenAI)</h2></div>
            <Toggle chave="ia_ativo" label="Usar IA no e-validador" />
          </div>
          <p className="text-xs text-gray-500 mb-3">
            Quando o método por palavra-chave não resolve, a IA lê o texto do documento e identifica CNPJ, competência e a obrigação. Só texto (não escaneado) e só nos casos difíceis.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">API Key (OpenAI)</label>
              <input type="password" value={cfg.openai_api_key ?? ''} onChange={(e) => set('openai_api_key', e.target.value)} className="input-field"
                placeholder={cfg.openai_api_key_set ? '•••••• (guardada, deixe vazio p/ manter)' : 'sk-...'} />
            </div>
            <Campo chave="openai_model" label="Modelo" ph="gpt-4o-mini" />
          </div>
          <div className="border-t border-gray-100 mt-4 pt-4 flex items-center gap-3">
            <button onClick={enviarTesteIA} className="btn-secondary flex items-center gap-2">
              <Sparkles size={16} /> Testar IA
            </button>
            <span className="text-xs text-gray-400">Salva a chave e faz um ping na OpenAI (sem precisar de documento).</span>
          </div>
        </div>

        <div className="flex justify-end">
          <button onClick={salvar} disabled={saving} className="btn-primary flex items-center gap-2">
            <Save size={18} /> {saving ? 'Salvando...' : 'Salvar configuração'}
          </button>
        </div>
      </div>
    </div>
  );
}
