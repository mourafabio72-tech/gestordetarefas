"""Prova da Fase 36: o Desvincular escolhe as obrigações e respeita a regra.

Até aqui o Desvincular só tirava o vínculo à mão. A obrigação alcança a empresa
pela regra de regime e segmento OU pelo vínculo, e regra em branco quer dizer
todas: tirar o vínculo de uma obrigação que alcança pela regra não mudava
nada, e o usuário viu isso como "não está acatando". Também tirava a empresa de
TODAS de uma vez, e deixava as tarefas já geradas em aberto.

O usuário decidiu (2026-09-18): escolhe a empresa e marca as obrigações; as
tarefas em aberto saem junto, como "não se aplica"; só com `alocar_obrigacao`;
motivo obrigatório, um para o lote.

    cd backend && ./venv/bin/python provas/prova_desvincular_regra.py

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

_tmp = tempfile.mkdtemp(prefix="prova_desvincular_")
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
MOTIVO = "Beta é do comércio e não faz estas entregas."
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


def estado():
    """Fotografia de tudo que o desvincular pode mudar: tarefas, exceções e vínculos."""
    db = SessionLocal()
    try:
        tarefas = {t.id: (t.status, bool(t.nao_se_aplica)) for t in db.query(Tarefa).all()}
        excecoes = sorted((x.obrigacao_id, x.empresa_id)
                          for x in db.query(ObrigacaoExcecao).all())
        vinculos = sorted((o.id, e.id) for o in db.query(Obrigacao).all() for e in o.empresas)
        return tarefas, excecoes, vinculos
    finally:
        db.close()


def tarefas_de(obrigacao, empresa):
    db = SessionLocal()
    try:
        return (db.query(Tarefa)
                .filter(Tarefa.obrigacao_id == ids[obrigacao],
                        Tarefa.empresa_id == ids[empresa])
                .order_by(Tarefa.competencia).all())
    finally:
        db.close()


def desvincular(headers, corpo):
    return cliente.post("/api/obrigacoes/desvincular-empresa", headers=headers, json=corpo)


# ------------------------------------------------------------------ cenário
db = SessionLocal()
admin = Usuario(nome="Chefe", email="chefe@bps4.com.br", grupo="admin",
                senha_hash=get_password_hash(SENHA), ativo=True)
analista = Usuario(nome="Ana", email="ana@bps4.com.br", grupo="analista",
                   senha_hash=get_password_hash(SENHA), ativo=True)
# As duas pontas da guarda, por override (achado do verificador de evidência):
# a analista acima não tem NEM `obrigacoes: editar` NEM a flag, e cairia no 403
# de qualquer uma das duas guardas. Estas separam uma da outra.
edita = Usuario(nome="Edu", email="edu@bps4.com.br", grupo="analista",
                permissoes=json.dumps({"obrigacoes": "editar"}),
                senha_hash=get_password_hash(SENHA), ativo=True)
aloca = Usuario(nome="Alice", email="alice@bps4.com.br", grupo="analista",
                permissoes=json.dumps({"alocar_obrigacao": True}),
                senha_hash=get_password_hash(SENHA), ativo=True)
db.add_all([admin, analista, edita, aloca])
alfa = Empresa(razao_social="ALFA SERVICOS LTDA", cnpj="11222333000181",
               regime_tributario="lucro_real", ativo=True)
beta = Empresa(razao_social="BETA COMERCIO LTDA", cnpj="44555666000172",
               regime_tributario="lucro_real", ativo=True)
db.add_all([alfa, beta])
db.commit()


def obrig(nome, **kw):
    return Obrigacao(nome=nome, ativa=kw.pop("ativa", True), meses_ativos=MESES,
                     regra_prazo_tipo="ultimo_dia_util", competencia_ref="mesmo_mes", **kw)


# Uma obrigação por jeito de alcançar (ou de não alcançar) a Beta.
ipi = obrig("Apuração de IPI", aplica_regimes="lucro_real")           # pela regra
ecf = obrig("ECF")                                                     # regra vazia + vínculo = ambos
dirb = obrig("Entrega DIRB", aplica_regimes="simples_nacional")        # só pelo vínculo
excl = obrig("Relatório do cliente", alvo_modo="vinculadas")           # modo vinculadas, vinculada
inativa = obrig("Obrigação inativa", ativa=False)                      # regra vazia, mas inativa
simples = obrig("DAS", aplica_regimes="simples_nacional")              # não alcança
jaexc = obrig("DeSTDA")                                                # regra vazia, com exceção
vmodo = obrig("Só dos vinculados", alvo_modo="vinculadas")             # vinculadas, Beta fora
db.add_all([ipi, ecf, dirb, excl, inativa, simples, jaexc, vmodo])
db.commit()
ecf.empresas.append(beta)
dirb.empresas.append(beta)
excl.empresas.append(beta)
excl.empresas.append(alfa)
vmodo.empresas.append(alfa)
db.add(ObrigacaoExcecao(obrigacao_id=jaexc.id, empresa_id=beta.id,
                        motivo="decidido antes", decidido_por_id=admin.id))
db.commit()
ids.update(admin=admin.id, analista=analista.id, alfa=alfa.id, beta=beta.id,
           ipi=ipi.id, ecf=ecf.id, dirb=dirb.id, excl=excl.id, inativa=inativa.id,
           simples=simples.id, jaexc=jaexc.id, vmodo=vmodo.id)
db.close()

db = SessionLocal()
for mes in (8, 9, 10):
    gerar_tarefas(db, mes, 2026)
db.close()

# Beta x IPI: a de 08 concluída (não pode mudar, nem contar como aberta).
db = SessionLocal()
t = (db.query(Tarefa).filter(Tarefa.obrigacao_id == ids["ipi"],
                             Tarefa.empresa_id == ids["beta"],
                             Tarefa.competencia == "08/2026").first())
t.status = StatusTarefa.CONCLUIDA
db.commit()
db.close()

checa(1, "cenário: Beta tem 3 meses de IPI, ECF, DIRB e do relatório; nada de DAS nem DeSTDA",
      all(len(tarefas_de(o, "beta")) == 3 for o in ("ipi", "ecf", "dirb", "excl"))
      and not tarefas_de("simples", "beta") and not tarefas_de("jaexc", "beta")
      and not tarefas_de("inativa", "beta"))

adm_h = entrar("chefe@bps4.com.br")
ana_h = entrar("ana@bps4.com.br")

# ------------------------------------------------ (a) o alcance da empresa
r = cliente.get(f"/api/obrigacoes/alcance-empresa/{ids['beta']}", headers=adm_h)
lista = r.json() if r.status_code == 200 and isinstance(r.json(), list) else []
por_id = {x.get("id"): x for x in lista if isinstance(x, dict)}
esperadas = {ids[k] for k in ("ipi", "ecf", "dirb", "excl")}
checa(2, "alcance lista só as ativas que alcançam a Beta, sem a que já tem exceção",
      r.status_code == 200 and set(por_id) == esperadas,
      f"({r.status_code}, {sorted(por_id)} esperado {sorted(esperadas)})")
vias = {k: por_id.get(ids[k], {}).get("via") for k in ("ipi", "ecf", "dirb", "excl")}
checa(3, "cada uma diz por onde alcança: regra, ambos, vínculo e vínculo",
      vias == {"ipi": "regra", "ecf": "ambos", "dirb": "vinculo", "excl": "vinculo"},
      f"({vias})")
abertas = {k: por_id.get(ids[k], {}).get("abertas") for k in ("ipi", "ecf")}
checa(4, "e quantas tarefas em aberto tem ali (IPI 2, porque a de 08 está concluída; ECF 3)",
      abertas == {"ipi": 2, "ecf": 3}, f"({abertas})")

# ------------------------------------------------ (e) sem a flag, 403 nas duas
antes = estado()
r1 = cliente.get(f"/api/obrigacoes/alcance-empresa/{ids['beta']}", headers=ana_h)
r2 = desvincular(ana_h, {"empresa_id": ids["beta"], "obrigacao_ids": [ids["ipi"]],
                         "motivo": MOTIVO})
checa(5, "analista sem alocar_obrigacao: 403 no alcance e no desvincular, e nada muda",
      r1.status_code == 403 and r2.status_code == 403 and estado() == antes,
      f"({r1.status_code}, {r2.status_code})")

# ------------------------------------------------ (d) validação, tudo ou nada
casos = [
    (6, "lista vazia", {"empresa_id": ids["beta"], "obrigacao_ids": [], "motivo": MOTIVO}),
    (7, "id que não é número", {"empresa_id": ids["beta"], "obrigacao_ids": ["abc"],
                                "motivo": MOTIVO}),
    (8, "motivo com menos de 3 letras", {"empresa_id": ids["beta"],
                                         "obrigacao_ids": [ids["ipi"]], "motivo": "x"}),
    (9, "sem motivo", {"empresa_id": ids["beta"], "obrigacao_ids": [ids["ipi"]]}),
    (10, "campo a mais", {"empresa_id": ids["beta"], "obrigacao_ids": [ids["ipi"]],
                          "motivo": MOTIVO, "todas": True}),
    (11, "uma válida junto com uma que não alcança a Beta",
     {"empresa_id": ids["beta"], "obrigacao_ids": [ids["dirb"], ids["simples"]],
      "motivo": MOTIVO}),
    (12, "uma válida junto com uma que não existe",
     {"empresa_id": ids["beta"], "obrigacao_ids": [ids["dirb"], 99999], "motivo": MOTIVO}),
    (13, "uma válida junto com a que já tem exceção",
     {"empresa_id": ids["beta"], "obrigacao_ids": [ids["dirb"], ids["jaexc"]],
      "motivo": MOTIVO}),
]
for n, nome, corpo in casos:
    r = desvincular(adm_h, corpo)
    checa(n, f"{nome}: 422 e nada muda", r.status_code == 422 and estado() == antes,
          f"({r.status_code})")

# ------------------------------------------------ (b) desvincula três
r, linhas = capturar(lambda: desvincular(adm_h, {
    "empresa_id": ids["beta"], "obrigacao_ids": [ids["ipi"], ids["ecf"], ids["dirb"]],
    "motivo": MOTIVO}))
_, excecoes, vinculos = estado()
checa(14, "com a flag: 200", r.status_code == 200, f"({r.status_code} {r.text[:120]})")
checa(15, "exceção nasce para as que alcançam pela regra (IPI e ECF), e não para a DIRB",
      set(excecoes) == {(ids["jaexc"], ids["beta"]), (ids["ipi"], ids["beta"]),
                        (ids["ecf"], ids["beta"])}, f"({excecoes})")
checa(16, "o vínculo à mão sai da ECF e da DIRB; o do relatório fica",
      (ids["ecf"], ids["beta"]) not in vinculos and (ids["dirb"], ids["beta"]) not in vinculos
      and (ids["excl"], ids["beta"]) in vinculos, f"({vinculos})")
saidas = [t for o in ("ipi", "ecf", "dirb") for t in tarefas_de(o, "beta")
          if t.status != StatusTarefa.CONCLUIDA]
checa(17, "as 8 em aberto das três vão para cancelada, com motivo, autor e data",
      len(saidas) == 8 and all(t.status == StatusTarefa.CANCELADA and t.nao_se_aplica
                               and t.nao_se_aplica_motivo == MOTIVO
                               and t.nao_se_aplica_por_id == ids["admin"]
                               and t.nao_se_aplica_em is not None for t in saidas),
      f"({[(t.competencia, t.status.value, t.nao_se_aplica) for t in saidas]})")
concl = [t for t in tarefas_de("ipi", "beta") if t.competencia == "08/2026"]
checa(18, "a concluída não muda", concl and concl[0].status == StatusTarefa.CONCLUIDA
      and not concl[0].nao_se_aplica)
intocadas = tarefas_de("excl", "beta") + [t for o in ("ipi", "ecf", "excl", "vmodo")
                                          for t in tarefas_de(o, "alfa")]
checa(19, "as do relatório da Beta e todas as da Alfa continuam em aberto",
      intocadas and all(t.status == StatusTarefa.PENDENTE and not t.nao_se_aplica
                        for t in intocadas), f"({len(intocadas)} conferidas)")

# ------------------------------------------------ (c) a geração seguinte
db = SessionLocal()
gerar_tarefas(db, 11, 2026)
db.close()
nov = lambda o, e: [t for t in tarefas_de(o, e) if t.competencia == "11/2026"]  # noqa: E731
checa(20, "a geração de 11/2026 não cria IPI, ECF nem DIRB para a Beta",
      not nov("ipi", "beta") and not nov("ecf", "beta") and not nov("dirb", "beta"))
checa(21, "e continua criando o relatório da Beta e o IPI e a ECF da Alfa",
      len(nov("excl", "beta")) == 1 and len(nov("ipi", "alfa")) == 1
      and len(nov("ecf", "alfa")) == 1)
r = cliente.get(f"/api/obrigacoes/alcance-empresa/{ids['beta']}", headers=adm_h)
depois = sorted(x.get("id") for x in r.json()) if r.status_code == 200 else None
checa(22, "o alcance da Beta agora tem só o relatório", depois == [ids["excl"]],
      f"({r.status_code}, {depois})")

# ------------------------------------------------ (f) o rastro
lote = [l for l in linhas if l.get("event") == "EDICAO_REGISTRO_CRITICO"
        and l.get("acao") == "desvincular_empresa"]
e = lote[0] if lote else {}
checa(23, "UMA linha de lote por chamada", len(lote) == 1 and e.get("lote") is True,
      f"({len(lote)} linhas)")
contagem = {k: e.get(k) for k in ("obrigacoes", "excecoes_criadas", "vinculos_removidos",
                                   "tarefas_canceladas", "empresa_id", "user_id")}
checa(24, "com a contagem: 3 obrigações, 2 exceções, 2 vínculos, 8 tarefas, empresa e usuário",
      contagem == {"obrigacoes": 3, "excecoes_criadas": 2, "vinculos_removidos": 2,
                   "tarefas_canceladas": 8, "empresa_id": ids["beta"],
                   "user_id": ids["admin"]}, f"({contagem})")
checa(25, "sem razão social nem CNPJ na linha",
      bool(e) and "BETA" not in json.dumps(e) and "44555666000172" not in json.dumps(e))

# ------------------------------------------------ não-regressão
r = desvincular(adm_h, {"empresa_id": 99999, "obrigacao_ids": [ids["ipi"]],
                        "motivo": MOTIVO})
checa(26, "empresa que não existe continua 404", r.status_code == 404, f"({r.status_code})")
r = cliente.get("/api/obrigacoes/alcance-empresa/99999", headers=adm_h)
checa(27, "alcance de empresa que não existe: 404", r.status_code == 404,
      f"({r.status_code})")

# ------------------------------------------------ motivo só com espaços
# Achado do verificador funcional: `min_length` media a string crua, e a rota
# fazia `strip()` depois. Três espaços passavam e a trilha ficava sem motivo.
antes = estado()
r = desvincular(adm_h, {"empresa_id": ids["beta"], "obrigacao_ids": [ids["excl"]],
                        "motivo": "     "})
checa(28, "motivo só com espaços: 422 e nada muda", r.status_code == 422 and estado() == antes,
      f"({r.status_code})")

# ------------------------------------------------ a guarda é a flag, e não o módulo
edu_h = entrar("edu@bps4.com.br")
alice_h = entrar("alice@bps4.com.br")
antes = estado()
r1 = cliente.get(f"/api/obrigacoes/alcance-empresa/{ids['beta']}", headers=edu_h)
r2 = desvincular(edu_h, {"empresa_id": ids["beta"], "obrigacao_ids": [ids["excl"]],
                         "motivo": MOTIVO})
checa(29, "com obrigacoes: editar e SEM a flag: 403 nas duas, e nada muda",
      r1.status_code == 403 and r2.status_code == 403 and estado() == antes,
      f"({r1.status_code}, {r2.status_code})")
r = cliente.get(f"/api/obrigacoes/alcance-empresa/{ids['beta']}", headers=alice_h)
checa(30, "com a flag e SEM obrigacoes: o alcance responde 200",
      r.status_code == 200, f"({r.status_code})")

print()
if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("PROVA OK: 30 checagens verdes")
