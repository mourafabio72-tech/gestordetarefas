"""
prova_competencia_prazo.py — competência de referência e regra de prazo.

O caso que motivou: SPED e EFD-Contribuições são entregues no SEGUNDO mês
subsequente ao fato gerador. Fato gerador de julho, entrega em setembro. O
campo `competencia_ref` só aceitava quatro apelidos -- mês anterior, mesmo mês,
mês seguinte, ano anterior --, e nenhum diz "dois meses antes". Gerando as
tarefas de setembro, a competência saía 08/2026: a tarefa nascia um mês
adiantada, e o comprovante do SPED de julho não casava na baixa pelo
e-validador, que procura pela competência.

Agora o campo é um deslocamento em meses. Os apelidos continuam valendo, porque
é o que está gravado nas obrigações já cadastradas.

Rodar:  python provas/prova_competencia_prazo.py
"""
import os, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.services.gerador import (calc_competencia, deslocamento_competencia,   # noqa: E402
                                  calc_prazo, calc_prazo_interno)

ok = True
def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


print("\n=== 1. o caso do SPED: fato gerador julho, entrega setembro ===")
check("entrega set/2026 com '2 meses antes' → competência 07/2026",
      calc_competencia(9, 2026, "-2") == "07/2026", f"({calc_competencia(9, 2026, '-2')})")
check("o apelido antigo daria 08/2026 — era este o erro",
      calc_competencia(9, 2026, "mes_anterior") == "08/2026")

print("\n=== 2. os apelidos antigos continuam valendo ===")
casos = [
    ("mes_anterior",  9, 2026, "08/2026"),
    ("mesmo_mes",     9, 2026, "09/2026"),
    ("mes_seguinte",  9, 2026, "10/2026"),
    ("ano_anterior",  3, 2026, "03/2025"),
]
for ref, m, a, esperado in casos:
    check(f"{ref} → {esperado}", calc_competencia(m, a, ref) == esperado,
          f"({calc_competencia(m, a, ref)})")

print("\n=== 3. deslocamento numérico atravessa a virada de ano ===")
check("jan/2026 com -2 → 11/2025", calc_competencia(1, 2026, "-2") == "11/2025",
      f"({calc_competencia(1, 2026, '-2')})")
check("fev/2026 com -3 → 11/2025", calc_competencia(2, 2026, "-3") == "11/2025",
      f"({calc_competencia(2, 2026, '-3')})")
check("mar/2026 com -14 → 01/2025", calc_competencia(3, 2026, "-14") == "01/2025",
      f"({calc_competencia(3, 2026, '-14')})")
check("dez/2026 com +1 → 01/2027", calc_competencia(12, 2026, "1") == "01/2027",
      f"({calc_competencia(12, 2026, '1')})")

print("\n=== 4. valor ausente ou estranho não gera tarefa fora de hora ===")
check("vazio cai no padrão histórico (mês anterior)", deslocamento_competencia("") == -1)
check("None idem", deslocamento_competencia(None) == -1)
check("lixo idem, em vez de explodir", deslocamento_competencia("qualquer coisa") == -1)
check("inteiro direto é aceito", deslocamento_competencia(-2) == -2)

print("\n=== 5. N-ésimo dia útil: a regra que o SPED usa no vencimento ===")
# Set/2026 abre numa terça. Dias úteis: 1,2,3,4, 7,8,9,10,11, 14...
d = calc_prazo(9, 2026, "dia_util", 10, "antecipar", False)
check("10º dia útil de set/2026 = 14/09", d.isoformat() == "2026-09-14", f"({d})")
check("e é dia útil, não fim de semana", d.weekday() < 5)
# "Dia 10" e "10º dia útil" são coisas diferentes, e é essa a razão de existir a
# regra: quatro dias de diferença só porque o mês tem dois fins de semana antes.
fixo = calc_prazo(9, 2026, "dia_fixo", 10, "antecipar", False)
check("dia fixo 10 cai em 10/09 — quatro dias antes", fixo.isoformat() == "2026-09-10",
      f"({fixo})")
check("as duas regras dão datas diferentes no mesmo mês", d != fixo)
# Mês que começa no fim de semana muda a conta, e é justamente o ponto
d2 = calc_prazo(11, 2026, "dia_util", 10, "antecipar", False)
check("10º dia útil de nov/2026 (mês que abre no domingo) = 13/11",
      d2.isoformat() == "2026-11-13", f"({d2})")
check("N maior que os dias úteis do mês cai no último útil",
      calc_prazo(9, 2026, "dia_util", 99, "antecipar", False).isoformat() == "2026-09-30")

print("\n=== 6. prazo interno sai do vencimento, e nunca em dia não útil ===")
venc = calc_prazo(9, 2026, "dia_util", 10, "antecipar", False)   # 14/09, segunda
p5 = calc_prazo_interno(venc, 5, "corridos", False)
check("5 dias corridos antes de 14/09 → 09/09", p5.isoformat() == "2026-09-09", f"({p5})")
p5u = calc_prazo_interno(venc, 5, "uteis", False)
check("5 dias úteis antes de 14/09 → 07/09", p5u.isoformat() == "2026-09-07", f"({p5u})")
check("contar em úteis recua mais que contar em corridos", p5u < p5)
check("os dois caem em dia útil", p5.weekday() < 5 and p5u.weekday() < 5)
check("zero dias antes = o próprio vencimento",
      calc_prazo_interno(venc, 0, "corridos", False) == venc)

print("\n=== 7. campo numérico em branco não derruba o cadastro ===")
# Terceira vez que este padrão aparece. Trocar a regra para "N-ésimo dia útil"
# sem digitar o dia recusava o cadastro inteiro num 422 -- que a tela mostrava
# como "[object Object]", sem dizer qual campo.
from app.schemas import ObrigacaoCreate                                   # noqa: E402
o = ObrigacaoCreate(nome="X", regra_prazo_tipo="dia_util", regra_prazo_dia="")
check("dia em branco é aceito", o.regra_prazo_dia is None)
check("dia preenchido chega como número",
      ObrigacaoCreate(nome="X", regra_prazo_dia="10").regra_prazo_dia == 10)
check("vale para os outros numéricos",
      ObrigacaoCreate(nome="X", ancora_dias_antes="", tempo_previsto_min="  ")
      .ancora_dias_antes is None)

print("\n=== 8. sem o dia, o N-ésimo dia útil cai no primeiro ===")
# Foi o que aconteceu em produção: o campo ficou vazio e o vencimento saiu
# 01/09 em vez de 14/09. A regra não quebra -- mas a data fica errada em
# silêncio, então vale saber que é este o comportamento.
d = calc_prazo(9, 2026, "dia_util", None, "antecipar", False)
check("sem dia informado, vira o 1º dia útil", d.isoformat() == "2026-09-01", f"({d})")
d10 = calc_prazo(9, 2026, "dia_util", 10, "antecipar", False)
check("com 10, vira o 10º", d10.isoformat() == "2026-09-14", f"({d10})")
check("são datas bem diferentes — 13 dias", (d10 - d).days == 13)

print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
