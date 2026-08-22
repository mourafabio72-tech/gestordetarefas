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


def montar_payload_zap(mensagem: str, conn_from: int = 0, user_id=None) -> dict:
    """Corpo do POST /api/send. Em função à parte para ser provado sem rede.

    Duas coisas andam juntas quando o aviso é para alguém do escritório:

    `userId` faz o atendimento nascer na conta daquele atendente e em aberto.
    Vai como INTEIRO -- o swagger declara `User.id` como string e o `userId` do
    SendMessage como integer, e mandar "12" onde se espera 12 é o tipo de
    incompatibilidade que a API recusa, ou pior, aceita e ignora.

    `ticketStrategy: "create"` abre um atendimento novo a cada aviso. Sem ele o
    Zap reaproveita o atendimento que já existe para aquele contato -- e como
    todo o escritório recebe na MESMA linha, os avisos do time inteiro caíam num
    fio só, com o `userId` de cada envio reatribuindo o fio para a próxima
    pessoa. No fim da varredura o atendimento inteiro ficava na conta de quem
    foi o último, e ninguém achava o seu.

    Para o cliente não vai nenhum dos dois: ele tem contato próprio, e criar
    atendimento novo a cada aviso picotaria a conversa dele em pedaços.
    """
    payload = {"body": mensagem, "connectionFrom": conn_from}
    if user_id not in (None, ""):
        try:
            payload["userId"] = int(user_id)
        except (TypeError, ValueError):
            payload["userId"] = user_id
        payload["ticketStrategy"] = "create"
    return payload


async def send_whatsapp_message(phone: str, message: str, cfg: dict, user_id=None) -> dict:
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
    payload = montar_payload_zap(message, conn_from, user_id)
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{url}/api/send/{numero}", json=payload, headers=headers, timeout=30.0)
        return {"success": response.status_code == 200, "status_code": response.status_code, "response": response.text}


# ── ZapContábil: quem é quem lá dentro ───────────────────────────────────────
#
# Dois cadastros distintos, e a diferença importa:
#   Contact = quem RECEBE mensagem. Tem `number` e `email`.
#   User    = quem ATENDE. Tem `email`, NÃO tem telefone.
#
# Por isso o número sai dos contatos, e dos usuários vem só o `id` — que serve
# para o `userId` do envio, o campo que faz o atendimento nascer na conta do
# colaborador certo. É ele que responde "como o Zap sabe que este aviso é do
# Fulano" quando a linha é uma só para o escritório inteiro.
#
# O e-mail liga os três cadastros (Tareffas, Contact e User) porque é o login
# da pessoa em todos eles.

PAGINA_ZAP = 100          # teto documentado por página
MAX_PAGINAS_ZAP = 20      # trava de segurança: 2000 registros bastam e sobram


async def _zap_paginado(cfg: dict, caminho: str, chave: str) -> list:
    """Percorre um endpoint paginado do Zap e devolve todos os registros.

    Lista vazia em qualquer contratempo — canal desligado, sem chave, API fora,
    resposta estranha. É de propósito: esta consulta enriquece o alerta, não o
    autoriza. Se ela cair, o disparo segue pelo telefone do cadastro local ou
    pelo e-mail, em vez de a varredura inteira morrer.

    Paginar não é zelo: o padrão do Zap é 20 registros por página, e sem isto o
    escritório do 21º colaborador em diante cairia no e-mail sem ninguém notar.
    """
    api_key = (cfg.get("zap_api_key") or "").strip()
    if not cfgmod.ativo(cfg, "whatsapp_ativo") or not api_key:
        return []
    url = cfg.get("zap_url") or "https://api-bps4.zapcontabil.chat"
    headers = {"Authorization": f"Bearer {api_key}", "accept": "application/json"}
    saida, pagina = [], 1
    try:
        async with httpx.AsyncClient() as client:
            while pagina <= MAX_PAGINAS_ZAP:
                r = await client.get(f"{url}{caminho}", headers=headers, timeout=20.0,
                                     params={"page": pagina, "pageSize": PAGINA_ZAP})
                if r.status_code != 200:
                    break
                dados = r.json()
                if not isinstance(dados, dict):
                    return dados if isinstance(dados, list) else saida
                lote = dados.get(chave) or []
                saida.extend(x for x in lote if isinstance(x, dict))
                total = dados.get("pageCount") or 1
                if pagina >= int(total) or not lote:
                    break
                pagina += 1
    except Exception:
        return saida
    return saida


async def contatos_zap(cfg: dict) -> list:
    """`GET /api/contacts` — quem pode receber mensagem, com número e e-mail."""
    return await _zap_paginado(cfg, "/api/contacts", "contacts")


async def usuarios_zap(cfg: dict) -> list:
    """`GET /api/users` — os atendentes. Daqui sai o `id`, não o telefone."""
    return await _zap_paginado(cfg, "/api/users", "users")


def _email(registro: dict) -> str:
    return str((registro or {}).get("email") or "").strip().lower()


def mapa_numero_por_email(contatos: list) -> dict:
    """{e-mail: número} a partir dos contatos do Zap.

    Contato bloqueado fica de fora: mandar para ele é erro garantido.
    Separado da chamada HTTP para poder ser provado sem rede.
    """
    saida = {}
    for c in contatos or []:
        if not isinstance(c, dict) or c.get("blocked"):
            continue
        email, numero = _email(c), normalizar_telefone(c.get("number"))
        if email and numero:
            saida[email] = numero
    return saida


def mapa_userid_por_email(usuarios: list) -> dict:
    """{e-mail: id do atendente} — o `userId` que direciona o atendimento.

    Usuário desabilitado fica de fora: atribuir a ele esconderia o aviso numa
    conta que ninguém abre.
    """
    saida = {}
    for u in usuarios or []:
        if not isinstance(u, dict) or u.get("enabled") is False:
            continue
        email, ident = _email(u), u.get("id")
        if not email or ident in (None, ""):
            continue
        # O swagger devolve o id como string; o envio quer inteiro. Converte já
        # aqui, para o mapa guardar o tipo que a API de envio espera.
        try:
            ident = int(ident)
        except (TypeError, ValueError):
            pass
        saida[email] = ident
    return saida


async def carregar_zap(cfg: dict) -> dict:
    """Tudo que a varredura precisa do Zap, numa consulta só.

    `linha` é o número único do escritório. É para lá que vai o aviso do time:
    o colaborador não tem WhatsApp próprio cadastrado no Zap, ele tem um LOGIN
    (o e-mail). Quem separa um aviso do outro é o `userId`, que faz o
    atendimento nascer na conta da pessoa.
    """
    return {"linha": normalizar_telefone(cfg.get("zap_phone")),
            "numero": mapa_numero_por_email(await contatos_zap(cfg)),
            "user_id": mapa_userid_por_email(await usuarios_zap(cfg))}


def _base_date(tarefa: Tarefa):
    """O prazo interno comanda os alertas; se não houver, cai no vencimento."""
    return tarefa.data_prazo or tarefa.data_vencimento


# As três faixas de urgência. Cada uma é um disparo próprio, com horários
# próprios, e rende uma mensagem própria — assim a cobrança do atrasado não
# precisa acontecer na mesma cadência do que vence hoje.
FAIXAS = ("a_vencer", "vence_hoje", "atrasada")

TITULO_FAIXA = {
    "a_vencer": ("📋", "a vencer"),
    "vence_hoje": ("⚠️", "vencem hoje", "vence hoje"),
    "atrasada": ("🚨", "atrasadas", "atrasada"),
}


def faixa_da_tarefa(dias_restantes, dias_antes: int = 3) -> str:
    """Em que faixa esta tarefa cai hoje — ou None, se ainda não é hora.

    A tarefa anda sozinha entre as faixas conforme o dia passa: hoje está em
    "a vencer", amanhã em "vence hoje", depois em "atrasada". Ninguém precisa
    reclassificar nada.

    "A vencer" são DOIS TOQUES, não uma contagem regressiva: o dia da
    antecedência e a véspera. Com antecedência 3, avisa faltando 3 e faltando 1,
    e cala no 2 -- dois lembretes espaçados em vez de um martelo diário. Uma
    tarefa que vence em 40 dias não é aviso, é ruído.

    E conta do PRAZO INTERNO, não do vencimento legal: de nada adianta avisar
    três dias antes do prazo da Receita se o time precisava ter terminado uma
    semana antes. Quem chama esta função já resolveu isso em `_base_date`.
    """
    if dias_restantes is None:
        return None
    if dias_restantes < 0:
        return "atrasada"
    if dias_restantes == 0:
        return "vence_hoje"
    if dias_restantes == 1 or dias_restantes == dias_antes:
        return "a_vencer"
    return None


def should_notify(days_remaining, faixa: str, dias_antes: int = 3) -> bool:
    """A tarefa entra no disparo desta faixa?"""
    return faixa_da_tarefa(days_remaining, dias_antes) == faixa


def urgencia(dias: int) -> str:
    """A primeira linha do aviso: o quanto isso corre."""
    if dias is None:
        return "📋 Sem prazo definido"
    if dias < 0:
        return f"🚨 *ATRASADA há {abs(dias)} dia(s)!*"
    if dias == 0:
        return "⚠️ *PRAZO INTERNO VENCE HOJE!*"
    if dias == 1:
        return "⏰ *Prazo interno vence amanhã!*"
    return f"📋 Prazo interno em *{dias} dias*"


def urgencia_curta(dias: int) -> tuple:
    """(ícone, frase) para uma linha de lista, sem gritar."""
    if dias is None:
        return ("📋", "sem prazo")
    if dias < 0:
        n = abs(dias)
        return ("🚨", f"atrasada há {n} dia" + ("s" if n > 1 else ""))
    if dias == 0:
        return ("⚠️", "vence hoje")
    if dias == 1:
        return ("⏰", "vence amanhã")
    return ("📋", f"faltam {dias} dias")


def folego_ate_vencer(venc_dias, venc_data=None) -> str:
    """Quanto ainda há entre o atraso interno e o prazo legal.

    Só faz sentido para tarefa atrasada no PRAZO INTERNO: "atrasada há 3 dias"
    soa igual quer o vencimento legal seja amanhã ou daqui a duas semanas, e
    não é a mesma coisa -- um caso é correr, o outro é multa a caminho. A frase
    diz de qual dos dois se trata.

    Devolve "" quando não há o que dizer, para o bloco não ganhar linha vazia.
    """
    if venc_dias is None:
        return ""
    data = f" ({venc_data})" if venc_data else ""
    if venc_dias > 1:
        return f"⏳ ainda dá: vence em {venc_dias} dias{data}"
    if venc_dias == 1:
        return f"⏳ atenção: vence amanhã{data}"
    if venc_dias == 0:
        return f"❗ o vencimento é HOJE{data}"
    n = abs(venc_dias)
    return f"❗ vencimento passou há {n} dia" + ("s" if n > 1 else "") + data


LIMITE_RESUMO = 3200   # WhatsApp corta perto de 4096; sobra folga para o rodapé


def montar_resumo(nome: str, itens: list, limite: int = LIMITE_RESUMO,
                  faixa: str = None) -> str:
    """Uma mensagem com TODAS as tarefas daquela pessoa naquela varredura.

    Antes saía um aviso por tarefa. Numa varredura de mês fechado isso é uma
    rajada de dezenas de mensagens para a mesma pessoa, quatro vezes por dia --
    e o efeito de uma rajada é a pessoa parar de ler. Uma mensagem com a lista
    ordenada por urgência é o mesmo conteúdo em algo que se lê.

    Ordena pelo que corre mais: o atrasado no topo, o folgado no fim. Empate de
    prazo desempata pelo nome da empresa, para a lista sair estável entre
    varreduras e a pessoa reconhecer o que já viu.

    Corta pelo TAMANHO, não pela quantidade: o WhatsApp trunca perto de 4096
    caracteres, e uma mensagem cortada no meio perderia justamente os links de
    comprovante do fim. O que não coube vira uma linha dizendo quantas faltam.
    """
    ordenados = sorted(itens or [], key=lambda i: (i.get("dias") if i.get("dias") is not None else 9999,
                                                   (i.get("empresa") or "")))
    total = len(ordenados)
    if not total:
        return ""
    # O cabeçalho diz de que faixa é a leva. Quem recebe sabe, na primeira
    # linha, se é planejamento, se é para hoje, ou se é cobrança.
    marca = TITULO_FAIXA.get(faixa)
    if marca:
        icone = marca[0]
        rotulo = marca[1] if total > 1 else marca[-1]
        plural = "tarefas" if total > 1 else "tarefa"
        cabeca = f"👤 *{nome}*\n{icone} *{total} {plural} {rotulo}*\n"
    else:
        plural = "tarefas pedindo atenção" if total > 1 else "tarefa pedindo atenção"
        cabeca = f"👤 *{nome}*\n📌 *{total} {plural}*\n"
    partes, usados, mostradas = [], len(cabeca), 0
    for i in ordenados:
        icone, frase = urgencia_curta(i.get("dias"))
        bloco = f"\n{icone} *{i.get('titulo')}*"
        if i.get("empresa"):
            bloco += f" · {i['empresa']}"
        bloco += f"\n{frase}"
        if i.get("prazo"):
            bloco += f" · prazo {i['prazo']}"
        if i.get("multa"):
            bloco += " · ⚠️ gera multa"
        # Só para o que já estourou o prazo interno: nas outras faixas a data
        # legal ainda não é a pergunta, e a linha só encheria a lista.
        if (i.get("dias") is not None) and i["dias"] < 0:
            folego = folego_ate_vencer(i.get("venc_dias"), i.get("venc_data"))
            if folego:
                bloco += f"\n{folego}"
        if i.get("link"):
            bloco += f"\n📎 {i['link']}"
        bloco += "\n"
        if usados + len(bloco) > limite and mostradas:
            break
        partes.append(bloco)
        usados += len(bloco)
        mostradas += 1
    corpo = "".join(partes)
    if mostradas < total:
        faltam = total - mostradas
        corpo += f"\n…e mais {faltam} tarefa" + ("s" if faltam > 1 else "") + ". Veja a lista no Tareffas.\n"
    return cabeca + corpo


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

    urgency = urgencia(days_remaining)

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


def eh_cliente(u) -> bool:
    """O usuário é do lado do cliente, não do escritório.

    Olha `tipo` e `grupo`: o campo canônico é `tipo` ("colaborador"|"cliente"),
    mas grupo é cadastro editável e nada impede alguém criar um grupo chamado
    "cliente" e usar só ele. Aceitar os dois evita que um cliente cadastrado
    pela outra convenção seja tratado como gente da casa.
    """
    for campo in ("tipo", "grupo"):
        if str(getattr(u, campo, "") or "").strip().lower() == "cliente":
            return True
    return False


def _numero_da_pessoa(u, zap: dict = None) -> str:
    """Número de WhatsApp da pessoa, na ordem em que se deve confiar.

    Primeiro o que está nos CONTATOS do ZapContábil, achado pelo e-mail: é lá
    que o cadastro vive e é mantido, e casar por e-mail evita ficar com duas
    verdades sobre o mesmo contato. Depois o telefone digitado aqui, para quem
    ainda não está lá.
    """
    email = str(getattr(u, "email", None) or "").strip().lower()
    numeros = (zap or {}).get("numero") or {}
    if email and numeros.get(email):
        return numeros[email]
    return normalizar_telefone(getattr(u, "telefone", None))


def canais_da_pessoa(u, zap: dict = None) -> list:
    """Por onde avisar esta pessoa: lista de (canal, endereço, id do atendente).

    GENTE DO ESCRITÓRIO não tem WhatsApp próprio no Zap — tem um login, que é o
    e-mail. A mensagem vai para a linha única do escritório levando o `userId`
    daquele login, e o atendimento nasce na conta da pessoa. O e-mail dela não
    é endereço de entrega aqui, é a chave que encontra o login.

    Sem login no Zap não há como direcionar, e mandar para a linha comum sem
    atribuição só encheria o balaio: nesse caso vale o número que o cadastro
    tiver e, faltando ele, o e-mail — deixar de avisar quem tem a tarefa na mão
    é falha pior do que avisar pelo canal errado.

    USUÁRIO DO LADO DO CLIENTE é outra coisa: ele tem WhatsApp próprio e recebe
    nele, mais o e-mail. Está fora do escritório, não abre o painel, e não tem
    supervisor para servir de rede se o aviso se perder.

    Quem não tem por onde ser avisado fica de fora, e isso aparece no ensaio.
    """
    email = getattr(u, "email", None)
    chave = str(email or "").strip().lower()
    numero = _numero_da_pessoa(u, zap)

    if eh_cliente(u):
        vias = []
        if numero:
            vias.append(("whatsapp", numero, None))
        if email:
            vias.append(("email", email, None))
        return vias

    linha = (zap or {}).get("linha")
    uid = ((zap or {}).get("user_id") or {}).get(chave)
    if linha and uid not in (None, ""):
        return [("whatsapp", linha, uid)]
    # Sem a linha, mas com número próprio: vale mandar para lá, e a atribuição
    # ao atendente continua valendo se ele existir -- o ticket cai na conta
    # dele, seja qual for o número por onde a mensagem entrou.
    if numero:
        return [("whatsapp", numero, uid or None)]
    if email:
        return [("email", email, None)]
    return []


def destinatarios_alerta(tarefa: Tarefa, subs_map: dict = None, niveis: int = 0,
                        zap: dict = None, incluir_cliente: bool = False) -> list:
    """Quem recebe o alerta e por qual canal.

    O alerta é acompanhamento de tarefa: vai para quem executa e para quem
    supervisiona, que é o par que a tarefa já tem gravado. Por isso o padrão é
    responsável (ou substituto) + supervisor, e nada além disso.

    Os dois alargamentos ficam desligados por padrão, cada um pela sua razão:
    - `niveis` sobe a cadeia de gestores acima do responsável. Zero porque
      cobrança em cópia para a diretoria é decisão de gestão, não default.
    - `incluir_cliente` avisa a EMPRESA da tarefa por e-mail e/ou WhatsApp.
      Desligado porque ligado sem querer manda mensagem para cliente real. Não
      confundir com o usuário do tipo cliente: esse é pessoa, entra como
      responsável da tarefa e recebe sempre, pelos dois canais.

    Canal: WhatsApp, no número que o ZapContábil tem para aquele e-mail; e-mail
    só como reserva de quem não tem número em lugar nenhum.

    `subs_map` {ausente_id: substituto}: quem está de férias/doença é trocado
    pelo substituto (e o gestor do ausente continua na cópia, quando ligada).
    """
    subs_map = subs_map or {}
    dest = []
    vistos = set()

    def juntar(papel, pessoa):
        if not pessoa:
            return
        cliente = eh_cliente(pessoa)
        for canal, endereco, uid in canais_da_pessoa(pessoa, zap):
            # A chave inclui o atendente, não só o endereço. Todo o escritório
            # recebe no MESMO número (a linha única), e uma chave só de endereço
            # colapsaria responsável e supervisor numa mensagem — dois avisos que
            # precisam cair em duas contas diferentes.
            marca = f"{canal}:{endereco}:{uid or ''}"
            if not endereco or marca in vistos:
                continue
            vistos.add(marca)
            item = {"papel": "cliente" if cliente else papel, "nome": pessoa.nome,
                    "canal": canal, "endereco": endereco}
            if uid not in (None, ""):
                item["zap_user_id"] = uid
            dest.append(item)

    for u in list(tarefa.responsaveis):
        alvo = subs_map.get(u.id, u)  # ausente -> substituto recebe no lugar
        juntar("substituto" if alvo and alvo.id != u.id else "colaborador", alvo)
        for g in _cadeia_gestores(u, niveis):
            juntar("gestor", g)
    juntar("supervisor", tarefa.supervisor)

    empresa = tarefa.empresa if incluir_cliente else None
    if empresa:
        tel = normalizar_telefone(empresa.telefone)
        if tel and f"whatsapp:{tel}:" not in vistos:
            vistos.add(f"whatsapp:{tel}:")
            dest.append({"papel": "empresa", "nome": empresa.razao_social,
                         "canal": "whatsapp", "endereco": tel})
        if empresa.email and f"email:{empresa.email}:" not in vistos:
            vistos.add(f"email:{empresa.email}:")
            dest.append({"papel": "empresa", "nome": empresa.razao_social,
                         "canal": "email", "endereco": empresa.email})
    return dest


async def _enviar(canal: str, endereco: str, assunto: str, mensagem: str, cfg: dict,
                  zap_user_id=None) -> dict:
    if canal == "whatsapp":
        return await send_whatsapp_message(endereco, mensagem, cfg, user_id=zap_user_id)
    if canal == "email":
        return send_email(endereco, assunto, _texto_simples(mensagem), cfg)
    return {"success": False, "error": f"canal desconhecido: {canal}"}


async def check_and_send_alerts(db: Session, faixa: str = "vence_hoje", ensaio: bool = False) -> dict:
    """Varre as tarefas em aberto e avisa quem precisa saber.

    Roda uma FAIXA por vez -- a vencer, vence hoje ou atrasada --, porque cada
    uma tem seus horários. A tarefa anda sozinha entre elas conforme o dia passa.

    Devolve {"tarefas": [...], "mensagens": [...]}. São contagens diferentes de
    propósito: uma varredura de mês fechado pode ter 400 tarefas na régua e
    mandar 40 mensagens, porque cada pessoa recebe UMA com a lista dela. Antes
    era um aviso por tarefa, o que numa rajada faz a pessoa parar de ler.

    Com `ensaio=True` percorre a mesma lógica -- as mesmas tarefas, a mesma
    régua, os mesmos destinatários, a mesma mensagem -- e não envia. Existe
    porque o alerta de verdade pode sair para o cliente: sem o ensaio, conferir
    a régua em produção significaria mandar mensagem para cliente real.
    """
    from .substituicao import mapa_substitutos
    cfg = cfgmod.carregar(db)
    try:
        dias_antes = int(cfg.get("alert_dias_antes") or 3)
    except (TypeError, ValueError):
        dias_antes = 3
    try:
        niveis = int(cfg.get("alert_gestor_niveis") or 0)
    except (TypeError, ValueError):
        niveis = 0
    incluir_cliente = cfgmod.ativo(cfg, "alert_cliente")

    now = datetime.now()
    subs_map = mapa_substitutos(db)
    # Uma consulta por varredura, não uma por destinatário.
    zap = await carregar_zap(cfg)

    # Bloqueados somem dos alertas também (empresa ou responsável principal bloqueado).
    tarefas = (db.query(Tarefa)
               .filter(Tarefa.status.in_([StatusTarefa.PENDENTE, StatusTarefa.EM_ANDAMENTO]),
                       ~Tarefa.empresa.has(Empresa.bloqueado == True),
                       ~Tarefa.responsavel.has(Usuario.bloqueado == True))
               .all())

    na_regua = []       # o que o ensaio mostra, tarefa a tarefa
    caixas = {}         # marca do destinatário -> {dest, itens}

    for tarefa in tarefas:
        base = _base_date(tarefa)
        if not base:
            continue
        dias = (base.date() - now.date()).days
        if faixa_da_tarefa(dias, dias_antes) != faixa:
            continue

        link = None
        try:
            from .upload import link_publico
            link = link_publico(cfg, tarefa, db)
        except Exception:
            pass

        empresa_nome = tarefa.empresa.razao_social if tarefa.empresa else None
        item = {"titulo": tarefa.titulo, "empresa": empresa_nome, "dias": dias,
                "prazo": base.strftime("%d/%m"), "multa": bool(tarefa.gera_multa),
                "link": link}
        # Fôlego até o prazo legal. Só quando o interno é que comandou o alerta:
        # se a tarefa não tem prazo interno, `base` JÁ é o vencimento, e repetir
        # a mesma contagem com outro nome confundiria em vez de informar.
        if tarefa.data_prazo and tarefa.data_vencimento:
            item["venc_dias"] = (tarefa.data_vencimento.date() - now.date()).days
            item["venc_data"] = tarefa.data_vencimento.strftime("%d/%m")

        despachos = []
        for d in destinatarios_alerta(tarefa, subs_map, niveis, zap, incluir_cliente):
            marca = f"{d['canal']}:{d['endereco']}:{d.get('zap_user_id') or ''}"
            caixas.setdefault(marca, {"dest": d, "itens": []})["itens"].append(item)
            despachos.append(d)

        na_regua.append({
            "tarefa_id": tarefa.id,
            "tarefa_titulo": tarefa.titulo,
            "empresa": empresa_nome,
            "responsavel": (tarefa.responsaveis[0].nome if tarefa.responsaveis else None),
            "dias_restantes": dias,
            "despachos": despachos,
        })

    mensagens = []
    for caixa in caixas.values():
        d = caixa["dest"]
        texto = montar_resumo(d["nome"], caixa["itens"], faixa=faixa)
        quantas = len(caixa["itens"])
        marca = TITULO_FAIXA.get(faixa)
        rotulo = (marca[1] if quantas > 1 else marca[-1]) if marca else "pedindo atenção"
        assunto = f"[Tareffas] {quantas} tarefa" + ("s" if quantas > 1 else "") + f" {rotulo}"
        registro = {**d, "tarefas": quantas}
        if ensaio:
            registro.update({"enviado": False, "skipped": False, "ensaio": True, "mensagem": texto})
        else:
            r = await _enviar(d["canal"], d["endereco"], assunto, texto, cfg, d.get("zap_user_id"))
            registro.update({"enviado": r.get("success", False),
                             "skipped": r.get("skipped", False), "detalhe": r})
        mensagens.append(registro)

    return {"tarefas": na_regua, "mensagens": mensagens}
