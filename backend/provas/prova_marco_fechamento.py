"""
prova_marco_fechamento.py — prazo que varia por empresa sem cadastro em cruz.

O problema: a entrega do balancete é dia 15 numa empresa, 5º dia útil noutra e
dia 18 numa terceira. E não é só o balancete: as etapas que o antecedem
(lançar notas, conciliar banco) precisam caber ANTES desse marco, em cada
cliente. Cadastrar isso obrigação por obrigação, empresa por empresa, seria o
produto das duas listas -- 3 empresas x 8 etapas = 24 ajustes na mão, refeitos
toda vez que um cliente mudasse de data.

O desenho: a EMPRESA tem um marco (o fechamento contábil dela) e a OBRIGAÇÃO
diz quantos dias antes do marco ela vence. Um cadastro por empresa, um por
obrigação. Muda o marco, a cadeia inteira daquele cliente desloca junto.

Obrigação com prazo legal (SPED, DEFIS) não se ancora em nada e segue como
sempre foi -- é o padrão, e a maioria.

Rodar:  DB_PATH=<temp.db> python provas/prova_marco_fechamento.py
"""
import os, sys, tempfile
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("DATABASE_URL", "sqlite:///" + tempfile.mktemp(suffix=".db"))

from app.services.gerador import (calc_vencimento, calc_marco_fechamento,   # noqa: E402
                                  calc_prazo)

ok = True
def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


class Emp:
    def __init__(self, nome, tipo=None, dia=None):
        self.razao_social, self.fechamento_tipo, self.fechamento_dia = nome, tipo, dia

class Obr:
    def __init__(self, nome, ancora=None, dias=0, tipo_dias="uteis",
                 regra="ultimo_dia_util", regra_dia=None):
        self.nome, self.ancora = nome, ancora
        self.ancora_dias_antes, self.ancora_tipo_dias = dias, tipo_dias
        self.regra_prazo_tipo, self.regra_prazo_dia = regra, regra_dia
        self.ajuste_nao_util, self.sabado_util = "antecipar", False

# Set/2026 abre numa terça. Dias úteis: 1,2,3,4, 7,8,9,10,11, 14,15,16,17,18, 21...
A = Emp("Empresa A", "dia_fixo", 15)      # entrega dia 15
B = Emp("Empresa B", "dia_util", 5)       # 5º dia útil
C = Emp("Empresa C", "dia_fixo", 18)      # dia 18
D = Emp("Empresa D")                       # não usa marco

print("\n=== 1. o marco é da empresa, e cada uma tem o seu ===")
check("A fecha em 15/09", calc_marco_fechamento(A, 9, 2026).isoformat() == "2026-09-15",
      f"({calc_marco_fechamento(A, 9, 2026)})")
check("B fecha no 5º dia útil = 07/09", calc_marco_fechamento(B, 9, 2026).isoformat() == "2026-09-07",
      f"({calc_marco_fechamento(B, 9, 2026)})")
check("C fecha em 18/09", calc_marco_fechamento(C, 9, 2026).isoformat() == "2026-09-18")
check("D não usa marco", calc_marco_fechamento(D, 9, 2026) is None)

print("\n=== 2. a MESMA obrigação vence em data diferente por empresa ===")
balancete = Obr("Balancete", ancora="fechamento", dias=0)
v = {e.razao_social: calc_vencimento(balancete, e, 9, 2026) for e in (A, B, C)}
for nome, esperado in [("Empresa A", "2026-09-15"), ("Empresa B", "2026-09-07"),
                       ("Empresa C", "2026-09-18")]:
    check(f"balancete da {nome} = {esperado}", v[nome].isoformat() == esperado, f"({v[nome]})")
check("as três datas são realmente diferentes", len({d.isoformat() for d in v.values()}) == 3)

print("\n=== 3. a cadeia inteira desloca junto com o marco ===")
# 3 etapas ancoradas no mesmo fechamento, cada uma com sua folga
etapas = [
    Obr("Lançar notas",   ancora="fechamento", dias=6),
    Obr("Conciliar banco", ancora="fechamento", dias=3),
    Obr("Balancete",      ancora="fechamento", dias=0),
]
for e in (A, B):
    datas = [calc_vencimento(o, e, 9, 2026) for o in etapas]
    print(f"    {e.razao_social}: " + " -> ".join(f"{o.nome} {d.strftime('%d/%m')}"
                                                   for o, d in zip(etapas, datas)))
    check(f"{e.razao_social}: as etapas vêm em ordem crescente",
          datas[0] < datas[1] < datas[2])
    check(f"{e.razao_social}: nenhuma cai depois do fechamento",
          max(datas) == calc_marco_fechamento(e, 9, 2026))

print("\n=== 4. prazo legal não se mexe: SPED e DEFIS seguem iguais em todas ===")
sped = Obr("EFD-Contribuições", regra="dia_util", regra_dia=10)   # sem âncora
datas_sped = {e.razao_social: calc_vencimento(sped, e, 9, 2026) for e in (A, B, C, D)}
check("mesma data para as quatro empresas",
      len({d.isoformat() for d in datas_sped.values()}) == 1,
      f"({sorted({d.isoformat() for d in datas_sped.values()})})")
check("e é a regra própria da obrigação (10º dia útil = 14/09)",
      datas_sped["Empresa A"].isoformat() == "2026-09-14", f"({datas_sped['Empresa A']})")

print("\n=== 5. falta de cadastro não impede a tarefa de nascer ===")
# empresa ancorada mas SEM marco definido -> cai na regra própria da obrigação
v_d = calc_vencimento(balancete, D, 9, 2026)
esperado = calc_prazo(9, 2026, "ultimo_dia_util", None, "antecipar", False)
check("empresa sem marco usa a regra própria da obrigação", v_d == esperado, f"({v_d})")
check("e a data existe, não é nula", v_d is not None)

print("\n=== 6. recuo em dias corridos também vale ===")
corr = Obr("Etapa", ancora="fechamento", dias=5, tipo_dias="corridos")
d = calc_vencimento(corr, A, 9, 2026)          # 5 corridos antes de 15/09 = 10/09
check("5 dias corridos antes de 15/09 = 10/09", d.isoformat() == "2026-09-10", f"({d})")
util = calc_vencimento(Obr("Etapa", ancora="fechamento", dias=5, tipo_dias="uteis"), A, 9, 2026)
check("5 dias úteis recuam mais que 5 corridos", util < d, f"({util} vs {d})")
check("nenhum dos dois cai em fim de semana", d.weekday() < 5 and util.weekday() < 5)

print("\n=== 7. o marco atravessa a virada de mês sem quebrar ===")
# Nov/2026 abre num domingo — o 5º dia útil não é o dia 5
m = calc_marco_fechamento(B, 11, 2026)
check("5º dia útil de nov/2026 = 06/11", m.isoformat() == "2026-11-06", f"({m})")
check("é dia útil", m.weekday() < 5)

print("\n=== 8. marco em branco não derruba o cadastro da empresa ===")
# O formulário envia TODOS os campos de uma vez. Com o marco vazio, o "" chegava
# num campo inteiro e o 422 derrubava o salvamento inteiro -- inclusive de quem
# só queria trocar o segmento.
from app.schemas import EmpresaCreate                                    # noqa: E402
try:
    e = EmpresaCreate(razao_social="TESTE", segmento="comercio",
                      fechamento_tipo="", fechamento_dia="")
    check("marco em branco é aceito", True)
    check("vira ausente, não string vazia",
          e.fechamento_tipo is None and e.fechamento_dia is None,
          f"({e.fechamento_tipo!r}, {e.fechamento_dia!r})")
except Exception as ex:
    check("marco em branco é aceito", False, f"({type(ex).__name__})")
e2 = EmpresaCreate(razao_social="T", fechamento_tipo="dia_util", fechamento_dia="10")
check("marco preenchido continua chegando como número", e2.fechamento_dia == 10,
      f"({e2.fechamento_dia!r})")
e3 = EmpresaCreate(razao_social="T", fechamento_tipo="  ", fechamento_dia=None)
check("só espaço também conta como em branco", e3.fechamento_tipo is None)

print("\n=== 9. campo de formulário vazio nunca derruba o salvamento ===")
# Mesmo padrão em toda parte: select sem escolha manda "", e "" num campo
# inteiro virava 422 -- que a tela mostrava como "[object Object]".
from app.routes.empresas import RespSetorItem                            # noqa: E402
i = RespSetorItem(setor_id=1, responsavel_id="")
check("setor que atende sem dono é aceito", i.responsavel_id is None)
check("com dono continua chegando número",
      RespSetorItem(setor_id=1, responsavel_id="7").responsavel_id == 7)

print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
