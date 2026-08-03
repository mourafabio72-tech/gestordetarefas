from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from .models import Usuario
from . import permissoes
import os

SECRET_KEY = os.getenv("SECRET_KEY", "sua-chave-secreta-aqui-mude-em-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 horas

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def require_grupos(*grupos):
    """Dependência: exige que o usuário logado pertença a um dos grupos."""
    def _dep(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        if current_user.grupo not in grupos:
            raise HTTPException(status_code=403, detail="Você não tem permissão para esta ação")
        return current_user
    return _dep


require_admin = require_grupos("admin")
require_gestor_ou_admin = require_grupos("admin", "gestor")


def permissao_efetiva(user: Usuario) -> dict:
    """Resolve a permissão do usuário: preset do papel + overrides do JSON."""
    return permissoes.resolver(user.grupo, getattr(user, "permissoes", None))


def require_perm(recurso: str, nivel: str = "ver"):
    """Dependência: exige `nivel` (ver|editar) no `recurso` da matriz."""
    def _dep(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        if not permissoes.pode(permissao_efetiva(current_user), recurso, nivel):
            raise HTTPException(
                status_code=403,
                detail=f"Sem permissão de '{nivel}' em '{recurso}'",
            )
        return current_user
    return _dep


def require_flag(flag: str):
    """Dependência: exige que a flag de ação sensível esteja ligada."""
    def _dep(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        if not permissoes.tem_flag(permissao_efetiva(current_user), flag):
            raise HTTPException(
                status_code=403,
                detail=f"Sem permissão para a ação '{flag}'",
            )
        return current_user
    return _dep