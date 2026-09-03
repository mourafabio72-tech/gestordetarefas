"""
prova_carimbo_build.py — o carimbo tem que dizer que CODIGO esta no ar.

O que ele fazia: lia o mtime do proprio versao.py. Em 2026-09-03 isso mentiu.
O /api/health respondia 20260901-1155 havia tres dias enquanto tres deploys
entravam, porque o EasyPanel faz checkout por cima do diretorio existente e so
o arquivo ALTERADO ganha mtime novo. Commit que nao mexe no versao.py nao move
o mtime do versao.py, e o carimbo congela. Quase demos o webhook como morto por
causa disso, com o deploy ja no ar.

O que ele faz agora: le o mtime mais recente de todo o pacote app/. Qualquer
arquivo de codigo que mude move o carimbo.

Rodar:  python provas/prova_carimbo_build.py
"""
import os, sys, tempfile, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + tempfile.mktemp(suffix=".db"))

from app import versao                                                   # noqa: E402

ok = True
def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


def pacote_falso(arquivos):
    """Monta um pacote de mentira: {caminho relativo: mtime}."""
    raiz = Path(tempfile.mkdtemp())
    for rel, quando in arquivos.items():
        alvo = raiz / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text("# nada")
        os.utime(alvo, (quando, quando))
    return raiz


def carimbo_de(raiz):
    original = versao._PACOTE
    try:
        versao._PACOTE = raiz
        return versao._carimbo_de_build()
    finally:
        versao._PACOTE = original


T0 = time.mktime(time.strptime("2026-09-01 11:55", "%Y-%m-%d %H:%M"))
T1 = T0 + 2 * 24 * 3600          # dois dias depois
T2 = T1 + 3600                   # uma hora depois disso

print("\n=== 1. o carimbo segue o arquivo MAIS NOVO, nao o versao.py ===")
# Este e exatamente o caso real: o commit mexeu em models.py e nao no versao.py.
raiz = pacote_falso({"versao.py": T0, "models.py": T1})
esperado = time.strftime("%Y%m%d-%H%M", time.localtime(T1))
check("pega o mtime de models.py", carimbo_de(raiz) == esperado,
      f"(deu {carimbo_de(raiz)}, esperava {esperado})")
antigo = time.strftime("%Y%m%d-%H%M", time.localtime(T0))
check("e NAO fica no do versao.py", carimbo_de(raiz) != antigo, f"(o velho era {antigo})")

print("\n=== 2. arquivo em subpasta tambem conta ===")
raiz = pacote_falso({"versao.py": T0, "routes/tarefas.py": T2})
check("varre o pacote inteiro, nao so a raiz",
      carimbo_de(raiz) == time.strftime("%Y%m%d-%H%M", time.localtime(T2)),
      f"({carimbo_de(raiz)})")

print("\n=== 3. __pycache__ nao entra, nem sendo o mais novo ===")
# O .pyc nasce quando o container importa o modulo: carimbaria a hora do BOOT,
# nao a do codigo, e o carimbo mudaria sozinho a cada restart sem deploy.
raiz = pacote_falso({"versao.py": T0, "models.py": T1,
                     "__pycache__/models.cpython-311.py": T2})
check("ignora o cache de bytecode",
      carimbo_de(raiz) == time.strftime("%Y%m%d-%H%M", time.localtime(T1)),
      f"({carimbo_de(raiz)})")

print("\n=== 4. so .py conta: dado no volume nao carimba deploy ===")
raiz = pacote_falso({"versao.py": T0, "data/upload_do_cliente.pdf": T2})
check("arquivo que nao e codigo nao move o carimbo",
      carimbo_de(raiz) == time.strftime("%Y%m%d-%H%M", time.localtime(T0)),
      f"({carimbo_de(raiz)})")

print("\n=== 5. pacote sem .py nenhum nao quebra ===")
raiz = pacote_falso({"leiame.txt": T1})
c = carimbo_de(raiz)
check("cai no mtime do proprio versao.py", c not in ("", None) and c != "desconhecido", f"({c})")

print("\n=== 6. o carimbo real sai no formato que o curl procura ===")
import re                                                                # noqa: E402
check("AAAAMMDD-HHMM", bool(re.fullmatch(r"\d{8}-\d{4}", versao.BUILD)), f"({versao.BUILD})")
check("VERSAO_COMPLETA vem com o prefixo 'build'",
      versao.VERSAO_COMPLETA == f"build {versao.BUILD}", f"({versao.VERSAO_COMPLETA})")

print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
