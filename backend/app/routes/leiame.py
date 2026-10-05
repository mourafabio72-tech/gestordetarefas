"""Registro do fluxo guiado do Leia-me (manual da equipe em /leia-me/).

Cada pessoa logada lê e grava só o próprio progresso. Admin e gestor veem o
quadro de todos os colaboradores ativos, inclusive quem não começou."""
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, StrictBool, field_validator
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_gestor_ou_admin
from ..database import get_db
from ..models import LeiameProgresso, Usuario

router = APIRouter(prefix="/leiame", tags=["leiame"])

TOTAL = 7  # etapas do fluxo guiado do manual


class EtapaEstado(BaseModel):
    acao: StrictBool
    resp: StrictBool
    erros: int = Field(0, ge=0, le=1000)


class ProgressoIn(BaseModel):
    estado: List[EtapaEstado]
    liberada: int = Field(..., ge=0, le=TOTAL - 1)

    @field_validator("estado")
    @classmethod
    def _sete(cls, v):
        if len(v) != TOTAL:
            raise ValueError(f"O fluxo tem {TOTAL} etapas.")
        return v


def _iso(d):
    return d.isoformat() + "Z" if d else None


def _saida(p: Optional[LeiameProgresso]) -> dict:
    if not p:
        return {"etapas": 0, "total": TOTAL, "concluido": False, "erros": 0, "liberada": 0,
                "estado": [], "concluido_em": None, "atualizado_em": None}
    return {"etapas": p.etapas, "total": TOTAL, "concluido": p.concluido_em is not None, "erros": p.erros,
            "liberada": p.liberada, "estado": json.loads(p.estado or "[]"),
            "concluido_em": _iso(p.concluido_em), "atualizado_em": _iso(p.atualizado_em)}


@router.get("/progresso")
def meu_progresso(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    p = db.query(LeiameProgresso).filter(LeiameProgresso.usuario_id == current_user.id).first()
    return _saida(p)


@router.put("/progresso")
def gravar_progresso(body: ProgressoIn, db: Session = Depends(get_db),
                     current_user: Usuario = Depends(get_current_user)):
    agora = datetime.utcnow()
    p = db.query(LeiameProgresso).filter(LeiameProgresso.usuario_id == current_user.id).first()
    if not p:
        p = LeiameProgresso(usuario_id=current_user.id, iniciado_em=agora)
        db.add(p)
    # Contado aqui, e não aceito do navegador: etapa feita = ação e resposta certas.
    p.etapas = sum(1 for e in body.estado if e.acao and e.resp)
    p.erros = sum(e.erros for e in body.estado)
    p.liberada = body.liberada
    p.estado = json.dumps([e.model_dump() for e in body.estado])
    if p.etapas == TOTAL and p.concluido_em is None:
        p.concluido_em = agora
    p.atualizado_em = agora
    db.commit()
    return _saida(p)


@router.get("/conclusoes")
def quadro(db: Session = Depends(get_db), current_user: Usuario = Depends(require_gestor_ou_admin)):
    pessoas = (db.query(Usuario)
               .filter(Usuario.ativo == True, Usuario.tipo != "cliente")
               .order_by(Usuario.nome).all())
    prog = {p.usuario_id: p for p in db.query(LeiameProgresso).all()}
    saida = []
    for u in pessoas:
        if u.bloqueado:
            continue
        p = prog.get(u.id)
        saida.append({"usuario_id": u.id, "nome": u.nome, "grupo": u.grupo,
                      "etapas": p.etapas if p else 0, "total": TOTAL,
                      "concluido": bool(p and p.concluido_em), "erros": p.erros if p else 0,
                      "concluido_em": _iso(p.concluido_em) if p else None,
                      "atualizado_em": _iso(p.atualizado_em) if p else None})
    return saida
