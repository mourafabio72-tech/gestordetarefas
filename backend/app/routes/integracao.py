"""Leitura das empresas e da equipe por outro app do ecossistema Zoaria.

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

A EQUIPE (2026-10-27, pedido do Fábio): `/usuarios` dá ao Workforce quem trabalha
no escritório, para ele cadastrar os colaboradores sem digitar de novo. Sai só
quem é da equipe (`tipo` colaborador), nunca o usuário-cliente; e de cada um só
id, nome, e-mail (é por ele que o Workforce liga a pessoa ao login do Hub), o
nome do setor, ativo e bloqueado. Nada de senha, grupo, permissões, telefone,
cargo ou convite. Mesmo token, mesma regra de porta fechada.
"""

import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Empresa, Usuario
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


@router.get("/usuarios")
def usuarios(request: Request, db: Session = Depends(get_db)):
    if not _token_valido(request):
        log_event("INTEGRACAO_NEGADA", level="WARNING", ip=ip_cliente(request))
        raise HTTPException(status_code=401, detail="Token de integração inválido.")
    equipe = (db.query(Usuario)
              .filter((Usuario.tipo == None) | (Usuario.tipo != "cliente"))  # noqa: E711
              .order_by(Usuario.id).all())
    lista = [{
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "setor": u.setor.nome if u.setor else None,
        "ativo": bool(u.ativo),
        "bloqueado": bool(u.bloqueado),
    } for u in equipe]
    log_event("INTEGRACAO_USUARIOS", total=len(lista))
    return {"usuarios": lista}
