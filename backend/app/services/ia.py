"""Reforço do e-validador com IA (OpenAI). Só texto. Chamada apenas quando o
método regex/palavra-chave não resolve (fallback). Devolve CNPJ, competência e
o id da obrigação identificada."""
import re
import json
import httpx
from . import config as cfgmod


def _digits(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def disponivel(cfg: dict) -> bool:
    return cfgmod.ativo(cfg, "ia_ativo") and bool((cfg.get("openai_api_key") or "").strip())


PROVEDORES = {
    "openai": ("OpenAI", "openai_api_key", "openai_model", "openai_url",
               "gpt-4o-mini", "https://api.openai.com/v1/chat/completions"),
    "nvidia": ("NVIDIA", "nvidia_api_key", "nvidia_model", "nvidia_url",
               "nvidia/llama-3.1-nemotron-70b-instruct", "https://integrate.api.nvidia.com/v1/chat/completions"),
}


def provedor_escolhido(cfg: dict) -> str:
    p = (cfg.get("ia_provedor") or "openai").strip().lower()
    return p if p in PROVEDORES else "openai"


def credenciais(cfg: dict, provedor: str):
    """(nome, chave, modelo, url) do provedor. Chave vazia = não configurado."""
    nome, k_chave, k_modelo, k_url, modelo_pad, url_pad = PROVEDORES[provedor]
    modelo = (cfg.get(k_modelo) or "").strip() or modelo_pad
    return (nome, (cfg.get(k_chave) or "").strip(),
            cfgmod.MODELOS_RETIRADOS.get(modelo, modelo),
            (cfg.get(k_url) or "").strip() or url_pad)


def _erro_http(nome: str, status: int, modelo: str) -> str:
    """Mensagem para a tela. Sem o corpo da resposta: ele pode ecoar o pedido."""
    if status in (404, 410):
        return (f"A {nome} respondeu HTTP {status}: o modelo {modelo} saiu do catálogo. "
                "Troque o modelo em Configuração > Inteligência artificial.")
    return f"A {nome} respondeu HTTP {status}."


def pergunta_disponivel(cfg: dict) -> bool:
    return bool(credenciais(cfg, provedor_escolhido(cfg))[1])


def testar(cfg: dict, provedor: str = "openai") -> dict:
    """Ping rápido: confirma que a chave/modelo respondem (sem precisar de documento)."""
    nome, key, modelo, url = credenciais(cfg, provedor)
    if not key:
        return {"ok": False, "erro": f"Chave da {nome} não configurada."}
    payload = {"model": modelo, "temperature": 0, "max_tokens": 5,
               "messages": [{"role": "user", "content": "Responda apenas: OK"}]}
    try:
        r = httpx.post(url, headers={"Authorization": f"Bearer {key}",
                                     "Content-Type": "application/json"},
                       json=payload, timeout=30.0)
        if r.status_code != 200:
            if r.status_code in (404, 410):
                return {"ok": False, "erro": _erro_http(nome, r.status_code, modelo)}
            return {"ok": False, "erro": f"HTTP {r.status_code}: {r.text[:180]}"}
        resp = r.json()["choices"][0]["message"]["content"].strip()
        return {"ok": True, "modelo": modelo, "resposta": resp}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


def extrair(texto: str, obrigacoes: list, cfg: dict) -> dict:
    """Retorna {'cnpj', 'competencia', 'obrigacao_id'} (qualquer um pode vir None).
    `obrigacoes` = lista de Obrigacao ativas (para a IA escolher entre elas)."""
    key = (cfg.get("openai_api_key") or "").strip()
    if not key:
        return {}
    modelo = cfg.get("openai_model") or "gpt-4o-mini"
    url = cfg.get("openai_url") or "https://api.openai.com/v1/chat/completions"
    lista = "\n".join(f"- id {o.id}: {o.nome}" for o in obrigacoes) or "(nenhuma)"

    sistema = ("Você lê comprovantes/recibos de entrega de obrigações contábeis brasileiras "
               "e extrai dados com precisão. Responda SOMENTE JSON válido.")
    usuario = (
        "Do documento abaixo, extraia:\n"
        "- cnpj: os 14 dígitos do CNPJ do contribuinte (só números) ou null\n"
        "- competencia: o período de apuração no formato MM/AAAA ou null\n"
        "- obrigacao_id: o id da obrigação da lista que este documento comprova, ou null se nenhuma casa\n\n"
        f"Obrigações cadastradas:\n{lista}\n\n"
        f'Documento (texto extraído):\n"""{(texto or "")[:6000]}"""\n\n'
        'Responda: {"cnpj": "...", "competencia": "MM/AAAA", "obrigacao_id": 0}'
    )
    payload = {
        "model": modelo,
        "messages": [{"role": "system", "content": sistema},
                     {"role": "user", "content": usuario}],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    try:
        r = httpx.post(url, headers={"Authorization": f"Bearer {key}",
                                     "Content-Type": "application/json"},
                       json=payload, timeout=45.0)
        if r.status_code != 200:
            return {"erro": f"IA HTTP {r.status_code}"}
        conteudo = r.json()["choices"][0]["message"]["content"]
        d = json.loads(conteudo)
        oid = d.get("obrigacao_id")
        try:
            oid = int(oid) if oid not in (None, "", 0, "0") else None
        except (TypeError, ValueError):
            oid = None
        return {
            "cnpj": _digits(d.get("cnpj")) or None,
            "competencia": (d.get("competencia") or None),
            "obrigacao_id": oid,
        }
    except Exception as e:  # pragma: no cover
        return {"erro": str(e)}


# ---------- "Pergunte à IA" ----------
# A IA só traduz a pergunta num filtro. Ela recebe a pergunta e a data de hoje,
# e mais nada: o banco não sai daqui. Quem lista as tarefas é o Tareffas, com o
# escopo de quem perguntou (routes/ia.py).

_DIAS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
         "sexta-feira", "sábado", "domingo")

_SISTEMA_PERGUNTA = (
    "Você traduz perguntas sobre tarefas de um escritório contábil num filtro JSON. "
    "Não responda a pergunta: devolva SOMENTE um objeto JSON, sem texto em volta. "
    "Campos (todos opcionais, omita o que a pergunta não pede):\n"
    '- situacao: "atrasada" (prazo já passou e não foi feita), "hoje" (vence hoje), '
    '"semana" (vence de hoje a 7 dias), "aberta" (não concluída), "concluida", "cancelada"\n'
    '- data_campo: "prazo" (prazo interno da equipe, o padrão) ou "vencimento" (prazo legal)\n'
    "- data_de, data_ate: datas AAAA-MM-DD, para períodos (\"esta semana\", \"até sexta\", \"em outubro\")\n"
    '- competencia: "MM/AAAA" quando a pergunta cita o mês de competência\n'
    "- setor: nome do setor citado (Fiscal, Contábil, DP, Financeiro...)\n"
    "- empresa: nome do cliente citado\n"
    "- obrigacao: nome da obrigação ou tarefa citada (DCTFWeb, Reinf, ECD, conciliação...)\n"
    '- minhas: true quando a pergunta é sobre "minhas" tarefas\n'
    '- prioridade: "baixa", "media", "alta", "urgente" ou "alta_urgente"\n'
    "- multa: true para tarefas que geram multa\n"
    '- contar: true quando a pergunta pede quantidade ("quantas", "quantos")'
)


def _json_da_resposta(texto: str):
    """Lê o objeto JSON da resposta. Modelos da NVIDIA costumam cercar o JSON
    com texto ou com cerca de código; pega do primeiro { ao último }."""
    texto = (texto or "").strip()
    try:
        d = json.loads(texto)
        return d if isinstance(d, dict) else None
    except ValueError:
        pass
    i, j = texto.find("{"), texto.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        d = json.loads(texto[i:j + 1])
        return d if isinstance(d, dict) else None
    except ValueError:
        return None


def interpretar(pergunta: str, hoje, cfg: dict) -> dict:
    """{'filtro': {...}, 'provedor': 'nvidia'} ou {'erro': '...'}. O filtro
    vem cru: quem valida campo a campo é a rota."""
    provedor = provedor_escolhido(cfg)
    nome, key, modelo, url = credenciais(cfg, provedor)
    if not key:
        return {"erro": "IA não configurada."}
    usuario = (f"Hoje é {hoje.isoformat()} ({_DIAS[hoje.weekday()]}).\n"
               f'Pergunta: """{pergunta}"""')
    payload = {"model": modelo, "temperature": 0, "max_tokens": 300,
               "messages": [{"role": "system", "content": _SISTEMA_PERGUNTA},
                            {"role": "user", "content": usuario}]}
    if provedor == "openai":
        payload["response_format"] = {"type": "json_object"}
    try:
        r = httpx.post(url, headers={"Authorization": f"Bearer {key}",
                                     "Content-Type": "application/json"},
                       json=payload, timeout=30.0)
        if r.status_code != 200:
            return {"erro": _erro_http(nome, r.status_code, modelo), "provedor": provedor}
        conteudo = r.json()["choices"][0]["message"]["content"]
    except Exception:
        return {"erro": f"Não consegui falar com a {nome} agora.", "provedor": provedor}
    filtro = _json_da_resposta(conteudo)
    if filtro is None:
        return {"erro": "A IA não entendeu a pergunta. Tente com outras palavras.", "provedor": provedor}
    return {"filtro": filtro, "provedor": provedor}
