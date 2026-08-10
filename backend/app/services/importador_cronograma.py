"""Importação de um CRONOGRAMA de fechamento (ex.: GRABER) como Obrigações
recorrentes. Cada atividade vira uma obrigação vinculada às entidades do grupo,
com prazo em N-ésimo dia útil (convertido da data do arquivo).

Fluxo: analisar(arquivo) -> preview editável -> importar(itens) -> cria empresas
do grupo + setores + obrigações.
"""
import io
import re
import calendar
import unicodedata
from collections import defaultdict, Counter
from datetime import datetime, date
from ..models import Empresa, Setor, Obrigacao

SETORES_PADRAO = ["Contabilidade", "Fiscal", "DP", "Financeiro"]
MESES_TODOS = "1,2,3,4,5,6,7,8,9,10,11,12"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def nth_dia_util(d: date) -> int:
    """Qual dia útil (seg-sex) do mês a data representa."""
    n = 0
    for dia in range(1, d.day + 1):
        if date(d.year, d.month, dia).weekday() < 5:
            n += 1
    return n


def chute_setor(nome: str) -> str:
    """Classificação por palavra-chave. Ordem: Fiscal, Contabilidade, DP,
    Financeiro (o usuário revisa no preview)."""
    n = _norm(nome)
    fiscal = ["icms", "pis", "cofins", " ipi", "iss", "irpj", "csll", "apuracao",
              "impostos retid", "retid", "guia", "sped", "reinf", "difal"]
    contab = ["dre", "balancete", "balanco", "book", "cmv", "imobilizado", "ifrs",
              "deprecia", "amortiza", "intercompany", "contabiliz", "faturamento",
              "rateio", "time sheet", "timesheet", "razao", "provisao", "reversao",
              " bp", "estoque", "selic", "diferido", "deferido"]
    dp = ["folha", "inss", "fgts", "ferias", "13o", "13º", "encargos", "rescis",
          "admissao", "holerite", "ponto"]
    fin = ["fluxo de caixa", "extrato", "baixas", "titulos", "bancari", "banco",
           "aplicacao financeira", "saldo", "contas a pagar", "contas a receber"]
    for setor, chaves in [("Fiscal", fiscal), ("Contabilidade", contab),
                          ("DP", dp), ("Financeiro", fin)]:
        if any(k in n for k in chaves):
            return setor
    return ""  # sem chute -> usuário escolhe


def parse_entidades(cel: str) -> list:
    """Extrai as entidades do grupo da coluna 'Empresa' (FOS, SL, SLS, TODAS...)."""
    c = _norm(cel)
    if not c:
        return []
    if "toda" in c:
        return ["FOS", "SL", "SLS"]
    out = set()
    for tok in re.split(r"[\s/,;]+", c):
        if tok.startswith("fos"):
            out.add("FOS")
        elif tok.startswith("sls"):
            out.add("SLS")
        elif tok.startswith("sl"):
            out.add("SL")
    return sorted(out)


def _ler(conteudo: bytes):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    return list(wb.worksheets[0].iter_rows(values_only=True))


def _achar_cabecalho(rows):
    """Acha a linha do cabeçalho (que tem 'Atividade' e 'Prazo')."""
    for i, r in enumerate(rows):
        vals = [_norm(c) for c in r]
        if "atividade" in vals and "prazo" in vals:
            return i, {v: j for j, v in enumerate(vals) if v}
    return None, {}


def analisar(conteudo: bytes) -> dict:
    """Lê o cronograma e devolve as obrigações candidatas (agrupadas por atividade)."""
    rows = _ler(conteudo)
    i_cab, cols = _achar_cabecalho(rows)
    if i_cab is None:
        return {"erro": "Não encontrei o cabeçalho (colunas 'Atividade' e 'Prazo').", "itens": []}

    c_ativ = cols.get("atividade")
    c_emp = cols.get("empresa")
    c_prazo = cols.get("prazo")

    grupos = defaultdict(lambda: {"ents": set(), "datas": []})
    for r in rows[i_cab + 1:]:
        if not r or c_ativ is None or not r[c_ativ]:
            continue
        nome = str(r[c_ativ]).strip()
        g = grupos[nome]
        if c_emp is not None:
            g["ents"].update(parse_entidades(r[c_emp]))
        if c_prazo is not None and isinstance(r[c_prazo], datetime):
            g["datas"].append(r[c_prazo].date())

    # mês de fechamento = mês mais comum entre as datas
    todas_datas = [d for g in grupos.values() for d in g["datas"]]
    mes_fech = Counter(d.month for d in todas_datas).most_common(1)[0][0] if todas_datas else None

    itens = []
    entidades = set()
    for nome, g in grupos.items():
        ents = sorted(g["ents"]) or ["FOS"]
        entidades.update(ents)
        rep = Counter(g["datas"]).most_common(1)[0][0] if g["datas"] else None
        if rep and rep.month == mes_fech:
            comp, tipo, dia = "mes_anterior", "dia_util", nth_dia_util(rep)
            label = f"{dia}º dia útil"
        elif rep:
            comp, tipo, dia = "mesmo_mes", "dia_util", nth_dia_util(rep)
            label = f"{dia}º dia útil (mesmo mês)"
        else:
            comp, tipo, dia = "mesmo_mes", "ultimo_dia_util", None
            label = "durante o mês"
        itens.append({
            "nome": nome, "setor": chute_setor(nome), "entidades": ents,
            "competencia_ref": comp, "regra_prazo_tipo": tipo, "regra_prazo_dia": dia,
            "prazo_label": label,
        })
    itens.sort(key=lambda x: (x["regra_prazo_dia"] or 99, x["nome"]))
    return {"itens": itens, "entidades": sorted(entidades), "total": len(itens)}


def _get_or_create_empresa(db, codigo: str, grupo: str):
    e = db.query(Empresa).filter(Empresa.razao_social == codigo).first()
    if not e:
        e = Empresa(razao_social=codigo, grupo=grupo, ativo=True)
        db.add(e)
        db.flush()
    elif grupo and not e.grupo:
        e.grupo = grupo
    return e


def _get_or_create_setor(db, nome: str):
    if not nome:
        return None
    s = db.query(Setor).filter(Setor.nome == nome).first()
    if not s:
        s = Setor(nome=nome)
        db.add(s)
        db.flush()
    return s


def importar(db, grupo: str, itens: list, mapa: dict = None) -> dict:
    """Cria setores e obrigações (dedupe por nome; se já existe, apenas acrescenta
    as empresas ao vínculo). Cada código de entidade (FOS/SL/SLS) é resolvido para
    uma empresa: se `mapa[codigo]` aponta uma empresa cadastrada, usa ela; senão,
    cria uma empresa pelo próprio código (fallback)."""
    grupo = (grupo or "").strip() or "GRUPO"
    mapa = mapa or {}
    codigos = sorted({c for it in itens for c in (it.get("entidades") or [])})

    def _resolver(it):
        """Empresas do item: se veio a seleção por linha (`empresa_ids`, mesmo vazia),
        respeita ela; senão, cai no antigo esquema por código (mapa/criação)."""
        if "empresa_ids" in it:
            emps = [db.query(Empresa).filter(Empresa.id == int(i)).first()
                    for i in (it.get("empresa_ids") or [])]
            return [e for e in emps if e]
        out = []
        for c in (it.get("entidades") or []):
            eid = mapa.get(c) or mapa.get(str(c))
            e = db.query(Empresa).filter(Empresa.id == int(eid)).first() if eid else None
            out.append(e or _get_or_create_empresa(db, c, grupo))
        return out

    criadas = atualizadas = 0
    usadas = set()
    for it in itens:
        nome = (it.get("nome") or "").strip()
        if not nome:
            continue
        setor = _get_or_create_setor(db, it.get("setor"))
        emps = _resolver(it)
        for e in emps:
            usadas.add(e.razao_social)

        o = db.query(Obrigacao).filter(Obrigacao.nome == nome).first()
        if o:
            atuais = {e.id for e in o.empresas}
            for e in emps:
                if e.id not in atuais:
                    o.empresas.append(e)
            atualizadas += 1
        else:
            o = Obrigacao(
                nome=nome,
                setor_id=setor.id if setor else None,
                competencia_ref=it.get("competencia_ref") or "mes_anterior",
                regra_prazo_tipo=it.get("regra_prazo_tipo") or "ultimo_dia_util",
                regra_prazo_dia=it.get("regra_prazo_dia"),
                meses_ativos=MESES_TODOS,
                ativa=True,
            )
            o.empresas = emps
            db.add(o)
            criadas += 1
    db.commit()
    return {"grupo": grupo, "criadas": criadas, "atualizadas": atualizadas,
            "empresas": sorted(usadas)}
