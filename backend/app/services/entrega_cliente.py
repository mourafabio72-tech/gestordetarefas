"""Entrega do documento de SAÍDA ao cliente.

Saiu da rota `POST /tarefas/{id}/enviar-cliente` em 2026-09-19, quando o
e-validador passou a enviar a guia que reconhece. As duas portas chamam esta
função, e a regra que importa fica escrita uma vez: a tarefa só conclui se
ALGUÉM recebeu.
"""
import html as html_mod
import os
import secrets
from datetime import datetime

from ..models import StatusTarefa, TarefaEnvio
from ..seguranca import log_event


_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
          "agosto", "setembro", "outubro", "novembro", "dezembro"]
_LOGO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo-bps4-email.png")
_COR = "#2da3a1"   # verde-água do logo; e-mail não lê os tokens do app


def _logo() -> bytes:
    try:
        with open(_LOGO, "rb") as f:
            return f.read()
    except OSError:
        return b""


def _competencia_por_extenso(comp: str) -> str:
    """"08/2026" vira "agosto/2026"; o que não se reconhece passa como veio."""
    try:
        mes, ano = (comp or "").split("/")
        return f"{_MESES[int(mes) - 1]}/{ano}"
    except (ValueError, IndexError):
        return comp or ""


def montar_mensagem(tarefa, empresa: str, link: str) -> dict:
    """Assunto, texto e HTML da guia para o cliente (texto aprovado em 2026-09-21).

    O nome da guia é o Mininome da obrigação, quando preenchido: o nome técnico
    ("das_simples") é para a equipe, e o cliente lia exatamente ele. O texto
    serve ao e-mail e ao WhatsApp; o HTML só ao e-mail, com o logo embutido.
    """
    obr = tarefa.obrigacao
    nome = ((obr.mininome or "").strip() or obr.nome) if obr else tarefa.titulo
    comp = _competencia_por_extenso(tarefa.competencia)
    venc = tarefa.data_vencimento.strftime("%d/%m/%Y") if tarefa.data_vencimento else None

    assunto = f"BPS4 | {nome}, {comp}, {empresa}" if comp else f"BPS4 | {nome}, {empresa}"
    linhas = [f"Olá, {empresa}.", "",
              f"Sua guia {nome}" + (f" da competência {comp}" if comp else "") + " está disponível."]
    if venc:
        linhas.append(f"Vencimento: {venc}.")
    linhas += ["", f"Baixar a guia: {link}", "",
               "O link é exclusivo desta mensagem. Qualquer dúvida, é só responder.", "",
               "BPS4 Contabilidade"]
    texto = "\n".join(linhas)

    e = html_mod.escape
    venc_html = f'<p style="margin:0 0 20px">Vencimento: <strong>{e(venc)}</strong>.</p>' if venc else ""
    comp_html = f" da competência <strong>{e(comp)}</strong>" if comp else ""
    html = f"""<!doctype html><html><body style="margin:0;background:#f6f3ec">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f3ec;padding:24px 0">
<tr><td align="center">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:10px;font-family:Arial,Helvetica,sans-serif;color:#2f3a2f">
<tr><td style="padding:28px 32px 8px"><img src="cid:logo-bps4" width="120" alt="BPS4" style="display:block;border:0"></td></tr>
<tr><td style="padding:8px 32px 28px;font-size:15px;line-height:1.55">
<p style="margin:0 0 16px">Olá, {e(empresa)}.</p>
<p style="margin:0 0 8px">Sua guia <strong>{e(nome)}</strong>{comp_html} está disponível.</p>
{venc_html}
<p style="margin:0 0 24px"><a href="{e(link)}" style="display:inline-block;background:{_COR};color:#ffffff;text-decoration:none;font-weight:bold;padding:12px 22px;border-radius:6px">Baixar a guia</a></p>
<p style="margin:0 0 4px;font-size:13px;color:#6b7266">O link é exclusivo desta mensagem. Qualquer dúvida, é só responder.</p>
<p style="margin:16px 0 0;font-size:13px;color:#6b7266">BPS4 Contabilidade</p>
</td></tr></table></td></tr></table></body></html>"""
    return {"assunto": assunto, "texto": texto, "html": html}


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
    logo = _logo()
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
        msg = montar_mensagem(tarefa, empresa, link)

        # Exceção de rede de UM destinatário não derruba os outros nem apaga o
        # que já saiu (achado de 2026-09-19): antes, o WhatsApp levantando
        # depois de o e-mail ter saído desfazia a transação, o envio real
        # sumia do banco e um reenvio duplicava a mensagem ao cliente.
        try:
            if d["canal"] == "whatsapp":
                # Link, não arquivo: é o que se pode rastrear, e ainda dispensa o
                # provedor aceitar o anexo.
                r = await send_whatsapp_message(d["endereco"], msg["texto"], cfg)
            else:
                # SÓ o link, sem anexo (decisão de 2026-09-21): o anexo sai do
                # servidor do e-mail e o Tareffas nunca sabe se o cliente pegou.
                r = send_email(d["endereco"], msg["assunto"], msg["texto"], cfg,
                               html=msg["html"],
                               imagens=[("logo-bps4", logo)] if logo else None)
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
