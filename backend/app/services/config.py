"""Configurações do sistema (chave-valor). Notificações/alertas.
Valor vem do banco; se não houver, cai no default (variável de ambiente)."""
import os
from ..models import Configuracao

DEFAULTS = {
    "email_ativo": "1" if os.getenv("SMTP_HOST") else "0",
    "smtp_host": os.getenv("SMTP_HOST", ""),
    "smtp_port": os.getenv("SMTP_PORT", "587"),
    "smtp_user": os.getenv("SMTP_USER", ""),
    "smtp_pass": os.getenv("SMTP_PASS", ""),
    "smtp_from": os.getenv("SMTP_FROM", ""),
    "smtp_tls": os.getenv("SMTP_TLS", "1"),
    "whatsapp_ativo": "1" if os.getenv("ZAP_API_KEY") else "0",
    "zap_url": os.getenv("ZAP_API_URL", "https://api-bps4.zapcontabil.chat"),
    "zap_api_key": os.getenv("ZAP_API_KEY", ""),
    "zap_phone": os.getenv("ZAP_PHONE", "5521971985815"),
    "zap_connection_from": os.getenv("ZAP_CONNECTION_FROM", "0"),
    "alert_dias_antes": os.getenv("ALERT_DAYS_BEFORE", "3"),
    "alert_gestor_niveis": os.getenv("ALERT_GESTOR_NIVEIS", "2"),
    "horarios_principal": "09:30,17:45",
    "horarios_extra": "14:30,16:00",
    "public_url": os.getenv("PUBLIC_URL", "https://gestordetarefas.zoaria.com.br"),
}
SEGREDOS = {"smtp_pass", "zap_api_key"}


def carregar(db) -> dict:
    cfg = dict(DEFAULTS)
    for row in db.query(Configuracao).all():
        if row.chave in DEFAULTS:
            cfg[row.chave] = row.valor
    return cfg


def salvar(db, dados: dict):
    for k, v in dados.items():
        if k not in DEFAULTS:
            continue
        # segredo vazio => não sobrescreve (mantém o valor guardado)
        if k in SEGREDOS and (v is None or v == ""):
            continue
        row = db.query(Configuracao).filter(Configuracao.chave == k).first()
        if row:
            row.valor = str(v)
        else:
            db.add(Configuracao(chave=k, valor=str(v)))
    db.commit()


def para_api(cfg: dict) -> dict:
    """Mascara segredos para a tela: não devolve senha/apikey, só se está preenchido."""
    out = dict(cfg)
    for k in SEGREDOS:
        out[k + "_set"] = bool((cfg.get(k) or "").strip())
        out[k] = ""
    return out


def ativo(cfg: dict, chave: str) -> bool:
    return str(cfg.get(chave, "0")).lower() in ("1", "true")
