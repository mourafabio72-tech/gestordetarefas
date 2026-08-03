from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Usuario
from ..auth import require_perm
from ..services.validador import processar

router = APIRouter(prefix="/evalidador", tags=["evalidador"])


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
            resultados.append(processar(db, arq.filename, conteudo))
        except Exception as e:
            resultados.append({"arquivo": arq.filename, "status": "erro",
                               "detalhe": f"Falha ao ler o PDF: {e}"})
    resumo = {}
    for r in resultados:
        resumo[r["status"]] = resumo.get(r["status"], 0) + 1
    return {"resumo": resumo, "resultados": resultados}
