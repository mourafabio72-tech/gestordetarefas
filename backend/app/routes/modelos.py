from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel
from ..database import get_db
from ..models import Usuario, Modelo
from ..auth import require_perm
from ..services.validador import analisar_para_repositorio, salvar_modelo

router = APIRouter(prefix="/modelos", tags=["modelos"])

TIPOS = {"recibo_entrega": "Recibo de entrega",
         "comprovante_pagamento": "Comprovante de pagamento",
         "relatorio": "Relatório",
         "outro": "Outro"}


def _serializar(m: Modelo) -> dict:
    return {
        "id": m.id,
        "nome_arquivo": m.nome_arquivo,
        "cnpj": m.cnpj,
        "razao_social_extraida": m.razao_social_extraida,
        "empresa_id": m.empresa_id,
        "empresa_nome": m.empresa.razao_social if m.empresa else None,
        "obrigacao_id": m.obrigacao_id,
        "obrigacao_nome": m.obrigacao.nome if m.obrigacao else None,
        "tipo_documento": m.tipo_documento,
        "tipo_label": TIPOS.get(m.tipo_documento, m.tipo_documento),
        "identificador": m.identificador,
        "competencia_exemplo": m.competencia_exemplo,
        "protocolo_exemplo": m.protocolo_exemplo,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("")
def listar(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("evalidador", "ver")),
):
    modelos = db.query(Modelo).order_by(Modelo.created_at.desc()).all()
    return [_serializar(m) for m in modelos]


@router.post("/analisar")
async def analisar(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("evalidador", "editar")),
):
    """Lê o documento e devolve a pré-visualização (empresa, tipo, candidatos a
    identificador, obrigação sugerida) para revisão antes de salvar."""
    conteudo = await arquivo.read()
    try:
        return analisar_para_repositorio(db, arquivo.filename, conteudo)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Falha ao ler o arquivo: {e}")


@router.post("")
def criar(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("evalidador", "editar")),
):
    """Grava o modelo revisado e treina a obrigação vinculada (acrescenta o
    identificador escolhido à lista da obrigação)."""
    if not body.get("cnpj") and not body.get("razao_social_extraida"):
        raise HTTPException(status_code=422, detail="Documento sem CNPJ nem razão social identificados.")
    m = salvar_modelo(db, body)
    return _serializar(m)


@router.delete("/{modelo_id}")
def excluir(
    modelo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("evalidador", "editar")),
):
    m = db.query(Modelo).filter(Modelo.id == modelo_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    db.delete(m)
    db.commit()
    return {"ok": True}
