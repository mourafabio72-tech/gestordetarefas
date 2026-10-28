from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Usuario
from ..auth import require_perm

router = APIRouter(prefix="/evalidador", tags=["evalidador"])


async def _enviar_guia(db, tarefa_id: int, usuario_id: int) -> dict:
    """Guia de "entregar" reconhecida e conferida: sai para o cliente.

    Mesma função do "Enviar ao cliente" da tarefa (decisão 4a de 2026-09-19).
    Se ninguém recebe, a tarefa segue aberta com a guia anexada (3a).
    """
    from ..models import Tarefa
    from ..services import entrega_cliente as ec
    tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    try:
        r = await ec.entregar_saida(db, tarefa, enviado_por=usuario_id, origem="evalidador")
    except ec.SemDestinatario as e:
        return {"status": "sem_destinatario", "detalhe": f"Guia anexada, sem envio: {e}"}
    except (ec.SemDocumento, ec.ArquivoSumiu) as e:
        return {"status": "erro", "detalhe": str(e)}
    except Exception as e:
        # Uma guia com problema não derruba o lote: as outras seguem.
        db.rollback()
        return {"status": "envio_falhou", "detalhe": f"Falha ao enviar: {type(e).__name__}"}
    return {"status": "enviada" if r["concluiu"] else "envio_falhou",
            "detalhe": r["message"], "enviados": r["enviados"], "falhas": r["falhas"]}


@router.post("/processar")
async def processar_comprovantes(
    arquivos: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("evalidador", "editar")),
):
    """Recebe comprovantes de entrega (PDF), extrai as chaves e baixa as tarefas.

    Complementar da guia (mesmo CNPJ e competência, sem obrigação própria)
    vai junto dela ao cliente: ver services/complementares.py.
    """
    from ..services.complementares import processar_lote
    lidos = [(arq.filename, await arq.read()) for arq in arquivos]
    resultados = await processar_lote(
        db, lidos, lambda db_, tid: _enviar_guia(db_, tid, current_user.id))
    resumo = {}
    for r in resultados:
        resumo[r["status"]] = resumo.get(r["status"], 0) + 1
    return {"resumo": resumo, "resultados": resultados}
