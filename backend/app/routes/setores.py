from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Setor, Usuario
from ..schemas import SetorCreate, SetorResponse
from ..auth import get_current_user, require_perm

router = APIRouter(prefix="/setores", tags=["setores"])

@router.get("", response_model=List[SetorResponse])
def list_setores(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # Setores são internos/globais do escritório.
    return db.query(Setor).filter(Setor.ativo == True).all()

@router.get("/{setor_id}", response_model=SetorResponse)
def get_setor(
    setor_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    setor = db.query(Setor).filter(Setor.id == setor_id).first()
    if not setor:
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    return setor

@router.post("", response_model=SetorResponse, status_code=201)
def create_setor(
    setor: SetorCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("setores", "editar"))
):
    db_setor = Setor(**setor.model_dump())
    db.add(db_setor)
    db.commit()
    db.refresh(db_setor)
    return db_setor

@router.put("/{setor_id}", response_model=SetorResponse)
def update_setor(
    setor_id: int,
    setor: SetorCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("setores", "editar"))
):
    db_setor = db.query(Setor).filter(Setor.id == setor_id).first()
    if not db_setor:
        raise HTTPException(status_code=404, detail="Setor não encontrado")

    for key, value in setor.model_dump(exclude_unset=True).items():
        setattr(db_setor, key, value)

    db.commit()
    db.refresh(db_setor)
    return db_setor

@router.delete("/{setor_id}")
def delete_setor(
    setor_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("setores", "editar"))
):
    db_setor = db.query(Setor).filter(Setor.id == setor_id).first()
    if not db_setor:
        raise HTTPException(status_code=404, detail="Setor não encontrado")

    db_setor.ativo = False
    db.commit()
    return {"message": "Setor desativado com sucesso"}