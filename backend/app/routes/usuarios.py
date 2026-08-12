import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import List, Optional
from ..database import get_db
from ..models import Usuario, Tarefa, StatusTarefa
from ..schemas import UsuarioCreate, UsuarioUpdate, UsuarioResponse
from ..auth import (get_password_hash, get_current_user, require_gestor_ou_admin,
                    permissao_efetiva)
from ..permissoes import pode
from ..services.substituicao import aplicar_definitiva
from ..services import config as cfgmod, convite as convite_mod

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


def _pode_gerir_papel(current_user: Usuario) -> bool:
    """Quem pode definir grupo/permissões de outro: precisa de 'usuarios: editar'."""
    return pode(permissao_efetiva(current_user), "usuarios", "editar")


class BloquearRequest(BaseModel):
    bloqueado: bool = True
    substituto_id: Optional[int] = None  # ao bloquear, transferir a carga p/ este usuário


def _carga_aberta(db: Session, usuario_id: int) -> int:
    return (db.query(Tarefa)
            .filter(Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO]),
                    or_(Tarefa.responsavel_id == usuario_id,
                        Tarefa.responsaveis.any(Usuario.id == usuario_id)))
            .count())


@router.get("/{usuario_id}/carga")
def carga_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin)
):
    return {"abertas": _carga_aberta(db, usuario_id)}


@router.post("/{usuario_id}/bloquear", response_model=UsuarioResponse)
def bloquear_usuario(
    usuario_id: int,
    body: BloquearRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin)
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if u.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode bloquear a si mesmo")
    # Ao bloquear, se veio um substituto, transfere a carga (substituição definitiva) antes.
    if body.bloqueado and body.substituto_id:
        if body.substituto_id == usuario_id:
            raise HTTPException(status_code=400, detail="Substituto deve ser diferente")
        aplicar_definitiva(db, usuario_id, body.substituto_id)
    if body.bloqueado and _eh_ultimo_admin(db, usuario_id):
        raise HTTPException(status_code=400, detail="Não é possível bloquear o último admin ativo.")
    u.bloqueado = body.bloqueado
    db.commit()
    db.refresh(u)
    return u


def _eh_ultimo_admin(db: Session, uid: int) -> bool:
    u = db.query(Usuario).filter(Usuario.id == uid).first()
    if not u or u.grupo != "admin":
        return False
    outros = db.query(Usuario).filter(Usuario.grupo == "admin", Usuario.id != uid,
                                      Usuario.ativo == True, Usuario.bloqueado == False).count()
    return outros == 0


def _gestor_invalido(db: Session, uid, gestor_id) -> str:
    """Mensagem de erro se o gestor for inválido (auto-gestor ou ciclo); senão ''."""
    if not gestor_id:
        return ""
    if uid is not None and gestor_id == uid:
        return "Um usuário não pode ser gestor de si mesmo."
    atual, seen = gestor_id, set()
    while atual and atual not in seen:
        if uid is not None and atual == uid:
            return "Vínculo de gestor cria um ciclo (A→B→A)."
        seen.add(atual)
        g = db.query(Usuario).filter(Usuario.id == atual).first()
        atual = g.gestor_id if g else None
    return ""

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


@router.get("/modelo-importacao")
def modelo_importacao_usuarios(current_user: Usuario = Depends(require_gestor_ou_admin)):
    from fastapi.responses import Response
    from ..services import importador_usuarios as impu
    return Response(
        content=impu.gerar_modelo(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=modelo_importacao_usuarios.xlsx"},
    )


@router.post("/importar")
async def importar_usuarios(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin),
):
    from ..services import importador_usuarios as impu
    conteudo = await arquivo.read()
    try:
        return impu.importar(db, arquivo.filename, conteudo, executor_email=current_user.email)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Falha ao ler a planilha: {e}")


class ConviteLoteBody(BaseModel):
    ids: Optional[List[int]] = None  # None/vazio = todos os pendentes


@router.post("/{usuario_id}/convite")
async def enviar_convite(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    cfg = cfgmod.carregar(db)
    res = await convite_mod.enviar(db, u, cfg)
    db.commit()
    if not res["ok"]:
        raise HTTPException(status_code=400, detail=res.get("erro") or "Falha ao enviar o convite.")
    return {"ok": True, **res}


@router.post("/convite-lote")
async def enviar_convite_lote(
    body: ConviteLoteBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin),
):
    q = db.query(Usuario).filter(Usuario.bloqueado == False)
    alvos = q.filter(Usuario.id.in_(body.ids)).all() if body.ids else q.filter(Usuario.ativado == False).all()
    cfg = cfgmod.carregar(db)
    enviados, falhas = 0, []
    for u in alvos:
        res = await convite_mod.enviar(db, u, cfg)
        if res["ok"]:
            enviados += 1
        else:
            falhas.append({"nome": u.nome, "erro": res.get("erro")})
    db.commit()
    return {"total": len(alvos), "enviados": enviados, "falhas": falhas}


@router.post("", response_model=UsuarioResponse, status_code=201)
def create_usuario(
    usuario: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin)
):
    existing = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # Só quem tem 'usuarios: editar' define papel/permissões; senão cai no default.
    pode_gerir = _pode_gerir_papel(current_user)
    grupo = usuario.grupo if pode_gerir else "usuario"
    permissoes_json = (json.dumps(usuario.permissoes)
                       if pode_gerir and usuario.permissoes else None)

    tipo = usuario.tipo or "colaborador"
    db_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=get_password_hash(usuario.senha),
        cargo=usuario.cargo,
        telefone=usuario.telefone,
        grupo=grupo,
        permissoes=permissoes_json,
        tipo=tipo,
        empresa_id=usuario.empresa_id if tipo == "cliente" else None,
        gestor_id=usuario.gestor_id,
        setor_id=usuario.setor_id,
        ativado=False,   # pendente até ativar pelo link de convite
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
    current_user: Usuario = Depends(require_gestor_ou_admin)
):
    db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if usuario.gestor_id is not None:
        erro = _gestor_invalido(db, usuario_id, usuario.gestor_id)
        if erro:
            raise HTTPException(status_code=400, detail=erro)
    if usuario.grupo is not None and usuario.grupo != "admin" and _eh_ultimo_admin(db, usuario_id):
        raise HTTPException(status_code=400, detail="Não é possível rebaixar o último admin ativo.")

    if usuario.nome is not None:
        db_usuario.nome = usuario.nome
    if usuario.email is not None:
        db_usuario.email = usuario.email
    if usuario.cargo is not None:
        db_usuario.cargo = usuario.cargo
    if usuario.telefone is not None:
        db_usuario.telefone = usuario.telefone
    if usuario.tipo is not None:
        db_usuario.tipo = usuario.tipo
    if usuario.empresa_id is not None or usuario.tipo == "colaborador":
        # cliente vincula empresa; colaborador nunca fica vinculado
        db_usuario.empresa_id = usuario.empresa_id if (usuario.tipo or db_usuario.tipo) == "cliente" else None
    if usuario.gestor_id is not None:
        db_usuario.gestor_id = usuario.gestor_id
    db_usuario.setor_id = usuario.setor_id  # form sempre envia (vazio = limpa)
    # Só quem tem 'usuarios: editar' altera papel e permissões de outro usuário.
    if _pode_gerir_papel(current_user):
        if usuario.grupo is not None:
            db_usuario.grupo = usuario.grupo
        if usuario.permissoes is not None:
            # {} limpa os overrides (volta a herdar 100% do preset do papel).
            db_usuario.permissoes = json.dumps(usuario.permissoes) if usuario.permissoes else None
    if usuario.senha:
        db_usuario.senha_hash = get_password_hash(usuario.senha)

    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def _usuario_em_uso(db: Session, uid: int) -> int:
    from ..models import Obrigacao, Empresa, tarefa_responsaveis
    n = db.query(Obrigacao).filter((Obrigacao.responsavel_id == uid) | (Obrigacao.supervisor_id == uid)).count()
    n += db.query(Tarefa).filter((Tarefa.responsavel_id == uid) | (Tarefa.supervisor_id == uid)).count()
    n += db.query(Empresa).filter((Empresa.responsavel_id == uid) | (Empresa.supervisor_id == uid)).count()
    n += db.query(Usuario).filter(Usuario.gestor_id == uid).count()
    n += db.query(tarefa_responsaveis).filter(tarefa_responsaveis.c.usuario_id == uid).count()
    return n


@router.delete("/{usuario_id}")
def delete_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_gestor_ou_admin)
):
    """Com vínculo (obrigação/tarefa/empresa/gestor): só INATIVA. Sem vínculo: exclui de vez.
    Nunca exclui a si mesmo."""
    db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if db_usuario.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir o próprio usuário.")
    if _eh_ultimo_admin(db, usuario_id):
        raise HTTPException(status_code=400, detail="Não é possível excluir o último admin ativo.")
    if _usuario_em_uso(db, usuario_id) > 0:
        db_usuario.ativo = False
        db.commit()
        return {"message": "Usuário tem vínculos (obrigações/tarefas/empresas) — foi inativado (não excluído).", "inativado": True}
    db.delete(db_usuario)
    db.commit()
    return {"message": "Usuário excluído.", "inativado": False}
