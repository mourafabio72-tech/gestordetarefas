"""
prova_prazo_interno.py: o prazo interno da equipe ganha regra própria.

Até 2026-10-02 o prazo interno era só "vencimento menos N dias" ("Lembrar"),
e o usuário não tinha como dizer "a depreciação fica pronta dia 05" quando o
fechamento do cliente é dia 15, nem "o ISS prestado sai no primeiro dia útil".
Decisões do usuário (LASTRO, 2026-10-02):

  1. três modos: antes do vencimento; antes do fechamento do cliente; regra
     própria (primeiro dia útil, último dia útil, dia fixo, N-ésimo dia útil);
  2. as obrigações que já existem mantêm o resultado de hoje;
  3. a etapa ancorada no fechamento continua vencendo no fechamento.

Regras locais: o prazo interno nunca passa do vencimento; "antes do
fechamento" sem fechamento cadastrado cai em "antes do vencimento" com o mesmo
N; a regra própria sempre antecipa dia não útil.

Outubro/2026 abre numa quinta: dias úteis 1, 2, 5, 6, 7, 8, 9, 12...

    python provas/prova_prazo_interno.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-prazo-interno-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from fastapi.testclient import TestClient                        # noqa: E402
from app.database import Base, engine, SessionLocal              # noqa: E402
from app.models import Usuario, Obrigacao, Setor, Empresa, Tarefa  # noqa: E402
from app.auth import get_password_hash, create_access_token      # noqa: E402
from app.main import app                                         # noqa: E402
from app.services import gerador                                 # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app, raise_server_exceptions=False)
TOTAL = 33
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


def tenta(n, descricao, fn):
    """Item que pode quebrar no RED (função ou coluna que ainda não existe)."""
    try:
        res = fn()
        checa(n, f"{descricao} {res[1] if isinstance(res, tuple) else ''}".strip(),
              res[0] if isinstance(res, tuple) else res)
    except Exception as e:                       # noqa: BLE001
        checa(n, f"{descricao} (quebrou: {type(e).__name__}: {str(e)[:90]})", False)


class Emp:
    def __init__(self, tipo=None, dia=None, id_=0):
        self.id, self.fechamento_tipo, self.fechamento_dia = id_, tipo, dia


class Obr:
    """Obrigação em memória, com os campos de prazo de hoje e os três novos."""
    def __init__(self, regra="dia_fixo", regra_dia=20, lembrar=5, tipo_dias="uteis",
                 modo=None, regra_int=None, dia_int=None, ancora=None, ancora_dias=0):
        self.regra_prazo_tipo, self.regra_prazo_dia = regra, regra_dia
        self.ajuste_nao_util, self.sabado_util = "antecipar", False
        self.lembrar_dias_antes, self.tipo_dias = lembrar, tipo_dias
        self.ancora, self.ancora_dias_antes, self.ancora_tipo_dias = ancora, ancora_dias, "uteis"
        self.interno_modo, self.interno_regra_tipo, self.interno_regra_dia = modo, regra_int, dia_int


def datas(o, e):
    v, p = gerador.calc_datas(o, e, 10, 2026)
    return v.isoformat(), p.isoformat()


def hoje(o, e):
    """O cálculo de antes desta fase, copiado do gerador (gerador.py:509-511)."""
    v = gerador.calc_vencimento(o, e, 10, 2026)
    p = gerador.calc_prazo_interno(v, o.lembrar_dias_antes, o.tipo_dias, bool(o.sabado_util))
    return v.isoformat(), p.isoformat()


SEM = Emp()
FECHA15 = Emp("dia_fixo", 15)

# (a) não-regressão: "antes do vencimento" dá a mesma data de hoje
combos = [Obr(lembrar=5, tipo_dias="uteis"), Obr(lembrar=5, tipo_dias="corridos"),
          Obr(regra="ultimo_dia_util", regra_dia=None, lembrar=0),
          Obr(regra="dia_util", regra_dia=10, lembrar=3),
          Obr(ancora="fechamento", ancora_dias=2, lembrar=1)]
for c in combos:
    c.interno_modo = "antes_vencimento"
tenta(1, "(a) antes do vencimento = cálculo de hoje nas 5 combinações, com e sem fechamento",
      lambda: (all(datas(c, e) == hoje(c, e) for c in combos for e in (SEM, FECHA15)), ""))
tenta(2, "(a) obrigação antiga, sem modo gravado (None), também = cálculo de hoje",
      lambda: (all(datas(Obr(lembrar=5, tipo_dias=t), SEM) == hoje(Obr(lembrar=5, tipo_dias=t), SEM)
                   for t in ("uteis", "corridos")), ""))
tenta(3, "(a) dia 20/10 com 5 dias úteis antes: vencimento 20/10, interno 13/10",
      lambda: ((r := datas(Obr(modo="antes_vencimento"), SEM)) == ("2026-10-20", "2026-10-13"), r))

# (b) antes do fechamento
tenta(4, "(b) fechamento dia 15, 10 corridos antes: interno 05/10, vencimento intacto 30/10",
      lambda: ((r := datas(Obr(regra="ultimo_dia_util", regra_dia=None, lembrar=10,
                               tipo_dias="corridos", modo="antes_fechamento"), FECHA15))
               == ("2026-10-30", "2026-10-05"), r))
tenta(5, "(b) fechamento dia 15, 2 dias úteis antes: interno 13/10",
      lambda: ((r := datas(Obr(regra="ultimo_dia_util", regra_dia=None, lembrar=2,
                               modo="antes_fechamento"), FECHA15))[1] == "2026-10-13", r))

# (c) regra própria
venc_fim = dict(regra="ultimo_dia_util", regra_dia=None, modo="regra")
tenta(6, "(c) primeiro dia útil: 01/10",
      lambda: ((r := datas(Obr(**venc_fim, regra_int="primeiro_dia_util"), SEM))[1] == "2026-10-01", r))
tenta(7, "(c) último dia útil: 30/10",
      lambda: ((r := datas(Obr(**venc_fim, regra_int="ultimo_dia_util"), SEM))[1] == "2026-10-30", r))
tenta(8, "(c) dia fixo 5: 05/10",
      lambda: ((r := datas(Obr(**venc_fim, regra_int="dia_fixo", dia_int=5), SEM))[1] == "2026-10-05", r))
tenta(9, "(c) dia fixo 4 (domingo) antecipa para 02/10",
      lambda: ((r := datas(Obr(**venc_fim, regra_int="dia_fixo", dia_int=4), SEM))[1] == "2026-10-02", r))
tenta(10, "(c) 3º dia útil: 05/10",
      lambda: ((r := datas(Obr(**venc_fim, regra_int="dia_util", dia_int=3), SEM))[1] == "2026-10-05", r))

# (d) o interno nunca passa do vencimento
tenta(11, "(d) vencimento dia 10 (sábado, vai a 09/10) e regra dia 20: interno fica em 09/10",
      lambda: ((r := datas(Obr(regra_dia=10, modo="regra", regra_int="dia_fixo", dia_int=20), SEM))
               == ("2026-10-09", "2026-10-09"), r))

# (e) antes do fechamento sem fechamento cadastrado
tenta(12, "(e) sem fechamento: cai em antes do vencimento com o mesmo N",
      lambda: ((r := datas(Obr(lembrar=10, tipo_dias="corridos", modo="antes_fechamento"), SEM))
               == datas(Obr(lembrar=10, tipo_dias="corridos", modo="antes_vencimento"), SEM), r))

# (f) ancorada continua vencendo no fechamento
tenta(13, "(f) ancorada, 0 dias: vencimento no fechamento 15/10; interno antes do fechamento 05/10",
      lambda: ((r := datas(Obr(ancora="fechamento", ancora_dias=0, lembrar=10, tipo_dias="corridos",
                               modo="antes_fechamento"), FECHA15)) == ("2026-10-15", "2026-10-05"), r))

# (g) as duas gerações dão as mesmas datas, gravadas na tarefa
admin_cab = {"Authorization": "Bearer " + create_access_token(data={"sub": "admin@x.com"})}
db = SessionLocal()
db.add(Usuario(nome="Admin", email="admin@x.com", grupo="admin", ativo=True,
               senha_hash=get_password_hash("x")))
db.add(Usuario(nome="Analista", email="analista@x.com", grupo="analista", ativo=True,
               senha_hash=get_password_hash("x")))
_setor = Setor(nome="Setor da prova", ativo=True)
_emp = Empresa(razao_social="Empresa da prova", cnpj="11222333000181", ativo=True,
               fechamento_tipo="dia_fixo", fechamento_dia=15)
db.add_all([_setor, _emp])
db.commit()
SETOR, EMP = _setor.id, _emp.id
db.close()
analista_cab = {"Authorization": "Bearer " + create_access_token(data={"sub": "analista@x.com"})}


def gera_nas_duas(**campos):
    s = SessionLocal()
    try:
        o = Obrigacao(nome="g", setor_id=SETOR, meses_ativos="10", regra_prazo_tipo="ultimo_dia_util",
                      lembrar_dias_antes=10, tipo_dias="corridos", **campos)
        s.add(o)
        s.commit()
        gerador.gerar_tarefas(s, 10, 2026, obrigacao_ids=[o.id])
        t1 = s.query(Tarefa).filter(Tarefa.obrigacao_id == o.id).one()
        um = (str(t1.data_vencimento)[:10], str(t1.data_prazo)[:10])
        s.delete(t1)
        s.commit()
        emp = s.get(Empresa, EMP)
        gerador.gerar_para_empresa(s, emp, 10, 2026)
        t2 = s.query(Tarefa).filter(Tarefa.obrigacao_id == o.id).one()
        dois = (str(t2.data_vencimento)[:10], str(t2.data_prazo)[:10])
        o.ativa = False
        s.commit()
        return um, dois
    finally:
        s.close()


tenta(14, "(g) regra própria dia 5: gerar o mês e gerar a empresa gravam 30/10 e 05/10",
      lambda: ((r := gera_nas_duas(interno_modo="regra", interno_regra_tipo="dia_fixo",
                                   interno_regra_dia=5))
               == (("2026-10-30", "2026-10-05"),) * 2, r))
tenta(15, "(g) antes do fechamento: as duas gerações gravam 05/10",
      lambda: ((r := gera_nas_duas(interno_modo="antes_fechamento"))
               == (("2026-10-30", "2026-10-05"),) * 2, r))


# (h) entrada inválida dá 422
def cria(**extra):
    return client.post("/api/obrigacoes", json={"nome": "h", "setor_id": SETOR, **extra},
                       headers=admin_cab)


ruins = [dict(interno_modo="qualquer"), dict(interno_modo="regra", interno_regra_tipo="toda_lua"),
         dict(interno_modo="regra", interno_regra_tipo="dia_fixo", interno_regra_dia=0),
         dict(interno_modo="regra", interno_regra_tipo="dia_fixo", interno_regra_dia=32),
         dict(interno_modo="regra")]
st = [cria(**x).status_code for x in ruins]
checa(16, f"(h) POST com modo, tipo, dia 0, dia 32 ou regra sem tipo dá 422 nos cinco: {st}",
      st == [422] * 5)

r = cria(interno_modo="regra", interno_regra_tipo="dia_fixo", interno_regra_dia=5)
j = r.json() if r.status_code == 201 else {}
checa(17, f"(h) POST válido grava e devolve o modo e a regra: {r.status_code} "
          f"{[j.get(k) for k in ('interno_modo', 'interno_regra_tipo', 'interno_regra_dia')]}",
      r.status_code == 201 and (j.get("interno_modo"), j.get("interno_regra_tipo"),
                                j.get("interno_regra_dia")) == ("regra", "dia_fixo", 5))

r = cria()
checa(18, f"(h) POST sem os campos novos nasce em antes do vencimento: {r.json().get('interno_modo')}",
      r.status_code == 201 and r.json().get("interno_modo") == "antes_vencimento")
sem_id = r.json().get("id")
st = [client.put(f"/api/obrigacoes/{sem_id}", json=x, headers=admin_cab).status_code
      for x in (dict(interno_modo="qualquer"), dict(interno_modo="regra"))]
checa(19, f"(h) PUT com modo inválido e PUT de regra sem tipo (no banco também não tem) dão 422: {st}",
      st == [422, 422])
s = SessionLocal()
modo_banco = getattr(s.get(Obrigacao, sem_id), "interno_modo", "sem coluna")
s.close()
checa(20, f"(h) e o banco não mudou: {modo_banco}", modo_banco == "antes_vencimento")

# (i) prévia
PREVIA = "/api/obrigacoes/previa-prazo"
corpo = dict(regra_prazo_tipo="dia_fixo", regra_prazo_dia=20, ajuste_nao_util="antecipar",
             sabado_util=False, lembrar_dias_antes=5, tipo_dias="uteis",
             interno_modo="antes_vencimento", mes=10, ano=2026)
r = client.post(PREVIA, json=corpo, headers=admin_cab)
j = r.json() if r.status_code == 200 else {}
checa(21, f"(i) prévia de outubro: {r.status_code} {j.get('vencimento')} {j.get('prazo_interno')}",
      r.status_code == 200 and (j.get("vencimento"), j.get("prazo_interno"))
      == ("2026-10-20", "2026-10-13"))
r = client.post(PREVIA, json=dict(corpo, ancora="fechamento", ancora_dias_antes=0,
                                  interno_modo="regra", interno_regra_tipo="dia_fixo",
                                  interno_regra_dia=5), headers=admin_cab)
j = r.json() if r.status_code == 200 else {}
checa(22, f"(i) ancorada na prévia usa o fechamento de exemplo dia 15: {r.status_code} "
          f"{j.get('vencimento')} {j.get('prazo_interno')}",
      r.status_code == 200 and (j.get("vencimento"), j.get("prazo_interno"))
      == ("2026-10-15", "2026-10-05"))
st = [client.post(PREVIA, json=corpo).status_code,
      client.post(PREVIA, json=corpo, headers=analista_cab).status_code]
checa(23, f"(i) prévia sem login 401 e sem obrigações:ver 403: {st}", st == [401, 403])
st = [client.post(PREVIA, json=dict(corpo, **x), headers=admin_cab).status_code
      for x in (dict(interno_modo="qualquer"), dict(mes=13), dict(fechamento_dia=40))]
checa(24, f"(i) prévia com modo, mês ou fechamento fora da faixa dá 422: {st}", st == [422] * 3)

# Itens 25 a 30: achados do verificador de 2026-10-02, escritos ANTES do conserto.
# 25. a migração preenche as obrigações que já existem (a prova acima usa create_all)
def migra_banco_antigo():
    import sqlite3
    from sqlalchemy import create_engine
    from app import init_db
    arq = f"{_tmp}/antigo.db"
    c = sqlite3.connect(arq)
    c.execute("CREATE TABLE obrigacoes (id INTEGER PRIMARY KEY, nome VARCHAR(200))")
    c.execute("INSERT INTO obrigacoes (nome) VALUES ('antiga')")
    c.commit(); c.close()
    original = init_db.engine
    init_db.engine = create_engine(f"sqlite:///{arq}")
    try:
        so = [m for m in init_db.MIGRACOES if m[0].startswith("interno_")]
        init_db.migrate(so); init_db.migrate(so)
    finally:
        init_db.engine = original
    c = sqlite3.connect(arq)
    linha = c.execute("SELECT interno_modo, interno_regra_tipo, interno_regra_dia FROM obrigacoes").fetchone()
    c.close()
    return linha == ("antes_vencimento", None, None), linha


tenta(25, "migração em banco antigo: a obrigação que já existe fica em antes_vencimento, rodando 2 vezes",
      migra_banco_antigo)

# 26. antes do fechamento respeita dias úteis x corridos (5 antes do dia 15)
tenta(26, "(b) 5 úteis antes do fechamento 15/10 dá 08/10, e 5 corridos dá 09/10",
      lambda: ((r := (datas(Obr(regra="ultimo_dia_util", regra_dia=None, lembrar=5, tipo_dias="uteis",
                                modo="antes_fechamento"), FECHA15)[1],
                      datas(Obr(regra="ultimo_dia_util", regra_dia=None, lembrar=5, tipo_dias="corridos",
                                modo="antes_fechamento"), FECHA15)[1]))
               == ("2026-10-08", "2026-10-09"), r))

# 27. a prévia anda até o próximo mês de entrega
r = client.post(PREVIA, json=dict(corpo, meses_ativos="3"), headers=admin_cab)
j = r.json() if r.status_code == 200 else {}
checa(27, f"(i) anual de março aberta em outubro/2026 mostra março/2027: {r.status_code} "
          f"{j.get('mes')}/{j.get('ano')} {j.get('vencimento')}",
      r.status_code == 200 and (j.get("mes"), j.get("ano"), j.get("vencimento")) == (3, 2027, "2027-03-19"))

# 28. a prévia avisa quando a regra própria foi limitada ao vencimento
base_lim = dict(corpo, regra_prazo_dia=10, interno_modo="regra", interno_regra_tipo="dia_fixo")
r1 = client.post(PREVIA, json=dict(base_lim, interno_regra_dia=20), headers=admin_cab).json()
r2 = client.post(PREVIA, json=dict(base_lim, interno_regra_dia=5), headers=admin_cab).json()
checa(28, f"(i) regra dia 20 com vencimento 09/10 vem limitada=True; dia 5 vem False: "
          f"{r1.get('interno_limitado')} {r2.get('interno_limitado')}",
      r1.get("interno_limitado") is True and r2.get("interno_limitado") is False)

# 29 e 30. dia fixo e N-ésimo dia útil exigem o dia
st = [cria(interno_modo="regra", interno_regra_tipo=t).status_code for t in ("dia_fixo", "dia_util")]
st.append(client.post(PREVIA, json=dict(corpo, interno_modo="regra", interno_regra_tipo="dia_fixo"),
                      headers=admin_cab).status_code)
checa(29, f"(h) regra dia fixo ou N-ésimo dia útil sem o dia dá 422 (POST, POST, prévia): {st}",
      st == [422, 422, 422])
st = [client.put(f"/api/obrigacoes/{sem_id}", json=dict(interno_modo="regra", interno_regra_tipo="dia_fixo"),
                 headers=admin_cab).status_code,
      cria(interno_modo="regra", interno_regra_tipo="primeiro_dia_util").status_code]
checa(30, f"(h) PUT de dia fixo sem dia dá 422; primeiro dia útil sem dia segue 201: {st}", st == [422, 201])

# 31 a 33: achados do verificador funcional de 2026-10-02, escritos ANTES do conserto.
st = [client.post(PREVIA, json=dict(corpo, **x), headers=admin_cab).status_code
      for x in ({"mes": [1]}, {"ano": [1]}, {"lembrar_dias_antes": [1]}, {"ancora_dias_antes": {"a": 1}})]
checa(31, f"(i) lista ou objeto num número da prévia dá 422, e não 500: {st}", st == [422] * 4)
st = [cria(interno_modo="regra", interno_regra_tipo="dia_fixo", interno_regra_dia=v).status_code
      for v in (True, 5.5)]
st += [client.post(PREVIA, json=dict(corpo, **x), headers=admin_cab).status_code
       for x in ({"mes": True}, {"mes": 1.5}, {"fechamento_dia": 2.5})]
checa(32, f"(h) booleano e número quebrado no dia e no mês dão 422: {st}", st == [422] * 5)
tenta(33, "dia negativo gravado direto no banco não derruba o cálculo (cai no dia 1)",
      lambda: ((r := (datas(Obr(**venc_fim, regra_int="dia_fixo", dia_int=-7), SEM)[1],
                      datas(Obr(regra="dia_fixo", regra_dia=-7, lembrar=0), SEM)[0]))
               == ("2026-10-01", "2026-10-01"), r))

assert len({*range(1, TOTAL + 1)}) == TOTAL
if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print(f"\nPROVA OK: {TOTAL} checagens verdes")
