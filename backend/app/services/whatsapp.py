import httpx
import re
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Tarefa, Usuario, Empresa, StatusTarefa
from .email import send_email
from . import config as cfgmod


def normalizar_telefone(valor) -> str:
    """Telefone do cadastro -> número que a API aceita. "" se não der para usar.

    O campo é texto livre e chega como "(21) 99999-9999", "21 99999 9999" ou já
    com o país. Sem esta passagem o envio falharia em silêncio, que é o pior
    modo de falhar num alerta: ninguém recebe e ninguém fica sabendo.

    DDD sem país (10 ou 11 dígitos) ganha o 55. Número que não chega a 12
    dígitos nem passa de 15 é lixo de cadastro e volta vazio, para o
    destinatário simplesmente não entrar na lista.
    """
    d = "".join(ch for ch in str(valor or "") if ch.isdigit())
    if d.startswith("00"):
        d = d[2:]
    if len(d) in (10, 11):
        d = "55" + d
    return d if 12 <= len(d) <= 15 else ""


async def send_whatsapp_message(phone: str, message: str, cfg: dict) -> dict:
    if not cfgmod.ativo(cfg, "whatsapp_ativo"):
        return {"success": False, "error": "WhatsApp desativado", "skipped": True}
    api_key = (cfg.get("zap_api_key") or "").strip()
    if not api_key:
        return {"success": False, "error": "ZAP_API_KEY não configurada", "skipped": True}
    url = cfg.get("zap_url") or "https://api-bps4.zapcontabil.chat"
    try:
        conn_from = int(cfg.get("zap_connection_from") or 0)
    except (TypeError, ValueError):
        conn_from = 0
    numero = normalizar_telefone(phone)
    if not numero:
        return {"success": False, "error": f"telefone inválido: {phone!r}"}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"body": message, "connectionFrom": conn_from}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{url}/api/send/{numero}", json=payload, headers=headers, timeout=30.0)
        return {"success": response.status_code == 200, "status_code": response.status_code, "response": response.text}


# O schema `User` do ZapContábil não está documentado campo a campo, e o nome do
# telefone varia entre instalações. Em vez de fixar um palpite, tentamos os
# candidatos em ordem — o primeiro que virar número válido vence.
CAMPOS_NUMERO_ZAP = ("number", "whatsapp", "whatsappNumber", "phone", "phoneNumber",
                     "celular", "telefone", "contactNumber", "wa_number", "mobile")


async def usuarios_zap(cfg: dict) -> list:
    """`GET /api/users` do ZapContábil — os colaboradores cadastrados lá.

    Devolve lista vazia em qualquer contratempo (canal desligado, sem chave, API
    fora do ar, resposta estranha). É de propósito: esta consulta enriquece o
    alerta, não o autoriza. Se ela falhar, o disparo segue pelo telefone do
    cadastro do Tareffas ou pelo e-mail, em vez de a varredura inteira morrer.
    """
    api_key = (cfg.get("zap_api_key") or "").strip()
    if not cfgmod.ativo(cfg, "whatsapp_ativo") or not api_key:
        return []
    url = cfg.get("zap_url") or "https://api-bps4.zapcontabil.chat"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{url}/api/users",
                                 headers={"Authorization": f"Bearer {api_key}",
                                          "accept": "application/json"}, timeout=20.0)
        if r.status_code != 200:
            return []
        dados = r.json()
    except Exception:
        return []
    # A resposta pode vir como lista pura ou embrulhada — `UserList` no swagger.
    if isinstance(dados, dict):
        for chave in ("users", "data", "rows", "items", "records"):
            if isinstance(dados.get(chave), list):
                return dados[chave]
        return []
    return dados if isinstance(dados, list) else []


def numero_do_usuario_zap(u: dict) -> str:
    """Primeiro campo do usuário do Zap que vira telefone utilizável."""
    if not isinstance(u, dict):
        return ""
    for campo in CAMPOS_NUMERO_ZAP:
        numero = normalizar_telefone(u.get(campo))
        if numero:
            return numero
    return ""


def mapa_por_email(usuarios: list) -> dict:
    """{e-mail em minúsculas: número} a partir da lista de usuários do Zap.

    O e-mail é a chave porque é o login do colaborador lá e o mesmo que ele tem
    aqui — é o que liga um cadastro ao outro sem obrigar a redigitar telefone.
    Separado da chamada HTTP para poder ser provado sem rede.
    """
    saida = {}
    for u in usuarios or []:
        if not isinstance(u, dict):
            continue
        email = str(u.get("email") or "").strip().lower()
        numero = numero_do_usuario_zap(u)
        if email and numero:
            saida[email] = numero
    return saida


async def mapa_zap_por_email(cfg: dict) -> dict:
    return mapa_por_email(await usuarios_zap(cfg))


def _base_date(tarefa: Tarefa):
    """O prazo interno comanda os alertas; se não houver, cai no vencimento."""
    return tarefa.data_prazo or tarefa.data_vencimento


def should_notify(days_remaining: int, slot: str, dias_antes: int = 3) -> bool:
    """Regras de disparo por proximidade do prazo interno.
    slot 'principal' = horários principais ; slot 'extra' = extras.
      - `dias_antes` e 1 dia antes  -> só nos horários principais
      - no dia do prazo e atrasada  -> em todos os horários
    """
    if days_remaining is None:
        return False
    if days_remaining <= 0:  # vence hoje ou já atrasada -> todos os horários
        return True
    if slot == "principal" and days_remaining in (1, dias_antes):
        return True
    return False


def format_task_message(tarefa: Tarefa, days_remaining: int, responsavel: Usuario = None,
                       para: str = None) -> str:
    """Monta o texto do alerta.

    `para` põe o nome do destinatário na PRIMEIRA linha. Vale quando a mensagem
    cai num painel compartilhado -- caso do ZapContábil, em que a linha é uma só
    para o escritório inteiro: sem o nome no topo, quem abre o painel vê uma
    pilha de avisos e não sabe qual é o seu. O nome do responsável continua no
    corpo, que é outra informação: quem responde pela tarefa, não quem está
    sendo avisado (o gestor recebe o aviso de uma tarefa que não é dele).
    """
    empresa_nome = tarefa.empresa.razao_social or tarefa.empresa.nome_fantasia
    setor_nome = tarefa.setor.nome if tarefa.setor else "Não definido"

    if days_remaining < 0:
        urgency = f"🚨 *ATRASADA há {abs(days_remaining)} dia(s)!*"
    elif days_remaining == 0:
        urgency = "⚠️ *PRAZO INTERNO VENCE HOJE!*"
    elif days_remaining == 1:
        urgency = "⏰ *Prazo interno vence amanhã!*"
    else:
        urgency = f"📋 Prazo interno em *{days_remaining} dias*"

    base = _base_date(tarefa)
    prazo_str = base.strftime("%d/%m/%Y %H:%M") if base else "-"

    linhas = []
    if para:
        linhas += [f"👤 *{para}*"]
    linhas += [
        urgency, "",
        f"*Tarefa:* {tarefa.titulo}",
        f"*Empresa:* {empresa_nome}",
        f"*Setor:* {setor_nome}",
        f"*Prazo interno:* {prazo_str}",
    ]
    if tarefa.data_vencimento:
        multa = " ⚠️ *GERA MULTA*" if tarefa.gera_multa else ""
        linhas.append(f"*Vencimento:* {tarefa.data_vencimento.strftime('%d/%m/%Y')}{multa}")
    if responsavel:
        linha = f"*Responsável:* {responsavel.nome}"
        if responsavel.gestor:
            linha += f"  (gestor: {responsavel.gestor.nome})"
        linhas.append(linha)
    linhas.append(f"*Prioridade:* {tarefa.prioridade.value.upper()}")
    linhas += ["", "Por favor, verifique e atualize o status desta tarefa."]
    return "\n".join(linhas)


def _texto_simples(msg: str) -> str:
    """Versão sem marcação de WhatsApp (asteriscos) para corpo de e-mail."""
    return re.sub(r"\*", "", msg)


def _cadeia_gestores(usuario, niveis: int) -> list:
    """Sobe a cadeia de gestores (gestor, gestor-do-gestor, ...) até `niveis`."""
    chain, seen, atual = [], {usuario.id}, usuario.gestor
    while atual and niveis > 0 and atual.id not in seen:
        chain.append(atual)
        seen.add(atual.id)
        atual = atual.gestor
        niveis -= 1
    return chain


def _canal_da_pessoa(u, zap_por_email: dict = None) -> tuple:
    """Canal de quem é do escritório: WhatsApp, com e-mail de reserva.

    A ordem tem uma razão em cada degrau:

    1. o número que está no ZapContábil, achado pelo e-mail. É lá que o cadastro
       do colaborador vive e é mantido; casar por e-mail evita redigitar
       telefone aqui e ficar com duas verdades sobre o mesmo contato.
    2. o telefone do cadastro do Tareffas, para quem ainda não está no Zap.
    3. o e-mail. Não é a regra, é a rede: deixar de avisar quem tem a tarefa na
       mão é falha pior do que avisar pelo canal errado.

    Quem não tem nada disso fica de fora, e isso aparece no ensaio.
    """
    email = getattr(u, "email", None)
    if zap_por_email and email:
        numero = zap_por_email.get(str(email).strip().lower())
        if numero:
            return ("whatsapp", numero)
    tel = normalizar_telefone(getattr(u, "telefone", None))
    if tel:
        return ("whatsapp", tel)
    if email:
        return ("email", email)
    return (None, None)


def destinatarios_alerta(tarefa: Tarefa, subs_map: dict = None, niveis: int = 2,
                        zap_por_email: dict = None) -> list:
    """Quem recebe o alerta e por qual canal:
    - gente do escritório (responsáveis, a cadeia de gestores deles, supervisor)
      -> WhatsApp, no número que o ZapContábil tem para aquele e-mail; e-mail só
      como reserva de quem não tem número em lugar nenhum
    - cliente (a empresa da tarefa) -> e-mail e/ou WhatsApp, conforme o que
      estiver preenchido no cadastro dela
    `subs_map` {ausente_id: substituto}: quem está de férias/doença é trocado pelo substituto
    (mas o gestor do ausente continua na cópia).
    """
    subs_map = subs_map or {}
    dest = []
    vistos = set()

    def juntar(papel, pessoa):
        if not pessoa:
            return
        canal, endereco = _canal_da_pessoa(pessoa, zap_por_email)
        # A chave é o endereço: a mesma pessoa em dois papéis (responsável e
        # supervisor, por exemplo) recebe uma mensagem só.
        if not endereco or endereco in vistos:
            return
        vistos.add(endereco)
        dest.append({"papel": papel, "nome": pessoa.nome, "canal": canal, "endereco": endereco})

    for u in list(tarefa.responsaveis):
        alvo = subs_map.get(u.id, u)  # ausente -> substituto recebe no lugar
        juntar("substituto" if alvo and alvo.id != u.id else "colaborador", alvo)
        for g in _cadeia_gestores(u, niveis):
            juntar("gestor", g)
    juntar("supervisor", tarefa.supervisor)

    empresa = tarefa.empresa
    if empresa:
        tel = normalizar_telefone(empresa.telefone)
        if tel and tel not in vistos:
            vistos.add(tel)
            dest.append({"papel": "cliente", "nome": empresa.razao_social,
                         "canal": "whatsapp", "endereco": tel})
        if empresa.email and empresa.email not in vistos:
            vistos.add(empresa.email)
            dest.append({"papel": "cliente", "nome": empresa.razao_social,
                         "canal": "email", "endereco": empresa.email})
    return dest


async def _enviar(canal: str, endereco: str, assunto: str, mensagem: str, cfg: dict) -> dict:
    if canal == "whatsapp":
        return await send_whatsapp_message(endereco, mensagem, cfg)
    if canal == "email":
        return send_email(endereco, assunto, _texto_simples(mensagem), cfg)
    return {"success": False, "error": f"canal desconhecido: {canal}"}


async def check_and_send_alerts(db: Session, slot: str = "principal", ensaio: bool = False) -> list:
    """Varre tarefas em aberto (excluindo bloqueadas) e dispara alertas por canal.

    Com `ensaio=True` percorre exatamente a mesma lógica -- as mesmas tarefas, a
    mesma régua de proximidade, os mesmos destinatários, a mesma mensagem -- mas
    NÃO envia nada. Existe porque o alerta de verdade sai para o WhatsApp e o
    e-mail do CLIENTE: sem o ensaio, conferir a régua em produção significaria
    disparar mensagem para cliente real. O ensaio devolve também o texto montado,
    para revisar a mensagem antes de ela sair.
    """
    from .substituicao import mapa_substitutos
    cfg = cfgmod.carregar(db)
    try:
        dias_antes = int(cfg.get("alert_dias_antes") or 3)
    except (TypeError, ValueError):
        dias_antes = 3
    try:
        niveis = int(cfg.get("alert_gestor_niveis") or 2)
    except (TypeError, ValueError):
        niveis = 2

    alerts_sent = []
    now = datetime.now()
    subs_map = mapa_substitutos(db)
    # Uma consulta por varredura, não uma por destinatário.
    zap_por_email = await mapa_zap_por_email(cfg)

    # Bloqueados somem dos alertas também (empresa ou responsável principal bloqueado).
    tarefas = (db.query(Tarefa)
               .filter(Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO]),
                       ~Tarefa.empresa.has(Empresa.bloqueado == True),
                       ~Tarefa.responsavel.has(Usuario.bloqueado == True))
               .all())

    for tarefa in tarefas:
        base = _base_date(tarefa)
        if not base:
            continue
        days_remaining = (base.date() - now.date()).days
        if not should_notify(days_remaining, slot, dias_antes):
            continue

        responsavel = None
        if tarefa.responsavel_id:
            responsavel = db.query(Usuario).filter(Usuario.id == tarefa.responsavel_id).first()

        rodape = ""
        try:
            from .upload import link_publico
            rodape = f"\n\n📎 Enviar o comprovante: {link_publico(cfg, tarefa, db)}"
        except Exception:
            pass
        assunto = f"[Tareffas] {tarefa.titulo} - {tarefa.empresa.razao_social}"
        # Guardado para o ensaio mostrar o texto-base sem repetir por destinatário.
        message = format_task_message(tarefa, days_remaining, responsavel) + rodape

        despachos = []
        for d in destinatarios_alerta(tarefa, subs_map, niveis, zap_por_email):
            # O nome de quem está sendo avisado abre a mensagem. No painel
            # compartilhado é o que separa o aviso do Fulano do da Ciclana.
            texto = format_task_message(tarefa, days_remaining, responsavel, para=d["nome"]) + rodape
            if ensaio:
                despachos.append({**d, "enviado": False, "skipped": False, "ensaio": True})
                continue
            r = await _enviar(d["canal"], d["endereco"], assunto, texto, cfg)
            despachos.append({**d, "enviado": r.get("success", False),
                              "skipped": r.get("skipped", False), "detalhe": r})

        item = {
            "tarefa_id": tarefa.id,
            "tarefa_titulo": tarefa.titulo,
            "empresa": tarefa.empresa.razao_social if tarefa.empresa else None,
            "responsavel": responsavel.nome if responsavel else None,
            "dias_restantes": days_remaining,
            "despachos": despachos,
        }
        if ensaio:
            item["assunto"] = assunto
            item["mensagem"] = message
        alerts_sent.append(item)

    return alerts_sent
