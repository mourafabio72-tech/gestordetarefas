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


def _excluir_definitivo(db: Session, o: Obrigacao):
    """Apaga a obrigação, suas tarefas geradas e os vínculos."""
    from ..models import Tarefa
    for t in db.query(Tarefa).filter(Tarefa.obrigacao_id == o.id).all():
        t.responsaveis = []
        db.delete(t)
    o.empresas = []
    db.delete(o)


@router.delete("/{obrigacao_id}")
def delete_obrigacao(
    obrigacao_id: int,
    definitivo: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    """Sem flag: inativa (mantém histórico). Com `?definitivo=true`: exclui de vez
    (apaga a obrigação e as tarefas já geradas)."""
    o = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Obrigação não encontrada")
    if definitivo:
        _excluir_definitivo(db, o)
        db.commit()
        return {"message": "Obrigação excluída"}
    o.ativa = False
    db.commit()
    return {"message": "Obrigação desativada"}


class LoteBody(BaseModel):
    ids: List[int]
    definitivo: bool = True


@router.post("/excluir-lote")
def excluir_lote(
    body: LoteBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    """Exclui (apaga obrigação + tarefas geradas) ou inativa várias de uma vez."""
    n = 0
    for oid in body.ids:
        o = db.query(Obrigacao).filter(Obrigacao.id == oid).first()
        if not o:
            continue
        if body.definitivo:
            _excluir_definitivo(db, o)
        else:
            o.ativa = False
        n += 1
    db.commit()
    return {"processadas": n}


class StatusBody(BaseModel):
    ativa: bool


@router.post("/{obrigacao_id}/status")
def status_obrigacao(
    obrigacao_id: int,
    body: StatusBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("obrigacoes", "editar")),
):
    o = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Obrigação não encontrada")
    o.ativa = body.ativa
    db.commit()
    return {"message": "Ativada" if body.ativa else "Inativada"}
