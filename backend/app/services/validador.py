"""e-validador — lê um comprovante de entrega (PDF), extrai as chaves e casa
com a tarefa correspondente para dar baixa.

Chaves (ver OBRIGACOES_SPEC.md):
  CNPJ  -> empresa.cnpj
  identificador (palavra-chave no texto) -> obrigacao.identificadores
  competência (período de apuração) -> tarefa.competencia
"""
import io
import re
import unicodedata
from datetime import datetime
import pypdf
from sqlalchemy.orm import Session
from ..models import Empresa, Obrigacao, Tarefa, StatusTarefa


def _norm(s: str) -> str:
    """minúsculo + sem acento, para casar palavras-chave."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def _so_digitos(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def ler_pdf(conteudo: bytes) -> str:
    r = pypdf.PdfReader(io.BytesIO(conteudo))
    return "\n".join((p.extract_text() or "") for p in r.pages)


def _ler_xlsx(conteudo: bytes) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    linhas = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            linhas.append(" ".join("" if c is None else str(c) for c in row))
    return "\n".join(linhas)


def _ler_xls(conteudo: bytes) -> str:
    import xlrd
    book = xlrd.open_workbook(file_contents=conteudo)
    linhas = []
    for sh in book.sheets():
        for r in range(sh.nrows):
            linhas.append(" ".join(str(sh.cell_value(r, c)) for c in range(sh.ncols)))
    return "\n".join(linhas)


def ler_arquivo(nome: str, conteudo: bytes) -> str:
    """Extrai o texto do comprovante — PDF, XLSX ou XLS."""
    n = (nome or "").lower()
    if n.endswith(".xlsx"):
        return _ler_xlsx(conteudo)
    if n.endswith(".xls"):
        return _ler_xls(conteudo)
    return ler_pdf(conteudo)  # default: PDF


def extrair_dados(texto: str) -> dict:
    d = {"cnpj": None, "competencia": None, "protocolo": None, "data_entrega": None}

    m = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", texto)
    if m:
        d["cnpj"] = _so_digitos(m.group(0))

    # Período de apuração: "01/05/2026 a 31/05/2026" -> competência 05/2026 (mês/ano do início)
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})\s*a\s*\d{2}/\d{2}/\d{4}", texto)
    if m:
        d["competencia"] = f"{m.group(2)}/{m.group(3)}"

    # Protocolo/hash do arquivo
    m = re.search(r"(?:Identifica[cç][aã]o do arquivo|Hash do Arquivo|N[uú]mero do Recibo)\s*:?\s*([0-9A-Fa-f]{16,})", texto)
    if m:
        d["protocolo"] = m.group(1)

    # Data da transmissão (perto de ReceitaNet) — melhor esforço
    m = re.search(r"ReceitaNet\s*:?\s*(\d{2}/\d{2}/\d{4})", texto)
    if m:
        try:
            d["data_entrega"] = datetime.strptime(m.group(1), "%d/%m/%Y")
        except ValueError:
            pass
    return d


def _casa_chave(chave: str, texto_norm: str) -> bool:
    """Match por limite de palavra (evita substring, ex.: 'DAS' em 'apuração DAS')."""
    k = _norm(chave)
    if not k:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", texto_norm) is not None


def candidatos_identificador(texto: str) -> list:
    """Sugere trechos distintivos do documento para usar como identificador."""
    vistos, cands = set(), []

    def add(t):
        t = (t or "").strip(" .:-\t")
        k = _norm(t)
        if t and 3 <= len(t) <= 70 and k and k not in vistos:
            vistos.add(k)
            cands.append(t)

    # 1) "Versão <nome>:" — costuma ser o identificador mais limpo (ex.: EFD-Contribuições, Sped Fiscal)
    for m in re.finditer(r"Vers[aã]o\s+([^\n:]{3,45}?)\s*:", texto):
        add(m.group(1))
    # 2) linhas-título em CAIXA ALTA (tipo do documento)
    for linha in texto.split("\n"):
        l = linha.strip()
        if 12 <= len(l) <= 70 and l == l.upper() and re.search(r"[A-ZÀ-Ÿ]{4}", l) and "R$" not in l and "/" not in l:
            add(l)
    return cands[:6]


def analisar_modelo(db: Session, nome: str, conteudo: bytes) -> dict:
    """Lê um comprovante modelo e sugere identificador(es), checando colisão com os existentes."""
    texto = ler_arquivo(nome, conteudo)
    dados = extrair_dados(texto)
    existentes = []
    for o in db.query(Obrigacao).all():
        for k in (o.identificadores or "").split(","):
            k = k.strip()
            if k:
                existentes.append((o.nome, _norm(k)))
    candidatos = []
    for cnd in candidatos_identificador(texto):
        nc = _norm(cnd)
        colide = sorted({nome for (nome, ek) in existentes if ek and (ek in nc or nc in ek)})
        candidatos.append({"texto": cnd, "colide_com": colide})
    return {
        "cnpj": dados["cnpj"],
        "competencia": dados["competencia"],
        "candidatos": candidatos,
    }


def identificar_obrigacao(db: Session, texto: str):
    """Acha a obrigação cujas palavras-chave (identificadores) aparecem no texto."""
    alvo = _norm(texto)
    candidatas = []
    for o in db.query(Obrigacao).filter(Obrigacao.ativa == True).all():
        chaves = [k.strip() for k in (o.identificadores or "").split(",") if k.strip()]
        if any(_casa_chave(k, alvo) for k in chaves):
            candidatas.append(o)
    return candidatas


def processar(db: Session, nome_arquivo: str, conteudo: bytes) -> dict:
    """Extrai, casa e (se único) baixa a tarefa. Retorna um relatório."""
    texto = ler_arquivo(nome_arquivo, conteudo)
    dados = extrair_dados(texto)
    res = {"arquivo": nome_arquivo, **dados, "status": None, "detalhe": None, "tarefa_id": None}

    if not dados["cnpj"]:
        res.update(status="erro", detalhe="CNPJ não encontrado no documento")
        return res
    empresa = db.query(Empresa).filter(Empresa.cnpj != None).all()
    empresa = next((e for e in empresa if _so_digitos(e.cnpj) == dados["cnpj"]), None)
    if not empresa:
        res.update(status="erro", detalhe=f"Empresa com CNPJ {dados['cnpj']} não cadastrada")
        return res
    res["empresa"] = empresa.razao_social

    obrigacoes = identificar_obrigacao(db, texto)
    if not obrigacoes:
        res.update(status="erro", detalhe="Nenhuma obrigação reconhecida (ajuste os identificadores)")
        return res
    if len(obrigacoes) > 1:
        res.update(status="ambiguo",
                   detalhe="Mais de uma obrigação casou: " + ", ".join(o.nome for o in obrigacoes))
        return res
    obrigacao = obrigacoes[0]
    res["obrigacao"] = obrigacao.nome

    if not dados["competencia"]:
        res.update(status="erro", detalhe="Competência (período de apuração) não encontrada")
        return res

    tarefa = (db.query(Tarefa)
              .filter(Tarefa.empresa_id == empresa.id,
                      Tarefa.obrigacao_id == obrigacao.id,
                      Tarefa.competencia == dados["competencia"])
              .first())
    if not tarefa:
        res.update(status="sem_tarefa",
                   detalhe=f"Sem tarefa de {obrigacao.mininome or obrigacao.nome} "
                           f"para {empresa.razao_social} na competência {dados['competencia']}")
        return res

    res["tarefa_id"] = tarefa.id
    if tarefa.status == StatusTarefa.CONCLUIDA:
        res.update(status="ja_baixada",
                   detalhe=f"Tarefa já estava baixada em {tarefa.data_entrega or tarefa.data_conclusao}")
        return res

    # Baixa
    tarefa.status = StatusTarefa.CONCLUIDA
    tarefa.data_conclusao = datetime.utcnow()
    tarefa.data_entrega = dados["data_entrega"] or datetime.utcnow()
    tarefa.protocolo_entrega = dados["protocolo"]
    tarefa.anexo_nome = nome_arquivo
    db.commit()
    res.update(status="baixada",
               detalhe=f"Tarefa #{tarefa.id} baixada ({obrigacao.mininome or obrigacao.nome} "
                       f"· {empresa.razao_social} · {dados['competencia']})")
    return res
