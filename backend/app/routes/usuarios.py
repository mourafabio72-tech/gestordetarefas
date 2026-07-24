from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Usuario
from ..schemas import UsuarioCreate, UsuarioUpdate, UsuarioResponse
from ..auth import get_password_hash, get_current_user

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

@router.get("", response_model=List[UsuarioResponse])
def list_usuarios(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return db.query(Usuario).filter(Usuario.ativo == True).all()

@router.get("/{usuario_id}", response_model=UsuarioResponse)
def get_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario

@router.post("", response_model=UsuarioResponse, status_code=201)
def create_usuario(
    usuario: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    existing = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    db_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=get_password_hash(usuario.senha),
        cargo=usuario.cargo,
        telefone=usuario.telefone,
        teams_webhook=usuario.teams_webhook
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@router.put("/{usuario_id}", response_model=UsuarioResponse)
def update_usuario(
    usuario_id: int,
    usuario: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if usuario.nome is not None:
        db_usuario.nome = usuario.nome
    if usuario.email is not None:
        db_usuario.email = usuario.email
    if usuario.cargo is not None:
        db_usuario.cargo = usuario.cargo
    if usuario.telefone is not None:
        db_usuario.telefone = usuario.telefone
    if usuario.teams_webhook is not None:
        db_usuario.teams_webhook = usuario.teams_webhook
    if usuario.senha:
        db_usuario.senha_hash = get_password_hash(usuario.senha)
        db_usuario.senha_hash = get_password_hash(usuario.senha)

    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@router.delete("/{usuario_id}")
def delete_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    db_usuario.ativo = False
    db.commit()
    return {"message": "Usuário desativado com sucesso"}
