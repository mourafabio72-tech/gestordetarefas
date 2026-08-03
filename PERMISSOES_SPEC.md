# Spec — Matriz de Permissões (JSON) do Gestor de Tarefas

> Origem: comparação com o cadastro de usuário/permissões do **Acessórias**.
> Objetivo: substituir o modelo atual de 3 papéis "tudo-ou-nada" por uma
> **matriz granular por recurso + escopo + flags de ação**, mantendo os papéis
> como **presets**.
>
> **Status: Onda 1 (backend) + F2 IMPLEMENTADOS e testados** (A1–A3, chaves
> B1–B7, escopo C1, flags D1–D6, enforcement E1–E5, e a tela de admin da matriz
> F2). Falta só **F1** (esconder botões conforme permissão). Módulo e-validador
> em si é projeto à parte.
>
> F2: página `frontend/src/pages/Grupos.jsx` (modal da matriz por usuário) +
> `frontend/src/permissoes.js` (espelho dos presets — MANTER EM SINCRONIA com
> `app/permissoes.py`). Salva só os overrides (diferenças do preset); `{}` limpa.
>
> Arquivos: `app/permissoes.py` (presets+resolução), `app/auth.py`
> (`require_perm`/`require_flag`/`permissao_efetiva`), migração em
> `app/init_db.py` (coluna `usuarios.permissoes`), guardas aplicadas em
> `routes/{empresas,setores,tarefas,usuarios,auth}.py`.
> `GET /api/auth/me` agora devolve `permissoes_efetivas` (usado pelo frontend).

## 1. Modelo atual (antes)
- `usuarios.grupo` = `admin | gestor | usuario` (coluna String).
- Guarda única: `require_gestor_ou_admin` protege escrita em empresas, setores,
  tarefas, usuários. `usuario` só lê.
- `usuarios.gestor_id` = hierarquia (quem é o superior).
- **Faltam:** escopo "ver só as minhas", permissão graduada por recurso,
  flags de ação sensível.

## 2. Modelo novo (depois)
Mantém `grupo` como **preset**. Adiciona coluna `usuarios.permissoes` (JSON/Text)
que, quando presente, **sobrescreve** o preset ponto a ponto. Usuário sem JSON
herda 100% do preset do papel.

### 2.1 Recursos (nível graduado)
Cada recurso aceita: `nenhum` | `ver` | `editar` (editar inclui criar/excluir).

| Chave | Recurso | Rota |
|---|---|---|
| `empresas`   | Cadastro de empresas        | `/empresas` |
| `setores`    | Setores / departamentos     | `/setores` |
| `tarefas`    | Tarefas / processos         | `/tarefas` |
| `obrigacoes` | Templates (tarefa-modelo)   | `/tarefas` (data_prazo nulo) |
| `usuarios`   | Cadastro de usuários        | `/usuarios` |
| `relatorios` | Relatórios / dashboard      | (agregações) |
| `evalidador` | e-validador (docs)          | *planejado* |

### 2.2 Escopo da tarefa (só para `tarefas`)
`escopo_tarefas`: `proprias` | `setor` | `todas`
- `proprias` = só onde `responsavel_id == user.id`
- `setor` = tarefas dos setores sob responsabilidade do usuário (via `gestor_id`/setor)
- `todas` = sem filtro

### 2.3 Flags de ação (boolean, independentes do papel)
| Chave | Ação sensível | Campo Acessórias equivalente |
|---|---|---|
| `alterar_prazo_legal`   | mexer em `data_vencimento` | "Pode alterar prazos técnicos/legais?" |
| `alterar_prazo_tecnico` | mexer em `data_prazo`      | idem |
| `dispensar_demanda`     | cancelar/dispensar tarefa  | "Pode dispensar demandas na Lista de Entregas?" |
| `apagar_anexo`          | excluir arquivo anexado    | "Pode apagar anexos (arquivos)?" |
| `alocar_obrigacao`      | alocar template em empresa | "Cadastro de Obrigações [2]" |
| `disparar_emails`       | disparar e-mails agendados | "Cadastro de departamentos [1]" |

## 3. Presets por papel
> `analista` e `consulta` são novos presets derivados de `usuario`.

| Chave | admin | gestor | analista | consulta |
|---|---|---|---|---|
| empresas   | editar | editar | ver     | ver |
| setores    | editar | editar | ver     | ver |
| tarefas    | editar | editar | editar  | ver |
| obrigacoes | editar | editar | nenhum  | ver |
| usuarios   | editar | ver    | nenhum  | nenhum |
| relatorios | editar | ver    | ver     | ver |
| evalidador | editar | editar | ver     | nenhum |
| **escopo_tarefas** | todas | todas | **proprias** | todas |
| alterar_prazo_legal   | ✔ | ✔ | ✘ | ✘ |
| alterar_prazo_tecnico | ✔ | ✔ | ✔ | ✘ |
| dispensar_demanda     | ✔ | ✔ | ✘ | ✘ |
| apagar_anexo          | ✔ | ✘ | ✘ | ✘ |
| alocar_obrigacao      | ✔ | ✔ | ✘ | ✘ |
| disparar_emails       | ✔ | ✔ | ✔ | ✘ |

## 4. Formato do JSON (`usuarios.permissoes`)
Exemplo — Andreia (Analista) igual ao print do Acessórias, mas liberando
edição de empresa (que ela tem lá como "Sim"):
```json
{
  "empresas": "editar",
  "setores": "ver",
  "tarefas": "editar",
  "obrigacoes": "editar",
  "usuarios": "nenhum",
  "relatorios": "ver",
  "escopo_tarefas": "proprias",
  "alterar_prazo_legal": false,
  "alterar_prazo_tecnico": false,
  "dispensar_demanda": true,
  "apagar_anexo": false,
  "alocar_obrigacao": true,
  "disparar_emails": true
}
```
Regra de resolução: `permissao_efetiva = merge(preset[grupo], permissoes_json)`.
JSON ausente ⇒ usa o preset puro do papel.

## 5. Pontos de aplicação (enforcement)
- **Backend `auth.py`:** nova dependência `require_perm(recurso, nivel)` e
  `require_flag(flag)` que leem a permissão efetiva do usuário logado.
  `require_gestor_ou_admin` continua válido nas rotas que não precisam de granularidade.
- **`routes/tarefas.py`:** aplicar `escopo_tarefas` no `GET /tarefas`
  (filtro por `responsavel_id`/setor); checar `alterar_prazo_*`, `dispensar_demanda`
  no `PUT`; `apagar_anexo` na exclusão de anexo.
- **`routes/empresas.py` / `setores.py`:** trocar guarda por `require_perm("empresas","editar")` etc.
- **`routes/usuarios.py`:** só quem tem `usuarios: editar` define grupo/permissões.
- **Frontend:** esconder/reabilitar botões conforme a permissão efetiva
  (endpoint `GET /auth/me` já devolve o usuário; incluir a permissão resolvida).

## 6. Migração de dados
- Adicionar coluna `permissoes TEXT NULL` em `usuarios` (idempotente, via `init_db.migrate()`).
- Usuários existentes: `permissoes = NULL` ⇒ herdam preset do papel atual → **zero quebra**.
- Opcional: renomear papel `usuario` → oferecer `analista`/`consulta` como presets.

## 7. Fora de escopo (campos do Acessórias que NÃO migram)
Regimes e Grupos de obrigações, Config. Sistema/e-Contínuo, APLA,
Salários e Honorários, Área VIP e App, Comunicados, Certificado digital.
