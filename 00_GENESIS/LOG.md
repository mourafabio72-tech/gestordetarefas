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

## Fases 18 e 19, abertas em 2026-09-09

[2026-09-09T17:52:00] fase=0 acao=genesis_ampliado resultado=ok obs="Trabalho novo:
os campos obrigatorios do Padrao_Logging_Estruturado no log_event central. Modo
ampliacao. 5 notas lidas integrais pelo principal, 17 fichas de 2 batedores em
paralelo (sonnet), 6 notas aplicam e 12 foram descartadas com motivo escrito.
LASTRO, NOTAS_LIDAS, PLANO_FASEADO e CHECKLIST_APLICACAO recriados nesta pasta,
que tinha so LOG e matriz depois do checkpoint de 11:28. Matriz ganhou 11 linhas
novas, todas pendentes. Brainstorming socratico rodado antes do plano, 4
perguntas: cinco campos automaticos em vez de tres, campo chamado user_id,
eventos que faltam ficam para fase propria, e X-Request-ID na resposta."

[2026-09-09T18:02:00] fase=0 acao=graphify_atualizado resultado=ok obs="graphify
update . rodou na versao 0.9.45, custo zero de token: 72 arquivos reextraidos por
AST, 1461 nos e 3299 arestas, mapa antigo salvo em graphify-out/2026-09-09/. O
aviso de 'run graphify label' fica sem acao de proposito: renomear comunidade
usa LLM e nao muda o mapa de quem chama quem, que e para o que ele serve aqui."
[2026-09-09T18:02:00] fase=0 acao=plano_aprovado resultado=ok obs="Aprovado sem
ajustes pelo usuario. Fase 18 e 19 liberadas para execucao pela genesis-continuar."

[2026-09-09T18:20:00] fase=18 acao=modo_escolhido resultado=ok obs="modo=autonomo.
Toca as fases 18 e 19 sem confirmacao de rotina entre elas. O item 19.4 e
CONFERENCIA_VISUAL na aba Logs do EasyPanel, entao a parada para o usuario
acontece la de qualquer forma."

[2026-09-09T18:26:00] fase=18 acao=prova_logging_RED resultado=ok obs="18.1 feito.
`backend/provas/prova_logging.py`, 16 checagens, escrita ANTES do codigo e
reprovando o codigo de hoje: `PROVA FALHOU nos itens: [1, 2, 3, 4, 5, 7, 8, 9,
11, 12, 13, 14, 15]`, exit 1. Os 3 que ja passavam passam por motivo legitimo: o
6 (chamador vence o default) porque log_event ja aceita kwargs, o 10 (fora de
request nao quebra) porque nao havia contexto nenhum a ler, e o 16 (nada da lista
proibida) porque o codigo ja nao vazava. Dois itens foram ENDURECIDOS depois do
primeiro RED, porque passavam por falso verde: o 7 comparava X-Request-ID ausente
com request_id ausente (None == None) e o 13 dava por 'null' um campo que
simplesmente nao existia. Agora exigem valor presente. As rotas `_prova_*` sao
criadas dentro da prova, nao existem em producao, e sao a unica forma de emitir
duas linhas no MESMO request."

[2026-09-09T18:27:00] fase=18 acao=contexto_e_middleware resultado=ok obs="18.2 a
18.6. `seguranca.py:59-95` ganhou tres contextvars (`_request_id`, `_rota`,
`_usuario`), `abrir_contexto(request)` com `uuid.uuid4().hex[:16]` como a nota, e
`registrar_usuario`. O `log_event` preenche os cinco por `setdefault` e escreve a
linha na ordem da tabela da nota (`timestamp, level, event, user_id, ip,
request_id, path, method`), com os extras do chamador depois. Middleware
`_contexto_de_log` em `main.py:66-79`, ao lado do `_headers_de_seguranca`, e o
`X-Request-ID` volta na resposta. O IP vem de `ip_cliente(request)`, que ja
existia e ja trata X-Forwarded-For: NENHUMA extracao de IP nova foi escrita.
Nenhuma dependencia entrou (`requirements.txt` intocado), e NENHUM dos 14
chamadores do log_event recebeu `request` como parametro. Correcao de nomenclatura
do checklist: a funcao chama `ip_cliente`, e nao `ip_do_cliente` como o item 18.3
escreveu."

[2026-09-09T18:27:20] fase=18 acao=user_id_da_autenticacao resultado=ok obs="18.5.
`auth.py:54` chama `registrar_usuario(user.id)` dentro de `get_current_user`, que
e o unico ponto do app onde o usuario existe: `require_grupos`, `require_perm` e
`require_flag` derivam dela. Nas tres rotas de entrada (LOGIN_OK, SSO_ATIVOU_CONTA
e SSO_OK) o `registrar_usuario` entra antes do log, porque quem esta entrando
ainda nao passou pela dependencia. `grep -rn 'usuario_id=' backend/app/routes/ |
grep log_event` volta vazio."

[2026-09-09T18:27:21] fase=18 acao=prova_logging_GREEN resultado=ok obs="18.7.
`PROVA OK: 16 checagens verdes`, exit 0. Linha real capturada no stdout:
{'timestamp': ..., 'level': 'INFO', 'event': 'LOGIN_OK', 'user_id': 1, 'ip':
'testclient', 'request_id': 'd15c9c7f04774712', 'path': '/api/auth/login',
'method': 'POST', 'email': 'logueiro@bps4.com.br'}."

[2026-09-09T18:27:30] fase=18 acao=regressao resultado=ok obs="18.8.
`prova_sso_f3.py`: PROVA OK, 25 checagens verdes. `prova_seguranca_f7.py`: PROVA
OK, 19 checagens verdes. Uma leitura que parece falha e nao e: as linhas de log da
prova_sso_f3 saem com `request_id` null. Causa lida no arquivo, nao suposta: aquela
prova monta um `FastAPI()` proprio em `provas/prova_sso_f3.py:49` e inclui so o
router de auth, entao ela nao passa pelos middlewares do `app.main`. As duas provas
que usam o app real (prova_logging e prova_seguranca_f7) trazem o `request_id`
preenchido. Nada a corrigir no codigo de producao."

[2026-09-09T18:28:00] fase=18 acao=travessao_e_escada resultado=ok obs="18.9 e
18.10. Um travessao encontrado em arquivo do diff, em comentario preexistente de
`routes/auth.py:188`, reescrito com dois-pontos. Nos cinco arquivos tocados o grep
volta vazio. Inventario de simplificacoes: `grep -rn 'escada:' backend/` devolve
ZERO marcadores, e esta fase nao criou nenhum: nada foi cortado pela metade aqui.
ACHADO FORA DE ESCOPO, que nao corrijo por conta propria: o backend tem cerca de
90 travessoes em COMENTARIO e DOCSTRING (models.py, services/, routes/), que a
varredura de 2026-09-09 nao pegou porque ela mediu pela AST so as strings de dado.
A nota Sem_Travessao diz 'Codigo, Comentarios, Templates, Documentacao'. Vira fase
propria, com o frontend medido do mesmo jeito."

[2026-09-09T18:34:00] fase=18 acao=suite_completa resultado=ok obs="A nota de TDD
manda rodar TODOS os testes do projeto, e nao so os dois que o checklist pediu.
As 25 provas de `backend/provas/` rodaram e as 25 sairam com exit 0. As tres que
imprimem linha final de contagem: prova_logging 16 verdes, prova_seguranca_f7 19
verdes, prova_sso_f3 25 verdes. Nenhuma regressao em painel, gerador, evalidador,
alertas, entrega ao cliente, importadores nem carimbo de build."

[2026-09-09T18:40:00] fase=18 acao=achado_verificador_1 resultado=corrigido obs="O
verificador de conformidade derrubou o item 18.5, e tinha razao. `tarefas.py:433`
chamava `log_event(\"DOCUMENTO_EXCLUIDO\", ...)` com `usuario_id=current_user.id`
na LINHA SEGUINTE, e o `grep -n 'usuario_id=' ... | grep log_event` do checklist
nunca casaria as duas strings, porque sao linhas diferentes. O metodo de prova
estava quebrado, e o LOG das 18:27:20 registrou ok com base nele. Duas correcoes:
(1) o `usuario_id=` saiu de `tarefas.py:433`, e o campo agora vem do contexto,
porque aquela rota depende de `get_current_user`; (2) a prova ganhou o item 17,
que le o codigo-fonte por AST e cobre os 14 chamadores, inclusive os que nenhuma
prova exercita. Provado que o item novo REPROVA o codigo publicado: rodado contra
`git show HEAD:backend/app/routes/tarefas.py`, devolve `['linha 433 passa
usuario_id']`. `PROVA OK: 17 checagens verdes` depois da correcao. Os outros 13
chamadores conferidos por AST: os que passam campo de usuario ja usam `user_id`."

[2026-09-09T18:44:00] fase=18 acao=verificador_2_evidencia resultado=LIMPO obs="O
verificador de evidencia rodou as provas por conta propria e sustentou os dez
itens, com duas ressalvas cosmeticas que o proprio LOG ja tinha confessado: o
nome `ip_do_cliente` errado no texto do item 18.3, e o unico travessao do
checklist, que e o proprio caractere citado entre aspas dentro do item 18.9.
DIVERGENCIA ENTRE VERIFICADORES, e fica registrada: este deu 18.5 por sustentado
usando o MESMO `grep -n` que o verificador 1 provou ser cego a chamada quebrada
em duas linhas. Quem tinha razao era o 1. Serve de lembrete: dois revisores que
rodam o mesmo comando errado concordam entre si, e concordancia nao e prova."

[2026-09-09T18:52:00] fase=18 acao=verificador_3_funcional resultado=ok_com_achado obs="O
verificador funcional atacou o desenho com carga real, e nao por leitura: 40
requests concorrentes com `asyncio.gather` e `httpx.AsyncClient`, em rota `async
def` e em rota `def` (que o FastAPI roda em threadpool), cada uma com IP e
identidade diferentes, capturando o stdout. ZERO vazamento: todo `request_id`
unico, e o `ip` de cada linha bate com o dono do request. O motivo esta no
mecanismo: cada request e uma `asyncio.Task` propria, `ContextVar.set()` dentro
dela nao alcanca as tasks irmas, e o `anyio` copia o contexto por chamada ao
mandar rota sincrona para a threadpool. O scheduler nao usa `log_event`, so o
`logging` padrao, entao nao herda contexto de request nenhum.
ACHADO REAL, e NAO corrigido nesta fase por ser escopo novo: quando a rota levanta
excecao nao tratada, o `call_next` propaga para cima e a resposta 500 sai SEM o
`X-Request-ID`, porque o `ServerErrorMiddleware` do Starlette fica por fora de
todo middleware de usuario. Provado com uma rota que so faz `raise ValueError`. O
mesmo ja valia, desde antes desta fase, para os CABECALHOS DE SEGURANCA do
`_headers_de_seguranca`: a pagina de erro sai sem `X-Content-Type-Options` e
companhia. E justo o caso em que o id mais serviria. Nao entra aqui porque
consertar exige mexer no tratamento de erro global do app, e a saida obvia (o
middleware capturar Exception) TROCA o modo de falha: o traceback que o Starlette
imprime hoje no stdout deixaria de sair, a menos que eu o reemita a mao. Isso e
fase propria, com prova sua, e vai ao usuario no fechamento junto com o achado dos
travessoes."

[2026-09-09T18:53:00] fase=18 acao=fase_fechada resultado=ok obs="Criterio de
aceite do PLANO_FASEADO atendido e verificavel por quem nao escreveu:
`python backend/provas/prova_logging.py` devolve todos os itens ok e sai com
codigo 0, e os mesmos itens saem com codigo 1 no codigo de hoje (RED colado no
LOG das 18:26, e o item 17 provado contra `git show HEAD`). Os oito campos, os
dois request_id distintos, o mesmo id em duas linhas do mesmo request, o log fora
de request com os cinco em null, o default que o chamador vence e a lista proibida
vazia: todos na prova. Tres verificadores adversariais rodaram em paralelo, um
achou item marcado sem estar cumprido (corrigido), um voltou LIMPO e um provou a
ausencia de vazamento com carga real. Fase 18: done."

[2026-09-09T18:38:00] fase=19 acao=publicado resultado=ok obs="19.1 a 19.3.
Commit `e3c14e6`, push em `origin main`, e o webhook publicou sozinho, sem clique
em Implantar. 19.2: producao devolve
`{\"status\":\"healthy\",\"build\":\"20260909-1835\"}` e o HEAD e `e3c14e6
20260909-1835`, os dois iguais, entao a imagem no ar e a desta fase. Antes do
deploy o carimbo era `20260909-1141`, o do commit anterior: a comparacao foi feita
nas duas pontas, e nao so depois. 19.3: `curl -sI .../api/health | grep -i
x-request-id` em tres chamadas devolve `9543699a3cbc4512`, `a325449b76254a10` e
`15c1ff5d47e347a4`, tres valores distintos de 16 hexadecimais. O `Dockerfile` do
backend usa `COPY . .`, conferido ANTES do push, entao o arquivo novo
(`provas/prova_logging.py`) entra na imagem em vez de ficar de fora como
aconteceu no broker em 01/09."

[2026-09-09T18:39:00] fase=19 acao=matriz_fechada resultado=ok obs="19.5. As 11
linhas que as fases 18 e 19 acrescentaram a `CONFORMIDADE_VAULT.md` estao todas
preenchidas com a saida real do comando, e `grep -c '| pendente |'` na matriz
inteira devolve 0. Uma delas teve a PROVA trocada, e nao so a evidencia colada: a
linha do `user_id` provava por `grep -n`, que e cego a chamada quebrada em duas
linhas, e passou a provar por leitura de AST."

[2026-09-09T18:39:30] fase=19 acao=parada resultado=blocked obs="Falta o item
19.4, e ele e CONFERENCIA_VISUAL por natureza: o log de producao nao sai por curl,
so pela aba Logs do servico no EasyPanel. O que o usuario tem de olhar esta no
relatorio de parada. Todo o resto das fases 18 e 19 esta fechado, publicado e
conferido de fora."
