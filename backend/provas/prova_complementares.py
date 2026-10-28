"""Prova: documentos complementares vão ao cliente junto da guia.

Pedido de 2026-10-28, decisões do Fábio:
  - vínculo automático pelo LOTE do e-validador: arquivo sem obrigação, com o
    CNPJ (ou a raiz) e a competência de uma guia de "entregar" do mesmo lote,
    vira complementar da tarefa dela;
  - entrega por UM link, que abre a página com a guia e os complementares.

  (a) o lote é lido inteiro ANTES de enviar: o complementar que vem antes da
      guia na lista já está na tarefa quando a guia sai;
  (b) arquivo de outra competência, ou num lote sem guia, não vira complementar;
  (c) duas guias da mesma empresa e competência no lote: "ambíguo", nada ligado;
  (d) mensagem e link: "Baixar os documentos", página /receber/<token>;
  (e) a página pública lista os arquivos; o download do complementar registra o
      acesso sem mexer no contador da guia; id de outra tarefa dá 404;
  (f) guia trocada leva os complementares antigos junto (banco e volume).

WhatsApp e e-mail são dublês: nada sai.

    cd backend && ./venv/bin/python provas/prova_complementares.py
"""
from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import asyncio
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_complementares_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("OPENAI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                          # noqa: E402
from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import (Empresa, Obrigacao, StatusTarefa, Tarefa,  # noqa: E402
                        TarefaEnvio, SaidaAcesso, TarefaComplementar)
from app.services import validador, whatsapp, email as email_mod   # noqa: E402
from app.services import upload as up, entrega_cliente as ec       # noqa: E402
from app.services.complementares import processar_lote             # noqa: E402
import app.main                                                    # noqa: E402

Base.metadata.create_all(bind=engine)
falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


TEXTOS = {
    "guia.pdf": "DOCUMENTO DE ARRECADACAO DO SIMPLES\nCNPJ: 11.222.333/0001-81\nCompetência: 09/2026",
    "memoria.pdf": "Memória de cálculo\nCNPJ: 11.222.333/0001-81\nCompetência: 09/2026",
    "extrato.pdf": "Extrato de faturamento\nCNPJ: 11.222.333\nPeríodo 01/09/2026 a 30/09/2026",
    "velho.pdf": "Memória de cálculo\nCNPJ: 11.222.333/0001-81\nCompetência: 08/2026",
    "iss.pdf": "GUIA ISS PROPRIO\nCNPJ: 11.222.333/0001-81\nCompetência: 09/2026",
}
validador.ler_arquivo = lambda nome, conteudo: TEXTOS.get(nome, "")

db = SessionLocal()
emp = Empresa(razao_social="Cliente Ficticio Ltda", cnpj="11.222.333/0001-81", ativo=True,
              email="financeiro@ficticio.com.br")
outra = Empresa(razao_social="Outra Ltda", cnpj="44.555.666/0001-99", ativo=True)
das = Obrigacao(nome="das", mininome="DAS", identificadores="DOCUMENTO DE ARRECADACAO DO SIMPLES",
                sentido="entregar", meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12", ativa=True)
iss = Obrigacao(nome="iss", mininome="ISS", identificadores="GUIA ISS PROPRIO",
                sentido="entregar", meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12", ativa=True)
db.add_all([emp, outra, das, iss])
db.flush()
t_das = Tarefa(titulo="das", empresa_id=emp.id, obrigacao_id=das.id, competencia="09/2026",
               status=StatusTarefa.PENDENTE)
t_iss = Tarefa(titulo="iss", empresa_id=emp.id, obrigacao_id=iss.id, competencia="09/2026",
               status=StatusTarefa.PENDENTE)
t_outra = Tarefa(titulo="das", empresa_id=outra.id, obrigacao_id=das.id, competencia="09/2026",
                 status=StatusTarefa.PENDENTE)
db.add_all([t_das, t_iss, t_outra])
db.commit()

ENVIOS = []


async def enviar_falso(db_, tid):
    t = db_.get(Tarefa, tid)
    ENVIOS.append({"tarefa_id": tid, "complementares": len(t.complementares)})
    return {"status": "enviada", "detalhe": "dublê"}


# ------------------------------------------------------------ (a) e (b)
print("\n(a) e (b) lote")
res = asyncio.run(processar_lote(db, [("memoria.pdf", b"m"), ("extrato.pdf", b"e"),
                                      ("velho.pdf", b"v"), ("guia.pdf", b"g")], enviar_falso))
por = {r["arquivo"]: r for r in res}
checa(1, "a guia saiu", por["guia.pdf"]["status"] == "enviada", por["guia.pdf"])
checa(2, "memoria e extrato (so a raiz) viraram complementares da tarefa do DAS",
      all(por[n]["status"] == "complementar" and por[n]["tarefa_id"] == t_das.id
          for n in ("memoria.pdf", "extrato.pdf")), [por[n] for n in ("memoria.pdf", "extrato.pdf")])
checa(3, "o complementar que veio ANTES da guia ja estava na tarefa quando ela saiu",
      ENVIOS == [{"tarefa_id": t_das.id, "complementares": 2}], ENVIOS)
checa(4, "outra competencia nao vira complementar", por["velho.pdf"]["status"] == "erro", por["velho.pdf"])
checa(5, "a resposta nao carrega campos internos",
      not any("empresa_ids" in r or "sem_obrigacao" in r for r in res))
compl = db.query(TarefaComplementar).filter(TarefaComplementar.tarefa_id == t_das.id).all()
checa(6, "os arquivos estao no volume com o nome original",
      sorted(up.nome_de_exibicao(c.arquivo) for c in compl) == ["extrato.pdf", "memoria.pdf"]
      and all(up.caminho_do_anexo(c.arquivo) for c in compl), [c.arquivo for c in compl])

ENVIOS.clear()
res = asyncio.run(processar_lote(db, [("memoria.pdf", b"m")], enviar_falso))
checa(7, "lote sem guia: o arquivo segue como erro, sem ligar a nada",
      res[0]["status"] == "erro" and not ENVIOS, res)

# ------------------------------------------------------------ (c)
print("\n(c) ambiguo")
db.get(Tarefa, t_das.id).status = StatusTarefa.PENDENTE
db.commit()
TEXTOS["guia.pdf"] = TEXTOS["guia.pdf"]       # mesma guia, reanexada
res = asyncio.run(processar_lote(db, [("guia.pdf", b"g2"), ("iss.pdf", b"i"), ("memoria.pdf", b"m")],
                                 enviar_falso))
por = {r["arquivo"]: r for r in res}
checa(8, "duas guias da mesma empresa e competencia: complementar ambiguo",
      por["memoria.pdf"]["status"] == "ambiguo" and "DAS" in por["memoria.pdf"]["detalhe"]
      and "ISS" in por["memoria.pdf"]["detalhe"], por["memoria.pdf"])
checa(9, "e a guia reanexada levou embora os complementares da anterior",
      db.query(TarefaComplementar).filter(TarefaComplementar.tarefa_id == t_das.id).count() == 0
      and not any(up.caminho_do_anexo(c) for c in [x.arquivo for x in compl]))

# ------------------------------------------------------------ (d)
print("\n(d) mensagem e link")
t = db.get(Tarefa, t_das.id)
t.status = StatusTarefa.PENDENTE
up.salvar_complementar(db, t, "memoria.pdf", b"conteudo-memoria")
db.commit()
db.refresh(t)
m = ec.montar_mensagem(t, "Cliente Ficticio Ltda", "https://x/receber/abc")
checa(10, "a mensagem diz 'Baixar os documentos' e quantos complementares vao",
      "Baixar os documentos: https://x/receber/abc" in m["texto"]
      and "Junto vão 1 documento(s) complementar(es)." in m["texto"]
      and "Baixar os documentos" in m["html"], m["texto"])
ens = asyncio.run(ec.entregar_saida(db, t, ensaio=True))
checa(11, "a janela de envio lista os complementares", ens.get("complementares") == ["memoria.pdf"], ens)

MANDADOS = []


def email_falso(to, subject, body, cfg, anexos=None, html=None, imagens=None):
    MANDADOS.append(body)
    return {"success": True}


async def carregar_zap_falso(cfg):
    return {}

email_mod.send_email = email_falso
whatsapp.carregar_zap = carregar_zap_falso
asyncio.run(ec.entregar_saida(db, t, origem="prova"))
env = db.query(TarefaEnvio).filter(TarefaEnvio.tarefa_id == t.id).first()
checa(12, "o link enviado abre a pagina /receber/<token>",
      env and MANDADOS and f"/receber/{env.token}" in MANDADOS[0], MANDADOS[:1])

# ------------------------------------------------------------ (e)
print("\n(e) pagina publica")
cli = TestClient(app.main.app)
r = cli.get(f"/api/publico/documentos/{env.token}")
j = r.json() if r.status_code == 200 else {}
checa(13, "a pagina lista a guia e o complementar",
      [a["tipo"] for a in j.get("arquivos", [])] == ["guia", "complementar"]
      and j.get("guia") == "DAS" and j.get("competencia") == "setembro/2026", (r.status_code, j))
c_id = db.query(TarefaComplementar).filter(TarefaComplementar.tarefa_id == t.id).first().id
antes = db.get(Tarefa, t.id).saida_downloads or 0
r = cli.get(f"/api/publico/baixar/{env.token}/complementar/{c_id}",
            headers={"user-agent": "Mozilla/5.0"})
checa(14, "o complementar baixa com o conteudo certo", r.status_code == 200
      and r.content == b"conteudo-memoria", r.status_code)
db.expire_all()
ac = db.query(SaidaAcesso).filter(SaidaAcesso.tarefa_id == t.id).order_by(SaidaAcesso.id.desc()).first()
checa(15, "o acesso fica registrado com o complementar, sem somar na guia",
      ac and ac.complementar_id == c_id and (db.get(Tarefa, t.id).saida_downloads or 0) == antes,
      ac and (ac.complementar_id, db.get(Tarefa, t.id).saida_downloads))
t_o = db.get(Tarefa, t_outra.id)
t_o.saida_nome = up.salvar_saida(t_o.id, "g.pdf", b"x")
db.commit()
c_outro = up.salvar_complementar(db, t_o, "segredo.pdf", b"de outro cliente")
db.commit()
r = cli.get(f"/api/publico/baixar/{env.token}/complementar/{c_outro.id}")
checa(16, "id de complementar de OUTRA tarefa da 404", r.status_code == 404, r.status_code)
r = cli.get("/api/publico/documentos/token-que-nao-existe")
checa(17, "token invalido da 404", r.status_code == 404, r.status_code)
db.close()

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 17 checagens verdes")
