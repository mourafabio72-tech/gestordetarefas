"""Prova da Fase 7: fechar a porta da frente.

Três coisas que o Tareffas não tinha e que a nota de segurança da vault exige:
registro e limite de tentativa no login por e-mail e senha, CORS por lista
explícita em vez de "*", e cabeçalhos de segurança em toda resposta.

    cd backend && ./venv/bin/python provas/prova_seguranca_f7.py

Roda contra as rotas reais, num SQLite temporário, e não deixa arquivo para trás.
O item 1 é a prova positiva: sem ele, um login que recusasse tudo passaria em
todos os outros parecendo trancado.
"""

from __future__ import annotations  # produção é 3.12, a máquina local é 3.9

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_seg_f7_")
_banco = os.path.join(_tmp, "prova.db")

# Precisam existir ANTES de importar o app: `database.py` lê a URL no import.
os.environ["DATABASE_URL"] = f"sqlite:///{_banco}"
os.environ["SECRET_KEY"] = "chave-jwt-de-teste"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("CORS_ORIGINS", None)  # a prova mede a lista PADRÃO do código

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                      # noqa: E402

from app.database import Base, engine, SessionLocal            # noqa: E402
from app.models import Usuario, LoginTentativa                 # noqa: E402
from app.auth import get_password_hash                         # noqa: E402
from app.seguranca import (falhas_recentes, HEADERS_SEGURANCA,  # noqa: E402
                           MAX_TENTATIVAS)
from app.main import app, CORS_ORIGENS                         # noqa: E402

Base.metadata.create_all(bind=engine)
cliente = TestClient(app)

SENHA = "senha-boa-123"
ORIGEM_BOA = "https://gestordetarefas.zoaria.com.br"
ORIGEM_ESTRANHA = "https://site-de-outra-pessoa.example"


def semear():
    db = SessionLocal()
    try:
        for email, grupo in (("porta@bps4.com.br", "analista"),
                             ("outra@bps4.com.br", "analista"),
                             ("baixa@bps4.com.br", "admin")):
            if db.query(Usuario).filter(Usuario.email == email).first():
                continue
            db.add(Usuario(nome="Pessoa", email=email, grupo=grupo,
                           senha_hash=get_password_hash(SENHA), ativo=True))
        db.commit()
    finally:
        db.close()


def entrar(email, senha, ip):
    return cliente.post("/api/auth/login", json={"email": email, "senha": senha},
                        headers={"X-Forwarded-For": ip})


def contar_tentativas(**filtros):
    db = SessionLocal()
    try:
        q = db.query(LoginTentativa)
        for k, v in filtros.items():
            q = q.filter(getattr(LoginTentativa, k) == v)
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


print("PROVA SEGURANÇA FASE 7 (fechar a porta da frente)")

# 1. PROVA POSITIVA. Sem ela, um login que recusasse tudo passaria no resto.
r = entrar("porta@bps4.com.br", SENHA, "10.7.0.1")
checa(1, "login por e-mail e senha correto continua entrando",
      r.status_code == 200 and r.json().get("access_token"))

# 2. Nota da vault, regra 2: toda tentativa, sucesso ou falha, é registrada.
checa(2, "a entrada bem sucedida deixa linha com origem 'senha'",
      contar_tentativas(ip="10.7.0.1", origem="senha", sucesso=True) == 1)

# 3. A falha também. Antes desta fase não deixava nada.
entrar("porta@bps4.com.br", "senha-errada", "10.7.0.2")
checa(3, "a tentativa recusada também é registrada",
      contar_tentativas(ip="10.7.0.2", origem="senha", sucesso=False) == 1)

# 4. O limite. Cinco falhas e o mesmo IP para de ser atendido.
for _ in range(MAX_TENTATIVAS - 1):
    entrar("porta@bps4.com.br", "senha-errada", "10.7.0.2")
r = entrar("porta@bps4.com.br", "senha-errada", "10.7.0.2")
checa(4, f"depois de {MAX_TENTATIVAS} falhas o mesmo IP recebe 429",
      r.status_code == 429)

# 5. E o corte vem ANTES de conferir a senha: nem a senha certa passa. É o que
#    separa limite de verdade de "conta erro e ainda assim deixa tentar".
r = entrar("porta@bps4.com.br", SENHA, "10.7.0.2")
checa(5, "bloqueado, nem a senha certa entra até a janela passar",
      r.status_code == 429)

# 6. O bloqueio é de quem errou, e não do sistema inteiro.
r = entrar("outra@bps4.com.br", SENHA, "10.7.0.9")
checa(6, "outra pessoa, de outro IP, entra normalmente",
      r.status_code == 200)

# 6b. Regra 1 da nota: conta por e-mail OU IP, não só uma das duas. Quem
#     estourou o limite não escapa trocando de IP, que é o que a máquina do
#     atacante faz de graça. O preço disso está declarado no CHECKLIST: dá para
#     travar a conta de outra pessoa errando a senha dela cinco vezes.
r = entrar("porta@bps4.com.br", SENHA, "10.7.0.99")
checa("6b", "o e-mail que estourou o limite não entra nem de um IP novo",
      r.status_code == 429)

# 7. A contagem do SSO é independente da do login por senha: são credenciais
#    diferentes, e quem errou a senha não perde o caminho do card do Hub.
db = SessionLocal()
try:
    n_sso = falhas_recentes(db, "porta@bps4.com.br", "10.7.0.2", origem="sso")
finally:
    db.close()
checa(7, "as falhas do login por senha não contam no limite do SSO", n_sso == 0)

# 8. A mensagem do 429 não conta quem existe: diz só que houve tentativa demais.
corpo = r.json().get("detail", "") if r.status_code == 429 else ""
r429 = entrar("nao-existe@bps4.com.br", "qualquer", "10.7.0.2")
checa(8, "e-mail inexistente do IP bloqueado recebe a MESMA resposta 429",
      r429.status_code == 429 and r429.json().get("detail") == entrar(
          "porta@bps4.com.br", SENHA, "10.7.0.2").json().get("detail"))

# --- Cabeçalhos de segurança -------------------------------------------------

esperados = list(HEADERS_SEGURANCA)
r = cliente.get("/health")
faltando = [h for h in esperados if h not in r.headers]
checa(9, f"resposta comum leva os {len(esperados)} cabeçalhos de segurança",
      r.status_code == 200 and not faltando)

# 10. Inclusive a resposta de erro, que é onde header costuma sumir.
r = cliente.get("/api/rota-que-nao-existe")
faltando = [h for h in esperados if h not in r.headers]
checa(10, "resposta de erro também leva os cabeçalhos", r.status_code == 404 and not faltando)

# 11. A CSP da API é a de quem não carrega recurso nenhum.
r = cliente.get("/health")
checa(11, "a CSP da API é default-src 'none'",
      r.headers.get("Content-Security-Policy", "").startswith("default-src 'none'"))

# 12. Menos na documentação, que carrega script e estilo de CDN. Exceção
#     declarada: os outros cabeçalhos continuam saindo lá.
r = cliente.get("/openapi.json")
checa(12, "o OpenAPI fica fora da CSP e mantém os demais cabeçalhos",
      "Content-Security-Policy" not in r.headers
      and r.headers.get("X-Content-Type-Options") == "nosniff")

# --- CORS --------------------------------------------------------------------

checa(13, "a lista de origens não é o coringa",
      "*" not in CORS_ORIGENS and ORIGEM_BOA in CORS_ORIGENS)

# 13b. Variável definida e VAZIA, que é como o docker-compose entrega quando
#      ninguém a preenche, cai na lista padrão e não em lista nenhuma.
import importlib                                              # noqa: E402
os.environ["CORS_ORIGINS"] = ""
import app.main as _main                                      # noqa: E402
_recarregado = importlib.reload(_main).CORS_ORIGENS
os.environ.pop("CORS_ORIGINS", None)
importlib.reload(_main)
checa("13b", "CORS_ORIGINS vazia cai na lista padrão, e não em lista vazia",
      ORIGEM_BOA in _recarregado)

r = cliente.options("/api/auth/login", headers={
    "Origin": ORIGEM_ESTRANHA,
    "Access-Control-Request-Method": "POST",
})
checa(14, "preflight de origem não listada não recebe permissão",
      "access-control-allow-origin" not in {k.lower() for k in r.headers})

r = cliente.options("/api/auth/login", headers={
    "Origin": ORIGEM_BOA,
    "Access-Control-Request-Method": "POST",
})
checa(15, "preflight da origem de produção recebe permissão",
      r.headers.get("access-control-allow-origin") == ORIGEM_BOA)

# 16. Sem cookie no projeto, o CORS não precisa liberar credencial de navegador.
checa(16, "o CORS não anuncia allow-credentials",
      "access-control-allow-credentials" not in {k.lower() for k in r.headers})

# 17. O middleware fica na frente de TODA resposta, inclusive a que devolve
#     arquivo binário. Middleware que reembrulha resposta é lugar clássico de
#     download sair truncado, e isso não aparece em rota de JSON.
token = entrar("baixa@bps4.com.br", SENHA, "10.7.0.30").json()["access_token"]
r = cliente.get("/api/empresas/modelo-importacao",
                headers={"Authorization": f"Bearer {token}"})
checa(17, "download de planilha continua inteiro e leva os cabeçalhos",
      r.status_code == 200
      and r.content[:2] == b"PK"                      # assinatura de arquivo xlsx
      and int(r.headers["content-length"]) == len(r.content)
      and r.headers.get("X-Content-Type-Options") == "nosniff")

for arquivo in Path(_tmp).glob("*"):
    arquivo.unlink()
os.rmdir(_tmp)

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 19 checagens verdes")
