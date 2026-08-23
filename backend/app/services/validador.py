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
from . import config as cfgmod
from . import ia as ia_mod


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


def conferir_saida(texto: str, cnpj_empresa: str, competencia_tarefa: str) -> dict:
    """O documento que vai sair é mesmo desta empresa e desta competência?

    Mandar a guia de um cliente para outro é o erro caro deste fluxo: o cliente
    recebe dado de terceiro e o escritório descobre pelo telefone. A conferência
    lê o próprio PDF e compara com o cadastro.

    AVISA, não bloqueia. Guia sem CNPJ legível existe (imagem escaneada,
    layout de prefeitura), e recusar o envio nesses casos travaria trabalho
    legítimo por falta de prova, não por prova em contrário. O que não se pode
    é deixar passar em silêncio o documento que diz OUTRO CNPJ.

    Devolve `{ok, alertas[], cnpj_lido, competencia_lida}`. `ok` só é falso
    quando algo lido CONTRADIZ o cadastro — não quando falta.
    """
    lido = extrair_dados(texto or "")
    cnpj_doc = _so_digitos(lido.get("cnpj") or "")
    comp_doc = lido.get("competencia")
    alertas = []

    cnpj_cad = _so_digitos(cnpj_empresa or "")
    if cnpj_doc and cnpj_cad and cnpj_doc != cnpj_cad:
        alertas.append(f"O documento é do CNPJ {_formata_cnpj(cnpj_doc)}, "
                       f"e a empresa da tarefa é {_formata_cnpj(cnpj_cad)}.")
    if comp_doc and competencia_tarefa and comp_doc != competencia_tarefa:
        alertas.append(f"O documento é da competência {comp_doc}, "
                       f"e a tarefa é de {competencia_tarefa}.")

    return {"ok": not alertas, "alertas": alertas,
            "cnpj_lido": cnpj_doc or None, "competencia_lida": comp_doc,
            # Sem texto legível não há o que conferir, e a tela precisa dizer
            # isso em vez de dar a impressão de que conferiu e passou.
            "leu_algo": bool(cnpj_doc or comp_doc)}


def _formata_cnpj(d: str) -> str:
    d = _so_digitos(d or "")
    if len(d) != 14:
        return d
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


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


def extrair_razao_social(texto: str) -> str:
    """Tenta ler o nome da empresa no documento (por rótulo ou linha vizinha ao CNPJ)."""
    # 1) por rótulo explícito
    m = re.search(
        r"(?:Raz[aã]o\s+Social|Nome\s+Empresarial|Contribuinte|Nome/Nome\s+Empresarial|Empresa)\s*:?\s*"
        r"([^\n]{4,120})",
        texto, re.IGNORECASE)
    if m:
        nome = m.group(1).strip(" .:-\t")
        # corta se vier "CNPJ:" grudado na mesma linha
        nome = re.split(r"\s+CNPJ", nome, flags=re.IGNORECASE)[0].strip()
        if 4 <= len(nome) <= 120:
            return nome
    # 2) linha imediatamente antes/depois do CNPJ, se parecer nome de empresa
    linhas = texto.split("\n")
    for i, l in enumerate(linhas):
        if re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", l):
            for j in (i, i - 1, i + 1):
                if 0 <= j < len(linhas):
                    cand = re.sub(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "", linhas[j]).strip(" .:-\t")
                    if 4 <= len(cand) <= 120 and re.search(r"[A-Za-zÀ-ÿ]{4}", cand) and "R$" not in cand:
                        return cand
            break
    return None


def classificar_tipo(texto: str) -> str:
    """Classifica o documento para organizar o repositório.

    A ordem importa, e o par guia/comprovante é o que mais erra: um DARF em
    branco é GUIA — documento a pagar, que o escritório entrega ao cliente. O
    mesmo DARF com autenticação bancária é COMPROVANTE — prova de que foi pago,
    que o cliente devolve. São papéis opostos no fluxo, e a versão anterior
    chamava os dois de comprovante só porque a palavra "DARF" aparecia.

    Por isso a marca de PAGAMENTO é testada primeiro: ela é o que distingue.
    """
    t = _norm(texto)
    # 1. Pago: autenticação, data de pagamento, o próprio "comprovante".
    if re.search(r"comprovante de pagamento|comprovante de arrecada|autenticacao banc"
                 r"|autenticacao mecanica|pagamento efetuado|data (?:do |de )?pagamento", t):
        return "comprovante_pagamento"
    # 2. Guia a pagar: o documento em si, sem marca de quitação.
    #
    # "DAS" fica FORA da lista de siglas soltas: "das" é preposição, e
    # "apuração das contas" viraria guia — a prova pegou isso. Para o DAS do
    # Simples, exige-se a sigla perto de "simples", que é como o documento
    # sempre se apresenta.
    if re.search(r"\bdarf\b|\bdarj\b|\bgps\b|\bgnre\b|\bdae\b|\bdam\b"
                 r"|guia de recolhimento|guia de arrecada|documento de arrecada"
                 r"|codigo de barras|linha digitavel|\bboleto\b"
                 r"|\bdas\b[^\n]{0,40}simples|simples[^\n]{0,40}\bdas\b", t):
        return "guia"
    if re.search(r"recibo de entrega|comprovante de entrega|recibo de transmiss|protocolo de entrega|recibo|transmiss", t):
        return "recibo_entrega"
    if re.search(r"relatorio|demonstrativo|balancete|extrato|memoria de calculo|apuracao", t):
        return "relatorio"
    return "outro"


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


def casar_empresa_por_cnpj(db: Session, cnpj: str):
    """Empresa cadastrada cujo CNPJ (só dígitos) bate com o informado."""
    if not cnpj:
        return None
    for e in db.query(Empresa).filter(Empresa.cnpj != None).all():
        if _so_digitos(e.cnpj) == _so_digitos(cnpj):
            return e
    return None


def analisar_para_repositorio(db: Session, nome: str, conteudo: bytes) -> dict:
    """Lê um documento-modelo e devolve tudo que o repositório precisa mostrar
    para revisão antes de salvar: empresa (casada por CNPJ), tipo, candidatos a
    identificador e a obrigação já reconhecida (se algum identificador atual casar)."""
    texto = ler_arquivo(nome, conteudo)
    dados = extrair_dados(texto)
    empresa = casar_empresa_por_cnpj(db, dados["cnpj"])
    razao = extrair_razao_social(texto)

    # colisão dos candidatos com identificadores já existentes
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

    # obrigação sugerida: se algum identificador atual já casa com este texto
    sugeridas = identificar_obrigacao(db, texto)
    obrig_sugerida = sugeridas[0] if len(sugeridas) == 1 else None

    return {
        "nome_arquivo": nome,
        "cnpj": dados["cnpj"],
        "razao_social_extraida": razao,
        "empresa_id": empresa.id if empresa else None,
        "empresa_nome": empresa.razao_social if empresa else None,
        "tipo_documento": classificar_tipo(texto),
        "competencia_exemplo": dados["competencia"],
        "protocolo_exemplo": dados["protocolo"],
        "candidatos": candidatos,
        "obrigacao_sugerida_id": obrig_sugerida.id if obrig_sugerida else None,
        "obrigacao_sugerida_nome": obrig_sugerida.nome if obrig_sugerida else None,
        "texto_extraido": texto,
    }


def _treinar_obrigacao(db: Session, obrigacao_id: int, identificador: str) -> bool:
    """Acrescenta o identificador do modelo à lista da obrigação (dedup por forma
    normalizada). É assim que o modelo 'treina' o e-validador."""
    ident = (identificador or "").strip()
    if not obrigacao_id or not ident:
        return False
    o = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id).first()
    if not o:
        return False
    atuais = [k.strip() for k in (o.identificadores or "").split(",") if k.strip()]
    if any(_norm(k) == _norm(ident) for k in atuais):
        return False
    atuais.append(ident)
    o.identificadores = ",".join(atuais)
    return True


def salvar_modelo(db: Session, dados: dict) -> "object":
    """Grava um Modelo no repositório e treina a obrigação vinculada (se houver)."""
    from ..models import Modelo
    m = Modelo(
        nome_arquivo=dados.get("nome_arquivo"),
        cnpj=_so_digitos(dados.get("cnpj") or "") or None,
        razao_social_extraida=dados.get("razao_social_extraida"),
        empresa_id=dados.get("empresa_id"),
        obrigacao_id=dados.get("obrigacao_id"),
        tipo_documento=dados.get("tipo_documento") or "outro",
        identificador=(dados.get("identificador") or "").strip() or None,
        competencia_exemplo=dados.get("competencia_exemplo"),
        protocolo_exemplo=dados.get("protocolo_exemplo"),
        texto_extraido=dados.get("texto_extraido"),
    )
    db.add(m)
    _treinar_obrigacao(db, m.obrigacao_id, m.identificador)
    db.commit()
    db.refresh(m)
    return m


def processar(db: Session, nome_arquivo: str, conteudo: bytes) -> dict:
    """Extrai, casa e (se único) baixa a tarefa. Retorna um relatório.
    Se o método regex/palavra-chave não resolver e a IA estiver ativa, usa a IA
    como reforço para preencher CNPJ/competência/obrigação."""
    texto = ler_arquivo(nome_arquivo, conteudo)
    dados = extrair_dados(texto)
    obrigacoes = identificar_obrigacao(db, texto)
    usou_ia = False

    # Reforço por IA só quando o método atual não resolveu.
    if (not dados["cnpj"]) or (not dados["competencia"]) or (len(obrigacoes) != 1):
        cfg = cfgmod.carregar(db)
        if ia_mod.disponivel(cfg):
            ativas = db.query(Obrigacao).filter(Obrigacao.ativa == True).all()
            r_ia = ia_mod.extrair(texto, ativas, cfg)
            if r_ia and not r_ia.get("erro"):
                usou_ia = True
                if not dados["cnpj"] and r_ia.get("cnpj"):
                    dados["cnpj"] = r_ia["cnpj"]
                if not dados["competencia"] and r_ia.get("competencia"):
                    dados["competencia"] = r_ia["competencia"]
                if len(obrigacoes) != 1 and r_ia.get("obrigacao_id"):
                    o = db.query(Obrigacao).filter(Obrigacao.id == r_ia["obrigacao_id"]).first()
                    if o:
                        obrigacoes = [o]

    res = {"arquivo": nome_arquivo, **dados, "ia": usou_ia,
           "status": None, "detalhe": None, "tarefa_id": None}

    if not dados["cnpj"]:
        res.update(status="erro", detalhe="CNPJ não encontrado no documento")
        return res
    empresa = db.query(Empresa).filter(Empresa.cnpj != None).all()
    empresa = next((e for e in empresa if _so_digitos(e.cnpj) == dados["cnpj"]), None)
    if not empresa:
        res.update(status="erro", detalhe=f"Empresa com CNPJ {dados['cnpj']} não cadastrada")
        return res
    res["empresa"] = empresa.razao_social

    if not obrigacoes:
        res.update(status="erro", detalhe="Nenhuma obrigação reconhecida (ajuste os identificadores ou ative a IA)")
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
