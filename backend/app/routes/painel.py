"""Painel: os números do mês em uma consulta só, com filtros.

Substitui `/tarefas/dashboard/stats` e `/dashboard/stats-por-setor`, que
respondiam perguntas soltas e não conversavam entre si.

Duas decisões estruturam este arquivo:

1. SITUAÇÃO EXCLUSIVA. A versão anterior contava "atrasada" dentro de
   "pendente", e a rosca do dashboard somava 101%. Aqui cada tarefa está em uma
   situação e só uma: concluída, cancelada, atrasada, em andamento ou pendente.
   Atrasada tira de pendente — é o que a pessoa entende ao ver o gráfico.

2. AGREGA EM MEMÓRIA. Uma consulta traz as colunas necessárias e o resto é
   contagem em Python. Com centenas de tarefas isso é mais barato que as vinte
   consultas que as rotas antigas faziam, e permite cortar por setor, por
   colaborador e por multa sem multiplicar idas ao banco.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Tarefa, Usuario, Setor, StatusTarefa, tarefa_responsaveis
from ..auth import get_current_user
from .tarefas import _aplicar_escopo

router = APIRouter(prefix="/painel", tags=["painel"])

SITUACOES = ("pendente", "em_andamento", "atrasada", "concluida", "cancelada")


def _situacao(status, prazo, agora) -> str:
    """Em que situação a tarefa está AGORA — uma só, nunca duas."""
    if status == StatusTarefa.CONCLUIDA:
        return "concluida"
    if status == StatusTarefa.CANCELADA:
        return "cancelada"
    if prazo and prazo < agora:
        return "atrasada"
    if status == StatusTarefa.EM_ANDAMENTO:
        return "em_andamento"
    return "pendente"


def _zero():
    return {s: 0 for s in SITUACOES} | {"total": 0, "multa": 0}


def _somar(alvo: dict, situacao: str, multa: bool):
    alvo[situacao] = alvo.get(situacao, 0) + 1
    alvo["total"] = alvo.get("total", 0) + 1
    # Multa só conta no que ainda pode dar problema: tarefa concluída que gera
    # multa já não é risco, e somá-la faria o número crescer justamente à
    # medida que o trabalho anda.
    if multa and situacao in ("pendente", "em_andamento", "atrasada"):
        alvo["multa"] = alvo.get("multa", 0) + 1


@router.get("")
def painel(
    empresa_id: int = None,
    setor_id: int = None,
    usuario_id: int = None,
    competencia: str = None,
    so_multa: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    agora = datetime.utcnow()
    hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_semana = hoje + timedelta(days=7)

    q = _aplicar_escopo(db.query(Tarefa), db, current_user)
    if empresa_id:
        q = q.filter(Tarefa.empresa_id == empresa_id)
    if setor_id:
        q = q.filter(Tarefa.setor_id == setor_id)
    if competencia:
        q = q.filter(Tarefa.competencia == competencia)
    if so_multa:
        q = q.filter(Tarefa.gera_multa == True)
    if usuario_id:
        q = q.filter(Tarefa.responsaveis.any(Usuario.id == usuario_id))

    tarefas = q.with_entities(
        Tarefa.id, Tarefa.titulo, Tarefa.status, Tarefa.data_prazo,
        Tarefa.setor_id, Tarefa.gera_multa, Tarefa.empresa_id).all()
    ids = [t.id for t in tarefas]

    nomes_setor = {s.id: s.nome for s in db.query(Setor).all()}
    # Responsáveis de todas as tarefas numa consulta, não uma por tarefa.
    resp = {}
    if ids:
        for tid, uid, nome in (db.query(tarefa_responsaveis.c.tarefa_id, Usuario.id, Usuario.nome)
                               .join(Usuario, Usuario.id == tarefa_responsaveis.c.usuario_id)
                               .filter(tarefa_responsaveis.c.tarefa_id.in_(ids)).all()):
            resp.setdefault(tid, []).append((uid, nome))

    resumo = _zero()
    resumo["vence_hoje"] = 0
    resumo["vence_semana"] = 0
    por_setor, por_colaborador = {}, {}

    for t in tarefas:
        sit = _situacao(t.status, t.data_prazo, agora)
        multa = bool(t.gera_multa)
        _somar(resumo, sit, multa)
        if sit in ("pendente", "em_andamento") and t.data_prazo:
            if hoje <= t.data_prazo < hoje + timedelta(days=1):
                resumo["vence_hoje"] += 1
            if hoje <= t.data_prazo <= fim_semana:
                resumo["vence_semana"] += 1

        chave_setor = nomes_setor.get(t.setor_id) or "Sem setor"
        _somar(por_setor.setdefault(chave_setor, _zero()), sit, multa)

        pessoas = resp.get(t.id) or [(None, "Sem responsável")]
        for _uid, nome in pessoas:
            _somar(por_colaborador.setdefault(nome, _zero()), sit, multa)

    def lista(d):
        # Mais carregado primeiro: quem tem mais em aberto é o que se olha antes.
        return sorted(
            [{"nome": k, **v} for k, v in d.items()],
            key=lambda x: (-(x["atrasada"] + x["pendente"] + x["em_andamento"]), x["nome"]))

    # Próximas do vencimento, agrupadas por setor. Só o que ainda vai ser feito.
    abertas = [t for t in tarefas
               if _situacao(t.status, t.data_prazo, agora) in ("pendente", "em_andamento", "atrasada")
               and t.data_prazo]
    abertas.sort(key=lambda t: t.data_prazo)
    grupos = {}
    for t in abertas[:200]:
        g = grupos.setdefault(nomes_setor.get(t.setor_id) or "Sem setor",
                              {"setor": nomes_setor.get(t.setor_id) or "Sem setor",
                               "total": 0, "atrasadas": 0, "tarefas": []})
        atrasada = t.data_prazo < agora
        g["total"] += 1
        g["atrasadas"] += 1 if atrasada else 0
        if len(g["tarefas"]) < 25:
            g["tarefas"].append({
                "id": t.id, "titulo": t.titulo, "data_prazo": t.data_prazo,
                "atrasada": atrasada, "multa": bool(t.gera_multa),
                "responsaveis": [n for _i, n in (resp.get(t.id) or [])],
            })
    proximas = sorted(grupos.values(), key=lambda g: (-g["atrasadas"], -g["total"], g["setor"]))

    return {"resumo": resumo, "por_setor": lista(por_setor),
            "por_colaborador": lista(por_colaborador), "proximas": proximas}
