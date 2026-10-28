"""Lote do e-validador com documentos complementares (2026-10-28).

A guia dá baixa na tarefa; o complementar (memória de cálculo, relatório,
extrato) vai ao cliente JUNTO dela. Decisão do Fábio: o vínculo é automático,
pelo próprio lote. Arquivo que não casa com obrigação nenhuma, mas traz o CNPJ
(ou a raiz) e a competência de uma guia de "entregar" do mesmo lote, vira
complementar da tarefa dessa guia.

A ordem importa: o lote inteiro é lido ANTES de qualquer envio. Se a guia
saísse na hora em que é lida, o complementar que vem depois dela na lista
chegaria tarde, com a mensagem ao cliente já enviada.
"""
from ..models import Tarefa
from . import upload as up
from .validador import processar

# Guias que recebem complementar: as de "entregar" anexadas neste lote.
_GUIA_DO_LOTE = ("pronta_para_envio", "aguardando_conferencia")


def _nome_da_guia(tarefa) -> str:
    o = tarefa.obrigacao
    return ((o.mininome or "").strip() or o.nome) if o else tarefa.titulo


def vincular(db, itens: list) -> None:
    """Liga cada arquivo sem obrigação à guia do lote de mesma empresa e
    competência. `itens` é a lista de {res, nome, conteudo}; o `res` de cada
    complementar é reescrito com o resultado."""
    guias = {}
    for it in itens:
        r = it["res"]
        if r.get("status") in _GUIA_DO_LOTE and r.get("tarefa_id"):
            t = db.get(Tarefa, r["tarefa_id"])
            if t:
                guias[t.id] = t
    if not guias:
        return
    for it in itens:
        r = it["res"]
        if not (r.get("sem_obrigacao") and r.get("empresa_ids")):
            continue
        comp = r.get("competencia")
        alvos = [t for t in guias.values()
                 if t.empresa_id in r["empresa_ids"] and (not comp or t.competencia == comp)]
        if len(alvos) == 1:
            t = alvos[0]
            up.salvar_complementar(db, t, it["nome"], it["conteudo"])
            r.update(status="complementar", tarefa_id=t.id, sem_obrigacao=False,
                     empresa=t.empresa.razao_social if t.empresa else r.get("empresa"),
                     detalhe=f"Complementar da guia {_nome_da_guia(t)} (tarefa #{t.id}): "
                             f"vai junto para o cliente.")
        elif len(alvos) > 1:
            nomes = ", ".join(f"{_nome_da_guia(t)} (#{t.id})" for t in alvos)
            r.update(status="ambiguo",
                     detalhe=f"Serve a mais de uma guia deste lote: {nomes}. "
                             f"Processe cada guia com os complementares dela num lote separado.")
    db.commit()


async def processar_lote(db, arquivos: list, enviar) -> list:
    """Lê todos, liga os complementares e só então envia as guias prontas.

    `arquivos` é a lista de (nome, conteúdo); `enviar(db, tarefa_id)` é a
    entrega ao cliente, recebida de fora para a prova trocar por um dublê.
    """
    itens = []
    for nome, conteudo in arquivos:
        try:
            res = processar(db, nome, conteudo)
        except Exception as e:
            res = {"arquivo": nome, "status": "erro", "detalhe": f"Falha ao ler o PDF: {e}"}
        itens.append({"res": res, "nome": nome, "conteudo": conteudo})
    vincular(db, itens)
    for it in itens:
        if it["res"].get("status") == "pronta_para_envio":
            it["res"].update(await enviar(db, it["res"]["tarefa_id"]))
    resultados = []
    for it in itens:
        r = it["res"]
        r.pop("sem_obrigacao", None)
        r.pop("empresa_ids", None)
        resultados.append(r)
    return resultados
