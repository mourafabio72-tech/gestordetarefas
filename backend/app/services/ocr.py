"""Leitura de imagem (OCR) para o e-validador, no próprio servidor.

Decisão de 2026-10-28: guia em imagem (PNG, JPG, PDF escaneado) é lida pelo
tesseract instalado no container, e não pela IA, para o documento do cliente
não sair do servidor. A IA continua recebendo só texto.

Tudo aqui é best-effort: sem o tesseract (máquina de desenvolvimento, por
exemplo), as funções devolvem "" e o e-validador segue com o que já tinha
(dados do arquivo, nome do arquivo). Nunca derruba o processamento.
"""
import io
import shutil

# Trava contra imagem gigante (bomba de descompressão): ~50 megapixels sobra
# para guia escaneada a 300 dpi e recusa o que só serviria para travar o
# servidor.
MAX_PIXELS = 50_000_000
# O tesseract lê melhor texto pequeno com a imagem perto de 300 dpi; acima
# disso só gasta tempo. Lado maior limitado a este tamanho.
MAX_LADO = 3500
TIMEOUT = 40          # segundos por imagem
MAX_PAGINAS_PDF = 4   # páginas sem texto lidas por PDF


def disponivel() -> bool:
    return shutil.which("tesseract") is not None


def ler_imagem(conteudo: bytes) -> str:
    """Texto de uma imagem (PNG, JPG...). "" se não der."""
    if not conteudo or not disponivel():
        return ""
    try:
        import pytesseract
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS
        img = Image.open(io.BytesIO(conteudo))
        img.load()
        if img.width * img.height > MAX_PIXELS:
            return ""
        maior = max(img.width, img.height)
        if maior > MAX_LADO:
            fator = MAX_LADO / maior
            img = img.resize((int(img.width * fator), int(img.height * fator)))
        if img.mode not in ("L", "RGB"):
            img = img.convert("RGB")
        return pytesseract.image_to_string(img, lang="por", timeout=TIMEOUT) or ""
    except Exception:
        return ""


def ler_paginas_do_pdf(conteudo: bytes) -> str:
    """Texto de um PDF sem texto, lendo cada PÁGINA desenhada como imagem.

    Página inteira, e não as imagens embutidas: o "Microsoft Print to PDF" grava
    o texto da guia como traços vetoriais, e as imagens do arquivo são o logo e
    o QR Code (DAS de 2026-11-03). Desenhar a página cobre esse caso e o escaneado.
    """
    if not conteudo or not disponivel():
        return ""
    partes = []
    try:
        import pypdfium2
        pdf = pypdfium2.PdfDocument(conteudo)
        try:
            for i in range(min(len(pdf), MAX_PAGINAS_PDF)):
                pagina = pdf[i]
                largura, altura = pagina.get_size()
                # 300 dpi, sem passar do lado máximo (o PDF é de 72 pontos por
                # polegada). Página gigante não vira imagem gigante na memória.
                escala = min(300 / 72, MAX_LADO / max(largura, altura, 1))
                img = pagina.render(scale=escala, grayscale=True).to_pil()
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                partes.append(ler_imagem(buf.getvalue()))
        finally:
            pdf.close()
    except Exception:
        pass
    return "\n".join(p for p in partes if p)


if __name__ == "__main__":
    import sys
    # Uso: python -m app.services.ocr ARQUIVO  (imagem ou PDF)
    caminho = sys.argv[1]
    dados = open(caminho, "rb").read()
    if caminho.lower().endswith(".pdf"):
        print(ler_paginas_do_pdf(dados))
    else:
        print(ler_imagem(dados))
