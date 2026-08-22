from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Usuario, SSOBilheteUsado
from ..schemas import LoginRequest, Token, UsuarioCreate, UsuarioResponse, MeResponse
from ..auth import (verify_password, create_access_token, get_password_hash,
                    get_current_user, permissao_efetiva)
from .. import sso as sso_bilhete
from ..seguranca import (ip_cliente, log_event, registrar_tentativa,
                         falhas_recentes, limpar_tentativas_antigas,
                         MAX_TENTATIVAS, JANELA_MINUTOS)

router = APIRouter(prefix="/auth", tags=["auth"])

# Uma mensagem só para TODOS os motivos de recusa do SSO: bilhete inválido,
# vencido, já usado, e-mail sem cadastro aqui, conta bloqueada, conta inativa.
# Motivo distinto por caso vira oráculo: quem tem um bilhete descobre se aquele
# e-mail existe no Tareffas, e qual é o estado da conta.
RECUSA_SSO = "Não foi possível entrar por aqui. Faça login com e-mail e senha."

# Rastro do bilhete consumido. Passado esse prazo, a linha só teria valor de
# auditoria antiga, e o bilhete que ela representa morreu em 60 segundos.
RETENCAO_BILHETES_DIAS = 7

@router.post("/login", response_model=Token)
def login(dados: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login por e-mail e senha, com registro e limite de tentativa.

    A contagem usa `origem="senha"`, separada da do SSO: quem errou a senha
    cinco vezes não fica impedido de entrar pelo card do Hub, que é outra
    credencial. O limite e a janela são os mesmos dos dois lados.
    """
    ip = ip_cliente(request)
    email = (dados.email or "").strip()

    # Antes de conferir a senha, como manda a nota: passou do limite, não atende.
    if falhas_recentes(db, email, ip, origem="senha") >= MAX_TENTATIVAS:
        log_event("LOGIN_BLOQUEADO", level="WARN", email=email or None, ip=ip,
                  janela_min=JANELA_MINUTOS)
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas. Aguarde {JANELA_MINUTOS} minutos.",
        )

    user = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if not user or not verify_password(dados.senha, user.senha_hash):
        registrar_tentativa(db, email, ip, sucesso=False, origem="senha")
        log_event("LOGIN_RECUSADO", level="WARN", email=email or None, ip=ip,
                  motivo="credenciais")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos"
        )
    if getattr(user, "bloqueado", False) or not user.ativo:
        registrar_tentativa(db, email, ip, sucesso=False, origem="senha")
        log_event("LOGIN_RECUSADO", level="WARN", email=email or None, ip=ip,
                  motivo="conta")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário bloqueado")

    access_token = create_access_token(data={"sub": user.email})
    registrar_tentativa(db, email, ip, sucesso=True, origem="senha")
    log_event("LOGIN_OK", email=email, ip=ip, usuario_id=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UsuarioResponse, status_code=201)
def register(
    usuario: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    existing = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    db_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=get_password_hash(usuario.senha),
        cargo=usuario.cargo
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

class SSORequest(BaseModel):
    # Com valor padrão de propósito: corpo sem o campo cai na recusa única de
    # 404, e não num 422 do pydantic que responderia diferente das outras.
    bilhete: str = ""


def _recusa_sso(db: Session, email: str, ip: str, motivo: str):
    """Recusa única: 404 com a MESMA mensagem, e o motivo só no log.

    404 e não 403, pela mesma razão do padrão de IDOR: 403 confirmaria que o
    recurso existe. Aqui confirmaria que o bilhete era legítimo e o problema
    está na conta, ou o contrário."""
    registrar_tentativa(db, email, ip, sucesso=False)
    log_event("SSO_RECUSADO", level="WARN", email=email or None, ip=ip, motivo=motivo)
    return HTTPException(status_code=404, detail=RECUSA_SSO)


def _marcar_bilhete_usado(db: Session, jti: str, ip: str) -> bool:
    """Uso único, decidido pelo banco e conferido pelo código.

    Quem chega primeiro insere; o segundo bate no conflito da chave primária e
    não afeta linha nenhuma. Sem conferir `rowcount`, a trava do banco existiria
    e ninguém obedeceria ao veredito dela.

    Isto acontece ANTES de qualquer sessão ser emitida: entre emitir e marcar
    existiria uma janela, e janela em credencial é onde o segundo pedido entra.
    """
    res = db.execute(
        text("INSERT INTO sso_bilhetes_usados (jti, usado_em, ip) "
             "VALUES (:jti, :usado_em, :ip) ON CONFLICT (jti) DO NOTHING"),
        {"jti": jti[:64], "usado_em": datetime.utcnow(), "ip": (ip or "")[:45]},
    )
    db.commit()
    return res.rowcount == 1


@router.post("/sso", response_model=Token)
def entrar_por_sso(body: SSORequest, request: Request, db: Session = Depends(get_db)):
    """Troca o bilhete do Hub Zoaria pelo MESMO JWT do login por senha.

    O bilhete carrega identidade e nada mais. Grupo, setor, empresa e overrides
    continuam sendo do Tareffas: o Hub só diz quem é a pessoa.

    Esta rota é porta de entrada externa, então não exige token de sessão nem
    tem o que isentar de CSRF: o projeto autentica por `Authorization: Bearer`
    guardado em `localStorage`, e não por cookie, então o navegador não anexa
    credencial sozinho num pedido de outro site.
    """
    ip = ip_cliente(request)
    bilhete = (body.bilhete or "").strip()

    # 1. Tamanho ANTES de tocar o banco. Lixo de 10 KB não merece uma query.
    if not bilhete or len(bilhete) > sso_bilhete.TAMANHO_MAXIMO:
        log_event("SSO_RECUSADO", level="WARN", email=None, ip=ip, motivo="tamanho")
        raise HTTPException(status_code=404, detail=RECUSA_SSO)

    # 2. Força bruta: o IP que erra em série para de ser atendido.
    if falhas_recentes(db, "", ip) >= MAX_TENTATIVAS:
        log_event("SSO_BLOQUEADO", level="WARN", ip=ip, janela_min=JANELA_MINUTOS)
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas. Aguarde {JANELA_MINUTOS} minutos.",
        )

    # 3. Assinatura, prazo e formato. Sem chave configurada, nada abre.
    dados = sso_bilhete.ler_bilhete(bilhete)
    if not dados:
        raise _recusa_sso(db, "", ip, "bilhete")

    email = str(dados.get("email") or "").strip().lower()
    jti = str(dados.get("jti") or "")

    # 4. Uso único ANTES de emitir qualquer sessão.
    if not _marcar_bilhete_usado(db, jti, ip):
        raise _recusa_sso(db, email, ip, "repetido")

    # 5. A conta precisa existir e estar elegível AGORA, não quando o bilhete
    #    foi emitido. Todos os casos saem pela mesma porta.
    #    Casamento sem diferenciar maiúscula: quem cadastrou "Fulano@bps4.com.br"
    #    aqui e "fulano@bps4.com.br" no Hub é a mesma pessoa, e comparação exata
    #    barraria gente legítima. Duas contas que só diferem por caixa tornam a
    #    identidade ambígua, e aí ninguém entra: escolher uma seria escolher no
    #    escuro de quem é a sessão.
    candidatos = db.query(Usuario).filter(func.lower(Usuario.email) == email).all()
    if len(candidatos) > 1:
        raise _recusa_sso(db, email, ip, "email_ambiguo")
    user = candidatos[0] if candidatos else None
    if not user:
        raise _recusa_sso(db, email, ip, "sem_cadastro")
    if getattr(user, "bloqueado", False):
        raise _recusa_sso(db, email, ip, "bloqueado")
    if not user.ativo:
        raise _recusa_sso(db, email, ip, "inativo")
    # Convite pendente NÃO barra a entrada pelo Hub: ele existe para a pessoa
    # criar uma SENHA, e quem entra por bilhete não usa senha. Exigir a ativação
    # antes seria atrito sem ganho — a liberação do card no Hub já é a decisão
    # de quem pode entrar, e o Hub já autenticou. O primeiro acesso pelo card
    # ativa a conta; o token de convite continua de pé para quem depois quiser
    # senha própria.
    if user.ativado is False:
        user.ativado = True
        db.commit()
        log_event("SSO_ATIVOU_CONTA", email=email, ip=ip, usuario_id=user.id)

    # 6. O MESMO token do login por senha, com a MESMA validade. Entrar pelo
    #    Hub não compra sessão mais longa.
    access_token = create_access_token(data={"sub": user.email})
    registrar_tentativa(db, email, ip, sucesso=True)
    log_event("SSO_OK", email=email, ip=ip, usuario_id=user.id)
    _limpar_bilhetes_antigos(db)
    return {"access_token": access_token, "token_type": "bearer"}


def _limpar_bilhetes_antigos(db: Session) -> None:
    """Varre o rastro vencido, dos bilhetes e das tentativas. Roda no fim da
    entrada bem sucedida, que é raro o bastante para não pesar e frequente o
    bastante para as duas tabelas não crescerem para sempre."""
    corte = datetime.utcnow() - timedelta(days=RETENCAO_BILHETES_DIAS)
    db.query(SSOBilheteUsado).filter(SSOBilheteUsado.usado_em < corte).delete()
    db.commit()
    limpar_tentativas_antigas(db)


@router.get("/me", response_model=MeResponse)
def get_me(current_user: Usuario = Depends(get_current_user)):
    return MeResponse(
        id=current_user.id,
        nome=current_user.nome,
        email=current_user.email,
        cargo=current_user.cargo,
        grupo=current_user.grupo,
        permissoes_efetivas=permissao_efetiva(current_user),
    )