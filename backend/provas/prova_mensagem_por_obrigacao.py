"""Prova: mensagem ao cliente por obrigação, e e-mail da empresa que chega.

Pedido de 2026-10-28:
  (a) a obrigação ganha "Mensagem ao cliente". Preenchida, ela sai no WhatsApp
      e no e-mail no lugar de "Sua guia X está disponível."; vazia, a frase
      padrão continua. O resto (saudação, vencimento, link, assinatura) fica.
  (b) "o e-mail do cliente não está indo": a ficha da empresa com dois
      endereços ("a@x; b@y") virava UM destinatário inválido e o SMTP recusava.
      Cada endereço vira um destinatário, sem espaço sobrando.
  (c) a falha diz o motivo na resposta (a tela só escrevia "falhou").

    cd backend && ./venv/bin/python provas/prova_mensagem_por_obrigacao.py
"""
from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_mensagem_por_obrigacao_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("OPENAI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import Empresa, Obrigacao, StatusTarefa, Tarefa    # noqa: E402
from app.schemas import ObrigacaoCreate, ObrigacaoUpdate           # noqa: E402
from app.services import entrega_cliente                           # noqa: E402
from app.services.whatsapp import destinatarios_cliente            # noqa: E402
import app.main                                                    # noqa: E402,F401

Base.metadata.create_all(bind=engine)
falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


db = SessionLocal()
emp = Empresa(razao_social="Cliente Ficticio Ltda", cnpj="11222333000181", ativo=True,
              email=" financeiro@ficticio.com.br ; socio@ficticio.com.br, ",
              telefone="21999990000")
o = Obrigacao(nome="folha_arquivamento", mininome="Folha", sentido="entregar",
              meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12", ativa=True)
db.add_all([emp, o])
db.flush()
t = Tarefa(titulo="folha_arquivamento", empresa_id=emp.id, obrigacao_id=o.id,
           competencia="09/2026", data_vencimento=date(2026, 10, 6), status=StatusTarefa.PENDENTE)
db.add(t)
db.commit()
t = db.get(Tarefa, t.id)

# ------------------------------------------------------------ (a)
print("\n(a) mensagem ao cliente")
m = entrega_cliente.montar_mensagem(t, "Cliente Ficticio Ltda", "https://x/l")
checa(1, "sem mensagem, a frase padrao continua",
      "Sua guia Folha da competência setembro/2026 está disponível." in m["texto"], m["texto"])
o.mensagem_cliente = "Segue a folha de setembro para conferência.\nQualquer ajuste, <responda>."
db.commit()
m = entrega_cliente.montar_mensagem(db.get(Tarefa, t.id), "Cliente Ficticio Ltda", "https://x/l")
checa(2, "com mensagem, ela sai no texto (WhatsApp e e-mail)",
      "Segue a folha de setembro para conferência." in m["texto"], m["texto"])
checa(3, "e a frase padrao sai de cena", "está disponível" not in m["texto"]
      and "está disponível" not in m["html"], m["texto"])
checa(4, "saudacao, vencimento, link e assinatura ficam",
      all(x in m["texto"] for x in ("Olá, Cliente Ficticio Ltda.", "Vencimento: 06/10/2026.",
                                    "https://x/l", "BPS4 Contabilidade")), m["texto"])
checa(5, "no HTML a mensagem vai escapada e com quebra de linha",
      "Segue a folha de setembro" in m["html"] and "&lt;responda&gt;" in m["html"]
      and "<br>" in m["html"], m["html"][:400])
o.mensagem_cliente = "   "
db.commit()
m = entrega_cliente.montar_mensagem(db.get(Tarefa, t.id), "Cliente Ficticio Ltda", "https://x/l")
checa(6, "so espaco conta como vazio", "está disponível" in m["texto"], m["texto"])

# schema
checa(7, "cadastro e edicao aceitam o campo",
      ObrigacaoCreate(nome="x", setor_id=1, mensagem_cliente="oi").mensagem_cliente == "oi"
      and ObrigacaoUpdate(mensagem_cliente="oi").mensagem_cliente == "oi")
try:
    ObrigacaoUpdate(mensagem_cliente="x" * 2001)
    checa(8, "mais de 2000 caracteres e recusado", False)
except Exception:
    checa(8, "mais de 2000 caracteres e recusado", True)

# ------------------------------------------------------------ (b)
print("\n(b) e-mail da empresa")
d = destinatarios_cliente(db, db.get(Tarefa, t.id))
emails = [x["endereco"] for x in d if x["canal"] == "email"]
checa(9, "dois enderecos na ficha viram dois destinatarios, sem espaco",
      emails == ["financeiro@ficticio.com.br", "socio@ficticio.com.br"], emails)
checa(10, "o WhatsApp continua", any(x["canal"] == "whatsapp" for x in d), d)
emp_db = db.get(Empresa, emp.id)
emp_db.email = "unico@ficticio.com.br"
db.commit()
emails = [x["endereco"] for x in destinatarios_cliente(db, db.get(Tarefa, t.id)) if x["canal"] == "email"]
checa(11, "um endereco so segue igual", emails == ["unico@ficticio.com.br"], emails)
emp_db.email = "isto nao e email"
db.commit()
emails = [x["endereco"] for x in destinatarios_cliente(db, db.get(Tarefa, t.id)) if x["canal"] == "email"]
checa(12, "texto que nao e e-mail nao vira destinatario", emails == [], emails)
db.close()

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 12 checagens verdes")
