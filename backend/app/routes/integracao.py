"""Leitura das empresas por outro app do ecossistema Zoaria (2026-10-25).

O Workforce (produtividade.zoaria.com.br) mede horas por cliente e precisa da lista
de clientes do escritório. Em vez de cadastrar tudo de novo lá, ele lê daqui, por
esta rota SÓ DE LEITURA.

QUEM ENTRA: quem manda `Authorization: Bearer <INTEGRACAO_EMPRESAS_TOKEN>`. Não é o
JWT de usuário, e não abre nada além desta lista. Sem a variável no servidor a rota
responde 404, como se não existisse: integração não configurada fica fechada, e
não aberta. A comparação é em tempo constante.

O QUE SAI: id, razão social, nome fantasia, CNPJ, grupo, ativo e bloqueado. Nada
de responsável, e-mail, telefone ou endereço: o Workforce só precisa reconhecer a
empresa.
"""

import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Empresa
from ..seguranca import ip_cliente, log_event

router = APIRouter(prefix="/integracao", tags=["integracao"])


def _token_valido(request: Request) -> bool:
    esperado = os.getenv("INTEGRACAO_EMPRESAS_TOKEN", "").strip()
    if not esperado:
        raise HTTPException(status_code=404, detail="Not Found")
    cabecalho = request.headers.get("Authorization", "")
    enviado = cabecalho[7:].strip() if cabecalho.startswith("Bearer ") else ""
    return bool(enviado) and hmac.compare_digest(enviado.encode(), esperado.encode())


@router.get("/empresas")
def empresas(request: Request, db: Session = Depends(get_db)):
    if not _token_valido(request):
        log_event("INTEGRACAO_NEGADA", level="WARNING", ip=ip_cliente(request))
        raise HTTPException(status_code=401, detail="Token de integração inválido.")
    lista = [{
        "id": e.id,
        "razao_social": e.razao_social,
        "nome_fantasia": e.nome_fantasia,
        "cnpj": e.cnpj,
        "grupo": e.grupo,
        "ativo": bool(e.ativo),
        "bloqueado": bool(e.bloqueado),
    } for e in db.query(Empresa).order_by(Empresa.id).all()]
    log_event("INTEGRACAO_EMPRESAS", total=len(lista))
    return {"empresas": lista}
