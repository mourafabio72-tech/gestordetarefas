"""Prova: a tela do MIT não se confunde com a DCTFWeb, e "Já baixada" diz qual.

Caso de 2026-11-03: o comprovante do MIT é um print do portal. A palavra MIT não
aparece nele, e o único nome de obrigação é o botão "Acessar DCTFWeb". O resultado
dizia "Tarefa já estava baixada" sem dizer de qual obrigação, e a competência
"PERÍODO DA APURAÇÃO: Setembro/2026" ("da", e não "de") só saía pela IA.

  (a) "Período da apuração" é lido, como "Período de apuração";
  (b) "Já baixada" e "Baixada" nomeiam a obrigação;
  (c) a chave "Acessar DCTFWeb" no MIT ganha da "DCTFWeb", e baixa a tarefa certa.

Texto no formato do que o OCR leu do print, com dados fictícios.

    cd backend && ./venv/bin/python provas/prova_mit_dctfweb.py
"""
from __future__ import annotations  # producao e 3.11, a maquina local e 3.9

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_mit_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("OPENAI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import Empresa, Obrigacao, StatusTarefa, Tarefa    # noqa: E402
from app.services import validador                                 # noqa: E402
import app.main                                                    # noqa: E402,F401

Base.metadata.create_all(bind=engine)
falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


TELA = """CLIENTE FICTICIO LTDA - CNPJ: 11.222.333/0001-81 | PERÍODO DA APURAÇÃO: Setembro/2026

Fluxo da Apuração
Iniciada em 22/10/2026
Encerrada em 22/10/2026
Acessar DCTFWeb
Resumo dos Débitos Apurados
Total Apurado:
R$ 98.373,35
"""
print("\n(a) competencia")
d = validador.extrair_dados(TELA)
checa(1, "'PERIODO DA APURACAO: Setembro/2026' da 09/2026, sem as datas da tela",
      d["competencia"] == "09/2026", d["competencia"])
c = validador.extrair_dados("Período de Apuração: Agosto/2026")["competencia"]
checa(2, "'Periodo de Apuracao' segue igual", c == "08/2026", c)

db = SessionLocal()
emp = Empresa(razao_social="Cliente Ficticio Ltda", cnpj="11222333000181", ativo=True)
dctf = Obrigacao(nome="dctfweb", mininome="DCTFWeb", identificadores="DCTFWeb", sentido="receber",
                 meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12", ativa=True)
db.add_all([emp, dctf])
db.flush()
t_dctf = Tarefa(titulo="dctfweb", empresa_id=emp.id, obrigacao_id=dctf.id, competencia="09/2026",
                status=StatusTarefa.CONCLUIDA, data_conclusao=datetime(2026, 11, 3, 13, 52))
db.add(t_dctf)
db.commit()
validador.ler_arquivo = lambda nome, conteudo: TELA

print("\n(b) mensagem")
r = validador.processar(db, "mit.pdf", b"%PDF-ficticio")
checa(3, "o caso de hoje: cai na DCTFWeb, e a mensagem diz qual tarefa estava baixada",
      r.get("status") == "ja_baixada" and "DCTFWeb" in (r.get("detalhe") or "")
      and "03/11/2026" in (r.get("detalhe") or ""), r.get("detalhe"))

print("\n(c) chave do MIT")
mit = Obrigacao(nome="entrega_mit", identificadores="Acessar DCTFWeb", sentido="receber",
                meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12", ativa=True)
db.add(mit)
db.flush()
t_mit = Tarefa(titulo="entrega_mit", empresa_id=emp.id, obrigacao_id=mit.id, competencia="09/2026",
               status=StatusTarefa.PENDENTE)
db.add(t_mit)
db.commit()
r = validador.processar(db, "mit.pdf", b"%PDF-ficticio")
checa(4, "com a chave no MIT, a tela baixa a tarefa do MIT",
      r.get("status") == "baixada" and r.get("tarefa_id") == t_mit.id, r)
checa(5, "e a mensagem da baixa nomeia a obrigacao", "entrega_mit" in (r.get("detalhe") or ""), r.get("detalhe"))
validador.ler_arquivo = lambda nome, conteudo: "Recibo de entrega DCTFWeb\nCNPJ: 11.222.333/0001-81\nCompetência: 10/2026"
db.add(Tarefa(titulo="dctfweb", empresa_id=emp.id, obrigacao_id=dctf.id, competencia="10/2026",
              status=StatusTarefa.PENDENTE))
db.commit()
r = validador.processar(db, "recibo.pdf", b"%PDF-ficticio")
checa(6, "o recibo da DCTFWeb continua indo para a DCTFWeb",
      r.get("status") == "baixada" and r.get("obrigacao") == "dctfweb", r)
db.close()

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 6 checagens verdes")
