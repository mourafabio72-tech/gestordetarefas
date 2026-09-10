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

[2026-09-09T19:05:00] fase=0 acao=escopo_ampliado resultado=ok obs="O usuario
mandou abrir as fases para os dois achados que a Fase 18 produziu e que eu nao
consertei por conta propria. PLANO_FASEADO ganhou a Fase 20 (resposta de erro sai
sem cabecalho e sem X-Request-ID) e a Fase 21 (cerca de 90 travessoes em
comentario e docstring), com criterio de aceite verificavel em cada uma, mais uma
secao de historico dizendo o que mudou e quando. CHECKLIST ganhou 18 itens, e a
matriz ganhou 6 linhas pendentes. Notas lidas para lastrar as fases novas, nesta
sessao e integrais: `CSRF_Cookies_Headers` (117 linhas, fim 'Ver também', a secao
'Headers de seguranca (em toda resposta)' com os seis cabecalhos) e
`Revisao_Vulnerabilidades` (36 linhas, fim 'Ver também', item 9, mensagem generica
ao cliente). Nenhuma fase anterior mudou de escopo: as 18 e 19 seguem fechadas."

[2026-09-09T19:10:00] fase=0 acao=plano_ampliado_aprovado resultado=ok obs="O
usuario aprovou as fases 20 e 21 e escolheu retomar em CONVERSA NOVA, para nao
carregar o historico desta. Fase 20 e a proxima acao, e o primeiro item dela e o
20.1: escrever `backend/provas/prova_erro_500.py` e ve-la falhar ANTES de tocar no
codigo. O modo segue `autonomo`, ja gravado no topo do PLANO_FASEADO: quem retomar
nao repergunta. Pendente do usuario, e so dele: o item 19.4, conferencia visual da
linha de log na aba Logs do EasyPanel."

[2026-09-09T19:30:00] fase=0 acao=fase_22_aberta resultado=ok obs="Achado do
USUARIO, e nao meu: ao conferir o item 19.4 ele trouxe o log do EasyPanel, e nele
aparecem cerca de 45 `ERROR: column ... already exists` por boot, vindos do
`migrate()`. Eu tinha conferido carimbo, cabecalho e rota, e nunca o log do banco.
Medido antes de escrever a fase: `init_db.py:65` roda as 64 migracoes sempre, uma
transacao por item, e usa o erro do banco como deteccao (`init_db.py:70-73`). A
armadilha esta declarada no plano: `ADD COLUMN IF NOT EXISTS` quebraria a suite,
porque as provas rodam em SQLite, que nao aceita essa forma. O caminho e o
`inspect(engine)`, que ja vem instalado. Tres migracoes nao sao ADD COLUMN
(`data_prazo_nullable`, `setor_empresa_nullable`, `identificadores_maior`) e
precisam de tratamento proprio, senao a fase promete um zero que nao entrega: elas
falham com erro de sintaxe em SQLite a cada rodada de prova hoje. Os indices ficam
como estao, ja usam IF NOT EXISTS. PLANO ganhou a Fase 22, CHECKLIST 10 itens, e a
matriz 3 linhas pendentes."

## Fase 20, executada em 2026-09-09 a noite

[2026-09-09T20:40:00] fase=20 acao=prova_erro_500_RED resultado=ok obs="20.1 feito.
`backend/provas/prova_erro_500.py`, 14 checagens, escrita ANTES do codigo e
reprovando o codigo de hoje: `PROVA FALHOU nos itens: [2, 3, 4, 6, 7, 8, 9]`,
exit 1. Os que ja passavam passam por motivo legitimo, e tres deles sao itens de
NAO-REGRESSAO, medidos ANTES justamente para acusar se a fase quebrar o que
funciona: o 1 (Starlette ja devolve 500), o 5 (o corpo de hoje e o texto
generico `Internal Server Error`, entao ja nao vaza), o 11 (caminho feliz), e o
12, 13 e 14, que sao o traceback do servidor de verdade. O 14 sobe um uvicorn em
subprocess numa porta livre, dispara a rota que estoura e le o stderr do
processo: e a unica forma de medir o log DO SERVIDOR, porque com TestClient nao
existe servidor nenhum para logar. O `raise_server_exceptions=False` no
TestClient e o que faz a prova ver a resposta em vez de receber a excecao."

[2026-09-09T20:40:30] fase=20 acao=state_e_handler resultado=ok obs="20.2 a 20.4.
`seguranca.py:85` grava o mesmo id em `request.state.request_id`, SEM tirar a
contextvar: o `log_event` continua lendo do contexto, e por isso nenhum dos 14
chamadores mudou. `main.py:80-113` ganhou o `@app.exception_handler(Exception)`,
que emite `ERRO_NAO_TRATADO` em nivel ERROR e devolve
`{'detail': 'Erro interno. Tente novamente.'}` com 500. Os cabecalhos saem do
`aplicar_headers` que ja existia (`main.py:111`), e nao de lista nova: degrau 2
da escada. O motivo de ler do `state` e nao da contextvar esta medido, e nao
suposto: o `ServerErrorMiddleware` roda em contexto ANCESTRAL ao da task do
request, entao a contextvar setada la dentro nao chega aqui. O `state` vive no
`scope`, que e o mesmo dicionario nas duas pontas.
LIMITE DECLARADO, e nao escondido: o `user_id` da linha `ERRO_NAO_TRATADO` sai
`null`, pelo mesmo motivo de contexto. Fazer diferente exigiria `get_current_user`
receber o `request` para gravar no `state`, e isso e escopo novo, nao item desta
fase. Os oito campos saem na linha, que e o que o criterio pede; o que falta e o
VALOR de um deles, e fica registrado aqui."

[2026-09-09T20:40:45] fase=20 acao=prova_erro_500_GREEN resultado=ok obs="20.6.
`PROVA OK: 14 checagens verdes`, exit 0. As duas linhas reais capturadas no
stdout, do MESMO request, com o mesmo id que voltou no cabecalho:
{'level': 'INFO', 'event': 'PROVA_ANTES_DE_ESTOURAR', ..., 'request_id':
'edd6329ded6f47bd', 'path': '/api/_prova_estoura', 'method': 'GET'} e
{'level': 'ERROR', 'event': 'ERRO_NAO_TRATADO', 'user_id': null, 'ip':
'testclient', 'request_id': 'edd6329ded6f47bd', 'path': '/api/_prova_estoura',
'method': 'GET', 'excecao': 'ValueError'}. O nome da excecao vai para o LOG e
NAO para o cliente, que e a Familia 6 na pratica: pouco ao cliente, muito ao
servidor."

[2026-09-09T20:41:00] fase=20 acao=ponto_que_a_fase_tinha_de_medir resultado=ok obs="20.5.
O PLANO mandava medir, e nao presumir, se registrar handler de `Exception` faz o
traceback sumir do stdout. NAO faz, e o motivo esta lido no fonte instalado, nao
suposto: `venv/lib/python3.9/site-packages/starlette/middleware/errors.py:184`
executa `raise exc` DEPOIS de chamar o handler, sempre. Duas provas disso: o item
12, em que o TestClient estrito recebe o `ValueError` original, e o item 14, com
uvicorn de verdade, onde `Traceback` e `ValueError` aparecem no stderr do
processo. O desenho da fase fica de pe."

[2026-09-09T20:42:00] fase=20 acao=regressao_suite_completa resultado=ok obs="20.7.
As 26 provas de `backend/provas/` rodaram e as 26 sairam com exit 0. As quatro
que imprimem contagem: prova_erro_500 14 verdes, prova_logging 17 verdes,
prova_seguranca_f7 19 verdes, prova_sso_f3 25 verdes. O handler global de
excecao nao mudou o comportamento de nenhuma rota: `HTTPException` continua
sendo tratada pelo `ExceptionMiddleware`, que fica por dentro, e so o que passa
por ele sem tratamento chega aqui."

[2026-09-09T20:42:30] fase=20 acao=travessao_e_escada resultado=ok obs="20.8.
`grep -n` de travessao nos tres arquivos do diff (`main.py`, `seguranca.py`,
`prova_erro_500.py`) volta vazio. Inventario de simplificacoes:
`grep -rn 'escada:' backend/` fora do venv devolve ZERO marcadores, e esta fase
nao criou nenhum."

[2026-09-09T20:44:00] fase=20 acao=publicado resultado=ok obs="20.9. Commit
`78dc6a3`, push em `origin main`, e o webhook publicou sozinho. Producao devolve
`{\"status\":\"healthy\",\"build\":\"20260909-2042\"}` e o HEAD e `78dc6a3
20260909-2042`: os dois iguais, entao a imagem no ar e a desta fase. O
`Dockerfile` do backend usa `COPY . .` (linha 17), conferido ANTES do push,
entao o arquivo novo `provas/prova_erro_500.py` entra na imagem. O que NAO da
para provar de fora, e fica dito: nao existe rota que estoure em producao, e nao
vou criar uma para tirar prova. O que o curl mostra e o caminho feliz, com
`x-request-id` e `x-content-type-options: nosniff`."

[2026-09-09T20:45:00] fase=20 acao=matriz resultado=ok obs="20.10. As cinco
linhas que a fase 20 abriu na `CONFORMIDADE_VAULT.md` estao preenchidas com a
saida real. Restam 4 linhas pendentes na matriz inteira, e todas sao de fase
futura: 1 da fase 21 (Sem_Travessao) e 3 da fase 22. RESSALVA gravada dentro da
propria linha do `Padrao_Logging_Estruturado`, para nao ficar so no LOG: os oito
campos saem na linha de erro, mas o `user_id` sai `null`."

## Fase 21, inventario feito antes de tocar em nada

[2026-09-09T20:46:00] fase=21 acao=inventario resultado=ok obs="21.1.
`grep -ro` em `backend/app`, `backend/provas` e `frontend/src` devolve 224
travessoes em 63 arquivos. E MAIS QUE O DOBRO do que o PLANO estimou (`cerca de
90`), e a diferenca tem explicacao: a estimativa contava so comentario e
docstring do BACKEND, e dizia com todas as letras que o frontend nao tinha sido
medido desse jeito. Agora esta medido. Os dez maiores: models.py 18,
services/whatsapp.py 12, services/validador.py 11, pages/painelDados.js 10,
routes/tarefas.py 10, pages/identificador.js 9, prova_entrega_cliente.py 8,
prova_tipo_documento.py 7, prova_painel.py 7, prova_sentido_obrigacao.py 6. O
numero nao muda o escopo da fase, muda o tamanho dela."

[2026-09-09T20:50:00] fase=20 acao=verificador_evidencia resultado=LIMPO obs="O
verificador de evidencia rodou as provas por conta propria, inclusive o RED
contra `HEAD~1` em worktree separada, e sustentou os oito itens. Confirmou por
leitura do fonte instalado o `raise exc` incondicional em
`starlette/middleware/errors.py:184`, e reproduziu o traceback no uvicorn de
verdade. Um achado de redacao, corrigido: o item 20.7 dizia `As 25 provas`, e
sao 26 desde que esta fase acrescentou a `prova_erro_500.py`. A segunda
observacao dele nasceu de leitura no meio do caminho: 20.9 e 20.10 ja estavam
gravados no LOG e ainda nao no CHECKLIST quando ele leu, porque o `startswith`
que usei para marcar exigia um espaco que aquelas duas linhas nao tinham. Os dois
itens ja estao marcados."

[2026-09-09T20:52:00] fase=20 acao=verificador_funcional resultado=LIMPO obs="O
verificador funcional atacou o desenho com carga real contra um uvicorn de
verdade, 3 rodadas de 31 checagens, todas verdes: 25 requests simultaneos que
estouram, com IP e caminho distintos, sem um unico id vazando para a linha de
outro; rota `async def` e rota `def` em threadpool, as duas mantendo a
correlacao; excecao dentro de `Depends`, tratada igual; `HTTPException`, 404 e
422 de validacao intactos, com o corpo de sempre e sem disparar
`ERRO_NAO_TRATADO`; e o traceback no stderr do processo. Registrou tambem que o
`log_event` nunca grava `str(exc)`, so `type(exc).__name__`, o que e mais
estrito do que a Familia 6 pede.
DOIS LIMITES DO DESENHO, que ele nomeou e eu registro em vez de esconder: (1)
excecao depois que o streaming ja comecou nao vira 500, porque nao da para
trocar um 200 ja enviado, mas o servidor ainda escreve `ERRO_NAO_TRATADO`; (2)
excecao dentro de `BackgroundTask` nao passa pelo handler e NAO deixa linha
nenhuma. O segundo nao afeta este app hoje, e isso foi medido, nao suposto:
`grep -rn 'BackgroundTask' backend/app/` volta vazio. Se um dia entrar, a
lacuna vira decisao explicita."

[2026-09-09T20:52:30] fase=20 acao=achado_verificador_conformidade resultado=corrigido obs="O
verificador de conformidade derrubou a ressalva que eu mesmo tinha escrito, e
ele estava certo. Eu tratei o `user_id` null da linha de erro como limite
aceitavel; a nota nao permite isso. `Padrao_Logging_Estruturado` define o campo
como 'ID do usuario autenticado, ou null se anonimo', e null com usuario logado e
VALOR ERRADO, nao campo ausente. Item de nota de padrao nao passa pela escada, e
por isso nao cabia marcador `escada:` aqui: cabia conserto. Ele provou com script
proprio, JWT valido e rota atras de `Depends(get_current_user)`, e apontou a
incoerencia dentro do proprio commit: eu resolvi a fronteira de contexto para o
`request_id` e deixei o usuario no fallback da contextvar, pelo mesmissimo motivo
que o meu docstring citava.
Achado irmao, e o mais util dos dois: a PROVA era cega. O item 8 conferia
presenca de chave, e a rota que estoura nao passa por autenticacao nenhuma,
entao as 14 verdes fechavam com o campo quebrado por baixo.
Duas correcoes, na ordem do TDD: (1) a prova ganhou os itens 15 e 16, com rota
autenticada que quebra, e o 15 REPROVA o codigo publicado (`PROVA FALHOU nos
itens: [15]`, exit 1); (2) `registrar_usuario` ganhou o `request` opcional e
grava no `state`, nos quatro pontos onde o usuario passa a existir
(`auth.py:55`, `routes/auth.py:68`, `:195`, `:202`), e o handler le de la.
`get_current_user` passou a receber `request`, que o FastAPI injeta sozinho.
`PROVA OK: 16 checagens verdes` depois. As 26 provas do backend em exit 0, o que
importa aqui porque a assinatura da dependencia de autenticacao mudou e ela rege
o app inteiro. Publicado em `c9c0eb6`."

[2026-09-09T20:53:00] fase=20 acao=fase_fechada resultado=ok obs="Criterio de
aceite do PLANO atendido e verificavel por quem nao escreveu:
`python backend/provas/prova_erro_500.py` sai com codigo 0 (16 verdes) e saia com
codigo 1 no codigo anterior, provado duas vezes, na abertura da fase e de novo
depois do conserto do `user_id`. Na resposta de erro: `X-Request-ID` igual ao
`request_id` da linha, os seis cabecalhos da nota, corpo sem traceback, sem nome
de excecao, sem caminho e sem SQL. Na linha `ERRO_NAO_TRATADO`: os oito campos, e
agora com o `user_id` de quem derrubou. E o ponto que o plano mandava medir: o
traceback CONTINUA no stdout do servidor, provado com uvicorn de verdade.
Publicado em `c9c0eb6`, carimbo `20260909-2052` batendo com o HEAD. Tres
verificadores adversariais rodaram: um voltou LIMPO com 31 checagens de carga
real, um voltou LIMPO na evidencia e achou um erro de redacao (25 provas virou
26), e um achou o `user_id` errado, que virou conserto e nao marcador. Fase 20:
done."

[2026-09-09T20:58:00] fase=21 acao=reescrita resultado=ok obs="21.2 e 21.3. As
224 ocorrencias sairam, uma por uma, com a pontuacao decidida pela frase:
dois-pontos quando o que vem depois explica, virgula quando e adendo, e
parenteses nos DEZ casos de aposto entre dois travessoes, tres deles cruzando
duas linhas (`models.py:218-219`, `identificador.js:6-7`, `Dashboard.jsx:159-160`)
e dois com a forma `—,` no fechamento (`Dashboard.jsx:384` e `:423`). Um unico
caso virou hifen e nao pontuacao de frase: `prova_tipo_documento.py:95`, onde o
travessao esta DENTRO do texto simulado de um documento
(`DOCUMENTO DE ARRECADACAO - GUIA DE RECOLHIMENTO`), e trocar por dois-pontos
mudaria o dado de teste. `grep -rn` em `backend/app`, `backend/provas` e
`frontend/src` volta vazio nos tres."

[2026-09-09T20:58:30] fase=21 acao=diff_conferido resultado=ok obs="21.4. O diff
tem 217 linhas removidas e 217 acrescentadas, troca de uma para uma, sem linha
movida nem arquivo fora da lista. A conferencia nao foi so de olho: um script
compara o ESQUELETO de cada par de linhas, que e o texto sem pontuacao e sem
espaco, e os 217 pares sao identicos. Mudanca de palavra, de nome ou de codigo
apareceria ai. Os dez casos de parenteses foram lidos a olho por cima disso, um
a um, inclusive os tres que fecham na linha seguinte."

[2026-09-09T20:59:00] fase=21 acao=regressao resultado=ok obs="21.5. 26 provas do
backend em exit 0, 18 provas do frontend em exit 0 (inclusive a
`prova_ordem_hooks.js`, que varre o `src` inteiro), e `npm run build` compilando
em 1.26s."

[2026-09-09T21:01:00] fase=21 acao=publicado resultado=ok_com_criterio_corrigido obs="21.6.
Commit `a959446`, push, e o carimbo de producao subiu para `20260909-2058`,
igual ao HEAD. A METADE DO CRITERIO ESCRITO NO PLANO NAO SE APLICA A ESTA FASE, e
isso e medida, nao desculpa: o item pedia `o hash do bundle do Vite mudando, que
e o que prova frontend novo no ar`. O bundle NAO muda, e nao poderia mudar: as 68
ocorrencias do frontend estavam todas em COMENTARIO de .js, .jsx e .css, e
comentario o minificador remove. Prova de que o bundle e o mesmo por conteudo, e
nao por acaso: `npm run build` DEPOIS da mudanca gera `index-DwKXh0Cp.js`, o
mesmo nome que producao ja servia, e o md5 do arquivo local bate com o md5 do
arquivo baixado de producao (`85c80e27b50cc269e4a87fa7689127e3` nos dois). Hash
igual aqui NAO e sinal de deploy parado: e a prova de que nao havia frontend novo
a subir. Quem prova esta fase no ar e o carimbo do backend, que se moveu porque
os arquivos .py mudaram."

[2026-09-09T21:01:30] fase=21 acao=matriz resultado=ok obs="21.7. A linha da
`Sem_Travessao` na matriz saiu de pendente. Restam 3 pendentes na matriz inteira,
todas da fase 22."

[2026-09-09T21:02:00] fase=21 acao=fase_fechada_aguardando_verificadores resultado=ok obs="Os
sete itens marcados com evidencia. Dois verificadores adversariais disparados
antes de mudar o status da fase para done."

[2026-09-09T21:06:00] fase=21 acao=achado_verificador resultado=corrigido obs="O
verificador adversarial derrubou a fase, e tinha razao em tres pontos. O ERRO DE
FUNDO foi meu: eu medi o escopo que o PLANO escreveu (`backend/app`,
`backend/provas`, `frontend/src`) em vez do escopo que a NOTA manda ('em lugar
nenhum: Codigo, Comentarios, Templates, Documentacao, README'). Plano e resumo,
nota e contrato.
(1) `frontend/provas` inteiro ficou de fora: 44 ocorrencias em 14 arquivos
versionados, o irmao exato de `backend/provas`, que eu limpei. Uma delas era
DADO de teste (`prova_identificador.js:13`, texto simulado de documento) e virou
hifen, como o outro caso ja registrado. (2) A documentacao da raiz, 45
ocorrencias em quatro `.md` e um comentario do `.gitignore`; celula vazia de
tabela markdown virou hifen, e nao dois-pontos. (3) Duas correcoes de escrita:
`colisaoIdentificador.js:17` tinha ficado com dois-pontos duplicado na mesma
frase, e cinco blocos de lista tinham travessao alinhado em coluna por
espacamento, que a troca desalinhou. Realinhados, inclusive as duas linhas de
continuacao de `models.py:441-442`, orfas da indentacao antiga.
ACHADO DELE QUE EU NAO TRATO COMO ERRO, e explico por que: ele aponta que o meu
metodo de conferencia (comparar o esqueleto da linha sem pontuacao) nao
distingue travessao de COMENTARIO de travessao dentro de LITERAL testado. Esta
certo, e o buraco existe. So que o unico caso desse tipo no diff eu ja tinha
achado e registrado por leitura, antes dele, no LOG das 20:58: e o
`prova_tipo_documento.py:95`. O metodo mecanico nao pega, a leitura pegou, e as
duas coisas rodaram. Fica dito para quem repetir a varredura noutro projeto: o
esqueleto prova que nao houve mudanca de PALAVRA, nao prova que a linha era
comentario.
Varredura do repositorio inteiro depois do conserto, fora de `venv`,
`node_modules`, `dist`, `.git`, `graphify-out`, `.claude` e `00_GENESIS`: zero
travessoes. O `00_GENESIS` fica de fora de proposito: e registro de auditoria e
append-only por regra da propria skill. Publicado em `970c5b7`."

[2026-09-09T21:12:00] fase=21 acao=verificador_final resultado=ok_com_achado obs="O
verificador de evidencia sustentou seis dos sete itens rodando tudo por conta
propria, inclusive reconstruindo o estado anterior num worktree de `a959446~1`
para recontar o inventario: 224 ocorrencias em 63 arquivos, igual ao LOG; 217
inserções e 217 delecoes no diff; 26 provas do backend e 18 do frontend em exit
0; `npm run build` limpo; e o md5 do bundle identico entre local e producao,
conferido por curl.
ACHADO QUE ACEITO, e e de auditoria, nao de codigo: o TEXTO do item 21.6 no
CHECKLIST continuava dizendo `o hash do bundle do Vite mudando, que e o que
prova frontend novo no ar`, que e o oposto do que aconteceu. Eu tinha corrigido
isso no LOG das 21:01 e deixado o item marcado com a frase antiga. Quem lesse so
o checklist, que e o artefato que fica, receberia uma afirmacao falsa. O item foi
reescrito com a medicao dentro dele. De quebra, o 21.5 dizia `As 25 provas` e
agora diz 26 do backend e 18 do frontend.
Registrado tambem o que ele varreu e decidiu excluir, para nao virar surpresa
depois: `graphify-out/` tem 44 travessoes e esta no `.gitignore` (artefato
gerado, analogo ao `dist/`); o `00_GENESIS` tem 11, e fica de fora por ser
registro append-only; e o en-dash de `PERMISSOES_SPEC.md:8-9` e notacao de faixa
(`A1–A3`), corretamente intocado."

[2026-09-09T21:13:00] fase=21 acao=fase_fechada resultado=ok obs="Criterio de
aceite atendido: `grep -rn` volta vazio nos tres caminhos do plano E no
repositorio inteiro fora dos gerados; a suite continua em exit 0 nas duas pontas;
o `npm run build` compila; e nenhum arquivo mudou alem da pontuacao, provado
mecanicamente nos dois lotes (217 e 99 pares de linha com esqueleto identico) e
lido a olho nos dez casos de parenteses. Publicado em `a959446` e `970c5b7`,
carimbo `20260909-2106`. Dois verificadores adversariais rodaram: o primeiro
achou o escopo curto (frontend/provas e a documentacao da raiz), que virou o
segundo lote, e o segundo achou o texto do item 21.6 contradizendo a propria
evidencia, que virou reescrita do item. Fase 21: done."

## Fase 22, executada em 2026-09-09 a noite

[2026-09-09T21:16:00] fase=22 acao=prova_RED resultado=ok obs="22.1.
`backend/provas/prova_migrate_silencioso.py`, 9 checagens, escrita ANTES do
codigo e reprovando o codigo de hoje: `PROVA FALHOU nos itens: [3, 4, 5, 6, 8,
9]`, exit 1. O cenario nao e um banco que ja nasce completo, e isso e o item 1 da
propria prova: depois do `create_all` ela DERRUBA tres colunas (`usuarios.telefone`,
`tarefas.anexo_nome`, `obrigacoes.ancora`) para o banco parecer desatualizado, e
so entao roda o `migrate` duas vezes. Correcao no meio do caminho, medida e nao
suposta: a primeira escolha incluia `tarefas.competencia`, e o SQLite recusa
`DROP COLUMN` de coluna indexada (`error in index ix_tarefas_competencia`). A
prova estava medindo o proprio tropeco, e a coluna foi trocada por uma sem
indice. O numero real de migracoes tambem entra aqui: sao 51, e nao 64 como o
PLANO estimou. 48 `ADD COLUMN` e 3 `ALTER COLUMN`."

[2026-09-09T21:18:00] fase=22 acao=migrate_pergunta_antes resultado=ok obs="22.2 e
22.3. `init_db.py` ganhou `inspect(engine)`, a lista saiu de dentro da funcao e
virou a constante `MIGRACOES`, e `migrate()` aceita uma lista propria, que e como
a prova injeta a migracao quebrada. Uma leitura por TABELA, guardada em cache, e
nao uma consulta por migracao. As tres que nao sao `ADD COLUMN` respondem pelo
mesmo `get_columns`: `nullable` decide as duas de `DROP NOT NULL`, e o `length`
do tipo decide a de `TYPE VARCHAR`. NENHUM `ADD COLUMN IF NOT EXISTS` entrou, e o
motivo esta no docstring: SQLite nao aceita essa forma e a suite inteira
quebraria."

[2026-09-09T21:18:30] fase=22 acao=silencio_que_nao_engole resultado=ok obs="22.4.
O `except` que sobrou continua reportando: item 9 da prova injeta
`ALTER TABLE tabela_que_nao_existe ADD COLUMN nada` e exige a linha
`Erro na coluna 'migracao_quebrada_de_proposito'` no stdout.
DESENHO QUE MUDEI NO MEIO, e o motivo importa: a primeira versao PULAVA migracao
cuja tabela nao existe, tratando como orfa. Isso fez o item 9 falhar, e o item
tinha razao contra mim: do lado do banco, tabela sumida por engano e tabela que
nunca existiu sao a mesma coisa, e pular as duas trocaria erro FALSO por erro
ESCONDIDO, que e pior. Agora tabela inexistente deixa rodar, e o log diz o que
houve. A migracao orfa de verdade (`setor_empresa_nullable`, cuja coluna saiu do
model) ja e resolvida pelo outro caminho: a coluna nao existe, entao o
`DROP NOT NULL` nao e necessario e nao roda."

[2026-09-09T21:19:00] fase=22 acao=GREEN_e_regressao resultado=ok obs="22.5 e
22.6. `PROVA OK: 9 checagens verdes`, exit 0. As 27 provas do backend em exit 0.
E a medida que da nome a fase: o boot de cada prova cuspia 45 linhas de
`Coluna ... ja existe` mais 3 de `Erro na coluna` (as tres ALTER COLUMN, que
falhavam com erro de sintaxe em SQLite a CADA rodada de prova). Agora
`grep -cE 'já existe|Erro na coluna|adicionada com sucesso'` no boot de
prova_painel, prova_logging e prova_erro_500 devolve ZERO nas tres."

[2026-09-09T21:20:00] fase=22 acao=publicado resultado=ok obs="22.7 e 22.8.
Travessao nos dois arquivos do diff: nenhum. `grep -rn 'escada:' backend/`: zero
marcadores, e esta fase nao criou nenhum. Commit `0a67db6`, push, e producao
responde `{\"status\":\"healthy\",\"build\":\"20260909-2120\"}`, igual ao HEAD."

[2026-09-09T21:21:00] fase=22 acao=matriz resultado=ok obs="22.10. As tres linhas
da fase 22 preenchidas com a saida real, e a matriz INTEIRA fica sem nenhuma
linha pendente: `grep -c '| pendente |'` devolve 0. Falta so o 22.9, que e
CONFERENCIA_VISUAL no log do servico `db` no EasyPanel, e e do usuario."

[2026-09-09T21:30:00] fase=19 acao=item_19_4_conferido resultado=ok obs="19.4
FECHADO. O usuario fez o login em producao e trouxe a linha do servico
`backend-1`, achada pelo `request_id` que o cabecalho `X-Request-ID` devolveu ao
navegador dele (`bb3db6abfe6c4866`), que e exatamente o caminho que a ampliacao
da Fase 18 existe para permitir. A linha, verbatim:
{\"timestamp\": \"2026-09-10T00:26:22.596201+00:00\", \"level\": \"INFO\",
\"event\": \"LOGIN_OK\", \"user_id\": 1, \"ip\": \"186.205.160.122\",
\"request_id\": \"bb3db6abfe6c4866\", \"path\": \"/api/auth/login\",
\"method\": \"POST\", \"email\": \"fabio@bps4.com.br\"}
Os oito campos da nota, na ordem da tabela dela, com o `email` como campo extra
do evento, que a propria nota autoriza no exemplo do LOGIN_FALHA.
O QUE SO ESTE ITEM PODIA PROVAR, e por isso ele nao era burocracia: o `ip` e
`186.205.160.122`, publico e do usuario, e nao um `172.16.x` da rede do Docker.
Nenhuma prova local alcanca isso, porque o `X-Forwarded-For` de verdade so existe
atras do nginx e do Traefik. O contraste esta na mesma tela: as linhas de acesso
do uvicorn, ao lado, mostram `172.16.2.4` em todas, que e o proxy. O
`ip_cliente`, que le a lista de tras para frente com `PROXIES_ANEXADOS = 1`, esta
acertando o alvo em producao.
DUAS OBSERVACOES REGISTRADAS, nenhuma delas violacao: (1) o `timestamp` sai em
UTC (`+00:00`) porque o container roda em UTC, enquanto na maquina local sai
`-03:00`. A nota pede ISO 8601 COM timezone, e o campo tem timezone, entao esta
cumprida; quem for correlacionar log com horario de reclamacao precisa lembrar
das 3 horas. (2) O `email` aparece na linha, e isso e decisao ja registrada no
LASTRO: a propria nota registra `email_tentado` no exemplo dela, entao nao e PII
vazando por descuido, e continua fora da lista proibida."

[2026-09-09T21:31:00] fase=22 acao=verificador_funcional resultado=ok_com_dois_achados obs="O
verificador funcional rodou os sete ataques com scripts proprios em /tmp. O RISCO
CENTRAL NAO SE CONFIRMOU: ele derrubou 37 das 48 colunas de ADD COLUMN num SQLite
(as 11 restantes sao FK, e o SQLite recusa DROP COLUMN nelas, limitacao do
harness dele e nao do codigo), rodou o migrate, e as 37 renasceram. Banco vazio
nao fica em silencio: as 51 tentam e cada uma reporta `no such table`, que e o
desenho. Cinco rodadas contra banco em dia: silencio total. As 11 decisoes das
tres migracoes especiais, testadas caso a caso, bateram todas. Cobertura das
regex: 48 no _ADD, 2 no _DROP_NOT_NULL, 1 no _TIPO_MAIOR, ZERO caindo no
`return True` cego. E o cache invalida por tabela depois de cada tentativa,
provado com a cadeia real `identificadores` -> `sentido` -> `identificadores_maior`.
ACHADO 1, CORRIGIDO: `identificadores_maior` e um `ALTER COLUMN ... TYPE`, que o
SQLite nao aceita. Num banco onde a coluna existe com o tamanho ANTIGO, a decisao
acerta, a execucao falha com erro de sintaxe, e como a coluna nunca cresce o erro
se repete em TODO boot, para sempre. Nao afeta producao, que e Postgres; afeta
quem restaura banco antigo em SQLite para cacar bug, que e exatamente quem esta
lendo o log. A prova nao pegava porque ela nao derrubava essa coluna. Corrigido
em `e8de598`: a prova ganhou os itens 10 e 11, que montam o cenario e exigem
silencio em cinco rodadas (o 11 reprova o codigo anterior), e o codigo ganhou uma
linha que pula esse tipo de migracao em SQLite, com o motivo verdadeiro escrito:
SQLite tambem nao IMPOE o tamanho declarado num VARCHAR.
ACHADO 2, NAO VIRA CODIGO E EXPLICO POR QUE: ele apontou assimetria: quando a
COLUNA falta, o `_ADD` roda e os outros dois ramos pulam calados, enquanto o
comentario ao lado promete que nada se pula em silencio. A assimetria e
deliberada e continua: relaxar `NOT NULL` de coluna que nao existe e migracao
orfa, como a `setor_empresa_nullable`, e reportar aquilo seria a linha de erro
falso que esta fase veio tirar do log. O que estava errado era o COMENTARIO, que
prometia o que o codigo nao fazia. Reescrito, com o preco declarado: migracao de
tipo cuja coluna DEVERIA existir some sem aviso. Ele tem razao no risco; a troca
e consciente."

[2026-09-09T21:34:00] fase=19 acao=fase_fechada resultado=ok obs="A fase 19 estava
parada desde as 18:39 esperando um unico item, o 19.4, que so o usuario podia
fazer. Ele fez, a linha veio, e a fase fecha agora. Criterio de aceite completo:
provas de regressao verdes, carimbo avancando com o commit, `X-Request-ID`
diferente a cada chamada, matriz sem pendencia, e a linha de log real conferida
em producao com os oito campos. Fase 19: done."

[2026-09-09T21:34:30] fase=22 acao=codigo_fechado resultado=ok obs="Os dez itens
de codigo da fase 22 estao marcados com evidencia, e o conserto do achado do
verificador esta publicado: commit `e8de598`, producao em `20260909-2131`,
batendo com o HEAD. A fase nao muda para done ainda por um motivo so, e ele esta
no proprio criterio de aceite: o item 22.9 e conferencia visual no log do servico
`db`, que nao sai por curl. Quando o usuario disser que nao ha mais
`already exists` la, a fase fecha."
