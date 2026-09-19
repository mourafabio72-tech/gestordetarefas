from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Usuario
from ..auth import require_perm
from ..services.validador import processar

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
    """Recebe comprovantes de entrega (PDF), extrai as chaves e baixa as tarefas."""
    resultados = []
    for arq in arquivos:
        conteudo = await arq.read()
        try:
            res = processar(db, arq.filename, conteudo)
        except Exception as e:
            resultados.append({"arquivo": arq.filename, "status": "erro",
                               "detalhe": f"Falha ao ler o PDF: {e}"})
            continue
        if res.get("status") == "pronta_para_envio":
            res.update(await _enviar_guia(db, res["tarefa_id"], current_user.id))
        resultados.append(res)
    resumo = {}
    for r in resultados:
        resumo[r["status"]] = resumo.get(r["status"], 0) + 1
    return {"resumo": resumo, "resultados": resultados}
