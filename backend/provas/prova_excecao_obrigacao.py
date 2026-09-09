"""
prova_excecao_obrigacao.py: "não se aplica a esta empresa", e o caminho de volta.

A obrigação pega a empresa pela regra (regime, segmento) ou pelo vínculo. Às
vezes a regra acerta o perfil e erra o cliente: a empresa é Lucro Real mas não
é contribuinte de IPI. Antes, a saída era cancelar a tarefa todo mês, para
sempre, ou desmontar a regra da obrigação inteira por causa de um cliente.

O que se prova aqui:
· desconsiderar tira a empresa da geração seguinte NOS DOIS MODOS de alvo. Só
  no modo 'regra' deixaria a decisão furada: bastaria a obrigação mudar de modo
  para a empresa voltar a gerar sem ninguém desfazer nada;
· remover a exceção faz a empresa voltar, e é isso que impede um clique errado
  de prender o cliente fora da obrigação para sempre;
· a tarefa desconsiderada NÃO é apagada: vai para CANCELADA com motivo, autor e
  data, e não conta como pendente nem como atrasada.

Rodar:  cd backend && ./venv/bin/python provas/prova_excecao_obrigacao.py
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_excecao_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp, 'prova.db')}"
os.environ["SECRET_KEY"] = "chave-jwt-de-teste"
os.environ["ZOARIA_SSO_SECRET"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                              # noqa: E402
from sqlalchemy import event                                          # noqa: E402

from app.database import SessionLocal, Base, engine                    # noqa: E402


# Produção é Postgres, que checa chave estrangeira sempre. Sem este PRAGMA a
# prova roda num banco mais permissivo que o real e não veria a linha órfã que
# sobra ao apagar a obrigação ou a empresa.
@event.listens_for(engine, "connect")
def _liga_fk(dbapi_con, _rec):
    dbapi_con.execute("PRAGMA foreign_keys=ON")

from app.models import (Empresa, Setor, Usuario, Obrigacao, Tarefa,     # noqa: E402
                        ObrigacaoExcecao, StatusTarefa, obrigacao_empresa)
from app.auth import get_password_hash                                 # noqa: E402
from app.services.gerador import gerar_tarefas, empresas_alvo          # noqa: E402
from app.routes.painel import _situacao                                # noqa: E402
from app.main import app                                               # noqa: E402

Base.metadata.create_all(bind=engine)
cliente = TestClient(app)
SENHA = "senha-boa-123"
ok = True


def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


def montar(alvo_modo):
    db = SessionLocal()
    # A associação primeiro: `query().delete()` é DELETE em massa, não passa
    # pelo ORM, e com a checagem de chave estrangeira ligada o banco recusa
    # apagar a obrigação que ainda tem empresa vinculada.
    db.execute(obrigacao_empresa.delete())
    for m in (Tarefa, ObrigacaoExcecao, Obrigacao, Empresa, Setor, Usuario):
        db.query(m).delete()
    db.commit()
    admin = Usuario(nome="Admin", email="admin@x.com", grupo="admin",
                    senha_hash=get_password_hash(SENHA), ativo=True)
    db.add(admin)
    setor = Setor(nome="Fiscal", ativo=True)
    db.add(setor)
    db.commit()
    empresas = {}
    for nome in ("Alfa", "Beta"):
        e = Empresa(razao_social=nome, cnpj=nome, regime_tributario="lucro_real", ativo=True)
        db.add(e)
        db.commit()
        empresas[nome] = e
    o = Obrigacao(nome="Apuração de IPI", setor_id=setor.id, alvo_modo=alvo_modo,
                  regra_prazo_tipo="ultimo_dia_util",
                  meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12",
                  competencia_ref="mes_anterior", ativa=True)
    if alvo_modo == "vinculadas":
        o.empresas = list(empresas.values())
    db.add(o)
    db.commit()
    r = cliente.post("/api/auth/login", json={"email": "admin@x.com", "senha": SENHA})
    cab = {"Authorization": "Bearer " + r.json()["access_token"]}
    return db, o, empresas, cab


def alvo(db, o):
    return sorted(e.razao_social for e in empresas_alvo(db, o))


for modo in ("regra", "vinculadas"):
    print(f"\n=== modo de alvo: {modo} ===")
    db, o, emps, cab = montar(modo)
    r1 = gerar_tarefas(db, 9, 2026)
    check(f"[{modo}] antes, a obrigação alcança as duas", alvo(db, o) == ["Alfa", "Beta"],
          f"({alvo(db, o)})")
    check(f"[{modo}] e gerou uma tarefa para cada", r1["criadas"] == 2, f"({r1['criadas']})")

    t = (db.query(Tarefa).join(Empresa, Tarefa.empresa_id == Empresa.id)
         .filter(Empresa.razao_social == "Beta").first())
    resp = cliente.post(f"/api/tarefas/{t.id}/nao-se-aplica", headers=cab,
                        json={"motivo": "Beta não é contribuinte de IPI."})
    check(f"[{modo}] a ação responde ok", resp.status_code == 200,
          f"({resp.status_code} {resp.text[:120]})")

    db.expire_all()
    t = db.query(Tarefa).filter(Tarefa.id == t.id).first()
    check(f"[{modo}] a tarefa NÃO foi apagada, foi para cancelada",
          t is not None and t.status == StatusTarefa.CANCELADA)
    check(f"[{modo}] com o motivo, o autor e a data gravados",
          t.nao_se_aplica is True and "IPI" in (t.nao_se_aplica_motivo or "")
          and t.nao_se_aplica_por_id and t.nao_se_aplica_em is not None,
          f"({t.nao_se_aplica_motivo}, {t.nao_se_aplica_por_id})")

    check(f"[{modo}] a empresa saiu do alvo da obrigação", alvo(db, o) == ["Alfa"],
          f"({alvo(db, o)})")
    r2 = gerar_tarefas(db, 10, 2026)
    criadas_beta = (db.query(Tarefa).join(Empresa, Tarefa.empresa_id == Empresa.id)
                    .filter(Empresa.razao_social == "Beta").count())
    check(f"[{modo}] o mês seguinte NÃO gera de novo para ela",
          criadas_beta == 1 and r2["criadas"] == 1, f"({criadas_beta}, {r2['criadas']})")

    # A volta: sem ela, um clique errado prende a empresa fora para sempre.
    x = db.query(ObrigacaoExcecao).filter(ObrigacaoExcecao.obrigacao_id == o.id).first()
    resp = cliente.delete(f"/api/obrigacoes/{o.id}/excecoes/{x.id}", headers=cab)
    db.expire_all()
    check(f"[{modo}] remover a exceção responde ok", resp.status_code == 200,
          f"({resp.status_code})")
    check(f"[{modo}] e a empresa volta ao alvo", alvo(db, o) == ["Alfa", "Beta"],
          f"({alvo(db, o)})")
    r3 = gerar_tarefas(db, 11, 2026)
    check(f"[{modo}] a geração seguinte inclui ela de novo", r3["criadas"] == 2,
          f"({r3['criadas']})")
    db.close()

print("\n=== a tarefa desconsiderada não conta como pendente nem atrasada ===")
db, o, emps, cab = montar("regra")
gerar_tarefas(db, 9, 2026)
t = (db.query(Tarefa).join(Empresa, Tarefa.empresa_id == Empresa.id)
     .filter(Empresa.razao_social == "Beta").first())
# prazo vencido de propósito: sem o cancelamento ela seria "atrasada"
t.data_prazo = datetime.utcnow() - timedelta(days=5)
db.commit()
agora = datetime.utcnow()
check("com o prazo vencido, antes da ação ela é atrasada",
      _situacao(t.status, t.data_prazo, agora) == "atrasada")
cliente.post(f"/api/tarefas/{t.id}/nao-se-aplica", headers=cab,
             json={"motivo": "não é contribuinte"})
db.expire_all()
t = db.query(Tarefa).filter(Tarefa.id == t.id).first()
situacao = _situacao(t.status, t.data_prazo, agora)
check("depois da ação ela sai de atrasada", situacao != "atrasada", f"({situacao})")
check("e não vira pendente: fica cancelada", situacao == "cancelada", f"({situacao})")

print("\n=== recusas ===")
avulsa = Tarefa(titulo="avulsa", empresa_id=emps["Alfa"].id, status=StatusTarefa.PENDENTE)
db.add(avulsa)
db.commit()
r = cliente.post(f"/api/tarefas/{avulsa.id}/nao-se-aplica", headers=cab,
                 json={"motivo": "qualquer coisa"})
check("tarefa avulsa, sem obrigação, é recusada com explicação",
      r.status_code == 422 and "obrigação" in r.json().get("detail", ""),
      f"({r.status_code} {r.text[:100]})")
r = cliente.post(f"/api/tarefas/{avulsa.id}/nao-se-aplica", headers=cab, json={"motivo": "x"})
check("motivo curto demais é recusado pelo schema", r.status_code == 422)
r = cliente.post("/api/tarefas/999999/nao-se-aplica", headers=cab, json={"motivo": "existe?"})
check("tarefa inexistente devolve 404, e nunca 403", r.status_code == 404)
r = cliente.post(f"/api/tarefas/{avulsa.id}/nao-se-aplica", headers=cab,
                 json={"motivo": "válido", "status": "concluida"})
check("campo inventado no corpo é recusado", r.status_code == 422)
db.close()

print("\n=== apagar a obrigação ou a empresa não deixa a exceção pendurada ===")
db, o, emps, cab = montar("regra")
gerar_tarefas(db, 9, 2026)
t = (db.query(Tarefa).join(Empresa, Tarefa.empresa_id == Empresa.id)
     .filter(Empresa.razao_social == "Beta").first())
cliente.post(f"/api/tarefas/{t.id}/nao-se-aplica", headers=cab,
             json={"motivo": "não é contribuinte"})
check("a exceção existe antes de apagar",
      db.query(ObrigacaoExcecao).count() == 1)
r = cliente.delete(f"/api/obrigacoes/{o.id}", headers=cab, params={"definitivo": True})
db.expire_all()
check("apagar a obrigação de vez responde ok, sem estourar chave estrangeira",
      r.status_code == 200, f"({r.status_code} {r.text[:120]})")
check("e a exceção vai junto, em vez de virar linha órfã",
      db.query(ObrigacaoExcecao).count() == 0,
      f"({db.query(ObrigacaoExcecao).count()} linhas)")
db.close()

print("\n=== duas tarefas da mesma empresa e obrigação, ao mesmo tempo ===")
db, o, emps, cab = montar("regra")
gerar_tarefas(db, 9, 2026)
gerar_tarefas(db, 10, 2026)          # a mesma empresa, outra competência
duas = (db.query(Tarefa).join(Empresa, Tarefa.empresa_id == Empresa.id)
        .filter(Empresa.razao_social == "Beta").all())
check("existem duas tarefas da mesma obrigação para a mesma empresa", len(duas) == 2)
respostas = [cliente.post(f"/api/tarefas/{x.id}/nao-se-aplica", headers=cab,
                          json={"motivo": "não é contribuinte"}).status_code
             for x in duas]
check("a segunda chamada NÃO estoura 500 na unique da exceção",
      respostas == [200, 200], f"({respostas})")
check("e a exceção continua sendo uma só", db.query(ObrigacaoExcecao).count() == 1,
      f"({db.query(ObrigacaoExcecao).count()})")
db.close()

print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
