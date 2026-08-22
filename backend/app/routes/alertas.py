from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Usuario
from ..auth import get_current_user, require_admin
from ..services.whatsapp import check_and_send_alerts

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.post("/verificar")
async def verificar_tarefas(
    slot: str = "principal",
    ensaio: bool = True,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    """Roda a verificação de alertas fora do horário agendado.

    `ensaio=true` é o padrão de propósito: o alerta de verdade sai para o
    WhatsApp e o e-mail do CLIENTE, e uma chamada acidental nesta rota mandaria
    mensagem para cliente real. Para disparar mesmo, é preciso pedir
    explicitamente `ensaio=false`.
    """
    r = await check_and_send_alerts(db, slot=slot, ensaio=ensaio)
    tarefas, mensagens = r["tarefas"], r["mensagens"]
    verbo = "sairiam" if ensaio else "saíram"
    return {
        "ensaio": ensaio,
        "slot": slot,
        # Duas contagens diferentes: cada pessoa recebe UMA mensagem com a lista
        # dela, então 400 tarefas na régua podem virar 40 mensagens.
        "tarefas": len(tarefas),
        "destinatarios": len(mensagens),
        "message": f"{len(tarefas)} tarefa(s) na régua, {len(mensagens)} mensagem(ns) {verbo}.",
        "alertas": tarefas,
        "mensagens": mensagens,
    }


@router.post("/enviar/{usuario_id}")
async def enviar_alerta_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    from ..models import Tarefa, StatusTarefa
    from ..services.whatsapp import send_whatsapp_message, format_task_message, _base_date
    from ..services import config as cfgmod
    from datetime import datetime

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    cfg = cfgmod.carregar(db)
    zap_phone = cfg.get("zap_phone") or ""
    tarefas = db.query(Tarefa).filter(
        Tarefa.responsavel_id == usuario_id,
        Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO])
    ).all()

    now = datetime.now()
    results = []

    for tarefa in tarefas:
        base = _base_date(tarefa)
        days_remaining = (base.date() - now.date()).days if base else 0
        message_wa = format_task_message(tarefa, days_remaining, usuario)
        wa_result = await send_whatsapp_message(zap_phone, message_wa, cfg)

        results.append({
            "tarefa_id": tarefa.id,
            "tarefa_titulo": tarefa.titulo,
            "whatsapp_enviado": wa_result.get("success", False)
        })

    return {
        "message": f"{len(results)} alertas enviados para {usuario.nome}",
        "results": results
    }
