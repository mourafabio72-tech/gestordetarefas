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
                                   normalizar_telefone, mapa_numero_por_email,
                                   mapa_userid_por_email, eh_cliente)

ok = True
def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


class U:
    def __init__(self, id, nome, email=None, gestor=None, telefone=None,
                 tipo="colaborador", grupo="analista"):
        self.id, self.nome, self.email, self.gestor = id, nome, email, gestor
        self.telefone, self.tipo, self.grupo = telefone, tipo, grupo

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

print("\n=== 3. alcance: responsável e supervisor, e mais ninguém por padrão ===")
diretor = U(1, "Diretor", "diretor@bps4.com", telefone="21988880001")
gerente = U(2, "Gerente", "gerente@bps4.com", gestor=diretor, telefone="21988880002")
analista = U(3, "Analista", "analista@bps4.com", gestor=gerente, telefone="(21) 98888-0003")
sup = U(4, "Supervisor", "sup@bps4.com", telefone="21988880004")
cli = E("Mark Building", email="fin@mark.com", telefone="5521977770000")

# O padrão: só quem executa e quem supervisiona.
d = destinatarios_alerta(T([analista], sup, cli))
trio = [(x["papel"], x["canal"], x["endereco"]) for x in d]
check("colaborador vai por WhatsApp", ("colaborador", "whatsapp", "5521988880003") in trio, str(trio))
check("supervisor por WhatsApp", ("supervisor", "whatsapp", "5521988880004") in trio)
check("só esses dois", len(d) == 2, f"({len(d)})")
check("gestor NÃO entra por padrão", not any(x["papel"] == "gestor" for x in d))
check("empresa NÃO entra por padrão", not any(x["papel"] == "empresa" for x in d))
check("nenhum e-mail: todo mundo tem número", [x for x in d if x["canal"] == "email"] == [])

# Os dois alargamentos, quando ligados na tela.
d = destinatarios_alerta(T([analista], sup, cli), {}, niveis=2)
papeis = [x["papel"] for x in d]
check("com níveis=2, os dois gestores entram", papeis.count("gestor") == 2, str(papeis))
check("mas a empresa continua fora", "empresa" not in papeis)

d = destinatarios_alerta(T([analista], sup, cli), {}, 0, incluir_cliente=True)
trio = [(x["papel"], x["canal"], x["endereco"]) for x in d]
check("com a empresa ligada, ela recebe por WhatsApp", ("empresa", "whatsapp", "5521977770000") in trio)
check("e também por e-mail", ("empresa", "email", "fin@mark.com") in trio)
check("sem trazer gestor junto", not any(x["papel"] == "gestor" for x in d))

print("\n=== 3b. o número vem dos CONTATOS do Zap, casado pelo e-mail ===")
# Contact tem number e email; User tem email e id, mas NÃO tem telefone.
contatos = [
    {"id": 7, "name": "Analista", "email": "ANALISTA@bps4.com", "number": "21977771111"},
    {"id": 8, "name": "Bloqueado", "email": "bloq@bps4.com", "number": "21977772222", "blocked": True},
    {"id": 9, "name": "Sem Numero", "email": "semnum@bps4.com"},
    {"id": 10, "name": "Sem Email", "number": "21977773333"},
    "linha inválida",
]
num = mapa_numero_por_email(contatos)
check("e-mail vira chave em minúsculas", "analista@bps4.com" in num, str(num))
check("contato bloqueado fica de fora", "bloq@bps4.com" not in num)
check("contato sem número fica de fora", "semnum@bps4.com" not in num)
check("contato sem e-mail fica de fora", len(num) == 1)
check("lista vazia ou nula não quebra", mapa_numero_por_email([]) == {} and mapa_numero_por_email(None) == {})

usuarios = [
    {"id": 3, "name": "Analista", "email": "analista@bps4.com", "enabled": True},
    {"id": 4, "name": "Desligado", "email": "off@bps4.com", "enabled": False},
    {"id": 5, "name": "Sem Email", "enabled": True},
    {"id": 6, "name": "Legado", "email": "legado@bps4.com"},
]
uid = mapa_userid_por_email(usuarios)
check("atendente ativo entra", uid.get("analista@bps4.com") == 3, str(uid))
check("atendente desabilitado fica de fora", "off@bps4.com" not in uid)
check("sem e-mail fica de fora", "5" not in str(uid.values()))
check("sem o campo enabled é tratado como ativo", uid.get("legado@bps4.com") == 6)

zap = {"numero": num, "user_id": uid}

# O número do Zap tem precedência sobre o telefone digitado no Tareffas, e o
# atendimento nasce na conta do atendente.
d = destinatarios_alerta(T([analista], None, None), {}, 0, zap=zap)
check("o número do contato do Zap vence o do cadastro local",
      (d[0]["canal"], d[0]["endereco"]) == ("whatsapp", "5521977771111"), str(d))
check("vai com o userId do atendente", d[0].get("zap_user_id") == 3)

# Quem não está nos contatos cai no telefone local — e sem userId.
d = destinatarios_alerta(T([sup], None, None), {}, 0, zap=zap)
check("quem não é contato usa o telefone do Tareffas", d[0]["endereco"] == "5521988880004")
check("e vai sem userId, porque não é atendente lá", "zap_user_id" not in d[0])

# E-mail com grafia diferente não casa: cai na reserva.
outro_email = U(40, "Grafia Diferente", "analista@BPS4.com.br")
d = destinatarios_alerta(T([outro_email], None, None), {}, 0, zap=zap)
check("domínio diferente não casa e cai no e-mail", d[0]["canal"] == "email")
check("destinatário por e-mail nunca leva userId", "zap_user_id" not in d[0])

# Cliente é contato, não atendente: nunca recebe atribuição de atendimento.
d = destinatarios_alerta(T([], None, cli), {}, 0, zap=zap, incluir_cliente=True)
check("empresa não leva userId", d and all("zap_user_id" not in x for x in d))

print("\n=== 4. e-mail é a reserva de quem não tem telefone ===")
semtel = U(7, "Sem Telefone", "semtel@bps4.com")
d = destinatarios_alerta(T([semtel], None, None), {}, 0)
check("cai no e-mail em vez de não avisar", (d[0]["canal"], d[0]["endereco"]) == ("email", "semtel@bps4.com"))
sonome = U(8, "Sem Nada")
check("sem telefone e sem e-mail fica de fora", destinatarios_alerta(T([sonome], None, None), {}, 0) == [])
lixo = U(11, "Telefone Podre", "podre@bps4.com", telefone="1234")
d = destinatarios_alerta(T([lixo], None, None), {}, 0)
check("telefone impossível não vira WhatsApp — usa o e-mail", d[0]["canal"] == "email")

print("\n=== 4b. usuário do lado do cliente recebe pelos DOIS canais ===")
# Ele está fora do escritório, não abre o painel, e não tem supervisor de rede.
cliente_u = U(50, "Dona da Empresa", "dona@markbuilding.com",
              telefone="21966665555", tipo="cliente", grupo="cliente")
d = destinatarios_alerta(T([cliente_u], None, None))
canais = sorted(x["canal"] for x in d)
check("recebe por WhatsApp e por e-mail", canais == ["email", "whatsapp"], str(canais))
check("marcado como cliente", all(x["papel"] == "cliente" for x in d), str([x["papel"] for x in d]))
check("colaborador continua com um canal só",
      len(destinatarios_alerta(T([analista], None, None))) == 1)

# As duas convenções de marcação, cada uma sozinha.
check("tipo=cliente basta", eh_cliente(U(51, "A", "a@x.com", tipo="cliente", grupo="analista")))
check("grupo=cliente basta", eh_cliente(U(52, "B", "b@x.com", tipo="colaborador", grupo="cliente")))
check("colaborador comum não é cliente", not eh_cliente(analista))
check("maiúscula e espaço não enganam", eh_cliente(U(53, "C", "c@x.com", tipo=" Cliente ")))
check("usuário sem os campos não quebra", not eh_cliente(type("V", (), {"nome": "x"})()))

# Cliente sem um dos dois cai no que tem.
so_zap_u = U(54, "Só Zap", None, telefone="21966664444", tipo="cliente")
check("cliente sem e-mail vai só no WhatsApp",
      [x["canal"] for x in destinatarios_alerta(T([so_zap_u], None, None))] == ["whatsapp"])
so_mail_u = U(55, "Só E-mail", "so@x.com", tipo="cliente")
check("cliente sem telefone vai só no e-mail",
      [x["canal"] for x in destinatarios_alerta(T([so_mail_u], None, None))] == ["email"])

# Cliente não é atendente do Zap: não pode levar atribuição de atendimento.
zap_com_cliente = {"numero": {"dona@markbuilding.com": "5521966665555"},
                   "user_id": {"dona@markbuilding.com": 99}}
d = destinatarios_alerta(T([cliente_u], None, None), {}, 0, zap=zap_com_cliente)
check("cliente nunca leva userId, mesmo constando como atendente",
      all("zap_user_id" not in x for x in d))

# Cliente como responsável não tem supervisor — e o alerta não inventa um.
d = destinatarios_alerta(T([cliente_u], None, None))
check("nenhum supervisor aparece do nada", not any(x["papel"] == "supervisor" for x in d))

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
canais = [x["canal"] for x in destinatarios_alerta(T([], None, so_email), {}, 0, incluir_cliente=True)]
check("empresa sem telefone não gera WhatsApp", canais == ["email"], str(canais))
so_zap = E("Só Zap", telefone="21977776666")
canais = [x["canal"] for x in destinatarios_alerta(T([], None, so_zap), {}, 0, incluir_cliente=True)]
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
d = destinatarios_alerta(T([dono], None, emp), {}, 0, incluir_cliente=True)
end = [x["endereco"] for x in d]
check("nenhum endereço repetido", len(end) == len(set(end)), str(end))
check("o mesmo número não recebe duas vezes", end.count("5521955554444") == 1)

print("\n" + ("TUDO VERDE" if ok else "VERMELHO") + "\n")
sys.exit(0 if ok else 1)
