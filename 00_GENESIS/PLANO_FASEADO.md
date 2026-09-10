# Plano faseado: os eventos que faltam na tabela da nota

modo=autonomo (escolhido em 2026-09-09, mantido)
plano aprovado em 2026-09-09, sem ajustes

As fases 1 a 22 estão fechadas e arquivadas nos três checkpoints desta pasta.
A numeração continua de lá.

O gatilho declarado para este trabalho era o levantamento de quais eventos já
existem, e ele está feito antes de qualquer proposta de código: está no LOG,
na entrada `fase=23 acao=levantamento` de 2026-09-09.

## O que o levantamento achou, em uma tabela

| Evento da nota | Estado hoje | Vai virar código? |
|---|---|---|
| `LOGIN_OK` | `routes/auth.py:69` | não, já existe |
| `LOGIN_FALHA` | existe como `LOGIN_RECUSADO`, 2 pontos | não, ver escada no LASTRO |
| `LOGIN_BLOQUEADO` | `routes/auth.py:42` e `SSO_BLOQUEADO` em `:151` | não, já existe |
| `EDICAO_REGISTRO_CRITICO` | 3 pontos | sim, um deles está com o nome errado |
| `EXCLUSAO_REGISTRO_CRITICO` | 1 ponto | sim, está com o nome errado |
| `CSRF_INVALIDO` | não se aplica, `routes/auth.py:137` explica | não |
| `RATE_LIMIT_HIT` | já existe com outro nome e outro escopo | não |
| `LOGOUT` | **ausente** | fase 23 |
| `ACESSO_NEGADO_403` | **ausente**, 14 pontos de 403 | fase 23 |
| `ACESSO_NEGADO_IDOR` | **ausente** | fase 23 |
| `MUDANCA_ROLE` | **ausente** | fase 23 |
| `CRIACAO_REGISTRO_CRITICO` | **ausente** | fase 24 |
| `EXPORT_DADOS` | **ausente** | fase 24 |

## Fase 23: autorização e sessão passam a deixar rastro

- **Status:** done (2026-09-09)
- **Duração estimada:** 1 sessão curta
- **Notas que regem:** `Padrao_Logging_Estruturado`, `Padrao_IDOR` (seção
  "Auditoria"), `Principios`, `Escada_Preguica_de_Codigo`,
  `TDD_RED_GREEN_REFACTOR`, `Sem_Travessao`
- **Dependências:** nenhuma. O contexto de log das fases 18 a 20 já entrega os
  oito campos, então nenhum evento novo precisa passar `user_id`, `ip`, `path`
  nem `request_id` a mão.
- **Output esperado:** quem tentou o que não podia deixa linha, e quem saiu
  deixa linha.

Os quatro eventos, com o ponto exato onde cada um nasce:

**`ACESSO_NEGADO_403`**, nas três guardas de `app/auth.py`: `require_grupos`
(`:63`), `require_perm` (`:82`) e `require_flag` (`:94`). É o degrau 2 da
escada em estado puro: os quatorze pontos de 403 do app passam por essas três,
e nenhuma rota é tocada. A linha leva o motivo da recusa como campo extra
(grupo exigido, ou recurso e nível, ou flag), que é o que transforma o evento
em algo acionável.

**`ACESSO_NEGADO_IDOR`**, e aqui o escopo é menor do que parece, medido e não
estimado: o app tem 52 pontos de 404, mas quase todos são "não existe". IDOR de
verdade só existe onde há escopo por usuário, e isso é `_aplicar_escopo`, usado
em 8 lugares, dos quais **apenas 2 buscam um recurso único por id**
(`routes/tarefas.py:351` e `:373`). Os outros 6 são listagem, e listagem
filtrada não é tentativa.

A condição da nota custa uma consulta, e isso está declarado em vez de
escondido: só é tentativa quando o recurso EXISTE e não é do usuário. Hoje o
SELECT com escopo devolve vazio nos dois casos. O desenho é um helper em
`routes/tarefas.py` que, ao não achar dentro do escopo, pergunta uma vez se o
id existe fora dele; se existir, emite o evento com `recurso` e `recurso_id`
como manda o exemplo da nota, e levanta o mesmo 404 de sempre. **A resposta ao
cliente não muda em nada**, e isso é item de prova, não promessa.

**`MUDANCA_ROLE`**, em `routes/usuarios.py:252-256`, o bloco que troca `grupo`
e `permissoes` de outro usuário. Hoje não deixa rastro nenhum, e é o buraco
mais sério dos seis: é a pergunta que uma auditoria faz primeiro. A linha leva
o alvo, o papel de antes e o papel de depois. **O valor anterior tem de ser
lido antes da atribuição**, senão o log grava o novo duas vezes, que é o erro
clássico deste evento.

**`LOGOUT`**, em rota nova `POST /api/auth/logout`, decisão 1 do usuário. Emite
o evento e devolve 200. Não invalida token, e o docstring diz isso com todas as
letras para ninguém ler a rota como revogação. O frontend chama em
`contexts/AuthContext.jsx:88`, antes de apagar o token, e **ignora falha**: se
a chamada quebrar, o usuário sai do mesmo jeito. Log não pode prender ninguém
dentro do sistema.

**Critério de aceite, verificável por quem não escreveu:**
`python backend/provas/prova_eventos_log.py` sai com código 0, e com código 1
no código de hoje. Entre os itens, obrigatoriamente: um 403 de cada uma das
três guardas emite `ACESSO_NEGADO_403` com o motivo, e o corpo da resposta 403
continua idêntico ao de hoje; buscar tarefa de outro usuário emite
`ACESSO_NEGADO_IDOR` com `recurso` e `recurso_id`, e buscar id inexistente
**não emite nada**, os dois devolvendo 404 com o mesmo corpo; trocar o grupo de
um usuário emite `MUDANCA_ROLE` com o papel anterior diferente do novo; o
logout emite `LOGOUT` com o `user_id` de quem saiu; e toda linha nova sai com
os oito campos da nota. A suíte inteira de `backend/provas` continua em exit 0.

## Fase 24: registro crítico para de mentir, e o export deixa rastro

- **Status:** done (2026-09-09)
- **Duração estimada:** 1 sessão curta
- **Notas que regem:** `Padrao_Logging_Estruturado` (a tabela de eventos e o
  anti-padrão do `event` não padronizado), `Escada_Preguica_de_Codigo`,
  `TDD_RED_GREEN_REFACTOR`, `Sem_Travessao`
- **Dependências:** fase 23, só para não misturar diff de autorização com diff
  de cadastro. Tecnicamente são independentes.
- **Output esperado:** criar e apagar cadastro crítico deixa linha com o nome
  certo, e o relatório de massa deixa linha.

**Primeiro o conserto, e ele vem antes do acréscimo:** os dois eventos de
registro crítico estão trocados no código de hoje.
`routes/tarefas.py:804` **cria** uma `ObrigacaoExcecao` (`db.add`,
`acao="criada"`) e emite `EXCLUSAO_REGISTRO_CRITICO`. `routes/obrigacoes.py:63`
**apaga** a exceção (`db.delete`, `acao="removida"`) e emite
`EDICAO_REGISTRO_CRITICO`. Não muda comportamento nenhum, e por isso nenhuma
prova pegou: o que quebra é o filtro, que é a única razão de o nome ser
padronizado. Quem procurar exclusão acha uma criação, e a exclusão de verdade
não aparece em busca nenhuma de exclusão.

`DOCUMENTO_EXCLUIDO` (`routes/tarefas.py:433`) vira
`EXCLUSAO_REGISTRO_CRITICO` com `tabela="tarefa_anexo"`, pelo mesmo motivo: a
nota lista "linha de log sem `event` padronizado" como anti-padrão. O nome
antigo vira campo, não some.

**Depois o acréscimo**, no escopo que a decisão 3 do usuário fixou. São quatro
tabelas, e não as 64 rotas de mutação do app:

| Onde | Rotas | Evento |
|---|---|---|
| `routes/usuarios.py` | `POST ""` (`:180`), `DELETE /{id}` (`:284`) | criação e exclusão |
| `routes/empresas.py` | `POST ""` (`:265`), `DELETE /{id}` (`:332`) | criação e exclusão |
| `routes/obrigacoes.py` | `POST ""` (`:270`), `DELETE /{id}` (`:316`), `POST /excluir-lote` (`:342`) | criação e exclusão |
| edição das mesmas | `PUT` de usuários (`:216`), empresas (`:295`), obrigações (`:285`) | edição |

As importações em lote (`POST /importar` de usuários e de empresas) emitem
**uma linha por lote, com a contagem**, e não uma por registro: importação de
200 empresas viraria 200 linhas e afogaria o log que este trabalho existe para
tornar legível. O mesmo vale para `excluir-lote`.

**`EXPORT_DADOS`** entra em `routes/obrigacoes.py:157`, o relatório XLSX, com
a contagem de linhas exportadas. É a única rota que hoje é export de massa de
verdade. O limite dessa escolha, e o que fica descoberto, está escrito no
LASTRO na íntegra e não se repete aqui: **o CSV da tela de Documentos nasce no
navegador e o servidor não o vê.**

**Critério de aceite, verificável por quem não escreveu:**
`python backend/provas/prova_registro_critico.py` sai com código 0, e com
código 1 no código de hoje. Entre os itens, obrigatoriamente: criar exceção de
obrigação emite `CRIACAO_REGISTRO_CRITICO` e não mais `EXCLUSAO`, e apagar
emite `EXCLUSAO_REGISTRO_CRITICO` e não mais `EDICAO`, provado contra
`git show HEAD` para não passar por acaso; criar e apagar usuário, empresa e
obrigação emitem o evento certo com `tabela` e o id do alvo; importar em lote
emite uma linha só, com a contagem; baixar o relatório de obrigações emite
`EXPORT_DADOS` com a contagem; e nenhum campo da lista proibida da nota aparece
em nenhuma linha nova. A suíte inteira de `backend/provas` continua em exit 0.

## Fase 25: entrega, prova no ar e matriz fechada

- **Status:** a fazer
- **Duração estimada:** 1 sessão curta
- **Notas que regem:** `Fechar_Tarefa_Rodar_Verifica`,
  `Padrao_Logging_Estruturado`
- **Dependências:** fases 23 e 24
- **Output esperado:** publicado e provado em produção, não só na máquina.

**Critério de aceite:** o carimbo de `/api/health` avança para o commit desta
fase e bate com o HEAD do repositório, conferido nas duas pontas e não só
depois; `curl` na rota de logout sem token devolve 401 e com token devolve 200;
e uma **conferência visual** na aba Logs do EasyPanel, que é a única prova que
não sai por curl: o usuário faz logout no app e a linha `LOGOUT` aparece com o
`user_id` dele e o `request_id` que o cabeçalho `X-Request-ID` devolveu ao
navegador. A matriz `CONFORMIDADE_VAULT.md` fecha sem linha pendente das fases
23 a 25.

O `Dockerfile` do backend usa `COPY . .`, e isso é conferido ANTES do push, e
não suposto: são três arquivos de prova novos, e arquivo novo que fica fora da
imagem foi o que derrubou o broker em 01/09.

## Fora de escopo (cortado pela escada ou por decisão)

- **`CSRF_INVALIDO` e `RATE_LIMIT_HIT`:** degrau 1. O primeiro não se aplica a
  `Authorization: Bearer`, o segundo já existe com outro nome. Nenhum código.
- **Renomear `LOGIN_RECUSADO` para `LOGIN_FALHA`:** degrau 6 invertido, o
  ganho é zero e quebraria busca antiga. Motivo completo no LASTRO.
- **`EXPORT_DADOS` no CSV da tela de Documentos:** decisão 2 do usuário. O
  servidor não vê o export, e marcar a listagem como export seria log que
  mente. Volta se ele quiser a chamada do frontend.
- **Tarefa, documento, setor, grupo e substituição como registro crítico:**
  decisão 3 do usuário. São o dia a dia da equipe, e logar tudo afogaria o
  sinal.
- **Blacklist de token no logout:** toca toda requisição autenticada e custa
  uma consulta por request. É trabalho próprio, não item de fase de logging.
- **Tabela `logs_acesso` de auditoria legal:** a `Principios` cita, este app
  não tem, e application log em stdout não vira audit log por decreto.

## Histórico deste plano

- **2026-09-09, noite:** plano aberto com as fases 23 a 25, depois do
  levantamento que era o gatilho declarado no plano anterior. Três decisões do
  usuário entraram antes da primeira linha de código: rota de logout que só
  registra, `EXPORT_DADOS` só onde o servidor vê, e registro crítico limitado a
  usuário, permissão, empresa e obrigação.
