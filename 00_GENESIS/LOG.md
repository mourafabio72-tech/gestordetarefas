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

[2026-09-18T18:20:00] fase=32 acao=trabalho_aberto resultado=ok obs="Recorte por regime tributario no modal Gerar tarefas do mes. Decisoes 1a, 2b, 3a, 4a. Fases 27 e 28 commitadas antes, local, sem push (45ac41a codigo, 4d1a669 GENESIS; provas 22 e 17 verdes na hora do commit). Graphify atualizado. Tres batedores sonnet em paralelo. Achado da ficha de seguranca, confirmado no codigo: POST /obrigacoes/gerar sem log_event, vira fase 32. Fases 32 a 34 planejadas, ordem de execucao 32, 33, 34, 29, 30, 31. Pendente: estilo do seletor (Padrao_Toggle_Tipos) e aprovacao do plano."

[2026-09-18T18:35:00] fase=0 acao=plano_aprovado resultado=ok obs="Fases 32 a 34 aprovadas sem ajustes. Estilo do seletor Para quais empresas: tipo 1, multi opcoes. Proxima: fase 32."

## Fase 32, aberta em 2026-09-18

[2026-09-18T18:45:00] fase=32 acao=retomada resultado=ok obs="modo=autonomo (gravado em 15/09, nao reperguntado). Lastro recarregado nesta invocacao: 2 doutrinas (Anti_Puxa_Saco 189 linhas, Leitura_e_Retencao_de_Notas 236), App_Online_Auth (82), Padrao_Logging_Estruturado (210) e TDD_RED_GREEN_REFACTOR (204), integrais."

[2026-09-18T18:50:00] fase=32 acao=prova_RED resultado=ok obs="32.1. `backend/provas/prova_gerar_log.py`, 13 checagens, escrita ANTES do codigo, no molde da `capturar()` de `prova_registro_critico.py`. Contra o codigo de hoje: `PROVA FALHOU nos itens: [2, 3, 4, 5, 6, 7, 8, 9, 10]`, rc=1 (medido sem pipe).
Pelo motivo certo: a rota nao emite linha nenhuma, entao 2 (uma linha por chamada), 3 (tabela e lote), 4 (oito campos e usuario), 5 (numeros da resposta), 6 (tamanho do recorte), 9 (zero criadas registra) e 10 (None sem recorte) falham. 7 e 8 (sem razao social, CNPJ nem lista de ids) falham HOJE porque a linha nao existe: tem guarda `bool(e1)` para nao passar vacuo.
Verdes no RED, cada um com motivo: 1 e o cenario; 11 a 13 sao nao-regressao medida antes: resposta da rota igual a do servico chamado direto, 403 sem a flag sem linha de criacao, 400 com mes 13 sem linha de criacao.
DECISAO DE NOME, dentro do plano: o plano pedia 'quantidade de obrigacoes e de empresas do recorte, None sem recorte'. Os campos sairam como `obrigacoes_no_recorte` e `empresas_no_recorte`, o segundo com o mesmo nome e o mesmo valor que o gerador ja devolve na resposta."

[2026-09-18T18:55:00] fase=32 acao=codigo_GREEN resultado=ok obs="32.2 e 32.3. Uma chamada a `log_event` em `gerar_competencia`, `routes/obrigacoes.py:234-237`, depois de `gerar_tarefas` e com os numeros da resposta dele. `obrigacoes_no_recorte` conta `set(body.obrigacao_ids)`, igual ao gerador que conta `set(empresa_ids)`: id repetido no body nao infla a contagem. `services/gerador.py` sem diff.
GREEN: `PROVA OK: 13 checagens verdes`. Suite do backend: `provas=33 falharam=0`. Travessao e en-dash nos dois arquivos tocados: rc=1. Marcadores `escada:` em backend/app, backend/provas e frontend/src: rc=1, nenhum."

[2026-09-18T19:10:00] fase=32 acao=verificador_evidencia resultado=ok obs="LIMPO. RED reproduzido numa worktree do HEAD `c92a577` com a prova copiada: `[2, 3, 4, 5, 6, 7, 8, 9, 10]`, rc=1, identico ao LOG 18:50. GREEN 13 verdes, suite 33 e 0, linhas citadas batem, `gerador.py` sem diff. Vacuidade: os itens 5 a 10 caem juntos quando a linha falta, guardados por `bool(e1)`."

[2026-09-18T19:12:00] fase=32 acao=verificador_seguranca resultado=erro obs="UM ACHADO REAL, aceito: `create_empresa` (`routes/empresas.py:304`) chama `gerar_empresa_mes_atual`, que cria as tarefas do mes da empresa nova em lote, e so a linha da EMPRESA saia. E o padrao irmao, o erro que este projeto ja registrou como o mais caro. Os outros pontos: linha nova sem PII e sem risco de derrubar a rota (`log_event` com `default=str` e excecao engolida), LIMPO; `obrigacoes_no_recorte` conta ids pedidos e nao os que existem, mesma semantica herdada de `empresas_no_recorte`, registrado e nao consertado; travessao LIMPO.
OBSERVACAO REGISTRADA, SEM CONSERTO: a linha de criacao de EMPRESA (`empresas.py`, anterior a este trabalho) leva `razao_social` e `cnpj`. A lista do 'NUNCA entra' da `Padrao_Logging_Estruturado` fala em CPF, RG, cartao, conta e saude, e nao em CNPJ de pessoa juridica. O caso cinzento e o MEI, cujo CNPJ aponta uma pessoa. Fica para decisao do usuario."

[2026-09-18T19:15:00] fase=32 acao=irmao_RED resultado=ok obs="Itens 14 a 16 na mesma prova: cadastrar empresa lucro_real gera as 2 tarefas (14, cenario, verde), deixa UMA linha de tarefa em lote com a contagem do header `X-Tarefas-Geradas` (15) e diz `origem=cadastro_empresa`, recorte 1 e nenhuma razao social (16). `PROVA FALHOU nos itens: [15, 16]`, rc=1."

[2026-09-18T19:20:00] fase=32 acao=irmao_GREEN resultado=ok obs="`routes/empresas.py:318`, linha `CRIACAO_REGISTRO_CRITICO` com `tabela=tarefa`, `lote=True`, `origem=cadastro_empresa`, criadas, puladas e `empresas_no_recorte=1`. A geracao do mes ganhou `origem=gerar_mes` (`obrigacoes.py:234`, item 3 agora confere), para os dois caminhos se separarem no filtro.
TROPECO NO CAMINHO, e corrigido pela ordem, nao pela prova: na primeira versao a linha de tarefa saiu DENTRO do try, antes da linha da empresa, e `prova_registro_critico.py` item 8 quebrou, porque ele le a PRIMEIRA linha CRIACAO. A linha de tarefa foi para depois da de empresa, que e a ordem causal, e so sai quando a geracao nao caiu no rollback. Prova antiga intocada.
`PROVA OK: 16 checagens verdes`; `provas=33 falharam=0`; travessao rc=1 nos tres arquivos; `gerador.py` sem diff."

[2026-09-18T19:22:00] fase=32 acao=fase_fechada resultado=ok obs="Criterio atendido: prova com RED no LOG (18:50 e 19:15) e GREEN (19:20), suite verde. Dois verificadores: evidencia LIMPO, seguranca com 1 achado real (o irmao), corrigido. CONFORMIDADE: as duas linhas da fase 32 em ok, com a saida colada. Balanco de simplificacoes: `escada:` rc=1 em backend/app, backend/provas e frontend/src, nenhum marcador. Fase 32: done. Proxima: fase 33, item 33.1."

## Fase 33, aberta em 2026-09-18

[2026-09-18T19:30:00] fase=33 acao=lastro_tela resultado=ok obs="Notas da fase lidas integrais nesta invocacao, com wc -l antes: Padrao_Toggle_Tipos 167, Padrao_Toggle_OnOff 234, Padrao_Selecao_em_Lote 283, Tela_Nao_Tem_Manual 112, Sistema_de_Estilos 215, Verificacoes_Mecanicas_de_Tela 278, Protocolo_Revisao_de_Tela 234, Portugues_BR_Acentuacao 165, Sem_Travessao 43, Sem_Popup_Nativo 116, Padrao_IDOR 199, Padrao_Mass_Assignment 210. Skills de tela: nao estao carregadas como skill, mas os GUIA.md de `frontend-design` (55) e `ui-ux-pro-max` (383) do pacote joviano-fabrica-apps foram lidos; onde conflitam, a vault vence. Do que sobra delas: foco visivel no teclado e estado desabilitado claro."

[2026-09-18T19:40:00] fase=33 acao=prova_RED resultado=ok obs="33.1. `frontend/provas/prova_recorte_regime.js`, escrita ANTES do modulo: `Error [ERR_MODULE_NOT_FOUND]: Cannot find module .../src/pages/recorteGeracao.js`, rc=1. RED por ausencia, como o plano define para prova de modulo novo."

[2026-09-18T19:45:00] fase=33 acao=modulo_GREEN resultado=ok obs="`src/pages/recorteGeracao.js`: `REGIMES_GERACAO` (7, na ordem decidida, rotulos iguais aos de `Empresas.jsx:27-36`), `empresasDosRegimes`, `idsDoRecorte`, `podeGerar`. DECISAO DENTRO DO PLANO: modo desconhecido FALHA FECHADO, `idsDoRecorte` devolve `[]` e `podeGerar` bloqueia; so 'todas' vira null. Sem isso um typo no estado mandaria null e geraria o escritorio inteiro. Item 14 novo guarda isso."

[2026-09-18T19:50:00] fase=33 acao=nomes_RED_GREEN resultado=ok obs="Item 16 novo para o texto da faixa de resumo ('Simples Nacional, Lucro Real e MEI', na ordem da lista). RED: `does not provide an export named 'nomesDosRegimes'`. GREEN: `PROVA OK: 16 checagens verdes`. Arquivo conferido UTF-8 depois do acrescimo por heredoc (`file`: UTF-8 text)."

[2026-09-18T19:55:00] fase=33 acao=tela resultado=ok obs="33.2 a 33.5 em `Obrigacoes.jsx`. Estado `gerModo` + `gerRegimes` (`:140`), chamada por `idsDoRecorte` (`:151`). Seletor tipo 1 em `:1059`: `role=radiogroup` + `aria-label`, tres `<button type=button role=radio aria-checked>`, `title` com a dica, escolhido `border-primary-600 bg-primary-50 text-primary-800`, foco visivel por `focus-visible:outline-primary-600` (conferido no CSS do build). Modo regime: 7 `check-app` em duas colunas com contagem por regime, e 'N empresa(s) no recorte'. Frase de consequencia ja existente passou a valer para os dois recortes. Resumo com ramo de regime (`:1147-1149`); botao com `podeGerar` e tres textos de bloqueio conforme a causa (`:1165-1171`).
DECISAO VISUAL DECLARADA: o modal foi de `max-w-md` para `max-w-lg` (`:1010`). Os tres rotulos em 12px semibold nao cabem numa linha em 416px uteis; o wrapper tem `flex-wrap` de reserva. A conferencia visual decide se ficou bom.
Build `✓ built`; `provas_front=20 falharam=0`; travessao rc=1; hex nas linhas `+` rc=1; popup nas linhas `+` 0; `h-4 w-4` e `cv-sw` nas linhas `+` rc=1."

[2026-09-18T20:00:00] fase=33 acao=checkbox_irmao resultado=ok obs="A lista de 'Somente as escolhidas', no mesmo bloco, ainda usava `h-4 w-4`, o checkbox cru. Trocado por `check-app`, uma palavra, para os dois modos do mesmo seletor terem o mesmo checkbox. No modal inteiro, `h-4 w-4` e `type=\"radio\"` voltam vazios. Os checkboxes crus FORA do modal seguem fora de escopo, como o PLANO diz. Build ok."

[2026-09-18T20:05:00] fase=33 acao=correcao_registro resultado=ok obs="Na primeira escrita da evidencia do CHECKLIST citei `itens 11 a 14 e 16` para `podeGerar` e `item 17` para `nomesDosRegimes`. A prova tem 16 itens: `podeGerar` e 11 a 15 (15 e a nao-regressao de escolhidas vazia) e `nomesDosRegimes` e o 16. Corrigido."

[2026-09-18T20:15:00] fase=33 acao=verificador_conformidade resultado=ok obs="LIMPO. Tipo 1 correto, check-app nos dois modos, zero travessao e popup, acentuacao das strings novas conferida, `GerarRequest` sem campo novo, `gerador.py` sem diff, comportamento de 'todas' e 'escolhidas' preservado. Duas observacoes, registradas sem conserto: (1) a frase de consequencia agora serve os dois recortes, e continua verdadeira nos dois; (2) 'de Lucro Real e Lucro Presumido' no resumo e a forma que o PLANO fixou no item 33.5, e nao ha regra da vault contra ela."

[2026-09-18T20:20:00] fase=33 acao=verificador_evidencia resultado=erro obs="Tres achados, os tres aceitos. (1) DEFEITO REAL: `empresasDosRegimes` contava empresa `bloqueado`, e o gerador exclui (`empresas_alvo`, gerador.py:226). 'Lucro Real (8)' prometia tarefa que nao sai, e um regime so com bloqueadas liberava o botao para uma geracao que nao cria nada. (2) EVIDENCIA IMPRECISA no 33.6: o item pede hex vazio nos arquivos tocados, e `Obrigacoes.jsx:928` tem `bg-[#faf7f0]`. E anterior e sai no 29.2, mas o registro dizia so 'linhas + e modulo', sem declarar o arquivo inteiro. (3) CITACAO: 'itens 11 a 15' para o lado que bloqueia incluia o 13, que prova o lado que libera."

[2026-09-18T20:25:00] fase=33 acao=bloqueada_RED_GREEN resultado=ok obs="Item 16 novo na prova (empresa bloqueada e empresa `ativo:false` fora da contagem e do recorte; regime so com bloqueada bloqueia o botao). RED: `AssertionError [ERR_ASSERTION]: Expected values to be strictly deep-equal`, rc=1. GREEN: filtro `e.ativo !== false && !e.bloqueado` em `empresasDosRegimes` (`recorteGeracao.js`), o mesmo criterio do gerador. `PROVA OK: 17 checagens verdes` (nomesDosRegimes passou a ser o 17); `provas_front=20 falharam=0`; build ok; travessao rc=1. CHECKLIST corrigido nos tres pontos: citacao de itens, numero da prova e a declaracao do hex anterior em `:928`.
Fica declarado e sem conserto: a lista de 'Somente as escolhidas' tambem mostra empresa bloqueada, como ja mostrava antes. Escolher uma bloqueada gera zero para ela; o resumo pos-geracao ja diz quantas foram criadas."

[2026-09-18T20:35:00] fase=33 acao=conformidade resultado=blocked obs="Sete linhas mecanicas da fase 33 em ok na CONFORMIDADE, com a saida colada (IDOR, Mass_Assignment, checkbox, hex com o `:928` declarado, popup, travessao, lingua). Faltam as tres de CONFERENCIA_VISUAL (Toggle_Tipos duas vezes, Tela_Nao_Tem_Manual) e o item 33.7. PARADA PREVISTA: so o usuario confere. A fase 33 nao fecha sem isso, e a 34 (push) espera."

[2026-09-18T20:50:00] fase=33 acao=ambiente_conferencia resultado=ok obs="Para o usuario conferir local: o banco `gestor_local.db` foi COPIADO para o scratchpad da sessao, e so na copia a senha de admin@bps4.local foi trocada, digitada por ele via getpass (script no scratchpad, fora do repo). Original intocado. Frontend subiu pelo painel do app (`.claude/launch.json` no diretorio de trabalho da sessao, fora do repo do Tareffas). Dois 401 no caminho: ele digitou admin@bps4.com.br, e o usuario local e admin@bps4.local."

[2026-09-18T20:55:00] fase=33 acao=conferencia_visual resultado=ok obs="Conferido em 2026-09-18 pelo usuario, tela Obrigacoes > Gerar tarefas do mes, modo Por regime tributario: 'ficou bom'. O print dele mostrou uma coisa que ele nao reclamou e eu nao deixei passar: a terceira opcao QUEBRAVA para a linha de baixo. Medido no navegador: tela com zoom de 81%, faixa com 369px para 390 de pai com 9.75px de padding, meio pixel a mais que o espaco. Estreitar botao era fragil (tentado com px-2, continuou quebrando). Solucao: padding de volta ao da nota (px-2.5 = 10px) e modal de `max-w-lg` para `max-w-xl` (`Obrigacoes.jsx:1010`). Medido depois: os tres botoes com o mesmo `top`, uma linha so. `flex-wrap` segue de reserva para celular.
Medido tambem, o que o print nao mostrava: Lucro Real + Lucro Presumido marcados -> '4 empresa(s) no recorte' e resumo 'Para 4 empresa(s) de Lucro Real e Lucro Presumido.', botao liberado; so MEI (0) -> '0 empresa(s) no recorte', botao `disabled` com title 'Nenhuma empresa ativa nos regimes marcados.'"

[2026-09-18T21:05:00] fase=33 acao=pedido_usuario resultado=ok obs="Pedido do usuario: 'colocar uma cor com ressalva, tipo verde'. Ambiguo, e uma das leituras (opcao escolhida em verde solido) contraria a Padrao_Toggle_Tipos (solido e do tipo 2, verde e do on/off). Perguntado com as tres leituras e o conflito na mesa; resposta: o TEXTO DE RESSALVA. A frase de consequencia ganhou caixa `border-primary-200 bg-primary-100 text-primary-900` (`Obrigacoes.jsx:1129`). Primeira tentativa com `primary-50` ficou quase da cor do creme, subiu um tom. So token, zero hex (linhas + com hex, popup: 0). Conferido por print no painel."

[2026-09-18T21:10:00] fase=33 acao=fase_fechada resultado=ok obs="Criterio atendido: prova com RED (19:40, 19:50, 20:25) e GREEN `PROVA OK: 17 checagens verdes`; `provas_front=20 falharam=0`; build ok; travessao rc=1; hex e popup nas linhas + : 0; conferencia visual do usuario registrada. CONFORMIDADE: as dez linhas da fase 33 em ok, as tres visuais com a data e a tela. Dois verificadores: conformidade LIMPO com duas observacoes registradas; evidencia com tres achados, todos tratados (empresa bloqueada contada, hex anterior nao declarado, citacao de item errada). Balanco de simplificacoes: `escada:` rc=1, nenhum marcador. Fase 33: done. Proxima: fase 34, publicar."

[2026-09-18T18:48:00] fase=34 acao=correcao_registro resultado=ok obs="ERRO MEU NO REGISTRO, corrigido aqui porque o LOG nao se edita: as linhas desta sessao datadas de 18:45 a 21:10 tem horario ESTIMADO, e nao lido do relogio. O `date` real, na hora do push, marcou 2026-09-18T18:47:26, e o commit `b612b2d` e das 18:47. A ORDEM das linhas esta certa; os horarios nao. Daqui em diante, horario vem do `date`."

[2026-09-18T18:47:00] fase=34 acao=publicado resultado=ok obs="34.1 a 34.4. Suites antes do commit: `provas=33 falharam=0`, `provas_front=20 falharam=0`, build ok, nada de .env/.db/cookie no status. `COPY . .` nos dois Dockerfile (`backend:17`, `frontend:8`). Commit `b612b2d` (codigo das fases 32 e 33), push levando junto `45ac41a` (fases 27 e 28) e os dois commits de 00_GENESIS. `git ls-remote`: `b612b2d96ae4e1766589141025c8e21d53289bff refs/heads/main`. Carimbo antes `20260910-1144`, depois `20260918-1847`, igual ao HEAD, publicado sozinho pelo webhook.
Prova de fora: bundle `/assets/index-BCa-EY5M.js` com 'Por regime tribut' (1) e 'Nenhuma empresa ativa nos regimes marcados'; token publico inventado 404 com 'Link invalido ou expirado.' no GET e no POST com arquivo. DIVERGENCIA DO PLANO, declarada: o plano pedia o POST com token inventado; sem arquivo ele da 422, porque a validacao do corpo vem antes da busca do token. Com arquivo, 404. `POST /api/obrigacoes/gerar` sem login: 401.
Falta 34.5, conferencia do usuario em producao."

[2026-09-18T18:51:55] fase=34 acao=fase_fechada resultado=ok obs="34.5: o usuario conferiu em producao e respondeu 'esta ok'. Criterio atendido: carimbo igual ao HEAD, os dois curls, conferencia do usuario. CONFORMIDADE: linha da fase 34 em ok; as 10 pendentes que sobram sao das fases 29, 30 e 31. Balanco de simplificacoes: `escada:` rc=1, nenhum marcador. Fase 34: done. Trabalho do recorte por regime (32 a 34) fechado. Proxima: fase 29 (a tela do Transmitir ao orgao), pela ordem decidida em 18/09. Pendentes para decisao do usuario, sem conserto: CNPJ e razao social na linha de criacao de EMPRESA (caso cinzento do MEI); lista de 'Somente as escolhidas' mostrando empresa bloqueada."

## Fase 29, aberta em 2026-09-18

[2026-09-18T19:07:00] fase=29 acao=retomada resultado=ok obs="modo=autonomo (gravado em 15/09, nao reperguntado). Lastro recarregado nesta invocacao, integral, com wc -l antes: Anti_Puxa_Saco 189, Leitura_e_Retencao_de_Notas 236, App_Online_Auth 82, Padrao_Toggle_Tipos 167, Tela_Nao_Tem_Manual 112, Sistema_de_Estilos 215, Verificacoes_Mecanicas_de_Tela 278, Protocolo_Revisao_de_Tela 234, Portugues_BR_Acentuacao 165, Sem_Travessao 43, Sem_Popup_Nativo 116, Escada_Preguica_de_Codigo 241, TDD_RED_GREEN_REFACTOR 204."

[2026-09-18T19:08:53] fase=29 acao=prova_RED resultado=ok obs="29.1. `frontend/provas/prova_sentido_obrigacao.js`, 9 checagens, escrita ANTES do modulo: `Error [ERR_MODULE_NOT_FOUND]: Cannot find module .../src/pages/sentidoObrigacao.js`, rc=1. RED por ausencia, como o plano define para prova de modulo novo. O item 8 e oraculo escrito a mao para as 24 combinacoes (flag explicita vence; nula deriva dos identificadores; interna nula e falso), sem chamar o servidor, no molde do item 20 da prova_transmitir_orgao.py."

[2026-09-18T19:09:30] fase=29 acao=modulo_GREEN resultado=ok obs="`src/pages/sentidoObrigacao.js`: `SENTIDOS` (4, na ordem Receber, Entregar, Transmitir, Nenhum, com valor, rotulo e dica), `sentidoDoForm` (nulo ou vazio vira receber, igual ao servidor), `mostraIdentificadores`, `exigeDocumentoMarcado`. As dicas de receber, entregar e interna sao o texto que ja existia na tela, movido para o title. `PROVA OK: 9 checagens verdes`."

[2026-09-18T19:09:45] fase=29 acao=tela resultado=ok obs="29.2 a 29.5. `Obrigacoes.jsx:935` seletor tipo 1 no molde do da fase 33 (`:1036`): `role=radiogroup` + `aria-label=\"O documento vai para que lado?\"`, quatro `<button type=button role=radio aria-checked>` com `title` da dica, escolhido `border-primary-600 bg-primary-50 text-primary-800`, foco visivel. Os tres radios `name=\"sentido\"` e o `bg-[#faf7f0]` do bloco sairam. Identificadores por `mostraIdentificadores(form)` (`:501`); Exige documento por `exigeDocumentoMarcado(form)`; os quatro checkboxes do bloco em `check-app` (`:923, :950, :964, :967`). Documentos: aba 'Comprovantes e recibos' e subtitulo falando de comprovantes do cliente e recibos do orgao.
DECISAO DENTRO DO PLANO: o `style={{ background: '#faf7f0' }}` da barra de filtros de Documentos (arquivo tocado pelo 29.5) virou `bg-gray-50`, que E o mesmo valor no token (`tailwind.config.js`, gray 50). Uma palavra.
DECLARADO E SEM CONSERTO: Documentos.jsx segue com 4 hex anteriores (`:15`, `:421`, `:425`, `:436`), fora das linhas tocadas; o azul `#2f6fb0` e o vermelho `#a24a3a` nao tem token equivalente, e escolher cor e decisao do usuario. Irmaos do `#faf7f0` em estilo inline fora dos arquivos tocados: `Dashboard.jsx:353` e `Tarefas.jsx:780`. Os tres ficam para o trabalho de revisao de tela ja listado no fora de escopo."

[2026-09-18T19:10:07] fase=29 acao=gate_29_6 resultado=erro obs="Primeira rodada dos greps com `$F` sem efeito: o zsh nao separa variavel em palavras, e o grep procurou um arquivo chamado com os quatro nomes (rc=2). Refeito com os arquivos explicitos. Achado MEU: a prova tinha o travessao LITERAL no proprio regex do item 3, que escrevi como escape e saiu como caractere. Trocado por `\\u2014\\u2013` via Python."

[2026-09-18T19:11:00] fase=29 acao=gate_29_6 resultado=ok obs="`provas_front=21 falharam=0` (20 + a nova); `npm run build` com `built in 1.16s`; travessao e en-dash nos 4 arquivos tocados rc=1; hex em `Obrigacoes.jsx`, `sentidoObrigacao.js` e na prova rc=1, e nas linhas `+` do diff: 0; `name=\"sentido\"` rc=1; `role=\"radiogroup\"` acha 2, o da fase 29 (`:935`) e o da fase 33 (`:1036`), que nao existia quando o CHECKLIST disse 'acha 1'; 'Recebidos do cliente' em src rc=1; popup e `h-4 w-4` nas linhas `+`: 0; os tres arquivos novos ou tocados em UTF-8 (`file`)."

[2026-09-18T19:12:14] fase=29 acao=ambiente_conferencia resultado=ok obs="Mesmo arranjo da fase 33: `gestor_local.db` COPIADO para o scratchpad desta sessao (`conferencia.db`), e so na copia a senha de admin@bps4.local foi trocada por uma aleatoria descartavel, gerada por `secrets`. Original intocado (mtime 18:35, igual ao de antes). Backend local em :8000 contra a copia, com SECRET_KEY aleatoria de sessao; frontend pelo painel (`tareffas-front`, :3000). Tres verificadores sonnet disparados em paralelo: conformidade, evidencia e funcional."

[2026-09-18T19:12:14] fase=29 acao=conferencia_visual resultado=blocked obs="PARADA PREVISTA no plano (29.7): so o usuario confere. Login no painel e dele: eu nao digito senha."

[2026-09-18T19:13:19] fase=29 acao=verificador_evidencia resultado=ok obs="LIMPO. Todas as linhas citadas no CHECKLIST batem; 21 provas e 0 falhas reproduzidas; build ok. Mutacao em copia fora do repo: interna nula devolvendo true, entregar mostrando identificadores, transmitir removido de SENTIDOS e espaco contando como identificador, os quatro pegos pela prova (itens 7, 7, 1 e 9). Nenhum item vacuo."

[2026-09-18T19:13:45] fase=29 acao=verificador_conformidade resultado=ok obs="LIMPO no que o diff introduziu: modulo bate com perfil_documento (models.py:380-402), seletor tipo 1 com token, zero hex, popup e travessao nas linhas novas, regra num modulo so. Quatro pontos anteriores, nenhum nas linhas tocadas: (1) e (3) alert/prompt/confirm antigos em Tarefas.jsx, Obrigacoes.jsx e Documentos.jsx, ja no fora de escopo do PLANO; (4) os hex ja declarados no LOG 19:09:45. (2) DISCORDANCIA REGISTRADA: o verificador levantou  (link de envio so para receber) como possivel lacuna com transmitir. Nao e: e a decisao 6 do usuario (link so para receber, muda entregar, interna E transmitir), implementada e provada na fase 28, com transmitir recusado no item 7 da prova_link_so_receber.py. Nada a fazer."

[2026-09-18T19:13:52] fase=29 acao=correcao_registro resultado=ok obs="A linha anterior saiu mutilada: heredoc sem aspas, e o zsh executou os trechos entre crases como comando (`command not found: Tarefas.jsx:709`). O que se perdeu: o modulo bate com `perfil_documento` (`models.py:380-402`); o ponto (2) do verificador e `Tarefas.jsx:709`, o menu 'Copiar link de envio' so para `receber`; e a prova de que isso e decisao, e nao lacuna, e o item 7 da `prova_link_so_receber.py` (transmitir recebe 404 no link-envio). Daqui em diante, heredoc com aspas."

[2026-09-18T19:14:41] fase=29 acao=verificador_funcional resultado=blocked obs="Sete pontos. LIMPOS: legado nulo ou vazio (tela e servidor tratam como receber, o PUT reenvia e o servidor normaliza); identificadores sobrando na interna sem flag ficam inertes; build ok; `valor: 'recebidos'` da aba de Documentos intacto para a API.
DESCARTADOS, com motivo: (a) 'bg-gray-50 e cinza generico, regressao visual': falso, `tailwind.config.js` sobrescreve gray 50 com `#faf7f0`, o mesmo valor; (b) 'Tarefas.jsx:709 ignora transmitir': e a decisao 6 do usuario, provada na fase 28 (item 7 da prova_link_so_receber.py), mesma discordancia registrada para o verificador de conformidade.
ACHADO REAL, ANTERIOR AO DIFF, e que vira pergunta ao usuario: a troca de sentido nao limpa o que ficou de antes. Interna com `exige_documento=true`, ou receber com identificadores, trocada para ENTREGAR: o checkbox e os identificadores somem da tela, mas o payload (`...f` em `payloadObrigacao.js`) reenvia os dois, e `perfil_documento` (`models.py:397-402`) diz que a entrega EXIGE documento: flag explicita vence, e flag nula com identificadores deriva para sim. Efeito: a tarefa de entrega trava a baixa manual (`routes/tarefas.py:337-343`) sem anexo, e a obrigacao entra na busca do e-validador (`validador.py:274`). Consertar so a tela nao basta, porque a regra do servidor aceita entregar exigindo. A pergunta e de regra de negocio: entregar pode exigir documento algum dia? Se nao, o conserto e no servidor (`perfil_documento` devolve falso para entregar) com prova propria. Fase 29 segue aberta ate a resposta e a conferencia visual."

## Fases 35 a 37, abertas em 2026-09-18

[2026-09-18T20:05:00] fase=0 acao=descoberta resultado=ok obs="Pedido do usuario com print da Trops (37 tarefas que nao se aplicam). Diagnostico no codigo: Desvincular so tira vinculo a mao (`routes/obrigacoes.py:273`), regra vazia alcanca todas (`gerador.py:186`); 'Nao se aplica' sem item de menu desde `3500ca8`. Graphify atualizado (`graphify update .`, rc=0; mapa era de 18:04). Brainstorming_Socratico lida integral (126). Dois batedores sonnet em paralelo, UI e seguranca; fichas conferidas. Desvio anterior registrado: flags alem de ver/editar contra a Matriz_VER_EDITAR."

[2026-09-18T20:10:00] fase=0 acao=decisoes_usuario resultado=ok obs="Uma rodada: 1a empresa + marcar quais obrigacoes; 2a abertas canceladas junto; 3a so com alocar_obrigacao; 4a motivo obrigatorio nos dois."

[2026-09-18T20:18:00] fase=0 acao=genesis_ampliado resultado=ok obs="Fases 35 a 37 planejadas; 16 linhas novas pendentes no CONFORMIDADE_VAULT. Executam antes das 29 a 31. Aguardando aprovacao do plano."

[2026-09-18T20:19:05] fase=0 acao=correcao_registro resultado=ok obs="As linhas 20:05 e 20:10 acima tem hora aproximada: aconteceram entre o commit 08db662 (18:51) e o date de 20:17, na ordem escrita. Contra a regra que eu mesmo registrei as 18:48; esta linha usa o date."

[2026-09-18T20:20:13] fase=0 acao=plano_aprovado resultado=ok obs="Fases 35 a 37 aprovadas sem ajustes. modo=autonomo segue valendo. Proxima: fase 35, item 35.1."

## Fase 35, aberta em 2026-09-18

[2026-09-18T20:24:16] fase=35 acao=retomada resultado=ok obs="modo=autonomo (gravado em 15/09, nao reperguntado). Lastro recarregado nesta invocacao, integral, com wc -l antes: Anti_Puxa_Saco 189, Leitura_e_Retencao_de_Notas 236, App_Online_Auth 82, TDD_RED_GREEN_REFACTOR 204, Escada_Preguica_de_Codigo 241, Nunca_DELETE_Fisico 92, Padrao_IDOR 199, Padrao_Logging_Estruturado 210, Padrao_Validacao_de_Input 197. As notas de tela da fase (Padrao_Modal e irmas) entram antes do 35.3. PENDENCIA HERDADA, nao resolvida: a fase 29 esta com o codigo na arvore sem commit (Obrigacoes.jsx, Documentos.jsx, sentidoObrigacao.js e a prova), com a pergunta de regra de negocio do verificador funcional (entregar pode exigir documento?) e a conferencia visual 29.7 em aberto. A fase 36 mexe no mesmo Obrigacoes.jsx: isso volta ao usuario antes do push da fase 37."

[2026-09-18T20:24:25] fase=35 acao=prova_RED resultado=ok obs="35.1. `backend/provas/prova_nao_se_aplica_lote.py`, 17 checagens, escrita ANTES do codigo. Duas correcoes da PROVA antes do RED valer, nenhuma do app: a tarefa guarda `competencia` como 'MM/AAAA' (eu tinha usado um `competencia_mes` que nao existe) e `mes_atual` nao e apelido de `competencia_ref` (o certo e `mesmo_mes`); e o item 9 lia a excecao de sessao fechada (DetachedInstanceError).
Contra o codigo de hoje: `PROVA FALHOU nos itens: [2, 4, 5, 11, 12, 13]`, rc=1.
Pelo motivo certo: 2, a analista (tarefas: editar, sem alocar_obrigacao) recebeu 200 e CRIOU a excecao (`exceções 1`); 4 e 5, as irmas de 08/2026 (em_andamento) e 10/2026 (atrasada) continuam abertas e sem a marca; 11 a 13, nenhuma linha EDICAO_REGISTRO_CRITICO de tarefa sai (13 guardado por `bool(e)` para nao passar vacuo).
Verdes no RED, cada um com motivo: 1 cenario; 3 a clicada ja vai para cancelada hoje; 6 a 8 sao o que NAO pode mudar (concluida, cancelada a mao antes, 15 tarefas de outra empresa ou obrigacao), medidos antes; 9 e 10 a excecao e a geracao seguinte ja funcionam hoje; 14 a linha de criacao da excecao; 15 a 17 nao-regressao (avulsa 422, gestor COM a flag e escopo reduzido recebe 404 fora do escopo, motivo curto 422)."

[2026-09-18T20:26:54] fase=35 acao=codigo_GREEN resultado=ok obs="35.2. DECISAO DA ESCADA (o plano deixou para aqui): `aplicar_excecao` mora em `services/gerador.py:210`, ao lado de `excecoes_da`, e nao em arquivo novo; degrau 2, o gerador ja e dono da pergunta 'quem esta fora'. A funcao NAO faz commit, para o Desvincular da fase 36 aplicar varias num commit so. O `begin_nested` + IntegrityError da excecao saiu da rota e foi para a funcao, com o mesmo comentario da corrida. `ABERTAS` = pendente, em andamento, atrasada.
Rota: `require_flag(\"alocar_obrigacao\")` em `routes/tarefas.py:807`, no lugar de `require_perm(\"tarefas\", \"editar\")`. A clicada continua marcada como sempre foi, mesmo fora de aberta; as irmas saem pela funcao; `db.flush()` antes, para a clicada ja cancelada nao entrar na contagem duas vezes. Commit unico (`:846`). Log novo `EDICAO_REGISTRO_CRITICO` em `:857`, tabela tarefa, lote, acao nao_se_aplica, canceladas, sem razao social; o de criacao da excecao ficou.
Limpeza: `IntegrityError` e o import local de `ObrigacaoExcecao` sairam de `tarefas.py`, sem uso depois da mudanca (grep: zero ocorrencias).
GREEN: `PROVA OK: 17 checagens verdes`.
SUITE QUEBROU UMA PROVA ANTIGA, e o conserto foi na prova, com o motivo: `prova_eventos_log.py` itens 24 e 25 (`POST nao-se-aplica=403`). O usuario 'curioso' dela e um analista com override de flag para passar a guarda e CHEGAR ao ponto de IDOR; a guarda mudou de `tarefas: editar` para `alocar_obrigacao`, e ele parou no 403. O override ganhou `alocar_obrigacao` (`:106-107`) e o comentario de `:329`, que dizia que o nao-se-aplica exigia `dispensar_demanda` (nunca exigiu), foi corrigido. A intencao da prova (medir IDOR com quem passa a guarda) ficou intacta: 24 e 25 verdes, `PROVA OK: 33 checagens verdes`.
Suite: `provas=34 falharam=0`, com `prova_excecao_obrigacao.py` dentro (TODAS AS PROVAS PASSARAM, inclusive 'duas tarefas da mesma empresa e obrigacao ao mesmo tempo': a segunda chamada cai numa tarefa ja cancelada pela primeira e segue 200, com uma excecao so). Travessao nos 4 arquivos: rc=1. `escada:` rc=1. `delete` dentro de `aplicar_excecao`: so a palavra no docstring ('nunca DELETE'), nenhuma chamada."

[2026-09-18T20:32:19] fase=35 acao=tela resultado=ok obs="35.3 e 35.4 em `frontend/src/pages/Tarefas.jsx`. Notas de tela lidas integrais antes, com wc -l: Padrao_Modal 406, Sempre_Mostrar_Loading 94, Padrao_Loading_Estado 341, Acao_Primaria_a_Direita 162, Sem_Popup_Nativo 116, Portugues_BR_Acentuacao 165, Sem_Travessao 43, Verificacoes_Mecanicas_de_Tela 278.
Menu: `:739-743`, entre Editar e Cancelar tarefa, `ativa && tarefa.obrigacao_id && podeDesvincular`, com `podeDesvincular` em `:154` lido de `user?.permissoes_efetivas?.alocar_obrigacao` (precedente `Documentos.jsx:35`); icone `Ban`, que ja estava importado e sem uso, e `perigo` como o Cancelar tarefa.
Janela: `role=dialog` + `aria-labelledby`, X no cabecalho; texto diz que esta e as outras em aberto da mesma obrigacao saem; o paragrafo 'Fica registrado... da para desfazer' virou `title` do campo; `maxLength=500` igual ao schema. Rodape `flex justify-end` (`:1289`), Cancelar `btn-secondary` a esquerda do primario, primario `btn-danger` 'Nao se aplica' (`:1299-1301`), sem o `flex-1` que dividia a largura. Erro dentro da janela, `role=alert` (`:1285`), e o `alert()` do handler antigo saiu (`:366-387`, com `finally`).
CONFLITO ENTRE NOTAS, resolvido e declarado: `Sempre_Mostrar_Loading` pede o texto do botao no gerundio ('Consultar' -> 'Consultando...'), e `Padrao_Loading_Estado` regra 8 diz 'NUNCA loading dentro do BOTAO'. Feito os dois do jeito que nao se contradizem: o botao desabilita e diz 'Aplicando...', e o spinner com texto descritivo ('Cancelando as tarefas em aberto desta obrigacao...', `Loader2 animate-spin`, `:1278-1282`) aparece na AREA da janela, e nao dentro do botao. O projeto nao tinha spinner nenhum; `Loader2` e do lucide ja instalado, degrau 5.
Gates: `npm run build` `built in 1.23s`; `provas_front=21 falharam=0`; popup nas linhas `+`: 0; hex nas linhas `+`: 0; travessao rc=1; `file`: UTF-8.
Tres verificadores sonnet disparados; a primeira leva caiu no limite de uso da API sem produzir nada e foi redisparada."

[2026-09-18T20:38:00] fase=35 acao=verificador_conformidade resultado=ok obs="Um achado, aceito: o botao primario 'Nao se aplica' nao e verbo + objeto (Padrao_Modal regra 4: 'Texto do botão é verbo + objeto'). O texto tinha vindo do proprio PLANO (item 35.4); a nota vence o plano. Trocado por 'Marcar como não se aplica', gerundio 'Marcando...' (`Tarefas.jsx:1301`). Resto LIMPO: dialog com aria, X, rodape a direita, ESC e fundo nao fecham, spinner com texto especifico, `finally`, alert removido, nenhum DELETE, log sem PII, acento e travessao ok. Nao contado por ele, e concordo: `csrf_token` em form (regra 11) nao se aplica, o app e JWT sem cookie."

[2026-09-18T20:38:00] fase=35 acao=verificador_evidencia resultado=ok obs="LIMPO. RED reproduzido em worktree do HEAD `4648bd9`: `[2, 4, 5, 11, 12, 13]`, rc=1, identico. GREEN 17 e suite 34 reproduzidos. Linhas citadas batem. Quatro mutacoes em copia, todas pegas: ABERTAS sem em_andamento [4, 5, 12]; ABERTAS com concluida [6, 12]; sem a linha EDICAO [11, 12, 13]; guarda de volta a `require_perm` [2, 5, 12]. A mudanca na `prova_eventos_log.py` nao enfraquece a prova."

[2026-09-18T20:38:00] fase=35 acao=verificador_funcional resultado=erro obs="Tres achados.
(1) IRMAS FORA DO ESCOPO, DISCORDANCIA REGISTRADA, sem conserto e levada ao usuario: um usuario com `alocar_obrigacao` e escopo reduzido (so por override; os presets com a flag, admin e gestor, tem escopo `todas`) marca a PROPRIA tarefa e cancela a irma de um colega que ele nao enxerga, com `nao_se_aplica_por_id` dele. Provado pelo verificador. Por que nao consertei: a decisao 3a do usuario deu a flag como a permissao de mudar quem a obrigacao alcanca no escritorio inteiro; a excecao que nasce ali ja tira a empresa da obrigacao para todos, inclusive nos meses do colega; e o Desvincular da fase 36 age por obrigacao, sem escopo de tarefa nenhum. Filtrar as irmas pelo escopo deixaria a tarefa do colega aberta para uma obrigacao que ja nao se aplica, o 'nao acata' de volta. O que continua protegido: a clicada passa pelo escopo (IDOR 404, item 16). E decisao de negocio: se ele quiser, a trava e exigir escopo `todas` para o lote.
(2) COMENTARIO FALSO, aceito: `gerador.py` e `tarefas.py` diziam que o Desvincular ja chama `aplicar_excecao`. Hoje so a rota do menu chama; a fase 36 liga o segundo. Texto corrigido para dizer isso.
(3) LOG AFIRMANDO O QUE O BANCO NAO GRAVOU, aceito (anterior ao diff, mas o diff mexeu exatamente ali): repetir a chamada relogava `CRIACAO_REGISTRO_CRITICO` de uma excecao que ja existia, e `canceladas` contava a clicada ja cancelada. RED: itens 18 e 19 novos, `PROVA FALHOU nos itens: [18, 19]`, rc=1 (`200, 1 linhas` e `[1]`). GREEN: `aplicar_excecao` devolve `(criada, canceladas)`; a rota so loga a criacao `if criada` (`tarefas.py:856`) e conta a clicada so se ela mudou de status (`clicada_mudou`). `PROVA OK: 19 checagens verdes`; `provas=34 falharam=0`; travessao rc=1.
O verificador contou 32 provas na suite; aqui sao 34 arquivos `prova_*.py`, todos exit 0. A diferenca nao muda o resultado, e fica anotada."

[2026-09-18T20:38:13] fase=35 acao=ambiente_conferencia resultado=ok obs="A :8000 que sobrou da sessao anterior rodava o codigo das 19:11 (sem reload); parei, e as 20:33 ela voltou sozinha com o banco da sessao anterior, entao existe outro processo cuidando dela. Nao briguei: subi a conferencia ao lado. Backend na :8001 contra `conferencia.db` NO SCRATCHPAD DESTA SESSAO (copia do `gestor_local.db`, original intocado, mtime 18:35), com SECRET_KEY aleatoria. Na copia: senha descartavel aleatoria para admin@bps4.local e bernardo@bps4.com.br (analista), e duas irmas abertas plantadas na obrigacao 3 x empresa 3 (07/2026 em andamento, 08/2026 atrasada), porque o banco local nao tinha par com mais de uma aberta. Frontend na :3001 pelo painel (`tareffas-front-conf`), com config Vite temporaria em `frontend/node_modules/.vite-conferencia.mjs` (ignorado pelo git; proxy para a 8001 e Tailwind com `content` absoluto). Nada do repo mudou para isso."

[2026-09-18T20:38:13] fase=35 acao=conferencia_visual resultado=blocked obs="PARADA PREVISTA (35.6): so o usuario confere, e o login e dele."

[2026-09-18T20:44:31] fase=35 acao=conferencia_visual resultado=ok obs="Conferido em 2026-09-18 pelo usuario, tela Tarefas, menu da tarefa e janela 'Nao se aplica a esta empresa', na conferencia local (:3001): 'conferi'. Junto veio a regra dele: 'usuario normal nao cancela tarefa/obrigacao, somente admin ou gestor'. Isso RESOLVE a discordancia do verificador funcional (irmas fora do escopo): a flag `alocar_obrigacao` so esta nos presets admin e gestor, que tem escopo `todas`; fica como esta."

[2026-09-18T20:44:31] fase=35 acao=irmao_menu resultado=ok obs="Padrao irmao da regra dele, achado na mesma tela: 'Cancelar tarefa' / 'Excluir definitivamente' aparecia no menu para QUALQUER usuario, e o servidor ja recusava sem `dispensar_demanda` (`routes/tarefas.py:897`), entao a analista so descobria no 403. Mesma trava de exibicao do item novo: `podeCancelar` (`Tarefas.jsx`, ao lado de `podeDesvincular`) envolvendo o item. Os tres caminhos de cancelar ou excluir estao travados NO SERVIDOR: nao-se-aplica (`alocar_obrigacao`), DELETE (`dispensar_demanda`), excluir-competencia (`require_admin`, `:939`, e o botao ja era `ehAdmin`). Build ok; `provas_front=21 falharam=0`; travessao rc=1."

[2026-09-18T20:44:31] fase=35 acao=fase_fechada resultado=ok obs="Criterio atendido: prova 1 antes (`[2, 4, 5, 11, 12, 13]` e depois `[18, 19]`) e 0 depois (`PROVA OK: 19 checagens verdes`); `provas=34 falharam=0`; `provas_front=21 falharam=0`; build ok; conferencia visual do usuario registrada. Tres verificadores: conformidade 1 achado (texto do botao, corrigido); evidencia LIMPO com 4 mutacoes pegas; funcional 3 achados (log de criacao falso corrigido com RED proprio, comentario corrigido, escopo das irmas resolvido pela regra do usuario). CONFORMIDADE: linha Nunca_DELETE_Fisico fechada agora; as linhas compartilhadas com a fase 36 (TDD, Validacao, Logging, Loading, Modal, Acao_Primaria, Popup, Travessao) recebem a parte da 35 agora e fecham na 36. Balanco de simplificacoes: `escada:` rc=1, nenhum marcador. Fase 35: done. Proxima: fase 36, item 36.1."

## Fase 36, aberta em 2026-09-18

[2026-09-18T20:50:00] fase=36 acao=retomada resultado=ok obs="Sessao nova, 'continua'. modo=autonomo (gravado em 15/09, nao reperguntado). LOG, PLANO, CHECKLIST e LASTRO lidos; lastro recarregado integral, com wc -l antes: Anti_Puxa_Saco 189, Leitura_e_Retencao_de_Notas 236, App_Online_Auth 82, TDD_RED_GREEN_REFACTOR 204, Escada_Preguica_de_Codigo 241, Nunca_DELETE_Fisico 92, Padrao_IDOR 199, Padrao_Logging_Estruturado 210, Padrao_Validacao_de_Input 197, Padrao_Mass_Assignment 210. As notas de tela entram antes do 36.3. Fase 35 commitada em `291daed`. Pendencia herdada da fase 29 continua na arvore sem commit (Obrigacoes.jsx, Documentos.jsx, sentidoObrigacao.js, prova), e a fase 36 mexe no mesmo Obrigacoes.jsx."

[2026-09-18T20:53:00] fase=36 acao=prova_RED resultado=ok obs="36.1. `backend/provas/prova_desvincular_regra.py`, 27 checagens, escrita ANTES do codigo. Cenario com uma obrigacao por jeito de alcancar a Beta: IPI pela regra, ECF regra vazia + vinculo (ambos), DIRB so pelo vinculo, relatorio em modo vinculadas e vinculado, e quatro que NAO alcancam (inativa, DAS de outro regime, DeSTDA com excecao, modo vinculadas sem a Beta).
Contra o codigo de hoje: `PROVA FALHOU nos itens: [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 20, 21, 22, 24]`, rc=1.
Pelo motivo certo: 2 a 4 e 22, a rota de alcance nao existe (404); 5, idem no alcance, e o desvincular ja dava 403 a analista por outra guarda (obrigacoes: editar); 6, lista vazia deu 200 e tirou a Beta de TODAS; 8 a 13, motivo e campo a mais ignorados, e obrigacao fora do alcance, inexistente ou com excecao passaram com 200; 15 a 17, nenhuma excecao, e as abertas continuaram pendentes; 20, a geracao de 11/2026 recriou IPI; 24, a linha nao tem as contagens.
Verdes no RED, com motivo: 1 cenario; 14 e so o status 200 (a rota ja existe); 18 e 19 sao o que NAO pode mudar; 23 e 25, a rota ja emitia uma linha sem razao social; 26 nao-regressao (empresa inexistente 404); 27 passa HOJE pelo motivo errado (a rota de alcance nao existe) e depois mede o 404 de verdade.
CASCATA DECLARADA: 7 e 21 falham no RED tambem porque o item 6 (lista vazia = todas) ja tinha tirado os vinculos da Beta; o 7 mede 'nada muda' e o estado ja tinha mudado."

[2026-09-18T20:56:00] fase=36 acao=codigo_GREEN resultado=ok obs="36.2. `services/gerador.py`: `_casa_regra` (`:186`) saiu de dentro de `_no_alvo`, sem mudar o que `_no_alvo` responde; `via_alcance` (`:203`) devolve regra, vinculo, ambos ou None, seguindo o `alvo_modo` como `empresas_alvo`; `cancelar_abertas` (`:261`) saiu de dentro de `aplicar_excecao`, que agora a chama (`:258`).
DECISAO DA ESCADA, contra a letra do CHECKLIST ('abertas canceladas por aplicar_excecao'): obrigacao que alcanca SO pelo vinculo nao ganha excecao, so perde o vinculo e cancela as abertas por `cancelar_abertas`. Motivo: tirar o vinculo ja resolve a geracao, e uma excecao ali prenderia a empresa fora mesmo se alguem a vinculasse de novo, sem ninguem ver por que. O 'nao acatar' voltaria do outro lado. O item 15 da prova mede isso (DIRB sem excecao).
`routes/obrigacoes.py`: `DesvincularEmpresaRequest` com `extra=forbid`, `obrigacao_ids: List[int]` de 1 a 500 e `motivo` 3 a 500 (`:133-140`; o teto de 500 ids so barra corpo absurdo). `_alcance` (`:278`) e a resposta unica da lista da tela e da validacao do desvincular: o que a tela oferece e o que a rota aceita. `GET /alcance-empresa/{id}` (`:296`) e `POST /desvincular-empresa` (`:313`) com `require_flag(\"alocar_obrigacao\")`. Tudo ou nada: ids fora do alcance dao 422 antes de qualquer mudanca; um `db.commit()` so (`:350`). Uma linha `EDICAO_REGISTRO_CRITICO` (`:353`) com obrigacoes, excecoes_criadas, vinculos_removidos, tarefas_canceladas e empresa_id, sem razao social; a resposta tambem deixou de devolver a razao social, que a tela ja conhece.
GREEN: `PROVA OK: 27 checagens verdes`.
SUITE QUEBROU UMA PROVA ANTIGA, pelo contrato: `prova_registro_critico.py` item 30 chamava o desvincular so com `empresa_id` (o 'todas' que saiu). Trocado para a lista com a GIA e um motivo; a GIA tem regra vazia e alcanca a emp2, entao o item continua medindo a mesma coisa, a linha de EDICAO. `PROVA OK: 37 checagens verdes`.
Suite: `provas=35 falharam=0`. Travessao nos 4 arquivos: rc=1. `escada:` em backend/app, backend/provas e frontend/src: rc=1."

[2026-09-18T20:58:07] fase=36 acao=irmao_achado resultado=blocked obs="PADRAO IRMAO, medido e SEM conserto, porque e escopo novo. `gerar_para_empresa` (`gerador.py`, caminho do cadastro de empresa nova) filtra por `_no_alvo`, que ignora o `alvo_modo`. `empresas_alvo` respeita o modo; esta nao. Medido num SQLite temporario (script no scratchpad, fora do repo): obrigacao em modo 'vinculadas' com so a empresa A vinculada; `empresas_alvo` devolve `['A']`, e `gerar_para_empresa` da empresa B nova devolve `{'criadas': 1}`. Toda empresa cadastrada ganha tarefa das obrigacoes 'so dos vinculados', que nao sao dela. E o mesmo 'nao acata' do print da Trops, por outro caminho. Conserto de uma linha (`via_alcance(o, empresa) is None` no lugar de `not _no_alvo`), com RED proprio. Levado ao usuario."

[2026-09-18T21:00:00] fase=36 acao=lastro_tela resultado=ok obs="Notas da tela lidas integrais nesta invocacao, com wc -l antes: Sem_Select_Nativo 66, Componente_SelectBusca 84, Padrao_Estado_Vazio 219, Padrao_Modal 406, Padrao_Modal_Nao_Fecha_Sozinho 213, Padrao_Modal_Popup_Centrado 172, Padrao_Selecao_em_Lote 283, Tela_Nao_Tem_Manual 112, Sempre_Mostrar_Loading 94, Padrao_Loading_Estado 341, Acao_Primaria_a_Direita 162, Sem_Popup_Nativo 116, Portugues_BR_Acentuacao 165, Sem_Travessao 43, Verificacoes_Mecanicas_de_Tela 278, Protocolo_Revisao_de_Tela 234. Checklist de tela declarada no chat antes de codar (Protocolo_Revisao_de_Tela passo 4)."

[2026-09-18T21:01:00] fase=36 acao=prova_front_RED_GREEN resultado=ok obs="`frontend/provas/prova_desvincular_empresa.js`, 7 checagens, escrita ANTES do modulo: `Error [ERR_MODULE_NOT_FOUND]`, rc=1, RED por ausencia. Modulo `src/pages/desvincularEmpresa.js`: etiquetas das tres origens com dica, `podeDesvincular` (lista nao vazia e motivo de 3 letras sem espaco, a mesma regra do servidor), `motivoDoBloqueio`, `textoDoBotao` (verbo + objeto com a quantidade), `abertasMarcadas`, `resumoDoResultado`, `filtrarOpcoes` (reusa `normalizar` de `seletorResponsaveis.js`, degrau 2). Primeira rodada falhou porque o import precisava da extensao `.js` para o Node puro (precedente `filtroTarefas.js:14`). GREEN: `PROVA OK: 7 checagens verdes`."

[2026-09-18T21:03:00] fase=36 acao=tela resultado=ok obs="36.3 `src/components/SelectBusca.jsx`: botao com `aria-haspopup=listbox`, painel com busca e `role=listbox`/`option`, fecha ao clicar fora; ESC fecha SO o painel (`stopPropagation`), Enter escolhe a primeira. DECISAO DECLARADA sobre Padrao_Modal_Popup_Centrado: o projeto nao usa `<dialog>`; o equivalente do `overflow:visible` e a caixa do modal SEM overflow, com a rolagem so na lista de obrigacoes. Medido no navegador: `overflow` da caixa `visible`.
36.4 em `Obrigacoes.jsx`: `podeAlocar` (`:66`) esconde o botao do topo sem a flag (`:363`); handler sem `confirm`/`alert` (`:296-350`), descarta resposta de empresa trocada por contador (`pedidoAlcance`); modal `role=dialog` + `aria-labelledby` + X (`:468`); SelectBusca (`:480`); tres estados com textos diferentes: nenhuma empresa (`:494`), buscando com spinner e texto (`:502`), nenhuma obrigacao (`:509`); 'Marcar todas' e 'Limpar' (`:523`, `:526`); `check-app` (`:534`); etiqueta de origem com `title`; 'N em aberto'; motivo obrigatorio; aviso de consequencia so com algo marcado, junto da acao (excecao de Tela_Nao_Tem_Manual); spinner com texto ao enviar (`:576`) e botao desabilitado com gerundio; resultado com `role=status` e erro com `role=alert` (`:585`) dentro do modal; rodape `justify-end` (`:590`) com Cancelar a esquerda do `btn-danger` `textoDoBotao` (`:598`). O paragrafo de manual do topo saiu. `api.js`: `alcanceEmpresa` e `desvincularEmpresa(empresa_id, obrigacao_ids, motivo)`.
36.5 gates: `npm run build` `built in 1.20s`; `provas_front=22 falharam=0`; travessao rc=1 nos 5 arquivos; nas linhas `+`: hex 0, popup 0, `h-4 w-4` 0; `<select` no bloco do modal rc=1; `confirm(`/`alert(` ligados ao desvincular: rc=1; tres arquivos novos UTF-8 (`file`). O `h-4 w-4` que sobra em `Obrigacoes.jsx:411` e o checkbox da listagem, fora de escopo desde a fase 33."

[2026-09-18T21:05:59] fase=36 acao=conferencia_local_minha resultado=ok obs="Medido por mim no navegador, antes de chamar o usuario. A :8001 da sessao anterior rodava codigo antigo (sem reload): reiniciada com o codigo novo, o MESMO banco de conferencia da sessao anterior e a mesma SECRET_KEY lida do processo (nao impressa), para o login do usuario continuar valendo; `/api/health` `build 20260918-2056`. A :3001 e de outra sessao e tem porta fixa: subi uma irma na :3002 (config temporaria em `frontend/node_modules/.vite-conferencia-3002.mjs`, ignorada pelo git; entrada `tareffas-front-conf-3002` no launch.json do diretorio da sessao, fora do repo). Entrei na copia com um token de teste gerado com a chave aleatoria da conferencia, sem digitar senha.
A COPIA NAO TINHA OBRIGACAO NENHUMA (`obrigacoes 0`, `tarefas 7`, `empresas 5`). Semeadas SO na copia: IPI (regra do regime do Cliente A), DIFAL (regra vazia), ECF (regra vazia + vinculo), DIRB (regime imune + vinculo) e Relatorio do cliente (modo vinculadas), com tarefas de 08 e 09/2026.
Resultado: modal abre com 'Nenhuma Empresa Escolhida'; busca 'clien' filtra para Cliente A e B, painel por cima da borda; lista com as 5, origens 'pela regra', 'pela regra e vinculada', 'vinculada' e 'N em aberto'; IPI + DIRB marcadas com motivo: aviso '4 tarefas em aberto serao canceladas', botao 'Desvincular 2 obrigacoes'; ao enviar, resultado '2 obrigacoes desvinculadas e 4 tarefas em aberto canceladas.' dentro do modal e as duas somem da lista. No banco da copia: as 4 tarefas CANCELADA com `nao_se_aplica=1` e o motivo; na linha de log `obrigacoes 2, excecoes_criadas 1, vinculos_removidos 1, tarefas_canceladas 4`, sem razao social. ESC com o painel aberto fecha so o painel; ESC de novo nao fecha o modal; zero `<select>` no modal; console sem erro.
Tres verificadores sonnet disparados em paralelo: conformidade, evidencia e funcional."

[2026-09-18T21:11:11] fase=36 acao=verificador_conformidade resultado=ok obs="Dois achados. (1) ACEITO: modal sem altura limitada (Padrao_Modal principio 4); em tela baixa o cabecalho e o botao podiam sair da janela. A caixa continua sem overflow (o painel do SelectBusca passa pela borda); o fundo ganhou `overflow-y-auto` e a caixa `my-auto`, que centraliza sem cortar o topo. Medido no navegador a 800x420: caixa 441px, titulo a 26px do topo, fundo rola, botao em 362-394 depois de rolar. (2) DISCORDANCIA REGISTRADA: pediu checkbox de tres estados no cabecalho e apontou 'Limpar' desabilitado como o anti-padrao 'botoes de lote soltos acima da tabela'. A Padrao_Selecao_em_Lote fala de TABELA de listagem com faixa que sobe do rodape; aqui e uma lista curta dentro de um modal, cujo unico destino e o botao do rodape, e 'Marcar todas' e 'Limpar' foram o que o PLANO aprovado pediu (36.4), no mesmo formato ja usado na tela (`Obrigacoes.jsx` da fase 33). Fica como esta. Resto LIMPO, inclusive acentuacao."

[2026-09-18T21:11:11] fase=36 acao=verificador_funcional resultado=ok obs="Um defeito real e uma leitura. (1) ACEITO, com RED proprio: motivo so com espacos passava (`min_length` media a string crua e a rota fazia `strip()` depois), e a trilha gravava motivo vazio. O IRMAO e o `NaoSeAplicaRequest` (`routes/tarefas.py:795`), mesma validacao. RED: item 28 da `prova_desvincular_regra.py` e item 20 da `prova_nao_se_aplica_lote.py`, os dois `(200)`, rc=1. GREEN: `str_strip_whitespace=True` no `model_config` dos dois schemas, que roda o strip antes do tamanho; `PROVA OK: 28` e `PROVA OK: 20`; `provas=35 falharam=0`; travessao rc=1. Na conferencia local: `motivo='   '` agora 422. (2) LEITURA, nao conserto: obrigacao INATIVA com vinculo manual nao aparece no alcance e da 422 no desvincular. E coerente com a geracao (inativa nao gera tarefa, e o alcance so lista ativas); o vinculo fica guardado para quando ela for reativada, e ai ela aparece na lista. Registrado para o usuario. Limpos: ids repetidos, empresa bloqueada, segmento, corrida (uma excecao so), 501 ids, tipos estranhos, alcance igual a `empresas_alvo`, troca rapida de empresa e duplo clique na tela.
Ambiente: a :8001 foi reiniciada sem guardar a SECRET_KEY anterior; voltou com chave nova e com `--reload`. O login do usuario na conferencia continua o mesmo (a senha esta no banco), so pede para entrar de novo."

[2026-09-18T21:12:57] fase=36 acao=verificador_evidencia resultado=ok obs="RED reproduzido numa worktree do HEAD `291daed` so com a prova nova: `[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 20, 21, 22, 24]`, rc=1, identico. GREEN e suites reproduzidos (35 e 22, zero falhas). Mutacoes: (a) `via_alcance` ignorando o modo, pega nos itens 2, 3 e 22; (c) sem o bloco de 'fora do alcance', a prova quebra com KeyError. DOIS ACHADOS.
(1) ACEITO: a mutacao (d), guarda de volta a `require_perm(obrigacoes, editar)`, passava VERDE. A analista da prova nao tem nem o modulo nem a flag, e cai no 403 de qualquer guarda. Itens 29 e 30 novos: 'Edu' (override `obrigacoes: editar`, sem a flag) recebe 403 nas duas rotas e nada muda; 'Alice' (override da flag, sem o modulo) recebe 200 no alcance. `PROVA OK: 30 checagens verdes`. A mutacao (d) refeita numa copia temporaria fora do repo: `PROVA FALHOU nos itens: [29, 30]`. Pega nos dois sentidos.
(2) DECLARADO, sem conserto: o item 7 (id que nao e numero) mede so a coercao do `List[int]`, que o schema antigo ja tinha; no RED ele falhou por cascata do item 6. Fica como nao-regressao do tipo, e o registro de 20:53 que o contou no RED pelo motivo certo estava errado nesse item.
(3) Evidencia que envelheceu durante a revisao, nao forjada (o proprio verificador diz): os consertos dos outros verificadores mexeram nas linhas. CHECKLIST da fase 36 remedido: backend `:133-142`, `:280`, `:298-299`, `:315`, `:318`, `:352`, `:355`; frontend +1 linha a partir de `:469`."

[2026-09-18T21:13:13] fase=36 acao=conferencia_visual resultado=blocked obs="PARADA PREVISTA (36.6): so o usuario confere. Itens 36.1 a 36.5 marcados com evidencia; tres verificadores tratados (conformidade: 1 aceito, 1 discordancia; funcional: 1 aceito com irmao na fase 35, 1 leitura; evidencia: 1 aceito com itens 29 e 30, 1 declarado). CONFORMIDADE: as linhas mecanicas das fases 35 e 36 em ok; pendentes so as quatro de CONFERENCIA_VISUAL (Estado_Vazio, Loading, Acao_Primaria, Tela_Nao_Tem_Manual). Balanco de simplificacoes: `escada:` rc=1, nenhum marcador.
TRES DECISOES COM O USUARIO, nenhuma resolvida aqui: (a) o irmao `gerar_para_empresa` ignorando o modo vinculadas (LOG 20:58:07), conserto de uma linha, escopo novo; (b) a pergunta da fase 29 (entregar pode exigir documento?) e o codigo dela na arvore sem commit, no mesmo `Obrigacoes.jsx`, antes do push da 37; (c) obrigacao inativa com vinculo nao aparece no Desvincular (leitura do verificador funcional), hoje coerente com a geracao."

[2026-09-18T21:15:49] fase=36 acao=conferencia_visual resultado=ok obs="Conferido em 2026-09-18 pelo usuario, tela Obrigacoes > Desvincular empresa, na conferencia local: 'conferi'. Junto veio a decisao (a) da parada: 'pode seguir com cadastramento', ou seja, consertar o irmao do cadastro de empresa nesta fase. As decisoes (b), fase 29, e (c), obrigacao inativa, seguem sem resposta."

[2026-09-18T21:15:49] fase=36 acao=irmao_RED_GREEN resultado=ok obs="Autorizado pelo usuario, entra na fase 36 (historico do PLANO atualizado). RED: secao 8 nova em `provas/prova_alvo_vinculadas.py` (a prova que ja guardava o modo vinculadas, mas so pela geracao do mes): empresa nova de lucro real com uma obrigacao 'so do cliente 1' (vinculadas, regra vazia) e uma geral. Contra o codigo de hoje: 'a empresa nova nao ganha a obrigacao so dos vinculados' FALHA `{'criadas': 2}`, e a segunda tambem; rc=1. A nao-regressao (a vinculada ganha as duas) ja passava.
GREEN: `gerar_para_empresa` (`services/gerador.py:513`) filtra por `via_alcance(o, empresa) is None` no lugar de `not _no_alvo`, com o motivo no comentario. `_no_alvo` segue com um chamador so, o ramo 'regra' de `empresas_alvo` (`:306`), onde o modo ja foi decidido. Secao 8: tres OK, `{'criadas': 1}` para a nova; `TODAS AS PROVAS PASSARAM`; `provas=35 falharam=0`; travessao rc=1."

[2026-09-18T21:15:49] fase=36 acao=fase_fechada resultado=ok obs="Criterio atendido: `prova_desvincular_regra.py` com RED (LOG 20:53, e depois [28]) e GREEN `PROVA OK: 30 checagens verdes`; front `prova_desvincular_empresa.js` RED por ausencia e GREEN 7; irmao do cadastro com RED e GREEN proprios; `provas=35 falharam=0`, `provas_front=22 falharam=0`, build ok; conferencia visual do usuario registrada; CONFORMIDADE sem linha pendente das fases 35 e 36 (as quatro visuais fechadas agora). Tres verificadores: 3 achados aceitos e consertados com RED, 1 discordancia e 2 declaracoes registradas. Balanco de simplificacoes: `escada:` rc=1, nenhum marcador. Fase 36: done. Proxima: fase 37 (publicar), que esbarra na decisao (b): o codigo da fase 29 esta na arvore, sem commit, no mesmo `Obrigacoes.jsx`."

## Fase 37, aberta em 2026-09-18

[2026-09-18T21:32:49] fase=37 acao=decisoes_usuario resultado=ok obs="Duas respostas: (1) PUBLICAR SO 35 E 36; a fase 29 fica na arvore esperando a conferencia visual 29.7. (2) Pergunta da fase 29: ENTREGAR NUNCA EXIGE DOCUMENTO. Vira regra da fase 29 quando ela for retomada: `perfil_documento` (`models.py`) devolve falso para entregar, com RED proprio; nao entra agora, porque e escopo da 29 e nao vai neste push. A decisao (c), obrigacao inativa no Desvincular, segue sem resposta e nao bloqueia."

[2026-09-18T21:32:49] fase=37 acao=recorte_e_commit resultado=ok obs="37.1. O `Obrigacoes.jsx` tinha 24 trechos, 15 da fase 36 e 9 da 29 (o import de `sentidoObrigacao` na linha 5 e tudo a partir da linha 497 antiga: identificadores, seletor de sentido e checkboxes do bloco). Patch so com os 15, com o import da 29 tirado do trecho da linha 5, aplicado ao indice com `git apply --cached --unidiff-zero`; a arvore nao foi tocada. Fora do commit: `Documentos.jsx`, `sentidoObrigacao.js` e `prova_sentido_obrigacao.js`.
PROVA DO RECORTE numa worktree limpa do HEAD com so o indice aplicado: `SENTIDOS|sentidoObrigacao` no `Obrigacoes.jsx` = 0; `vite build` `built in 1.19s`; `provas=35 falharam=0`; `provas_front=21 falharam=0` (21 porque a prova da 29 fica fora). Worktree removida. `COPY . .` nos dois Dockerfile (`backend:17`, `frontend:8`), entao os arquivos novos entram na imagem. Nada de .env, .db ou cookie no indice.
Commit `7045b5d`. A arvore ficou so com a fase 29 (`git diff --stat` do Obrigacoes.jsx: 1 file changed, 32 insertions(+), 55 deletions(-))."

[2026-09-18T21:33:40] fase=37 acao=publicado resultado=ok obs="37.2 e 37.3. Push de `291daed` (fase 35), `7045b5d` (fase 36) e dos commits de 00_GENESIS; `git ls-remote`: `166d59462f5f96d9fdce8edf6e9d042df6bc7798 refs/heads/main`. Carimbo antes `20260918-1847`, depois `20260918-2132`, igual ao HEAD, virou ~20s depois do push, sozinho pelo webhook.
Prova de fora, sem login: bundle `/assets/index-Dz50vD9F.js` com 'Nao se aplica a esta empresa' (3), 'pela regra' (3), 'Nenhuma Empresa Escolhida' (1) e 'alcance-empresa' (1); e 'Transmitir ao orgao' (0), que prova que a fase 29 NAO subiu, como decidido. `GET /api/obrigacoes/alcance-empresa/1` 401 e `POST /api/obrigacoes/desvincular-empresa` 401: as rotas existem e exigem login (rota inventada no mesmo prefixo: 404). Falta 37.4, conferencia do usuario em producao."

[2026-09-18T22:06:57] fase=37 acao=conferencia_producao resultado=blocked obs="Usuario testou em producao, na Trops: marcou varias como nao se aplica e disse que 'algumas nao sairam' (darf teste, darf_csll_lucropresumido_2372, lancamento_cmv). Diagnostico pelo codigo antes de mexer: a rota cancela sempre a clicada que veio de obrigacao, e a lista recarrega. Perguntado o status: as duas com obrigacao estao CANCELADAS. Causa: tarefa cancelada continuava no quadro (filtro de situacao vazio mostrava todas), com o selo 'Cancelada', e parecia nao ter saido. 'darf teste' tem cara de avulsa (sem obrigacao, sem a opcao no menu); sem resposta ainda."

[2026-09-18T22:06:57] fase=37 acao=cancelada_fora_da_visao resultado=ok obs="Pedido do usuario: 'pode esconder da visao padrao'. RED: caso novo em `frontend/provas/prova_filtro_tarefas.js` (sem situacao, as canceladas nao aparecem; escolhendo Cancelada, voltam; outras situacoes e a busca por texto nao mudam): `actual: [ 1, 2, 3, 4 ]`, rc=1. GREEN: uma linha em `filtroTarefas.js` (`!f.status && t.status === 'cancelada'`); `PROVA OK: 19 casos`. Na tela, o vazio da Situacao dizia 'Todas', que passou a ser mentira: virou 'Sem canceladas', com `title` dizendo como ver as canceladas. A primeira tentativa, 'Todas, menos canceladas', cortava em 110px (visto no navegador); 'Sem canceladas' mede 77px de texto num seletor de 108. IRMAO achado na mesma tela: o contador sem filtro mostrava `tarefas.length` (35 na copia), contando as escondidas; passou a `filteredTarefas.length` (31, medido). `provas_front=22 falharam=0`, build ok, travessao rc=1. Commit 4836af4."

[2026-09-18T22:11:44] fase=37 acao=publicado_canceladas resultado=ok obs="Push `ba5b30e` confirmado por `git ls-remote`. Bundle servido `/assets/index-w6-KSNUi.js` com 'Sem canceladas' (1): o frontend novo esta no ar. O carimbo do backend ficou `20260918-2132`, e esta CERTO: o commit so mexeu no frontend e no 00_GENESIS, a imagem do backend nao mudou, e o cache do Docker manteve a camada (regra do CLAUDE.md: carimbo velho nao e prova de deploy parado). Falta a conferencia do usuario em producao (37.4) e a resposta sobre 'darf teste'."
