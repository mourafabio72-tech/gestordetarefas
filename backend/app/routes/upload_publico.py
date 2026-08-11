"""Endpoints PÚBLICOS (sem login) de envio de comprovante por token.
O token é único por tarefa e não expõe dados sensíveis além do necessário
para o cliente entender o que enviar."""
import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Tarefa, Empresa, Obrigacao, StatusTarefa
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
