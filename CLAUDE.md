# Tareffas (Gestor de Tarefas)

> Antes de TUDO: existe uma vault Obsidian em `/Users/fabiomoura/ObsidianJovi/`
> que é a **fonte da verdade** para regras técnicas, padrões visuais, segurança,
> auth, layout, identidade e copy. Este arquivo não repete essas regras: aponta
> para elas.

## ANTES de qualquer tarefa, OBRIGATÓRIO LER (vault Obsidian)

1. `/Users/fabiomoura/ObsidianJovi/CLAUDE.md` : manual mestre (regras operacionais e BOOT DA VAULT)
2. `/Users/fabiomoura/ObsidianJovi/00A_MAPAS/_MAPA_CHAVES.md` : índice de TODOS os padrões técnicos
3. `/Users/fabiomoura/ObsidianJovi/01_SISTEMAS/07_Regras_de_Ouro/Padroes_do_Vault_na_Integra.md` : cláusula pétrea, padrão do vault se cumpre INTEIRO (citação + checklist + gate + auto-revisão)
4. `/Users/fabiomoura/ObsidianJovi/01_SISTEMAS/07_Regras_de_Ouro/Economia_de_Tokens.md` : cláusula pétrea de tokens
5. `/Users/fabiomoura/ObsidianJovi/01_SISTEMAS/07_Regras_de_Ouro/Cross_Pasta_via_Mapa.md` : organização de links

As duas doutrinas de `00B_DOUTRINAS/` (`Anti_Puxa_Saco`, `Leitura_e_Retencao_de_Notas`)
carregam sempre, não entram por rota.

## Antes de ESCREVER UI / HTML / CSS / JSX, OBRIGATÓRIO LER os padrões aplicáveis

Pelo `_MAPA_CHAVES.md`, identifique e leia ANTES de escrever 1 linha:

| Se envolver... | Leia |
|---|---|
| Menu (sidebar) | `Padrao_Menu_Sidebar` |
| Listagem 4+ linhas | `Padrao_Tabela` + `Padrao_Barra_de_Filtros` |
| Indicadores topo | `Padrao_KPI_Dashboard` |
| Formulário (input + select + botão) | `Padrao_Formulario` |
| Caixa/card | `Padrao_Box_Card` |
| Modal/popup | `Padrao_Modal` + `Sem_Popup_Nativo` |
| Upload | `Padrao_Upload_Arquivo` |
| Toggle | `Padrao_Toggle_OnOff` |
| Importação Excel | `Padrao_Excel_Template_Importacao` |
| Loading | `Sempre_Mostrar_Loading` |
| IA | `Padrao_Marca_IA` + `Sempre_Marcar_IA` |

Se não leu, NÃO escreva HTML. Pergunte qual padrão usar.

**Cumpra o padrão NA ÍNTEGRA, não um resumo dele.** Antes de codar: cite o trecho
da nota (`arquivo:linha`, texto cru), vire cada regra num item de checklist, mostre
e espere o ok (gate), e no fim releia a nota marcando item a item. Cortar um item
em silêncio é BUG, não economia. Vale igual para **segurança e auth** (CSRF,
validação em trust boundary, permissões): nunca opcional.

## Como a vault é carregada nesta máquina

Não existe skill `obsidian-keys` aqui (foi descartada). O carregamento acontece por:

- **`joviano-obsidian`** (plugin instalado em `~/.claude/skills`), config em
  `~/ClaudeCode/ClaudePluginConfig/obsidian-jovi.json`, que aponta o `vault_path`.
- **`genesis-iniciar` / `genesis-continuar`**, que leem o `00_GENESIS/` deste projeto
  e recarregam o LASTRO a cada invocação.

Se nenhuma disparar, leia os 5 arquivos da lista acima na mão.

## 00_GENESIS: o estado do trabalho em curso

`00_GENESIS/` na raiz é o checkpoint deste projeto. Ao retomar qualquer trabalho:
ler `00_GENESIS/LOG.md` **integral** antes de agir, e seguir o `PLANO_FASEADO.md`.
Marcar `CHECKLIST_APLICACAO.md` só com evidência apontável. Regra completa no
`CLAUDE.md` da vault, seção 12.

## Hierarquia de precedência (em conflito, vence quem está mais abaixo)

```
Convenções gerais da vault (01_SISTEMAS/)
        >>>
Quirks deste projeto (descritos NESTE arquivo abaixo)
        >>>
Pedido específico desta sessão
```

## Contexto de negócio

O dono é Fábio Moura, sócio de BPO contábil na BPS4. O workspace com o mapa dos
outros apps do ecossistema Zoaria fica em `/Users/fabiomoura/CLAUDE_FABIO/CLAUDE.md`.
Consulte-o quando o trabalho tocar outro app (Hub, DRE, XmlHub, FinControl).
Ele traz o negócio e o inventário, não os padrões técnicos: estes vivem na vault.

---

# CONVENÇÕES ESPECÍFICAS DESTE PROJETO

## O que é

Gestor de obrigações e tarefas contábeis da BPS4. Uma obrigação é um modelo
recorrente que gera tarefas por competência; o e-validador dá baixa a partir do
documento enviado. Tipo de app: **App Online Auth (single-tenant)**, regime WEB.

- Produção: `https://gestordetarefas.zoaria.com.br`
- Login próprio (JWT de 8 horas), não o SSO do Hub. Decisão firmada.
- Card no Hub Zoaria, módulo operacional.

## Stack

| Camada | O que |
|---|---|
| Backend | FastAPI + SQLAlchemy + Postgres 15, JWT com `python-jose`, senha em `bcrypt` |
| Frontend | React + Vite + Tailwind, servido por nginx que faz proxy de `/api` |
| Agendamento | APScheduler em `services/scheduler.py`, sobe no evento de startup |
| Deploy | EasyPanel via `docker-compose.yml`, auto-deploy por webhook do GitHub |

Rodar local: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000`
e `cd frontend && npm run dev`. O `.bat` não existe aqui: a máquina é macOS.

## Mapa de pastas

```
backend/app/
  main.py          sobe o FastAPI, registra os 15 routers, roda migrate/seed no import
  models.py        11 tabelas (usuarios, empresas, setores, grupos, tarefas,
                   obrigacoes, substituicoes, configuracoes, modelos,
                   empresa_setor_responsavel, empresa_obrigacao_detalhe)
  schemas.py       Pydantic de entrada e saída
  auth.py          JWT, hash de senha e as dependências de permissão
  permissoes.py    a matriz (ver abaixo)
  init_db.py       migrate() idempotente + seed do admin e dos grupos
  database.py      engine e get_db
  routes/          um arquivo por recurso, todos com prefixo /api
  services/        gerador de tarefas, e-validador, importadores, e-mail,
                   whatsapp, scheduler, IA (OpenAI, opcional)
frontend/src/
  pages/           uma página por tela (17)
  components/      Layout.jsx (menu e casca)
  contexts/        AuthContext.jsx (token, usuário logado, permissão efetiva)
  services/api.js  axios com o interceptor do token
  permissoes.js    espelho da matriz do backend, para esconder o que não pode
00_GENESIS/        checkpoint do trabalho em curso
*.md na raiz       specs vivas: PERMISSOES_SPEC, OBRIGACOES_SPEC,
                   NOTIFICACOES_WHATSAPP_EMAIL, DEPLOY
```

O backend valida permissão de verdade. O `permissoes.js` do frontend é só conforto
visual: **nunca** trate a checagem do frontend como controle de acesso.

## Modelo de grupo e overrides

Em `backend/app/permissoes.py`. Duas camadas:

```
permissão efetiva = preset do grupo (tabela `grupos`, com fallback nos PRESETS do código)
                    + overrides do JSON em usuarios.permissoes
```

- **Grupo** é cadastro editável no banco (tabela `grupos`, slug + JSON de permissões
  + ativo). Os `PRESETS` do código são semente e rede de segurança, não a fonte em
  runtime: `carregar_do_banco()` popula o cache no startup e após cada alteração.
- **Grupo não é cargo.** `usuarios.cargo` é texto livre e não interfere em permissão.
- **Overrides** ficam em `usuarios.permissoes` (Text com JSON). `NULL` herda 100% do
  preset. Chave fora de `CHAVES` é ignorada no merge.
- Três tipos de chave: **recursos** com nível graduado (`nenhum` < `ver` < `editar`),
  o **escopo** de tarefas (`proprias` | `setor` | `todas`) e **flags** booleanas de
  ação sensível (`alterar_prazo_legal`, `apagar_anexo`, `alocar_obrigacao`, ...).
- Papel `usuario` é legado (só leitura, vê tudo). Existe para não quebrar contas
  antigas. Não usar em cadastro novo.
- Nas rotas, usar as dependências de `auth.py`: `require_perm(recurso, nivel)`,
  `require_flag(flag)`, `require_admin`. Evitar `require_grupos` em código novo:
  ele checa o nome do papel, não a matriz, e fura o cadastro editável de grupos.
- `bloqueado=True` e `ativo=False` barram o acesso. `ativado=False` é convite de
  primeiro acesso pendente; `NULL` é conta legada, considerada ativa.
- Admin de resgate: o e-mail em `ADMIN_EMAIL` é promovido a admin no startup.

Detalhe da matriz e histórico das ondas: `PERMISSOES_SPEC.md`.

## Variáveis de ambiente

Nenhum segredo no código nem no git. O `.env.example` fica sem valor real.
Atenção: **o EasyPanel descarta variável cujo valor começa com ponto.**

| Grupo | Variáveis |
|---|---|
| Banco | `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`, ou `DATABASE_URL` inteira |
| Sessão | `SECRET_KEY` (assina o JWT de 8 horas) |
| Admin inicial | `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NOME` |
| WhatsApp (Zap Contábil) | `ZAP_API_URL`, `ZAP_API_KEY`, `ZAP_CONNECTION_FROM`, `ZAP_PHONE` |
| E-mail | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_TLS` |
| Alertas | `ALERT_DAYS_BEFORE`, `ALERT_GESTOR_NIVEIS`, `TEAMS_WEBHOOK_URL` |
| Links públicos | `PUBLIC_URL`, `UPLOAD_DIR` |
| IA (opcional) | `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_URL` |
| Frontend (build) | `VITE_HUB_URL` (volta para o Hub; padrão `https://zoaria.com.br`) |

A configuração de notificações também vive no banco (tabela `configuracoes`), com
os segredos mascarados na API. O `.env` é o piso; o banco tem a última palavra
quando a chave existe nos dois lugares.

## Quirks que já custaram tempo

- `redirect_slashes=False` no FastAPI. A rota tem que bater exatamente, com ou sem
  barra final. Chamada com a barra errada devolve 404, não redireciona.
- `Base.metadata.create_all`, `migrate()` e os seeds rodam **no import** de
  `main.py`, antes do app existir. Importar `app.main` em script solto mexe no banco.
- `migrate()` é DDL na mão, idempotente, em `init_db.py`. O `alembic` está no
  `requirements.txt` mas não há migrations no repositório: coluna nova entra no
  `migrate()`, não em revisão do Alembic.
- CORS está em `allow_origins=["*"]` porque em produção o nginx serve tudo na mesma
  origem. Só faz diferença em desenvolvimento.
- `backend/gestor_local.db` é SQLite de teste local. Produção é Postgres.
- Os volumes `uploads` e `pgdata` são persistentes. `UPLOAD_DIR=/app/data/uploads`
  guarda comprovante enviado por cliente: apagar volume perde documento.
