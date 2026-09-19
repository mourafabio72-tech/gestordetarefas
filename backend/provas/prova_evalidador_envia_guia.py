"""
prova_evalidador_envia_guia.py: a guia reconhecida pelo e-validador sai para o cliente.

Decisões do usuário em 2026-09-19:
  2a. envio automático só se o CNPJ e a competência LIDOS na guia batem com a
      tarefa; valor que veio da IA não conta como lido, e a guia fica anexada
      esperando alguém conferir;
  3a. se nenhum contato recebe, a tarefa fica aberta com a guia anexada;
  4a. os mesmos destinatários e canais do "Enviar ao cliente".

WhatsApp e e-mail são dublês: nada sai para a rede. Os itens 8 a 10 são
não-regressão e passam JÁ no RED. Os itens 11 a 13 vieram do verificador.

    python provas/prova_evalidador_envia_guia.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-envia-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from fastapi.testclient import TestClient                              # noqa: E402
from app.database import Base, engine, SessionLocal                    # noqa: E402
from app.models import (Usuario, Obrigacao, Empresa, Tarefa, StatusTarefa,  # noqa: E402
                        TarefaEnvio)
from app.auth import get_password_hash, create_access_token            # noqa: E402
from app.main import app                                               # noqa: E402
from app.services import validador, whatsapp, email as email_mod       # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app, raise_server_exceptions=False)
TOTAL = 13
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


# Dublês de rede: registram o que sairia e respondem conforme `REDE_OK`.
SAIU = []
REDE_OK = {"valor": True}


async def zap_falso(phone, message, cfg, user_id=None):
    SAIU.append(("whatsapp", phone))
    return {"success": REDE_OK["valor"]}


def email_falso(to, subject, body, cfg, anexos=None):
    SAIU.append(("email", to))
    return {"success": REDE_OK["valor"]}


async def carregar_zap_falso(cfg):
    return {}

whatsapp.send_whatsapp_message = zap_falso
whatsapp.carregar_zap = carregar_zap_falso
email_mod.send_email = email_falso

cab = {"Authorization": "Bearer " + create_access_token(data={"sub": "admin@x.com"})}
db = SessionLocal()
db.add(Usuario(nome="Admin", email="admin@x.com", grupo="admin", ativo=True,
               senha_hash=get_password_hash("x")))
com = Empresa(razao_social="Cliente Com Contato", cnpj="11.222.333/0001-81",
              email="financeiro@cliente.com", telefone="21999998888")
sem = Empresa(razao_social="Cliente Sem Contato", cnpj="44.555.666/0001-99")
o_ent = Obrigacao(nome="darf_teste", sentido="entregar", identificadores="GUIA GAMA")
o_rec = Obrigacao(nome="comprovante", sentido="receber", identificadores="COMPROVANTE ALFA")
db.add_all([com, sem, o_ent, o_rec])
db.commit()


def nova(emp, obr, comp):
    t = Tarefa(titulo=obr.nome, empresa_id=emp.id, obrigacao_id=obr.id,
               competencia=comp, status=StatusTarefa.PENDENTE)
    db.add(t)
    db.commit()
    return t.id


t_ok = nova(com, o_ent, "05/2026")
t_falha = nova(com, o_ent, "06/2026")
t_ia = nova(com, o_ent, "07/2026")
t_sem = nova(sem, o_ent, "05/2026")
t_rec = nova(com, o_rec, "05/2026")
t_exc = nova(com, o_ent, "08/2026")
t_lote = nova(com, o_ent, "09/2026")

TEXTOS = {
    "guia_maio.pdf": "GUIA GAMA CNPJ 11.222.333/0001-81 Período de Apuração 31/05/2026",
    "guia_junho.pdf": "GUIA GAMA CNPJ 11.222.333/0001-81 Período de Apuração 30/06/2026",
    "guia_ilegivel.pdf": "GUIA GAMA CNPJ 11.222.333/0001-81 sem data legível",
    "guia_sem.pdf": "GUIA GAMA CNPJ 44.555.666/0001-99 Período de Apuração 31/05/2026",
    "comprovante.pdf": "COMPROVANTE ALFA CNPJ 11.222.333/0001-81 01/05/2026 a 31/05/2026",
    "guia_agosto.pdf": "GUIA GAMA CNPJ 11.222.333/0001-81 Período de Apuração 31/08/2026",
    "guia_setembro.pdf": "GUIA GAMA CNPJ 11.222.333/0001-81 Período de Apuração 30/09/2026",
}
validador.ler_arquivo = lambda nome, conteudo: TEXTOS[nome]
# A IA "acha" a competência que a guia ilegível não mostra: não conta como lida.
validador.ia_mod.disponivel = lambda cfg: True
validador.ia_mod.extrair = lambda texto, ativas, cfg: {"competencia": "07/2026"}


def subir(nome):
    buf = io.StringIO()
    with redirect_stdout(buf):
        r = client.post("/api/evalidador/processar", headers=cab,
                        files=[("arquivos", (nome, io.BytesIO(b"%PDF " + nome.encode()),
                                             "application/pdf"))])
    logs = []
    for linha in buf.getvalue().splitlines():
        if linha.strip().startswith("{"):
            try:
                logs.append(json.loads(linha))
            except json.JSONDecodeError:
                pass
    res = (r.json().get("resultados") or [{}])[0] if r.status_code == 200 else {}
    return res, logs


def tarefa(tid):
    s = SessionLocal()
    try:
        return s.query(Tarefa).filter(Tarefa.id == tid).first()
    finally:
        s.close()


def envios(tid):
    s = SessionLocal()
    try:
        return s.query(TarefaEnvio).filter(TarefaEnvio.tarefa_id == tid).all()
    finally:
        s.close()


# 1 a 3. guia reconhecida e conferida: sai para os dois contatos e conclui
SAIU.clear()
res, logs = subir("guia_maio.pdf")
t = tarefa(t_ok)
checa(1, f"status 'enviada' ({res.get('status')}: {res.get('detalhe')})", res.get("status") == "enviada")
checa(2, f"saiu para WhatsApp e e-mail do cliente: {SAIU}",
      sorted(c for c, _ in SAIU) == ["email", "whatsapp"])
checa(3, f"tarefa concluída, guia na saída, um envio registrado por destinatário ({t.status})",
      t.status == StatusTarefa.CONCLUIDA and t.saida_nome
      and len([e for e in envios(t_ok) if e.sucesso]) == 2)

# 4. log: uma linha, com a contagem, sem endereço nem telefone
linha = [l for l in logs if l.get("event") == "EDICAO_REGISTRO_CRITICO"
         and l.get("acao") == "envio_cliente"]
bruto = json.dumps(linha, ensure_ascii=False)
checa(4, f"uma linha de log do envio, sem e-mail nem telefone: {linha}",
      len(linha) == 1 and linha[0].get("enviados") == 2 and linha[0].get("origem") == "evalidador"
      and "financeiro@cliente.com" not in bruto and "99998888" not in bruto)

# 5. nenhum envio funciona: a tarefa fica aberta com a guia anexada
SAIU.clear()
REDE_OK["valor"] = False
res, _ = subir("guia_junho.pdf")
REDE_OK["valor"] = True
t = tarefa(t_falha)
checa(5, f"envio falhou: status {res.get('status')}, tarefa {t.status}, guia anexada",
      res.get("status") == "envio_falhou" and t.status == StatusTarefa.PENDENTE and t.saida_nome)

# 6. competência que veio da IA não conta como lida: nada sai
SAIU.clear()
res, _ = subir("guia_ilegivel.pdf")
t = tarefa(t_ia)
checa(6, f"competência da IA: status {res.get('status')}, saiu {SAIU}, tarefa {t.status}",
      res.get("status") == "aguardando_conferencia" and SAIU == []
      and t.status == StatusTarefa.PENDENTE and t.saida_nome)

# 7. empresa sem contato: nada sai, a guia fica anexada
SAIU.clear()
res, _ = subir("guia_sem.pdf")
t = tarefa(t_sem)
checa(7, f"sem destinatário: status {res.get('status')}, tarefa {t.status}",
      res.get("status") == "sem_destinatario" and SAIU == []
      and t.status == StatusTarefa.PENDENTE and t.saida_nome)

# 8. não-regressão: comprovante de receber baixa como antes, sem envio
SAIU.clear()
res, _ = subir("comprovante.pdf")
checa(8, f"receber continua baixando sem enviar nada: {res.get('status')}, saiu {SAIU}",
      res.get("status") == "baixada" and SAIU == []
      and tarefa(t_rec).status == StatusTarefa.CONCLUIDA)

# 9. não-regressão: guia de tarefa já concluída não sai de novo
SAIU.clear()
res, _ = subir("guia_maio.pdf")
checa(9, f"tarefa já concluída não reenvia: {res.get('status')}, saiu {SAIU}",
      res.get("status") == "ja_baixada" and SAIU == [])

# 10. não-regressão: o "Enviar ao cliente" da tela continua enviando e concluindo
SAIU.clear()
r = client.post(f"/api/tarefas/{t_falha}/enviar-cliente", headers=cab)
checa(10, f"Enviar ao cliente da tela: {r.status_code}, saiu {SAIU}, tarefa {tarefa(t_falha).status}",
      r.status_code == 200 and len(SAIU) == 2 and tarefa(t_falha).status == StatusTarefa.CONCLUIDA)

# 11 a 13. Achado do verificador: o WhatsApp levanta exceção de rede DEPOIS de
# o e-mail já ter saído. Antes, a transação caía, o envio real sumia do banco
# e o lote inteiro dava 500. Agora cada envio fica registrado na hora, a falha
# de um destinatário não derruba os outros, e o lote segue.
async def zap_explode(phone, message, cfg, user_id=None):
    SAIU.append(("whatsapp", phone))
    raise RuntimeError("timeout de rede")
whatsapp.send_whatsapp_message = zap_explode
SAIU.clear()
buf = io.StringIO()
with redirect_stdout(buf):
    r = client.post("/api/evalidador/processar", headers=cab, files=[
        ("arquivos", ("guia_agosto.pdf", io.BytesIO(b"%PDF a"), "application/pdf")),
        ("arquivos", ("guia_setembro.pdf", io.BytesIO(b"%PDF s"), "application/pdf"))])
whatsapp.send_whatsapp_message = zap_falso
res = r.json().get("resultados", []) if r.status_code == 200 else []
ev = envios(t_exc)
checa(11, f"lote não cai: HTTP {r.status_code}, {len(res)} resultados", r.status_code == 200 and len(res) == 2)
checa(12, f"o e-mail que saiu fica registrado, e o WhatsApp como falha: {[(e.canal, e.sucesso) for e in ev]}",
      sorted((e.canal, e.sucesso) for e in ev) == [("email", True), ("whatsapp", False)])
checa(13, f"alguém recebeu, então conclui ({tarefa(t_exc).status}); a segunda guia do lote também sai ({tarefa(t_lote).status})",
      tarefa(t_exc).status == StatusTarefa.CONCLUIDA and tarefa(t_lote).status == StatusTarefa.CONCLUIDA)

db.close()
print()
if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print(f"PROVA OK: {TOTAL} checagens verdes")
