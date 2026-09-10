"""Prova da Fase 23: autorizacao e sessao passam a deixar rastro.

A `Padrao_Logging_Estruturado` da vault tem duas tabelas. A dos oito campos foi
cumprida pelas fases 18 a 20. Esta prova cobre quatro eventos da OUTRA tabela,
"O que SEMPRE entra em log", que o app pratica e nao registrava:
`ACESSO_NEGADO_403`, `ACESSO_NEGADO_IDOR`, `MUDANCA_ROLE` e `LOGOUT`.

    cd backend && ./venv/bin/python provas/prova_eventos_log.py

Mede o que sai no stdout de verdade, e nao o que o codigo parece fazer. Roda
contra as rotas reais, num SQLite temporario, e nao deixa arquivo para tras.

Tres itens sao de NAO-REGRESSAO, e estao aqui de proposito: o evento novo nao
pode mudar o status nem o corpo que o cliente recebe. A `Padrao_IDOR` e
explicita nisso, e um 403 no lugar do 404 confirmaria ao atacante que o recurso
existe. Sao os itens 4, 9 e 10.
"""

from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_eventos_")
_banco = os.path.join(_tmp, "prova.db")

# Precisam existir ANTES de importar o app: `database.py` le a URL no import.
os.environ["DATABASE_URL"] = f"sqlite:///{_banco}"
os.environ["SECRET_KEY"] = "chave-jwt-de-teste"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import Depends                                    # noqa: E402
from fastapi.testclient import TestClient                      # noqa: E402

from app.auth import (get_password_hash, require_grupos,       # noqa: E402
                      require_perm, require_flag)
from app.database import Base, engine, SessionLocal            # noqa: E402
from app.seguranca import log_event                            # noqa: E402
from app.models import Empresa, Setor, Tarefa, Usuario         # noqa: E402
from app.main import app                                       # noqa: E402

Base.metadata.create_all(bind=engine)

SENHA = "senha-boa-123"
EMAIL_ADMIN = "chefe@bps4.com.br"
EMAIL_ANALISTA = "analista@bps4.com.br"
EMAIL_CURIOSO = "curioso@bps4.com.br"

CAMPOS = ["timestamp", "level", "event", "user_id", "ip", "request_id",
          "path", "method"]

# Lista absoluta da nota, na forma de pedaco de nome de chave.
PROIBIDAS = ["senha", "password", "token", "authorization", "cookie", "csrf",
             "cpf", "cartao", "secret"]


# As tres guardas de `app/auth.py` sao o ponto unico por onde passa toda
# negativa vertical do app: quatorze rotas devolvem 403, e todas por aqui. Sao
# rotas de prova porque o que se mede e a GUARDA, e nao a rota que a usa.
@app.get("/api/_prova_grupo")
def _prova_grupo(u: Usuario = Depends(require_grupos("admin"))):
    return {"ok": True}


@app.get("/api/_prova_perm")
def _prova_perm(u: Usuario = Depends(require_perm("usuarios", "ver"))):
    return {"ok": True}


@app.get("/api/_prova_flag")
def _prova_flag(u: Usuario = Depends(require_flag("apagar_anexo"))):
    return {"ok": True}


cliente = TestClient(app)

ids = {}


def semear():
    db = SessionLocal()
    try:
        admin = Usuario(nome="Chefe", email=EMAIL_ADMIN, grupo="admin",
                        senha_hash=get_password_hash(SENHA), ativo=True)
        # 'analista' e o papel com `escopo_tarefas: proprias`, e por isso o
        # unico que enxerga so o que e dele. Ele tambem tem `usuarios: nenhum`
        # e `apagar_anexo: False`, entao as tres guardas recusam com ele.
        analista = Usuario(nome="Analista", email=EMAIL_ANALISTA,
                           grupo="analista",
                           senha_hash=get_password_hash(SENHA), ativo=True)
        alvo = Usuario(nome="Alvo do Papel", email="alvo@bps4.com.br",
                       grupo="analista",
                       senha_hash=get_password_hash(SENHA), ativo=True)
        # Analista com a flag de dispensar ligada por override, e so ela: o
        # escopo continua `proprias`. E o unico jeito de as rotas de DELETE e
        # de nao-se-aplica chegarem ao ponto de IDOR em vez de pararem antes,
        # no 403 da guarda.
        curioso = Usuario(nome="Curioso", email=EMAIL_CURIOSO, grupo="analista",
                          permissoes=json.dumps({"dispensar_demanda": True}),
                          senha_hash=get_password_hash(SENHA), ativo=True)
        db.add(curioso)
        empresa = Empresa(razao_social="Cliente Teste", cnpj="00000000000191")
        setor = Setor(nome="Fiscal")
        db.add_all([admin, analista, alvo, empresa, setor])
        db.commit()
        # Tarefa do ADMIN: existe, e esta fora do escopo do analista. E esse o
        # caso de IDOR, e nao o id inexistente.
        tarefa = Tarefa(titulo="Tarefa do chefe", empresa_id=empresa.id,
                        setor_id=setor.id, responsavel_id=admin.id)
        db.add(tarefa)
        db.commit()
        ids.update(admin=admin.id, analista=analista.id, alvo=alvo.id,
                   tarefa=tarefa.id)
    finally:
        db.close()


def entrar(email):
    r = cliente.post("/api/auth/login", json={"email": email, "senha": SENHA})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def capturar(funcao):
    """Roda `funcao` com o stdout desviado e devolve (retorno, linhas JSON)."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        retorno = funcao()
    linhas = []
    for bruta in buffer.getvalue().splitlines():
        bruta = bruta.strip()
        if not bruta.startswith("{"):
            continue
        try:
            linhas.append(json.loads(bruta))
        except json.JSONDecodeError:
            continue
    return retorno, linhas


def evento(linhas, nome):
    """A primeira linha com aquele evento, ou None."""
    for linha in linhas:
        if linha.get("event") == nome:
            return linha
    return None


semear()
falhou = []
todas_as_linhas = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


admin = entrar(EMAIL_ADMIN)
analista = entrar(EMAIL_ANALISTA)
curioso = entrar(EMAIL_CURIOSO)


# ------------------------------------------------- (a) ACESSO_NEGADO_403
r_grupo, l_grupo = capturar(
    lambda: cliente.get("/api/_prova_grupo", headers=analista))
r_perm, l_perm = capturar(
    lambda: cliente.get("/api/_prova_perm", headers=analista))
r_flag, l_flag = capturar(
    lambda: cliente.get("/api/_prova_flag", headers=analista))
todas_as_linhas += l_grupo + l_perm + l_flag

e_grupo = evento(l_grupo, "ACESSO_NEGADO_403")
e_perm = evento(l_perm, "ACESSO_NEGADO_403")
e_flag = evento(l_flag, "ACESSO_NEGADO_403")

checa(1, "require_grupos recusando emite ACESSO_NEGADO_403 dizendo qual grupo",
      e_grupo is not None and "admin" in str(e_grupo.get("exigido", "")))
checa(2, "require_perm recusando emite ACESSO_NEGADO_403 com recurso e nivel",
      e_perm is not None
      and e_perm.get("recurso") == "usuarios" and e_perm.get("nivel") == "ver")
checa(3, "require_flag recusando emite ACESSO_NEGADO_403 com a flag",
      e_flag is not None and e_flag.get("flag") == "apagar_anexo")
checa(4, "NAO-REGRESSAO: o 403 continua 403, com o mesmo corpo de hoje",
      r_grupo.status_code == 403 and r_perm.status_code == 403
      and r_flag.status_code == 403
      and r_grupo.json() == {"detail": "Você não tem permissão para esta ação"}
      and r_perm.json() == {"detail": "Sem permissão de 'ver' em 'usuarios'"}
      and r_flag.json() == {"detail": "Sem permissão para a ação 'apagar_anexo'"})
checa(5, "o 403 sai em nivel WARN, e nao INFO: recusa nao e rotina",
      e_grupo is not None and e_grupo.get("level") == "WARN")

# Quem PODE nao gera evento nenhum. Sem este item, um `log_event` posto no
# lugar errado (fora do `if`) passaria nos itens acima e encheria o log.
_, l_permitido = capturar(
    lambda: cliente.get("/api/_prova_grupo", headers=admin))
checa(6, "quem tem permissao NAO gera ACESSO_NEGADO_403",
      evento(l_permitido, "ACESSO_NEGADO_403") is None)


# ------------------------------------------------ (b) ACESSO_NEGADO_IDOR
r_idor, l_idor = capturar(
    lambda: cliente.get(f"/api/tarefas/{ids['tarefa']}/envios",
                        headers=analista))
r_inexistente, l_inexistente = capturar(
    lambda: cliente.get("/api/tarefas/999999/envios", headers=analista))
todas_as_linhas += l_idor + l_inexistente

e_idor = evento(l_idor, "ACESSO_NEGADO_IDOR")

checa(7, "recurso que EXISTE e nao e do usuario emite ACESSO_NEGADO_IDOR",
      e_idor is not None)
checa(8, "a linha do IDOR traz `recurso` e `recurso_id`, como o exemplo da nota",
      e_idor is not None and e_idor.get("recurso") == "tarefa"
      and e_idor.get("recurso_id") == ids["tarefa"])
checa(9, "id INEXISTENTE nao emite evento nenhum: digitacao errada nao e ataque",
      evento(l_inexistente, "ACESSO_NEGADO_IDOR") is None)
checa(10, "NAO-REGRESSAO: os dois casos devolvem 404 com o MESMO corpo",
      r_idor.status_code == 404 and r_inexistente.status_code == 404
      and r_idor.json() == r_inexistente.json())

# O dono nao dispara nada, pelo mesmo motivo do item 6.
_, l_dono = capturar(
    lambda: cliente.get(f"/api/tarefas/{ids['tarefa']}/envios", headers=admin))
checa(11, "o dono do recurso NAO gera ACESSO_NEGADO_IDOR",
      evento(l_dono, "ACESSO_NEGADO_IDOR") is None)

# O segundo ponto de busca por id unico, para o helper nao ficar aplicado pela
# metade: quem cobre `/envios` tem de cobrir o anexo tambem.
_, l_anexo = capturar(
    lambda: cliente.get(f"/api/tarefas/{ids['tarefa']}/anexo",
                        headers=analista))
checa(12, "a rota do anexo tambem emite IDOR, e nao so a de envios",
      evento(l_anexo, "ACESSO_NEGADO_IDOR") is not None)


# ------------------------------------------------------ (c) MUDANCA_ROLE
def _trocar_papel():
    return cliente.put(f"/api/usuarios/{ids['alvo']}",
                       json={"grupo": "gestor"}, headers=admin)


r_papel, l_papel = capturar(_trocar_papel)
todas_as_linhas += l_papel
e_papel = evento(l_papel, "MUDANCA_ROLE")

checa(13, "trocar o grupo de outro usuario emite MUDANCA_ROLE",
      r_papel.status_code == 200 and e_papel is not None)
checa(14, "a linha diz o alvo, o papel de ANTES e o de DEPOIS",
      e_papel is not None and e_papel.get("alvo_id") == ids["alvo"]
      and e_papel.get("de") == "analista" and e_papel.get("para") == "gestor")

# O erro classico deste evento e ler o valor anterior DEPOIS da atribuicao, e
# gravar o novo duas vezes. Este item so passa se a leitura vier antes.
checa(15, "o papel de antes e diferente do de depois: nao gravou o novo duas vezes",
      e_papel is not None and e_papel.get("de") != e_papel.get("para"))

_, l_sem_papel = capturar(
    lambda: cliente.put(f"/api/usuarios/{ids['alvo']}",
                        json={"nome": "Alvo Renomeado"}, headers=admin))
checa(16, "editar outro campo, sem tocar no papel, NAO emite MUDANCA_ROLE",
      evento(l_sem_papel, "MUDANCA_ROLE") is None)

_, l_permissoes = capturar(
    lambda: cliente.put(f"/api/usuarios/{ids['alvo']}",
                        json={"permissoes": {"empresas": "editar"}},
                        headers=admin))
checa(17, "mudar as permissoes, e nao o grupo, tambem emite MUDANCA_ROLE",
      evento(l_permissoes, "MUDANCA_ROLE") is not None)


# ------------------------------------------------------------ (d) LOGOUT
r_logout, l_logout = capturar(
    lambda: cliente.post("/api/auth/logout", headers=analista))
todas_as_linhas += l_logout
e_logout = evento(l_logout, "LOGOUT")

checa(18, "POST /api/auth/logout devolve 200 e emite LOGOUT",
      r_logout.status_code == 200 and e_logout is not None)
checa(19, "a linha do LOGOUT diz QUEM saiu",
      e_logout is not None and e_logout.get("user_id") == ids["analista"])

r_sem_token = cliente.post("/api/auth/logout")
checa(20, "logout sem token devolve 401: a rota e autenticada como as outras",
      r_sem_token.status_code == 401)


# -------------------------------------------- (e) os oito campos e a lista
novos = [linha for linha in todas_as_linhas
         if linha.get("event") in ("ACESSO_NEGADO_403", "ACESSO_NEGADO_IDOR",
                                   "MUDANCA_ROLE", "LOGOUT")]

checa(21, "toda linha nova traz os oito campos da nota, na ordem da tabela",
      len(novos) >= 4
      and all(list(linha)[:8] == CAMPOS for linha in novos))
checa(22, "toda linha nova tem request_id, path e method preenchidos",
      len(novos) >= 4
      and all(linha.get("request_id") and linha.get("path")
              and linha.get("method") for linha in novos))

achados = []
for linha in novos:
    for chave in linha:
        for proibida in PROIBIDAS:
            if proibida in chave.lower():
                achados.append((linha.get("event"), chave))
checa(23, f"nenhuma linha nova carrega campo da lista proibida (achados: {achados})",
      not achados)


# --------------------------- (f) os chamadores irmaos, achado do verificador
# O helper de IDOR nasceu ligado a `_tarefa_no_escopo` e a rota do anexo, e
# ficou de fora de QUATRO rotas que fazem a mesma pergunta por outro caminho:
# buscam a tarefa sem escopo e depois chamam o predicado `_no_escopo`. Entre
# elas esta o `GET /api/tarefas/{id}`, que e a rota de IDOR mais obvia que
# existe. Este bloco varre as quatro, e a lista e explicita para nao depender
# de nenhuma delas continuar existindo em silencio.
#
# O `DELETE` e o `nao-se-aplica` exigem a flag `dispensar_demanda`, que o
# analista nao tem: com ele as duas param no 403 da guarda e nunca chegam ao
# ponto de IDOR. Por isso as quatro rodam com um usuario que TEM a flag e
# continua com escopo `proprias`. Sem esse cuidado, dois itens passariam sem
# medir nada, que e o pior tipo de verde.
IRMAS = [
    ("GET tarefa", lambda h: cliente.get(f"/api/tarefas/{ids['tarefa']}",
                                         headers=h)),
    ("PUT tarefa", lambda h: cliente.put(f"/api/tarefas/{ids['tarefa']}",
                                         json={"titulo": "invadida"},
                                         headers=h)),
    ("POST nao-se-aplica",
     lambda h: cliente.post(f"/api/tarefas/{ids['tarefa']}/nao-se-aplica",
                            json={"motivo": "invadindo"}, headers=h)),
    ("DELETE tarefa", lambda h: cliente.delete(f"/api/tarefas/{ids['tarefa']}",
                                               headers=h)),
]

sem_evento = []
sem_404 = []
for nome, chamada in IRMAS:
    resposta, linhas = capturar(lambda: chamada(curioso))
    if evento(linhas, "ACESSO_NEGADO_IDOR") is None:
        sem_evento.append(nome)
    if resposta.status_code != 404:
        sem_404.append(f"{nome}={resposta.status_code}")
    todas_as_linhas += linhas

checa(24, f"as 4 rotas irmas tambem emitem IDOR (mudas: {sem_evento})",
      not sem_evento)
checa(25, f"e as 4 continuam devolvendo 404, e nao 403 (fora: {sem_404})",
      not sem_404)

falso_positivo = []
for nome, chamada in IRMAS:
    _, linhas = capturar(lambda: chamada(admin))
    if evento(linhas, "ACESSO_NEGADO_IDOR") is not None:
        falso_positivo.append(nome)
checa(26, f"e o DONO nao dispara nada nelas (falso positivo: {falso_positivo})",
      not falso_positivo)


# ------------- (g) MUDANCA_ROLE pela porta lateral: a importacao em lote
# `services/importador_usuarios.py` troca o `grupo` de quem ja existe, que e a
# mesma mutacao que o PUT registra. Sem esta cobertura, quem quiser mudar papel
# sem deixar rastro sobe uma planilha.
def _planilha_trocando_papel():
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["nome", "email", "nivel"])
    # O alvo esta como 'gestor' desde o item 13. A planilha o rebaixa.
    ws.append(["Alvo do Papel", "alvo@bps4.com.br", "consulta"])
    # Uma segunda linha que NAO muda papel nenhum, para o item 28.
    ws.append(["Analista", EMAIL_ANALISTA, "analista"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


_, l_import = capturar(
    lambda: cliente.post(
        "/api/usuarios/importar",
        files={"arquivo": ("usuarios.xlsx", _planilha_trocando_papel(),
                           "application/vnd.openxmlformats-officedocument"
                           ".spreadsheetml.sheet")},
        headers=admin))
todas_as_linhas += l_import
papeis_no_lote = [linha for linha in l_import
                  if linha.get("event") == "MUDANCA_ROLE"]

checa(27, "importar planilha que troca o papel de alguem emite MUDANCA_ROLE",
      len(papeis_no_lote) >= 1)
checa(28, "e emite UMA linha por papel que mudou de fato, nao uma por linha "
          f"da planilha (saiu: {len(papeis_no_lote)})",
      len(papeis_no_lote) == 1)
checa(29, "a linha do lote diz de onde para onde, como a do PUT",
      bool(papeis_no_lote)
      and papeis_no_lote[0].get("de") == "gestor"
      and papeis_no_lote[0].get("para") == "consulta")


# -------- (h) o logger nao pode derrubar quem ele registra, achado adversarial
# `log_event` monta a linha com `json.dumps` e nao valida os `**campos`. Um
# campo nao serializavel levanta TypeError DENTRO da guarda, e a recusa vira
# 500. Nas rotas de IDOR isso e pior do que parece: `existe=False` nunca chama
# o logger e continua 404, `existe=True` estoura e vira 500, e o STATUS passa a
# dizer se o recurso existe, que e exatamente o oraculo que a funcao existe
# para fechar.
@app.get("/api/_prova_log_quebrado")
def _prova_log_quebrado():
    log_event("PROVA_CAMPO_IMPOSSIVEL", bicho=object())
    return {"ok": True}


# `raise_server_exceptions=False` para ver a resposta que o cliente REAL
# receberia, e nao a excecao que o TestClient relanca por padrao.
cliente_real = TestClient(app, raise_server_exceptions=False)
r_quebrado, l_quebrado = capturar(
    lambda: cliente_real.get("/api/_prova_log_quebrado"))

checa(30, "campo nao serializavel no log NAO derruba a requisicao",
      r_quebrado.status_code == 200)
linha_quebrada = evento(l_quebrado, "PROVA_CAMPO_IMPOSSIVEL")
checa(31, "e a linha SAI mesmo assim, com o campo convertido em texto",
      linha_quebrada is not None
      and "object object at" in str(linha_quebrada.get("bicho", "")))


# ------- (i) MUDANCA_ROLE nao pode nascer de ordem de chave, achado adversarial
# As permissoes sao gravadas como TEXTO JSON. Reenviar o mesmo conteudo com as
# chaves em outra ordem gera outra string, e a comparacao literal daria mudanca
# onde nao houve. Evento de auditoria que dispara sozinho vira ruido, e ruido e
# o que faz ninguem mais olhar o log.
MESMAS = {"empresas": "editar", "usuarios": "ver"}
capturar(lambda: cliente.put(f"/api/usuarios/{ids['alvo']}",
                             json={"permissoes": MESMAS}, headers=admin))
_, l_reordenado = capturar(
    lambda: cliente.put(f"/api/usuarios/{ids['alvo']}",
                        json={"permissoes": dict(reversed(list(MESMAS.items())))},
                        headers=admin))
checa(32, "reenviar as MESMAS permissoes em outra ordem NAO emite MUDANCA_ROLE",
      evento(l_reordenado, "MUDANCA_ROLE") is None)

_, l_mudou = capturar(
    lambda: cliente.put(f"/api/usuarios/{ids['alvo']}",
                        json={"permissoes": {"empresas": "ver"}}, headers=admin))
checa(33, "e mudanca de verdade na permissao continua emitindo",
      evento(l_mudou, "MUDANCA_ROLE") is not None)


print()
if falhou:
    print(f"PROVA FALHOU nos itens: {sorted(set(falhou))}")
    sys.exit(1)
print(f"PROVA OK: {33 - len(falhou)} checagens verdes")
