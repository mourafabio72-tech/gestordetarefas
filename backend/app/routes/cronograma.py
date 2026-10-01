from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel
from ..database import get_db
from ..models import Usuario, Obrigacao
from ..auth import require_perm
from ..services import importador_cronograma as cron

router = APIRouter(prefix="/cronograma", tags=["cronograma"])


@router.get("/modelo-importacao")
def modelo_importacao(current_user: Usuario = Depends(require_perm("obrigacoes", "editar"))):
    return Response(
        content=cron.gerar_modelo(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=modelo_importacao_obrigacoes.xlsx"},
    )


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
    mapa: Dict[str, Any] = {}   # {codigo_entidade: empresa_id}
    para_todas: bool = True     # obrigações valem para todas as empresas (sem grudar CNPJ)


@router.post("/importar")
def importar(
    body: ImportarBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    if not body.itens:
        raise HTTPException(status_code=422, detail="Nada para importar.")
    # Obrigação NOVA sem setor fura a matriz da empresa e gera para todas.
    # Recusa o lote inteiro antes de gravar, com os nomes, para a tela mostrar
    # o que falta escolher. A que já existe só ganha vínculo, não setor.
    novas_sem_setor = [
        (it.get("nome") or "").strip() for it in body.itens
        if (it.get("nome") or "").strip() and not (it.get("setor") or "").strip()
        and not db.query(Obrigacao.id).filter(
            Obrigacao.nome == (it.get("nome") or "").strip()).first()]
    if novas_sem_setor:
        raise HTTPException(status_code=422, detail="Escolha o setor de: "
                            + ", ".join(novas_sem_setor))
    return cron.importar(db, body.grupo, body.itens, body.mapa, para_todas=body.para_todas)
