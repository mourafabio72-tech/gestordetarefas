"""Prova: o e-validador lê imagem (PNG, JPG e PDF escaneado) pelo OCR do servidor.

Decisão de 2026-10-28: tesseract no container, e não a IA, para a guia do
cliente não sair do servidor. Esta prova não depende do tesseract instalado
(a máquina de desenvolvimento não tem): o OCR é trocado por um dublê, e o
teste com o tesseract de verdade roda dentro do container (ver o LOG).

  (a) PNG e JPG vão para o OCR; PDF com texto NÃO passa pelo OCR;
  (b) PDF sem texto (página escaneada) passa pelo OCR, e os dados do arquivo
      continuam entrando no texto;
  (c) "04. COMPETÊNCIA" com o valor na linha de baixo (DARM do Rio) vira 09/2026,
      sem confundir com data de vencimento nem com o CNPJ;
  (d) sem tesseract, nada quebra: o OCR devolve "" e o fluxo segue;
  (e) de ponta a ponta: guia PNG com CNPJ e competência lidos sai pronta para
      envio (lida na guia, não no nome do arquivo).

    cd backend && ./venv/bin/python provas/prova_ocr.py
"""
from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import io
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_ocr_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("OPENAI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pypdf import PdfWriter                                        # noqa: E402
from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import Empresa, Obrigacao, StatusTarefa, Tarefa    # noqa: E402
from app.services import ocr, validador                            # noqa: E402
import app.main                                                    # noqa: E402,F401

Base.metadata.create_all(bind=engine)
falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


# Texto no formato do que o tesseract leu da guia real, com dados fictícios.
OCR_GUIA = """PREFEITURA DA CIDADE DO RIO DE JANEIRO 01. RECEITA
DOCUMENTO DE ARRECADAÇÃO DE RECEITAS MUNICIPAIS 02. INSCRIÇÃO DO CONTRIBUINTE
CLIENTE FICTICIO LTDA 06/10/2026
11. INFORMAÇÕES COMPLEMENTARES 04. COMPETÊNCIA
CNPJ: 11.222.333/0001-81 09/2026
Valor ISS = R$ 4.050,00
BANCOS E CASAS LOTÉRICAS NÃO ESTÃO AUTORIZADOS A RECEBER ESTE DOCUMENTO APÓS 09. VALOR TOTAL
06/10/2026
"""
chamadas = []
ocr_original = (ocr.ler_imagem, ocr.ler_imagens_do_pdf)
ocr.ler_imagem = lambda conteudo: (chamadas.append("imagem"), OCR_GUIA)[1]
ocr.ler_imagens_do_pdf = lambda reader: (chamadas.append("pdf"), OCR_GUIA)[1]


def pdf(texto_pagina=False, autor=""):
    w = PdfWriter()
    w.add_blank_page(width=595, height=842)
    if autor:
        w.add_metadata({"/Author": autor})
    buf = io.BytesIO()
    w.write(buf)
    dados = buf.getvalue()
    if texto_pagina:            # PDF "com texto": troca o leitor de página
        return dados
    return dados


# ------------------------------------------------------------ (a)
print("\n(a) quem vai para o OCR")
chamadas.clear()
t = validador.ler_arquivo("guia.PNG", b"\x89PNG-ficticio")
checa(1, "PNG vai para o OCR", chamadas == ["imagem"] and "COMPETÊNCIA" in t, chamadas)
chamadas.clear()
validador.ler_arquivo("foto.jpeg", b"jpg")
validador.ler_arquivo("foto.JPG", b"jpg")
checa(2, "JPG e JPEG tambem", chamadas == ["imagem", "imagem"], chamadas)
chamadas.clear()
import pypdf                                                       # noqa: E402
orig_extract = pypdf.PageObject.extract_text
pypdf.PageObject.extract_text = lambda self, *a, **k: "RECIBO DE ENTREGA texto de verdade"
validador.ler_arquivo("recibo.pdf", pdf())
pypdf.PageObject.extract_text = orig_extract
checa(3, "PDF com texto nao passa pelo OCR", chamadas == [], chamadas)

# ------------------------------------------------------------ (b)
print("\n(b) PDF escaneado")
chamadas.clear()
t = validador.ler_arquivo("guia.pdf", pdf(autor="CLIENTE FICTICIO LTDA, CNPJ 11.222.333/0001-81"))
checa(4, "PDF sem texto passa pelo OCR", chamadas == ["pdf"], chamadas)
checa(5, "e os dados do arquivo continuam no texto", "Autor do arquivo" in t, t[-120:])

# ------------------------------------------------------------ (c)
print("\n(c) competencia com o valor embaixo do rotulo")
d = validador.extrair_dados(OCR_GUIA)
checa(6, "'04. COMPETÊNCIA' + linha de baixo da 09/2026", d["competencia"] == "09/2026", d)
checa(7, "o CNPJ do OCR e lido", d["cnpj"] == "11222333000181", d["cnpj"])
d = validador.extrair_dados("COMPETÊNCIA\nVencimento 06/10/2026")
checa(8, "data de vencimento depois do rotulo nao vira competencia", d["competencia"] is None, d)
d = validador.extrair_dados("Competência: 03/2026")
checa(9, "'Competência: 03/2026' na mesma linha", d["competencia"] == "03/2026", d)

# ------------------------------------------------------------ (d)
print("\n(d) sem tesseract")
ocr.ler_imagem, ocr.ler_imagens_do_pdf = ocr_original
orig_which = ocr.shutil.which
ocr.shutil.which = lambda nome: None
checa(10, "sem o programa, OCR devolve vazio e nao quebra",
      ocr.ler_imagem(b"qualquer") == "" and validador.ler_arquivo("x.png", b"x") == "")
ocr.shutil.which = orig_which
checa(11, "imagem que nao e imagem devolve vazio", ocr.ler_imagem(b"isto nao e imagem") == "")
ocr.ler_imagem = lambda conteudo: OCR_GUIA

# ------------------------------------------------------------ (e)
print("\n(e) de ponta a ponta")
db = SessionLocal()
emp = Empresa(razao_social="Cliente Ficticio Ltda", cnpj="11222333000181", ativo=True)
o = Obrigacao(nome="guia_iss", identificadores="DOCUMENTO DE ARRECADAÇÃO DE RECEITAS MUNICIPAIS",
              sentido="entregar", meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12", ativa=True)
db.add_all([emp, o])
db.flush()
tar = Tarefa(titulo="guia_iss", empresa_id=emp.id, obrigacao_id=o.id, competencia="09/2026",
             status=StatusTarefa.PENDENTE)
db.add(tar)
db.commit()
r = validador.processar(db, "foto da guia.png", b"\x89PNG-ficticio")
checa(12, "guia PNG acha a tarefa 09/2026", r.get("tarefa_id") == tar.id, r)
checa(13, "competencia lida na guia, nao no nome", r.get("competencia_origem") == "documento", r)
checa(14, "CNPJ e competencia lidos na guia: pronta para envio, sem esperar conferencia",
      r.get("status") == "pronta_para_envio", r.get("status"))
db.close()

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 14 checagens verdes")
