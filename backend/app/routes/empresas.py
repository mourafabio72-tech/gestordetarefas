from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from ..database import get_db
from ..models import Empresa, Usuario, Setor, EmpresaSetorResponsavel
from ..schemas import EmpresaCreate, EmpresaResponse
from ..auth import get_current_user, require_perm
from ..services import importador_empresas as imp
from ..services.validacao import cnpj_valido


def _empresa_em_uso(db: Session, eid: int) -> int:
    from ..models import Tarefa, obrigacao_empresa
    n = db.query(Tarefa).filter(Tarefa.empresa_id == eid).count()
    n += db.query(obrigacao_empresa).filter(obrigacao_empresa.c.empresa_id == eid).count()
    n += db.query(Usuario).filter(Usuario.empresa_id == eid).count()
    return n

router = APIRouter(prefix="/empresas", tags=["empresas"])


class BloquearRequest(BaseModel):
    bloqueado: bool = True


class RespSetorItem(BaseModel):
    setor_id: int
    responsavel_id: Optional[int] = None


class RespSetorBody(BaseModel):
    itens: List[RespSetorItem]


@router.get("/{empresa_id}/responsaveis-setor")
def get_responsaveis_setor(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Um item por setor ATIVO: o responsável dessa empresa naquele setor (ou None)."""
    mapa = {r.setor_id: r.responsavel_id
            for r in db.query(EmpresaSetorResponsavel).filter(EmpresaSetorResponsavel.empresa_id == empresa_id).all()}
    setores = db.query(Setor).filter(Setor.ativo == True).order_by(Setor.nome).all()
    return [{"setor_id": s.id, "setor_nome": s.nome, "responsavel_id": mapa.get(s.id)} for s in setores]


@router.put("/{empresa_id}/responsaveis-setor")
def set_responsaveis_setor(
    empresa_id: int,
    body: RespSetorBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar")),
):
    """Grava a matriz responsável×setor da empresa (upsert por setor)."""
    if not db.query(Empresa).filter(Empresa.id == empresa_id).first():
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    existentes = {r.setor_id: r for r in db.query(EmpresaSetorResponsavel)
                  .filter(EmpresaSetorResponsavel.empresa_id == empresa_id).all()}
    for it in body.itens:
        row = existentes.get(it.setor_id)
        if row:
            row.responsavel_id = it.responsavel_id
        else:
            db.add(EmpresaSetorResponsavel(empresa_id=empresa_id, setor_id=it.setor_id,
                                           responsavel_id=it.responsavel_id))
    db.commit()
    return {"ok": True}


@router.get("/modelo-importacao")
def modelo_importacao(current_user: Usuario = Depends(require_perm("empresas", "editar"))):
    conteudo = imp.gerar_modelo()
    return Response(
        content=conteudo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=modelo_importacao_empresas.xlsx"},
    )


@router.post("/importar")
async def importar_empresas(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar")),
):
    conteudo = await arquivo.read()
    try:
        return imp.importar(db, arquivo.filename, conteudo)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Falha ao ler a planilha: {e}")

@router.get("", response_model=List[EmpresaResponse])
def list_empresas(
    todas: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Por padrão só as ativas (dropdowns pelo app). `todas=true` inclui inativas
    (usado no cadastro de Empresas, que filtra por situação)."""
    q = db.query(Empresa)
    if not todas:
        q = q.filter(Empresa.ativo == True)
    return q.all()

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
    response: Response,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("empresas", "editar"))
):
    if empresa.cnpj:
        if not cnpj_valido(empresa.cnpj):
            raise HTTPException(status_code=400, detail="CNPJ inválido (dígitos verificadores não conferem).")
        existing = db.query(Empresa).filter(Empresa.cnpj == empresa.cnpj).first()
        if existing:
            raise HTTPException(status_code=400, detail="CNPJ já cadastrado")

    db_empresa = Empresa(**empresa.model_dump())
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)

    # Vínculo automático: gera já as tarefas do mês para as obrigações cuja
    # regra (regime/segmento) casa com esta empresa. Falha aqui não quebra o cadastro.
    try:
        from ..services import gerador
        res = gerador.gerar_empresa_mes_atual(db, db_empresa)
        response.headers["X-Tarefas-Geradas"] = str(res.get("criadas", 0))
    except Exception:
        db.rollback()
        response.headers["X-Tarefas-Geradas"] = "0"
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

    if empresa.cnpj and not cnpj_valido(empresa.cnpj):
        raise HTTPException(status_code=400, detail="CNPJ inválido (dígitos verificadores não conferem).")

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

    if _empresa_em_uso(db, empresa_id) > 0:
        db_empresa.ativo = False
        db.commit()
        return {"message": "Empresa tem tarefas/obrigações/usuários vinculados — foi inativada (não excluída).", "inativado": True}
    db.delete(db_empresa)
    db.commit()
    return {"message": "Empresa excluída.", "inativado": False}