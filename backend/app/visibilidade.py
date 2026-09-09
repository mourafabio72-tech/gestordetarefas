"""Quando uma tarefa some por causa de quem responde por ela.

Regra: pessoa bloqueada não aparece, e a tarefa dela também não. Com UM
responsável isso era uma linha; com VÁRIOS, passa a ser uma pergunta diferente,
porque bloquear uma pessoa não pode fazer sumir a tarefa que outra continua
tocando. A tarefa só some quando TODOS os responsáveis estão bloqueados.

Mora num arquivo próprio porque a mesma regra é feita em dois lugares que não
se falam: a listagem da tela (`routes/tarefas.py`) e a varredura dos alertas
(`services/whatsapp.py`). Escrita duas vezes, ela divergiria na primeira
mudança, e uma tarefa apareceria na tela sem gerar alerta, ou o contrário.
"""
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from .models import Tarefa, Usuario, Empresa, StatusTarefa


def responsavel_visivel():
    """Condição SQL: a tarefa tem alguém não bloqueado para responder por ela.

    Três casos, todos de propósito:
    · tem lista e pelo menos um não está bloqueado -> aparece;
    · não tem lista -> cai no responsável principal, que cobre tarefa antiga
      gravada antes do M2M existir;
    · não tem lista nem principal -> aparece. Tarefa sem dono não é tarefa de
      pessoa bloqueada, é buraco de cadastro, e esconder buraco de cadastro é
      exatamente o que faz ninguém arrumar.
    """
    return or_(
        Tarefa.responsaveis.any(Usuario.bloqueado.isnot(True)),
        and_(~Tarefa.responsaveis.any(),
             ~Tarefa.responsavel.has(Usuario.bloqueado == True)),
    )


def tarefas_abertas_do_usuario(db: Session, usuario_id: int) -> list:
    """As tarefas em aberto pelas quais a pessoa responde, principal ou não.

    Serve o disparo manual de alerta, que antes filtrava só pelo
    `responsavel_id`: o segundo responsável via a tarefa na tela e não recebia
    a cobrança. Aplica o mesmo esconde-esconde da listagem, para não cobrar
    ninguém por tarefa de empresa bloqueada nem por tarefa que sumiu da tela.
    """
    return (db.query(Tarefa)
            .filter(Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO]),
                    ~Tarefa.empresa.has(Empresa.bloqueado == True),
                    responsavel_visivel(),
                    or_(Tarefa.responsavel_id == usuario_id,
                        Tarefa.responsaveis.any(Usuario.id == usuario_id)))
            .all())
