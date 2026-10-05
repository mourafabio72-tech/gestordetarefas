"""Pergunte à IA (pedido de 2026-10-05).

A IA só traduz a pergunta num filtro. Para ela vão a pergunta e a data de hoje,
e nada do banco: nome de cliente, CNPJ e título de tarefa não saem daqui. O
filtro volta cru, é validado campo a campo (o que vier inválido é descartado e
listado em `ignorados`), e quem consulta é o Tareffas, com o escopo de quem
perguntou. A frase "entendi" é montada do filtro validado, nunca do texto da IA:
o que a tela diz que filtrou é o que filtrou.
"""
import re
import time
import unicodedata
from collections import defaultdict, deque
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session, joinedload, selectinload

from ..auth import get_current_user
from ..database import get_db
from ..models import Tarefa, Empresa, Setor, Usuario, StatusTarefa
from ..permissoes import eh_cliente
from ..seguranca import log_event
from ..services import config as cfgmod, ia as ia_mod
from .tarefas import _aplicar_escopo

router = APIRouter(prefix="/ia", tags=["ia"])

TZ = ZoneInfo("America/Sao_Paulo")
LIMITE = 20            # perguntas por pessoa...
JANELA = 10 * 60       # ...a cada 10 minutos. Cada pergunta custa na conta da chave.
MAX_LISTA = 50         # a contagem é sempre a real; a lista para aqui
_uso = defaultdict(deque)

SITUACOES = {
    "atrasada": "atrasadas",
    "hoje": "que vencem hoje",
    "semana": "que vencem nos próximos 7 dias",
    "aberta": "em aberto",
    "concluida": "concluídas",
    "cancelada": "canceladas",
}
PRIORIDADES = {"baixa", "media", "alta", "urgente", "alta_urgente"}
TEXTOS = ("setor", "empresa", "obrigacao")
COMPETENCIA = re.compile(r"^(0[1-9]|1[0-2])/\d{4}$")


def _sem_acento(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _hoje() -> date:
    return datetime.now(TZ).date()


def _colaborador(user: Usuario = Depends(get_current_user)) -> Usuario:
    if eh_cliente(user):
        raise HTTPException(status_code=403, detail="Recurso da equipe.")
    return user


def normalizar(cru: dict):
    """(filtro válido, nomes dos campos descartados)."""
    f, ignorados = {}, []
    for k, v in (cru or {}).items():
        if v is None or v == "" or v is False:
            continue
        ok = True
        if k == "situacao":
            ok = v in SITUACOES
        elif k == "data_campo":
            ok = v in ("prazo", "vencimento")
        elif k in ("data_de", "data_ate"):
            try:
                v = date.fromisoformat(str(v)[:10])
            except ValueError:
                ok = False
        elif k == "competencia":
            ok = isinstance(v, str) and bool(COMPETENCIA.match(v.strip()))
            v = str(v).strip()
        elif k in TEXTOS:
            ok = isinstance(v, str) and 0 < len(v.strip()) <= 80
            v = str(v).strip()
        elif k == "prioridade":
            ok = v in PRIORIDADES
        elif k in ("minhas", "multa", "contar"):
            ok = v is True
        else:
            continue                      # campo que não existe: nem conta como erro
        if ok:
            f[k] = v
        else:
            ignorados.append(k)
    return f, ignorados


def _dia(dt):
    return dt.date() if isinstance(dt, datetime) else dt


def _confere(t: Tarefa, f: dict, hoje: date, uid: int, setores: set, empresas: set) -> bool:
    sit = f.get("situacao")
    if sit in ("atrasada", "hoje", "semana"):
        alvo = _dia(t.data_prazo) or _dia(t.data_vencimento)   # o mesmo critério do semáforo da tela
        if alvo is None:
            return False
        dias = (alvo - hoje).days
        if sit == "atrasada" and dias >= 0:
            return False
        if sit == "hoje" and dias != 0:
            return False
        if sit == "semana" and not 0 <= dias <= 7:
            return False
    if "data_de" in f or "data_ate" in f:
        d = _dia(t.data_vencimento if f.get("data_campo") == "vencimento" else t.data_prazo)
        if d is None or ("data_de" in f and d < f["data_de"]) or ("data_ate" in f and d > f["data_ate"]):
            return False
    if "competencia" in f and t.competencia != f["competencia"]:
        return False
    if "setor" in f and t.setor_id not in setores:
        return False
    if "empresa" in f and t.empresa_id not in empresas:
        return False
    if "obrigacao" in f:
        termo = _sem_acento(f["obrigacao"])
        nomes = [t.titulo] + ([t.obrigacao.nome, t.obrigacao.mininome] if t.obrigacao else [])
        if not any(termo in _sem_acento(n) for n in nomes if n):
            return False
    if f.get("minhas"):
        if not (t.responsavel_id == uid or t.supervisor_id == uid
                or any(r.id == uid for r in t.responsaveis)):
            return False
    if "prioridade" in f:
        aceitas = ("alta", "urgente") if f["prioridade"] == "alta_urgente" else (f["prioridade"],)
        if getattr(t.prioridade, "value", t.prioridade) not in aceitas:
            return False
    if f.get("multa") and not t.gera_multa:
        return False
    return True


def _br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def entendi(f: dict) -> str:
    partes = ["Suas tarefas" if f.get("minhas") else "Tarefas"]
    if "situacao" in f:
        partes.append(SITUACOES[f["situacao"]])
    if "obrigacao" in f:
        partes.append(f'de "{f["obrigacao"]}"')
    if "empresa" in f:
        partes.append(f'da empresa "{f["empresa"]}"')
    if "setor" in f:
        partes.append(f'do setor "{f["setor"]}"')
    if "competencia" in f:
        partes.append(f"da competência {f['competencia']}")
    if "data_de" in f or "data_ate" in f:
        campo = "vencimento legal" if f.get("data_campo") == "vencimento" else "prazo interno"
        if "data_de" in f and "data_ate" in f:
            partes.append(f"com {campo} de {_br(f['data_de'])} a {_br(f['data_ate'])}")
        elif "data_de" in f:
            partes.append(f"com {campo} a partir de {_br(f['data_de'])}")
        else:
            partes.append(f"com {campo} até {_br(f['data_ate'])}")
    if "prioridade" in f:
        partes.append("de prioridade alta ou urgente" if f["prioridade"] == "alta_urgente"
                      else f"de prioridade {f['prioridade']}")
    if f.get("multa"):
        partes.append("que geram multa")
    return " ".join(partes) + "."


def _item(t: Tarefa) -> dict:
    emp = t.empresa
    return {
        "id": t.id,
        "titulo": t.titulo,
        "empresa_id": t.empresa_id,
        "empresa": (emp.nome_fantasia or emp.razao_social) if emp else "",
        "setor": t.setor.nome if t.setor else "",
        "competencia": t.competencia,
        "status": getattr(t.status, "value", t.status),
        "data_prazo": _dia(t.data_prazo).isoformat() if t.data_prazo else None,
        "data_vencimento": _dia(t.data_vencimento).isoformat() if t.data_vencimento else None,
    }


class PerguntaIn(BaseModel):
    pergunta: str

    @field_validator("pergunta")
    @classmethod
    def _tamanho(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("Escreva a pergunta.")
        if len(v) > 300:
            raise ValueError("Pergunta longa demais: até 300 caracteres.")
        return v


@router.get("/status")
def status_ia(db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    cfg = cfgmod.carregar(db)
    return {"disponivel": (not eh_cliente(user)) and ia_mod.pergunta_disponivel(cfg),
            "provedor": ia_mod.provedor_escolhido(cfg)}


def _consome_cota(uid: int):
    agora = time.monotonic()
    fila = _uso[uid]
    while fila and agora - fila[0] > JANELA:
        fila.popleft()
    if len(fila) >= LIMITE:
        raise HTTPException(status_code=429,
                            detail=f"Muitas perguntas seguidas. Espere alguns minutos (limite de {LIMITE} a cada 10 minutos).")
    fila.append(agora)


@router.post("/perguntar")
def perguntar(body: PerguntaIn, db: Session = Depends(get_db), user: Usuario = Depends(_colaborador)):
    cfg = cfgmod.carregar(db)
    if not ia_mod.pergunta_disponivel(cfg):
        raise HTTPException(status_code=409,
                            detail="A IA não está configurada. Peça ao admin para cadastrar a chave em Configuração > Inteligência artificial.")
    _consome_cota(user.id)
    hoje = _hoje()
    r = ia_mod.interpretar(body.pergunta, hoje, cfg)
    if "erro" in r:
        # Sem o texto da pergunta no log: ela pode citar cliente.
        log_event("IA_PERGUNTA", level="WARN",
                  provedor=r.get("provedor"), resultado="erro")
        raise HTTPException(status_code=502, detail=r["erro"])

    f, ignorados = normalizar(r["filtro"])
    sit = f.get("situacao")
    q = _aplicar_escopo(db.query(Tarefa), db, user)
    if sit in ("concluida", "cancelada"):
        q = q.filter(Tarefa.status == StatusTarefa(sit))
    elif sit:
        q = q.filter(~Tarefa.status.in_([StatusTarefa.CONCLUIDA, StatusTarefa.CANCELADA]))
    else:
        q = q.filter(Tarefa.status != StatusTarefa.CANCELADA)   # igual à tela de Tarefas

    setores = empresas = set()
    if "setor" in f:
        termo = _sem_acento(f["setor"])
        setores = {s.id for s in db.query(Setor).all() if termo in _sem_acento(s.nome)}
    if "empresa" in f:
        termo = _sem_acento(f["empresa"])
        empresas = {e.id for e in db.query(Empresa.id, Empresa.razao_social, Empresa.nome_fantasia).all()
                    if termo in _sem_acento(e.razao_social) or termo in _sem_acento(e.nome_fantasia)}

    candidatas = (q.options(joinedload(Tarefa.obrigacao), joinedload(Tarefa.setor),
                            joinedload(Tarefa.empresa), selectinload(Tarefa.responsaveis))
                  .order_by(Tarefa.data_prazo.asc()).all())
    achadas = [t for t in candidatas if _confere(t, f, hoje, user.id, setores, empresas)]
    achadas.sort(key=lambda t: (_dia(t.data_prazo) is None, _dia(t.data_prazo) or hoje, t.titulo))

    log_event("IA_PERGUNTA", provedor=r.get("provedor"),
              resultado="ok", total=len(achadas))
    return {
        "entendi": entendi(f),
        "filtro": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in f.items()},
        "ignorados": ignorados,
        "contar": bool(f.get("contar")),
        "total": len(achadas),
        "tarefas": [_item(t) for t in achadas[:MAX_LISTA]],
    }
