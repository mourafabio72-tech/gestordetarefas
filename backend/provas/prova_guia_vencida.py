"""
prova_guia_vencida.py: guia vencida não sai sozinha para o cliente.

Decisão do Fábio em 2026-11-05: o e-validador mandava ao cliente qualquer guia
conferida, mesmo vencida (o DAS da Rio Bravo, vencido em 20/10, sairia ao ser
reprocessado). Agora a guia vencida fica anexada em "aguardando conferência".

O vencimento vem, nesta ordem: o que está escrito na guia ("Pagar este
documento até", "Data de vencimento"; a data mais nova, porque a guia
recalculada traz o prazo novo), o "VENC dd.mm.aaaa" do nome do arquivo, e só
então o vencimento da tarefa. Vencer HOJE ainda sai.

WhatsApp e e-mail são dublês. O "hoje" é fixo em 05/11/2026.

    python provas/prova_guia_vencida.py
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-vencida-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from fastapi.testclient import TestClient                              # noqa: E402
from app.database import Base, engine, SessionLocal                    # noqa: E402
from app.models import Usuario, Obrigacao, Empresa, Tarefa, StatusTarefa  # noqa: E402
from app.auth import get_password_hash, create_access_token            # noqa: E402
from app.main import app                                               # noqa: E402
from app.services import validador, whatsapp, email as email_mod       # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app, raise_server_exceptions=False)
TOTAL = 10
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


SAIU = []


async def zap_falso(phone, message, cfg, user_id=None):
    SAIU.append(("whatsapp", phone))
    return {"success": True}


def email_falso(to, subject, body, cfg, anexos=None, html=None, imagens=None):
    SAIU.append(("email", to))
    return {"success": True}


async def carregar_zap_falso(cfg):
    return {}

whatsapp.send_whatsapp_message = zap_falso
whatsapp.carregar_zap = carregar_zap_falso
email_mod.send_email = email_falso
validador._hoje = lambda: date(2026, 11, 5)

cab = {"Authorization": "Bearer " + create_access_token(data={"sub": "admin@x.com"})}
db = SessionLocal()
db.add(Usuario(nome="Admin", email="admin@x.com", grupo="admin", ativo=True,
               senha_hash=get_password_hash("x")))
emp = Empresa(razao_social="Cliente Com Contato", cnpj="11.222.333/0001-81",
              email="financeiro@cliente.com", telefone="21999998888")
o = Obrigacao(nome="das_teste", sentido="entregar", identificadores="GUIA GAMA")
db.add_all([emp, o])
db.commit()


def nova(comp, venc=None):
    t = Tarefa(titulo=o.nome, empresa_id=emp.id, obrigacao_id=o.id, competencia=comp,
               status=StatusTarefa.PENDENTE, data_vencimento=venc)
    db.add(t)
    db.commit()
    return t.id


CNPJ = "CNPJ 11.222.333/0001-81"
CASOS = {
    # nome do arquivo: (competência, vencimento da tarefa, texto da guia)
    "das_01.pdf": ("01/2026", None, f"GUIA GAMA {CNPJ} Período de Apuração 01/2026 "
                                    "Pagar este documento até 20/10/2026"),
    "das_02.pdf": ("02/2026", None, f"GUIA GAMA {CNPJ} Período de Apuração 02/2026 "
                                    "Data de Vencimento 05/11/2026"),
    "das_03.pdf": ("03/2026", None, f"GUIA GAMA {CNPJ} Período de Apuração 03/2026 "
                                    "Data de Vencimento 20/10/2026 Pagar este documento até 30/11/2026"),
    "das_04.pdf": ("04/2026", datetime(2026, 10, 20), f"GUIA GAMA {CNPJ} Período de Apuração 04/2026"),
    "das_05.pdf": ("05/2026", datetime(2026, 12, 20), f"GUIA GAMA {CNPJ} Período de Apuração 05/2026"),
    "das_06 VENC 06.10.2026.pdf": ("06/2026", datetime(2026, 12, 20),
                                   f"GUIA GAMA {CNPJ} Período de Apuração 06/2026"),
    "das_07.pdf": ("07/2026", datetime(2026, 10, 20), f"GUIA GAMA {CNPJ} Período de Apuração 07/2026 "
                                                      "Vencimento: 30/11/2026"),
}
TAREFA = {nome: nova(comp, venc) for nome, (comp, venc, _) in CASOS.items()}
validador.ler_arquivo = lambda nome, conteudo: CASOS[nome][2]


def subir(nome):
    with redirect_stdout(io.StringIO()):
        r = client.post("/api/evalidador/processar", headers=cab,
                        files=[("arquivos", (nome, io.BytesIO(b"%PDF x"), "application/pdf"))])
    return (r.json().get("resultados") or [{}])[0] if r.status_code == 200 else {}


def status(tid):
    s = SessionLocal()
    try:
        return s.get(Tarefa, tid).status
    finally:
        s.close()


def segura(n, nome, trecho):
    SAIU.clear()
    res = subir(nome)
    t = TAREFA[nome]
    checa(n, f"{nome}: {res.get('status')}, saiu {SAIU}, {res.get('detalhe')}",
          res.get("status") == "aguardando_conferencia" and SAIU == []
          and status(t) == StatusTarefa.PENDENTE and trecho in (res.get("detalhe") or ""))


def sai(n, nome):
    SAIU.clear()
    res = subir(nome)
    checa(n, f"{nome}: {res.get('status')}, saiu {SAIU}",
          res.get("status") == "enviada" and len(SAIU) == 2
          and status(TAREFA[nome]) == StatusTarefa.CONCLUIDA)


segura(1, "das_01.pdf", "vencida em 20/10/2026")
sai(2, "das_02.pdf")                                   # vence hoje: ainda sai
sai(3, "das_03.pdf")                                   # recalculada: vale a data mais nova
segura(4, "das_04.pdf", "vencida em 20/10/2026")       # sem data na guia: vale a da tarefa
sai(5, "das_05.pdf")                                   # tarefa ainda no prazo
segura(6, "das_06 VENC 06.10.2026.pdf", "06/10/2026")  # nome do arquivo vence a tarefa
sai(7, "das_07.pdf")                                   # guia vence a tarefa

# 8. O detalhe diz de onde veio o vencimento.
SAIU.clear()
s = SessionLocal()
t1 = s.get(Tarefa, TAREFA["das_01.pdf"])
checa(8, "a guia vencida ficou anexada à tarefa", bool(t1.saida_nome))
s.close()

# 9. O "Enviar ao cliente" da tela continua liberado: quem conferiu decide.
SAIU.clear()
r = client.post(f"/api/tarefas/{TAREFA['das_01.pdf']}/enviar-cliente", headers=cab)
checa(9, f"Enviar ao cliente manual: {r.status_code}, saiu {SAIU}",
      r.status_code == 200 and len(SAIU) == 2 and status(TAREFA["das_01.pdf"]) == StatusTarefa.CONCLUIDA)

# 10. Unidade: datas soltas que não são vencimento não contam.
v = validador.vencimento_lido("Período de Apuração 30/09/2026 Data de emissão 01/10/2026")
checa(10, f"sem rótulo de vencimento, nada lido: {v}", v is None)

db.close()
print()
if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print(f"PROVA OK: {TOTAL} checagens verdes")
