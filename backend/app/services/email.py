"""Envio de e-mail (SMTP). Configuração vem do banco (Configuração → Notificações),
com fallback para variáveis de ambiente. No-op gracioso se não configurado."""
import mimetypes
import smtplib
from email.message import EmailMessage


def send_email(to: str, subject: str, body: str, cfg: dict, anexos: list = None) -> dict:
    """Envia um e-mail. `anexos` é uma lista de (nome, bytes).

    O tipo de cada anexo é adivinhado pela extensão: sem isso tudo viraria
    octet-stream e o cliente de e-mail ofereceria "baixar arquivo desconhecido"
    no lugar de abrir o PDF da guia.
    """
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
        for nome, conteudo in (anexos or []):
            tipo, _ = mimetypes.guess_type(nome)
            maior, menor = (tipo or "application/octet-stream").split("/", 1)
            msg.add_attachment(conteudo, maintype=maior, subtype=menor, filename=nome)
        with smtplib.SMTP(host, port, timeout=30) as s:
            if usa_tls:
                s.starttls()
            if user:
                s.login(user, senha)
            s.send_message(msg)
        return {"success": True}
    except Exception as e:  # pragma: no cover
        return {"success": False, "error": str(e)}
