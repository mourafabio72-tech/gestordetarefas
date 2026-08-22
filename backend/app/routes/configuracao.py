from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel
from ..database import get_db
from ..models import Usuario
from ..auth import require_admin
from ..services import config as cfgmod
from ..services.email import send_email

router = APIRouter(prefix="/configuracao", tags=["configuracao"])


@router.get("/notificacoes")
def get_notificacoes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    return cfgmod.para_api(cfgmod.carregar(db))


@router.put("/notificacoes")
def put_notificacoes(
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    cfgmod.salvar(db, body)
    try:
        from ..services.scheduler import reconfigurar_alertas
        reconfigurar_alertas(db)
    except Exception:
        pass
    return cfgmod.para_api(cfgmod.carregar(db))


class TesteEmail(BaseModel):
    para: str


@router.post("/notificacoes/testar-email")
def testar_email(
    body: TesteEmail,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    cfg = cfgmod.carregar(db)
    return send_email(
        body.para,
        "[Tareffas] E-mail de teste",
        "Este é um e-mail de teste do Tareffas.\n\n"
        "Se você recebeu esta mensagem, o envio de e-mail está funcionando.",
        cfg,
    )


class TesteWhatsapp(BaseModel):
    para: str  # número no formato 55DDDNUMERO


@router.post("/notificacoes/testar-whatsapp")
async def testar_whatsapp(
    body: TesteWhatsapp,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    from ..services.whatsapp import send_whatsapp_message
    cfg = cfgmod.carregar(db)
    numero = "".join(ch for ch in (body.para or "") if ch.isdigit())
    return await send_whatsapp_message(
        numero,
        "🔔 *Teste do Tareffas*\n\nSe você recebeu esta mensagem, o envio por WhatsApp está funcionando.",
        cfg,
    )


@router.get("/notificacoes/zap-usuarios")
async def zap_usuarios(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    """Cruza os colaboradores do Tareffas com os usuários do ZapContábil.

    O alerta do time sai pelo número que o Zap tem para aquele e-mail. Sem esta
    conferência, um e-mail escrito diferente nos dois cadastros joga a pessoa
    silenciosamente para o canal de reserva -- ela recebe por e-mail e ninguém
    percebe que o WhatsApp nunca chegou.
    """
    from ..services.whatsapp import usuarios_zap, mapa_por_email, CAMPOS_NUMERO_ZAP
    cfg = cfgmod.carregar(db)
    lista = await usuarios_zap(cfg)
    mapa = mapa_por_email(lista)
    emails_zap = {str(u.get("email") or "").strip().lower()
                  for u in lista if isinstance(u, dict)}

    casaram, sem_numero, fora = [], [], []
    for u in db.query(Usuario).filter(Usuario.bloqueado != True).all():
        email = (u.email or "").strip().lower()
        item = {"nome": u.nome, "email": u.email}
        if email in mapa:
            casaram.append({**item, "numero": mapa[email]})
        elif email in emails_zap:
            sem_numero.append(item)
        else:
            fora.append({**item, "telefone_no_tareffas": bool(u.telefone)})

    return {
        "no_zap": len(lista),
        "com_numero": len(mapa),
        # As chaves que a API devolveu — serve para descobrir em qual campo o
        # telefone vem nesta instalação, se nenhum dos candidatos acertar.
        "campos": sorted({k for u in lista if isinstance(u, dict) for k in u}),
        "campos_procurados": list(CAMPOS_NUMERO_ZAP),
        "casaram": casaram,
        "no_zap_sem_numero": sem_numero,
        "fora_do_zap": fora,
    }


@router.post("/notificacoes/testar-ia")
def testar_ia(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    from ..services import ia as ia_mod
    return ia_mod.testar(cfgmod.carregar(db))
