"""Substituição de responsável — temporária (janela de datas) ou definitiva (reatribui tudo)."""
from datetime import date
from sqlalchemy.orm import Session
from ..models import Substituicao, Tarefa, Empresa, Obrigacao, Usuario, StatusTarefa


def _temporarias_ativas(db: Session, hoje: date = None):
    hoje = hoje or date.today()
    subs = (db.query(Substituicao)
            .filter(Substituicao.tipo == "temporaria", Substituicao.ativa == True)
            .all())
    return [s for s in subs
            if (not s.data_inicio or s.data_inicio <= hoje)
            and (not s.data_fim or hoje <= s.data_fim)]


def mapa_substitutos(db: Session, hoje: date = None) -> dict:
    """{usuario_ausente_id: Usuario substituto} das substituições temporárias ativas."""
    return {s.usuario_id: s.substituto for s in _temporarias_ativas(db, hoje)}


def originais_cobertos(db: Session, substituto_id: int, hoje: date = None) -> set:
    """Ids das pessoas que este usuário está cobrindo agora (para expandir o escopo)."""
    return {s.usuario_id for s in _temporarias_ativas(db, hoje)
            if s.substituto_id == substituto_id}


def aplicar_definitiva(db: Session, usuario_id: int, substituto_id: int) -> dict:
    """Reatribui de forma permanente tudo de `usuario_id` para `substituto_id`."""
    novo = db.query(Usuario).filter(Usuario.id == substituto_id).first()
    if not novo:
        raise ValueError("Substituto não encontrado")

    tarefas_resp = 0
    for t in db.query(Tarefa).filter(
            Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO])).all():
        mudou = False
        if any(u.id == usuario_id for u in t.responsaveis):
            t.responsaveis = [novo if u.id == usuario_id else u for u in t.responsaveis]
            # dedup mantendo ordem
            vistos, limpos = set(), []
            for u in t.responsaveis:
                if u.id not in vistos:
                    vistos.add(u.id); limpos.append(u)
            t.responsaveis = limpos
            mudou = True
        if t.responsavel_id == usuario_id:
            t.responsavel_id = substituto_id; mudou = True
        if t.supervisor_id == usuario_id:
            t.supervisor_id = substituto_id; mudou = True
        if mudou:
            tarefas_resp += 1

    emp = (db.query(Empresa).filter(Empresa.responsavel_id == usuario_id).update(
        {Empresa.responsavel_id: substituto_id}))
    emp += (db.query(Empresa).filter(Empresa.supervisor_id == usuario_id).update(
        {Empresa.supervisor_id: substituto_id}))
    obg = (db.query(Obrigacao).filter(Obrigacao.responsavel_id == usuario_id).update(
        {Obrigacao.responsavel_id: substituto_id}))
    obg += (db.query(Obrigacao).filter(Obrigacao.supervisor_id == usuario_id).update(
        {Obrigacao.supervisor_id: substituto_id}))

    db.commit()
    return {"tarefas": tarefas_resp, "empresas": emp, "obrigacoes": obg}
