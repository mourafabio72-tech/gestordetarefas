"""Relatório das empresas: forma de tributação e equipe por setor (2026-11-04).

Uma linha por empresa ativa e uma coluna por setor, lidas da matriz empresa ×
setor, a mesma que gera as tarefas. Assim o relatório mostra quem de fato recebe
a tarefa, e não um cadastro paralelo.
"""
import io

from ..models import Empresa, EmpresaSetorResponsavel, Setor

REGIMES = {"indefinido": "Indefinido", "lucro_real": "Lucro Real",
           "lucro_presumido": "Lucro Presumido", "mei": "MEI",
           "simples_nacional": "Simples Nacional", "terceiro_setor": "Terceiro Setor",
           "imune": "Imune", "isento": "Isento"}
SEGMENTOS = {"comercio": "Comércio", "servico": "Serviço",
             "comercio_servico": "Comércio & Serviço", "industria": "Indústria",
             "holding": "Holding", "imune": "Imune", "igreja": "Igreja"}
SEM_NINGUEM = "sem responsável"


def _texto(valor) -> str:
    """Texto que o Excel não executa: nome começando com = + - @ viraria fórmula."""
    v = str(valor or "")
    return f"'{v}" if v[:1] in ("=", "+", "-", "@") else v


def _nomes(vinculo) -> str:
    gente = list(vinculo.responsaveis) or ([vinculo.responsavel] if vinculo.responsavel else [])
    return "; ".join(_texto(u.nome) for u in gente) or SEM_NINGUEM


def gerar(db) -> bytes:
    import openpyxl
    from openpyxl.styles import Font
    setores = db.query(Setor).filter(Setor.ativo == True).order_by(Setor.nome).all()
    matriz = {}
    for v in db.query(EmpresaSetorResponsavel).all():
        matriz[(v.empresa_id, v.setor_id)] = v

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Empresas e equipe"
    ws.append(["Código", "Razão social", "CNPJ", "Forma de tributação", "Segmento", "Grupo",
               "Situação"] + [s.nome for s in setores])
    for c in ws[1]:
        c.font = Font(bold=True)
    empresas = (db.query(Empresa).filter(Empresa.ativo == True)
                .order_by(Empresa.razao_social).all())
    for e in empresas:
        colunas = []
        for s in setores:
            v = matriz.get((e.id, s.id))
            colunas.append(_nomes(v) if v else "")
        ws.append([e.id, _texto(e.razao_social), e.cnpj or "",
                   REGIMES.get(e.regime_tributario, e.regime_tributario or ""),
                   SEGMENTOS.get(e.segmento, e.segmento or ""), _texto(e.grupo),
                   "Bloqueada" if e.bloqueado else "Ativa"] + colunas)
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions
    for i, largura in enumerate([9, 44, 20, 20, 18, 18, 11] + [32] * len(setores), start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = largura
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
