"""Entrega do documento de SAÍDA ao cliente.

Saiu da rota `POST /tarefas/{id}/enviar-cliente` em 2026-09-19, quando o
e-validador passou a enviar a guia que reconhece. As duas portas chamam esta
função, e a regra que importa fica escrita uma vez: a tarefa só conclui se
ALGUÉM recebeu.
"""
import secrets
from datetime import datetime

from ..models import StatusTarefa, TarefaEnvio
from ..seguranca import log_event


class SemDocumento(Exception):
    pass


class ArquivoSumiu(Exception):
    pass


class SemDestinatario(Exception):
    pass


async def entregar_saida(db, tarefa, enviado_por=None, ensaio=False, origem="tela") -> dict:
    """Entrega o documento anexado ao cliente e conclui a tarefa.

    Vai para os contatos da EMPRESA e para os USUÁRIOS do tipo cliente ligados
    a ela, sem repetir endereço.

    A tarefa só é concluída se ALGUÉM recebeu. Concluir com todos os envios
    falhando registraria como entregue um documento que não chegou a ninguém,
    e o erro só apareceria quando o cliente reclamasse da multa.

    `ensaio=True` devolve a lista de destinatários sem enviar nada.
    """
    from . import upload as up, config as cfgmod
    from .whatsapp import destinatarios_cliente, carregar_zap, send_whatsapp_message
    from .email import send_email
    from .razao_social import formatar as formatar_razao

    if not tarefa.saida_nome:
        raise SemDocumento("Anexe o documento antes de enviar.")
    try:
        conteudo = up.ler_arquivo_salvo(tarefa.saida_nome)
    except FileNotFoundError:
        raise ArquivoSumiu("O arquivo não está mais no armazenamento.")

    destinos = destinatarios_cliente(db, tarefa)
    if not destinos:
        raise SemDestinatario(
            "A empresa não tem e-mail nem telefone, e não há usuário do tipo "
            "cliente vinculado a ela. Sem isso não há para onde enviar.")
    if ensaio:
        return {"ensaio": True, "arquivo": up.nome_de_exibicao(tarefa.saida_nome),
                "destinatarios": destinos}

    cfg = cfgmod.carregar(db)
    nome_arquivo = up.nome_de_exibicao(tarefa.saida_nome)
    empresa = formatar_razao(tarefa.empresa.razao_social) if tarefa.empresa else ""
    comp = f" ({tarefa.competencia})" if tarefa.competencia else ""
    assunto = f"[BPS4] {tarefa.titulo}{comp}"
    # Um link POR DESTINATÁRIO, não um por tarefa. Com link único, o acesso diz
    # que alguém abriu; a pergunta é quem: o sócio que paga ou o e-mail geral
    # que ninguém lê. O token do envio responde isso.
    base = (cfg.get("public_url") or "").rstrip("/")
    # O documento do cliente não vai para atendente do escritório: quem recebe é
    # o cliente, e o atendimento nasce na fila padrão da conexão.
    await carregar_zap(cfg)

    resultados = []
    for d in destinos:
        # O envio nasce ANTES da mensagem sair: é dele que vem o token do link,
        # e o texto precisa carregar esse token.
        envio = TarefaEnvio(tarefa_id=tarefa.id, arquivo=nome_arquivo, canal=d["canal"],
                            endereco=d["endereco"], destinatario=d["nome"],
                            token=secrets.token_urlsafe(24), sucesso=False,
                            enviado_por=enviado_por)
        db.add(envio)
        db.flush()          # garante o id sem fechar a transação
        link = f"{base}/api/publico/baixar/{envio.token}"
        texto = (f"Olá,\n\nSegue {tarefa.titulo}{comp} referente a {empresa}.\n\n"
                 f"📎 {nome_arquivo}\n{link}\n\nQualquer dúvida, estamos à disposição.")

        # Exceção de rede de UM destinatário não derruba os outros nem apaga o
        # que já saiu (achado de 2026-09-19): antes, o WhatsApp levantando
        # depois de o e-mail ter saído desfazia a transação, o envio real
        # sumia do banco e um reenvio duplicava a mensagem ao cliente.
        try:
            if d["canal"] == "whatsapp":
                # Link, não arquivo: é o que se pode rastrear, e ainda dispensa o
                # provedor aceitar o anexo.
                r = await send_whatsapp_message(d["endereco"], texto, cfg)
            else:
                r = send_email(d["endereco"], assunto, texto, cfg,
                               anexos=[(nome_arquivo, conteudo)])
        except Exception as e:
            r = {"success": False, "error": f"{type(e).__name__}: {e}"}
        ok = bool(r.get("success"))
        envio.sucesso = ok
        envio.detalhe = None if ok else str(r.get("error") or r.get("response") or "")[:500]
        # Grava cada envio assim que ele sai: o registro do que chegou ao
        # cliente não pode depender de o próximo destinatário dar certo.
        db.commit()
        resultados.append({**d, "enviado": ok, "detalhe": r})

    entregou = any(r["enviado"] for r in resultados)
    if entregou:
        tarefa.status = StatusTarefa.CONCLUIDA
        tarefa.data_conclusao = datetime.utcnow()
        tarefa.data_entrega = tarefa.data_entrega or datetime.utcnow()
    db.commit()

    enviados = sum(1 for r in resultados if r["enviado"])
    # Contagem, e nunca endereço ou telefone: é dado pessoal do cliente.
    log_event("EDICAO_REGISTRO_CRITICO", tabela="tarefa", alvo_id=tarefa.id,
              acao="envio_cliente", origem=origem, enviados=enviados,
              falhas=len(resultados) - enviados, concluiu=entregou)
    return {
        "arquivo": nome_arquivo,
        "enviados": enviados,
        "falhas": len(resultados) - enviados,
        "concluiu": entregou,
        "message": (f"{enviados} de {len(resultados)} envio(s) concluído(s)."
                    + (" Tarefa concluída." if entregou
                       else " Nenhum envio funcionou: a tarefa segue aberta.")),
        "resultados": resultados,
    }
