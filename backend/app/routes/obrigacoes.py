from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from ..database import get_db
from ..models import Obrigacao, Empresa, Usuario
from ..schemas import ObrigacaoCreate, ObrigacaoUpdate, ObrigacaoResponse
from ..auth import get_current_user, require_perm, require_flag
from ..services.gerador import gerar_tarefas

router = APIRouter(prefix="/obrigacoes", tags=["obrigacoes"])


class CopiarModeloRequest(BaseModel):
    origem_empresa_id: int
    destino_empresa_id: int


class GerarRequest(BaseModel):
    mes: int   # mês de entrega (1-12)
    ano: int


def _set_empresas(db: Session, obrigacao: Obrigacao, empresa_ids):
    if empresa_ids is None:
        return
    empresas = db.query(Empresa).filter(Empresa.id.in_(empresa_ids)).all() if empresa_ids else []
    obrigacao.empresas = empresas


@router.get("", response_model=List[ObrigacaoResponse])
def list_obrigacoes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "ver")),
):
    return db.query(Obrigacao).order_by(Obrigacao.nome.asc()).all()


@router.get("/{obrigacao_id}", response_model=ObrigacaoResponse)
def get_obrigacao(
    obrigacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "ver")),
):
    o = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Obrigação não encontrada")
    return o


@router.post("/analisar-modelo")
async def analisar_modelo_endpoint(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    """Analisa um comprovante modelo (PDF) e sugere identificador(es) + CNPJ/competência."""
    from ..services.validador import analisar_modelo
    conteudo = await arquivo.read()
    try:
        return analisar_modelo(db, arquivo.filename, conteudo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Não consegui ler o arquivo: {e}")


@router.post("/gerar")
def gerar_competencia(
    body: GerarRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_flag("alocar_obrigacao")),
):
    """Gera as tarefas do mês de entrega informado (empresas da regra ∪ vínculo)."""
    if not (1 <= body.mes <= 12):
        raise HTTPException(status_code=400, detail="Mês inválido (1-12)")
    return gerar_tarefas(db, body.mes, body.ano)


@router.post("/copiar-empresa")
def copiar_modelo_empresa(
    body: CopiarModeloRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    """Vincula a empresa-destino a todas as obrigações da empresa-origem."""
    if body.origem_empresa_id == body.destino_empresa_id:
        raise HTTPException(status_code=400, detail="Origem e destino devem ser diferentes")
    destino = db.query(Empresa).filter(Empresa.id == body.destino_empresa_id).first()
    if not destino:
        raise HTTPException(status_code=404, detail="Empresa de destino não encontrada")

    obrigacoes = (db.query(Obrigacao)
                  .filter(Obrigacao.empresas.any(Empresa.id == body.origem_empresa_id))
                  .all())
    vinculadas = 0
    for o in obrigacoes:
        if destino not in o.empresas:
            o.empresas.append(destino)
            vinculadas += 1
    db.commit()
    return {"message": f"{vinculadas} obrigação(ões) vinculada(s) à empresa destino.",
            "vinculadas": vinculadas, "total_origem": len(obrigacoes)}


@router.post("", response_model=ObrigacaoResponse, status_code=201)
def create_obrigacao(
    obrigacao: ObrigacaoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    dados = obrigacao.model_dump(exclude={"empresa_ids"})
    o = Obrigacao(**dados)
    _set_empresas(db, o, obrigacao.empresa_ids)
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.put("/{obrigacao_id}", response_model=ObrigacaoResponse)
def update_obrigacao(
    obrigacao_id: int,
    obrigacao: ObrigacaoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    o = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Obrigação não encontrada")

    dados = obrigacao.model_dump(exclude_unset=True)
    empresa_ids = dados.pop("empresa_ids", None)
    for k, v in dados.items():
        setattr(o, k, v)
    _set_empresas(db, o, empresa_ids)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/{obrigacao_id}")
def delete_obrigacao(
    obrigacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    o = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Obrigação não encontrada")
    # Desativa (mantém histórico e o vínculo das tarefas já geradas).
    o.ativa = False
    db.commit()
    return {"message": "Obrigação desativada"}
