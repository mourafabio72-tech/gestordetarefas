import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from pydantic import BaseModel
from typing import List, Optional
from ..database import get_db
from ..models import Usuario, Tarefa, StatusTarefa
from ..schemas import UsuarioCreate, UsuarioUpdate, UsuarioResponse
from ..auth import (get_password_hash, get_current_user, require_gestor_ou_admin,
                    permissao_efetiva)
from ..permissoes import pode
from ..seguranca import log_event
from ..services.substituicao import aplicar_definitiva
from ..services import config as cfgmod, convite as convite_mod

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


def _perm_json(bruto):
    """As permissões como dicionário, para comparar conteúdo e não texto.

    Texto inválido no banco volta como ele mesmo, em vez de derrubar a rota:
    coluna de texto aceita qualquer coisa, e a comparação continua honesta.
    """
    if not bruto:
        return None
    try:
        return json.loads(bruto)
    except (TypeError, ValueError):
        return bruto


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
    # Bloquear mexe em quem consegue entrar, e pode ter redistribuido a carga
    # para outra pessoa no caminho. Sem esta linha, a pergunta "quem tirou o
    # acesso de fulano, e quando" nao tinha resposta.
    log_event("EDICAO_REGISTRO_CRITICO", level="WARN", tabela="usuario",
              alvo_id=u.id, alvo_email=u.email, bloqueado=u.bloqueado,
              substituto_id=body.substituto_id)
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
    return db.query(Usuario).filter(Usuario.ativo == True).order_by(func.lower(Usuario.nome)).all()

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
        resultado = impu.importar(db, arquivo.filename, conteudo,
                                  executor_email=current_user.email)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Falha ao ler a planilha: {e}")
    # Uma linha por lote, igual a importacao de empresas. A troca de papel
    # dentro do lote continua saindo uma por pessoa, no evento proprio dela:
    # "criei 200 usuarios" e um fato so, e "fulano virou admin" e um fato por
    # pessoa, que e o que uma auditoria vem perguntar.
    resumo = resultado.get("resumo") or {}
    criadas = int(resumo.get("criadas") or 0)
    atualizadas = int(resumo.get("atualizadas") or 0)
    # Planilha sem a coluna obrigatória devolve 200 com um erro dentro e não
    # grava nada. A linha saía assim mesmo, com zero: o número não mentia, mas
    # o EVENTO sim, anunciando criação crítica onde não houve criação nenhuma.
    # As rotas singulares nunca logam em caminho de erro, e o lote segue a
    # mesma regra.
    if criadas or atualizadas:
        log_event("CRIACAO_REGISTRO_CRITICO", tabela="usuario", lote=True,
                  quantidade=criadas, atualizadas=atualizadas,
                  arquivo=arquivo.filename)
    return resultado


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
    log_event("CRIACAO_REGISTRO_CRITICO", tabela="usuario",
              alvo_id=db_usuario.id, alvo_email=db_usuario.email,
              grupo=db_usuario.grupo)
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
    papel_a_registrar = None
    if _pode_gerir_papel(current_user):
        # O valor de ANTES é lido aqui, antes de qualquer atribuição. Ler depois
        # gravaria o papel novo nos dois campos do log, que é o erro clássico
        # deste evento: a linha diria "de gestor para gestor" e não provaria
        # nada. É a pergunta que uma auditoria faz primeiro, então a linha
        # precisa dizer de onde para onde.
        papel_antes = db_usuario.grupo
        permissoes_antes = db_usuario.permissoes
        if usuario.grupo is not None:
            db_usuario.grupo = usuario.grupo
        if usuario.permissoes is not None:
            # {} limpa os overrides (volta a herdar 100% do preset do papel).
            db_usuario.permissoes = json.dumps(usuario.permissoes) if usuario.permissoes else None
        # Permissão pontual muda o que a pessoa faz tanto quanto o papel muda,
        # e por isso as duas entram no mesmo evento. Só registra o que mudou de
        # fato: reenviar o mesmo papel na tela não é mudança de papel.
        #
        # A comparação das permissões é pelo CONTEÚDO, e não pelo texto. Elas
        # são guardadas como JSON em coluna de texto, e o mesmo dicionário
        # serializado com as chaves em outra ordem dá outra string: comparar
        # texto acusaria mudança onde não houve, e evento de auditoria que
        # dispara sozinho vira ruído, que é o que faz ninguém mais olhar o log.
        permissoes_mudaram = _perm_json(db_usuario.permissoes) != _perm_json(permissoes_antes)
        if db_usuario.grupo != papel_antes or permissoes_mudaram:
            # A linha e MONTADA aqui, onde o valor de antes ainda existe, e
            # EMITIDA depois do commit. Emitir aqui foi o defeito que um
            # verificador reproduziu: o commit pode estourar (este PUT nao
            # confere e-mail duplicado, so a criacao confere), e a linha ja
            # teria anunciado uma promocao de privilegio que nunca aconteceu.
            # Log de auditoria que mente sobre elevacao de acesso e pior do
            # que log nenhum: manda quem investiga para o lado errado com ar
            # de prova.
            papel_a_registrar = dict(
                alvo_id=db_usuario.id, alvo_email=db_usuario.email,
                de=papel_antes, para=db_usuario.grupo,
                permissoes_mudaram=permissoes_mudaram)
    credencial_redefinida = bool(usuario.senha)
    if credencial_redefinida:
        db_usuario.senha_hash = get_password_hash(usuario.senha)

    db.commit()
    db.refresh(db_usuario)
    if papel_a_registrar:
        log_event("MUDANCA_ROLE", level="WARN", **papel_a_registrar)
    # A troca de papel já saiu acima, no seu próprio evento. Esta linha é a
    # edição do cadastro, e diz apenas SE a credencial foi redefinida: a senha
    # em si, nova ou antiga, está na lista do que nunca entra em log.
    #
    # O campo se chamava `senha_trocada`, e a prova reprovou: ela varre os
    # NOMES das chaves contra a lista proibida. A heurística é conservadora de
    # propósito, e o certo era mudar o nome, não afrouxar a trava. Chave de log
    # com a palavra "senha" tem de continuar acendendo a luz vermelha.
    log_event("EDICAO_REGISTRO_CRITICO", tabela="usuario",
              alvo_id=db_usuario.id, alvo_email=db_usuario.email,
              credencial_redefinida=credencial_redefinida)
    return db_usuario

def _usuario_em_uso(db: Session, uid: int) -> int:
    from ..models import (Obrigacao, Empresa, tarefa_responsaveis,
                          EmpresaSetorResponsavel, empresa_setor_resp_usuarios)
    n = db.query(Obrigacao).filter((Obrigacao.responsavel_id == uid) | (Obrigacao.supervisor_id == uid)).count()
    n += db.query(Tarefa).filter((Tarefa.responsavel_id == uid) | (Tarefa.supervisor_id == uid)).count()
    n += db.query(Empresa).filter((Empresa.responsavel_id == uid) | (Empresa.supervisor_id == uid)).count()
    n += db.query(Usuario).filter(Usuario.gestor_id == uid).count()
    n += db.query(tarefa_responsaveis).filter(tarefa_responsaveis.c.usuario_id == uid).count()
    # Ser responsável por um setor de uma empresa também é vínculo. Sem estas
    # duas linhas, a pessoa era APAGADA de vez e a matriz ficava apontando para
    # um id que não existe mais: o principal some da tela e o secundário vira
    # linha pendurada. Vale para os dois papéis, porque com vários responsáveis
    # o secundário não aparece em `responsavel_id`.
    n += db.query(EmpresaSetorResponsavel).filter(
        EmpresaSetorResponsavel.responsavel_id == uid).count()
    n += db.query(empresa_setor_resp_usuarios).filter(
        empresa_setor_resp_usuarios.c.usuario_id == uid).count()
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
    # Os dois desfechos saem com o MESMO nome de evento, e um campo distingue.
    # A nota é explícita: `EXCLUSAO_REGISTRO_CRITICO | Idem (soft delete)`.
    # Nomes diferentes fariam quem audita ter de saber os dois para achar o
    # que procura.
    alvo = {"tabela": "usuario", "alvo_id": db_usuario.id,
            "alvo_email": db_usuario.email}
    if _usuario_em_uso(db, usuario_id) > 0:
        db_usuario.ativo = False
        db.commit()
        log_event("EXCLUSAO_REGISTRO_CRITICO", level="WARN", inativado=True, **alvo)
        return {"message": "Usuário tem vínculos (obrigações/tarefas/empresas), então foi inativado e não excluído.", "inativado": True}
    db.delete(db_usuario)
    db.commit()
    log_event("EXCLUSAO_REGISTRO_CRITICO", level="WARN", inativado=False, **alvo)
    return {"message": "Usuário excluído.", "inativado": False}
