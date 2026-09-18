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

## Fases 27 a 31, abertas em 2026-09-15

Trabalho novo: obrigação acessória que o escritório transmite e cuja baixa é
pelo recibo no e-validador. LASTRO, NOTAS_LIDAS, PLANO_FASEADO e
CHECKLIST_APLICACAO recriados com escopo deste trabalho.

[2026-09-15T15:10:00] fase=0 acao=descoberta resultado=ok obs="Boot da vault
com 2 doutrinas e _MAPA_ROTA; 5 pastas do mapa ausentes nesta copia (51, 70, 20,
10, 60). Graphify atualizado (mapa era de 09/09 e 15 arquivos tinham mudado).
Quatro batedores sonnet em paralelo: UI, seguranca, estilo e processo. O de UI
leu errado a Padrao_Toggle_Tipos (disse que radio fica fora); conferido pelo
principal, a linha 11 da nota poe todo seletor nao suspenso nos 3 tipos, e a
pergunta de estilo subiu ao usuario."

[2026-09-15T15:12:00] fase=0 acao=achados resultado=ok obs="Quatro defeitos
medidos no codigo, nenhum corrigido ainda: (1) ObrigacaoUpdate sem `sentido`,
entao a edicao nunca gravou a troca de sentido (schemas.py:274,
obrigacoes.py:313); (2) identificadores escondidos para interna
(Obrigacoes.jsx:497), o que torna a interna com documento uma baixa travada que
o e-validador nunca casa; (3) painel.py:94 nao seguiu a reversao de 09/09 do
models.py:377; (4) link publico de envio gerado para toda tarefa
(whatsapp.py:740, Tarefas.jsx:710). Registrado fora de escopo: alert/prompt
nativos antigos em Tarefas.jsx."

[2026-09-15T15:20:00] fase=0 acao=decisoes_usuario resultado=ok obs="Duas
rodadas. Primeira: 1a quarta opcao Transmitir ao orgao, 2a recibo fica no
acervo, 3b eu listo e ele aprova, 4b sem contador no painel. Segunda, nascida
das notas: 1a seletor tipo 1 da Padrao_Toggle_Tipos, 2a link de envio so para
receber (muda entregar e interna tambem), 3a aba Comprovantes e recibos."

[2026-09-15T15:30:00] fase=0 acao=genesis_ampliado resultado=ok obs="Fases 27 a
31 planejadas, 14 linhas novas pendentes no CONFORMIDADE_VAULT. Aguardando
aprovacao do plano."

[2026-09-15T15:40:00] fase=0 acao=plano_aprovado resultado=ok obs="aprovado
sem ajustes. Proxima acao: fase 27, item 27.1 (prova RED)."

[2026-09-15T16:00:00] fase=27 acao=retomada resultado=ok obs="modo=autonomo,
escolhido pelo usuario. Lastro recarregado: 2 doutrinas e as 5 notas da fase 27,
integrais. Paradas previstas: conferencia visual 29.7 e 30.5, e a lista da 31.2."

[2026-09-15T16:20:00] fase=27 acao=prova_RED resultado=ok obs="27.1.
`backend/provas/prova_transmitir_orgao.py`, 19 checagens, escrita ANTES do
codigo. Contra o codigo de hoje: `PROVA FALHOU nos itens: [2, 3, 4, 5, 6, 7, 10,
19]`, exit 1 (capturado sem pipe, porque o zsh nao tem PIPESTATUS e a primeira
leitura veio vazia).
O que falha, e pelo motivo certo: 2 a 4, o PUT devolve 200 e o GET continua
`receber` (defeito 1 do LASTRO, o campo fora do ObrigacaoUpdate); 5 a 7, POST e
PUT aceitam `sentido=qualquer` (texto livre); 10, a matriz acha EXATAMENTE os
dois casos do defeito 3, `('interna', True, '')` e `('interna', True, 'EFD')`:
o model diz que exige, o painel diz que nao; 19, a funcao unica ainda nao existe.
O que passa, e o porque de cada um, para nao parecer falso verde: 1 e cenario;
11 guarda a matriz contra rodar vazia; 8 passa HOJE PELO MOTIVO ERRADO (o PUT
invalido nao muda o banco porque o campo e descartado, e depois vai continuar
passando porque o 422 barra antes); 9 passa hoje porque o sentido e texto livre,
e continua valendo depois porque transmitir entra na lista; 12, 13 e 14 passam
porque transmitir ja cai no ramo nao-interna do model e do e-validador, o que
confirma a regra local 2 do LASTRO sem codigo novo nesses dois lugares; 15 a 18
sao nao-regressao medida antes: receber/entregar/interna sem flag, listagem com
sentido legado nulo e vazio (guarda do Literal que vai entrar), varchar(10)
comportando `transmitir` no Postgres, e transmitir fora de aguardando cliente.
Vizinhas antes da mudanca: prova_sentido_obrigacao, prova_evalidador_interna e
prova_painel em exit 0."

[2026-09-15T16:35:00] fase=27 acao=codigo_GREEN resultado=ok obs="27.2 a 27.5.
`perfil_documento` em `models.py:380`, chamada por `Tarefa.exige_documento`
(`:377`) e por `_perfil_obrigacao` (`painel.py:94`, import em `:34`). A regra
saiu do painel: `grep -n 'sentido == \"interna\"' app/routes/painel.py` volta
vazio, rc=1. `Sentido = Literal[...]` em `schemas.py:226`, usado em
`ObrigacaoBase` (`:231`) e acrescentado ao `ObrigacaoUpdate` (`:282`).
DECISAO FORA DO PLANO, e declarada: `ObrigacaoResponse` herda de
`ObrigacaoBase`, entao o Literal ia valer tambem na SAIDA, e obrigacao antiga
com sentido nulo ou vazio no banco derrubaria a listagem com 500. A resposta
sobrescreve com `Optional[str]` (`schemas.py:314`): lista fechada na entrada,
tolerante na saida. O item 16 da prova e a sentinela disso.
Comentarios com os quatro valores: `models.py:338`, `:450-455`,
`schemas.py:211`, docstring de `identificar_obrigacao` (`validador.py:267`).
GREEN: `PROVA OK: 19 checagens verdes`, exit 0. Suite: `provas=31
falharam=0`, com as tres vizinhas dentro. Travessao e en-dash nos cinco
arquivos tocados: grep rc=1, vazio. Nenhum marcador `escada:` nesta fase."

[2026-09-15T16:55:00] fase=27 acao=verificador_conformidade resultado=ok obs="LIMPO.
Varreu `backend/app` por sentido, exige_documento, perfil_documento e \"receber\":
nenhum outro ponto escreve ou valida sentido (init_db.py:23 so cria a coluna),
nenhuma copia da regra fora da funcao, `tarefas.py:333-339` ja passa pela
propriedade, travessao zero."

[2026-09-15T17:05:00] fase=27 acao=verificador_evidencia resultado=ok obs="Todas as
linhas citadas no CHECKLIST batem, suite 31 e 0 falhas reproduzida. UM ACHADO
REAL, e aceito: o item 10 compara `perfil_documento` com ela mesma, porque
model e painel agora chamam a mesma funcao. Ele pega duplicacao reintroduzida,
e nao erro da regra: um bug na funcao passaria nos dois lados.
CORRECAO: item 20 novo, oraculo escrito a mao para as 24 combinacoes, sem
chamar o codigo (flag explicita vence; nula deriva dos identificadores; interna
nula nunca exige), conferindo model E painel contra a tabela. No codigo novo:
`PROVA OK: 20 checagens verdes`, exit 0. Contra o HEAD `963fc40`, numa worktree
limpa com a prova nova copiada: `FALHA 20 ... erradas: [('interna', True, ''),
('interna', True, 'EFD')]` e `PROVA FALHOU nos itens: [2, 3, 4, 5, 6, 7, 10,
19, 20]`. O item 20 reprova o codigo antigo pelo motivo certo. Worktree removida.
O item 10 fica, com o papel escrito no comentario da prova."

[2026-09-15T17:15:00] fase=27 acao=verificador_funcional resultado=erro obs="QUEBRA
REAL, causada por esta fase. Obrigacao legada com `sentido=\"\"` no banco abre
na tela com Receber marcado (`Obrigacoes.jsx:930`, `form.sentido || 'receber'`),
e `payloadObrigacao.js` espalha `...f` sem normalizar: o PUT sai com
`sentido:\"\"`, e o `Literal` novo devolve 422. Resultado: NENHUM campo daquela
obrigacao salva mais, e o Duplicar (POST) quebra igual. `null` nao quebra, so o
vazio. O item 16 criava a legada vazia e so testava a LISTAGEM, nunca a
gravacao: foi o buraco. Demais pontos do verificador: importador_cronograma nao
seta sentido (default da coluna); PUT com null grava NULL e se comporta como
receber em todo lugar; o falso positivo do item 10 ja estava tratado pelo item
20.
RED do conserto: itens 21 (PUT da legada com sentido vazio salva o nome) e 22
(POST com sentido vazio cria a copia) escritos antes, `PROVA FALHOU nos itens:
[21, 22]`, exit 1."

[2026-09-15T17:25:00] fase=27 acao=conserto_vazio_GREEN resultado=ok obs="Na causa
raiz, o servidor, e nao na tela: `_sentido_em_branco` em `schemas.py:229`,
aplicada por `field_validator(mode=\"before\")` nos DOIS schemas de entrada
(`:245` ObrigacaoBase, `:297` ObrigacaoUpdate), mesmo desenho do
`_numero_em_branco` que ja existia no arquivo. Vazio vira None, que se comporta
como receber em todo o sistema; palavra inventada continua 422 (itens 5 e 7
verdes). A tela ainda manda o vazio, e isso se arruma na fase 29 sem depender
dela. `PROVA OK: 22 checagens verdes`, exit 0; suite `provas=31 falharam=0`;
travessao rc=1 nos cinco arquivos."

[2026-09-15T17:30:00] fase=27 acao=fase_fechada resultado=ok obs="Criterio atendido:
a prova saiu 1 antes (LOG 16:20) e 0 depois, nas duas rodadas de conserto
(itens 20 e 21-22, cada uma com RED proprio); 31 provas do backend em exit 0
(eram 30 + a nova); travessao vazio nos arquivos tocados. Tres verificadores:
conformidade LIMPO; evidencia com 1 achado (item 10 tautologico, virou item
20); funcional com 1 quebra real (sentido vazio travava a edicao, virou itens
21-22 e o validador). Nenhuma discordancia registrada: os dois achados eram
reais. Balanco de simplificacoes: zero marcadores `escada:` no projeto, nenhum
entrou nesta fase. Fase 27: done. Proxima: fase 28, item 28.1."

[2026-09-15T17:35:00] fase=27 acao=correcao_registro resultado=ok obs="O 'zero
marcadores escada:' da linha anterior foi escrito com um grep que NAO RODOU: o
zsh expandiu `--include=*.py` sem aspas (`no matches found`) e o `0` era do
`wc -l` sobre saida vazia. Refeito com aspas em backend/app, backend/provas e
frontend/src: rc=1, nenhum marcador. O numero estava certo, a prova e que faltava.
Tambem remedidas as linhas do CHECKLIST 27.3 (`schemas.py:244, :296, :329`),
que tinham andado com o conserto do vazio, e o 27.5 passou a citar 22 checagens."

## Fase 28, aberta em 2026-09-15

[2026-09-15T17:50:00] fase=28 acao=prova_RED resultado=ok obs="28.1.
`backend/provas/prova_link_so_receber.py`, 16 checagens, escrita ANTES do codigo.
Contra o codigo de hoje: `PROVA FALHOU nos itens: [3, 4, 7, 8, 9, 10, 11, 12]`,
exit 1.
Pelo motivo certo: 3, a regua em ensaio pos `/enviar/` na mensagem dos cinco
responsaveis (`com link: ['avulsa', 'entregar', 'interna', 'receber',
'transmitir']`); 4 e 8, token de upload criado para quem nao recebe; 7,
`{'entregar': 200, 'interna': 200, 'transmitir': 200}` no link-envio; 9 a 12, as
rotas publicas abriram contexto e ACEITARAM o upload (`[200, 200]`) com token
de tarefa entregar e transmitir, e o arquivo foi anexado.
Verdes no RED, cada um com motivo: 1 cenario (a regua montou mensagem para os
cinco, sem rede: `contatos_zap` e `usuarios_zap` sao dubles); 2, 5 e 6 sao o que
deve continuar (receber e avulsa com link, link-envio do receber 200); 13 a 16
sao a nao-regressao medida antes, com destaque para o 15: `/api/publico/baixar`
do entregar serve a guia com 200.
NOTA sobre o 8: hoje ele falha tambem por causa do 4, ja que a regua criou os
tokens antes da rota ser chamada. Depois do conserto os dois caminhos ficam
isolados, e o 8 so pode falhar se a ROTA gravar token ao recusar.
28.2 pre-condicao: `grep -rn \"_tarefa_por_token\" app` devolve a definicao
(`upload_publico.py:16`) e dois chamadores, `contexto` (`:27`) e `enviar`
(`:42`). `baixar_documento` (`:62`) nao passa por ele: procura por
`TarefaEnvio.token` e `Tarefa.saida_token`. A trava no helper nao alcanca o download."

[2026-09-15T18:05:00] fase=28 acao=codigo_GREEN resultado=ok obs="28.2 a 28.4.
Irmaos procurados antes de editar: `grep -rn \"link_publico\|get_or_create_token\|upload_token\"
backend/app frontend/src` acha DOIS chamadores de `link_publico`, a regua
(`whatsapp.py:741`) e a rota (`tarefas.py:225`), e um leitor de
`upload_token`, o `_tarefa_por_token`. Sao os tres do plano, sem quarto.
A mesma checagem nos tres: `whatsapp.py:742` (`if tarefa.sentido ==
\"receber\"`, antes do `link_publico`, entao o token nem nasce);
`tarefas.py:226` (`if t.sentido != \"receber\"`, 404, ANTES do `link_publico`);
`upload_publico.py:21` (`if not t or t.sentido != \"receber\"`, a mesma linha e o
mesmo texto do token inexistente). Menu da tela: `Tarefas.jsx:709`, `{ativa &&
tarefa.sentido === 'receber' && (`. A checagem usa a propriedade
`Tarefa.sentido`, que ja devolve receber para tarefa avulsa e para obrigacao
com sentido nulo ou vazio: nada de legado muda.
GREEN: `PROVA OK: 16 checagens verdes`, exit 0. Suite backend `provas=32
falharam=0` (31 + a nova, com prova_escopo_link e prova_entrega_cliente
dentro). Frontend `provas_front=19 falharam=0` e `npm run build` com `built in
1.21s`. Popup nativo em linha nova do Tarefas.jsx: 0. Travessao nos cinco
arquivos: rc=1. Nenhum marcador `escada:`."

[2026-09-15T18:25:00] fase=28 acao=verificador_conformidade resultado=ok obs="LIMPO.
Nenhum quarto emissor de `/enviar/`, `upload_token` ou `link_publico` em
backend/app e frontend/src. `tarefa.sentido` chega real na tela
(`TarefaResponse.sentido`, schemas.py:211). Ordem do `_tarefa_por_token`: token
inexistente e sentido errado dao o mesmo 404; o 403 de empresa bloqueada so e
alcancado por tarefa receber existente, comportamento herdado e nao introduzido
aqui. Apontou `alert()`/`prompt()` em `handleCopiarLink` (`Tarefas.jsx:498,500`):
pre-existente e ja listado como fora de escopo no PLANO, nada a fazer nesta fase."

[2026-09-15T18:30:00] fase=28 acao=verificador_evidencia resultado=ok obs="RED
reproduzido numa worktree do HEAD `963fc40`: `[3, 4, 7, 8, 9, 10, 11, 12]`,
exit 1, identico ao LOG 17:50. Suites conferidas: 32 backend, 19 frontend, zero
falhas. Item 15 nao e vacuo (usa `saida_token`, caminho que nao passa pelo
helper). UM ACHADO, aceito: a evidencia do 28.2 citava `upload_publico.py:27,
:42, :62`, linhas do grep ANTES do conserto, que andaram 3 com o comentario do
GREEN. CHECKLIST corrigido: mantida a medicao original, que e o que o item
pede, e acrescentadas as linhas atuais `:30, :45, :65`."

[2026-09-15T18:45:00] fase=28 acao=verificador_funcional resultado=ok obs="Nenhuma
quebra no codigo. Dois pontos. (1) LACUNA NA PROVA, aceita: o item 5 cobre so
tarefa sem obrigacao; obrigacao real com sentido NULL ou vazio gravado nao era
testada. Item 17 novo; nasce verde por ser nao-regressao, e isso fica declarado.
A primeira versao dele quebrou com DetachedInstanceError (a prova lia `emp.id`
de sessao fechada; defeito da prova, nao do app), corrigida relendo os ids.
`PROVA OK: 17 checagens verdes`, exit 0. (2) RISCO REGISTRADO, sem conserto:
tarefa cuja obrigacao some sem cascata vira orfa, `Tarefa.sentido` cai no
`else \"receber\"` e o upload reabre. Nao e alcancavel pela API
(`_excluir_definitivo` apaga as tarefas antes da obrigacao), e consertar pede
separar avulsa de orfa na propriedade, que e escopo novo. Fica para decisao do
usuario, e nao vira marcador `escada:` porque nao e simplificacao feita aqui.
Fase 28: done. Proxima: fase 29.
PAUSA: o usuario perguntou por que a geracao nao criou tarefas de empresas
selecionadas. Diagnostico fora do plano, sem mudanca de codigo."
