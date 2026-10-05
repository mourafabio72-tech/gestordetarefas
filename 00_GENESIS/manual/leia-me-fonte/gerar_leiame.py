"""Gera o manual interativo nas duas versões, a partir de fonte.html.

    python3 gerar_leiame.py                      # só a do Tareffas (frontend/public/leia-me)
    python3 gerar_leiame.py --claude SAIDA.html  # também a da página do Claude
    python3 gerar_leiame.py --equipe SAIDA.html  # também a cópia avulsa para a equipe

Tareffas: a rota /leia-me/ abre sem login e o nginx tem CSP (script-src 'self',
font-src 'self' data:). Por isso: script em arquivo, Poppins servida pelo
site, prints como arquivo, nomes de cliente trocados por texto genérico, e o
registro de quem concluiu feito pela API do Tareffas (registro_tareffas.js).

Claude: um arquivo só, prints embutidos, Poppins do Google, registro pelo
`db` da página (o bloco que já está em fonte.html).

Equipe: a do Claude sem registro (só leitura, avisa que o registro é pelo
Leia-me do Tareffas) e sem nomes de cliente, para mandar por e-mail ou WhatsApp."""
import base64
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
FRONT = os.path.normpath(os.path.join(AQUI, "..", "..", "..", "frontend", "public", "leia-me"))
IMG = os.path.join(FRONT, "img")

INICIO_REG = "/* ---------- Registro de quem fez o fluxo ----------"
FIM_REG = "Recarregue a página.';});}"
NOMES = ("BSM", "Graber", "Bffc", "Fundação", "Fast One")


def troca(s, a, b):
    assert s.count(a) == 1, f"trecho não encontrado uma vez só: {a[:60]}"
    return s.replace(a, b, 1)


def tareffas(fonte):
    s = troca(fonte, '<link rel="preconnect" href="https://fonts.googleapis.com">\n', "")
    s = troca(s, '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap">\n', "")
    s = troca(s, "<style>\n", "<style>\n"
              '@font-face{font-family:"Poppins";src:url("fontes/Poppins-Regular.ttf") format("truetype");font-weight:400 500;font-display:swap}\n'
              '@font-face{font-family:"Poppins";src:url("fontes/Poppins-SemiBold.ttf") format("truetype");font-weight:600;font-display:swap}\n'
              '@font-face{font-family:"Poppins";src:url("fontes/Poppins-Bold.ttf") format("truetype");font-weight:700;font-display:swap}\n')
    s = troca(s, "25 no Simples, 13 nos grupos Graber e Bffc e na Fundação.", "25 no Simples e 13 em alguns grupos combinados com a gestão.")
    s = troca(s, "ex:'O grupo BSM não tem Contabilidade pela BPS4: o setor fica desmarcado nas 8 empresas, e nenhuma etapa contábil nem a ECD nasce para elas.',",
              "ex:'Um grupo que não contratou a Contabilidade da BPS4 fica com o setor desmarcado nas suas empresas, e nenhuma etapa contábil nem a ECD nasce para elas.',")
    s = troca(s, '<span class="rotulo">Só para quem edita esta página</span>', '<span class="rotulo">Só para admin e gestor</span>')
    s = troca(s, "body{background:var(--bg);", "body{margin:0;background:var(--bg);")
    i, j = s.index(INICIO_REG), s.index(FIM_REG) + len(FIM_REG)
    s = s[:i] + open(os.path.join(AQUI, "registro_tareffas.js"), encoding="utf-8").read() + s[j:]
    s = re.sub(r"\{\{img:([a-z\-]+)\}\}", lambda m: "img/" + m.group(1) + ".webp", s)
    for proibido in NOMES + ("fonts.googleapis", "{{img", "claude.use"):
        assert proibido not in s, f"sobrou '{proibido}' na versão do Tareffas"
    m = re.search(r"<script>\n?([\s\S]*)</script>", s)
    js = m.group(1)
    s = s[:m.start()] + '<script src="leia-me.js"></script>' + s[m.end():]
    assert "<script>" not in s
    for f in set(re.findall(r"img/([a-z\-]+)\.webp", s + js)):
        assert os.path.exists(os.path.join(IMG, f + ".webp")), f"falta img/{f}.webp"
    cab = '<!doctype html>\n<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    open(os.path.join(FRONT, "index.html"), "w", encoding="utf-8").write(cab + s + "\n</html>\n")
    open(os.path.join(FRONT, "leia-me.js"), "w", encoding="utf-8").write(js)
    return FRONT


def claude(fonte, destino):
    s = troca(fonte, "body{background:var(--bg);", "body{margin:0;background:var(--bg);")
    s = re.sub(r"\{\{img:([a-z\-]+)\}\}", lambda m: "data:image/webp;base64," + base64.b64encode(
        open(os.path.join(IMG, m.group(1) + ".webp"), "rb").read()).decode(), s)
    open(destino, "w", encoding="utf-8").write(s)
    return destino


def generico(s):
    """Troca os nomes de cliente por texto genérico (versões que saem do escritório)."""
    s = troca(s, "25 no Simples, 13 nos grupos Graber e Bffc e na Fundação.", "25 no Simples e 13 em alguns grupos combinados com a gestão.")
    return troca(s, "ex:'O grupo BSM não tem Contabilidade pela BPS4: o setor fica desmarcado nas 8 empresas, e nenhuma etapa contábil nem a ECD nasce para elas.',",
                 "ex:'Um grupo que não contratou a Contabilidade da BPS4 fica com o setor desmarcado nas suas empresas, e nenhuma etapa contábil nem a ECD nasce para elas.',")


def equipe(fonte, destino):
    s = generico(fonte)
    i, j = s.index(INICIO_REG), s.index(FIM_REG) + len(FIM_REG)
    s = s[:i] + ("/* Cópia para a equipe: o registro de quem concluiu só existe no Tareffas. */\n"
                 "function registra(){}\n"
                 "function msgReg(t){const el=$('regStatus');if(el)el.textContent=t;}\n"
                 "msgReg('Esta é uma cópia para leitura. Para registrar que você concluiu o fluxo, faça-o pelo botão Leia-me, no menu do Tareffas.');\n") + s[j:]
    s = troca(s, "body{background:var(--bg);", "body{margin:0;background:var(--bg);")
    # Confere antes de embutir os prints: o base64 pode conter "BSM" por acaso.
    for proibido in NOMES + ("claude.use",):
        assert proibido not in s, f"sobrou '{proibido}' na cópia da equipe"
    s = re.sub(r"\{\{img:([a-z\-]+)\}\}", lambda m: "data:image/webp;base64," + base64.b64encode(
        open(os.path.join(IMG, m.group(1) + ".webp"), "rb").read()).decode(), s)
    assert "{{img" not in s
    cab = '<!doctype html>\n<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    open(destino, "w", encoding="utf-8").write(cab + s + "\n</html>\n")
    return destino


if __name__ == "__main__":
    fonte = open(os.path.join(AQUI, "fonte.html"), encoding="utf-8").read()
    assert "—" not in fonte and "–" not in fonte, "travessão na fonte"
    print("Tareffas:", tareffas(fonte))
    if "--claude" in sys.argv:
        print("Claude:", claude(fonte, sys.argv[sys.argv.index("--claude") + 1]))
    if "--equipe" in sys.argv:
        print("Equipe:", equipe(fonte, sys.argv[sys.argv.index("--equipe") + 1]))
