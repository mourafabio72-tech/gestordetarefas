# Deploy — Gestor de Tarefas (padrão Zoaria / EasyPanel)

Guia de deploy do app em `https://gestordetarefas.zoaria.com.br`.

## Arquitetura

- **Backend:** FastAPI + PostgreSQL + JWT (Bearer em localStorage)
- **Frontend:** React/Vite → build estático servido por nginx (proxy `/api` → backend)
- **3 containers** via `docker-compose.yml`: `db` (Postgres) · `backend` · `frontend`
- **Extras:** alertas WhatsApp (Zap Contábil), scheduler (8h/14h/18h), Teams webhook
- **Login:** próprio do app (JWT). Entra no hub `zoaria.com.br` só como card do catálogo
  (módulo `operacional`), **sem** SSO por cookie.

## Repositórios

- Deploy repo: `mourafabio72-tech/gestordetarefas` (branch `main`) → auto-deploy no EasyPanel
- Clone local de trabalho: `_deploy_gestortarefas/` na raiz do vault

Fluxo: editar no clone → `git commit` → `git push origin main` → EasyPanel builda sozinho.

## Passo-a-passo no EasyPanel

Servidor: `2.25.192.225:3000` (mesmo projeto dos outros apps Zoaria).

1. **Create Service → Compose**, conectado ao repo `gestordetarefas`, branch `main`,
   com **auto-deploy (webhook) ligado**.
2. Apontar para o `docker-compose.yml` da raiz.
3. **Volume persistente** `postgres_data` (o banco mora aqui — não pode ser efêmero).
4. **Domínio:** `gestordetarefas.zoaria.com.br` → serviço **frontend**, porta **80**,
   com SSL (Let's Encrypt).

## Variáveis de ambiente

> ⚠️ EasyPanel **descarta** valores que começam com `.` (ponto). Nunca inicie um valor com ponto.

| Variável | Obrigatória | Observação |
|---|---|---|
| `DB_PASSWORD` | sim | senha forte do Postgres |
| `SECRET_KEY` | sim | `openssl rand -hex 32` |
| `ADMIN_EMAIL` | sim | admin inicial (criado só na 1ª subida, se a tabela estiver vazia) |
| `ADMIN_PASSWORD` | sim | senha do admin inicial |
| `ADMIN_NOME` | não | default: `Administrador` |
| `ZAP_API_KEY` | p/ WhatsApp | sem ela, os alertas de WhatsApp não são enviados |
| `ZAP_API_URL` | não | default: `https://api-bps4.zapcontabil.chat` |
| `ZAP_PHONE` | não | default: `5521971985815` |
| `ALERT_DAYS_BEFORE` | não | default: `3` |
| `TEAMS_WEBHOOK_URL` | não | alertas no Teams (opcional) |

`DATABASE_URL` é montada automaticamente pelo compose a partir de `DB_USER`/`DB_PASSWORD`.

## DNS (Hostinger)

Criar registro A: `gestordetarefas` → `2.25.192.225` (igual a `dre`, `conciliacao`, `nfse`).

## Pós-deploy (conferência)

1. Abrir `https://gestordetarefas.zoaria.com.br` → tela de login.
2. Logar com `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
3. Verificar o card **Gestor de Tarefas** no hub (módulo Operacional). Se o hub em
   produção já tiver banco populado, adicionar o card por `/admin/apps`.

## Segurança

- `/api/auth/register` exige usuário autenticado (só o admin cria novos usuários).
- Postgres e backend **não** são expostos à internet (sem `ports` no compose); só o
  frontend (nginx) recebe o domínio.
