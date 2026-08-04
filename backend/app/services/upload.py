"""Upload público de comprovante por tarefa.

O cliente recebe no alerta um link único (com token) por tarefa. Ao subir o
arquivo, a tarefa é baixada — como o token identifica exatamente a tarefa, não
depende do matcher do e-validador.
"""
import os
import re
import secrets
from datetime import datetime
from ..models import Tarefa, StatusTarefa
from . import validador

# Volume em produção (EasyPanel): defina UPLOAD_DIR=/app/data/uploads
UPLOAD_DIR = os.getenv("UPLOAD_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")

EXT_OK = {".pdf", ".xlsx", ".xls", ".png", ".jpg", ".jpeg"}
MAX_BYTES = 15 * 1024 * 1024  # 15 MB


def get_or_create_token(db, tarefa: Tarefa) -> str:
    if not tarefa.upload_token:
        tarefa.upload_token = secrets.token_urlsafe(24)
        db.commit()
    return tarefa.upload_token


def link_publico(cfg: dict, tarefa: Tarefa, db) -> str:
    base = (cfg.get("public_url") or "").rstrip("/")
    return f"{base}/enviar/{get_or_create_token(db, tarefa)}"


def _seguro(nome: str) -> str:
    nome = os.path.basename(nome or "arquivo")
    return re.sub(r"[^A-Za-z0-9._-]", "_", nome)[:120] or "arquivo"


def salvar_arquivo(token: str, filename: str, conteudo: bytes) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    nome = f"{token}_{_seguro(filename)}"
    with open(os.path.join(UPLOAD_DIR, nome), "wb") as f:
        f.write(conteudo)
    return nome


def registrar_baixa(db, tarefa: Tarefa, filename: str, conteudo: bytes) -> dict:
    """Salva o arquivo e baixa a tarefa (best-effort na extração de protocolo/data)."""
    guardado = salvar_arquivo(tarefa.upload_token, filename, conteudo)
    protocolo, data_entrega = None, None
    try:
        texto = validador.ler_arquivo(filename, conteudo)
        dados = validador.extrair_dados(texto)
        protocolo = dados.get("protocolo")
        data_entrega = dados.get("data_entrega")
    except Exception:
        pass  # imagem/planilha sem texto — segue só com o arquivo

    tarefa.anexo_nome = guardado
    tarefa.protocolo_entrega = protocolo
    tarefa.data_entrega = data_entrega or datetime.utcnow()
    tarefa.status = StatusTarefa.CONCLUIDA
    tarefa.data_conclusao = datetime.utcnow()
    db.commit()
    return {"status": "baixada", "arquivo": guardado, "protocolo": protocolo}
