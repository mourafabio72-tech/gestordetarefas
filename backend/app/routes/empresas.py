from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from ..database import get_db
from ..models import Empresa, Usuario
from ..schemas import EmpresaCreate, EmpresaResponse
from ..auth import get_current_user, require_perm

router = APIRouter(prefix="/empresas", tags=["empresas"])


class BloquearRequest(BaseModel):
    bloqueado: bool = True

@router.get("", response_model=List[EmpresaResponse])
def list_empresas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return db.query(Empresa).filter(Empresa.ativo == True).all()

@router.get("/{empresa_id}", response_model=EmpresaResponse)
def get_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa

@router.post("", response_model=EmpresaResponse, status_code=201)
def create_empresa(
    empresa: EmpresaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar"))
):
    if empresa.cnpj:
        existing = db.query(Empresa).filter(Empresa.cnpj == empresa.cnpj).first()
        if existing:
            raise HTTPException(status_code=400, detail="CNPJ já cadastrado")

    db_empresa = Empresa(**empresa.model_dump())
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return db_empresa

@router.put("/{empresa_id}", response_model=EmpresaResponse)
def update_empresa(
    empresa_id: int,
    empresa: EmpresaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar"))
):
    db_empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    for key, value in empresa.model_dump(exclude_unset=True).items():
        setattr(db_empresa, key, value)

    db.commit()
    db.refresh(db_empresa)
    return db_empresa

@router.post("/{empresa_id}/bloquear", response_model=EmpresaResponse)
def bloquear_empresa(
    empresa_id: int,
    body: BloquearRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar"))
):
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    emp.bloqueado = body.bloqueado
    db.commit()
    db.refresh(emp)
    return emp


@router.delete("/{empresa_id}")
def delete_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar"))
):
    db_empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    db_empresa.ativo = False
    db.commit()
    return {"message": "Empresa desativada com sucesso"}