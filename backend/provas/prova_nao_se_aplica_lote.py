"""Prova da Fase 35: "Não se aplica a esta empresa" vale para a obrigação inteira.

Até aqui a rota marcava UMA tarefa e criava a exceção. As outras tarefas em
aberto da mesma obrigação e da mesma empresa, de outras competências, ficavam
penduradas: o print da Trops mostrava a mesma obrigação atrasada em vários
meses, e cancelar uma não tirava as outras. E bastava `tarefas: editar` para
decidir que uma obrigação não se aplica ao cliente, decisão que muda a geração
dos meses seguintes. O usuário decidiu (2026-09-18): só quem tem a flag
`alocar_obrigacao`, e as abertas saem junto, com motivo, autor e data.

    cd backend && ./venv/bin/python provas/prova_nao_se_aplica_lote.py

Mede o banco e o stdout de verdade, num SQLite temporário.
"""

from __future__ import annotations  # produção é 3.12, a máquina local é 3.9

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_nao_se_aplica_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp, 'prova.db')}"
os.environ["SECRET_KEY"] = "chave-jwt-de-teste"
os.environ["ZOARIA_SSO_SECRET"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                          # noqa: E402

from app.auth import get_password_hash                             # noqa: E402
from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import (Empresa, Obrigacao, ObrigacaoExcecao,      # noqa: E402
                        StatusTarefa, Tarefa, Usuario)
from app.main import app                                           # noqa: E402
from app.services.gerador import gerar_tarefas                     # noqa: E402

Base.metadata.create_all(bind=engine)
cliente = TestClient(app)
SENHA = "senha-boa-123"
MESES = "1,2,3,4,5,6,7,8,9,10,11,12"
MOTIVO = "Beta não é contribuinte de IPI."
ids = {}
falhou = []


def checa(n, descricao, condicao, extra=""):
    print(("  ok  " if condicao else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  {extra}" if extra else ""))
    if not condicao:
        falhou.append(n)


def capturar(funcao):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        retorno = funcao()
    linhas = []
    for bruta in buffer.getvalue().splitlines():
        bruta = bruta.strip()
        if bruta.startswith("{"):
            try:
                linhas.append(json.loads(bruta))
            except json.JSONDecodeError:
                pass
    return retorno, linhas


def entrar(email):
    r = cliente.post("/api/auth/login", json={"email": email, "senha": SENHA})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def tarefa(obrigacao, empresa, mes):
    db = SessionLocal()
    try:
        return (db.query(Tarefa)
                .filter(Tarefa.obrigacao_id == ids[obrigacao],
                        Tarefa.empresa_id == ids[empresa],
                        Tarefa.competencia == f"{mes:02d}/2026").first())
    finally:
        db.close()


def estado():
    """Fotografia (status, nao_se_aplica) de toda tarefa, por id."""
    db = SessionLocal()
    try:
        return {t.id: (t.status, bool(t.nao_se_aplica)) for t in db.query(Tarefa).all()}
    finally:
        db.close()


# ------------------------------------------------------------------ cenário
db = SessionLocal()
admin = Usuario(nome="Chefe", email="chefe@bps4.com.br", grupo="admin",
                senha_hash=get_password_hash(SENHA), ativo=True)
analista = Usuario(nome="Ana", email="ana@bps4.com.br", grupo="analista",
                   senha_hash=get_password_hash(SENHA), ativo=True)
# Gestor COM a flag e de escopo reduzido: o único jeito de medir que a flag
# nova não abriu o escopo. O preset de gestor tem `todas`; o override reduz.
gestor = Usuario(nome="Gil", email="gil@bps4.com.br", grupo="gestor",
                 permissoes=json.dumps({"escopo_tarefas": "proprias"}),
                 senha_hash=get_password_hash(SENHA), ativo=True)
db.add_all([admin, analista, gestor])
alfa = Empresa(razao_social="ALFA SERVICOS LTDA", cnpj="11222333000181",
               regime_tributario="lucro_real", ativo=True)
beta = Empresa(razao_social="BETA COMERCIO LTDA", cnpj="44555666000172",
               regime_tributario="lucro_real", ativo=True)
db.add_all([alfa, beta])
db.commit()
ipi = Obrigacao(nome="Apuração de IPI", ativa=True, meses_ativos=MESES,
                regra_prazo_tipo="ultimo_dia_util", competencia_ref="mesmo_mes")
ecf = Obrigacao(nome="ECF", ativa=True, meses_ativos=MESES,
                regra_prazo_tipo="ultimo_dia_util", competencia_ref="mesmo_mes")
db.add_all([ipi, ecf])
db.commit()
ids.update(admin=admin.id, analista=analista.id, alfa=alfa.id, beta=beta.id,
           ipi=ipi.id, ecf=ecf.id)
db.close()

db = SessionLocal()
for mes in (6, 7, 8, 9, 10):
    gerar_tarefas(db, mes, 2026)
db.close()

# Beta x IPI, uma competência por situação: 6 cancelada à mão, 7 concluída,
# 8 em andamento, 9 pendente (a clicada), 10 atrasada.
situacoes = {6: StatusTarefa.CANCELADA, 7: StatusTarefa.CONCLUIDA,
             8: StatusTarefa.EM_ANDAMENTO, 9: StatusTarefa.PENDENTE,
             10: StatusTarefa.ATRASADA}
db = SessionLocal()
for mes, st in situacoes.items():
    t = (db.query(Tarefa).filter(Tarefa.obrigacao_id == ids["ipi"],
                                 Tarefa.empresa_id == ids["beta"],
                                 Tarefa.competencia == f"{mes:02d}/2026").first())
    t.status = st
    if mes == 9:
        t.responsavel_id = ids["analista"]     # no escopo da analista
db.commit()
db.close()

alvo = tarefa("ipi", "beta", 9)
checa(1, "cenário: 5 competências de Beta x IPI, e as tarefas de Alfa e de ECF",
      alvo is not None and len(estado()) == 20, f"({len(estado())} tarefas)")

adm_h = entrar("chefe@bps4.com.br")
ana_h = entrar("ana@bps4.com.br")
gil_h = entrar("gil@bps4.com.br")

# ------------------------------------------------ (a) sem a flag, 403 e nada muda
antes = estado()
r = cliente.post(f"/api/tarefas/{alvo.id}/nao-se-aplica", headers=ana_h,
                 json={"motivo": MOTIVO})
db = SessionLocal()
n_exc = db.query(ObrigacaoExcecao).count()
db.close()
checa(2, "analista (tarefas: editar, sem alocar_obrigacao) recebe 403, e nada muda",
      r.status_code == 403 and estado() == antes and n_exc == 0,
      f"({r.status_code}, exceções {n_exc})")

# ------------------------------------------------ (b) a clicada
r, linhas = capturar(lambda: cliente.post(f"/api/tarefas/{alvo.id}/nao-se-aplica",
                                          headers=adm_h, json={"motivo": MOTIVO}))
t9 = tarefa("ipi", "beta", 9)
checa(3, "com a flag, a clicada vai para cancelada com motivo, autor e data",
      r.status_code == 200 and t9.status == StatusTarefa.CANCELADA
      and t9.nao_se_aplica and t9.nao_se_aplica_motivo == MOTIVO
      and t9.nao_se_aplica_por_id == ids["admin"] and t9.nao_se_aplica_em is not None,
      f"({r.status_code} {t9.status})")

# ------------------------------------------------ (c) as irmãs abertas
irmas = [tarefa("ipi", "beta", m) for m in (8, 10)]
checa(4, "as abertas de outras competências (em andamento e atrasada) saem junto",
      all(t.status == StatusTarefa.CANCELADA and t.nao_se_aplica for t in irmas),
      f"({[(t.competencia, t.status.value, t.nao_se_aplica) for t in irmas]})")
checa(5, "e com o mesmo motivo, o mesmo autor e data",
      all(t.nao_se_aplica_motivo == MOTIVO and t.nao_se_aplica_por_id == ids["admin"]
          and t.nao_se_aplica_em is not None for t in irmas))

# ------------------------------------------------ (d) o que NÃO pode mudar
t7, t6 = tarefa("ipi", "beta", 7), tarefa("ipi", "beta", 6)
checa(6, "a concluída da mesma obrigação e empresa não muda",
      t7.status == StatusTarefa.CONCLUIDA and not t7.nao_se_aplica)
checa(7, "a cancelada à mão antes continua sem a marca de não se aplica",
      t6.status == StatusTarefa.CANCELADA and not t6.nao_se_aplica)
depois = estado()
outras = [i for i in antes
          if i not in {tarefa("ipi", "beta", m).id for m in (6, 7, 8, 9, 10)}]
checa(8, "tarefa de outra empresa ou de outra obrigação não muda",
      all(depois[i] == antes[i] for i in outras) and len(outras) == 15,
      f"({len(outras)} conferidas)")

# ------------------------------------------------ (e) exceção e geração seguinte
db = SessionLocal()
excs = [(x.obrigacao_id, x.empresa_id) for x in db.query(ObrigacaoExcecao).all()]
r11 = gerar_tarefas(db, 11, 2026)
db.close()
checa(9, "a exceção nasce uma vez só, para Beta x IPI",
      excs == [(ids["ipi"], ids["beta"])], f"({excs})")
checa(10, "a geração seguinte não cria Beta x IPI, e cria as outras três",
      tarefa("ipi", "beta", 11) is None and r11["criadas"] == 3,
      f"(criadas {r11['criadas']})")

# ------------------------------------------------ (f) o rastro
edicoes = [l for l in linhas if l.get("event") == "EDICAO_REGISTRO_CRITICO"
           and l.get("tabela") == "tarefa"]
e = edicoes[0] if edicoes else {}
checa(11, "UMA linha EDICAO_REGISTRO_CRITICO de tarefa, em lote, acao nao_se_aplica",
      len(edicoes) == 1 and e.get("lote") is True and e.get("acao") == "nao_se_aplica",
      f"({len(edicoes)} linhas)")
checa(12, "com a contagem de canceladas (3), obrigação, empresa e o usuário",
      bool(e) and e.get("canceladas") == 3 and e.get("obrigacao_id") == ids["ipi"]
      and e.get("empresa_id") == ids["beta"] and e.get("user_id") == ids["admin"],
      f"({ {k: e.get(k) for k in ('canceladas', 'obrigacao_id', 'empresa_id', 'user_id')} })")
checa(13, "sem razão social nem CNPJ na linha",
      bool(e) and "BETA" not in json.dumps(e) and "44555666000172" not in json.dumps(e))
checa(14, "a linha de criação da exceção continua saindo",
      any(l.get("event") == "CRIACAO_REGISTRO_CRITICO"
          and l.get("tabela") == "obrigacao_excecao" for l in linhas))

# ------------------------------------------------ (g) não-regressão
db = SessionLocal()
avulsa = Tarefa(titulo="avulsa", empresa_id=ids["alfa"], status=StatusTarefa.PENDENTE)
db.add(avulsa)
db.commit()
avulsa_id = avulsa.id
db.close()
r = cliente.post(f"/api/tarefas/{avulsa_id}/nao-se-aplica", headers=adm_h,
                 json={"motivo": "qualquer coisa"})
checa(15, "tarefa avulsa continua 422", r.status_code == 422, f"({r.status_code})")
fora = tarefa("ecf", "alfa", 9)
r = cliente.post(f"/api/tarefas/{fora.id}/nao-se-aplica", headers=gil_h,
                 json={"motivo": "não se aplica"})
checa(16, "gestor com a flag e escopo reduzido: tarefa fora do escopo continua 404",
      r.status_code == 404 and tarefa("ecf", "alfa", 9).status == StatusTarefa.PENDENTE,
      f"({r.status_code})")
r = cliente.post(f"/api/tarefas/{fora.id}/nao-se-aplica", headers=adm_h,
                 json={"motivo": "x"})
checa(17, "motivo com menos de 3 letras continua 422", r.status_code == 422,
      f"({r.status_code})")

# ------------------------------------------------ (h) o log não afirma o que não houve
# Segunda chamada na mesma tarefa: a exceção já existe e nada está em aberto.
# Achado do verificador funcional: o log dizia CRIACAO de uma exceção que o
# banco não criou, e 'canceladas' contava a clicada, que já estava cancelada.
r, linhas2 = capturar(lambda: cliente.post(f"/api/tarefas/{alvo.id}/nao-se-aplica",
                                           headers=adm_h, json={"motivo": MOTIVO}))
criacoes2 = [l for l in linhas2 if l.get("event") == "CRIACAO_REGISTRO_CRITICO"
             and l.get("tabela") == "obrigacao_excecao"]
edicoes2 = [l for l in linhas2 if l.get("event") == "EDICAO_REGISTRO_CRITICO"
            and l.get("tabela") == "tarefa"]
checa(18, "repetir a chamada responde 200 e NÃO loga criação de exceção que já existia",
      r.status_code == 200 and criacoes2 == [], f"({r.status_code}, {len(criacoes2)} linhas)")
checa(19, "e a linha de lote diz canceladas=0, porque nada estava em aberto",
      len(edicoes2) == 1 and edicoes2[0].get("canceladas") == 0,
      f"({[l.get('canceladas') for l in edicoes2]})")

print()
if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("PROVA OK: 19 checagens verdes")
