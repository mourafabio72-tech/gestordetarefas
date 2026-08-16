"""seguranca.py: IP de quem chamou, log de evento e contagem de tentativas.

Três coisas que toda porta de entrada precisa e que este projeto não tinha:
saber de onde veio o pedido, deixar rastro em formato que uma ferramenta lê, e
contar quantas vezes o mesmo IP errou antes de deixar tentar de novo.

O que NUNCA entra em log aqui: o bilhete, o JWT, a senha. O que entra é quem
tentou, de onde, e o que aconteceu.
"""

from __future__ import annotations  # produção é 3.12, a máquina local é 3.9

import json
import sys
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import LoginTentativa

# Mesmos parâmetros da nota de força bruta da vault. Ficam aqui, e não na tabela
# `configuracoes`, porque valor de segurança que só se muda com deploy é um
# problema menor do que valor de segurança que qualquer um afrouxa pela tela.
MAX_TENTATIVAS = 5
JANELA_MINUTOS = 15

# Rastro de tentativa é insumo de investigação, não arquivo permanente.
RETENCAO_TENTATIVAS_DIAS = 30

# Quantos saltos NOSSOS anexam o próprio IP em `X-Forwarded-For` depois que o
# cliente já foi identificado. Aqui é 1: o nginx do frontend faz proxy de /api
# com `$proxy_add_x_forwarded_for` e acrescenta o IP do Traefik do EasyPanel.
# Mudar a topologia (tirar o nginx, pôr um CDN na frente) muda este número, e
# errar aqui não quebra nada visível: só faz o limite por IP contar o alvo errado.
PROXIES_ANEXADOS = 1


def ip_cliente(request) -> str:
    """IP de quem chamou, atrás do nginx e do proxy do EasyPanel.

    Lê a lista de trás para frente, e não do começo. O começo é território do
    cliente: quem quiser escapar do limite por IP manda `X-Forwarded-For: 1.2.3.4`
    e ganha um IP novo a cada tentativa, porque o nginx ANEXA à lista em vez de
    substituir. O fim da lista é escrito pelos nossos proxies, um por salto, e é
    a única parte que o cliente não consegue forjar.
    """
    encaminhado = (request.headers.get("x-forwarded-for") or "").strip()
    if encaminhado:
        partes = [p.strip() for p in encaminhado.split(",") if p.strip()]
        if len(partes) > PROXIES_ANEXADOS:
            return partes[-(PROXIES_ANEXADOS + 1)][:45]
        if partes:
            return partes[0][:45]
    return (request.client.host if request.client else "")[:45]


def log_event(event: str, level: str = "INFO", **campos) -> None:
    """Uma linha JSON por evento, no stdout que o EasyPanel captura."""
    linha = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "level": level,
        "event": event,
    }
    linha.update(campos)
    print(json.dumps(linha, ensure_ascii=False), file=sys.stdout, flush=True)


def registrar_tentativa(db: Session, email: str, ip: str, sucesso: bool,
                        origem: str = "sso") -> None:
    """Toda tentativa, sucesso ou falha, deixa linha. Sem exceção."""
    db.add(LoginTentativa(
        email=(email or "")[:200],
        ip=(ip or "")[:45],
        origem=origem,
        sucesso=bool(sucesso),
    ))
    db.commit()


def falhas_recentes(db: Session, email: str, ip: str,
                    origem: str = "sso") -> int:
    """Conta falhas da janela por e-mail OU IP, como manda a nota da vault.

    O `origem` separa a conta do SSO da conta do login por senha: quem errou a
    senha cinco vezes não deveria ficar impedido de entrar pelo caminho do Hub,
    que é outra credencial.
    """
    corte = datetime.utcnow() - timedelta(minutes=JANELA_MINUTOS)
    q = db.query(LoginTentativa).filter(
        LoginTentativa.sucesso.is_(False),
        LoginTentativa.origem == origem,
        LoginTentativa.criado_em > corte,
    )
    alvo = []
    if email:
        alvo.append(LoginTentativa.email == email)
    if ip:
        alvo.append(LoginTentativa.ip == ip)
    if not alvo:
        return 0
    from sqlalchemy import or_
    return q.filter(or_(*alvo)).count()


def limpar_tentativas_antigas(db: Session) -> int:
    """Apaga rastro que passou da retenção. Devolve quantas linhas saíram."""
    corte = datetime.utcnow() - timedelta(days=RETENCAO_TENTATIVAS_DIAS)
    n = db.query(LoginTentativa).filter(LoginTentativa.criado_em < corte).delete()
    db.commit()
    return n
