import httpx
import re
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Tarefa, Usuario, Empresa, StatusTarefa
from .email import send_email
from . import config as cfgmod


async def send_whatsapp_message(phone: str, message: str, cfg: dict) -> dict:
    if not cfgmod.ativo(cfg, "whatsapp_ativo"):
        return {"success": False, "error": "WhatsApp desativado", "skipped": True}
    api_key = (cfg.get("zap_api_key") or "").strip()
    if not api_key:
        return {"success": False, "error": "ZAP_API_KEY não configurada", "skipped": True}
    url = cfg.get("zap_url") or "https://api-bps4.zapcontabil.chat"
    try:
        conn_from = int(cfg.get("zap_connection_from") or 0)
    except (TypeError, ValueError):
        conn_from = 0
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"body": message, "connectionFrom": conn_from}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{url}/api/send/{phone}", json=payload, headers=headers, timeout=30.0)
        return {"success": response.status_code == 200, "status_code": response.status_code, "response": response.text}


def _base_date(tarefa: Tarefa):
    """O prazo interno comanda os alertas; se não houver, cai no vencimento."""
    return tarefa.data_prazo or tarefa.data_vencimento


def should_notify(days_remaining: int, slot: str, dias_antes: int = 3) -> bool:
    """Regras de disparo por proximidade do prazo interno.
    slot 'principal' = horários principais ; slot 'extra' = extras.
      - `dias_antes` e 1 dia antes  -> só nos horários principais
      - no dia do prazo e atrasada  -> em todos os horários
    """
    if days_remaining is None:
        return False
    if days_remaining <= 0:  # vence hoje ou já atrasada -> todos os horários
        return True
    if slot == "principal" and days_remaining in (1, dias_antes):
        return True
    return False


def format_task_message(tarefa: Tarefa, days_remaining: int, responsavel: Usuario = None) -> str:
    empresa_nome = tarefa.empresa.razao_social or tarefa.empresa.nome_fantasia
    setor_nome = tarefa.setor.nome if tarefa.setor else "Não definido"

    if days_remaining < 0:
        urgency = f"🚨 *ATRASADA há {abs(days_remaining)} dia(s)!*"
    elif days_remaining == 0:
        urgency = "⚠️ *PRAZO INTERNO VENCE HOJE!*"
    elif days_remaining == 1:
        urgency = "⏰ *Prazo interno vence amanhã!*"
    else:
        urgency = f"📋 Prazo interno em *{days_remaining} dias*"

    base = _base_date(tarefa)
    prazo_str = base.strftime("%d/%m/%Y %H:%M") if base else "-"

    linhas = [
        urgency, "",
        f"*Tarefa:* {tarefa.titulo}",
        f"*Empresa:* {empresa_nome}",
        f"*Setor:* {setor_nome}",
        f"*Prazo interno:* {prazo_str}",
    ]
    if tarefa.data_vencimento:
        multa = " ⚠️ *GERA MULTA*" if tarefa.gera_multa else ""
        linhas.append(f"*Vencimento:* {tarefa.data_vencimento.strftime('%d/%m/%Y')}{multa}")
    if responsavel:
        linha = f"*Responsável:* {responsavel.nome}"
        if responsavel.gestor:
            linha += f"  (gestor: {responsavel.gestor.nome})"
        linhas.append(linha)
    linhas.append(f"*Prioridade:* {tarefa.prioridade.value.upper()}")
    linhas += ["", "Por favor, verifique e atualize o status desta tarefa."]
    return "\n".join(linhas)


def _texto_simples(msg: str) -> str:
    """Versão sem marcação de WhatsApp (asteriscos) para corpo de e-mail."""
    return re.sub(r"\*", "", msg)


def _cadeia_gestores(usuario, niveis: int) -> list:
    """Sobe a cadeia de gestores (gestor, gestor-do-gestor, ...) até `niveis`."""
    chain, seen, atual = [], {usuario.id}, usuario.gestor
    while atual and niveis > 0 and atual.id not in seen:
        chain.append(atual)
        seen.add(atual.id)
        atual = atual.gestor
        niveis -= 1
    return chain


def destinatarios_alerta(tarefa: Tarefa, subs_map: dict = None, niveis: int = 2) -> list:
    """Quem recebe o alerta e por qual canal:
    - responsáveis + a cadeia de gestores deles (N níveis) + supervisor -> e-mail
    - cliente (empresa da tarefa) -> WhatsApp + e-mail
    `subs_map` {ausente_id: substituto}: quem está de férias/doença é trocado pelo substituto
    (mas o gestor do ausente continua na cópia).
    """
    subs_map = subs_map or {}
    dest = []
    vistos = set()
    for u in list(tarefa.responsaveis):
        alvo = subs_map.get(u.id, u)  # ausente -> substituto recebe no lugar
        if alvo and alvo.email and alvo.email not in vistos:
            vistos.add(alvo.email)
            dest.append({"papel": "substituto" if alvo.id != u.id else "colaborador",
                         "nome": alvo.nome, "canal": "email", "endereco": alvo.email})
        for g in _cadeia_gestores(u, niveis):
            if g.email and g.email not in vistos:
                vistos.add(g.email)
                dest.append({"papel": "gestor", "nome": g.nome,
                             "canal": "email", "endereco": g.email})
    sup = tarefa.supervisor
    if sup and sup.email and sup.email not in vistos:
        vistos.add(sup.email)
        dest.append({"papel": "supervisor", "nome": sup.nome,
                     "canal": "email", "endereco": sup.email})
    empresa = tarefa.empresa
    if empresa:
        if empresa.telefone:
            dest.append({"papel": "cliente", "nome": empresa.razao_social,
                         "canal": "whatsapp", "endereco": empresa.telefone})
        if empresa.email:
            dest.append({"papel": "cliente", "nome": empresa.razao_social,
                         "canal": "email", "endereco": empresa.email})
    return dest


async def _enviar(canal: str, endereco: str, assunto: str, mensagem: str, cfg: dict) -> dict:
    if canal == "whatsapp":
        return await send_whatsapp_message(endereco, mensagem, cfg)
    if canal == "email":
        return send_email(endereco, assunto, _texto_simples(mensagem), cfg)
    return {"success": False, "error": f"canal desconhecido: {canal}"}


async def check_and_send_alerts(db: Session, slot: str = "principal") -> list:
    """Varre tarefas em aberto (excluindo bloqueadas) e dispara alertas por canal."""
    from .substituicao import mapa_substitutos
    cfg = cfgmod.carregar(db)
    try:
        dias_antes = int(cfg.get("alert_dias_antes") or 3)
    except (TypeError, ValueError):
        dias_antes = 3
    try:
        niveis = int(cfg.get("alert_gestor_niveis") or 2)
    except (TypeError, ValueError):
        niveis = 2

    alerts_sent = []
    now = datetime.now()
    subs_map = mapa_substitutos(db)

    # Bloqueados somem dos alertas também (empresa ou responsável principal bloqueado).
    tarefas = (db.query(Tarefa)
               .filter(Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO]),
                       ~Tarefa.empresa.has(Empresa.bloqueado == True),
                       ~Tarefa.responsavel.has(Usuario.bloqueado == True))
               .all())

    for tarefa in tarefas:
        base = _base_date(tarefa)
        if not base:
            continue
        days_remaining = (base.date() - now.date()).days
        if not should_notify(days_remaining, slot, dias_antes):
            continue

        responsavel = None
        if tarefa.responsavel_id:
            responsavel = db.query(Usuario).filter(Usuario.id == tarefa.responsavel_id).first()

        message = format_task_message(tarefa, days_remaining, responsavel)
        try:
            from .upload import link_publico
            link = link_publico(cfg, tarefa, db)
            message += f"\n\n📎 Enviar o comprovante: {link}"
        except Exception:
            pass
        assunto = f"[Tareffas] {tarefa.titulo} - {tarefa.empresa.razao_social}"

        despachos = []
        for d in destinatarios_alerta(tarefa, subs_map, niveis):
            r = await _enviar(d["canal"], d["endereco"], assunto, message, cfg)
            despachos.append({**d, "enviado": r.get("success", False),
                              "skipped": r.get("skipped", False), "detalhe": r})

        alerts_sent.append({
            "tarefa_id": tarefa.id,
            "tarefa_titulo": tarefa.titulo,
            "responsavel": responsavel.nome if responsavel else None,
            "dias_restantes": days_remaining,
            "despachos": despachos,
        })

    return alerts_sent
