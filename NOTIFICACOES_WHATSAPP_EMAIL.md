# Disparo de mensagens — WhatsApp e E-mail (Tareffas)

Guia completo do sistema de notificações do **Tareffas**: como funciona, como
configurar, as regras de disparo, e **como reimplementar** o mesmo mecanismo em
outro app. Escrito a partir do código real (`backend/app/services/*`).

---

## 1. Visão geral

O app dispara **alertas de tarefas** por dois canais:

- **E-mail** (SMTP) — para colaboradores, gestores, supervisores e clientes.
- **WhatsApp** (API ZapContábil) — para o cliente (empresa).

A cada horário configurado, um **agendador** (APScheduler) varre as tarefas em
aberto, decide **quais** notificar (pela proximidade do prazo) e **quem** recebe
por **qual canal**, e envia. Toda a configuração (servidor SMTP, chave da API,
horários, antecedência) fica **no banco** (tela Configuração → Notificações),
com fallback para variáveis de ambiente. **Nenhum segredo fica no código.**

```
scheduler (cron) ──> check_and_send_alerts(db, slot)
                         │
                         ├─ carrega config (banco/env)
                         ├─ para cada tarefa em aberto e "no prazo de alertar":
                         │     ├─ monta a mensagem (+ link de envio do comprovante)
                         │     ├─ destinatarios_alerta() -> lista {papel, canal, endereço}
                         │     └─ _enviar() -> email.send_email() ou whatsapp.send_whatsapp_message()
                         └─ retorna relatório de despachos
```

### Mapa de arquivos

| Arquivo | Papel |
|---|---|
| `services/config.py` | Config chave-valor (banco + fallback env) + mascaramento de segredos |
| `services/email.py` | `send_email()` — envio SMTP |
| `services/whatsapp.py` | Envio WhatsApp + regras de disparo + destinatários + varredura |
| `services/scheduler.py` | Agendador (cron) que chama a varredura nos horários |
| `services/upload.py` | Link público de envio do comprovante (entra na mensagem) |
| `routes/configuracao.py` | Endpoints da tela (GET/PUT + testar e-mail/WhatsApp) |
| `pages/Notificacoes.jsx` | Tela de configuração (frontend) |

---

## 2. Configuração (banco + env), com segredos mascarados

`services/config.py` centraliza tudo. A regra: **o valor vem do banco**
(tabela `configuracoes`, chave-valor); se não houver, cai no **default**, que
por sua vez lê de **variável de ambiente**.

```python
DEFAULTS = {
    "email_ativo":  "1" if os.getenv("SMTP_HOST") else "0",
    "smtp_host":    os.getenv("SMTP_HOST", ""),
    "smtp_port":    os.getenv("SMTP_PORT", "587"),
    "smtp_user":    os.getenv("SMTP_USER", ""),
    "smtp_pass":    os.getenv("SMTP_PASS", ""),
    "smtp_from":    os.getenv("SMTP_FROM", ""),
    "smtp_tls":     os.getenv("SMTP_TLS", "1"),
    "whatsapp_ativo": "1" if os.getenv("ZAP_API_KEY") else "0",
    "zap_url":      os.getenv("ZAP_API_URL", "https://api-bps4.zapcontabil.chat"),
    "zap_api_key":  os.getenv("ZAP_API_KEY", ""),
    "zap_phone":    os.getenv("ZAP_PHONE", "5521971985815"),
    "zap_connection_from": os.getenv("ZAP_CONNECTION_FROM", "0"),
    "alert_dias_antes":    os.getenv("ALERT_DAYS_BEFORE", "3"),
    "alert_gestor_niveis": os.getenv("ALERT_GESTOR_NIVEIS", "2"),
    "horarios_principal":  "09:30,17:45",
    "horarios_extra":      "14:30,16:00",
    "public_url":   os.getenv("PUBLIC_URL", "https://gestordetarefas.zoaria.com.br"),
}
SEGREDOS = {"smtp_pass", "zap_api_key"}
```

Funções-chave:

- `carregar(db)` → dict com defaults sobrescritos pelo que está no banco.
- `salvar(db, dados)` → grava só as chaves conhecidas; **segredo vazio não
  sobrescreve** (mantém o valor guardado — permite salvar a tela sem redigitar a
  senha).
- `para_api(cfg)` → **mascara segredos** para a tela: devolve `smtp_pass=""` +
  `smtp_pass_set=true/false` (nunca manda a senha de volta ao navegador).
- `ativo(cfg, chave)` → `True` se `"1"`/`"true"`.

### Tabela de chaves

| Chave | Env fallback | O que é |
|---|---|---|
| `email_ativo` | (auto se `SMTP_HOST`) | liga/desliga e-mail |
| `smtp_host` | `SMTP_HOST` | servidor SMTP (ex.: `smtp.office365.com`) |
| `smtp_port` | `SMTP_PORT` (587) | porta |
| `smtp_user` | `SMTP_USER` | usuário/login SMTP |
| `smtp_pass` | `SMTP_PASS` | **segredo** — senha/app password |
| `smtp_from` | `SMTP_FROM` | remetente (From) |
| `smtp_tls` | `SMTP_TLS` (1) | usar STARTTLS |
| `whatsapp_ativo` | (auto se `ZAP_API_KEY`) | liga/desliga WhatsApp |
| `zap_url` | `ZAP_API_URL` | base da API ZapContábil |
| `zap_api_key` | `ZAP_API_KEY` | **segredo** — token Bearer |
| `zap_phone` | `ZAP_PHONE` | número de origem (referência) |
| `zap_connection_from` | `ZAP_CONNECTION_FROM` (0) | id da conexão/instância |
| `alert_dias_antes` | `ALERT_DAYS_BEFORE` (3) | antecedência do 1º aviso |
| `alert_gestor_niveis` | `ALERT_GESTOR_NIVEIS` (2) | níveis da cadeia de gestores |
| `horarios_principal` | — | horários dos avisos principais (CSV `HH:MM`) |
| `horarios_extra` | — | horários extras (só p/ vence hoje/atrasada) |
| `public_url` | `PUBLIC_URL` | base do link de envio de comprovante |

---

## 3. E-mail (SMTP)

`services/email.py` — `send_email(to, subject, body, cfg)`:

- **No-op gracioso**: se `email_ativo` != 1 ou sem `smtp_host`, retorna
  `{"success": False, "skipped": True}` sem estourar erro.
- Abre `smtplib.SMTP(host, port, timeout=30)`, faz `starttls()` se `smtp_tls`,
  `login(user, senha)` se houver usuário, e `send_message()`.
- Retorna `{"success": True}` ou `{"success": False, "error": "..."}`.

```python
with smtplib.SMTP(host, port, timeout=30) as s:
    if usa_tls: s.starttls()
    if user:    s.login(user, senha)
    s.send_message(msg)
```

### Passo a passo — Outlook / Microsoft 365

Na tela **Configuração → Notificações**:

1. **Servidor SMTP:** `smtp.office365.com`
2. **Porta:** `587`
3. **Usuário:** o e-mail completo (ex.: `voce@bps4.com.br`)
4. **Senha:** uma **senha de app** (App Password) — não a senha normal se a
   conta tem MFA. Gere em *Segurança da conta Microsoft → Senhas de app*.
5. **Remetente (From):** o mesmo e-mail do usuário.
6. **TLS:** marcado (STARTTLS na 587).
7. **Ativar e-mail** → **Salvar**.
8. **Testar** enviando para você — confira inclusive o spam.

> Se a organização bloquear **SMTP AUTH**, um admin precisa habilitar
> "Authenticated SMTP" para a caixa, ou usar um relay/servidor dedicado.

---

## 4. WhatsApp (API ZapContábil)

`services/whatsapp.py` — `send_whatsapp_message(phone, message, cfg)`:

```python
url = cfg.get("zap_url") or "https://api-bps4.zapcontabil.chat"
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
payload = {"body": message, "connectionFrom": int(cfg.get("zap_connection_from") or 0)}
POST  {url}/api/send/{phone}   (timeout 30s)
```

- **No-op gracioso** se `whatsapp_ativo` != 1 ou sem `zap_api_key`.
- `phone` deve ir **só com dígitos**, formato `55DDDNUMERO`
  (a rota de teste já remove máscara).
- Sucesso = HTTP 200.

Na tela: **URL da API**, **API Key** (Bearer), **número de origem**,
`connectionFrom` (id da conexão) → **Ativar** → **Salvar** → **Testar**.

---

## 5. Regras de disparo (quando avisa)

`should_notify(days_remaining, slot, dias_antes)` decide se uma tarefa entra no
disparo daquele horário. O **prazo interno** (`data_prazo`) comanda; se não
houver, cai no `data_vencimento`.

| Situação (dias até o prazo) | Horários que disparam |
|---|---|
| Faltam `dias_antes` (padrão 3) ou **1 dia** | só os **principais** |
| **Vence hoje** (0) | **todos** (principais + extras) |
| **Atrasada** (< 0) | **todos** |
| Demais dias | não dispara |

```python
def should_notify(days_remaining, slot, dias_antes=3):
    if days_remaining is None: return False
    if days_remaining <= 0: return True                       # hoje/atrasada -> todos
    if slot == "principal" and days_remaining in (1, dias_antes): return True
    return False
```

- **slot `principal`** = horários de `horarios_principal`.
- **slot `extra`** = horários de `horarios_extra` (só pegam o que já venceu/hoje).
- Isso evita spam: avisa com antecedência 1x/2x ao dia, e "aperta" só quando
  vence ou atrasa.

---

## 6. Quem recebe e por qual canal

`destinatarios_alerta(tarefa, subs_map, niveis)` monta a lista de destinos:

- **Responsáveis** (M2M) → **e-mail**. Se o responsável está de férias/doença
  (`subs_map`), o **substituto** recebe no lugar (papel `substituto`).
- **Cadeia de gestores** de cada responsável → **e-mail**, subindo `niveis`
  (padrão 2): gestor direto, gestor-do-gestor… (`_cadeia_gestores`). Evita
  loop com um `seen`.
- **Supervisor** da tarefa → **e-mail**.
- **Cliente = a Empresa** da tarefa:
  - `empresa.telefone` → **WhatsApp**
  - `empresa.email` → **e-mail**

Cada destino é um dict: `{"papel", "nome", "canal": "email"|"whatsapp", "endereco"}`.
E-mails duplicados são deduplicados (`vistos`).

```python
_enviar(canal, endereco, assunto, mensagem, cfg):
    whatsapp -> send_whatsapp_message(endereco, mensagem, cfg)
    email    -> send_email(endereco, assunto, _texto_simples(mensagem), cfg)
```

> `_texto_simples()` remove os `*` (negrito do WhatsApp) para o corpo do e-mail.

### Exclusões (bloqueio)

A varredura ignora tarefas cuja **empresa** ou **responsável principal** estão
**bloqueados**:

```python
.filter(Tarefa.status.in_([PENDENTE, EM_ANDAMENTO]),
        ~Tarefa.empresa.has(Empresa.bloqueado == True),
        ~Tarefa.responsavel.has(Usuario.bloqueado == True))
```

---

## 7. Formato da mensagem + link de comprovante

`format_task_message(tarefa, days_remaining, responsavel)` monta o texto com
marcação de WhatsApp (`*negrito*`), incluindo urgência, empresa, setor, prazo
interno, vencimento (com aviso de multa), responsável (+ gestor), prioridade.

Antes de despachar, a varredura **anexa o link público de envio do
comprovante** (ver `services/upload.py`):

```python
message = format_task_message(tarefa, days_remaining, responsavel)
try:
    from .upload import link_publico
    message += f"\n\n📎 Enviar o comprovante: {link_publico(cfg, tarefa, db)}"
except Exception:
    pass
assunto = f"[Tareffas] {tarefa.titulo} — {tarefa.empresa.razao_social}"
```

O cliente clica no link (`{public_url}/enviar/{token}`), sobe o arquivo, e a
**tarefa baixa sozinha** (o token identifica a tarefa — não depende do matcher).

---

## 8. Agendador (scheduler)

`services/scheduler.py` usa **APScheduler** (`AsyncIOScheduler`) com timezone
`America/Sao_Paulo`.

- `start_scheduler()` (chamado no `main.py`, no startup):
  - cria um job por horário de `horarios_principal` e `horarios_extra`
    (ids `alerta_<slot>_<HHMM>`), cada um chamando `scheduled_check(slot)`;
  - cria `gerar_mensal` — gera as tarefas do mês **todo dia 1 às 06:00**.
- `reconfigurar_alertas(db)` — **reagenda** os jobs com os horários atuais.
  É chamado pelo `PUT /configuracao/notificacoes` **ao salvar**, então mudar os
  horários na tela vale na hora, sem reiniciar o serviço.
- `scheduled_check(slot)` abre uma sessão, chama `check_and_send_alerts(db, slot)`
  e loga quantas tarefas foram notificadas.

```python
def _agendar_alertas(cfg):
    # remove jobs "alerta_*" e recria a partir dos horários do config
    for slot in ("principal", "extra"):
        for hh, mm in _parse_horarios(cfg.get(f"horarios_{slot}", "")):
            scheduler.add_job(scheduled_check, _cron(hh, mm), args=[slot],
                              id=f"alerta_{slot}_{hh:02d}{mm:02d}", replace_existing=True)
```

---

## 9. Endpoints (tela de Notificações)

`routes/configuracao.py` (todos exigem **admin**):

| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/configuracao/notificacoes` | devolve config **mascarada** (`para_api`) |
| PUT | `/api/configuracao/notificacoes` | salva + `reconfigurar_alertas` |
| POST | `/api/configuracao/notificacoes/testar-email` | envia e-mail de teste para `{para}` |
| POST | `/api/configuracao/notificacoes/testar-whatsapp` | envia WhatsApp de teste para `{para}` |

O teste usa a config **salva** (`carregar(db)`), então salve antes de testar.

---

## 10. Como testar

1. Preencher SMTP → **Ativar** → **Salvar** → **Testar e-mail** para você.
2. Preencher ZAP → **Ativar** → **Salvar** → **Testar WhatsApp** (`55DDDNUMERO`).
3. Fim-a-fim: crie uma tarefa com `data_prazo` a `dias_antes`, 1 dia, hoje ou
   atrasada, e espere o horário — ou chame `check_and_send_alerts(db, "principal")`
   manualmente num shell para forçar a varredura.

> **Cuidado ao testar SMTP com host inválido + e-mail ativo:** o `starttls`/
> `login` pode travar até o timeout (30s). Teste com dados reais ou desative o
> e-mail enquanto valida outra coisa.

---

## 11. Segurança (regras duras)

- **Segredos nunca no código nem no Git.** `smtp_pass` e `zap_api_key` só via
  tela (gravados no banco) ou env. `para_api` nunca devolve o segredo ao front.
- **Não commitar** o banco local (`*.db` no `.gitignore`).
- Em produção (EasyPanel), setar as env como fallback é opcional — o recomendado
  é configurar pela tela (config é **por banco**; não migra de dev → prod).
- O **link público** de comprovante usa token aleatório (`secrets.token_urlsafe`),
  escopo de uma tarefa só, e recusa empresa bloqueada.

---

## 12. Receita para reimplementar em outro app

Passo a passo mínimo para levar esse disparo a outro projeto (FastAPI + SQLAlchemy):

1. **Dependências:** `apscheduler`, `httpx` (WhatsApp), `smtplib` (stdlib).
2. **Config chave-valor:** tabela `configuracoes(chave, valor)` + um módulo
   `config.py` com `DEFAULTS` (lendo env), `carregar/salvar/para_api/ativo` e um
   set `SEGREDOS` para mascarar. **Não** devolver segredo ao front; **não**
   sobrescrever segredo com valor vazio.
3. **E-mail:** copiar `send_email(to, subject, body, cfg)` — no-op se inativo,
   STARTTLS + login condicional.
4. **WhatsApp:** copiar `send_whatsapp_message(phone, message, cfg)` — POST
   `"{zap_url}/api/send/{phone}"` com Bearer e `connectionFrom`. Ajustar ao
   provedor se não for ZapContábil (o contrato muda pouco: URL + token + body).
5. **Regras + destinatários:** adaptar `should_notify` (proximidade do prazo) e
   `destinatarios_alerta` (quem/qual canal) ao seu modelo de dados. Deduplicar
   e-mails; excluir bloqueados.
6. **Varredura:** `check_and_send_alerts(db, slot)` — carrega config, filtra
   tarefas abertas, monta mensagem, itera destinatários, chama `_enviar`.
7. **Scheduler:** APScheduler com um job por horário (CronTrigger + timezone),
   `start_scheduler()` no startup e `reconfigurar_alertas()` chamado ao salvar a
   config, para os horários valerem sem reiniciar.
8. **Endpoints + tela:** GET/PUT da config (com máscara) + `testar-email` e
   `testar-whatsapp`.
9. **Segurança:** segredos só via env/banco, nunca no código; `.gitignore`
   cobrindo banco local e `.env`.

### Ordem de chamada (resumo)

```
main.py (startup)
  └─ start_scheduler()                 # cria jobs a partir da config
        └─ scheduled_check(slot)       # em cada horário
              └─ check_and_send_alerts(db, slot)
                    ├─ config.carregar(db)
                    ├─ mapa_substitutos(db)          # férias/doença
                    ├─ query tarefas abertas (exclui bloqueados)
                    └─ para cada tarefa "no prazo de alertar":
                          ├─ format_task_message(...) + link_publico(...)
                          ├─ destinatarios_alerta(tarefa, subs_map, niveis)
                          └─ _enviar(canal, endereco, assunto, msg, cfg)
                                ├─ email.send_email(...)
                                └─ whatsapp.send_whatsapp_message(...)
PUT /configuracao/notificacoes
  └─ config.salvar(db, body)
  └─ scheduler.reconfigurar_alertas(db)   # horários valem na hora
```

---

*Gerado a partir do código do Tareffas (`backend/app/services/config.py`,
`email.py`, `whatsapp.py`, `scheduler.py`, `upload.py`,
`routes/configuracao.py`).*
