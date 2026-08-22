"""Consulta dos comprovantes que baixaram tarefas.

A tela de Tarefas leva ao documento pela tarefa. Auditoria pede o contrário:
"todos os comprovantes da MKB em 2026", sem saber de qual tarefa cada um veio.
Este é o caminho por documento.

O download em si continua em `/tarefas/{id}/anexo` — aqui só se acha.
"""
import os
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import or_, func
from ..database import get_db
from ..models import Tarefa, Usuario, Obrigacao
from ..auth import get_current_user
from .tarefas import _aplicar_escopo
from ..services import upload as up

router = APIRouter(prefix="/documentos", tags=["documentos"])

# Teto de linhas por consulta. Existe para uma busca sem filtro não arrastar o
# arquivo inteiro do escritório; a resposta diz quando cortou, para a tela poder
# avisar em vez de mentir por omissão que aquilo é tudo.
LIMITE_PADRAO = 300
LIMITE_MAXIMO = 2000


def _data(texto):
    try:
        return date.fromisoformat((texto or "")[:10])
    except ValueError:
        return None


@router.get("")
def listar_documentos(
    empresa_id: int = None,
    setor_id: int = None,
    obrigacao_id: int = None,
    competencia: str = None,
    entrega_de: str = None,
    entrega_ate: str = None,
    usuario_id: int = None,
    texto: str = None,
    extensao: str = None,
    limite: int = Query(LIMITE_PADRAO, ge=1, le=LIMITE_MAXIMO),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Tarefas que têm comprovante, com os filtros da tela.

    O escopo é o MESMO da listagem de tarefas: quem não enxerga a tarefa não
    encontra o documento dela aqui. Sem isso, esta rota seria uma porta lateral
    para o acervo inteiro.
    """
    q = _aplicar_escopo(db.query(Tarefa), db, current_user).filter(
        Tarefa.anexo_nome.isnot(None), Tarefa.anexo_nome != "")

    if empresa_id:
        q = q.filter(Tarefa.empresa_id == empresa_id)
    if setor_id:
        q = q.filter(Tarefa.setor_id == setor_id)
    if obrigacao_id:
        q = q.filter(Tarefa.obrigacao_id == obrigacao_id)
    if competencia:
        q = q.filter(Tarefa.competencia == competencia)
    if usuario_id:
        q = q.filter(or_(Tarefa.responsavel_id == usuario_id,
                         Tarefa.supervisor_id == usuario_id,
                         Tarefa.responsaveis.any(Usuario.id == usuario_id)))
    d1, d2 = _data(entrega_de), _data(entrega_ate)
    if d1:
        q = q.filter(func.date(Tarefa.data_entrega) >= d1)
    if d2:
        q = q.filter(func.date(Tarefa.data_entrega) <= d2)
    if texto:
        # Uma caixa só para título, protocolo e nome do arquivo: quem procura um
        # comprovante lembra de UM desses três, e raramente sabe qual.
        alvo = f"%{texto.strip().lower()}%"
        q = q.filter(or_(func.lower(Tarefa.titulo).like(alvo),
                         func.lower(Tarefa.protocolo_entrega).like(alvo),
                         func.lower(Tarefa.anexo_nome).like(alvo)))
    if extensao:
        q = q.filter(func.lower(Tarefa.anexo_nome).like(f"%.{extensao.strip().lower()}"))

    total = q.count()
    linhas = (q.options(joinedload(Tarefa.empresa), joinedload(Tarefa.setor),
                        joinedload(Tarefa.obrigacao), selectinload(Tarefa.responsaveis))
              # Entrega mais recente primeiro; quem não tem data de entrega
              # (comprovante de antes do campo) cai para o fim pelo id.
              .order_by(Tarefa.data_entrega.desc().nullslast(), Tarefa.id.desc())
              .limit(limite).all())

    docs = []
    for t in linhas:
        nome = up.nome_de_exibicao(t.anexo_nome)
        docs.append({
            "tarefa_id": t.id,
            "arquivo": nome,
            "extensao": os.path.splitext(nome)[1].lower().lstrip("."),
            "titulo": t.titulo,
            "empresa": t.empresa.razao_social if t.empresa else None,
            "empresa_id": t.empresa_id,
            "setor": t.setor.nome if t.setor else None,
            "obrigacao": (t.obrigacao.mininome or t.obrigacao.nome) if t.obrigacao else None,
            "competencia": t.competencia,
            "data_entrega": t.data_entrega,
            "protocolo": t.protocolo_entrega,
            "responsaveis": [u.nome for u in t.responsaveis],
            # A tela precisa saber se o arquivo AINDA está no volume: um acervo
            # que lista documento que não abre é pior do que não listar.
            "no_volume": bool(up.caminho_do_anexo(t.anexo_nome)),
        })

    return {"total": total, "mostrando": len(docs),
            "cortou": total > len(docs), "limite": limite, "documentos": docs}


@router.get("/competencias")
def competencias_com_documento(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Competências que têm comprovante, da mais recente para a mais antiga.

    Sai dos próprios dados para o filtro não oferecer competência que devolveria
    tela vazia. Ordena por AAAA+MM, porque "MM/AAAA" como texto poria 12/2025 na
    frente de 01/2026.
    """
    q = _aplicar_escopo(db.query(Tarefa.competencia).distinct(), db, current_user).filter(
        Tarefa.anexo_nome.isnot(None), Tarefa.anexo_nome != "",
        Tarefa.competencia.isnot(None))
    comps = [c for (c,) in q.all() if c]
    return sorted(comps, key=lambda c: (c.split("/")[1] + c.split("/")[0]) if "/" in c else c,
                  reverse=True)
