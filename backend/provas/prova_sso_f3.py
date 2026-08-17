"""Prova da Fase 3: o Tareffas consome o bilhete do Hub Zoaria.

Roda contra a rota real, num SQLite temporário. Não depende de Postgres, não
depende de ZOARIA_SSO_SECRET estar definida na máquina, e não deixa arquivo para
trás.

    cd backend && ./venv/bin/python provas/prova_sso_f3.py

Cada caso precisa poder FALHAR. O item 1 é a prova positiva: sem ele, uma rota
que recusa tudo passaria em todos os outros parecendo segura.
"""

from __future__ import annotations  # produção é 3.12, a máquina local é 3.9

import os
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

CHAVE = "chave-de-teste-f3"
_tmp = tempfile.mkdtemp(prefix="prova_sso_f3_")
_banco = os.path.join(_tmp, "prova.db")

# As duas variáveis precisam existir ANTES de importar o app: `database.py` lê a
# URL no import, e `sso.py` lê a chave do mesmo jeito.
os.environ["DATABASE_URL"] = f"sqlite:///{_banco}"
os.environ["ZOARIA_SSO_SECRET"] = CHAVE
os.environ["SECRET_KEY"] = "chave-jwt-de-teste"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI                                    # noqa: E402
from fastapi.testclient import TestClient                      # noqa: E402
from itsdangerous import URLSafeTimedSerializer                # noqa: E402
from jose import jwt                                           # noqa: E402
from sqlalchemy import event                                   # noqa: E402

from app.database import Base, engine, SessionLocal            # noqa: E402
from app.models import Usuario, SSOBilheteUsado, LoginTentativa  # noqa: E402
from app.auth import get_password_hash, SECRET_KEY, ALGORITHM  # noqa: E402
from app.routes import auth as rota_auth                       # noqa: E402
from app import sso as sso_mod                                 # noqa: E402

Base.metadata.create_all(bind=engine)

app = FastAPI(redirect_slashes=False)
app.include_router(rota_auth.router, prefix="/api")
cliente = TestClient(app)

# Contador de queries, para provar que o bilhete grande é recusado ANTES do banco.
_queries = {"n": 0}


@event.listens_for(engine, "before_cursor_execute")
def _conta(conn, cursor, statement, parameters, context, executemany):
    _queries["n"] += 1


emissor = URLSafeTimedSerializer(CHAVE, salt="zoaria-sso-bilhete")
_seq = {"n": 0}


def bilhete(email, nome="Fulano", segundos=60, jti=None, chave=None, salt=None):
    _seq["n"] += 1
    ser = emissor if (chave is None and salt is None) else URLSafeTimedSerializer(
        chave or CHAVE, salt=salt or "zoaria-sso-bilhete")
    return ser.dumps({
        "email": email,
        "nome": nome,
        "jti": jti or f"jti-{_seq['n']}",
        "exp": int(time.time()) + segundos,
    })


def entrar(b, ip="10.0.0.1"):
    return cliente.post("/api/auth/sso", json={"bilhete": b},
                        headers={"X-Forwarded-For": ip})


def semear():
    db = SessionLocal()
    try:
        for email, extra in [
            ("ativa@bps4.com.br", {}),
            ("bloqueada@bps4.com.br", {"bloqueado": True}),
            ("inativa@bps4.com.br", {"ativo": False}),
            ("pendente@bps4.com.br", {"ativado": False}),
        ]:
            u = Usuario(nome="Pessoa", email=email, grupo="analista",
                        senha_hash=get_password_hash("senha-boa-123"), ativo=True)
            for k, v in extra.items():
                setattr(u, k, v)
            db.add(u)
        db.commit()
    finally:
        db.close()


def contar(modelo, **filtros):
    db = SessionLocal()
    try:
        q = db.query(modelo)
        for k, v in filtros.items():
            q = q.filter(getattr(modelo, k) == v)
        return q.count()
    finally:
        db.close()


semear()
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>2}. {descricao}")
    else:
        print(f"FALHA  {n:>2}. {descricao}")
        falhou.append(n)


print("PROVA SSO FASE 3 (Tareffas consome o bilhete)")

# 1. PROVA POSITIVA. Sem ela, uma rota que recusa tudo passa no resto.
r = entrar(bilhete("ativa@bps4.com.br"), ip="10.0.0.11")
checa(1, "bilhete válido de conta ativa entra e recebe token",
      r.status_code == 200 and r.json().get("access_token"))

# 2. O JWT do SSO tem a MESMA validade do login por senha. Entrar pelo Hub não
#    compra sessão mais longa.
# O cabeçalho de IP vai também no login por senha: desde a Fase 7 ele registra
# tentativa igual ao SSO, e sem o cabeçalho a linha nasceria com o IP da conexão
# do teste, que é o que o item 17 proíbe.
r_senha = cliente.post("/api/auth/login",
                       json={"email": "ativa@bps4.com.br", "senha": "senha-boa-123"},
                       headers={"X-Forwarded-For": "10.0.0.12, 172.18.0.5"})
exp_sso = jwt.decode(r.json()["access_token"], SECRET_KEY, algorithms=[ALGORITHM])["exp"]
exp_senha = jwt.decode(r_senha.json()["access_token"], SECRET_KEY,
                       algorithms=[ALGORITHM])["exp"]
checa(2, "JWT do SSO expira junto com o do login por senha (diferença < 5s)",
      r_senha.status_code == 200 and abs(exp_sso - exp_senha) < 5)

# 3. Login por e-mail e senha continua funcionando. O SSO é caminho adicional,
#    nunca substituto (tipo App Online Auth).
checa(3, "login por senha segue funcionando ao lado do SSO",
      r_senha.status_code == 200 and r_senha.json().get("access_token"))

# 4. Uso único: o MESMO bilhete não entra duas vezes.
b_repetido = bilhete("ativa@bps4.com.br")
primeira = entrar(b_repetido, ip="10.0.0.12")
segunda = entrar(b_repetido, ip="10.0.0.12")
checa(4, "mesmo bilhete usado duas vezes: só a primeira entra",
      primeira.status_code == 200 and segunda.status_code == 404)

# 5 a 8. Recusa uniforme. Inexistente, expirado, usado, assinatura errada e
#    conta em qualquer estado irregular saem pela MESMA porta.
casos = {
    "lixo": ("nao-e-bilhete-nenhum", "10.0.0.21"),
    "expirado": (bilhete("ativa@bps4.com.br", segundos=-1), "10.0.0.22"),
    "ja usado": (b_repetido, "10.0.0.23"),
    "chave errada": (bilhete("ativa@bps4.com.br", chave="chave-do-invasor"), "10.0.0.24"),
    "salt alheio": (bilhete("ativa@bps4.com.br", salt="outro-salt"), "10.0.0.25"),
    "sem cadastro": (bilhete("ninguem@exemplo.com"), "10.0.0.26"),
    "bloqueada": (bilhete("bloqueada@bps4.com.br"), "10.0.0.27"),
    "inativa": (bilhete("inativa@bps4.com.br"), "10.0.0.28"),
    "convite pendente": (bilhete("pendente@bps4.com.br"), "10.0.0.29"),
}
respostas = {nome: entrar(b, ip=ip) for nome, (b, ip) in casos.items()}

checa(5, "todas as recusas devolvem 404, nunca 403",
      all(r.status_code == 404 for r in respostas.values()))
checa(6, "todas as recusas devolvem o MESMO corpo, sem dizer o motivo",
      len({r.text for r in respostas.values()}) == 1)
checa(7, "a mensagem não revela se o problema é o bilhete ou a conta",
      all(p not in respostas["sem cadastro"].text.lower()
          for p in ("cadastr", "bloquead", "inativ", "expirad", "usado")))
checa(8, "conta bloqueada, inativa e com convite pendente são barradas",
      all(respostas[k].status_code == 404
          for k in ("bloqueada", "inativa", "convite pendente")))

# 9. Tamanho recusado ANTES de consultar o banco.
_queries["n"] = 0
r = entrar("A" * (sso_mod.TAMANHO_MAXIMO + 1), ip="10.0.0.31")
checa(9, "bilhete acima do teto é recusado sem nenhuma query no banco",
      r.status_code == 404 and _queries["n"] == 0)

# 10. O jti é marcado como usado ANTES de o token existir. A prova é uma entrada
#     que MARCOU e não emitiu nada: o e-mail não tem cadastro aqui.
b_orfao = bilhete("ninguem-mesmo@exemplo.com", jti="jti-orfao")
r = entrar(b_orfao, ip="10.0.0.32")
checa(10, "jti fica gravado mesmo quando nenhuma sessão é emitida",
      r.status_code == 404 and contar(SSOBilheteUsado, jti="jti-orfao") == 1)

# 11. Corrida: o mesmo bilhete em duas requisições simultâneas.
b_corrida = bilhete("ativa@bps4.com.br", jti="jti-corrida")
porta = threading.Barrier(2)
saidas = []


def _disputa():
    porta.wait()
    saidas.append(entrar(b_corrida, ip="10.0.0.33").status_code)


t1, t2 = threading.Thread(target=_disputa), threading.Thread(target=_disputa)
t1.start(), t2.start(), t1.join(), t2.join()
checa(11, "duas requisições simultâneas com o mesmo bilhete: só UMA entra",
      sorted(saidas) == [200, 404] and contar(SSOBilheteUsado, jti="jti-corrida") == 1)

# 12 e 13. Toda tentativa vira linha, com sucesso e com falha.
ip_rastro = "10.0.0.41"
entrar(bilhete("ativa@bps4.com.br"), ip=ip_rastro)
entrar("lixo", ip=ip_rastro)
checa(12, "tentativa bem sucedida é registrada com o IP de quem entrou",
      contar(LoginTentativa, ip=ip_rastro, sucesso=True) == 1)
checa(13, "tentativa recusada também é registrada",
      contar(LoginTentativa, ip=ip_rastro, sucesso=False) >= 1)

# 14. Força bruta: o IP que erra em série para de ser atendido.
ip_bruto = "10.0.0.51"
for _ in range(rota_auth.MAX_TENTATIVAS):
    entrar("lixo-invalido", ip=ip_bruto)
r = entrar(bilhete("ativa@bps4.com.br"), ip=ip_bruto)
checa(14, f"depois de {rota_auth.MAX_TENTATIVAS} falhas o mesmo IP recebe 429",
      r.status_code == 429)

# 15. O limite é por IP: quem não errou nada continua entrando.
r = entrar(bilhete("ativa@bps4.com.br"), ip="10.0.0.52")
checa(15, "o bloqueio é do IP que errou, e não do sistema inteiro",
      r.status_code == 200)

# 16. O bilhete NUNCA entra em log nem em tabela.
db = SessionLocal()
try:
    rastros = [str(x.jti) for x in db.query(SSOBilheteUsado).all()]
    rastros += [f"{t.email}|{t.ip}" for t in db.query(LoginTentativa).all()]
finally:
    db.close()
checa(16, "nenhum valor de bilhete aparece nas tabelas de rastro",
      not any(b_repetido[:40] in linha for linha in rastros))

# 17. IP do cliente vem do X-Forwarded-For, e não do proxy.
checa(17, "o IP registrado é o do cliente, não o da conexão do proxy",
      contar(LoginTentativa, ip="10.0.0.11") >= 1
      and contar(LoginTentativa, ip="testclient") == 0)

# 18a. Cadeia de proxy: o IP vem do fim da lista, e não do começo. Quem forja
#      `X-Forwarded-For` para escapar do limite não consegue mover o alvo.
r = cliente.post("/api/auth/sso", json={"bilhete": bilhete("ativa@bps4.com.br")},
                 headers={"X-Forwarded-For": "1.2.3.4, 200.10.20.30, 172.18.0.5"})
checa("18a", "com cadeia de proxy, o IP contado é o do cliente real",
      r.status_code == 200 and contar(LoginTentativa, ip="200.10.20.30") == 1
      and contar(LoginTentativa, ip="1.2.3.4") == 0)

# 18b. E-mail com caixa diferente é a mesma pessoa.
db = SessionLocal()
try:
    db.add(Usuario(nome="Caixa Alta", email="Maiuscula@bps4.com.br", grupo="analista",
                   senha_hash=get_password_hash("x"), ativo=True))
    db.commit()
finally:
    db.close()
r = entrar(bilhete("maiuscula@bps4.com.br"), ip="10.0.0.81")
checa("18b", "e-mail cadastrado com maiúscula casa com o bilhete em minúscula",
      r.status_code == 200)

# 18c. Duas contas que só diferem por caixa tornam a identidade ambígua, e aí
#      ninguém entra: escolher uma seria escolher no escuro de quem é a sessão.
db = SessionLocal()
try:
    db.add(Usuario(nome="Sósia", email="maiuscula@bps4.com.br", grupo="analista",
                   senha_hash=get_password_hash("x"), ativo=True))
    db.commit()
finally:
    db.close()
r = entrar(bilhete("maiuscula@bps4.com.br"), ip="10.0.0.82")
checa("18c", "e-mail ambíguo (duas contas, só a caixa difere) é recusado",
      r.status_code == 404)

# 18d. Corpo sem o campo cai na MESMA recusa, e não num 422 que responderia
#      diferente das outras.
r = cliente.post("/api/auth/sso", json={}, headers={"X-Forwarded-For": "10.0.0.83"})
checa("18d", "corpo sem o campo bilhete devolve a recusa única, não 422",
      r.status_code == 404 and r.text == respostas["lixo"].text)

# 19. Limpeza do rastro vencido.
db = SessionLocal()
try:
    db.add(SSOBilheteUsado(
        jti="jti-antigo",
        usado_em=datetime.utcnow() - timedelta(days=rota_auth.RETENCAO_BILHETES_DIAS + 1),
    ))
    db.commit()
finally:
    db.close()
entrar(bilhete("ativa@bps4.com.br"), ip="10.0.0.61")
checa(19, "bilhete usado fora da retenção é apagado na próxima entrada",
      contar(SSOBilheteUsado, jti="jti-antigo") == 0)

# 20. Sem chave configurada, o SSO fica desligado e nem bilhete bom entra.
b_bom = bilhete("ativa@bps4.com.br")
sso_mod.SSO_SECRET = ""
r = entrar(b_bom, ip="10.0.0.71")
sso_mod.SSO_SECRET = CHAVE
checa(20, "com ZOARIA_SSO_SECRET vazia nada entra pelo SSO",
      r.status_code == 404)

# 21. E o login por senha continua de pé mesmo com o SSO desligado.
sso_mod.SSO_SECRET = ""
r = cliente.post("/api/auth/login",
                 json={"email": "ativa@bps4.com.br", "senha": "senha-boa-123"},
                 headers={"X-Forwarded-For": "10.0.0.13, 172.18.0.5"})
sso_mod.SSO_SECRET = CHAVE
checa(21, "SSO desligado não derruba o login por e-mail e senha",
      r.status_code == 200)

for arquivo in Path(_tmp).glob("*"):
    arquivo.unlink()
os.rmdir(_tmp)

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 25 checagens verdes")
