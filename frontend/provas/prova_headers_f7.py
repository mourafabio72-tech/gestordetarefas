"""Prova da Fase 7, lado do que o navegador recebe.

Duas coisas, e a segunda é a que importa:

1. Confere que `nginx.conf` declara os cabeçalhos de segurança no `location /`,
   todos com `always` (sem ele o nginx omite o cabeçalho nas respostas de erro).
2. Sobe o `dist/` com EXATAMENTE os cabeçalhos lidos do arquivo, para a CSP ser
   testada no navegador de verdade. CSP mal calibrada não quebra teste nenhum:
   quebra a tela do usuário, e só o console mostra.

    cd frontend && python3 provas/prova_headers_f7.py           # só a conferência
    cd frontend && python3 provas/prova_headers_f7.py --servir  # sobe em :4173

Esta máquina não tem nginx nem docker, então a SINTAXE do nginx.conf não é
provada aqui, só o conteúdo dos cabeçalhos. Está declarado de propósito.
"""

import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONF = RAIZ / "nginx.conf"
DIST = RAIZ / "dist"

OBRIGATORIOS = [
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Strict-Transport-Security",
    "Permissions-Policy",
    "Content-Security-Policy",
]


def headers_do_location_raiz():
    """Extrai os `add_header` do bloco `location /` do nginx.conf."""
    texto = CONF.read_text(encoding="utf-8")
    inicio = texto.index("location / {")
    fim = texto.index("location /api")
    bloco = texto[inicio:fim]
    achados = {}
    for nome, valor in re.findall(r'add_header\s+(\S+)\s+"([^"]*)"\s+always;', bloco):
        achados[nome] = valor
    return achados


falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>2}. {descricao}")
    else:
        print(f"FALHA  {n:>2}. {descricao}")
        falhou.append(n)


print("PROVA CABEÇALHOS FASE 7 (o que o navegador recebe)")
achados = headers_do_location_raiz()

faltando = [h for h in OBRIGATORIOS if h not in achados]
checa(1, f"os {len(OBRIGATORIOS)} cabeçalhos estão no location / com `always`", not faltando)

csp = achados.get("Content-Security-Policy", "")
checa(2, "a CSP tem default-src 'self' e não libera script de fora",
      "default-src 'self'" in csp and "script-src 'self';" in csp)

checa(3, "a CSP não usa 'unsafe-eval' nem 'unsafe-inline' em script",
      "unsafe-eval" not in csp and "script-src 'self' 'unsafe-inline'" not in csp)

checa(4, "object-src e base-uri estão trancados",
      "object-src 'none'" in csp and "base-uri 'self'" in csp)

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 4 checagens verdes")

if "--servir" in sys.argv:
    if not DIST.is_dir():
        print("dist/ não existe. Rode `npm run build` antes.")
        sys.exit(1)

    class ComHeaders(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(DIST), **kw)

        def end_headers(self):
            for nome, valor in achados.items():
                # HSTS em http local faria o navegador travar o domínio em https.
                if nome == "Strict-Transport-Security":
                    continue
                self.send_header(nome, valor)
            super().end_headers()

        def send_head(self):
            # O nginx faz try_files: rota do React cai no index.html.
            caminho = DIST / self.path.lstrip("/").split("?")[0]
            if not caminho.exists() and not self.path.startswith("/assets"):
                self.path = "/index.html"
            return super().send_head()

        def log_message(self, *a):
            pass

    print("\nservindo dist/ em http://localhost:4173 com a CSP do nginx.conf")
    ThreadingHTTPServer(("127.0.0.1", 4173), ComHeaders).serve_forever()
