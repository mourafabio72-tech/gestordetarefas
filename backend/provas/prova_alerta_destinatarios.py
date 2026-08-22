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

from app.services.whatsapp import (should_notify, destinatarios_alerta,  # noqa: E402
                                   normalizar_telefone, numero_do_usuario_zap,
                                   mapa_por_email)

ok = True
def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


class U:
    def __init__(self, id, nome, email=None, gestor=None, telefone=None):
        self.id, self.nome, self.email, self.gestor = id, nome, email, gestor
        self.telefone = telefone

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

print("\n=== 2. telefone do cadastro vira número que a API aceita ===")
check("celular com máscara ganha o 55", normalizar_telefone("(21) 99999-9999") == "5521999999999",
      normalizar_telefone("(21) 99999-9999"))
check("fixo com DDD também", normalizar_telefone("21 2222-3333") == "552122223333")
check("quem já tem o país fica como está", normalizar_telefone("5521999999999") == "5521999999999")
check("00 de discagem internacional sai", normalizar_telefone("005521999999999") == "5521999999999")
check("ramal de 4 dígitos é lixo, volta vazio", normalizar_telefone("4523") == "")
check("vazio e nulo não quebram", normalizar_telefone("") == "" and normalizar_telefone(None) == "")
check("texto sem dígito volta vazio", normalizar_telefone("não tem") == "")

print("\n=== 3. canais: escritório no WhatsApp, cliente conforme o cadastro ===")
diretor = U(1, "Diretor", "diretor@bps4.com", telefone="21988880001")
gerente = U(2, "Gerente", "gerente@bps4.com", gestor=diretor, telefone="21988880002")
analista = U(3, "Analista", "analista@bps4.com", gestor=gerente, telefone="(21) 98888-0003")
sup = U(4, "Supervisor", "sup@bps4.com", telefone="21988880004")
cli = E("Mark Building", email="fin@mark.com", telefone="5521977770000")

d = destinatarios_alerta(T([analista], sup, cli), {}, niveis=2)
trio = [(x["papel"], x["canal"], x["endereco"]) for x in d]
check("colaborador vai por WhatsApp", ("colaborador", "whatsapp", "5521988880003") in trio, str(trio))
check("gestor também por WhatsApp", ("gestor", "whatsapp", "5521988880002") in trio)
check("o gestor do gestor idem", ("gestor", "whatsapp", "5521988880001") in trio)
check("supervisor por WhatsApp", ("supervisor", "whatsapp", "5521988880004") in trio)
check("cliente por WhatsApp", ("cliente", "whatsapp", "5521977770000") in trio)
check("cliente TAMBÉM por e-mail", ("cliente", "email", "fin@mark.com") in trio)
check("nenhum e-mail para o escritório",
      [x for x in d if x["canal"] == "email" and x["papel"] != "cliente"] == [])
check("seis destinatários no total", len(d) == 6, f"({len(d)})")

print("\n=== 3b. o número vem do cadastro do ZapContábil, casado pelo e-mail ===")
# A API devolve o telefone em campo de nome variável; tentamos vários.
check("campo 'number'", numero_do_usuario_zap({"number": "21988887777"}) == "5521988887777")
check("campo 'whatsapp'", numero_do_usuario_zap({"whatsapp": "(21) 98888-6666"}) == "5521988886666")
check("campo 'phoneNumber'", numero_do_usuario_zap({"phoneNumber": "5521988885555"}) == "5521988885555")
check("nenhum campo conhecido volta vazio", numero_do_usuario_zap({"nome": "X"}) == "")
check("resposta que não é dicionário não quebra", numero_do_usuario_zap("lixo") == "")

zap = mapa_por_email([
    {"id": 1, "name": "Analista", "email": "ANALISTA@bps4.com", "number": "21977771111"},
    {"id": 2, "name": "Sem Numero", "email": "semnum@bps4.com"},
    {"id": 3, "name": "Sem Email", "number": "21977772222"},
    "linha inválida",
])
check("e-mail vira chave em minúsculas", "analista@bps4.com" in zap, str(zap))
check("usuário do Zap sem número fica de fora", "semnum@bps4.com" not in zap)
check("usuário sem e-mail fica de fora", len(zap) == 1)
check("lista vazia ou nula não quebra", mapa_por_email([]) == {} and mapa_por_email(None) == {})

# O número do Zap tem precedência sobre o telefone digitado no Tareffas.
d = destinatarios_alerta(T([analista], None, None), {}, 0, zap_por_email=zap)
check("o número do Zap vence o do cadastro local",
      (d[0]["canal"], d[0]["endereco"]) == ("whatsapp", "5521977771111"), str(d))
# Quem não está no Zap cai no telefone local.
d = destinatarios_alerta(T([sup], None, None), {}, 0, zap_por_email=zap)
check("quem não está no Zap usa o telefone do Tareffas", d[0]["endereco"] == "5521988880004")
# E-mail escrito diferente nos dois cadastros não casa — vai para a reserva.
outro_email = U(40, "Grafia Diferente", "analista@BPS4.com.br")
d = destinatarios_alerta(T([outro_email], None, None), {}, 0, zap_por_email=zap)
check("e-mail com domínio diferente não casa e cai no e-mail", d[0]["canal"] == "email")

print("\n=== 4. e-mail é a reserva de quem não tem telefone ===")
semtel = U(7, "Sem Telefone", "semtel@bps4.com")
d = destinatarios_alerta(T([semtel], None, None), {}, 0)
check("cai no e-mail em vez de não avisar", (d[0]["canal"], d[0]["endereco"]) == ("email", "semtel@bps4.com"))
sonome = U(8, "Sem Nada")
check("sem telefone e sem e-mail fica de fora", destinatarios_alerta(T([sonome], None, None), {}, 0) == [])
lixo = U(11, "Telefone Podre", "podre@bps4.com", telefone="1234")
d = destinatarios_alerta(T([lixo], None, None), {}, 0)
check("telefone impossível não vira WhatsApp — usa o e-mail", d[0]["canal"] == "email")

print("\n=== 5. níveis de gestor limitam a subida ===")
d1 = destinatarios_alerta(T([analista], None, None), {}, niveis=1)
check("com 1 nível, só o gerente", len(d1) == 2 and d1[1]["nome"] == "Gerente")
d0 = destinatarios_alerta(T([analista], None, None), {}, niveis=0)
check("com 0 nível, ninguém acima", len(d0) == 1)

print("\n=== 6. substituição: quem está fora é trocado, o gestor dele fica ===")
ferista = U(9, "De Férias", "ferias@bps4.com", gestor=gerente, telefone="21988889999")
subst = U(10, "Substituto", "subst@bps4.com", telefone="21988887777")
d = destinatarios_alerta(T([ferista], None, None), {9: subst}, niveis=1)
end = [x["endereco"] for x in d]
check("o ausente NÃO recebe", "5521988889999" not in end)
check("o substituto recebe no lugar, por WhatsApp", ("5521988887777" in end) and d[0]["canal"] == "whatsapp")
check("marcado como substituto", d[0]["papel"] == "substituto")
check("o gestor do ausente continua na cópia", "5521988880002" in end)

print("\n=== 7. as bordas que duplicariam ou quebrariam o envio ===")
d = destinatarios_alerta(T([analista], analista, None), {}, niveis=0)
check("responsável que também é supervisor recebe uma vez só", len(d) == 1, f"({len(d)})")
outro = U(5, "Outro", "outro@bps4.com", gestor=gerente, telefone="21988880005")
d = destinatarios_alerta(T([analista, outro], None, None), {}, niveis=1)
check("gestor comum a dois responsáveis não duplica",
      [x["endereco"] for x in d].count("5521988880002") == 1)
so_email = E("Só E-mail", email="c@x.com")
canais = [x["canal"] for x in destinatarios_alerta(T([], None, so_email), {}, 0)]
check("empresa sem telefone não gera WhatsApp", canais == ["email"], str(canais))
so_zap = E("Só Zap", telefone="21977776666")
canais = [x["canal"] for x in destinatarios_alerta(T([], None, so_zap), {}, 0)]
check("empresa sem e-mail não gera e-mail", canais == ["whatsapp"], str(canais))
check("tarefa sem empresa não quebra", destinatarios_alerta(T([analista], None, None), {}, 0) != [])
a = U(20, "A", "a@x.com", telefone="21911110001")
b = U(21, "B", "b@x.com", telefone="21911110002"); b.gestor = a; a.gestor = b
check("ciclo de gestores não trava", len(destinatarios_alerta(T([a], None, None), {}, 10)) <= 3)
# Colaborador que também é o contato cadastrado da empresa. O mesmo NÚMERO não
# pode receber duas vezes. O e-mail da empresa continua saindo: é outro canal e
# outro papel (ele é avisado como colaborador no zap e como cliente no e-mail),
# e suprimir isso esconderia da empresa um aviso que é dela.
dono = U(30, "Dono", "dono@x.com", telefone="21955554444")
emp = E("Empresa do Dono", email="dono@x.com", telefone="21955554444")
d = destinatarios_alerta(T([dono], None, emp), {}, 0)
end = [x["endereco"] for x in d]
check("nenhum endereço repetido", len(end) == len(set(end)), str(end))
check("o mesmo número não recebe duas vezes", end.count("5521955554444") == 1)

print("\n" + ("TUDO VERDE" if ok else "VERMELHO") + "\n")
sys.exit(0 if ok else 1)
