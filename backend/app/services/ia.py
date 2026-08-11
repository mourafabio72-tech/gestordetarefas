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


def testar(cfg: dict) -> dict:
    """Ping rápido: confirma que a chave/modelo respondem (sem precisar de documento)."""
    key = (cfg.get("openai_api_key") or "").strip()
    if not key:
        return {"ok": False, "erro": "Chave da OpenAI não configurada."}
    modelo = cfg.get("openai_model") or "gpt-4o-mini"
    url = cfg.get("openai_url") or "https://api.openai.com/v1/chat/completions"
    payload = {"model": modelo, "temperature": 0, "max_tokens": 5,
               "messages": [{"role": "user", "content": "Responda apenas: OK"}]}
    try:
        r = httpx.post(url, headers={"Authorization": f"Bearer {key}",
                                     "Content-Type": "application/json"},
                       json=payload, timeout=30.0)
        if r.status_code != 200:
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
