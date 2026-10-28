"""Prova: o e-validador acha o CNPJ do cabeçalho, não o da relação dentro do relatório.

Caso de 2026-10-27, apuração de retidos de um cliente: o texto do PDF sai com a
tabela de prestadores primeiro e o cabeçalho ("CNPJ: ...") no fim. O e-validador
ficava com o PRIMEIRO CNPJ formatado, o de um prestador, e respondia "empresa
não cadastrada". A competência vinha escrita "APURAÇÃO SETEMBRO DE 2026", formato
que ele não lia; a IA entrou e pegou "06.2026" de títulos velhos do relatório.

  (a) CNPJ com rótulo ("CNPJ: ...") passa à frente dos soltos de tabela;
  (b) entre todos, vale o primeiro de empresa CADASTRADA;
  (c) "Apuração setembro de 2026" vira 09/2026;
  (d) não-regressão: documento com um CNPJ só e período de/a segue igual;
  (e) a conferência da guia não acusa "outro CNPJ" quando o rótulo é da empresa.

Os CNPJs e nomes aqui são fictícios, no formato do relatório real.

    cd backend && ./venv/bin/python provas/prova_cnpj_cabecalho.py
"""
from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_cnpj_cabecalho_")
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


CLIENTE, PRESTADOR, OUTRO = "11.222.333/0001-81", "44.555.666/0001-99", "77.888.999/0001-10"
RELATORIO = f"""Numero Prestador CNPJ Emissao Vencto Valor Original Código VALOR IRRF
000000455SERVICOS ALFA {PRESTADOR} 24/09/2026 30/09/2026 2.989,92R$  1708 29,90R$
000000374APOIO BETA {OUTRO} 02/09/202602/09/2026 7.798,33R$  1708 116,97R$
Resumo
APURAÇÃO IRRF 1708 06.2026_VENC._20.07.2026
CLIENTE FICTICIO LTDA
CNPJ: {CLIENTE}
 APURAÇÃO SETEMBRO DE 2026
APURAÇÃO IRRF 3208  06.2026_VENC._20.07.2026
"""

# ------------------------------------------------------------ (a) e (c)
print("\n(a) e (c) extracao")
d = validador.extrair_dados(RELATORIO)
checa(1, "CNPJ com rotulo vem primeiro", d["cnpj"] == "11222333000181", d["cnpj"])
checa(2, "a lista traz todos, sem repetir, rotulado na frente",
      d.get("cnpjs") == ["11222333000181", "44555666000199", "77888999000110"], d.get("cnpjs"))
checa(3, "'APURAÇÃO SETEMBRO DE 2026' da 09/2026", d["competencia"] == "09/2026", d["competencia"])
c = validador.extrair_dados("Apuracao de dezembro/2025\nCNPJ 11.222.333/0001-81")["competencia"]
checa(4, "'Apuracao de dezembro/2025' da 12/2025", c == "12/2025", c)

# ------------------------------------------------------------ (d)
print("\n(d) nao-regressao")
d = validador.extrair_dados(f"RECIBO\nCNPJ {CLIENTE}\nPeríodo 01/05/2026 a 31/05/2026")
checa(5, "recibo de um CNPJ so e periodo de/a segue igual",
      (d["cnpj"], d["competencia"]) == ("11222333000181", "05/2026"), d)
d = validador.extrair_dados("Data de vencimento 30/04/2026\nTabela de apuracao de juros")
checa(6, "texto sem mes por extenso depois de 'apuracao' nao vira competencia", d["competencia"] is None, d)

# ------------------------------------------------------------ (b) processar de ponta a ponta
print("\n(b) o e-validador da baixa na tarefa do cliente")
db = SessionLocal()
emp = Empresa(razao_social="Cliente Ficticio Ltda", cnpj="11222333000181", ativo=True)
o = Obrigacao(nome="irrf_retido", identificadores="APURAÇÃO IRRF 1708", sentido="receber",
              meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12", ativa=True)
db.add_all([emp, o])
db.flush()
t = Tarefa(titulo="irrf_retido", empresa_id=emp.id, obrigacao_id=o.id, competencia="09/2026",
           status=StatusTarefa.PENDENTE)
db.add(t)
db.commit()
tid = t.id
validador.ler_arquivo = lambda nome, conteudo: RELATORIO
r = validador.processar(db, "retidos.pdf", b"%PDF-ficticio")
checa(7, "prestador nao cadastrado na frente nao impede: baixa a tarefa do cliente",
      r.get("status") == "baixada" and r.get("tarefa_id") == tid, r)
checa(8, "a resposta mostra o CNPJ do cliente e a competencia 09/2026",
      (r.get("cnpj"), r.get("competencia")) == ("11222333000181", "09/2026"), r)

# prestador tambem e cliente, e o relatorio NAO tem rotulo: vale o primeiro cadastrado
db.add(Empresa(razao_social="Servicos Alfa", cnpj="44555666000199", ativo=True))
db.commit()
sem_rotulo = RELATORIO.replace(f"CNPJ: {CLIENTE}", "")
d = validador.extrair_dados(sem_rotulo)
checa(9, "sem rotulo, a ordem e a do texto", d["cnpj"] == "44555666000199", d["cnpj"])
emp_doc = validador.empresa_do_documento(db, validador.extrair_dados(RELATORIO))
checa(10, "com rotulo, o prestador que tambem e cliente nao passa na frente",
      emp_doc is not None and emp_doc.cnpj == "11222333000181", emp_doc and emp_doc.cnpj)
db.close()

# ------------------------------------------------------------ (e)
print("\n(e) conferencia da guia")
conf = validador.conferir_saida(RELATORIO, "11222333000181", "09/2026")
checa(11, "guia com o rotulo da empresa nao gera alerta de outro CNPJ", conf["ok"], conf["alertas"])
conf = validador.conferir_saida(RELATORIO, "99888777000166", "09/2026")
checa(12, "guia de OUTRA empresa continua acusando", not conf["ok"], conf)

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 12 checagens verdes")
