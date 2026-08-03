from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Substituicao, Usuario
from ..schemas import SubstituicaoCreate, SubstituicaoResponse
from ..auth import require_gestor_ou_admin
from ..services.substituicao import aplicar_definitiva

router = APIRouter(prefix="/substituicoes", tags=["substituicoes"])


@router.get("", response_model=List[SubstituicaoResponse])
def list_substituicoes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin),
):
    return db.query(Substituicao).order_by(Substituicao.created_at.desc()).all()


@router.post("", response_model=SubstituicaoResponse, status_code=201)
def create_substituicao(
    body: SubstituicaoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin),
):
    if body.usuario_id == body.substituto_id:
        raise HTTPException(status_code=400, detail="A pessoa e o substituto devem ser diferentes")
    for uid in (body.usuario_id, body.substituto_id):
        if not db.query(Usuario).filter(Usuario.id == uid, Usuario.ativo == True).first():
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if body.tipo == "temporaria" and not body.data_inicio:
        raise HTTPException(status_code=400, detail="Substituição temporária exige data de início")

    sub = Substituicao(
        usuario_id=body.usuario_id, substituto_id=body.substituto_id, tipo=body.tipo,
        data_inicio=body.data_inicio, data_fim=body.data_fim, motivo=body.motivo, ativa=True,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    # Definitiva: reatribui tudo imediatamente.
    if body.tipo == "definitiva":
        aplicar_definitiva(db, body.usuario_id, body.substituto_id)
        db.refresh(sub)
    return sub


@router.delete("/{sub_id}")
def encerrar_substituicao(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin),
):
    sub = db.query(Substituicao).filter(Substituicao.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substituição não encontrada")
    sub.ativa = False
    db.commit()
    return {"message": "Substituição encerrada"}
