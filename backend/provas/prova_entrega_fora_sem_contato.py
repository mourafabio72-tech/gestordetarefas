"""Prova: guia enviada por fora, e relatório de quem está sem contato.

Pedido de 2026-11-03: uma guia foi enviada ao cliente fora do Tareffas, e a
tarefa não tinha como concluir (a baixa manual é bloqueada, e o envio só conclui
se ALGUÉM recebeu pelo sistema). E: quais obrigações de envio ao cliente alcançam
empresas sem dados de contato.

  (a) "enviada por fora" conclui a tarefa, exige a guia anexada e o como foi,
      registra quem declarou e não sai nada para o cliente;
  (b) tarefa concluída ou cancelada não aceita a declaração;
  (c) o relatório lista a empresa sem contato com as obrigações de "entregar"
      que a alcançam, pela mesma regra do gerador;
  (d) fica de fora quem tem contato, usuário cliente, ou não está no alcance;
  (e) e-mail que o envio descarta conta como sem contato, e diz o motivo.

    cd backend && ./venv/bin/python provas/prova_entrega_fora_sem_contato.py
"""
from __future__ import annotations  # producao e 3.11, a maquina local e 3.9

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_entrega_fora_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("OPENAI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import (Empresa, Obrigacao, Setor, StatusTarefa,   # noqa: E402
                        Tarefa, TarefaEnvio, Usuario, EmpresaSetorResponsavel)
from app.services import entrega_cliente as ec, upload as up, whatsapp, email as email_mod  # noqa: E402
from app.services.sem_contato import empresas_sem_contato          # noqa: E402
import app.main                                                    # noqa: E402,F401

Base.metadata.create_all(bind=engine)
falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


SAIU = []
email_mod.send_email = lambda *a, **k: (SAIU.append(a), {"success": True})[1]

db = SessionLocal()
fiscal = Setor(nome="Fiscal Prova")
dp = Setor(nome="DP Prova")
db.add_all([fiscal, dp])
db.flush()
sem = Empresa(razao_social="Sem Contato Ltda", cnpj="11.111.111/0001-11", ativo=True)
ruim = Empresa(razao_social="Email Ruim Ltda", cnpj="22.222.222/0001-22", ativo=True, email="contato@semponto")
com = Empresa(razao_social="Com Email Ltda", cnpj="33.333.333/0001-33", ativo=True, email="a@b.com.br")
tel = Empresa(razao_social="Com Telefone Ltda", cnpj="44.444.444/0001-44", ativo=True, telefone="21999990000")
pessoa = Empresa(razao_social="Com Usuario Ltda", cnpj="55.555.555/0001-55", ativo=True)
outro_setor = Empresa(razao_social="So DP Ltda", cnpj="66.666.666/0001-66", ativo=True)
db.add_all([sem, ruim, com, tel, pessoa, outro_setor])
db.flush()
db.add(Usuario(nome="Socio", email="socio@x.com.br", senha_hash="x", tipo="cliente",
               empresa_id=pessoa.id, ativo=True, bloqueado=False))
db.add(EmpresaSetorResponsavel(empresa_id=outro_setor.id, setor_id=dp.id))
das = Obrigacao(nome="das_prova", mininome="DAS", sentido="entregar", setor_id=fiscal.id, ativa=True,
                meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12")
iss = Obrigacao(nome="iss_prova", sentido="entregar", setor_id=fiscal.id, ativa=True,
                meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12")
inativa = Obrigacao(nome="inativa_prova", sentido="entregar", setor_id=fiscal.id, ativa=False,
                    meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12")
recebe = Obrigacao(nome="recibo_prova", sentido="receber", setor_id=fiscal.id, ativa=True,
                   meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12")
db.add_all([das, iss, inativa, recebe])
db.flush()
t = Tarefa(titulo="das_prova", empresa_id=sem.id, obrigacao_id=das.id, competencia="09/2026",
           status=StatusTarefa.PENDENTE)
db.add(t)
db.commit()
quem = db.query(Usuario).first()

# ------------------------------------------------------------ (a)
print("\n(a) enviada por fora")
try:
    ec.registrar_entrega_fora(db, t, quem.id, "por e-mail do analista")
    checa(1, "sem guia anexada e recusado", False)
except ec.SemDocumento:
    checa(1, "sem guia anexada e recusado", True)
t.saida_nome = up.salvar_saida(t.id, "guia.pdf", b"%PDF guia")
db.commit()
try:
    ec.registrar_entrega_fora(db, t, quem.id, "   ")
    checa(2, "sem dizer como foi e recusado", False)
except ValueError:
    checa(2, "sem dizer como foi e recusado", True)
r = ec.registrar_entrega_fora(db, t, quem.id, "por e-mail do analista em 01/10")
db.expire_all()
t = db.get(Tarefa, t.id)
checa(3, "a tarefa conclui, com data", t.status == StatusTarefa.CONCLUIDA and t.data_conclusao and t.data_entrega
      and r.get("concluiu"), (t.status, r))
env = db.query(TarefaEnvio).filter(TarefaEnvio.tarefa_id == t.id).one()
checa(4, "o historico registra canal fora, quem declarou e como foi",
      env.canal == "fora" and env.sucesso and env.enviado_por == quem.id
      and "01/10" in (env.detalhe or "") and env.token is None, (env.canal, env.detalhe))
checa(5, "nada saiu para o cliente", not SAIU, SAIU)

# ------------------------------------------------------------ (b)
print("\n(b) estados")
try:
    ec.registrar_entrega_fora(db, t, quem.id, "de novo")
    checa(6, "tarefa ja concluida nao aceita", False)
except ec.EstadoInvalido:
    checa(6, "tarefa ja concluida nao aceita", True)
tc = Tarefa(titulo="x", empresa_id=sem.id, obrigacao_id=iss.id, competencia="09/2026",
            status=StatusTarefa.CANCELADA, saida_nome="saida_0_x.pdf")
db.add(tc)
db.commit()
try:
    ec.registrar_entrega_fora(db, tc, quem.id, "por fora")
    checa(7, "tarefa cancelada nao aceita", False)
except ec.EstadoInvalido:
    checa(7, "tarefa cancelada nao aceita", True)

# ------------------------------------------------------------ (c), (d) e (e)
print("\n(c), (d) e (e) relatorio")
db.add(Tarefa(titulo="iss_prova", empresa_id=sem.id, obrigacao_id=iss.id, competencia="10/2026",
              status=StatusTarefa.PENDENTE))
db.commit()
linhas = {l["razao_social"]: l for l in empresas_sem_contato(db)}
checa(8, "lista so quem nao tem para onde enviar",
      sorted(linhas) == ["Email Ruim Ltda", "Sem Contato Ltda"], sorted(linhas))
l = linhas.get("Sem Contato Ltda", {})
checa(9, "com as obrigacoes de entregar ativas que a alcancam",
      l.get("obrigacoes") == ["DAS", "iss_prova"], l.get("obrigacoes"))
checa(10, "conta as tarefas abertas dessas obrigacoes (a concluida e a cancelada nao)",
      l.get("tarefas_abertas") == 1, l.get("tarefas_abertas"))
checa(11, "motivo: sem nada na ficha", l.get("motivo") == "Sem e-mail e sem telefone", l.get("motivo"))
l = linhas.get("Email Ruim Ltda", {})
checa(12, "e-mail que o envio descarta aparece, com o motivo e o que esta gravado",
      l.get("motivo") == "E-mail inválido na ficha" and l.get("email") == "contato@semponto", l)
db.close()

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 12 checagens verdes")
