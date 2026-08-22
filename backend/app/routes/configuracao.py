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
    """Cruza os colaboradores do Tareffas com o cadastro do ZapContábil.

    São dois cadastros lá, e cada um responde por uma coisa: o CONTATO dá o
    número para onde a mensagem vai; o USUÁRIO dá o id que faz o atendimento
    nascer na conta da pessoa. O e-mail é o que liga os três.

    Sem esta conferência, um e-mail escrito diferente joga a pessoa em silêncio
    para o canal de reserva: ela recebe por e-mail e ninguém percebe que o
    WhatsApp nunca chegou.
    """
    from ..services.whatsapp import (contatos_zap, usuarios_zap,
                                     mapa_numero_por_email, mapa_userid_por_email)
    cfg = cfgmod.carregar(db)
    contatos = await contatos_zap(cfg)
    atendentes = await usuarios_zap(cfg)
    numeros = mapa_numero_por_email(contatos)
    uids = mapa_userid_por_email(atendentes)

    casaram, so_numero, fora = [], [], []
    for u in db.query(Usuario).filter(Usuario.bloqueado != True).all():
        email = (u.email or "").strip().lower()
        item = {"nome": u.nome, "email": u.email}
        if email in numeros and email in uids:
            casaram.append({**item, "numero": numeros[email], "zap_user_id": uids[email]})
        elif email in numeros:
            so_numero.append(item)
        else:
            fora.append({**item, "telefone_no_tareffas": bool(u.telefone)})

    return {
        "contatos": len(contatos),
        "contatos_com_numero": len(numeros),
        "atendentes": len(atendentes),
        # As chaves que a API devolveu de fato — se um dia o schema mudar, o
        # diagnóstico aparece aqui em vez de virar investigação.
        "campos_contato": sorted({k for c in contatos for k in c}),
        "campos_usuario": sorted({k for a in atendentes for k in a}),
        "casaram": casaram,
        "so_numero": so_numero,
        "fora_do_zap": fora,
    }


@router.post("/notificacoes/testar-ia")
def testar_ia(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    from ..services import ia as ia_mod
    return ia_mod.testar(cfgmod.carregar(db))
