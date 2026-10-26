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


def parse_entidades(cel) -> list:
    """Divide a coluna Empresa em códigos/nomes (ex.: 'FOS, SL' -> ['FOS','SL'])."""
    c = str(cel or "").strip()
    if not c:
        return []
    return sorted({t.strip().upper() for t in re.split(r"[/,;]+", c) if t.strip()})


# ---- Layout único: Descrição da tarefa · Competência · Vencimento · Empresa · Gera multa · Setor ----
FIELD_ALIASES = {
    "nome": ["descricao da tarefa", "descricao das tarefas", "descricao das tarefa",
             "descricao", "descrição", "tarefa", "atividade", "obrigacao", "obrigação"],
    "competencia": ["competencia", "competência"],
    "vencimento": ["vencimento", "prazo", "prazo legal", "transicao", "transição", "meta",
                   "data prevista", "data"],
    # Prazo da equipe, quando difere do vencimento (2026-10-26, fluxo do DP).
    "interno": ["prazo interno", "prazo interno bps4", "interno"],
    "sentido": ["sentido"],
    "comentario": ["comentario", "comentário", "observacao", "observação", "roteiro"],
    "empresa": ["empresa", "empresas", "entidade", "entidades"],
    "cnpj": ["cnpj", "cnpj/cpf", "cnpj cpf"],
    "multa": ["gera multa", "multa", "passivel de multa", "passível de multa"],
    "setor": ["setor", "departamento", "area", "área", "responsavel", "responsável"],
}

COMPETENCIAS = {
    "mes anterior": "mes_anterior", "mesmo mes": "mesmo_mes",
    "ano anterior": "ano_anterior", "mes seguinte": "mes_seguinte", "subsequente": "mes_seguinte",
}


def _mapear_colunas(header) -> dict:
    m = {}
    norm = [_norm(c) for c in header]
    for field, aliases in FIELD_ALIASES.items():
        for j, h in enumerate(norm):
            if h and h in aliases and field not in m:
                m[field] = j
    return m


def map_competencia(cel) -> str:
    t = _norm(cel)
    for k, v in COMPETENCIAS.items():
        if k in t:
            return v
    return "mes_anterior"


def parse_vencimento(cel):
    """Devolve (regra_prazo_tipo, regra_prazo_dia, label) de uma data OU de texto
    ('5º dia útil', 'último dia útil', 'Dia 12', 'Até dia 15') OU de um número (12)."""
    if isinstance(cel, datetime):
        n = nth_dia_util(cel.date())
        return "dia_util", n, f"{n}º dia útil"
    if isinstance(cel, (int, float)) and not isinstance(cel, bool) and 1 <= int(cel) <= 31:
        return "dia_fixo", int(cel), f"Dia {int(cel)}"
    t = _norm(cel)
    m = re.search(r"(\d+)\s*[ºo°]?\s*dia\s*util", t)
    if m:
        n = int(m.group(1))
        return "dia_util", n, f"{n}º dia útil"
    # "Dia 12", "Até dia 15", "12": dia do mês. Antes caía no fallback de
    # último dia útil, calado, e o prazo da folha ia parar no fim do mês.
    m = re.fullmatch(r"(?:ate\s+)?(?:o\s+)?(?:dia\s*)?(\d{1,2})", t)
    if m and 1 <= int(m.group(1)) <= 31:
        n = int(m.group(1))
        return "dia_fixo", n, f"Dia {n}"
    if "ultimo dia" in t:
        return "ultimo_dia_util", None, "último dia útil"
    if "primeiro dia" in t:
        return "primeiro_dia_util", None, "primeiro dia útil"
    return "ultimo_dia_util", None, "-"


def mapear_setor(cel) -> str:
    """Mapeia o texto da coluna Setor/Responsável para um dos 4 setores padrão."""
    t = _norm(cel)
    if not t:
        return ""
    if "fiscal" in t:
        return "Fiscal"
    if re.search(r"\bdp\b", t) or "pessoal" in t:
        return "DP"
    if "contab" in t or "controlad" in t:
        return "Contabilidade"
    if any(k in t for k in ["pagar", "receber", "tesouraria", "faturamento", "financ", "caixa"]):
        return "Financeiro"
    return ""


SENTIDOS = ("receber", "entregar", "transmitir", "interna")
TIPOS_PRAZO = ("ultimo_dia_util", "primeiro_dia_util", "dia_fixo", "dia_util")


def map_sentido(cel):
    """Texto da coluna Sentido -> um dos quatro, ou None (fica o padrão do modelo)."""
    t = _norm(cel)
    return t if t in SENTIDOS else None


def _dia(v):
    """Dia de 1 a 31, ou None. O item volta do navegador: não se confia nele."""
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 31 else None


def parse_multa(cel) -> bool:
    t = _norm(cel)
    return t in ("sim", "s", "x", "1", "true", "verdadeiro") or "sim" in t


def _ler(conteudo: bytes):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    return list(wb.worksheets[0].iter_rows(values_only=True))


def _achar_cabecalho(rows):
    """Cabeçalho = 1ª linha com a coluna de descrição/atividade."""
    for i, r in enumerate(rows):
        m = _mapear_colunas(r)
        if "nome" in m:
            return i, m
    return None, {}


def analisar(conteudo: bytes) -> dict:
    """Lê a planilha (layout único) e devolve as obrigações candidatas, agrupadas por descrição."""
    rows = _ler(conteudo)
    i_cab, c = _achar_cabecalho(rows)
    if i_cab is None:
        return {"erro": "Não encontrei o cabeçalho (precisa da coluna 'Descrição da tarefa').", "itens": []}

    def cel(r, campo):
        j = c.get(campo)
        return r[j] if (j is not None and j < len(r)) else None

    grupos, ordem = {}, []
    for r in rows[i_cab + 1:]:
        nome_cel = cel(r, "nome")
        if not nome_cel or not str(nome_cel).strip():
            continue
        nome = str(nome_cel).strip()
        if nome not in grupos:
            grupos[nome] = {"ents": set(), "cnpjs": set(), "setor": None, "setor_raw": None,
                            "comp": None, "tipo": None, "dia": None, "label": None, "multa": False,
                            "i_tipo": None, "i_dia": None, "i_label": None, "sentido": None,
                            "comentario": None}
            ordem.append(nome)
        g = grupos[nome]
        g["ents"].update(parse_entidades(cel(r, "empresa")))
        cnpj = re.sub(r"\D", "", str(cel(r, "cnpj") or ""))
        if cnpj:
            g["cnpjs"].add(cnpj)
        sc = cel(r, "setor")
        if g["setor_raw"] is None and sc not in (None, ""):
            g["setor_raw"] = str(sc).strip()
        if g["setor"] is None:
            g["setor"] = mapear_setor(sc) or chute_setor(nome)
        if g["comp"] is None and cel(r, "competencia") is not None:
            g["comp"] = map_competencia(cel(r, "competencia"))
        v = cel(r, "vencimento")
        if g["tipo"] is None and v not in (None, ""):
            g["tipo"], g["dia"], g["label"] = parse_vencimento(v)
        if parse_multa(cel(r, "multa")):
            g["multa"] = True
        vi = cel(r, "interno")
        if g["i_tipo"] is None and vi not in (None, ""):
            g["i_tipo"], g["i_dia"], g["i_label"] = parse_vencimento(vi)
        if g["sentido"] is None:
            g["sentido"] = map_sentido(cel(r, "sentido"))
        cm = cel(r, "comentario")
        if g["comentario"] is None and cm not in (None, ""):
            g["comentario"] = str(cm).strip()

    itens, entidades = [], set()
    for nome in ordem:
        g = grupos[nome]
        ents = sorted(g["ents"])
        entidades.update(ents)
        itens.append({
            "nome": nome, "setor": g["setor"] or "", "setor_raw": g["setor_raw"] or "",
            "entidades": ents, "cnpjs": sorted(g["cnpjs"]),
            "competencia_ref": g["comp"] or "mes_anterior",
            "regra_prazo_tipo": g["tipo"] or "ultimo_dia_util",
            "regra_prazo_dia": g["dia"], "prazo_label": g["label"] or "-",
            "gera_multa": g["multa"],
            "interno_regra_tipo": g["i_tipo"], "interno_regra_dia": g["i_dia"],
            "interno_label": g["i_label"], "sentido": g["sentido"],
            "comentario": g["comentario"],
        })
    itens.sort(key=lambda x: (x["regra_prazo_dia"] or 99, x["nome"]))
    return {"itens": itens, "entidades": sorted(entidades), "total": len(itens)}


def _get_or_create_empresa(db, codigo: str, grupo: str):
    # Pela CHAVE, e nao pelo texto exato: desde 2026-10-26 a razao social e
    # gravada formatada ("Gnileb Ltda"), e a planilha continua vindo como o
    # cliente escreveu ("GNILEB LTDA."). Comparar o texto cru criaria a empresa
    # de novo a cada importacao.
    from .razao_social import chave
    alvo = chave(codigo)
    e = next((x for x in db.query(Empresa).all() if chave(x.razao_social) == alvo), None)
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


def importar(db, grupo: str, itens: list, mapa: dict = None, para_todas: bool = True) -> dict:
    """Cria setores e obrigações (dedupe por nome).

    `para_todas=True` (padrão): a obrigação vale para TODAS as empresas: não
    grava vínculo por CNPJ (regra de regime/segmento vazia = todas). Se a obrigação
    já existir com vínculos antigos, eles são LIMPOS para ficar coerente com a tela.

    `para_todas=False`: mantém o vínculo por empresa (seleção por linha `empresa_ids`
    ou código FOS/SL/SLS via `mapa`), para obrigações realmente específicas."""
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
        emps = [] if para_todas else _resolver(it)
        for e in emps:
            usadas.add(e.razao_social)

        o = db.query(Obrigacao).filter(Obrigacao.nome == nome).first()
        if o:
            if para_todas:
                o.empresas = []        # limpa vínculos antigos → vale para todas
            else:
                atuais = {e.id for e in o.empresas}
                for e in emps:
                    if e.id not in atuais:
                        o.empresas.append(e)
            # garante que não há restrição de regime/segmento (para_todas)
            if para_todas:
                o.aplica_regimes = None
                o.aplica_segmentos = None
            atualizadas += 1
        else:
            # O item volta do navegador: tipo, dia e sentido fora da lista não
            # entram (antes, qualquer texto virava regra_prazo_tipo).
            tipo = it.get("regra_prazo_tipo")
            tipo = tipo if tipo in TIPOS_PRAZO else "ultimo_dia_util"
            dia = _dia(it.get("regra_prazo_dia")) if tipo in ("dia_fixo", "dia_util") else None
            if tipo in ("dia_fixo", "dia_util") and dia is None:
                tipo = "ultimo_dia_util"
            comp = it.get("competencia_ref")
            o = Obrigacao(
                nome=nome,
                setor_id=setor.id if setor else None,
                competencia_ref=comp if comp in set(COMPETENCIAS.values()) else "mes_anterior",
                regra_prazo_tipo=tipo,
                regra_prazo_dia=dia,
                meses_ativos=MESES_TODOS,
                passivel_multa=bool(it.get("gera_multa")),
                ativa=True,
            )
            i_tipo = it.get("interno_regra_tipo")
            i_dia = _dia(it.get("interno_regra_dia"))
            if i_tipo in TIPOS_PRAZO and (i_dia is not None or i_tipo in ("ultimo_dia_util", "primeiro_dia_util")):
                o.interno_modo = "regra"
                o.interno_regra_tipo = i_tipo
                o.interno_regra_dia = i_dia if i_tipo in ("dia_fixo", "dia_util") else None
            if it.get("sentido") in SENTIDOS:
                o.sentido = it["sentido"]
            if (it.get("comentario") or "").strip():
                o.comentario_padrao = str(it["comentario"]).strip()[:2000]
            o.empresas = emps
            db.add(o)
            criadas += 1
    db.commit()
    return {"grupo": grupo, "criadas": criadas, "atualizadas": atualizadas,
            "empresas": sorted(usadas)}


def gerar_modelo() -> bytes:
    """XLSX-modelo do layout único de importação de obrigações."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Obrigações"
    ws.append(["Descrição da tarefa", "Competência", "Vencimento", "Empresa", "CNPJ", "Gera multa", "Setor"])
    ws.append(["Apuração do ICMS", "Mês anterior", "5º dia útil", "FOS", "12.345.678/0001-90", "Sim", "Fiscal"])
    ws.append(["Conciliação bancária", "Mês anterior", "6º dia útil", "FOS", "12.345.678/0001-90", "Não", "Financeiro"])
    ws.append(["Fechamento da folha", "Mês anterior", "Último dia útil", "EDS", "98.765.432/0001-10", "Não", "DP"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
