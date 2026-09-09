"""Prova da Fase 9: vários responsáveis por (empresa, setor), e a validação que
a rota não tinha.

Até aqui o par (empresa, setor) tinha UM dono, e o PUT gravava `setor_id` e
`responsavel_id` direto do corpo, sem conferir se aquilo existia. Com N ids na
mesma requisição isso piora: um número inventado no meio da lista entrava no
banco como chave estrangeira apontando para o vazio.

Duas coisas se provam aqui, e a segunda é a que importa mais:

1. a lista grava, volta na ordem, e o PRINCIPAL é sempre o primeiro dela;
2. id de setor, id de pessoa, pessoa do tipo cliente, pessoa bloqueada, lista
   acima do teto e campo inventado no corpo são recusados ANTES de qualquer
   gravação, com 404 e nunca 403 (`Padrao_IDOR`).

    cd backend && ./venv/bin/python provas/prova_responsaveis_multiplos.py

Roda contra as rotas reais, num SQLite temporário, e não deixa arquivo para
trás. Tirando a checagem de elegibilidade da rota, os itens 6 a 11 falham.
"""

from __future__ import annotations  # produção é 3.12, a máquina local é 3.9

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_resp_mult_")
_banco = os.path.join(_tmp, "prova.db")

# Precisam existir ANTES de importar o app: `database.py` lê a URL no import.
os.environ["DATABASE_URL"] = f"sqlite:///{_banco}"
os.environ["SECRET_KEY"] = "chave-jwt-de-teste"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                        # noqa: E402
from sqlalchemy import event                                     # noqa: E402

from app.database import Base, engine, SessionLocal              # noqa: E402


# O SQLite só checa chave estrangeira se mandarem, e produção é Postgres, que
# checa sempre. Sem este PRAGMA a prova roda num banco mais permissivo que o
# real e a linha órfã na tabela do meio passaria despercebida.
@event.listens_for(engine, "connect")
def _liga_fk(dbapi_con, _rec):
    dbapi_con.execute("PRAGMA foreign_keys=ON")

from app.models import (Usuario, Empresa, Setor,                 # noqa: E402
                        EmpresaSetorResponsavel,
                        empresa_setor_resp_usuarios)
from app.auth import get_password_hash                           # noqa: E402
from app.routes.empresas import MAX_RESP_POR_SETOR               # noqa: E402
from app.main import app                                         # noqa: E402

Base.metadata.create_all(bind=engine)
cliente = TestClient(app)

SENHA = "senha-boa-123"
IDS = {}


def semear():
    db = SessionLocal()
    try:
        emp = Empresa(razao_social="Cliente Alfa", cnpj="11222333000181")
        db.add(emp)
        db.flush()
        IDS["empresa"] = emp.id

        for chave, nome in (("fiscal", "Fiscal"), ("contabil", "Contábil")):
            s = Setor(nome=nome, ativo=True)
            db.add(s)
            db.flush()
            IDS[chave] = s.id
        inativo = Setor(nome="Setor Desativado", ativo=False)
        db.add(inativo)
        db.flush()
        IDS["setor_inativo"] = inativo.id

        pessoas = [
            ("admin", "admin@bps4.com.br", "admin", "colaborador", False, True),
            ("ana", "ana@bps4.com.br", "analista", "colaborador", False, True),
            ("bruno", "bruno@bps4.com.br", "analista", "colaborador", False, True),
            ("carla", "carla@bps4.com.br", "analista", "colaborador", False, True),
            ("bloqueada", "bloq@bps4.com.br", "analista", "colaborador", True, True),
            ("do_cliente", "cli@alfa.com.br", "consulta", "cliente", False, True),
        ]
        for chave, email, grupo, tipo, bloqueado, ativo in pessoas:
            u = Usuario(nome=chave.title(), email=email, grupo=grupo, tipo=tipo,
                        bloqueado=bloqueado, ativo=ativo,
                        senha_hash=get_password_hash(SENHA))
            db.add(u)
            db.flush()
            IDS[chave] = u.id
        db.commit()
    finally:
        db.close()


semear()

r = cliente.post("/api/auth/login",
                 json={"email": "admin@bps4.com.br", "senha": SENHA})
CAB = {"Authorization": "Bearer " + r.json()["access_token"]}


def gravar(itens):
    return cliente.put(f"/api/empresas/{IDS['empresa']}/responsaveis-setor",
                       json={"itens": itens}, headers=CAB)


def ler(setor_chave="fiscal"):
    r = cliente.get(f"/api/empresas/{IDS['empresa']}/responsaveis-setor", headers=CAB)
    for linha in r.json():
        if linha["setor_id"] == IDS[setor_chave]:
            return linha
    return None


def linhas_da_associativa():
    db = SessionLocal()
    try:
        return db.query(empresa_setor_resp_usuarios).count()
    finally:
        db.close()


def principal_no_banco(setor_chave="fiscal"):
    db = SessionLocal()
    try:
        v = (db.query(EmpresaSetorResponsavel)
             .filter(EmpresaSetorResponsavel.empresa_id == IDS["empresa"],
                     EmpresaSetorResponsavel.setor_id == IDS[setor_chave]).first())
        return v.responsavel_id if v else None
    finally:
        db.close()


falhou = []


def checa(n, descricao, condicao, extra=""):
    if condicao:
        print(f"  ok  {n:>2}. {descricao}")
    else:
        print(f"FALHA  {n:>2}. {descricao}" + (f"   {extra}" if extra else ""))
        falhou.append(n)


print("PROVA FASE 9 (vários responsáveis por empresa e setor)")

# 1. PROVA POSITIVA. Sem ela, uma rota que recusasse tudo passaria no resto.
r = gravar([{"setor_id": IDS["fiscal"],
             "responsavel_ids": [IDS["ana"], IDS["bruno"]]}])
checa(1, "o par (empresa, setor) grava dois responsáveis",
      r.status_code == 200, f"({r.status_code} {r.text[:120]})")

# 2. A ordem volta como foi mandada. Sem isso, "o primeiro da lista" não
#    significa nada, porque o primeiro mudaria a cada leitura.
checa(2, "o GET devolve a lista na ordem escolhida",
      ler()["responsavel_ids"] == [IDS["ana"], IDS["bruno"]],
      f"({ler()['responsavel_ids']})")

# 3. O principal é o primeiro, e mora no campo antigo.
checa(3, "responsavel_id continua saindo, e vale o primeiro da lista",
      ler()["responsavel_id"] == IDS["ana"] and principal_no_banco() == IDS["ana"])

# 4. Trocar a ordem troca o principal. É a regra 3 do LASTRO, e é o que
#    impede o campo antigo de virar uma segunda verdade parada no tempo.
gravar([{"setor_id": IDS["fiscal"], "responsavel_ids": [IDS["bruno"], IDS["ana"]]}])
checa(4, "inverter a lista inverte o principal",
      ler()["responsavel_id"] == IDS["bruno"] and principal_no_banco() == IDS["bruno"],
      f"({ler()['responsavel_id']})")

# 5. O formato antigo, de um só, continua salvando. A tela ainda manda assim
#    até a fase 11, e quebrar isso deixaria o cadastro inteiro sem gravar.
gravar([{"setor_id": IDS["fiscal"], "responsavel_id": IDS["carla"]}])
checa(5, "o corpo antigo, com um responsável só, continua valendo",
      ler()["responsavel_ids"] == [IDS["carla"]] and ler()["responsavel_id"] == IDS["carla"])

# 6. Id de pessoa que não existe. Antes desta fase entrava no banco.
antes = ler()["responsavel_ids"]
r = gravar([{"setor_id": IDS["fiscal"], "responsavel_ids": [IDS["ana"], 999_999]}])
checa(6, "id de pessoa inexistente é recusado", r.status_code == 404,
      f"({r.status_code})")

# 7. Pessoa do tipo cliente não é analista de setor nenhum: ela é de fora.
r2 = gravar([{"setor_id": IDS["fiscal"], "responsavel_ids": [IDS["do_cliente"]]}])
checa(7, "usuário do tipo cliente é recusado", r2.status_code == 404,
      f"({r2.status_code})")

# 8. Bloqueado não recebe tarefa, então não entra na matriz.
r3 = gravar([{"setor_id": IDS["fiscal"], "responsavel_ids": [IDS["bloqueada"]]}])
checa(8, "usuário bloqueado é recusado", r3.status_code == 404, f"({r3.status_code})")

# 9. Setor inexistente e setor inativo, pelo mesmo caminho.
r4 = gravar([{"setor_id": 999_999, "responsavel_ids": [IDS["ana"]]}])
r5 = gravar([{"setor_id": IDS["setor_inativo"], "responsavel_ids": [IDS["ana"]]}])
checa(9, "setor inexistente e setor inativo são recusados",
      r4.status_code == 404 and r5.status_code == 404,
      f"({r4.status_code}, {r5.status_code})")

# 10. Nenhuma recusa pode devolver 403: 403 confirma que o recurso existe
#     (Padrao_IDOR, anti-padrões). E a mensagem tem que ser a MESMA para id que
#     não existe e para id que existe mas não serve, senão o texto vira um
#     oráculo: quem varre ids descobre quem é do sistema pela resposta.
recusas = {r.status_code, r2.status_code, r3.status_code, r4.status_code, r5.status_code}
motivos = {x.json().get("detail") for x in (r, r2, r3)}
checa(10, "recusa é 404, e a mensagem não diz se o id existe ou só não serve",
      recusas == {404} and len(motivos) == 1, f"({recusas}, {motivos})")

# 11. E o mais importante: recusar não pode ter gravado metade. A validação
#     roda ANTES do delete, então a matriz continua como estava.
checa(11, "recusa não altera o que já estava gravado",
      ler()["responsavel_ids"] == antes, f"({ler()['responsavel_ids']} vs {antes})")

# 12. Id repetido colapsa em vez de derrubar o salvamento.
gravar([{"setor_id": IDS["fiscal"],
         "responsavel_ids": [IDS["ana"], IDS["bruno"], IDS["ana"]]}])
checa(12, "id repetido colapsa, mantendo a primeira posição",
      ler()["responsavel_ids"] == [IDS["ana"], IDS["bruno"]],
      f"({ler()['responsavel_ids']})")

# 13. Teto de tamanho da lista. Sem ele, um corpo com 100 mil ids faz a rota
#     consultar e gravar até cair.
r = gravar([{"setor_id": IDS["fiscal"],
             "responsavel_ids": [IDS["ana"]] * (MAX_RESP_POR_SETOR + 1)}])
checa(13, f"lista acima de {MAX_RESP_POR_SETOR} é recusada",
      r.status_code == 422, f"({r.status_code})")

# 14. Whitelist do corpo: campo que não foi declarado não passa (Mass Assignment).
r = gravar([{"setor_id": IDS["fiscal"], "responsavel_ids": [IDS["ana"]],
             "responsavel_id_extra": 1, "atende": True}])
checa(14, "campo inventado no corpo é recusado", r.status_code == 422,
      f"({r.status_code})")

# 15. Regravar não deixa órfão na tabela do meio. `query().delete()` é DELETE em
#     massa e não passa pelo ORM: sem a limpeza explícita, cada salvamento
#     empilharia linhas apontando para vínculo que já morreu.
gravar([{"setor_id": IDS["fiscal"], "responsavel_ids": [IDS["ana"], IDS["bruno"]]},
        {"setor_id": IDS["contabil"], "responsavel_ids": [IDS["carla"]]}])
gravar([{"setor_id": IDS["fiscal"], "responsavel_ids": [IDS["carla"]]}])
checa(15, "regravar não deixa linha órfã na tabela do meio",
      linhas_da_associativa() == 1, f"({linhas_da_associativa()} linhas)")

# 16. Setor sem ninguém continua sendo "atende, mas sem dono ainda".
gravar([{"setor_id": IDS["fiscal"], "responsavel_ids": []}])
linha = ler()
checa(16, "setor sem responsável continua marcado como atendido",
      linha["atende"] is True and linha["responsavel_ids"] == []
      and linha["responsavel_id"] is None)

# 17. Apagar a EMPRESA não pode deixar linha pendurada na tabela do meio. O
#     cascade do ORM chega até o vínculo, mas as linhas daqui já não estão
#     carregadas nesse ponto: quem fecha isso é o ON DELETE CASCADE do banco.
gravar([{"setor_id": IDS["fiscal"], "responsavel_ids": [IDS["ana"], IDS["bruno"]]}])
r = cliente.delete(f"/api/empresas/{IDS['empresa']}", headers=CAB)
checa(17, "apagar a empresa não deixa linha órfã na tabela do meio",
      r.status_code == 200 and linhas_da_associativa() == 0,
      f"({r.status_code}, {linhas_da_associativa()} linhas)")

# 18. Quem responde por um setor tem vínculo, então é INATIVADO e não apagado.
#     Vale para o secundário também: com vários responsáveis, ele não aparece
#     em `responsavel_id`, e sem contar a lista ele seria apagado em silêncio.
db = SessionLocal()
try:
    nova_emp = Empresa(razao_social="Cliente Beta", cnpj="99888777000166")
    db.add(nova_emp)
    db.flush()
    IDS["empresa"] = nova_emp.id
    db.commit()
finally:
    db.close()
gravar([{"setor_id": IDS["fiscal"], "responsavel_ids": [IDS["ana"], IDS["bruno"]]}])
r_princ = cliente.delete(f"/api/usuarios/{IDS['ana']}", headers=CAB)
r_seg = cliente.delete(f"/api/usuarios/{IDS['bruno']}", headers=CAB)
checa(18, "responsável de setor é inativado, nunca apagado, principal ou não",
      r_princ.json().get("inativado") is True and r_seg.json().get("inativado") is True,
      f"({r_princ.json()}, {r_seg.json()})")

# 19. E a matriz continua de pé depois disso: ninguém virou id pendurado.
checa(19, "a matriz sobrevive à inativação, sem id apontando para o vazio",
      ler()["responsavel_ids"] == [IDS["ana"], IDS["bruno"]],
      f"({ler()['responsavel_ids']})")

print()
if falhou:
    print(f"HOUVE FALHA nos itens {falhou}")
    sys.exit(1)
print("TODAS AS PROVAS PASSARAM")
sys.exit(0)
