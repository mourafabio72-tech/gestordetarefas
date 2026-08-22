"""
prova_alerta_destinatarios.py — quem recebe o alerta, por qual canal, e quando.

Estas são as duas regras que decidem se um alerta sai certo ou errado, e as
duas erram em silêncio: `should_notify` (a régua de proximidade do prazo) e
`destinatarios_alerta` (a lista de quem recebe). Um erro aqui não derruba o
sistema -- ele manda mensagem para o cliente errado, ou não manda para ninguém.

Não toca no banco: monta dublês com os mesmos atributos que o código lê.

Rodar:  python provas/prova_alerta_destinatarios.py
"""
import os, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.services.whatsapp import should_notify, destinatarios_alerta  # noqa: E402

ok = True
def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


class U:
    def __init__(self, id, nome, email=None, gestor=None):
        self.id, self.nome, self.email, self.gestor = id, nome, email, gestor

class E:
    def __init__(self, razao_social, email=None, telefone=None):
        self.razao_social, self.email, self.telefone = razao_social, email, telefone

class T:
    def __init__(self, responsaveis=(), supervisor=None, empresa=None):
        self.responsaveis, self.supervisor, self.empresa = list(responsaveis), supervisor, empresa


print("\n=== 1. régua: o que sai só no horário principal e o que sai sempre ===")
check("3 dias antes (padrão) sai no principal", should_notify(3, "principal", 3))
check("3 dias antes NÃO sai no extra", not should_notify(3, "extra", 3))
check("1 dia antes sai no principal", should_notify(1, "principal", 3))
check("1 dia antes NÃO sai no extra", not should_notify(1, "extra", 3))
check("no dia do prazo sai no principal", should_notify(0, "principal", 3))
check("no dia do prazo sai TAMBÉM no extra", should_notify(0, "extra", 3))
check("atrasada sai em todo horário", should_notify(-5, "extra", 3))
check("2 dias antes não sai (não é 1 nem 3)", not should_notify(2, "principal", 3))
check("com dias_antes=5, o 5 passa a sair", should_notify(5, "principal", 5))
check("com dias_antes=5, o 3 deixa de sair", not should_notify(3, "principal", 5))
check("tarefa sem data não notifica", not should_notify(None, "principal", 3))

print("\n=== 2. destinatários: responsável, cadeia de gestores, supervisor, cliente ===")
diretor = U(1, "Diretor", "diretor@bps4.com")
gerente = U(2, "Gerente", "gerente@bps4.com", gestor=diretor)
analista = U(3, "Analista", "analista@bps4.com", gestor=gerente)
sup = U(4, "Supervisor", "sup@bps4.com")
cli = E("Mark Building", email="fin@mark.com", telefone="5521999999999")

d = destinatarios_alerta(T([analista], sup, cli), {}, niveis=2)
papeis = [(x["papel"], x["canal"], x["endereco"]) for x in d]
check("o colaborador recebe por e-mail", ("colaborador", "email", "analista@bps4.com") in papeis)
check("o gerente entra na cópia", ("gestor", "email", "gerente@bps4.com") in papeis)
check("o diretor também, com 2 níveis", ("gestor", "email", "diretor@bps4.com") in papeis)
check("o supervisor entra", ("supervisor", "email", "sup@bps4.com") in papeis)
check("o cliente recebe por WhatsApp", ("cliente", "whatsapp", "5521999999999") in papeis)
check("e também por e-mail", ("cliente", "email", "fin@mark.com") in papeis)
check("seis destinatários no total", len(d) == 6, f"({len(d)})")

print("\n=== 3. níveis de gestor limitam a subida ===")
d1 = destinatarios_alerta(T([analista], None, None), {}, niveis=1)
check("com 1 nível, só o gerente", [x["endereco"] for x in d1] == ["analista@bps4.com", "gerente@bps4.com"],
      str([x["endereco"] for x in d1]))
d0 = destinatarios_alerta(T([analista], None, None), {}, niveis=0)
check("com 0 nível, ninguém acima", [x["endereco"] for x in d0] == ["analista@bps4.com"])

print("\n=== 4. substituição: quem está fora é trocado, o gestor dele fica ===")
ferista = U(9, "De Férias", "ferias@bps4.com", gestor=gerente)
subst = U(10, "Substituto", "subst@bps4.com")
d = destinatarios_alerta(T([ferista], None, None), {9: subst}, niveis=1)
enderecos = [x["endereco"] for x in d]
check("o ausente NÃO recebe", "ferias@bps4.com" not in enderecos)
check("o substituto recebe no lugar", "subst@bps4.com" in enderecos)
check("marcado como substituto", d[0]["papel"] == "substituto")
check("o gestor do ausente continua na cópia", "gerente@bps4.com" in enderecos)

print("\n=== 5. as bordas que duplicariam ou quebrariam o envio ===")
# Mesma pessoa como responsável e supervisor: não pode receber duas vezes.
d = destinatarios_alerta(T([analista], analista, None), {}, niveis=0)
check("responsável que também é supervisor recebe uma vez só", len(d) == 1, f"({len(d)})")
# Dois responsáveis com o mesmo gestor: o gestor recebe uma vez.
outro = U(5, "Outro", "outro@bps4.com", gestor=gerente)
d = destinatarios_alerta(T([analista, outro], None, None), {}, niveis=1)
check("gestor comum a dois responsáveis não duplica",
      [x["endereco"] for x in d].count("gerente@bps4.com") == 1)
# Sem e-mail cadastrado: não vira destinatário vazio.
semmail = U(6, "Sem E-mail", None)
check("usuário sem e-mail é ignorado", destinatarios_alerta(T([semmail], None, None), {}, 0) == [])
# Empresa sem telefone: só o e-mail dela.
so_email = E("Só E-mail", email="c@x.com")
canais = [x["canal"] for x in destinatarios_alerta(T([], None, so_email), {}, 0)]
check("empresa sem telefone não gera WhatsApp", canais == ["email"], str(canais))
# Tarefa sem empresa (avulsa): não quebra.
check("tarefa sem empresa não quebra", destinatarios_alerta(T([analista], None, None), {}, 0) != [])
# Ciclo de gestor (A gerencia B que gerencia A): não pode entrar em laço.
a = U(20, "A", "a@x.com"); b = U(21, "B", "b@x.com", gestor=a); a.gestor = b
check("ciclo de gestores não trava", len(destinatarios_alerta(T([a], None, None), {}, 10)) <= 3)

print("\n" + ("TUDO VERDE" if ok else "VERMELHO") + "\n")
sys.exit(0 if ok else 1)
