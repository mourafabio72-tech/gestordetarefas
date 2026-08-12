"""Cadastro de GRUPOS (papéis de acesso) com matriz de permissões editável.

Fonte da verdade em runtime é a tabela `grupos` (cache em permissoes._GRUPOS_DB).
Só admin gerencia. 'admin' é protegido: não bloqueia, não exclui, permissões
sempre totais. Grupo com usuários não pode ser bloqueado/excluído (realocar antes).
"""
import re
import json
import unicodedata
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..database import get_db
from ..models import Grupo, Usuario
from ..auth import require_admin
from .. import permissoes

router = APIRouter(prefix="/grupos", tags=["grupos"])


class GrupoCreate(BaseModel):
    label: str
    descricao: Optional[str] = None
    permissoes: Optional[Dict[str, Any]] = None


class GrupoUpdate(BaseModel):
    label: Optional[str] = None
    descricao: Optional[str] = None
    permissoes: Optional[Dict[str, Any]] = None


class StatusRequest(BaseModel):
    ativo: bool


def _slug(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s[:30] or "grupo"


def _slug_unico(db: Session, base: str) -> str:
    slug, i = base, 2
    while db.query(Grupo).filter(Grupo.slug == slug).first():
        slug = f"{base[:26]}_{i}"
        i += 1
    return slug


def _sanitizar(perm: dict) -> dict:
    """Mantém só chaves válidas e valores no domínio certo."""
    out = {}
    for k, v in (perm or {}).items():
        if k in permissoes.RECURSOS:
            if v in permissoes.NIVEL_ORDEM:
                out[k] = v
        elif k == "escopo_tarefas":
            if v in permissoes.ESCOPOS:
                out[k] = v
        elif k in permissoes.FLAGS:
            out[k] = bool(v)
    return out


def _qtd_usuarios(db: Session, slug: str) -> int:
    return db.query(Usuario).filter(Usuario.grupo == slug).count()


def _serializar(db: Session, g: Grupo) -> dict:
    try:
        perm = json.loads(g.permissoes) if g.permissoes else {}
    except (ValueError, TypeError):
        perm = {}
    return {
        "slug": g.slug, "label": g.label, "descricao": g.descricao,
        "permissoes": permissoes._completar(perm, g.slug),
        "sistema": bool(g.sistema), "ativo": bool(g.ativo),
        "usuarios": _qtd_usuarios(db, g.slug),
    }


@router.get("")
def listar(db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    return [_serializar(db, g) for g in db.query(Grupo).order_by(Grupo.sistema.desc(), Grupo.label).all()]


@router.post("", status_code=201)
def criar(body: GrupoCreate, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    label = (body.label or "").strip()
    if not label:
        raise HTTPException(status_code=400, detail="Informe o nome do grupo.")
    slug = _slug_unico(db, _slug(label))
    perm = _completar_seguro(_sanitizar(body.permissoes), slug)
    g = Grupo(slug=slug, label=label, descricao=(body.descricao or "").strip() or None,
              permissoes=json.dumps(perm), sistema=False, ativo=True)
    db.add(g)
    db.commit()
    db.refresh(g)
    permissoes.carregar_do_banco(db)
    return _serializar(db, g)


def _completar_seguro(perm: dict, slug: str) -> dict:
    """Completa com o preset base do slug (ou consulta) as chaves faltantes."""
    return permissoes._completar(perm, slug)


@router.put("/{slug}")
def atualizar(slug: str, body: GrupoUpdate, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    g = db.query(Grupo).filter(Grupo.slug == slug).first()
    if not g:
        raise HTTPException(status_code=404, detail="Grupo não encontrado.")
    if body.label is not None and body.label.strip():
        g.label = body.label.strip()
    if body.descricao is not None:
        g.descricao = body.descricao.strip() or None
    if body.permissoes is not None:
        if slug == "admin":
            raise HTTPException(status_code=400, detail="O grupo Admin tem acesso total e não pode ser restringido.")
        g.permissoes = json.dumps(_completar_seguro(_sanitizar(body.permissoes), slug))
    db.commit()
    permissoes.carregar_do_banco(db)
    return _serializar(db, g)


@router.post("/{slug}/status")
def status(slug: str, body: StatusRequest, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    g = db.query(Grupo).filter(Grupo.slug == slug).first()
    if not g:
        raise HTTPException(status_code=404, detail="Grupo não encontrado.")
    if not body.ativo:
        if slug == "admin":
            raise HTTPException(status_code=400, detail="O grupo Admin não pode ser bloqueado.")
        n = _qtd_usuarios(db, slug)
        if n > 0:
            raise HTTPException(status_code=400,
                                detail=f"{n} usuário(s) ainda estão neste grupo. Realoque-os antes de bloquear.")
    g.ativo = body.ativo
    db.commit()
    permissoes.carregar_do_banco(db)
    return _serializar(db, g)


@router.delete("/{slug}")
def excluir(slug: str, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    g = db.query(Grupo).filter(Grupo.slug == slug).first()
    if not g:
        raise HTTPException(status_code=404, detail="Grupo não encontrado.")
    if g.sistema:
        raise HTTPException(status_code=400, detail="Grupo nativo não pode ser excluído (só bloqueado).")
    n = _qtd_usuarios(db, slug)
    if n > 0:
        raise HTTPException(status_code=400,
                            detail=f"{n} usuário(s) ainda estão neste grupo. Realoque-os antes de excluir.")
    db.delete(g)
    db.commit()
    permissoes.carregar_do_banco(db)
    return {"message": "Grupo excluído."}
