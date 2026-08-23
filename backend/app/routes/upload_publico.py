"""Endpoints PÚBLICOS (sem login) de envio de comprovante por token.
O token é único por tarefa e não expõe dados sensíveis além do necessário
para o cliente entender o que enviar."""
import os
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Tarefa, Empresa, Obrigacao, StatusTarefa, SaidaAcesso
from ..services import upload as up

router = APIRouter(prefix="/publico", tags=["publico"])


def _tarefa_por_token(db: Session, token: str) -> Tarefa:
    t = db.query(Tarefa).filter(Tarefa.upload_token == token).first()
    if not t:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado.")
    if t.empresa and t.empresa.bloqueado:
        raise HTTPException(status_code=403, detail="Envio indisponível.")
    return t


@router.get("/tarefa/{token}")
def contexto(token: str, db: Session = Depends(get_db)):
    t = _tarefa_por_token(db, token)
    obrig = db.query(Obrigacao).filter(Obrigacao.id == t.obrigacao_id).first() if t.obrigacao_id else None
    return {
        "titulo": t.titulo,
        "empresa": t.empresa.razao_social if t.empresa else None,
        "obrigacao": obrig.nome if obrig else None,
        "competencia": t.competencia,
        "prazo": t.data_prazo.isoformat() if t.data_prazo else None,
        "ja_enviado": t.status == StatusTarefa.CONCLUIDA,
        "anexo_nome": t.anexo_nome,
    }


@router.post("/tarefa/{token}")
async def enviar(token: str, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    t = _tarefa_por_token(db, token)
    ext = os.path.splitext((arquivo.filename or "").lower())[1]
    if ext not in up.EXT_OK:
        raise HTTPException(status_code=422, detail="Formato não aceito. Envie PDF, Excel ou imagem.")
    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=422, detail="Arquivo vazio.")
    if len(conteudo) > up.MAX_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo grande demais (máx. 15 MB).")
    res = up.registrar_baixa(db, t, arquivo.filename, conteudo)
    return {"ok": True, **res}


# Tipos que o navegador abre sem baixar. PDF é o caso de 90% das guias, e abrir
# na hora é o que o cliente espera de um link no WhatsApp.
_ABRE_NO_NAVEGADOR = {".pdf": "application/pdf", ".png": "image/png",
                      ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


@router.get("/baixar/{token}")
def baixar_documento(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Entrega ao CLIENTE o documento da tarefa, pelo link que ele recebeu.

    Sem login: quem tem o link entra, como no envio de comprovante. O token é
    de 24 bytes e vale por tarefa — e trocar o documento gera token novo, o que
    invalida o link anterior. É assim que uma guia retificada tira a errada de
    circulação em vez de deixar as duas valendo.

    Cada acesso é registrado, e é isto que responde a pergunta do fim do mês:
    quais clientes ainda não pegaram a guia. Um anexo de e-mail sai do nosso
    alcance no instante do envio; um link é uma requisição aqui.
    """
    tarefa = db.query(Tarefa).filter(Tarefa.saida_token == token).first()
    if not tarefa or not tarefa.saida_nome:
        raise HTTPException(status_code=404, detail="Documento não encontrado ou link expirado.")
    caminho = up.caminho_do_anexo(tarefa.saida_nome)
    if not caminho:
        raise HTTPException(status_code=410, detail="O arquivo não está mais disponível.")

    # Registra ANTES de servir: se o download falhar no meio, o acesso
    # aconteceu do mesmo jeito, e é o acesso que se quer saber.
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() \
        or (request.client.host if request.client else "")
    ua = (request.headers.get("user-agent") or "")[:300]

    # Quanto faz desde a última vez que ESTE ip pegou ESTE documento. O
    # WhatsApp busca o link para montar a prévia antes de alguém clicar, e o
    # visualizador de PDF pede o arquivo em partes — as duas coisas inflavam o
    # contador e faziam "abriu 2×" onde houve uma abertura só.
    # Só acessos que CONTARAM entram na janela. Sem este filtro, a prévia do
    # WhatsApp — que chega segundos antes — engoliria a primeira abertura de
    # verdade sempre que as duas saíssem do mesmo IP, como acontece numa rede
    # corporativa.
    ultimo = (db.query(SaidaAcesso)
              .filter(SaidaAcesso.tarefa_id == tarefa.id, SaidaAcesso.ip == ip[:60],
                      SaidaAcesso.contado == True)
              .order_by(SaidaAcesso.id.desc()).first())
    segundos = None
    if ultimo is not None and ultimo.quando is not None:
        agora = datetime.now(ultimo.quando.tzinfo) if ultimo.quando.tzinfo else datetime.utcnow()
        segundos = (agora - ultimo.quando).total_seconds()

    conta = up.conta_como_abertura(ua, segundos)
    db.add(SaidaAcesso(tarefa_id=tarefa.id, ip=ip[:60], user_agent=ua, contado=conta))
    if conta:
        tarefa.saida_downloads = (tarefa.saida_downloads or 0) + 1
        tarefa.saida_baixada_em = datetime.utcnow()
    db.commit()

    nome = up.nome_de_exibicao(tarefa.saida_nome)
    ext = os.path.splitext(nome)[1].lower()
    tipo = _ABRE_NO_NAVEGADOR.get(ext, "application/octet-stream")
    return FileResponse(caminho, media_type=tipo, filename=nome,
                        content_disposition_type="inline" if ext in _ABRE_NO_NAVEGADOR else "attachment")
