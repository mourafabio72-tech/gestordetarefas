from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel
from ..database import get_db
from ..models import Usuario, Modelo
from ..auth import require_perm
from ..services.validador import analisar_para_repositorio, salvar_modelo, _norm

router = APIRouter(prefix="/modelos", tags=["modelos"])

TIPOS = {"guia": "Guia a pagar (DARF, DAS, GPS…)",
         "comprovante_pagamento": "Comprovante de pagamento",
         "declaracao": "Declaração (ECF, ECD, DCTF, DEFIS…)",
         "recibo_entrega": "Recibo de entrega",
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
    auto: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("evalidador", "editar")),
):
    """Analisa vários documentos e devolve todos com a sugestão preenchida.

    O salvamento automático ficou DESLIGADO por padrão (`auto=false`), e a razão
    veio do uso: o matcher casou quatro de seis arquivos com a obrigação errada
    — PIS, ICMS e Simples entrando como IPI — porque um identificador genérico
    salvo antes casava com toda guia. Cada acerto errado era salvo sozinho e
    reforçava o erro, sem ninguém ver.

    A sugestão continua: o formulário vem preenchido com empresa, obrigação e
    identificador. O que mudou é que alguém confirma antes de virar treino.
    """
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

        # Candidato utilizável: sem colisão, OU colidindo apenas com a própria
        # obrigação sugerida — que é o caso do segundo layout do mesmo documento
        # (Lucro Real e Presumido caindo na mesma apuração). Tratar isso como
        # colisão mandaria para revisão manual justamente o que dá para resolver
        # sozinho.
        nome_sugerida = (a.get("obrigacao_sugerida_nome") or "").strip().lower()

        def _utilizavel(c):
            outras = [n for n in (c.get("colide_com") or [])
                      if str(n).strip().lower() != nome_sugerida]
            return not outras

        livre = next((c for c in a.get("candidatos", []) if _utilizavel(c)), None)
        ident_norm = _norm(livre["texto"]) if livre else None

        pode_auto = (
            auto
            and a.get("empresa_id")
            and a.get("obrigacao_sugerida_id")
            and livre
            and not (ident_norm in usados and usados[ident_norm] != a["obrigacao_sugerida_id"])
        )

        if pode_auto:
          # O salvamento também precisa estar protegido: fora do try, um único
          # arquivo que derruba o INSERT leva junto a remessa inteira — os
          # outros quatro, que estavam bem, voltam como "falhou ao enviar" e a
          # pessoa procura defeito onde não há.
          try:
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
          except Exception as e:
            db.rollback()
            a["motivo"] = f"Falha ao salvar automaticamente: {e}"
            revisar.append(a)
        else:
            # motivo curto para a UI
            if not auto and a.get("empresa_id") and a.get("obrigacao_sugerida_id"):
                a["motivo"] = "Reconhecido — confira e salve"
            elif not a.get("empresa_id"):
                a["motivo"] = "Empresa não reconhecida (CNPJ não cadastrado)"
            elif not a.get("obrigacao_sugerida_id"):
                a["motivo"] = "Obrigação não reconhecida: escolha e defina o identificador"
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
    # Um 500 mudo aqui é o pior desfecho: quem está cadastrando não tem acesso
    # ao log do servidor, e a tela só sabe dizer "erro no servidor". Traduzir a
    # exceção em mensagem é o que transforma o problema em algo acionável.
    try:
        m = salvar_modelo(db, body)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=422,
                            detail=f"Não consegui salvar este modelo: {type(e).__name__}: {e}"[:400])
    return _serializar(m)


@router.put("/{modelo_id}")
def editar(
    modelo_id: int,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_perm("evalidador", "editar")),
):
    """Altera qualquer campo do modelo e acerta o treino da obrigação."""
    from ..services.validador import atualizar_modelo
    try:
        m = atualizar_modelo(db, modelo_id, body)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=422,
                            detail=f"Não consegui salvar a alteração: {type(e).__name__}: {e}"[:400])
    if not m:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
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
    # O treino sai junto. Apagar o modelo e deixar o identificador na obrigação
    # é o pior dos dois mundos: some o registro de onde aquilo veio, e o
    # e-validador continua casando por ele — foi assim que os vínculos errados
    # sobreviveram à limpeza dos modelos.
    from ..services.validador import _esquecer_identificador
    esqueceu = _esquecer_identificador(db, m.obrigacao_id, m.identificador,
                                       ignorar_modelo_id=m.id)
    db.delete(m)
    db.commit()
    return {"ok": True, "identificador_removido": esqueceu}
