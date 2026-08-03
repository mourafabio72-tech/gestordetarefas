"""Envio de e-mail (SMTP). Configuração vem do banco (Configuração → Notificações),
com fallback para variáveis de ambiente. No-op gracioso se não configurado."""
import smtplib
from email.message import EmailMessage


def send_email(to: str, subject: str, body: str, cfg: dict) -> dict:
    if not to:
        return {"success": False, "error": "destinatário vazio"}
    if str(cfg.get("email_ativo", "0")).lower() not in ("1", "true"):
        return {"success": False, "error": "e-mail desativado", "skipped": True}
    host = (cfg.get("smtp_host") or "").strip()
    if not host:
        return {"success": False, "error": "SMTP não configurado", "skipped": True}
    try:
        port = int(cfg.get("smtp_port") or 587)
        user = cfg.get("smtp_user") or ""
        senha = cfg.get("smtp_pass") or ""
        remetente = (cfg.get("smtp_from") or user or "no-reply@gestordetarefas.local")
        usa_tls = str(cfg.get("smtp_tls", "1")).lower() in ("1", "true")

        msg = EmailMessage()
        msg["From"] = remetente
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(host, port, timeout=30) as s:
            if usa_tls:
                s.starttls()
            if user:
                s.login(user, senha)
            s.send_message(msg)
        return {"success": True}
    except Exception as e:  # pragma: no cover
        return {"success": False, "error": str(e)}
