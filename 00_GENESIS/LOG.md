# LOG

Trabalho fechado em 2026-09-09: **os campos obrigatorios no logger central**, e
as quatro frentes que vieram junto. Cinco fases, da 18 a 22, todas em done,
publicadas e conferidas em producao, inclusive as duas que so o usuario podia
conferir: a linha de log real na aba Logs do `backend`, e a ausencia de
`already exists` no log do `db`.

O historico completo (LASTRO, NOTAS_LIDAS, PLANO_FASEADO, CHECKLIST_APLICACAO e
o LOG integral) esta em `checkpoint 20260909 213548.zip`, nesta mesma pasta. Os
trabalhos anteriores estao em `checkpoint 20260909 112849.zip` (varios
responsaveis por empresa e setor) e `checkpoint 20260817 152106.zip` (o SSO do
Hub).

O `CONFORMIDADE_VAULT.md` segue aberto aqui de proposito, como das outras vezes:
e a prova de que a entrega obedeceu o padrao, e e a unica coisa desta pasta que
alguem pode precisar mostrar a terceiro. Ele esta sem nenhuma linha pendente.

## O que este trabalho deixou no ar

| Fase | O que mudou | Como se pergunta a producao |
|---|---|---|
| 18 | os oito campos obrigatorios entram sozinhos em toda linha de log | `curl -sI .../api/health` traz `X-Request-ID` diferente a cada chamada |
| 19 | publicado e provado, com a linha real conferida na aba Logs | `curl -s .../api/health` traz o `build` do commit |
| 20 | erro 500 sai com id, com cabecalhos e dizendo quem derrubou a rota | so pela aba Logs, buscando `ERRO_NAO_TRATADO` |
| 21 | zero travessao no projeto, inclusive comentario e documentacao | `grep -rn "—"` no repositorio volta vazio |
| 22 | o boot parou de escrever a lista de migracoes como erro no banco | aba Logs do servico `db`, sem `already exists` |

## O que ficou para o usuario, e nao e codigo

- **Nada deste trabalho.** As duas conferencias visuais foram feitas em
  2026-09-09 e estao coladas no LOG que foi para o zip.
- O que continua aberto e de outra frente, e esta no `CLAUDE.md` da vault: os
  eventos que faltam na tabela da nota de logging (`ACESSO_NEGADO_403`,
  `RATE_LIMIT_HIT`, `LOGOUT`, `EXPORT_DADOS`), cortados desta fase por decisao
  do usuario. Viram fase propria, e o gatilho e o levantamento de quais ja
  existem hoje.
