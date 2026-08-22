import { useState, useEffect } from 'react';
import { configuracaoAPI, alertasAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { Bell, Mail, MessageCircle, Clock, Save, Send, Sparkles, PlayCircle } from 'lucide-react';

export default function Notificacoes() {
  const [cfg, setCfg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testEmail, setTestEmail] = useState('');
  const [msg, setMsg] = useState(null);
  const [slotEnsaio, setSlotEnsaio] = useState('principal');
  const [ensaio, setEnsaio] = useState(null);
  const [ensaiando, setEnsaiando] = useState(false);
  const [msgAberta, setMsgAberta] = useState(null);
  const [zap, setZap] = useState(null);
  const [conferindoZap, setConferindoZap] = useState(false);

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

  // Cruza os colaboradores daqui com os usuários cadastrados no ZapContábil.
  const conferirZap = async () => {
    setConferindoZap(true); setMsg(null);
    try {
      const { data } = await configuracaoAPI.zapUsuarios();
      setZap(data);
    } catch (e) {
      setMsg({ ok: false, txt: mensagemDeErro(e, 'Erro ao consultar o ZapContábil') });
    } finally { setConferindoZap(false); }
  };

  // Ensaio: roda a verificação de agora e mostra o que sairia, sem enviar.
  const rodarEnsaio = async () => {
    setEnsaiando(true); setMsg(null); setMsgAberta(null);
    try {
      const { data } = await alertasAPI.verificar({ slot: slotEnsaio, ensaio: true });
      setEnsaio(data);
    } catch (e) {
      setMsg({ ok: false, txt: mensagemDeErro(e, 'Erro ao rodar o ensaio') });
    } finally { setEnsaiando(false); }
  };

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

        {/* Conferência do cadastro. O alerta do time sai pelo número que o Zap
            tem para aquele e-mail; e-mail escrito diferente nos dois cadastros
            joga a pessoa em silêncio para o canal de reserva -- ela recebe por
            e-mail e ninguém percebe que o WhatsApp nunca chegou. */}
        <div className="card">
          <div className="flex items-center gap-2 mb-1">
            <MessageCircle size={18} className="text-green-600" />
            <h2 className="text-xl font-semibold">Colaboradores no ZapContábil</h2>
          </div>
          <p className="text-xs text-gray-500 mb-3">
            São dois cadastros lá, e cada um responde por uma coisa. O <strong>contato</strong> dá o
            número para onde a mensagem vai; o <strong>atendente</strong> dá o id que faz o atendimento
            nascer na conta da pessoa, em vez de cair num balaio comum. O <strong>e-mail</strong> liga
            os três cadastros. Quem não casar recebe por e-mail sem avisar ninguém — é por isso que
            esta conferência existe.
          </p>
          <button onClick={conferirZap} disabled={conferindoZap} className="btn-secondary flex items-center gap-2">
            <MessageCircle size={16} /> {conferindoZap ? 'Consultando…' : 'Conferir cadastro'}
          </button>

          {zap && (
            <div className="mt-3 border-t border-gray-100 pt-3 text-sm">
              <p className="mb-2">
                <strong>{zap.contatos}</strong> contato(s) no Zap,{' '}
                <strong>{zap.contatos_com_numero}</strong> com número •{' '}
                <strong>{zap.atendentes}</strong> atendente(s).
              </p>
              {zap.contatos === 0 && (
                <p className="text-xs text-red-700 mb-1">
                  A API não devolveu contato nenhum. Confira a chave e se o canal está ativo —
                  sem isso o time todo cai no e-mail.
                </p>
              )}
              {zap.casaram?.length > 0 && (
                <p className="text-xs text-green-800 mb-1">
                  ✓ {zap.casaram.length} com WhatsApp e atendimento direcionado:{' '}
                  {zap.casaram.map((c) => c.nome).join(', ')}
                </p>
              )}
              {zap.so_numero?.length > 0 && (
                <p className="text-xs text-amber-700 mb-1">
                  ⚠ Recebem o WhatsApp, mas o atendimento não vai para a conta deles
                  (são contato, não atendente): {zap.so_numero.map((c) => c.nome).join(', ')}
                </p>
              )}
              {zap.fora_do_zap?.length > 0 && (
                <p className="text-xs text-gray-600 mb-1">
                  Não achei nos contatos (confira a grafia do e-mail):{' '}
                  {zap.fora_do_zap.map((c) => `${c.nome}${c.telefone_no_tareffas ? ' (usa o telefone daqui)' : ' (vai por e-mail)'}`).join(', ')}
                </p>
              )}
              <details className="mt-2">
                <summary className="text-xs text-gray-400 cursor-pointer">campos que a API devolveu</summary>
                <p className="text-[11px] text-gray-500 font-mono mt-1">
                  contato: {zap.campos_contato?.join(', ') || '—'}<br />
                  usuário: {zap.campos_usuario?.join(', ') || '—'}
                </p>
              </details>
            </div>
          )}
        </div>

        {/* Ensaio. Existe porque o alerta de verdade sai para o WhatsApp e o
            e-mail do CLIENTE: conferir a régua em produção, sem isto, seria
            mandar mensagem para cliente real. Roda a mesma lógica do horário
            agendado e mostra o que sairia. */}
        <div className="card">
          <div className="flex items-center gap-2 mb-1">
            <PlayCircle size={18} className="text-primary-700" />
            <h2 className="text-xl font-semibold">Ensaio do alerta</h2>
          </div>
          <p className="text-xs text-gray-500 mb-2">
            Roda agora a mesma verificação do horário agendado e mostra quem receberia o quê —
            <strong> sem enviar nada</strong>. É assim que se confere a régua sem disparar mensagem para cliente real.
          </p>
          <p className="text-xs text-gray-500 mb-3">
            <MessageCircle size={12} className="inline text-green-600" /> Quem é do escritório
            (responsável, gestores e supervisor) recebe por <strong>WhatsApp</strong>, no número que o
            ZapContábil tem para o e-mail dele; o e-mail entra só como reserva de quem não tem número.{' '}
            <Mail size={12} className="inline text-blue-600" /> O <strong>cliente</strong> recebe
            por e-mail e/ou WhatsApp, conforme o que estiver preenchido na empresa.
          </p>
          <div className="flex flex-wrap items-center gap-3 mb-1">
            <select value={slotEnsaio} onChange={(e) => setSlotEnsaio(e.target.value)}
              className="input-field w-auto">
              <option value="principal">Horário principal</option>
              <option value="extra">Horário extra</option>
            </select>
            <button onClick={rodarEnsaio} disabled={ensaiando} className="btn-secondary flex items-center gap-2">
              <PlayCircle size={16} /> {ensaiando ? 'Rodando…' : 'Ver o que sairia agora'}
            </button>
          </div>

          {ensaio && (
            <div className="mt-3 border-t border-gray-100 pt-3">
              <p className="text-sm mb-2">
                <strong>{ensaio.tarefas}</strong> tarefa(s) na régua,{' '}
                <strong>{ensaio.destinatarios}</strong> destinatário(s).
              </p>
              {ensaio.tarefas === 0 && (
                <p className="text-xs text-gray-500">
                  Nenhuma tarefa se encaixa neste horário. A régua avisa com a antecedência configurada acima,
                  no dia anterior, no dia do prazo e enquanto estiver atrasada — o horário extra só pega
                  o que vence hoje ou já venceu.
                </p>
              )}
              {ensaio.alertas.map((a) => (
                <div key={a.tarefa_id} className="border-t border-gray-100 py-2 first:border-t-0">
                  <div className="flex flex-wrap items-baseline gap-x-2">
                    <strong className="text-[13px] text-gray-800">{a.tarefa_titulo}</strong>
                    <span className="text-xs text-gray-500">{a.empresa}</span>
                    <span className="ml-auto text-xs text-gray-600 tabular-nums">
                      {a.dias_restantes < 0 ? `atrasada há ${-a.dias_restantes} dia(s)`
                        : a.dias_restantes === 0 ? 'vence hoje'
                        : `faltam ${a.dias_restantes} dia(s)`}
                    </span>
                  </div>
                  <ul className="mt-1 space-y-0.5">
                    {a.despachos.map((d, i) => (
                      <li key={i} className="text-xs text-gray-600 flex items-center gap-1.5">
                        {d.canal === 'whatsapp'
                          ? <MessageCircle size={12} className="shrink-0 text-green-600" />
                          : <Mail size={12} className="shrink-0 text-blue-600" />}
                        <span className="font-medium">{d.papel}</span>
                        <span className="truncate">{d.nome}</span>
                        <span className="text-gray-400 truncate">{d.endereco}</span>
                      </li>
                    ))}
                  </ul>
                  <button type="button" onClick={() => setMsgAberta(msgAberta === a.tarefa_id ? null : a.tarefa_id)}
                    className="text-xs text-primary-700 underline mt-1">
                    {msgAberta === a.tarefa_id ? 'esconder a mensagem' : 'ver a mensagem que sairia'}
                  </button>
                  {msgAberta === a.tarefa_id && (
                    <pre className="mt-1 p-2 rounded-lg bg-gray-50 text-[11px] whitespace-pre-wrap font-sans text-gray-700">{a.mensagem}</pre>
                  )}
                </div>
              ))}
            </div>
          )}
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
