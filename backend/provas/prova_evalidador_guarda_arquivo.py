"""
prova_evalidador_guarda_arquivo.py: o e-validador guarda o arquivo que baixa.

Achado de 2026-09-19: `processar` gravava na tarefa só o NOME do arquivo
(`tarefa.anexo_nome = nome_arquivo`) e jogava o conteúdo fora. O acervo listava
o recibo, e o download respondia 410, "O arquivo não está mais no
armazenamento". Nunca esteve. O link público (`registrar_baixa`) sempre salvou;
o e-validador, não.

A guia de "entregar" vai para o documento de SAÍDA (`saida_nome`), que é o que
o "Enviar ao cliente" lê, e troca a guia anterior do mesmo jeito que a rota de
anexar: apaga a velha e revoga os links já enviados.

Os itens 7 e 8 são não-regressão da rota de anexar e passam JÁ no RED.

    python provas/prova_evalidador_guarda_arquivo.py
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-guarda-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from fastapi.testclient import TestClient                              # noqa: E402
from app.database import Base, engine, SessionLocal                    # noqa: E402
from app.models import (Usuario, Obrigacao, Empresa, Tarefa, StatusTarefa,  # noqa: E402
                        TarefaEnvio)
from app.auth import get_password_hash, create_access_token            # noqa: E402
from app.main import app                                               # noqa: E402
from app.services import validador, upload as up                       # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app, raise_server_exceptions=False)
TOTAL = 8
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


cab = {"Authorization": "Bearer " + create_access_token(data={"sub": "admin@x.com"})}
db = SessionLocal()
db.add(Usuario(nome="Admin", email="admin@x.com", grupo="admin", ativo=True,
               senha_hash=get_password_hash("x")))
emp = Empresa(razao_social="Cliente Prova", cnpj="11.222.333/0001-81")
o_rec = Obrigacao(nome="comprovante", sentido="receber", identificadores="COMPROVANTE ALFA")
o_tra = Obrigacao(nome="sped", sentido="transmitir", identificadores="RECIBO BETA")
o_ent = Obrigacao(nome="guia", sentido="entregar", identificadores="GUIA GAMA")
db.add_all([emp, o_rec, o_tra, o_ent])
db.commit()


def nova_tarefa(obrigacao, competencia="05/2026"):
    t = Tarefa(titulo=obrigacao.nome, empresa_id=emp.id, obrigacao_id=obrigacao.id,
               competencia=competencia, status=StatusTarefa.PENDENTE)
    db.add(t)
    db.commit()
    return t.id


t_rec, t_tra, t_ent = nova_tarefa(o_rec), nova_tarefa(o_tra), nova_tarefa(o_ent)
t_ent2 = nova_tarefa(o_ent, "06/2026")

TEXTOS = {
    "comprovante.pdf": "COMPROVANTE ALFA CNPJ 11.222.333/0001-81 01/05/2026 a 31/05/2026",
    "recibo.pdf": "RECIBO BETA CNPJ 11.222.333/0001-81 01/05/2026 a 31/05/2026",
    "guia.pdf": "GUIA GAMA CNPJ 11.222.333/0001-81 01/05/2026 a 31/05/2026",
    "guia_junho.pdf": "GUIA GAMA CNPJ 11.222.333/0001-81 01/06/2026 a 30/06/2026",
}
validador.ler_arquivo = lambda nome, conteudo: TEXTOS[nome]


def tarefa(tid):
    s = SessionLocal()
    try:
        return s.query(Tarefa).filter(Tarefa.id == tid).first()
    finally:
        s.close()


# 1 e 2. receber e transmitir: o arquivo existe e o download devolve o conteúdo
for n, arq, tid in [(1, "comprovante.pdf", t_rec), (2, "recibo.pdf", t_tra)]:
    corpo = f"conteudo de {arq}".encode()
    res = validador.processar(SessionLocal(), arq, corpo)
    t = tarefa(tid)
    r = client.get(f"/api/tarefas/{tid}/anexo", headers=cab)
    checa(n, f"{arq}: {res.get('status')}, arquivo no volume e download {r.status_code}",
          res.get("status") == "baixada" and up.caminho_do_anexo(t.anexo_nome) is not None
          and r.status_code == 200 and r.content == corpo)

# 3. o download guarda o nome original, sem prefixo
r = client.get(f"/api/tarefas/{t_rec}/anexo", headers=cab)
checa(3, f"download devolve o nome original: {r.headers.get('content-disposition')}",
      "comprovante.pdf" in (r.headers.get("content-disposition") or "")
      and "ev" not in (r.headers.get("content-disposition") or "").split("filename")[-1][:5])

# 4. entregar: a guia vai para a SAÍDA, e não para o comprovante
corpo = b"guia de maio"
res = validador.processar(SessionLocal(), "guia.pdf", corpo)
t = tarefa(t_ent)
r = client.get(f"/api/tarefas/{t_ent}/saida", headers=cab)
checa(4, f"guia de entregar vai para saida_nome e o download da saída dá {r.status_code}",
      t.saida_nome and not t.anexo_nome and r.status_code == 200 and r.content == corpo)

# 5 e 6. guia nova no lugar de uma anexada antes: a velha sai e os links morrem
s = SessionLocal()
t2 = s.query(Tarefa).filter(Tarefa.id == t_ent2).first()
t2.saida_nome = up.salvar_saida(t2.id, "velha.pdf", b"guia velha")
velha = t2.saida_nome
t2.saida_token = "token-velho"
s.add(TarefaEnvio(tarefa_id=t2.id, arquivo="velha.pdf", canal="email", endereco="x@x.com",
                  destinatario="X", token="envio-velho", sucesso=True))
s.commit()
s.close()
validador.processar(SessionLocal(), "guia_junho.pdf", b"guia nova")
t = tarefa(t_ent2)
s = SessionLocal()
tokens = [e.token for e in s.query(TarefaEnvio).filter(TarefaEnvio.tarefa_id == t_ent2).all()]
s.close()
checa(5, "a guia velha sai do volume e a nova fica no lugar",
      up.caminho_do_anexo(velha) is None and up.ler_arquivo_salvo(t.saida_nome) == b"guia nova")
checa(6, f"os links já enviados são revogados: saida_token {t.saida_token!r}, envios {tokens}",
      t.saida_token is None and tokens == [None])

# 7 e 8. não-regressão: a rota de anexar continua trocando e revogando
r1 = client.post(f"/api/tarefas/{t_ent}/saida", headers=cab,
                 files={"arquivo": ("manual.pdf", io.BytesIO(b"manual"), "application/pdf")})
t = tarefa(t_ent)
checa(7, f"anexar pela tela continua gravando a saída ({r1.status_code})",
      r1.status_code == 200 and up.ler_arquivo_salvo(t.saida_nome) == b"manual")
checa(8, "anexar pela tela continua zerando o token do link",
      t.saida_token is None)

db.close()
print()
if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print(f"PROVA OK: {TOTAL} checagens verdes")
