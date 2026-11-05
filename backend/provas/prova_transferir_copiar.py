"""Prova: quem transfere, para quem, e o que a cópia entre empresas leva.

Pedido de 2026-11-05, e a regra é do Fábio: transferência é entre COLABORADORES,
com a tarefa sempre na mesma empresa. E corrigir os furos que a leitura achou:

  (a) transferir olha a permissão `transferir_tarefa`, e não o nome do grupo.
      O analista transfere e copia, por decisão do Fábio, no alcance dele;
  (b) o novo responsável tem de ser colaborador ativo e desbloqueado; a empresa
      da tarefa não muda;
  (c) editar responsáveis não aceita cliente de OUTRA empresa;
  (d) copiar respeita o alcance de quem copia;
  (e) a cópia de tarefa de obrigação mantém a obrigação e a competência, com as
      datas e os responsáveis da empresa de DESTINO, sem repetir tarefa;
  (f) destino bloqueado ou inativo é recusado; quem não tem a flag, 403.

    cd backend && ./venv/bin/python provas/prova_transferir_copiar.py
"""
from __future__ import annotations  # producao e 3.11, a maquina local e 3.9

import json
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_transferir_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("OPENAI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                          # noqa: E402
from app.auth import create_access_token                           # noqa: E402
from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import (Empresa, EmpresaSetorResponsavel, Obrigacao,  # noqa: E402
                        Setor, StatusTarefa, Tarefa, Usuario)
from app.services import resp_setor                                # noqa: E402
import app.main                                                    # noqa: E402

Base.metadata.create_all(bind=engine)
falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


db = SessionLocal()


def pessoa(nome, grupo="analista", tipo="colaborador", **k):
    u = Usuario(nome=nome, email=f"{nome}@prova.local", senha_hash="x", grupo=grupo, tipo=tipo,
                ativo=k.pop("ativo", True), bloqueado=k.pop("bloqueado", False), ativado=True, **k)
    db.add(u)
    return u


fiscal = Setor(nome="Fiscal")
origem = Empresa(razao_social="Origem Ltda", cnpj="11.222.333/0001-81", ativo=True)
destino = Empresa(razao_social="Destino Ltda", cnpj="11.444.777/0001-61", ativo=True)
parada = Empresa(razao_social="Bloqueada Ltda", ativo=True, bloqueado=True)
db.add_all([fiscal, origem, destino, parada])
db.flush()
admin = pessoa("admin", "admin")
gestor = pessoa("gestor", "gestor")
ana = pessoa("ana")
bia = pessoa("bia")
ausente = pessoa("ausente", ativo=False)
travada = pessoa("travada", bloqueado=True)
cli_outro = pessoa("clioutro", tipo="cliente", empresa_id=destino.id)
cli_mesmo = pessoa("climesmo", tipo="cliente", empresa_id=origem.id)
com_flag = pessoa("comflag", "estagiario", permissoes=json.dumps({"transferir_tarefa": True, "escopo_tarefas": "todas"}))
copiador = pessoa("copiador", "analista")
estag = pessoa("estag", "estagiario", permissoes=json.dumps({"escopo_tarefas": "todas"}))
db.flush()
v = EmpresaSetorResponsavel(empresa_id=destino.id, setor_id=fiscal.id)
db.add(v)
db.flush()
resp_setor.gravar(db, v, [bia.id])
o = Obrigacao(nome="das", sentido="entregar", setor_id=fiscal.id, ativa=True, competencia_ref="mes_anterior",
              regra_prazo_tipo="dia_fixo", regra_prazo_dia=20, meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12")
db.add(o)
db.flush()
t = Tarefa(titulo="das", empresa_id=origem.id, setor_id=fiscal.id, obrigacao_id=o.id, competencia="09/2026",
           responsavel_id=ana.id, status=StatusTarefa.PENDENTE)
t.responsaveis = [ana]
av = Tarefa(titulo="avulsa", empresa_id=origem.id, setor_id=fiscal.id, responsavel_id=gestor.id,
            status=StatusTarefa.PENDENTE, competencia="09/2026")
av.responsaveis = [gestor]
db.add_all([t, av])
db.commit()
ids = {u.nome: u.id for u in db.query(Usuario).all()}
tid, avid, oid = t.id, av.id, o.id
eo, ed, ep = origem.id, destino.id, parada.id
cli = TestClient(app.main.app)


def h(nome):
    return {"Authorization": "Bearer " + create_access_token({"sub": f"{nome}@prova.local"})}


def transferir(quem, para):
    return cli.post(f"/api/tarefas/{tid}/transferir", json={"responsavel_id": ids[para]}, headers=h(quem))


def copiar(quem, de=None, para=None):
    return cli.post("/api/tarefas/copiar", json={"origem_empresa_id": de or eo, "destino_empresa_id": para or ed},
                    headers=h(quem))


print("\n(a) quem transfere")
checa(1, "estagiario nao transfere", transferir("estag", "bia").status_code == 403)
r = transferir("comflag", "bia")
checa(2, "grupo sem o preset, com a permissao ligada, transfere", r.status_code == 200, (r.status_code, r.text[:120]))
r = transferir("bia", "ana")
checa(23, "analista transfere a tarefa dele", r.status_code == 200, (r.status_code, r.text[:120]))
r = transferir("bia", "ana")
checa(24, "analista nao transfere a tarefa de outro (fora do alcance)", r.status_code == 404, r.status_code)
checa(3, "gestor transfere pelo preset", transferir("gestor", "ana").status_code == 200)

print("\n(b) para quem")
for n, alvo in ((4, "clioutro"), (5, "climesmo"), (6, "ausente"), (7, "travada")):
    r = transferir("admin", alvo)
    checa(n, f"nao transfere para {alvo}", r.status_code == 400, (r.status_code, r.text[:100]))
r = transferir("admin", "bia")
db.expire_all()
tt = db.get(Tarefa, tid)
checa(8, "colaborador ativo recebe, e a empresa nao muda",
      r.status_code == 200 and tt.responsavel_id == ids["bia"] and tt.empresa_id == eo, r.status_code)

print("\n(c) editar responsaveis")
r = cli.put(f"/api/tarefas/{tid}", json={"responsavel_ids": [ids["clioutro"]]}, headers=h("admin"))
checa(9, "cliente de outra empresa e recusado", r.status_code == 400, (r.status_code, r.text[:100]))
r = cli.put(f"/api/tarefas/{tid}", json={"responsavel_ids": [ids["climesmo"]]}, headers=h("admin"))
checa(10, "cliente da mesma empresa continua aceito", r.status_code == 200, (r.status_code, r.text[:100]))
r = cli.put(f"/api/tarefas/{tid}", json={"responsavel_ids": [ids["bia"]]}, headers=h("comflag"))
checa(11, "editar responsaveis segue a mesma permissao de transferir", r.status_code == 200, r.status_code)
r = cli.put(f"/api/tarefas/{tid}", json={"responsavel_ids": [ids["ana"]]}, headers=h("estag"))
checa(12, "quem nao tem a permissao nao troca", r.status_code == 403, r.status_code)

print("\n(d) e (f) copiar: acesso")
checa(13, "estagiario nao copia: 403", copiar("estag").status_code == 403)
from app.permissoes import resolver                                # noqa: E402
pa = resolver("analista")
checa(25, "analista copia e transfere, sem ganhar nao-se-aplica nem desvincular",
      pa.get("copiar_tarefas") and pa.get("transferir_tarefa") and not pa.get("alocar_obrigacao"), pa)
r = copiar("admin", para=ep)
checa(14, "destino bloqueado e recusado", r.status_code == 400, (r.status_code, r.text[:100]))
r = copiar("copiador")
checa(15, "escopo reduzido nao copia o que nao alcanca",
      r.status_code == 200 and r.json().get("copiadas") == 0
      and db.query(Tarefa).filter(Tarefa.empresa_id == ed).count() == 0, (r.status_code, r.text[:120]))

print("\n(e) copiar: o que a copia leva")
r = copiar("admin")
db.expire_all()
nova = db.query(Tarefa).filter(Tarefa.empresa_id == ed, Tarefa.obrigacao_id == oid).first()
checa(16, "a copia mantem a obrigacao e a competencia", nova is not None and nova.competencia == "09/2026",
      r.text[:150])
checa(17, "com a data calculada para o destino", nova is not None and nova.data_vencimento is not None,
      nova and nova.data_vencimento)
checa(18, "e os responsaveis da matriz do destino, nao os da origem",
      nova is not None and [u.nome for u in nova.responsaveis] == ["bia"], nova and [u.nome for u in nova.responsaveis])
copia_av = db.query(Tarefa).filter(Tarefa.empresa_id == ed, Tarefa.titulo == "avulsa").first()
checa(19, "avulsa vai sem datas, com a equipe do destino",
      copia_av is not None and copia_av.data_vencimento is None
      and [u.nome for u in copia_av.responsaveis] == ["bia"], copia_av and [u.nome for u in copia_av.responsaveis])
checa(20, "a original fica onde estava", db.get(Tarefa, tid).empresa_id == eo)
r = copiar("admin")
db.expire_all()
checa(21, "copiar de novo nao repete a tarefa de obrigacao",
      db.query(Tarefa).filter(Tarefa.empresa_id == ed, Tarefa.obrigacao_id == oid).count() == 1, r.text[:150])
checa(22, "e a resposta diz quantas pulou", (r.json().get("puladas") or 0) >= 1, r.text[:150])
db.close()

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 25 checagens verdes")
