from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel
from ..database import get_db
from ..models import Usuario, Modelo
from ..auth import require_perm
from ..services.validador import analisar_para_repositorio, salvar_modelo, _norm

router = APIRouter(prefix="/modelos", tags=["modelos"])

TIPOS = {"recibo_entrega": "Recibo de entrega",
         "comprovante_pagamento": "Comprovante de pagamento",
         "relatorio": "Relatório",
         "outro": "Outro"}


def _serializar(m: Modelo) -> dict:
    return {
        "id": m.id,
        "nome_arquivo": m.nome_arquivo,
        "cnpj": m.cnpj,
        "razao_social_extraida": m.razao_social_extraida,
        "empresa_id": m.empresa_id,
        "empresa_nome": m.empresa.razao_social if m.empresa else None,
        "obrigacao_id": m.obrigacao_id,
        "obrigacao_nome": m.obrigacao.nome if m.obrigacao else None,
        "tipo_documento": m.tipo_documento,
        "tipo_label": TIPOS.get(m.tipo_documento, m.tipo_documento),
        "identificador": m.identificador,
        "competencia_exemplo": m.competencia_exemplo,
        "protocolo_exemplo": m.protocolo_exemplo,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("")
def listar(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("evalidador", "ver")),
):
    modelos = db.query(Modelo).order_by(Modelo.created_at.desc()).all()
    return [_serializar(m) for m in modelos]


@router.post("/analisar")
async def analisar(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("evalidador", "editar")),
):
    """Lê o documento e devolve a pré-visualização (empresa, tipo, candidatos a
    identificador, obrigação sugerida) para revisão antes de salvar."""
    conteudo = await arquivo.read()
    try:
        return analisar_para_repositorio(db, arquivo.filename, conteudo)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Falha ao ler o arquivo: {e}")


@router.post("/lote")
async def lote(
    arquivos: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("evalidador", "editar")),
):
    """Analisa vários documentos: salva sozinho os 100% reconhecidos (empresa casada
    por CNPJ + obrigação sugerida + identificador livre de colisão) e devolve os demais
    para revisão manual. Não salva automático se o identificador colidir — nem com os
    existentes, nem com outro arquivo do mesmo lote (evita bagunçar o matcher)."""
    salvos, revisar = [], []
    usados = {}  # identificador_normalizado -> obrigacao_id já escolhido neste lote

    for arq in arquivos:
        conteudo = await arq.read()
        try:
            a = analisar_para_repositorio(db, arq.filename, conteudo)
        except Exception as e:
            revisar.append({"nome_arquivo": arq.filename, "erro": f"Falha ao ler: {e}",
                            "cnpj": None, "candidatos": []})
            continue

        # candidato livre de colisão com os identificadores já cadastrados
        livre = next((c for c in a.get("candidatos", []) if not c.get("colide_com")), None)
        ident_norm = _norm(livre["texto"]) if livre else None

        pode_auto = (
            a.get("empresa_id")
            and a.get("obrigacao_sugerida_id")
            and livre
            and not (ident_norm in usados and usados[ident_norm] != a["obrigacao_sugerida_id"])
        )

        if pode_auto:
            m = salvar_modelo(db, {
                "nome_arquivo": a["nome_arquivo"],
                "cnpj": a["cnpj"],
                "razao_social_extraida": a["razao_social_extraida"],
                "empresa_id": a["empresa_id"],
                "obrigacao_id": a["obrigacao_sugerida_id"],
                "tipo_documento": a["tipo_documento"],
                "identificador": livre["texto"],
                "competencia_exemplo": a["competencia_exemplo"],
                "protocolo_exemplo": a["protocolo_exemplo"],
                "texto_extraido": a["texto_extraido"],
            })
            usados[ident_norm] = a["obrigacao_sugerida_id"]
            salvos.append(_serializar(m))
        else:
            # motivo curto para a UI
            if not a.get("empresa_id"):
                a["motivo"] = "Empresa não reconhecida (CNPJ não cadastrado)"
            elif not a.get("obrigacao_sugerida_id"):
                a["motivo"] = "Obrigação não reconhecida — escolha e defina o identificador"
            elif not livre:
                a["motivo"] = "Identificador candidato colide com obrigação existente"
            else:
                a["motivo"] = "Identificador repetido no lote para outra obrigação"
            revisar.append(a)

    return {
        "resumo": {"total": len(arquivos), "salvos": len(salvos), "revisar": len(revisar)},
        "salvos": salvos,
        "revisar": revisar,
    }


@router.post("")
def criar(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("evalidador", "editar")),
):
    """Grava o modelo revisado e treina a obrigação vinculada (acrescenta o
    identificador escolhido à lista da obrigação)."""
    if not body.get("cnpj") and not body.get("razao_social_extraida"):
        raise HTTPException(status_code=422, detail="Documento sem CNPJ nem razão social identificados.")
    m = salvar_modelo(db, body)
    return _serializar(m)


@router.delete("/{modelo_id}")
def excluir(
    modelo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("evalidador", "editar")),
):
    m = db.query(Modelo).filter(Modelo.id == modelo_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    db.delete(m)
    db.commit()
    return {"ok": True}
