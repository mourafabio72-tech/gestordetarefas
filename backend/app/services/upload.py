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


def remover_arquivo(nome: str) -> bool:
    """Apaga um comprovante do volume. Devolve se havia algo para apagar.

    Chamado quando a tarefa é excluída DE VEZ. Sem isso o arquivo fica no
    volume para sempre, sem nada no banco apontando para ele -- lixo que não dá
    nem para achar depois. `basename` impede que um nome guardado com ".." saia
    apagando fora da pasta.
    """
    if not nome:
        return False
    caminho = os.path.join(UPLOAD_DIR, os.path.basename(nome))
    try:
        if os.path.isfile(caminho):
            os.remove(caminho)
            return True
    except OSError:
        pass          # arquivo em uso ou permissão: a tarefa some do mesmo jeito
    return False


def remover_arquivos(nomes) -> int:
    """Tira do volume vários arquivos de uma vez. Devolve quantos saíram.

    Existe porque uma tarefa pode ter DOIS arquivos, em campos separados de
    propósito: `anexo_nome`, o comprovante que o cliente subiu, e `saida_nome`,
    o documento que o escritório entregou. A exclusão apagava só o primeiro, e
    toda guia já enviada virava arquivo órfão no volume. A exclusão por
    competência não apagava nenhum dos dois: um mês inteiro deixava centenas.

    Nome repetido ou vazio não conta duas vezes.
    """
    vistos, saidos = set(), 0
    for nome in nomes:
        if not nome or nome in vistos:
            continue
        vistos.add(nome)
        if remover_arquivo(nome):
            saidos += 1
    return saidos


def caminho_do_anexo(nome: str):
    """Caminho absoluto do comprovante no volume, ou None se não houver arquivo.

    `basename` antes de juntar: o nome vem do banco, mas um registro antigo ou
    adulterado com ".." leria arquivo fora da pasta de uploads. A checagem é
    barata e a consequência de não fazer é servir qualquer arquivo do container.
    """
    if not nome:
        return None
    caminho = os.path.join(UPLOAD_DIR, os.path.basename(nome))
    return caminho if os.path.isfile(caminho) else None


def nome_de_exibicao(nome: str) -> str:
    """O nome que o arquivo tinha quando foi enviado.

    No volume ele é guardado como "{token}_{arquivo}", e o token é a credencial
    do link público de envio. Devolvê-lo no cabeçalho do download vazaria por
    histórico do navegador e pasta de downloads — e aquele link, enquanto a
    tarefa existir, deixa qualquer um substituir o comprovante.
    """
    base = os.path.basename(nome or "")
    # Documento de saída é "saida_{id}_{arquivo}": duas partes a descartar, não
    # uma. Cortar só a primeira deixaria o id da tarefa colado no nome.
    if base.startswith("saida_"):
        partes = base.split("_", 2)
        return partes[2] if len(partes) == 3 else base
    return base.split("_", 1)[1] if "_" in base else (base or "comprovante")


def salvar_arquivo(token: str, filename: str, conteudo: bytes) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    nome = f"{token}_{_seguro(filename)}"
    with open(os.path.join(UPLOAD_DIR, nome), "wb") as f:
        f.write(conteudo)
    return nome


# Quem busca o link sem ser o cliente. O WhatsApp puxa a URL para montar a
# prévia da mensagem assim que ela é enviada -- antes de qualquer pessoa tocar
# nela --, e o mesmo vale para Telegram, Slack e afins.
ROBOS = ("whatsapp", "facebookexternalhit", "facebot", "telegrambot", "slackbot",
         "discordbot", "twitterbot", "linkedinbot", "skypeuripreview", "bingbot",
         "googlebot", "bot/", "crawler", "spider", "preview", "curl", "wget",
         "python-requests", "httpx", "axios")

# Duas requisições do mesmo lugar em segundos são a mesma abertura: visualizador
# de PDF pede o arquivo em partes, e recarregar a página é reflexo, não segunda
# consulta.
JANELA_MESMA_ABERTURA = 120   # segundos


def eh_robo(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return any(marca in ua for marca in ROBOS)


def conta_como_abertura(user_agent: str, segundos_desde_o_ultimo) -> bool:
    """Esta requisição é uma abertura nova do cliente?

    Não conta robô, e não conta repetição do mesmo IP dentro da janela. O
    registro de auditoria guarda as duas assim mesmo -- o que se descarta é a
    CONTAGEM, porque "o cliente abriu 2 vezes" quando ele abriu uma faz duvidar
    do número inteiro.
    """
    if eh_robo(user_agent):
        return False
    if segundos_desde_o_ultimo is not None and segundos_desde_o_ultimo < JANELA_MESMA_ABERTURA:
        return False
    return True


def token_saida(db, tarefa) -> str:
    """Token do link público do documento de saída, criando se não houver."""
    if not tarefa.saida_token:
        tarefa.saida_token = secrets.token_urlsafe(24)
        db.commit()
    return tarefa.saida_token


def link_saida(cfg: dict, tarefa, db) -> str:
    base = (cfg.get("public_url") or "").rstrip("/")
    return f"{base}/api/publico/baixar/{token_saida(db, tarefa)}"


def salvar_saida(tarefa_id: int, filename: str, conteudo: bytes) -> str:
    """Guarda o documento que o escritório vai ENTREGAR ao cliente.

    Prefixo "saida_" no nome para o arquivo se distinguir do comprovante que o
    cliente sobe, que fica na mesma pasta. Olhar o volume e não saber o que
    entra e o que sai é o tipo de coisa que só atrapalha no dia da urgência.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    nome = f"saida_{tarefa_id}_{_seguro(filename)}"
    with open(os.path.join(UPLOAD_DIR, nome), "wb") as f:
        f.write(conteudo)
    return nome


def ler_arquivo_salvo(nome: str) -> bytes:
    """Conteúdo de um arquivo do volume. Levanta se não existir."""
    caminho = caminho_do_anexo(nome)
    if not caminho:
        raise FileNotFoundError(nome)
    with open(caminho, "rb") as f:
        return f.read()


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
