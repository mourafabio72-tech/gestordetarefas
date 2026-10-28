"""Prova: o e-validador aceita o CNPJ completo OU a raiz (8 primeiros dígitos).

Pedido de 2026-10-28. Documento federal costuma trazer só a raiz
("CNPJ: 11.222.333"), e guia de filial chega para empresa cadastrada pela
matriz. A regra:
  (a) CNPJ completo cadastrado vence, como sempre;
  (b) sem completo, vale a raiz: lida sozinha no texto ou tirada do completo;
  (c) raiz de uma empresa só: é ela;
  (d) raiz de matriz e filiais: vale a que tem a tarefa da obrigação na
      competência; mais de uma com tarefa aberta é "ambíguo", sem chute;
  (e) na conferência da guia, a mesma raiz conta como CNPJ certo; raiz de
      outra empresa continua acusando.

    cd backend && ./venv/bin/python provas/prova_cnpj_raiz.py
"""
from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_cnpj_raiz_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("OPENAI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import Empresa, Obrigacao, StatusTarefa, Tarefa    # noqa: E402
from app.services import validador                                 # noqa: E402
import app.main                                                    # noqa: E402,F401

Base.metadata.create_all(bind=engine)
falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


# ------------------------------------------------------------ extração
print("\nextracao")
d = validador.extrair_dados("RECIBO DCTFWeb\nCNPJ: 11.222.333\nPeríodo 01/09/2026 a 30/09/2026")
checa(1, "'CNPJ: 11.222.333' vira raiz lida", d.get("raizes") == ["11222333"], d)
checa(2, "e nao vira CNPJ completo", d["cnpj"] is None, d["cnpj"])
d = validador.extrair_dados("CNPJ 11.222.333/0002-62\nCNPJ: 11.222.333")
checa(3, "completo e raiz da mesma empresa nao repetem a raiz", d.get("raizes") == ["11222333"], d)
d = validador.extrair_dados("CNPJ: 11222333000181\nTotal")
checa(4, "CNPJ rotulado sem pontuacao tambem e lido", d["cnpj"] == "11222333000181", d)

# ------------------------------------------------------------ cadastro
db = SessionLocal()
unica = Empresa(razao_social="Unica Ltda", cnpj="44.555.666/0001-99", ativo=True)
matriz = Empresa(razao_social="Grupo Matriz", cnpj="11.222.333/0001-81", ativo=True)
filial = Empresa(razao_social="Grupo Filial", cnpj="11.222.333/0002-62", ativo=True)
o = Obrigacao(nome="dctfweb", identificadores="RECIBO DCTFWeb", sentido="receber",
              meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12", ativa=True)
db.add_all([unica, matriz, filial, o])
db.flush()

print("\nescolha da empresa")
e = validador.empresa_do_documento(db, validador.extrair_dados("CNPJ: 44.555.666"))
checa(5, "raiz de uma empresa so: e ela", e is not None and e.id == unica.id, e and e.razao_social)
e = validador.empresa_do_documento(db, validador.extrair_dados("CNPJ: 44.555.666/0003-50"))
checa(6, "filial nao cadastrada de empresa unica cai na empresa pela raiz",
      e is not None and e.id == unica.id, e and e.razao_social)
e = validador.empresa_do_documento(db, validador.extrair_dados("CNPJ 11.222.333/0002-62"))
checa(7, "completo cadastrado vence a raiz (filial, nao matriz)", e is not None and e.id == filial.id,
      e and e.razao_social)
cands = validador.empresas_do_documento(db, validador.extrair_dados("CNPJ: 11.222.333"))
checa(8, "raiz de matriz e filial devolve as duas candidatas",
      sorted(c.id for c in cands) == sorted([matriz.id, filial.id]), [c.razao_social for c in cands])

# ------------------------------------------------------------ processar
print("\nprocessar")
tf = Tarefa(titulo="dctfweb", empresa_id=filial.id, obrigacao_id=o.id, competencia="09/2026",
            status=StatusTarefa.PENDENTE)
db.add(tf)
db.commit()
TEXTO = "RECIBO DCTFWeb\nCNPJ: 11.222.333\nPeríodo 01/09/2026 a 30/09/2026"
validador.ler_arquivo = lambda nome, conteudo: TEXTO
r = validador.processar(db, "recibo.pdf", b"%PDF-ficticio")
checa(9, "so a filial tem a tarefa: ela recebe a baixa",
      r.get("tarefa_id") == tf.id and r.get("status") == "baixada", r)

tm = Tarefa(titulo="dctfweb", empresa_id=matriz.id, obrigacao_id=o.id, competencia="10/2026",
            status=StatusTarefa.PENDENTE)
tf2 = Tarefa(titulo="dctfweb", empresa_id=filial.id, obrigacao_id=o.id, competencia="10/2026",
             status=StatusTarefa.PENDENTE)
db.add_all([tm, tf2])
db.commit()
TEXTO = "RECIBO DCTFWeb\nCNPJ: 11.222.333\nPeríodo 01/10/2026 a 31/10/2026"
r = validador.processar(db, "recibo.pdf", b"%PDF-ficticio")
checa(10, "matriz e filial com tarefa aberta: ambiguo, nada baixado",
      r.get("status") == "ambiguo" and db.get(Tarefa, tm.id).status == StatusTarefa.PENDENTE
      and db.get(Tarefa, tf2.id).status == StatusTarefa.PENDENTE, r)
checa(11, "e a mensagem nomeia as empresas",
      "Grupo Matriz" in (r.get("detalhe") or "") and "Grupo Filial" in (r.get("detalhe") or ""),
      r.get("detalhe"))
TEXTO = "RECIBO DCTFWeb\nCNPJ: 99.888.777\nPeríodo 01/10/2026 a 31/10/2026"
r = validador.processar(db, "recibo.pdf", b"%PDF-ficticio")
checa(12, "raiz que ninguem tem: empresa nao cadastrada",
      r.get("status") == "erro" and "não cadastrada" in (r.get("detalhe") or ""), r)
db.close()

# ------------------------------------------------------------ conferencia
print("\nconferencia da guia")
c = validador.conferir_saida("GUIA\nCNPJ 11.222.333/0002-62\nCompetência: 09/2026",
                             "11222333000181", "09/2026")
checa(13, "mesma raiz conta como CNPJ certo", c["ok"] and c["cnpj_lido"], c)
c = validador.conferir_saida("GUIA\nCNPJ: 11.222.333\nCompetência: 09/2026", "11222333000181", "09/2026")
checa(14, "raiz sozinha da empresa tambem", c["ok"] and c["cnpj_lido"], c)
c = validador.conferir_saida("GUIA\nCNPJ 99.888.777/0001-10\nCompetência: 09/2026",
                             "11222333000181", "09/2026")
checa(15, "raiz de outra empresa continua acusando", not c["ok"], c)

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 15 checagens verdes")
