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
MAX_IMAGENS_PDF = 4   # páginas escaneadas lidas por PDF


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


def ler_imagens_do_pdf(reader) -> str:
    """Texto das imagens de um PDF que não tem texto (página escaneada)."""
    if not disponivel():
        return ""
    partes = []
    try:
        lidas = 0
        for pagina in reader.pages:
            for imagem in pagina.images:
                if lidas >= MAX_IMAGENS_PDF:
                    break
                partes.append(ler_imagem(imagem.data))
                lidas += 1
    except Exception:
        pass
    return "\n".join(p for p in partes if p)


if __name__ == "__main__":
    import sys
    # Uso: python -m app.services.ocr ARQUIVO  (imagem ou PDF)
    caminho = sys.argv[1]
    dados = open(caminho, "rb").read()
    if caminho.lower().endswith(".pdf"):
        import pypdf
        print(ler_imagens_do_pdf(pypdf.PdfReader(io.BytesIO(dados))))
    else:
        print(ler_imagem(dados))
