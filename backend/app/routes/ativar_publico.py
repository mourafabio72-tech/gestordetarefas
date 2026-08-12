"""Endpoints PÚBLICOS (sem login) de ativação de acesso por token de convite.
A pessoa abre o link, define a própria senha e a conta é ativada."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models import Usuario
from ..auth import get_password_hash

router = APIRouter(prefix="/publico", tags=["publico"])


class AtivarBody(BaseModel):
    senha: str


def _por_token(db: Session, token: str) -> Usuario:
    u = db.query(Usuario).filter(Usuario.convite_token == token).first()
    if not u:
        raise HTTPException(status_code=404, detail="Convite inválido ou já utilizado.")
    if u.bloqueado:
        raise HTTPException(status_code=403, detail="Acesso indisponível.")
    return u


@router.get("/ativar/{token}")
def contexto(token: str, db: Session = Depends(get_db)):
    u = _por_token(db, token)
    return {"nome": u.nome, "email": u.email, "ja_ativado": bool(u.ativado)}


@router.post("/ativar/{token}")
def ativar(token: str, body: AtivarBody, db: Session = Depends(get_db)):
    u = _por_token(db, token)
    senha = (body.senha or "").strip()
    if len(senha) < 6:
        raise HTTPException(status_code=422, detail="A senha precisa ter ao menos 6 caracteres.")
    u.senha_hash = get_password_hash(senha)
    u.ativado = True
    u.convite_token = None  # token de uso único
    db.commit()
    return {"ok": True, "email": u.email}
