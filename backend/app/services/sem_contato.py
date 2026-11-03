"""Empresas que deviam receber guia e não têm para onde enviar (2026-11-03).

O e-validador só descobre isso na hora de enviar ("Sem destinatário"), com a
guia na mão. Aqui a pergunta é feita antes, pelas mesmas regras: quem a obrigação
alcança é o que o gerador usa, e quem recebe é o que o envio usa.
"""
from ..models import Obrigacao, StatusTarefa, Tarefa
from .gerador import _empresa_atende, empresas_alvo
from .razao_social import formatar as formatar_razao
from .whatsapp import destinatarios_da_empresa


def _motivo(empresa) -> str:
    if (empresa.email or "").strip():
        return "E-mail inválido na ficha"
    if (empresa.telefone or "").strip():
        return "Telefone inválido na ficha"
    return "Sem e-mail e sem telefone"


def empresas_sem_contato(db) -> list:
    """Uma linha por empresa, com as obrigações de "entregar" que a alcançam."""
    alcance, empresas, tem_contato = {}, {}, {}
    obrigacoes = (db.query(Obrigacao)
                  .filter(Obrigacao.ativa == True, Obrigacao.sentido == "entregar")
                  .order_by(Obrigacao.nome).all())
    for o in obrigacoes:
        for e in empresas_alvo(db, o):
            if e.id not in tem_contato:
                tem_contato[e.id] = bool(destinatarios_da_empresa(db, e))
                empresas[e.id] = e
            if tem_contato[e.id] or not _empresa_atende(db, e.id, o.setor_id):
                continue
            alcance.setdefault(e.id, []).append(o)

    linhas = []
    for eid, obrs in alcance.items():
        e = empresas[eid]
        abertas = (db.query(Tarefa)
                   .filter(Tarefa.empresa_id == eid,
                           Tarefa.obrigacao_id.in_([o.id for o in obrs]),
                           Tarefa.status.notin_([StatusTarefa.CONCLUIDA, StatusTarefa.CANCELADA]))
                   .count())
        linhas.append({
            "empresa_id": eid,
            "razao_social": formatar_razao(e.razao_social),
            "cnpj": e.cnpj,
            "email": e.email or None,
            "telefone": e.telefone or None,
            "motivo": _motivo(e),
            "obrigacoes": [(o.mininome or "").strip() or o.nome for o in obrs],
            "tarefas_abertas": abertas,
        })
    return sorted(linhas, key=lambda l: l["razao_social"].lower())
