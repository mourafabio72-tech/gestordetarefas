"""e-validador: lê um comprovante de entrega (PDF), extrai as chaves e casa
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
    """Texto das páginas e, no fim, os dados do arquivo (autor, título, assunto).

    Guia em PDF de imagem não tem texto nenhum, mas há emissor que grava o que
    importa nos dados do arquivo: a Prefeitura do Rio põe "RAZÃO, CNPJ ..." no
    autor e "Guia de Recolhimento de ISS" no título (2026-10-27)."""
    r = pypdf.PdfReader(io.BytesIO(conteudo))
    texto = "\n".join((p.extract_text() or "") for p in r.pages)
    # Página escaneada não tem texto: lê a imagem pelo OCR do servidor
    # (2026-10-28). PDF com texto não passa por aqui, que é o caso comum.
    if not texto.strip():
        from . import ocr
        texto = ocr.ler_imagens_do_pdf(r)
    # Com rótulo, para a tela Modelos saber o que é título (sugestão de
    # palavra-chave) e o que é autor (razão social).
    try:
        meta = r.metadata or {}
        extras = [f"{rotulo} do arquivo: {str(meta.get(k)).strip()}"
                  for k, rotulo in (("/Title", "Título"), ("/Subject", "Assunto"),
                                    ("/Author", "Autor"), ("/Keywords", "Palavras-chave"))
                  if str(meta.get(k) or "").strip()]
    except Exception:
        extras = []
    return texto + ("\n" + "\n".join(extras) if extras else "")


def competencia_do_nome(nome: str):
    """Competência MM/AAAA tirada do nome do arquivo ("ISS 09.2026 VENC ..."),
    ou None. Data completa (06.10.2026) não conta: o "10.2026" de dentro dela
    é o mês do vencimento, não a competência."""
    nome = str(nome or "")
    for m in re.finditer(r"(?<!\d)(0[1-9]|1[0-2])[._/ -](20\d{2})(?!\d)", nome):
        i = m.start()
        if i >= 2 and nome[i - 1] in "._/- " and nome[i - 2].isdigit():
            continue                      # é o mês de uma data dd.mm.aaaa
        return f"{m.group(1)}/{m.group(2)}"
    return None


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


EXT_IMAGEM = (".png", ".jpg", ".jpeg")


def ler_arquivo(nome: str, conteudo: bytes) -> str:
    """Extrai o texto do comprovante: PDF, XLSX, XLS ou imagem (PNG, JPG, pelo OCR)."""
    n = (nome or "").lower()
    if n.endswith(EXT_IMAGEM):
        from . import ocr
        return ocr.ler_imagem(conteudo)
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
    quando algo lido CONTRADIZ o cadastro, não quando falta.
    """
    lido = extrair_dados(texto or "")
    # Completo ou, na falta dele, a raiz (8 dígitos) que o documento traz.
    cnpj_doc = _so_digitos(lido.get("cnpj") or "") or ((lido.get("raizes") or [""])[0])
    comp_doc = lido.get("competencia")
    alertas = []

    cnpj_cad = _so_digitos(cnpj_empresa or "")
    # A mesma RAIZ conta como certo (2026-10-28): matriz e filial são a mesma
    # empresa, e guia federal traz só os 8 primeiros dígitos.
    if cnpj_doc and cnpj_cad and cnpj_doc[:8] != cnpj_cad[:8]:
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
    if len(d) == 8:
        return f"{d[:2]}.{d[2:5]}.{d[5:]}"
    if len(d) != 14:
        return d
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


_MES_POR_NOME = {n: i for i, n in enumerate(
    ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto",
     "setembro", "outubro", "novembro", "dezembro"], start=1)}


def extrair_dados(texto: str) -> dict:
    d = {"cnpj": None, "cnpjs": [], "raizes": [], "competencia": None, "protocolo": None,
         "data_entrega": None}

    # TODOS os CNPJs, com o que tem rótulo ("CNPJ: ...") na frente. Relatório
    # com relação de prestadores sai do PDF com a tabela antes do cabeçalho, e
    # o primeiro CNPJ do texto era o de um prestador (caso de 2026-10-27). Quem
    # escolhe entre eles, olhando o cadastro, é `empresa_do_documento`.
    formato = r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"
    rotulo = r"CNPJ(?:\s*/\s*CPF)?\s*:?\s*"
    rotulados = re.findall(rotulo + "(" + formato + r"|\d{14}(?!\d))", texto, re.IGNORECASE)
    for c in rotulados + re.findall(formato, texto):
        c = _so_digitos(c)
        if c not in d["cnpjs"]:
            d["cnpjs"].append(c)
    d["cnpj"] = d["cnpjs"][0] if d["cnpjs"] else None
    # Só a RAIZ ("CNPJ: 11.222.333", comum em recibo federal), com rótulo e
    # sem a barra da filial depois. Quem casa com o cadastro é
    # `empresas_do_documento` (2026-10-28).
    for r in re.findall(rotulo + r"(\d{2}\.\d{3}\.\d{3})(?![\d/.])", texto, re.IGNORECASE):
        r = _so_digitos(r)
        if r not in d["raizes"]:
            d["raizes"].append(r)

    # Período de apuração: "01/05/2026 a 31/05/2026" -> competência 05/2026 (mês/ano do início)
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})\s*a\s*\d{2}/\d{2}/\d{4}", texto)
    if m:
        d["competencia"] = f"{m.group(2)}/{m.group(3)}"
    else:
        # DARF: "Período de Apuração 31/03/2026", data única e ÚLTIMO dia do
        # período -> 03/2026. Só quando não há período de/a (decisão de
        # 2026-09-19): até aqui toda guia saía com a competência em branco.
        m = re.search(r"per[ií]odo\s+de\s+apura[cç][aã]o\s*:?\s*\d{2}/(\d{2})/(\d{4})",
                      texto, re.IGNORECASE)
        if m:
            d["competencia"] = f"{m.group(1)}/{m.group(2)}"
        else:
            # DAS: só mês e ano, "Agosto/2026", "08/2026" ou "dezembro de 2025".
            m = re.search(r"per[ií]odo\s+de\s+apura[cç][aã]o\s*:?\s*"
                          r"(\d{2}|[a-zç]+)\s*(?:/|de)\s*(\d{4})", texto, re.IGNORECASE)
            if m:
                mes = m.group(1)
                if not mes.isdigit():
                    mes = _MES_POR_NOME.get(_norm(mes))
                if mes and 1 <= int(mes) <= 12:
                    d["competencia"] = f"{int(mes):02d}/{m.group(2)}"
            else:
                # DAS do PGDAS-D: "Período de Apuração" é cabeçalho de tabela e o
                # valor ("agosto/2026") vem linhas depois (PDF real, 2026-09-21).
                # Depois do rótulo, vale o primeiro mês POR EXTENSO: datas
                # dd/mm/aaaa no caminho (vencimento) não contam.
                t = _norm(texto)
                i = re.search(r"periodo\s+de\s+apuracao", t)
                if i:
                    m = re.search(r"(?<![a-z])(" + "|".join(_MES_POR_NOME) + r")\s*(?:/|de)\s*(\d{4})",
                                  t[i.end():])
                    if m:
                        d["competencia"] = f"{_MES_POR_NOME[m.group(1)]:02d}/{m.group(2)}"

    # Rótulo "Competência" com o valor na mesma linha ou logo abaixo, como no
    # DARM do Rio lido pelo OCR ("04. COMPETÊNCIA" ... "CNPJ: ... 09/2026").
    # MM/AAAA solto: o mês de uma data dd/mm/aaaa (vencimento) não conta.
    if not d["competencia"]:
        m = re.search(r"compet[eê]ncia\s*:?[^\n]*\n?[^\n]{0,80}?(?<![\d/])(0[1-9]|1[0-2])/(20\d{2})(?![\d/])",
                      texto, re.IGNORECASE)
        if m:
            d["competencia"] = f"{m.group(1)}/{m.group(2)}"

    # Relatório de apuração: "APURAÇÃO SETEMBRO DE 2026", "Apuração de
    # dezembro/2025". Só mês POR EXTENSO logo depois da palavra, para não
    # pegar data nem título de outro mês no meio do caminho.
    if not d["competencia"]:
        m = re.search(r"apuracao\s+(?:de\s+)?(" + "|".join(_MES_POR_NOME) + r")\s*(?:/|de)?\s*(\d{4})",
                      _norm(texto))
        if m:
            d["competencia"] = f"{_MES_POR_NOME[m.group(1)]:02d}/{m.group(2)}"

    # Protocolo/hash do arquivo
    m = re.search(r"(?:Identifica[cç][aã]o do arquivo|Hash do Arquivo|N[uú]mero do Recibo)\s*:?\s*([0-9A-Fa-f]{16,})", texto)
    if m:
        d["protocolo"] = m.group(1)

    # Data da transmissão (perto de ReceitaNet), melhor esforço
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
        r"(?:Raz[aã]o\s+Social|Nome\s+Empresarial|Contribuinte|Nome/Nome\s+Empresarial|Empresa"
        r"|Autor\s+do\s+arquivo)\s*:?\s*"
        r"([^\n]{4,120})",
        texto, re.IGNORECASE)
    if m:
        nome = m.group(1).strip(" .:-\t")
        # corta se vier "CNPJ:" grudado na mesma linha
        nome = re.split(r",?\s+CNPJ", nome, flags=re.IGNORECASE)[0].strip(" ,")
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
    branco é GUIA: documento a pagar, que o escritório entrega ao cliente. O
    mesmo DARF com autenticação bancária é COMPROVANTE: prova de que foi pago,
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
    # "apuração das contas" viraria guia: a prova pegou isso. Para o DAS do
    # Simples, exige-se a sigla perto de "simples", que é como o documento
    # sempre se apresenta.
    if re.search(r"\bdarf\b|\bdarj\b|\bgps\b|\bgnre\b|\bdae\b|\bdam\b"
                 r"|guia de recolhimento|guia de arrecada|documento de arrecada"
                 r"|codigo de barras|linha digitavel|\bboleto\b"
                 r"|\bdas\b[^\n]{0,40}simples|simples[^\n]{0,40}\bdas\b", t):
        return "guia"
    # 3. Recibo ANTES de declaração: "Recibo de Entrega da ECF" é o recibo, não
    # a ECF. O recibo é a prova de que a declaração foi entregue, e é ele que
    # costuma chegar ao escritório.
    if re.search(r"recibo de entrega|comprovante de entrega|recibo de transmiss|protocolo de entrega|recibo|transmiss", t):
        return "recibo_entrega"
    # 4. A declaração em si: o documento transmitido ou o espelho dele.
    if re.search(r"declaracao|\becf\b|\becd\b|\bdctf\b|\bdirf\b|\brais\b|\bdefis\b"
                 r"|\bdasn\b|\bdmed\b|\bdimob\b|\bsped\b|\befd\b|escrituracao", t):
        return "declaracao"
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

    # 0) título e assunto gravados no arquivo (ler_pdf): numa guia em imagem
    # são o único texto que diz o tipo do documento.
    for m in re.finditer(r"(?:T[ií]tulo|Assunto) do arquivo:\s*([^\n]+)", texto):
        add(m.group(1))
    # 1) "Versão <nome>:", costuma ser o identificador mais limpo (ex.: EFD-Contribuições, Sped Fiscal)
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
        "competencia": dados["competencia"] or competencia_do_nome(nome),
        "candidatos": candidatos,
    }


def identificar_obrigacao(db: Session, texto: str):
    """Acha a obrigação cujas palavras-chave (identificadores) aparecem no texto.

    Obrigação INTERNA fica fora POR PADRÃO: ela não troca documento com o
    cliente, e deixá-la concorrer criaria ambiguidade com quem de fato recebe.

    A exceção, aberta em 2026-09-09 junto com a reversão de `models.py`: interna
    que LIGOU `exige_documento` entra. Ela tem documento, só que quem anexa é o
    analista. Sem esta exceção a flag seria uma armadilha: a tarefa passaria a
    exigir documento e o e-validador nunca acharia a obrigação para dar a baixa,
    deixando o trabalho travado, que é pior do que era antes.

    Interna com a flag em `NULL` continua de fora, como sempre esteve.
    `transmitir` entra como `receber`: o recibo do órgão é o documento que casa.
    """
    alvo = _norm(texto)
    casadas = []                       # (obrigação, chaves dela que casaram)
    for o in db.query(Obrigacao).filter(
            Obrigacao.ativa == True,
            (Obrigacao.sentido.is_(None)) | (Obrigacao.sentido != "interna")
            | (Obrigacao.exige_documento.is_(True))).all():
        chaves = [k.strip() for k in (o.identificadores or "").split(",") if k.strip()]
        achadas = [_norm(k) for k in chaves if _casa_chave(k, alvo)]
        if achadas:
            casadas.append((o, achadas))

    # Desempate pela chave mais específica (decisão de 2026-09-19): a chave do
    # SPED Fiscal está DENTRO da do SPED Contribuições, e todo recibo de
    # Contribuições casava com as duas. A candidata sai quando TODA chave dela
    # que casou está contida numa chave MAIOR que casou em outra. Chaves
    # independentes, ou iguais, continuam ambíguas: aí não há o que escolher.
    def engolida(minhas, outra):
        return all(any(len(k) < len(maior) and _casa_chave(k, maior) for maior in outra)
                   for k in minhas)

    return [o for o, minhas in casadas
            if not any(engolida(minhas, outras) for p, outras in casadas if p is not o)]


def empresas_do_documento(db: Session, dados: dict) -> list:
    """As empresas que o documento pode ser, pelo CNPJ.

    1. O primeiro CNPJ completo da lista (rotulado na frente) que é de empresa
       cadastrada: uma só. CNPJ de prestador numa relação não é cliente e fica
       de fora; se for cliente também, o rótulo do cabeçalho decide.
    2. Sem completo cadastrado, a RAIZ (8 dígitos), tirada dos completos lidos
       e depois das raízes soltas (2026-10-28). Raiz de matriz e filiais
       devolve todas, e quem desempata é a tarefa (`processar`).
    """
    empresas = db.query(Empresa).filter(Empresa.cnpj != None).order_by(Empresa.cnpj).all()
    cad = {}
    for e in empresas:
        cad.setdefault(_so_digitos(e.cnpj), e)
    cnpjs = dados.get("cnpjs") or ([dados["cnpj"]] if dados.get("cnpj") else [])
    for c in cnpjs:
        if c in cad:
            return [cad[c]]
    for raiz in [c[:8] for c in cnpjs] + list(dados.get("raizes") or []):
        achadas = [e for e in empresas if _so_digitos(e.cnpj)[:8] == raiz]
        if achadas:
            return achadas
    return []


def empresa_do_documento(db: Session, dados: dict):
    """A empresa do documento, quando o CNPJ (ou a raiz) aponta UMA só."""
    achadas = empresas_do_documento(db, dados)
    return achadas[0] if len(achadas) == 1 else None


def analisar_para_repositorio(db: Session, nome: str, conteudo: bytes) -> dict:
    """Lê um documento-modelo e devolve tudo que o repositório precisa mostrar
    para revisão antes de salvar: empresa (casada por CNPJ), tipo, candidatos a
    identificador e a obrigação já reconhecida (se algum identificador atual casar)."""
    texto = ler_arquivo(nome, conteudo)
    dados = extrair_dados(texto)
    empresa = empresa_do_documento(db, dados)
    if empresa:
        dados["cnpj"] = _so_digitos(empresa.cnpj)
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
        "competencia_exemplo": dados["competencia"] or competencia_do_nome(nome),
        "protocolo_exemplo": dados["protocolo"],
        "candidatos": candidatos,
        "obrigacao_sugerida_id": obrig_sugerida.id if obrig_sugerida else None,
        "obrigacao_sugerida_nome": obrig_sugerida.nome if obrig_sugerida else None,
        "texto_extraido": texto,
    }


LIMITE_IDENTIFICADORES = 2000   # tamanho da coluna obrigacoes.identificadores


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
    nova = ",".join(atuais + [ident])
    # Recusa explícita em vez de deixar o banco estourar: um erro com nome é
    # acionável, um 500 no meio do cadastro não é.
    if len(nova) > LIMITE_IDENTIFICADORES:
        raise ValueError(
            f"A lista de identificadores de '{o.nome}' chegaria a {len(nova)} caracteres, "
            f"acima do limite de {LIMITE_IDENTIFICADORES}. Apague os que não usa mais "
            f"em Cadastro → Obrigações antes de acrescentar outro.")
    o.identificadores = nova
    return True


def _cabe(valor, limite: int):
    """Corta o texto no limite da coluna. None continua None.

    Tudo aqui vem de dentro de um PDF, e PDF não respeita tamanho de coluna: o
    protocolo é um hash sem tamanho máximo no padrão que o extrai, e a
    competência mal lida pode trazer a frase inteira. Estourar a coluna derruba
    o INSERT com erro 500 no meio do cadastro, e a tela não tem como explicar
    isso a quem está só salvando um modelo.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto[:limite] or None


def salvar_modelo(db: Session, dados: dict) -> "object":
    """Grava um Modelo no repositório e treina a obrigação vinculada (se houver)."""
    from ..models import Modelo
    # A competência só entra se estiver no formato da coluna (MM/AAAA); qualquer
    # outra coisa é leitura ruim, e guardá-la cortada em 7 caracteres inventaria
    # um dado errado em vez de admitir que não leu.
    comp = (dados.get("competencia_exemplo") or "").strip()
    if not re.fullmatch(r"\d{2}/\d{4}", comp):
        comp = None
    m = Modelo(
        nome_arquivo=_cabe(dados.get("nome_arquivo"), 200),
        cnpj=_cabe(_so_digitos(dados.get("cnpj") or ""), 14),
        razao_social_extraida=_cabe(dados.get("razao_social_extraida"), 200),
        empresa_id=dados.get("empresa_id"),
        obrigacao_id=dados.get("obrigacao_id"),
        tipo_documento=_cabe(dados.get("tipo_documento") or "outro", 30),
        identificador=_cabe(dados.get("identificador"), 120),
        competencia_exemplo=comp,
        protocolo_exemplo=_cabe(dados.get("protocolo_exemplo"), 120),
        texto_extraido=dados.get("texto_extraido"),
    )
    db.add(m)
    _treinar_obrigacao(db, m.obrigacao_id, m.identificador)
    db.commit()
    db.refresh(m)
    return m


def _esquecer_identificador(db: Session, obrigacao_id, ident: str, ignorar_modelo_id=None):
    """Tira o identificador da obrigação, se nenhum OUTRO modelo ainda o usar.

    Editar um modelo tem de desfazer o treino que ele causou: é justamente
    para isso que se edita, quando o vínculo saiu errado. Mas dois modelos
    podem ter chegado ao mesmo identificador (o mesmo layout em duas empresas),
    e aí apagá-lo cegamente desligaria o reconhecimento dos dois.
    """
    from ..models import Modelo
    if not obrigacao_id or not (ident or "").strip():
        return False
    o = db.query(Obrigacao).filter(Obrigacao.id == obrigacao_id).first()
    if not o:
        return False
    outros = db.query(Modelo).filter(
        Modelo.obrigacao_id == obrigacao_id,
        Modelo.identificador.isnot(None))
    if ignorar_modelo_id:
        outros = outros.filter(Modelo.id != ignorar_modelo_id)
    if any(_norm(m.identificador) == _norm(ident) for m in outros.all()):
        return False
    atuais = [k.strip() for k in (o.identificadores or "").split(",") if k.strip()]
    restantes = [k for k in atuais if _norm(k) != _norm(ident)]
    if len(restantes) == len(atuais):
        return False
    o.identificadores = ",".join(restantes)
    return True


def atualizar_modelo(db: Session, modelo_id: int, dados: dict):
    """Edita um modelo e ACERTA o treino: o identificador antigo sai da
    obrigação antiga, o novo entra na nova.

    Sem isso, corrigir um vínculo errado na tela deixaria o erro vivo onde ele
    importa, na lista de identificadores da obrigação, que é o que o
    e-validador consulta.
    """
    from ..models import Modelo
    m = db.query(Modelo).filter(Modelo.id == modelo_id).first()
    if not m:
        return None

    ident_novo = (dados.get("identificador") or "").strip() or None
    obrig_nova = dados.get("obrigacao_id")
    mudou_vinculo = (_norm(ident_novo or "") != _norm(m.identificador or "")
                     or obrig_nova != m.obrigacao_id)
    if mudou_vinculo:
        _esquecer_identificador(db, m.obrigacao_id, m.identificador, ignorar_modelo_id=m.id)

    comp = (dados.get("competencia_exemplo") or "").strip()
    m.nome_arquivo = _cabe(dados.get("nome_arquivo"), 200) or m.nome_arquivo
    m.cnpj = _cabe(_so_digitos(dados.get("cnpj") or ""), 14)
    m.razao_social_extraida = _cabe(dados.get("razao_social_extraida"), 200)
    m.empresa_id = dados.get("empresa_id")
    m.obrigacao_id = obrig_nova
    m.tipo_documento = _cabe(dados.get("tipo_documento") or "outro", 30)
    m.identificador = _cabe(ident_novo, 120)
    m.competencia_exemplo = comp if re.fullmatch(r"\d{2}/\d{4}", comp) else None
    m.protocolo_exemplo = _cabe(dados.get("protocolo_exemplo"), 120)

    if mudou_vinculo:
        _treinar_obrigacao(db, m.obrigacao_id, m.identificador)
    db.commit()
    db.refresh(m)
    return m


def _quando_br(dt) -> str:
    """'28/10/2026 às 10:23' no horário de Brasília. A conclusão é gravada em
    UTC (utcnow), e a mensagem mostrava '2026-10-28 13:23:25.392285'. Data sem
    fuso é tratada como UTC, que é como o app grava."""
    if not dt:
        return "data não registrada"
    from datetime import timezone
    from zoneinfo import ZoneInfo
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y às %H:%M")


def processar(db: Session, nome_arquivo: str, conteudo: bytes) -> dict:
    """Extrai, casa e (se único) baixa a tarefa. Retorna um relatório.
    Se o método regex/palavra-chave não resolver e a IA estiver ativa, usa a IA
    como reforço para preencher CNPJ/competência/obrigação."""
    texto = ler_arquivo(nome_arquivo, conteudo)
    dados = extrair_dados(texto)
    obrigacoes = identificar_obrigacao(db, texto)
    usou_ia = False
    # Documento sem competência legível (guia em imagem): vale a do nome do
    # arquivo, convenção do escritório, antes da IA. Não conta como LIDA na
    # guia: `conferir_saida` relê o texto, e a guia de "entregar" espera alguém.
    origem_comp = "documento" if dados["competencia"] else None
    if not dados["competencia"]:
        dados["competencia"] = competencia_do_nome(nome_arquivo)
        origem_comp = "nome do arquivo" if dados["competencia"] else None

    # Reforço por IA só quando o método atual não resolveu.
    if (not (dados["cnpj"] or dados["raizes"])) or (not dados["competencia"]) or (len(obrigacoes) != 1):
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

    if origem_comp is None and dados["competencia"]:
        origem_comp = "IA"
    res = {"arquivo": nome_arquivo, **dados, "ia": usou_ia, "competencia_origem": origem_comp,
           "status": None, "detalhe": None, "tarefa_id": None}

    if not (dados["cnpj"] or dados["raizes"]):
        res.update(status="erro", detalhe="CNPJ não encontrado no documento")
        return res
    if dados["cnpj"] and dados["cnpj"] not in dados["cnpjs"]:
        dados["cnpjs"].append(dados["cnpj"])        # veio da IA
    candidatas = empresas_do_documento(db, dados)
    if not candidatas:
        lido = dados["cnpj"] or dados["raizes"][0]
        res.update(status="erro", detalhe=f"Empresa com CNPJ {_formata_cnpj(lido)} não cadastrada")
        return res
    # Raiz de matriz e filiais: a empresa sai da TAREFA, mais abaixo.
    empresa = candidatas[0] if len(candidatas) == 1 else None
    if empresa:
        dados["cnpj"] = res["cnpj"] = _so_digitos(empresa.cnpj)
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

    tarefas = (db.query(Tarefa)
               .filter(Tarefa.empresa_id.in_([c.id for c in candidatas]),
                       Tarefa.obrigacao_id == obrigacao.id,
                       Tarefa.competencia == dados["competencia"])
               .order_by(Tarefa.id).all())
    if empresa is None and len(tarefas) > 1:
        # Só a raiz casou e mais de uma empresa do grupo tem a tarefa: vale a
        # única ainda aberta; com duas abertas não se chuta.
        abertas = [t for t in tarefas
                   if t.status not in (StatusTarefa.CONCLUIDA, StatusTarefa.CANCELADA)]
        if len(abertas) == 1:
            tarefas = abertas
        else:
            nomes = ", ".join(sorted({t.empresa.razao_social for t in (abertas or tarefas)}))
            res.update(status="ambiguo",
                       detalhe=f"A raiz do CNPJ {_formata_cnpj(dados['raizes'][0] if dados['raizes'] else dados['cnpj'][:8])} "
                               f"é de mais de uma empresa com esta tarefa: {nomes}. "
                               f"Envie o documento com o CNPJ completo ou dê baixa na tela.")
            return res
    tarefa = tarefas[0] if tarefas else None
    if not tarefa:
        quem = empresa.razao_social if empresa else ", ".join(c.razao_social for c in candidatas)
        res.update(status="sem_tarefa",
                   detalhe=f"Sem tarefa de {obrigacao.mininome or obrigacao.nome} "
                           f"para {quem} na competência {dados['competencia']}")
        return res
    if empresa is None:
        empresa = tarefa.empresa
        dados["cnpj"] = res["cnpj"] = _so_digitos(empresa.cnpj)
        res["empresa"] = empresa.razao_social

    res["tarefa_id"] = tarefa.id
    if tarefa.status == StatusTarefa.CONCLUIDA:
        res.update(status="ja_baixada",
                   detalhe=f"Tarefa já estava baixada em "
                           f"{_quando_br(tarefa.data_conclusao or tarefa.data_entrega)}.")
        return res
    # Tarefa cancelada não recebe baixa automática. Vale sobretudo para a que
    # alguém marcou como "não se aplica a esta empresa": um documento chegando
    # depois reverteria a decisão em silêncio, concluindo um trabalho que uma
    # pessoa disse por escrito que não era daquele cliente.
    if tarefa.status == StatusTarefa.CANCELADA:
        motivo = ("marcada como 'não se aplica a esta empresa'"
                  if tarefa.nao_se_aplica else "cancelada")
        res.update(status="cancelada",
                   detalhe=f"Tarefa #{tarefa.id} está {motivo}. "
                           f"Para dar baixa, reabra a tarefa antes.")
        return res

    # O ARQUIVO fica guardado, e não só o nome. Até 2026-09-19 esta linha era
    # `tarefa.anexo_nome = nome_arquivo`: o acervo listava o recibo e o
    # download respondia 410, porque o conteúdo nunca foi salvo.
    from . import upload as up

    # Guia de "entregar": vai para a SAÍDA e NÃO conclui aqui. Quem conclui é a
    # entrega ao cliente (services/entrega_cliente.py), chamada pela rota do
    # e-validador, e só se alguém recebeu. Decisão 2a de 2026-09-19: sai
    # sozinha só se o CNPJ e a competência LIDOS na guia batem com a tarefa;
    # valor que veio da IA não conta, e a guia espera alguém conferir.
    if tarefa.sentido == "entregar":
        up.trocar_saida(db, tarefa, nome_arquivo, conteudo)
        db.commit()
        conf = conferir_saida(texto, empresa.cnpj, tarefa.competencia)
        if conf["ok"] and conf["cnpj_lido"] and conf["competencia_lida"]:
            res.update(status="pronta_para_envio",
                       detalhe=f"Guia anexada à tarefa #{tarefa.id}.")
        else:
            # Diz o que FALTOU, e de onde veio o que não foi lido na guia:
            # "CNPJ e competência não foram lidos" aparecia mesmo com o CNPJ
            # lido dos dados do arquivo (guia de ISS em imagem, 2026-10-27).
            nao_lidos = []
            if not conf["cnpj_lido"]:
                nao_lidos.append("o CNPJ" + (" (veio da IA)" if usou_ia else ""))
            if not conf["competencia_lida"]:
                de_onde = {"nome do arquivo": " (veio do nome do arquivo)", "IA": " (veio da IA)"}
                nao_lidos.append("a competência" + de_onde.get(origem_comp, ""))
            falta = conf["alertas"] or [
                "Não foi lido na própria guia: " + " e ".join(nao_lidos) + "."]
            res.update(status="aguardando_conferencia",
                       detalhe=f"Guia anexada à tarefa #{tarefa.id}, sem envio: "
                               + " ".join(falta)
                               + " Confira e use \"Enviar ao cliente\" na tarefa.")
        return res

    # Baixa
    tarefa.status = StatusTarefa.CONCLUIDA
    tarefa.data_conclusao = datetime.utcnow()
    tarefa.data_entrega = dados["data_entrega"] or datetime.utcnow()
    tarefa.protocolo_entrega = dados["protocolo"]
    # "ev<id>" no lugar do token do link público: tarefa fora de "receber" não
    # tem token (fase 28), e o prefixo só separa arquivos de mesmo nome.
    tarefa.anexo_nome = up.salvar_arquivo(f"ev{tarefa.id}", nome_arquivo, conteudo)
    db.commit()
    res.update(status="baixada",
               detalhe=f"Tarefa #{tarefa.id} baixada ({obrigacao.mininome or obrigacao.nome} "
                       f"· {empresa.razao_social} · {dados['competencia']})")
    return res
