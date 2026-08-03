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
        "[Gestor de Tarefas] E-mail de teste",
        "Este é um e-mail de teste do Gestor de Tarefas.\n\n"
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
        "🔔 *Teste do Gestor de Tarefas*\n\nSe você recebeu esta mensagem, o envio por WhatsApp está funcionando.",
        cfg,
    )
