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

Equipe: só um aviso (desde 2026-10-25) mandando fazer a trilha pelo Leia-me
do Tareffas. A cópia completa não registrava o progresso e confundia a equipe."""
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


TAREFFAS = "https://gestordetarefas.zoaria.com.br"

AVISO_EQUIPE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tareffas: faça a trilha pelo sistema</title>
<style>
:root{--bg:#FBF6EC;--papel:#FFFDF9;--areia:#DCCDB6;--oliva:#55614E;--escuro:#2F3B2F;--texto:#3D4A38;--suave:#66705E}
@media (prefers-color-scheme:dark){:root{--bg:#1C221B;--papel:#242C23;--areia:#3E4A3B;--oliva:#A9BC98;--escuro:#EEF0E6;--texto:#D8DECF;--suave:#A6AF9B}}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:grid;place-items:center;padding:16px;background:var(--bg);color:var(--texto);
 font-family:'Poppins',ui-sans-serif,system-ui,-apple-system,'Segoe UI',Arial,sans-serif;line-height:1.6}
main{max-width:560px;width:100%;background:var(--papel);border:1px solid var(--areia);border-radius:16px;padding:28px}
h1{margin:0 0 8px;font-size:1.4rem;color:var(--escuro)}
ol{padding-left:1.2em;margin:16px 0}
li{margin:6px 0}
.btn{display:inline-block;margin-top:8px;padding:10px 18px;border-radius:10px;background:var(--oliva);color:var(--bg);
 text-decoration:none;font-weight:600}
.nota{margin-top:18px;font-size:.9rem;color:var(--suave)}
</style></head>
<body><main>
<h1>A trilha do Tareffas mudou de lugar</h1>
<p>Esta cópia avulsa não guarda o seu progresso. Para a trilha valer e você aparecer
como concluído, faça-a dentro do Tareffas:</p>
<ol>
<li>Entre no Tareffas com o seu login.</li>
<li>No menu da esquerda, clique em <strong>Leia-me</strong>.</li>
<li>Faça a trilha até o fim. O progresso fica salvo na sua conta.</li>
</ol>
<a class="btn" href="__URL__/">Abrir o Tareffas</a>
<p class="nota">Já fez a trilha por esta cópia? Ela não foi registrada.
Refaça pelo botão Leia-me do Tareffas.</p>
</main></body></html>
"""


def equipe(fonte, destino):
    """A cópia avulsa virou um aviso (2026-10-25). Fazendo a trilha por ela, o
    progresso ficava só no navegador e nunca chegava ao quadro 'Quem leu o
    Leia-me': a equipe fazia a trilha e o controle não andava. `fonte` fica
    na assinatura para a chamada continuar igual."""
    s = AVISO_EQUIPE.replace("__URL__", TAREFFAS)
    assert "—" not in s and "–" not in s, "travessão no aviso"
    open(destino, "w", encoding="utf-8").write(s)
    return destino


if __name__ == "__main__":
    fonte = open(os.path.join(AQUI, "fonte.html"), encoding="utf-8").read()
    assert "—" not in fonte and "–" not in fonte, "travessão na fonte"
    print("Tareffas:", tareffas(fonte))
    if "--claude" in sys.argv:
        print("Claude:", claude(fonte, sys.argv[sys.argv.index("--claude") + 1]))
    if "--equipe" in sys.argv:
        print("Equipe:", equipe(fonte, sys.argv[sys.argv.index("--equipe") + 1]))
