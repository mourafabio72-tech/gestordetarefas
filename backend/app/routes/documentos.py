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
    tipo: str = "recebidos",        # recebidos (do cliente) | entregues (ao cliente)
    baixado: str = None,            # entregues: "sim" | "nao"
    limite: int = Query(LIMITE_PADRAO, ge=1, le=LIMITE_MAXIMO),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Tarefas que têm comprovante, com os filtros da tela.

    O escopo é o MESMO da listagem de tarefas: quem não enxerga a tarefa não
    encontra o documento dela aqui. Sem isso, esta rota seria uma porta lateral
    para o acervo inteiro.
    """
    # Dois acervos, não um: o que o cliente MANDOU (comprovante) e o que o
    # escritório ENTREGOU (guia). Misturar os dois numa lista só faria a coluna
    # "arquivo" significar coisas diferentes em linhas vizinhas.
    entregues = (tipo or "recebidos").lower() == "entregues"
    campo_arquivo = Tarefa.saida_nome if entregues else Tarefa.anexo_nome
    q = _aplicar_escopo(db.query(Tarefa), db, current_user).filter(
        campo_arquivo.isnot(None), campo_arquivo != "")
    if entregues and baixado in ("sim", "nao"):
        # A pergunta do fim do mês: quem ainda não pegou a guia.
        q = q.filter((Tarefa.saida_downloads > 0) if baixado == "sim"
                     else ((Tarefa.saida_downloads == 0) | (Tarefa.saida_downloads.is_(None))))

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
                         func.lower(campo_arquivo).like(alvo)))
    if extensao:
        q = q.filter(func.lower(campo_arquivo).like(f"%.{extensao.strip().lower()}"))

    total = q.count()
    linhas = (q.options(joinedload(Tarefa.empresa), joinedload(Tarefa.setor),
                        joinedload(Tarefa.obrigacao), selectinload(Tarefa.responsaveis))
              # Entrega mais recente primeiro; quem não tem data de entrega
              # (comprovante de antes do campo) cai para o fim pelo id.
              .order_by((Tarefa.saida_baixada_em if entregues else Tarefa.data_entrega)
                        .desc().nullslast(), Tarefa.id.desc())
              .limit(limite).all())

    docs = []
    for t in linhas:
        bruto = t.saida_nome if entregues else t.anexo_nome
        nome = up.nome_de_exibicao(bruto)
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
            # Só faz sentido no acervo de entregues, e é o que responde
            # "o cliente pegou?".
            "downloads": (t.saida_downloads or 0) if entregues else None,
            "baixado_em": t.saida_baixada_em if entregues else None,
            # A tela precisa saber se o arquivo AINDA está no volume: um acervo
            # que lista documento que não abre é pior do que não listar.
            "no_volume": bool(up.caminho_do_anexo(bruto)),
        })

    return {"total": total, "mostrando": len(docs), "tipo": "entregues" if entregues else "recebidos",
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
        or_(Tarefa.anexo_nome.isnot(None), Tarefa.saida_nome.isnot(None)),
        Tarefa.competencia.isnot(None))
    comps = [c for (c,) in q.all() if c]
    return sorted(comps, key=lambda c: (c.split("/")[1] + c.split("/")[0]) if "/" in c else c,
                  reverse=True)
