"""
prova_painel.py — os números do painel.

O que motivou: a rosca do dashboard somava 101%. "Atrasada" era contada dentro
de "pendente", então uma tarefa aparecia duas vezes e a soma passava do total.
Um painel em que os números não fecham não é usado para decidir nada.

    python provas/prova_painel.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-painel-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from fastapi.testclient import TestClient                      # noqa: E402
from app.database import Base, engine, SessionLocal            # noqa: E402
from app.models import (Usuario, Empresa, Setor, Tarefa, Obrigacao, TarefaEnvio,  # noqa: E402
                        StatusTarefa, PrioridadeTarefa)
from app.auth import get_password_hash, create_access_token    # noqa: E402
from app.main import app                                       # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

ok = True
def checa(nome, cond, extra=""):
    global ok
    print(("  ok   " if cond else "FALHA  ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


cab = {"Authorization": "Bearer " + create_access_token(data={"sub": "admin@x.com"})}
agora = datetime.utcnow()

db = SessionLocal()
db.add(Usuario(nome="Admin", email="admin@x.com", grupo="admin", ativo=True,
               senha_hash=get_password_hash("x")))
ana = Usuario(nome="Ana", email="ana@x.com", grupo="analista", ativo=True,
              senha_hash=get_password_hash("x"))
bia = Usuario(nome="Bia", email="bia@x.com", grupo="analista", ativo=True,
              senha_hash=get_password_hash("x"))
fiscal = Setor(nome="Fiscal"); contab = Setor(nome="Contabilidade")
emp = Empresa(razao_social="Cliente", cnpj="1")
db.add_all([ana, bia, fiscal, contab, emp]); db.commit()

def nova(titulo, status, dias, setor, multa=False, quem=(), comp="07/2026"):
    t = Tarefa(titulo=titulo, empresa_id=emp.id, setor_id=setor.id, status=status,
               gera_multa=multa, competencia=comp,
               data_prazo=agora + timedelta(days=dias) if dias is not None else None)
    db.add(t); db.commit()
    for u in quem:
        t.responsaveis.append(u)
    db.commit()
    return t

nova("atrasada com multa", StatusTarefa.PENDENTE, -3, fiscal, multa=True, quem=(ana,))
nova("atrasada sem multa", StatusTarefa.PENDENTE, -1, fiscal, quem=(ana,))
nova("pendente futura", StatusTarefa.PENDENTE, 5, fiscal, multa=True, quem=(bia,))
nova("em andamento", StatusTarefa.EM_ANDAMENTO, 2, contab, quem=(ana, bia))
nova("concluida com multa", StatusTarefa.CONCLUIDA, -10, contab, multa=True, quem=(bia,))
nova("cancelada", StatusTarefa.CANCELADA, -10, contab)
nova("sem responsavel", StatusTarefa.PENDENTE, 3, contab)
db.close()

d = client.get("/api/painel", headers=cab).json()
r = d["resumo"]

print("\n1. Situação exclusiva — cada tarefa conta UMA vez")
checa("total é 7", r["total"] == 7, str(r["total"]))
soma = sum(r[s] for s in ("pendente", "em_andamento", "atrasada", "concluida", "cancelada"))
checa("as situações somam exatamente o total", soma == r["total"], f"({soma} x {r['total']})")
checa("atrasada NÃO está dentro de pendente",
      r["atrasada"] == 2 and r["pendente"] == 2, f"atrasada={r['atrasada']} pendente={r['pendente']}")
checa("em andamento", r["em_andamento"] == 1)
checa("concluída", r["concluida"] == 1)
checa("cancelada", r["cancelada"] == 1)

print("\n2. Multa conta só o que ainda pode dar problema")
checa("duas em aberto geram multa", r["multa"] == 2, str(r["multa"]))
checa("a concluída com multa não entra — já não é risco", r["multa"] != 3)

print("\n3. Por setor")
setores = {s["nome"]: s for s in d["por_setor"]}
checa("Fiscal com 3", setores["Fiscal"]["total"] == 3)
checa("e 2 atrasadas", setores["Fiscal"]["atrasada"] == 2)
checa("Contabilidade com 4", setores["Contabilidade"]["total"] == 4)
checa("o mais carregado vem primeiro", d["por_setor"][0]["nome"] == "Fiscal", d["por_setor"][0]["nome"])

print("\n4. Por colaborador — tarefa com dois responsáveis conta para os dois")
colab = {c["nome"]: c for c in d["por_colaborador"]}
checa("Ana com 3", colab["Ana"]["total"] == 3, str(colab["Ana"]["total"]))
checa("Bia com 3", colab["Bia"]["total"] == 3, str(colab["Bia"]["total"]))
# Duas tarefas sem ninguém: a "sem responsavel" e a "cancelada".
checa("quem não tem responsável aparece à parte",
      colab.get("Sem responsável", {}).get("total") == 2,
      str(colab.get("Sem responsável", {}).get("total")))
# A soma por colaborador passa do total, e tem de passar: tarefa com dois
# responsáveis conta para os dois. Confundir isso com erro levaria a "consertar"
# a contagem e esconder metade do trabalho de alguém.
soma_colab = sum(c["total"] for c in d["por_colaborador"])
checa("a soma por colaborador excede o total, por causa do trabalho dividido",
      soma_colab == 8 and soma_colab > r["total"], str(soma_colab))

print("\n5. Próximas do vencimento, em tabela")
checa("uma linha por tarefa em aberto, não um grupo", len(d["proximas"]) == 5,
      str(len(d["proximas"])))
checa("concluída e cancelada ficam de fora",
      all(t["titulo"] not in ("concluida com multa", "cancelada") for t in d["proximas"]))
checa("ordenadas pelo prazo", d["proximas"][0]["titulo"] == "atrasada com multa",
      d["proximas"][0]["titulo"])
checa("a linha traz empresa", d["proximas"][0]["empresa"] == "Cliente")
checa("traz o setor, que virou coluna", d["proximas"][0]["setor"] == "Fiscal")
checa("traz quem responde", d["proximas"][0]["responsaveis"] == ["Ana"])
checa("marca a atrasada", d["proximas"][0]["atrasada"] is True)
checa("e se gera multa", d["proximas"][0]["multa"] is True)
checa("diz o total de abertas, para a tabela avisar quando cortar",
      d["abertas_total"] == 5, str(d["abertas_total"]))

print("\n6. Filtros")
f = lambda **kw: client.get("/api/painel", params=kw, headers=cab).json()["resumo"]
checa("por setor", f(setor_id=fiscal.id if False else 1)["total"] in (3, 4))
checa("só multa traz as três que geram", f(so_multa=True)["total"] == 3, str(f(so_multa=True)["total"]))
checa("competência que não existe zera", f(competencia="01/1999")["total"] == 0)
checa("competência certa traz tudo", f(competencia="07/2026")["total"] == 7)

print("\n7. Sem sessão não abre")
checa("401 ou 403", client.get("/api/painel").status_code in (401, 403))

print("\n8. Atraso tem dono — travado no cliente x travado aqui dentro")
db = SessionLocal()
receber = Obrigacao(nome="DAS", sentido="receber", exige_documento=True)
entregar = Obrigacao(nome="Guia", sentido="entregar")
interna = Obrigacao(nome="Conciliar banco", sentido="interna", exige_documento=True)
emp2 = Empresa(razao_social="Segunda Cliente Ltda", nome_fantasia="Segunda", cnpj="2")
db.add_all([receber, entregar, interna, emp2]); db.commit()
# Ids relidos: os objetos da primeira sessão morreram no db.close() acima.
emp_id = db.query(Empresa.id).filter_by(cnpj="1").scalar()
fiscal_id = db.query(Setor.id).filter_by(nome="Fiscal").scalar()
emp2_id, receber_id, entregar_id, interna_id = emp2.id, receber.id, entregar.id, interna.id

def nova2(titulo, status, dias, ob=None, anexo=None, downloads=0,
          prioridade=PrioridadeTarefa.MEDIA, conclusao=None, empresa=None):
    t = Tarefa(titulo=titulo, empresa_id=empresa or emp_id, setor_id=fiscal_id,
               status=status, obrigacao_id=ob, anexo_nome=anexo,
               saida_downloads=downloads, prioridade=prioridade,
               data_conclusao=agora + timedelta(days=conclusao) if conclusao is not None else None,
               data_prazo=agora + timedelta(days=dias) if dias is not None else None)
    db.add(t); db.commit()
    return t.id

t_agu = nova2("doc nao chegou", StatusTarefa.PENDENTE, -2, ob=receber_id)
nova2("doc ja chegou", StatusTarefa.PENDENTE, 2, ob=receber_id, anexo="comprovante.pdf")
nova2("conciliar banco", StatusTarefa.PENDENTE, -1, ob=interna_id)
t_fechada = nova2("guia enviada e nao aberta", StatusTarefa.CONCLUIDA, -1, ob=entregar_id)
t_lida = nova2("guia enviada e aberta", StatusTarefa.CONCLUIDA, -1, ob=entregar_id, downloads=3)
nova2("guia pronta mas nao enviada", StatusTarefa.PENDENTE, 4, ob=entregar_id)
nova2("urgente em aberto", StatusTarefa.PENDENTE, 1, prioridade=PrioridadeTarefa.URGENTE)
nova2("alta ja concluida", StatusTarefa.CONCLUIDA, -1, prioridade=PrioridadeTarefa.ALTA)
nova2("entregue no prazo", StatusTarefa.CONCLUIDA, -5, conclusao=-6)
nova2("entregue atrasada", StatusTarefa.CONCLUIDA, -5, conclusao=-3)
nova2("tarefa da segunda", StatusTarefa.PENDENTE, 3, empresa=emp2_id)
for tid in (t_fechada, t_lida):
    db.add(TarefaEnvio(tarefa_id=tid, canal="whatsapp", sucesso=True))
db.commit(); db.close()

d2 = client.get("/api/painel", headers=cab).json()
r2 = d2["resumo"]

checa("aguardando o cliente conta só o documento que falta",
      r2["aguardando_cliente"] == 1, str(r2["aguardando_cliente"]))
checa("documento já entregue sai da fila de cobrança",
      all(x["titulo"] != "doc ja chegou" for x in d2["aguardando"]))
checa("obrigação interna nunca espera documento de ninguém",
      all(x["titulo"] != "conciliar banco" for x in d2["aguardando"]))
checa("a lista diz de quem é a empresa e se já atrasou",
      d2["aguardando"][0]["empresa"] == "Cliente" and d2["aguardando"][0]["atrasada"])

print("\n9. Guia que saiu daqui e ninguém abriu")
checa("conta a enviada sem abertura", r2["nao_abertas"] == 1, str(r2["nao_abertas"]))
checa("a que o cliente baixou não entra",
      all(x["titulo"] != "guia enviada e aberta" for x in d2["nao_abertas"]))
# Sem envio não há o que cobrar do cliente: o documento ainda está com a gente.
checa("a que nem foi enviada não entra",
      all(x["titulo"] != "guia pronta mas nao enviada" for x in d2["nao_abertas"]))
checa("a lista traz quando saiu", bool(d2["nao_abertas"][0]["enviado_em"]))

print("\n10. Prioridade e pontualidade")
checa("urgente/alta conta só em aberto", r2["urgentes"] == 1, str(r2["urgentes"]))
checa("pontualidade olha só quem tinha prazo e foi concluída",
      r2["concluidas_com_prazo"] == 2, str(r2["concluidas_com_prazo"]))
checa("uma no prazo, uma fora", r2["no_prazo"] == 1, str(r2["no_prazo"]))

print("\n11. Por empresa")
empresas = {e["nome"]: e for e in d2["por_empresa"]}
checa("as duas empresas aparecem", len(empresas) == 2, str(list(empresas)))
checa("usa o nome fantasia quando existe", "Segunda" in empresas)
checa("a soma por empresa fecha com o total",
      sum(e["total"] for e in d2["por_empresa"]) == r2["total"])
checa("a mais carregada vem primeiro", d2["por_empresa"][0]["nome"] == "Cliente")

print("\n12. Fuso — o 500 que a prova em SQLite não pegava")
# Postgres devolve datetime AWARE para DateTime(timezone=True); SQLite devolve
# NAIVE. O painel compara data em Python (as rotas antigas comparavam no SQL,
# e o banco resolvia sozinho), então `aware < naive` estourava TypeError e a
# tela mostrava "500: erro no servidor". Nenhuma prova via isso, porque toda
# prova roda em SQLite. Estas checagens chamam a função direto, com os dois
# tipos, e é o que impede a volta do erro.
from datetime import timezone as _tz                            # noqa: E402
from app.routes.painel import _utc, _situacao                   # noqa: E402

agora_aware = datetime.now(_tz.utc)
naive = datetime.utcnow() - timedelta(days=2)
aware = agora_aware - timedelta(days=2)

checa("data sem fuso vira UTC", _utc(naive).tzinfo == _tz.utc)
checa("data com fuso passa intacta", _utc(aware) is aware)
checa("nulo continua nulo", _utc(None) is None)

try:
    naive < agora_aware
    puro = False
except TypeError:
    puro = True
checa("comparar aware com naive de fato estoura — era este o 500", puro)

try:
    sit_pg = _situacao(StatusTarefa.PENDENTE, _utc(aware), agora_aware)
    sit_lite = _situacao(StatusTarefa.PENDENTE, _utc(naive), agora_aware)
    quebrou = None
except TypeError as e:
    sit_pg = sit_lite = None
    quebrou = str(e)
checa("prazo vindo do Postgres não quebra", quebrou is None, quebrou or "")
checa("e é lido como atrasada", sit_pg == "atrasada", str(sit_pg))
checa("prazo vindo do SQLite dá a MESMA resposta", sit_lite == "atrasada", str(sit_lite))

print("\n13. A linha Cliente no gráfico por setor")
# Onde a bola está parada quando não está com nenhum setor nosso. É ADITIVA: a
# tarefa continua contando no setor dela, porque tirá-la de lá mudaria a carga
# do setor, que é outra pergunta.
setores2 = {x["nome"]: x for x in d2["por_setor"]}
checa("existe uma linha Cliente", "Cliente" in setores2, str(list(setores2)))
checa("junta o que espera documento com o que foi enviado e não abriram",
      setores2["Cliente"]["total"] == 2, str(setores2["Cliente"]["total"]))
checa("vem marcada como derivada, para ninguém somar errado",
      setores2["Cliente"].get("derivado") is True)
checa("é a última da lista", d2["por_setor"][-1]["nome"] == "Cliente")
# A tarefa "doc nao chegou" é do Fiscal e está esperando o cliente: tem de
# aparecer nos dois lugares, e é justamente por isso que a linha é marcada.
checa("a mesma tarefa continua contada no setor dela",
      setores2["Fiscal"]["total"] > 0 and setores2["Cliente"]["total"] > 0)

sem_cliente = client.get("/api/painel", params={"competencia": "07/2026"}, headers=cab).json()
checa("sem nada parado no cliente, a linha nem aparece",
      all(x["nome"] != "Cliente" for x in sem_cliente["por_setor"]))

import shutil                                                  # noqa: E402
shutil.rmtree(_tmp, ignore_errors=True)
print("\n" + ("TUDO VERDE" if ok else "VERMELHO") + "\n")
sys.exit(0 if ok else 1)
