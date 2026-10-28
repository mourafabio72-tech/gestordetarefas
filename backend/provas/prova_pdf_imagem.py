"""Prova: guia em PDF de imagem (ISS da Prefeitura do Rio) é reconhecida.

Caso de 2026-10-27: a guia de ISS é uma foto dentro do PDF, sem texto nenhum.
O e-validador não achava nada. A prefeitura grava no AUTOR do arquivo a razão
social e o CNPJ, e no TÍTULO "Guia de Recolhimento de ISS". A competência só
está na imagem e no nome do arquivo ("... ISS 09.2026 VENC 06.10.2026.PDF").

Decisão do usuário: ler os dados do arquivo (autor, título, assunto) junto com
o texto, e, quando o documento não tem competência, tirá-la do nome do arquivo.
Competência que veio do nome NÃO conta como lida na guia: a guia de "entregar"
é anexada, mas não sai sozinha para o cliente.

    cd backend && ./venv/bin/python provas/prova_pdf_imagem.py
"""
from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import io
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_pdf_imagem_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("OPENAI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pypdf import PdfWriter                                        # noqa: E402
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


def pdf_sem_texto(autor="", titulo=""):
    w = PdfWriter()
    w.add_blank_page(width=595, height=842)
    w.add_metadata({"/Author": autor, "/Title": titulo, "/Creator": "Prefeitura Ficticia"})
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


GUIA = pdf_sem_texto("CLIENTE FICTICIO LTDA, CNPJ 11.222.333/0001-81, Inscrição no. 1.234.567-8",
                     "Guia de Recolhimento de ISS")

# ------------------------------------------------------------ leitura
print("\nleitura dos dados do arquivo")
texto = validador.ler_arquivo("guia.pdf", GUIA)
d = validador.extrair_dados(texto)
checa(1, "o CNPJ do autor do arquivo e lido", d["cnpj"] == "11222333000181", (d["cnpj"], texto[:120]))
checa(2, "o titulo entra no texto (para casar a obrigacao)", "Guia de Recolhimento de ISS" in texto, texto[:120])
checa(3, "PDF sem dados no arquivo continua sem CNPJ", validador.extrair_dados(
    validador.ler_arquivo("x.pdf", pdf_sem_texto()))["cnpj"] is None)

# ------------------------------------------------------------ competencia pelo nome
print("\ncompetencia pelo nome do arquivo")
cn = validador.competencia_do_nome
checa(4, "'... ISS 09.2026 VENC 06.10.2026.PDF' da 09/2026",
      cn("4X GUIA ISS 09.2026 VENC 06.10.2026.PDF") == "09/2026", cn("4X GUIA ISS 09.2026 VENC 06.10.2026.PDF"))
checa(5, "data de vencimento antes da competencia nao engana",
      cn("GUIA VENC 06.10.2026 ISS 09.2026.pdf") == "09/2026", cn("GUIA VENC 06.10.2026 ISS 09.2026.pdf"))
checa(6, "'09-2026' e '09_2026' tambem", cn("iss 09-2026.pdf") == "09/2026" and cn("iss_09_2026.pdf") == "09/2026",
      (cn("iss 09-2026.pdf"), cn("iss_09_2026.pdf")))
checa(7, "nome sem competencia devolve None", cn("guia iss.pdf") is None and cn("venc 06.10.2026.pdf") is None,
      (cn("guia iss.pdf"), cn("venc 06.10.2026.pdf")))

# ------------------------------------------------------------ processar
print("\nprocessar de ponta a ponta")
db = SessionLocal()
emp = Empresa(razao_social="Cliente Ficticio Ltda", cnpj="11222333000181", ativo=True)
o = Obrigacao(nome="guia_iss", identificadores="Guia de Recolhimento de ISS", sentido="entregar",
              meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12", ativa=True)
db.add_all([emp, o])
db.flush()
t = Tarefa(titulo="guia_iss", empresa_id=emp.id, obrigacao_id=o.id, competencia="09/2026",
           status=StatusTarefa.PENDENTE)
db.add(t)
db.commit()
tid = t.id
r = validador.processar(db, "CLIENTE GUIA ISS 09.2026 VENC 06.10.2026.PDF", GUIA)
checa(8, "acha a tarefa 09/2026 e anexa a guia", r.get("tarefa_id") == tid and r.get("competencia") == "09/2026", r)
checa(9, "competencia do nome nao conta como lida: guia espera conferencia, nao sai sozinha",
      r.get("status") == "aguardando_conferencia", r.get("status"))
checa(17, "a mensagem diz que so a competencia faltou, e que veio do nome do arquivo",
      "competência" in (r.get("detalhe") or "") and "nome do arquivo" in (r.get("detalhe") or "")
      and "CNPJ e competência não foram lidos" not in (r.get("detalhe") or ""), r.get("detalhe"))
checa(10, "a resposta diz de onde veio a competencia",
      r.get("competencia_origem") == "nome do arquivo", r.get("competencia_origem"))
r = validador.processar(db, "guia iss sem data.pdf", GUIA)
checa(11, "sem competencia no documento nem no nome, erro claro",
      r.get("status") == "erro" and "ompet" in (r.get("detalhe") or ""), r)

# ------------------------------------------------------------ tela Modelos
print("\ntela Modelos (analisar para o repositorio)")
nome = "CLIENTE GUIA ISS 09.2026 VENC 06.10.2026.PDF"
a = validador.analisar_para_repositorio(db, nome, GUIA)
cands = [c["texto"] for c in a.get("candidatos", [])]
checa(12, "o titulo do arquivo vira sugestao de palavra-chave", "Guia de Recolhimento de ISS" in cands, cands)
checa(13, "a empresa e casada pelo CNPJ do autor", a.get("empresa_id") == emp.id, a.get("empresa_id"))
checa(14, "competencia de exemplo sai do nome do arquivo", a.get("competencia_exemplo") == "09/2026",
      a.get("competencia_exemplo"))
checa(15, "razao social sai limpa, sem o resto do autor",
      a.get("razao_social_extraida") == "CLIENTE FICTICIO LTDA", a.get("razao_social_extraida"))
m = validador.analisar_modelo(db, nome, GUIA)
checa(16, "analisar_modelo (tela Obrigacoes) tambem sugere o titulo e a competencia",
      "Guia de Recolhimento de ISS" in [c["texto"] for c in m["candidatos"]] and m["competencia"] == "09/2026", m)
db.close()

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 17 checagens verdes")
