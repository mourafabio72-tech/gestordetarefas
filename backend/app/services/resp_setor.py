"""Quem responde por um par (empresa, setor).

Existe para haver UM ponto que escreve isso. A lista mora na associativa
`empresa_setor_resp_usuarios`, com a ordem escolhida na tela, e o
`responsavel_id` do vínculo é o PRINCIPAL, que vale sempre o primeiro da lista.
São duas verdades sobre o mesmo fato, e duas verdades divergem quando cada
chamador grava do seu jeito: a tela por um lado, o importador de planilha por
outro. Por isso os dois passam por aqui.
"""
from typing import List

from sqlalchemy.orm import Session

from ..models import EmpresaSetorResponsavel, empresa_setor_resp_usuarios


def gravar(db: Session, vinculo: EmpresaSetorResponsavel, ids: List[int]) -> None:
    """Regrava a lista do vínculo. Lista vazia = atende o setor, sem dono ainda."""
    vinculo.responsavel_id = ids[0] if ids else None
    vinculo.responsaveis = []
    db.flush()                       # o vínculo precisa ter id antes da associativa
    for ordem, uid in enumerate(ids):
        db.execute(empresa_setor_resp_usuarios.insert().values(
            vinculo_id=vinculo.id, usuario_id=uid, ordem=ordem))
