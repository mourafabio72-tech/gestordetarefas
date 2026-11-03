"""Prova: o OCR lê a PÁGINA do PDF desenhada, e não só as imagens embutidas.

Caso de 2026-11-03, DAS salvo pelo "Microsoft Print to PDF": o texto da guia sai
como traços vetoriais (15 mil curvas, nenhuma fonte), e as duas imagens do
arquivo são o logo e o QR Code. O OCR lia só as imagens e respondia "CNPJ não
encontrado". O tesseract aqui é dublê; a renderização é de verdade.

  (a) PDF sem texto: a página vai para o OCR como imagem, com os traços nela;
  (b) o lado maior respeita o limite, mesmo em página gigante;
  (c) no máximo MAX_PAGINAS_PDF páginas; sem tesseract ou com arquivo ruim, "";
  (d) PDF com texto continua sem passar pelo OCR;
  (e) no Print to PDF, autor e título são da impressora, e ficam de fora.

    cd backend && ./venv/bin/python provas/prova_ocr_pagina.py
"""
from __future__ import annotations  # producao e 3.11, a maquina local e 3.9

import io
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_ocr_pagina_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("OPENAI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image                                              # noqa: E402
from pypdf import PdfWriter                                        # noqa: E402
from pypdf.generic import DecodedStreamObject, NameObject          # noqa: E402
from app.services import ocr, validador                            # noqa: E402

falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


def pdf_com_traco(paginas=1, largura=595, altura=842, meta=None):
    """PDF sem fonte: só um retângulo preto desenhado, como o Print to PDF faz."""
    w = PdfWriter()
    for _ in range(paginas):
        p = w.add_blank_page(width=largura, height=altura)
        s = DecodedStreamObject()
        s.set_data(b"0 0 0 rg 100 100 300 200 re f")
        p[NameObject("/Contents")] = w._add_object(s)
    if meta:
        w.add_metadata(meta)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


IMAGENS = []
ocr.disponivel = lambda: True
ocr.ler_imagem = lambda conteudo: (IMAGENS.append(Image.open(io.BytesIO(conteudo))), "CNPJ lido")[1]

# ------------------------------------------------------------ (a)
print("\n(a) pagina desenhada")
t = validador.ler_arquivo("guia.pdf", pdf_com_traco())
checa(1, "a pagina sem texto vai para o OCR", len(IMAGENS) == 1 and "CNPJ lido" in t, (len(IMAGENS), t))
img = IMAGENS[0].convert("L") if IMAGENS else None
checa(2, "e a imagem traz o traco desenhado (tem preto e tem branco)",
      img is not None and img.getextrema()[0] < 50 and img.getextrema()[1] > 200,
      img and img.getextrema())
checa(3, "A4 sai perto de 300 dpi, para o OCR ler texto pequeno",
      img is not None and 2400 <= img.width <= 2500, img and img.size)

# ------------------------------------------------------------ (b) e (c)
print("\n(b) e (c) limites")
IMAGENS.clear()
ocr.ler_paginas_do_pdf(pdf_com_traco(largura=14000, altura=14000))
checa(4, "pagina gigante respeita o lado maximo",
      IMAGENS and max(IMAGENS[0].size) <= ocr.MAX_LADO, IMAGENS and IMAGENS[0].size)
IMAGENS.clear()
ocr.ler_paginas_do_pdf(pdf_com_traco(paginas=ocr.MAX_PAGINAS_PDF + 3))
checa(5, "no maximo MAX_PAGINAS_PDF paginas", len(IMAGENS) == ocr.MAX_PAGINAS_PDF, len(IMAGENS))
IMAGENS.clear()
checa(6, "arquivo que nao e PDF devolve vazio", ocr.ler_paginas_do_pdf(b"isto nao e pdf") == "")
ocr.disponivel = lambda: False
checa(7, "sem tesseract devolve vazio, sem renderizar",
      ocr.ler_paginas_do_pdf(pdf_com_traco()) == "" and not IMAGENS)
ocr.disponivel = lambda: True

# ------------------------------------------------------------ (d)
print("\n(d) PDF com texto")
import pypdf                                                       # noqa: E402
orig = pypdf.PageObject.extract_text
pypdf.PageObject.extract_text = lambda self, *a, **k: "RECIBO de verdade"
IMAGENS.clear()
validador.ler_arquivo("recibo.pdf", pdf_com_traco())
pypdf.PageObject.extract_text = orig
checa(8, "PDF com texto nao passa pelo OCR", not IMAGENS, len(IMAGENS))

# ------------------------------------------------------------ (e)
print("\n(e) dados do arquivo")
t = validador.ler_arquivo("g.pdf", pdf_com_traco(meta={
    "/Producer": "Microsoft: Print To PDF", "/Author": "Pessoa Que Imprimiu",
    "/Title": "Microsoft Print to PDF - Job #9.pdf"}))
checa(9, "Print to PDF: autor e titulo da impressora ficam de fora",
      "Pessoa Que Imprimiu" not in t and "Job #9" not in t, t)
t = validador.ler_arquivo("g.pdf", pdf_com_traco(meta={
    "/Producer": "Prefeitura", "/Author": "CLIENTE LTDA, CNPJ 11.222.333/0001-81",
    "/Title": "Guia de Recolhimento de ISS"}))
checa(10, "outro emissor: autor e titulo continuam valendo",
      "11.222.333/0001-81" in t and "Guia de Recolhimento de ISS" in t, t)

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 10 checagens verdes")
