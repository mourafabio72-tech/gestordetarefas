"""sso.py: Tareffas, o consumo do bilhete emitido pelo Hub Zoaria.

Quem clica no card do Tareffas dentro do Hub chega aqui com um bilhete curto na
URL. Este módulo confere tamanho, assinatura e prazo, e devolve a IDENTIDADE que
veio dentro dele. Nada além disso: grupo, setor, empresa e permissões continuam
sendo decisão do Tareffas, e o Hub não opina.

ESPELHO de `aplicações/zoaria-hub/sso.py`, que emite. As três constantes abaixo
(salt, validade e tamanho máximo) precisam ser idênticas nos dois lados: mudar
de um lado só derruba a entrada sem nenhuma mensagem de erro que explique.

O que este módulo NÃO faz, de propósito: uso único. Isso é da rota que consome,
porque é ela que tem o banco. Ver `routes/auth.py`, rota `/api/auth/sso`.
"""

from __future__ import annotations  # produção é 3.12, a máquina local é 3.9

import os
import time

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# Chave PRÓPRIA do SSO, separada da SECRET_KEY que assina o JWT: trocar esta
# derruba só a entrada pelo Hub, e não as sessões de quem já está dentro.
SSO_SECRET = os.getenv("ZOARIA_SSO_SECRET", "").strip()

# Salt próprio, igual ao do Hub. Separa este bilhete de qualquer outro token
# assinado com a mesma chave: um não vale no lugar do outro.
_SALT = "zoaria-sso-bilhete"

# 60 segundos. É o tempo de um redirecionamento, não o de uma pessoa pensando.
VALIDADE_SEGUNDOS = 60

# Teto de tamanho, para recusar lixo ANTES de gastar banco. Um bilhete real fica
# perto de 200 bytes; o resto é folga para nome e e-mail longos.
TAMANHO_MAXIMO = 512


def sso_ativo() -> bool:
    """Sem chave configurada não existe SSO, e a rota recusa tudo."""
    return bool(SSO_SECRET)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(SSO_SECRET, salt=_SALT)


def ler_bilhete(bilhete: str) -> dict | None:
    """Confere tamanho, assinatura e prazo. Devolve o conteúdo ou None.

    Um só retorno de falha para todos os motivos: adulterado, vencido, grande
    demais e malformado saem iguais daqui. Motivo distinto por caso vira oráculo
    para descobrir quais bilhetes existiram.

    O `exp` gravado dentro do bilhete é conferido além do `max_age`, porque o
    prazo é decisão de quem emite, e não de quem lê.
    """
    if not bilhete or len(bilhete) > TAMANHO_MAXIMO:
        return None
    if not sso_ativo():
        return None
    try:
        dados = _serializer().loads(bilhete, max_age=VALIDADE_SEGUNDOS)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(dados, dict):
        return None
    if int(dados.get("exp", 0)) < int(time.time()):
        return None
    if not dados.get("email") or not dados.get("jti"):
        return None
    return dados


if __name__ == "__main__":
    # Checagem executável mínima, exercitando as funções reais. A chave de teste
    # entra no global do módulo para o `_serializer()` enxergá-la: a prova não
    # pode depender de ZOARIA_SSO_SECRET estar definida na máquina de quem roda.
    globals()["SSO_SECRET"] = "chave-de-teste"

    assert sso_ativo(), "com chave definida o SSO tem de estar ativo"

    emissor = URLSafeTimedSerializer("chave-de-teste", salt=_SALT)

    def _emitir(email="alguem@bps4.com.br", nome="Alguém", jti="abc123", segundos=60):
        return emissor.dumps({
            "email": email, "nome": nome, "jti": jti,
            "exp": int(time.time()) + segundos,
        })

    # 1. PROVA POSITIVA. Sem ela, uma função que recusa tudo passa no resto.
    lido = ler_bilhete(_emitir())
    assert lido is not None, "bilhete recém-emitido tinha de abrir"
    assert lido["email"] == "alguem@bps4.com.br"
    assert lido["nome"] == "Alguém", "acentuação tem de sobreviver ao trajeto"
    assert lido["jti"] == "abc123"

    # 2. Chave errada não abre.
    alheio = URLSafeTimedSerializer("chave-errada", salt=_SALT).dumps(
        {"email": "invasor@exemplo.com", "nome": "x", "jti": "y",
         "exp": int(time.time()) + 60})
    assert ler_bilhete(alheio) is None, "bilhete de outra chave tinha de ser recusado"

    # 3. Salt errado não abre, mesmo com a chave certa.
    salt_alheio = URLSafeTimedSerializer("chave-de-teste", salt="outro-salt").dumps(
        {"email": "a@b.c", "nome": "x", "jti": "y", "exp": int(time.time()) + 60})
    assert ler_bilhete(salt_alheio) is None, "token de outro salt tinha de ser recusado"

    # 4. `exp` no passado não abre, mesmo com assinatura boa e dentro do max_age.
    assert ler_bilhete(_emitir(segundos=-1)) is None, "exp vencido tinha de ser recusado"

    # 5. Bilhete sem e-mail ou sem jti não abre: sem eles não há quem entrar nem
    #    o que marcar como usado.
    sem_email = emissor.dumps({"email": "", "nome": "x", "jti": "y",
                               "exp": int(time.time()) + 60})
    sem_jti = emissor.dumps({"email": "a@b.c", "nome": "x", "jti": "",
                             "exp": int(time.time()) + 60})
    assert ler_bilhete(sem_email) is None and ler_bilhete(sem_jti) is None

    # 6. Tamanho, vazio e lixo: recusa antes de qualquer conta.
    assert ler_bilhete("A" * (TAMANHO_MAXIMO + 1)) is None
    assert ler_bilhete("") is None and ler_bilhete("lixo") is None

    # 7. Sem chave, nada abre, nem um bilhete que era válido um instante atrás.
    valido = _emitir()
    globals()["SSO_SECRET"] = ""
    assert not sso_ativo(), "sem chave o SSO tem de ficar desligado"
    assert ler_bilhete(valido) is None, "sem chave nem bilhete bom pode abrir"

    print(f"PROVA OK: abre com a chave certa; recusa chave errada, salt alheio, "
          f"exp vencido, campo faltando, tamanho acima de {TAMANHO_MAXIMO}, lixo "
          f"e SSO desligado")
