"""
prova_link_so_receber.py: o link público de envio de comprovante é só de "receber".

O link `/enviar/<token>` abre uma porta de upload SEM senha. Ele faz sentido
quando o cliente tem de mandar um comprovante. Até 2026-09-15 saía para toda
tarefa, olhando nada: guia a entregar, trabalho interno e, com o sentido novo,
obrigação que o escritório transmite ao órgão.

A trava tem três pontos no servidor, e os três são irmãos:
  (a) a régua de alerta, que põe o link na mensagem;
  (b) a rota `GET /api/tarefas/{id}/link-envio`, que CRIA o token;
  (c) as rotas públicas `/api/publico/tarefa/{token}`, que aceitam o upload.
Travar só um deixaria os outros abertos.

E há um caminho que NÃO pode travar: `/api/publico/baixar/{token}`, por onde o
cliente pega a guia do "entregar". Os itens de não-regressão medem isso antes.

    python provas/prova_link_so_receber.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-link-receber-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from fastapi.testclient import TestClient                      # noqa: E402
from app.database import Base, engine, SessionLocal            # noqa: E402
from app.models import Usuario, Empresa, Setor, Tarefa, Obrigacao, StatusTarefa  # noqa: E402
from app.auth import get_password_hash, create_access_token    # noqa: E402
from app.services import whatsapp as zap                       # noqa: E402
from app.services import upload as up                          # noqa: E402
from app.services import config as cfgmod                      # noqa: E402
from app.main import app                                       # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
TOTAL = 17
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


# Dublês: a régua não fala com a API do Zap.
async def _vazio(cfg):
    return []
zap.contatos_zap = _vazio
zap.usuarios_zap = _vazio

cab = {"Authorization": "Bearer " + create_access_token(data={"sub": "admin@x.com"})}
agora = datetime.now()

db = SessionLocal()
db.add(Usuario(nome="Admin", email="admin@x.com", grupo="admin", ativo=True,
               senha_hash=get_password_hash("x")))
emp, setor = Empresa(razao_social="Cliente", cnpj="1"), Setor(nome="Fiscal")
db.add_all([emp, setor])
db.commit()

ids = {}
for sentido in ("receber", "entregar", "interna", "transmitir", None):
    rotulo = sentido or "avulsa"
    pessoa = Usuario(nome=f"Resp {rotulo}", email=f"{rotulo}@x.com", grupo="analista", ativo=True,
                     senha_hash=get_password_hash("x"))
    db.add(pessoa)
    ob = None
    if sentido:
        ob = Obrigacao(nome=f"obrig {rotulo}", sentido=sentido, ativa=True)
        db.add(ob)
    db.commit()
    t = Tarefa(titulo=f"tarefa {rotulo}", empresa_id=emp.id, setor_id=setor.id,
               obrigacao_id=ob.id if ob else None, status=StatusTarefa.PENDENTE,
               competencia="08/2026", data_prazo=agora, data_vencimento=agora)
    db.add(t)
    db.commit()
    t.responsaveis.append(pessoa)
    db.commit()
    ids[rotulo] = t.id
db.close()


def token_de(rotulo):
    s = SessionLocal()
    try:
        return s.query(Tarefa.upload_token).filter(Tarefa.id == ids[rotulo]).scalar()
    finally:
        s.close()


# --------------------------------------------------------------- (a) a régua
print("\n(a) A régua de alerta, em ensaio")
s = SessionLocal()
cfg = cfgmod.carregar(s)
try:
    dias_antes = int(cfg.get("alert_dias_antes") or 3)
except (TypeError, ValueError):
    dias_antes = 3
faixa = zap.faixa_da_tarefa(0, dias_antes)
res = asyncio.run(zap.check_and_send_alerts(s, faixa=faixa, ensaio=True))
s.close()
texto_de = {}
for m in res.get("mensagens", []):
    texto_de[m.get("nome")] = m.get("mensagem") or ""
com_link = {r for r in ("receber", "entregar", "interna", "transmitir", "avulsa")
            if "/enviar/" in texto_de.get(f"Resp {r}", "")}
checa(1, f"cenário: a régua montou mensagem para os cinco (achados: {sorted(texto_de)})",
      len([n for n in texto_de if n.startswith("Resp ")]) == 5)
checa(2, f"receber recebe link (com link: {sorted(com_link)})", "receber" in com_link)
checa(3, "entregar, interna e transmitir NÃO recebem link",
      not ({"entregar", "interna", "transmitir"} & com_link))
checa(4, "e a régua não criou token de upload para elas",
      not any(token_de(r) for r in ("entregar", "interna", "transmitir")))
checa(5, "tarefa avulsa, sem obrigação, é receber e continua recebendo link", "avulsa" in com_link)

# ---------------------------------------------------------- (b) link-envio
print("\n(b) GET /api/tarefas/{id}/link-envio")
r = client.get(f"/api/tarefas/{ids['receber']}/link-envio", headers=cab)
checa(6, "receber devolve o link", r.status_code == 200 and "/enviar/" in (r.json().get("link") or ""))
recusas = {rot: client.get(f"/api/tarefas/{ids[rot]}/link-envio", headers=cab).status_code
           for rot in ("entregar", "interna", "transmitir")}
checa(7, f"entregar, interna e transmitir devolvem 404 ({recusas})",
      set(recusas.values()) == {404})
# Os tokens de entregar/interna/transmitir só poderiam vir da rota: a régua do
# item 4 não cria mais. Se a rota recusar e ainda assim gravar, este pega.
checa(8, "a recusa não cria token de upload", not any(token_de(r) for r in ("entregar", "interna", "transmitir")))

# ------------------------------------------------------- (c) rotas públicas
print("\n(c) /api/publico/tarefa/{token} com token de tarefa fora de receber")
db = SessionLocal()
velho = {}
for rot in ("entregar", "transmitir"):
    t = db.query(Tarefa).get(ids[rot])
    t.upload_token = f"token-antigo-{rot}-0123456789abcdef"
    velho[rot] = t.upload_token
db.commit()
db.close()

inexistente = client.get("/api/publico/tarefa/nao-existe-esse-token")
arquivo = {"arquivo": ("comprovante.pdf", b"%PDF-1.4 prova", "application/pdf")}
inexistente_post = client.post("/api/publico/tarefa/nao-existe-esse-token", files=arquivo)
ctx = [client.get(f"/api/publico/tarefa/{velho[r]}") for r in velho]
env = [client.post(f"/api/publico/tarefa/{velho[r]}", files=arquivo) for r in velho]
checa(9, f"GET do contexto recusa com 404 ({[x.status_code for x in ctx]})",
      all(x.status_code == 404 for x in ctx))
checa(10, "e com o MESMO corpo de token inexistente, sem dizer que a tarefa existe",
      all(x.json() == inexistente.json() for x in ctx))
checa(11, f"POST do upload recusa com 404 e o mesmo corpo ({[x.status_code for x in env]})",
      all(x.status_code == 404 and x.json() == inexistente_post.json() for x in env))
s = SessionLocal()
anexos = [s.query(Tarefa.anexo_nome).filter(Tarefa.id == ids[r]).scalar() for r in velho]
s.close()
checa(12, "e nenhum arquivo foi anexado a elas", not any(anexos))

# --------------------------------------------------------- (d) não-regressão
print("\n(d) Não-regressão, medida antes")
tok_receber = token_de("receber")
checa(13, "receber: o contexto público abre", client.get(f"/api/publico/tarefa/{tok_receber}").status_code == 200)
r = client.post(f"/api/publico/tarefa/{tok_receber}", files=arquivo)
checa(14, f"receber: o upload do comprovante é aceito ({r.status_code})", r.status_code == 200)

db = SessionLocal()
t = db.query(Tarefa).get(ids["entregar"])
t.saida_nome = up.salvar_saida(t.id, "guia.pdf", b"%PDF-1.4 guia")
t.saida_token = "token-saida-entregar-0123456789abcdef"
db.commit()
db.close()
r = client.get("/api/publico/baixar/token-saida-entregar-0123456789abcdef",
               headers={"user-agent": "Mozilla/5.0 Chrome/120"})
checa(15, f"entregar: o cliente continua baixando a guia pelo link ({r.status_code})", r.status_code == 200)
checa(16, "token inexistente no download continua 404",
      client.get("/api/publico/baixar/nao-existe").status_code == 404)

# Achado do verificador funcional: o item 5 cobre só a tarefa SEM obrigação.
# Obrigação antiga com sentido nulo ou vazio gravado é outro caminho da mesma
# propriedade, e é o legado real de produção.
db = SessionLocal()
# Os objetos da primeira sessão morreram no close: relê os ids.
emp = db.query(Empresa).filter_by(cnpj="1").one()
setor = db.query(Setor).filter_by(nome="Fiscal").one()
legadas = {}
for rot, valor in (("nula", None), ("vazia", "")):
    ob = Obrigacao(nome=f"legada {rot}", sentido=valor, ativa=True)
    db.add(ob)
    db.commit()
    t = Tarefa(titulo=f"tarefa legada {rot}", empresa_id=emp.id, setor_id=setor.id,
               obrigacao_id=ob.id, status=StatusTarefa.PENDENTE, competencia="08/2026",
               data_prazo=agora, data_vencimento=agora)
    db.add(t)
    db.commit()
    legadas[rot] = t.id
db.close()
st = {rot: client.get(f"/api/tarefas/{tid}/link-envio", headers=cab).status_code
      for rot, tid in legadas.items()}
checa(17, f"obrigação legada com sentido nulo ou vazio continua gerando link ({st})",
      set(st.values()) == {200})

import shutil                                                  # noqa: E402
shutil.rmtree(_tmp, ignore_errors=True)

print()
if falhou:
    print(f"PROVA FALHOU nos itens: {sorted(set(falhou))}")
    sys.exit(1)
print(f"PROVA OK: {TOTAL} checagens verdes")
