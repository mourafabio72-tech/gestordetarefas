# LOG

Trabalho fechado em 2026-09-10: **os eventos que faltavam na tabela da nota de
logging**. Tres fases, da 23 a 25, todas em done, publicadas e conferidas em
producao, inclusive a que so o usuario podia conferir: a linha `LOGOUT` real na
aba Logs do `backend`.

**Com este trabalho a `Padrao_Logging_Estruturado` esta cumprida por inteiro.**
Ela tem duas tabelas: a dos oito campos obrigatorios, fechada pelas fases 18 a
20 em 09/09, e a dos treze eventos minimos, fechada agora. Dos treze, quatro ja
existiam, um existe com outro nome mantido pela escada (`LOGIN_RECUSADO`), dois
nao se aplicam a este app com o motivo escrito no codigo (`CSRF_INVALIDO` e
`RATE_LIMIT_HIT`), e seis entraram nestas fases. Esta frente acaba aqui, e nao
continua.

O historico completo (LASTRO, NOTAS_LIDAS, PLANO_FASEADO, CHECKLIST_APLICACAO e
o LOG integral) esta em `checkpoint 20260910 114113.zip`, nesta mesma pasta. Os
trabalhos anteriores estao em `checkpoint 20260909 213548.zip` (os campos
obrigatorios no logger), `checkpoint 20260909 112849.zip` (varios responsaveis
por empresa e setor) e `checkpoint 20260817 152106.zip` (o SSO do Hub).

O `CONFORMIDADE_VAULT.md` segue aberto aqui de proposito, como das outras vezes:
e a prova de que a entrega obedeceu o padrao, e e a unica coisa desta pasta que
alguem pode precisar mostrar a terceiro. Ele esta sem nenhuma linha pendente.

## O que este trabalho deixou no ar

| Fase | O que mudou | Como se pergunta a producao |
|---|---|---|
| 23 | quem tenta o que nao pode deixa rastro, e quem sai tambem | aba Logs, buscando `ACESSO_NEGADO_403`, `ACESSO_NEGADO_IDOR`, `MUDANCA_ROLE` ou `LOGOUT` |
| 24 | criar, editar e apagar cadastro critico deixa linha com o nome certo, e os dois nomes trocados voltaram ao lugar | aba Logs, buscando `CRIACAO_REGISTRO_CRITICO` e irmaos |
| 25 | publicado e provado, com a linha real conferida na aba Logs | `curl -s .../api/health` traz o `build` do commit |

## O placar dos verificadores, que vale guardar

Seis verificadores adversariais rodaram e **os seis acharam algo real**, o que
nao tinha acontecido em nenhum trabalho anterior deste projeto: a guarda de
IDOR aplicada pela metade em quatro rotas (entre elas a mais obvia de todas), a
importacao trocando papel sem rastro, as linhas de evidencia que eu colei sem
serem captura literal, o logger que podia derrubar quem ele registra, sete
rotas irmas mudando as mesmas tabelas por outro verbo, e log afirmando o que o
banco nao gravou. Todos viraram conserto, e nenhum virou marcador de divida.

O setimo achado nao veio de verificador nenhum: veio do **usuario**, colando o
log de producao. O logout devolvia 401 com todas as provas verdes, porque o
defeito morava entre o navegador e a rota, onde nenhuma delas olhava.

Duas licoes ficam do dia. **Cobrir uma rota e nao procurar o padrao IRMAO e o
erro mais caro deste projeto**, e ele aconteceu DUAS vezes em doze horas, nas
duas fases cujo LASTRO cita a `Escada_Preguica_de_Codigo`. E **conferencia
visual nao e burocracia**: a de hoje derrubou uma fase que estava verde em
tudo que se mede de fora.

## O que ficou para o usuario, e nao e codigo

- **Nada deste trabalho.** As duas conferencias visuais foram feitas e estao
  coladas no LOG que foi para o zip.

## Fase 26, aberta e fechada em 2026-09-10

Trabalho NOVO, e nao continuacao do anterior: aquele era de logging, este e de
AUTORIZACAO. Nasceu de um achado meu durante a fase 23, registrado como
`blocked` e levado ao usuario no fechamento, que mandou virar fase propria.

[2026-09-10T14:05:00] fase=26 acao=prova_RED resultado=ok obs="26.1.
`backend/provas/prova_escopo_link.py`, 12 checagens, escrita ANTES do codigo e
reprovando o codigo de hoje: `PROVA FALHOU nos itens: [2, 3, 4, 5, 8, 9, 10,
11]`, exit 1. Os quatro que passavam sao o cenario (1) e tres itens de
NAO-REGRESSAO medidos antes de proposito: o dono continua recebendo o link (6),
o dono nao gera IDOR (7), e o admin continua transferindo (12). Sem eles, uma
rota que recusasse TODO MUNDO passaria nos primeiros itens e pareceria
consertada.
O RED PROVOU QUE O BURACO ERA PIOR DO QUE EU TINHA DITO AO USUARIO. Eu descrevi
`GET /{id}/link-envio` como leitura indevida. O item 3 mostra que nao e so
leitura: `link_publico` chama `get_or_create_token`, entao o GET CRIA o token
quando ele ainda nao existe. Quem passasse por ali ABRIA uma porta de upload
sem senha numa tarefa de empresa que nao atende. Um GET que muta, e a mutacao
e justamente a porta.
E o item 11 provou o irmao menor de verdade, e nao por leitura: o gestor de
escopo reduzido TRANSFERIU a tarefa alheia, e o responsavel mudou no banco. O
cenario precisou de cuidado, porque o preset de gestor tem escopo `todas` e o
buraco so aparece com override, que o app permite criar."

[2026-09-10T14:07:00] fase=26 acao=escopo_aplicado resultado=ok obs="26.2 e
26.3. As duas rotas passaram a usar `_tarefa_no_escopo`, que ja existia e ja e
o que as outras sete rotas usam: degrau 2 da escada, sem funcao nova. Uma linha
em cada, e o evento `ACESSO_NEGADO_IDOR` sai de brinde, porque o helper ja
registra.
`PROVA OK: 12 checagens verdes`. Regressao: 30 provas do backend e 19 do
frontend em exit 0. Travessao nos arquivos do diff: nenhum."

[2026-09-10T14:12:00] fase=26 acao=publicado resultado=ok obs="Commit `b1bb759`,
push com `git ls-remote` NO SERVIDOR confirmando o ref
(`b1bb759ddd4436dd...`), e o webhook publicou sozinho. Carimbo de producao
`20260910-1144`, igual ao HEAD, conferido nas duas pontas.
O QUE DA PARA PROVAR DE FORA, e e pouco de proposito: as duas rotas continuam
exigindo autenticacao (401 sem token nas duas). O COMPORTAMENTO DE ESCOPO NAO
SE PROVA POR CURL, porque exige dois usuarios com escopos diferentes e um deles
sem direito a tarefa do outro: isso esta provado na maquina, pelos 12 itens,
com os tres de nao-regressao medidos antes.
NAO PECO CONFERENCIA VISUAL DESTA VEZ, e explico em vez de omitir: para o
usuario ver o buraco fechado ele teria de entrar como um analista de escopo
reduzido e tentar abrir a tela de uma tarefa alheia, o que e trabalhoso e
mexe com conta de outra pessoa. O risco de nao conferir e conhecido e pequeno:
o helper `_tarefa_no_escopo` ja rege sete outras rotas em producao desde
09/09, e as tres nao-regressoes garantem que quem tem direito nao perdeu
acesso."

[2026-09-10T14:13:00] fase=26 acao=fase_fechada resultado=ok obs="Criterio
atendido: `prova_escopo_link.py` sai com codigo 0 (12 verdes) e saia com codigo
1 no codigo anterior, com o RED colado aqui; as 30 provas do backend e as 19 do
frontend em exit 0; carimbo batendo com o HEAD.
REGISTRO DE PROCESSO, para nao parecer lacuna a quem ler depois: esta fase NAO
teve `PLANO_FASEADO` nem `CHECKLIST` proprios. Ela nasceu de um achado ja
registrado como `blocked`, foi aprovada em uma frase pelo usuario, tem um unico
criterio de aceite e um diff de duas linhas em duas rotas. Montar os quatro
artefatos para isso seria burocracia, e o registro que importa esta aqui: o
achado, o RED, o desenho, o GREEN e a prova em producao. Fase de tamanho maior
volta a abrir os artefatos.
Fase 26: done. Nenhum marcador `escada:` no projeto."
