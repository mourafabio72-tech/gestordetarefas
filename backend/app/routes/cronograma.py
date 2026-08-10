from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel
from ..database import get_db
from ..models import Usuario
from ..auth import require_perm
from ..services import importador_cronograma as cron

router = APIRouter(prefix="/cronograma", tags=["cronograma"])


@router.post("/analisar")
async def analisar(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    conteudo = await arquivo.read()
    try:
        return cron.analisar(conteudo)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Falha ao ler o cronograma: {e}")


class ImportarBody(BaseModel):
    grupo: str
    itens: List[Dict[str, Any]]


@router.post("/importar")
def importar(
    body: ImportarBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    if not body.itens:
        raise HTTPException(status_code=422, detail="Nada para importar.")
    return cron.importar(db, body.grupo, body.itens)
