"""Painel: os números do mês em uma consulta só, com filtros.

Substitui `/tarefas/dashboard/stats` e `/dashboard/stats-por-setor`, que
respondiam perguntas soltas e não conversavam entre si.

Três decisões estruturam este arquivo:

1. SITUAÇÃO EXCLUSIVA. A versão anterior contava "atrasada" dentro de
   "pendente", e a rosca do dashboard somava 101%. Aqui cada tarefa está em uma
   situação e só uma: concluída, cancelada, atrasada, em andamento ou pendente.
   Atrasada tira de pendente — é o que a pessoa entende ao ver o gráfico.

2. AGREGA EM MEMÓRIA. Uma consulta traz as colunas necessárias e o resto é
   contagem em Python. Com centenas de tarefas isso é mais barato que as vinte
   consultas que as rotas antigas faziam, e permite cortar por setor, por
   colaborador, por empresa e por multa sem multiplicar idas ao banco.

3. COMPARA DATA EM PYTHON, ENTÃO NORMALIZA O FUSO. As rotas antigas
   comparavam `data_prazo < now` dentro do SQL, e o banco resolvia o fuso
   sozinho. Aqui a comparação é em Python: a coluna é DateTime(timezone=True),
   o Postgres devolve AWARE e o SQLite devolve NAIVE, e misturar os dois
   levanta TypeError. Toda data lida passa por `_utc()` antes de ser comparada.

4. ATRASO TEM DONO. "12 atrasadas" não diz o que fazer. Atraso porque o cliente
   não mandou o documento é cobrança; atraso com o documento na mão é trabalho
   parado aqui dentro. São dois problemas diferentes, com duas ações
   diferentes, e o painel separa os dois.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (Tarefa, Usuario, Setor, Empresa, Obrigacao, TarefaEnvio,
                      StatusTarefa, PrioridadeTarefa, tarefa_responsaveis)
from ..auth import get_current_user
from .tarefas import _aplicar_escopo

router = APIRouter(prefix="/painel", tags=["painel"])

SITUACOES = ("pendente", "em_andamento", "atrasada", "concluida", "cancelada")
ABERTAS = ("pendente", "em_andamento", "atrasada")


def _utc(dt):
    """Data comparável, venha ela com fuso ou sem.

    Postgres devolve datetime aware; SQLite, naive. `aware < naive` é
    TypeError, e foi o 500 do painel em produção — invisível na prova, que
    roda em SQLite. Sem fuso, assume UTC: é o que `datetime.utcnow()` gravou.
    """
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _situacao(status, prazo, agora) -> str:
    """Em que situação a tarefa está AGORA — uma só, nunca duas.

    `prazo` já tem de vir de `_utc()`."""
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
    if multa and situacao in ABERTAS:
        alvo["multa"] = alvo.get("multa", 0) + 1


def _perfil_obrigacao(o) -> tuple:
    """(sentido, exige_documento) da obrigação — mesma regra do model.

    Repetida aqui porque a consulta do painel não carrega o objeto Tarefa, e
    instanciar centenas de ORM só para ler duas propriedades desfaz a economia
    de trazer colunas soltas.
    """
    sentido = (o.sentido or "receber")
    if sentido == "interna":
        return sentido, False
    if o.exige_documento is None:
        return sentido, bool((o.identificadores or "").strip())
    return sentido, bool(o.exige_documento)


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
    agora = datetime.now(timezone.utc)
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
        Tarefa.data_vencimento, Tarefa.data_conclusao, Tarefa.prioridade,
        Tarefa.setor_id, Tarefa.empresa_id, Tarefa.obrigacao_id,
        Tarefa.gera_multa, Tarefa.anexo_nome, Tarefa.saida_downloads).all()
    ids = [t.id for t in tarefas]

    nomes_setor = {s.id: s.nome for s in db.query(Setor).all()}
    nomes_empresa = {e.id: (e.nome_fantasia or e.razao_social)
                     for e in db.query(Empresa.id, Empresa.razao_social, Empresa.nome_fantasia).all()}
    perfis = {o.id: _perfil_obrigacao(o) for o in db.query(
        Obrigacao.id, Obrigacao.sentido, Obrigacao.exige_documento, Obrigacao.identificadores).all()}

    # Responsáveis de todas as tarefas numa consulta, não uma por tarefa.
    resp = {}
    if ids:
        for tid, uid, nome in (db.query(tarefa_responsaveis.c.tarefa_id, Usuario.id, Usuario.nome)
                               .join(Usuario, Usuario.id == tarefa_responsaveis.c.usuario_id)
                               .filter(tarefa_responsaveis.c.tarefa_id.in_(ids)).all()):
            resp.setdefault(tid, []).append((uid, nome))

    # Último envio bem-sucedido por tarefa: é o que permite dizer "saiu daqui
    # há 4 dias e ninguém abriu".
    enviado_em = {}
    if ids:
        for tid, quando in (db.query(TarefaEnvio.tarefa_id, func.max(TarefaEnvio.enviado_em))
                            .filter(TarefaEnvio.tarefa_id.in_(ids), TarefaEnvio.sucesso == True)
                            .group_by(TarefaEnvio.tarefa_id).all()):
            enviado_em[tid] = quando

    resumo = _zero() | {"vence_hoje": 0, "vence_semana": 0, "urgentes": 0,
                        "aguardando_cliente": 0, "nao_abertas": 0,
                        "concluidas_com_prazo": 0, "no_prazo": 0}
    por_setor, por_colaborador, por_empresa = {}, {}, {}
    aguardando, nao_abertas = [], []

    for t in tarefas:
        prazo = _utc(t.data_prazo)
        sit = _situacao(t.status, prazo, agora)
        multa = bool(t.gera_multa)
        aberta = sit in ABERTAS
        _somar(resumo, sit, multa)

        if aberta and prazo:
            if hoje <= prazo < hoje + timedelta(days=1):
                resumo["vence_hoje"] += 1
            if hoje <= prazo <= fim_semana:
                resumo["vence_semana"] += 1
        if aberta and t.prioridade in (PrioridadeTarefa.URGENTE, PrioridadeTarefa.ALTA):
            resumo["urgentes"] += 1

        # Pontualidade: só as concluídas que tinham prazo para cumprir.
        if sit == "concluida" and prazo and t.data_conclusao:
            resumo["concluidas_com_prazo"] += 1
            if _utc(t.data_conclusao) <= prazo:
                resumo["no_prazo"] += 1

        sentido, exige = perfis.get(t.obrigacao_id, ("receber", False))
        empresa = nomes_empresa.get(t.empresa_id) or "Sem empresa"

        # Travada no cliente: o escritório não tem o que fazer enquanto o
        # documento não chega. Cobrar é a ação, e ela não é a mesma de "sentar
        # e executar" — por isso sai do balaio geral de atrasadas.
        if aberta and sentido == "receber" and exige and not t.anexo_nome:
            resumo["aguardando_cliente"] += 1
            aguardando.append({"id": t.id, "titulo": t.titulo, "empresa": empresa,
                               "data_prazo": prazo, "atrasada": sit == "atrasada"})

        # Saiu daqui e ninguém abriu. A guia entregue no prazo não protege o
        # cliente se ele não baixou: quem leva a multa é ele, e a reclamação
        # chega aqui.
        if sentido == "entregar" and enviado_em.get(t.id) and not (t.saida_downloads or 0):
            resumo["nao_abertas"] += 1
            nao_abertas.append({"id": t.id, "titulo": t.titulo, "empresa": empresa,
                                "enviado_em": enviado_em[t.id],
                                "data_vencimento": _utc(t.data_vencimento) or prazo})

        _somar(por_setor.setdefault(nomes_setor.get(t.setor_id) or "Sem setor", _zero()), sit, multa)
        _somar(por_empresa.setdefault(empresa, _zero()), sit, multa)
        for _uid, nome in (resp.get(t.id) or [(None, "Sem responsável")]):
            _somar(por_colaborador.setdefault(nome, _zero()), sit, multa)

    def lista(d):
        # Mais carregado primeiro: quem tem mais em aberto é o que se olha antes.
        return sorted(
            [{"nome": k, **v} for k, v in d.items()],
            key=lambda x: (-(x["atrasada"] + x["pendente"] + x["em_andamento"]), x["nome"]))

    aguardando.sort(key=lambda x: (x["data_prazo"] is None, x["data_prazo"]))
    nao_abertas.sort(key=lambda x: (x["data_vencimento"] is None, x["data_vencimento"]))

    # Próximas do vencimento, agrupadas por setor. Só o que ainda vai ser feito.
    abertas = [t for t in tarefas
               if _situacao(t.status, _utc(t.data_prazo), agora) in ABERTAS and t.data_prazo]
    abertas.sort(key=lambda t: _utc(t.data_prazo))
    grupos = {}
    for t in abertas[:200]:
        prazo = _utc(t.data_prazo)
        nome_setor = nomes_setor.get(t.setor_id) or "Sem setor"
        g = grupos.setdefault(nome_setor, {"setor": nome_setor, "total": 0,
                                           "atrasadas": 0, "tarefas": []})
        atrasada = prazo < agora
        g["total"] += 1
        g["atrasadas"] += 1 if atrasada else 0
        if len(g["tarefas"]) < 25:
            g["tarefas"].append({
                "id": t.id, "titulo": t.titulo, "data_prazo": prazo,
                "atrasada": atrasada, "multa": bool(t.gera_multa),
                "empresa": nomes_empresa.get(t.empresa_id) or "Sem empresa",
                "responsaveis": [n for _i, n in (resp.get(t.id) or [])],
            })
    proximas = sorted(grupos.values(), key=lambda g: (-g["atrasadas"], -g["total"], g["setor"]))

    return {"resumo": resumo,
            "por_setor": lista(por_setor),
            "por_colaborador": lista(por_colaborador),
            "por_empresa": lista(por_empresa),
            "aguardando": aguardando[:12],
            "nao_abertas": nao_abertas[:12],
            "proximas": proximas}
