# LOG

Trabalho fechado em 2026-09-09: **varios responsaveis por (empresa, setor)**, e
com ele as oito frentes que vieram junto (o responsavel saindo da obrigacao, o
e-validador em obrigacao interna, a excecao por empresa e o check "aplicar a
todas"). Nove fases, da 9 a 17, todas em done, publicadas e conferidas em
producao pelo carimbo e pelas rotas.

O historico completo (LASTRO, NOTAS_LIDAS, PLANO_FASEADO, CHECKLIST_APLICACAO,
o LOG integral e a matriz) esta em `checkpoint 20260909 112849.zip`, nesta mesma pasta. O trabalho anterior,
o SSO do Hub, esta em `checkpoint 20260817 152106.zip`.

O `CONFORMIDADE_VAULT.md` segue aberto aqui de proposito, como da outra vez: e
a prova de que a entrega obedeceu o padrao, e e a unica coisa desta pasta que
alguem pode precisar mostrar a terceiro.

## O que ficou para o usuario, e nao e codigo

- **Preencher a matriz (empresa, setor)** das empresas que ainda nao tem
  responsavel cadastrado. A tarefa nao herda mais o responsavel da obrigacao, e
  o scheduler gera o mes no dia 1 as 6h. A resposta da geracao diz quantas
  nasceram sem dono e de quais empresas.
- ~~Travessoes em texto visivel, que a Fase 6 tinha zerado em 17/08 e voltaram
  no trabalho de agosto e setembro~~ **FEITO em 2026-09-09**, a pedido do
  usuario, logo depois do fechamento: 51 no frontend (9 telas) e 3 no backend,
  todos reescritos. Medido tirando comentario antes de contar, e no backend
  pela AST, so nas strings de dado. Zero nos dois lados. Detalhe na matriz de
  conformidade.
- **`log_event` sem `request_id`, `path` e `method`**, que a
  `Padrao_Logging_Estruturado` lista como obrigatorios. Achado de verificador,
  nao corrigido porque e o logger central do app inteiro.

## Depois do fechamento

- **2026-09-09, tela de Empresas nao abria.** Reportado pelo usuario logo apos
  o fechamento. Causa: o `useEffect` que fecha o popover de responsaveis ficou
  ACIMA do `const [showModal]` em `frontend/src/pages/Empresas.jsx`, e o array
  de dependencia e avaliado no corpo do render. `showModal` caia na zona morta
  e o React nem montava: `ReferenceError: Cannot access 'showModal' before
  initialization`, tela branca ao clicar no menu. Entrou no commit `d78f97e`,
  da propria Fase 15. **O build compila igual**, entao nem o `npm run build`
  nem a verificacao adversarial pegaram: e erro de runtime, e nenhuma prova
  montava o componente.
  Corrigido movendo o `useEffect` para depois da declaracao (`c335723`), sem
  mudar comportamento: `prova_seletor_responsaveis.js` segue 18 de 18.
  Checagem executavel nova, `frontend/provas/prova_ordem_hooks.js`, que varre
  TODO o `src` e nao so esta tela. Reprova o codigo publicado
  (`src/pages/Empresas.jsx:66 usa 'showModal', que so nasce na linha 68`,
  exit 1) e aprova o corrigido (exit 0). Varredura no resto do frontend:
  limpo, era o unico caso.
  PUBLICADO E PROVADO NO AR: o carimbo do `/api/health` NAO se move aqui, e
  isso esta certo, porque ele e do backend e a mudanca foi so de frontend. A
  prova e o hash de conteudo do bundle do Vite: a versao quebrada gera
  `index-DRT8Tced.js`, a corrigida gera `index-DwKXh0Cp.js`, e o
  `curl https://gestordetarefas.zoaria.com.br/` devolve
  `assets/index-DwKXh0Cp.js`.
