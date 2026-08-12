"""Convite de primeiro acesso: gera um token, monta o link de ativação e envia
pelo canal certo. Regra de canal pelo TIPO do usuário:
  - cliente  -> WhatsApp (ZapContábil) no telefone; sem telefone, cai no e-mail.
  - colaborador -> e-mail (SMTP).
A pessoa abre o link e define a própria senha (o admin nunca vê a senha)."""
import secrets
from . import config as cfgmod
from . import email as email_mod
from . import whatsapp as zap_mod


def gerar_token() -> str:
    return secrets.token_urlsafe(24)


def _link(cfg: dict, token: str) -> str:
    base = (cfg.get("public_url") or "").rstrip("/")
    return f"{base}/ativar/{token}"


def _msg(usuario, link: str) -> str:
    return (
        f"Olá, {usuario.nome}! Seu acesso ao Tareffas foi criado.\n"
        f"Defina sua senha e entre por este link (válido por alguns dias):\n{link}"
    )


async def enviar(db, usuario, cfg: dict) -> dict:
    """Gera/renova o token, salva no usuário e dispara pelo canal do tipo.
    Retorna {canal, ok, erro}. Não faz commit — quem chama commita."""
    token = gerar_token()
    usuario.convite_token = token
    if usuario.ativado is None:
        usuario.ativado = False
    link = _link(cfg, token)
    corpo = _msg(usuario, link)

    # cliente com telefone -> WhatsApp; senão e-mail
    if usuario.tipo == "cliente" and (usuario.telefone or "").strip():
        fone = "".join(ch for ch in usuario.telefone if ch.isdigit())
        r = await zap_mod.send_whatsapp_message(fone, corpo, cfg)
        if r.get("success"):
            return {"canal": "whatsapp", "ok": True, "erro": None}
        # fallback e-mail se o Whats falhar/estiver off
        if not usuario.email:
            return {"canal": "whatsapp", "ok": False, "erro": r.get("error") or "Falha no WhatsApp"}

    if not usuario.email:
        return {"canal": "email", "ok": False, "erro": "Usuário sem e-mail nem telefone válido."}
    r = email_mod.send_email(usuario.email, "Acesso ao Tareffas", corpo, cfg)
    return {"canal": "email", "ok": bool(r.get("success")), "erro": r.get("error")}
