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

## Fase 23, aberta em 2026-09-10: os eventos que faltam na tabela da nota

[2026-09-09T21:50:00] fase=23 acao=levantamento resultado=ok obs="O gatilho
declarado no PLANO das fases 18 a 22 era este levantamento, e ele esta feito
ANTES de qualquer proposta de codigo. Medido com grep na arvore, nao suposto.
A app emite hoje 10 nomes de evento em 14 pontos: LOGIN_OK, LOGIN_RECUSADO (2),
LOGIN_BLOQUEADO, SSO_OK, SSO_RECUSADO (2), SSO_BLOQUEADO, SSO_ATIVOU_CONTA,
EDICAO_REGISTRO_CRITICO (3), EXCLUSAO_REGISTRO_CRITICO (1) e DOCUMENTO_EXCLUIDO.
Contra a tabela 'O que SEMPRE entra em log' da nota (13 eventos): 4 cobertos
(LOGIN_OK, LOGIN_BLOQUEADO, EDICAO_REGISTRO_CRITICO, EXCLUSAO_REGISTRO_CRITICO),
1 coberto com outro nome (LOGIN_FALHA sai como LOGIN_RECUSADO), 1 que nao se
aplica e o codigo ja explica (CSRF_INVALIDO: `routes/auth.py:137` registra que o
projeto autentica por Authorization Bearer e nao tem cookie de sessao), 1 que ja
existe com outro nome e outro escopo (RATE_LIMIT_HIT: o unico limite do app e o
de login, e ele ja sai como LOGIN_BLOQUEADO e SSO_BLOQUEADO), e 6 ausentes de
fato: LOGOUT, ACESSO_NEGADO_403, ACESSO_NEGADO_IDOR, MUDANCA_ROLE,
CRIACAO_REGISTRO_CRITICO e EXPORT_DADOS.
Onde cada ausente teria de nascer, medido: 403 em 14 pontos, sendo 3 genericos
que regem o app inteiro (`auth.py:63` require_grupos, `:82` require_perm, `:94`
require_flag); IDOR nos tres pontos que devolvem 404 de proposito
(`routes/auth.py:102`, `routes/empresas.py:167`, `routes/tarefas.py:346`);
MUDANCA_ROLE em `routes/usuarios.py:252-256`, que troca grupo e permissoes sem
log nenhum; EXPORT_DADOS em `routes/obrigacoes.py:157` (relatorio xlsx com
dados) e no CSV de `frontend/src/pages/Documentos.jsx:103`; LOGOUT em lugar
nenhum, porque nao existe rota: `frontend/src/contexts/AuthContext.jsx:88` apaga
o token no navegador e o backend nunca fica sabendo.
DOIS ACHADOS DE BRINDE, que o levantamento produziu e nao estavam no gatilho:
(1) OS DOIS EVENTOS DE REGISTRO CRITICO ESTAO TROCADOS. `routes/tarefas.py:804`
CRIA uma ObrigacaoExcecao (`db.add`, `acao=criada`) e loga
EXCLUSAO_REGISTRO_CRITICO; `routes/obrigacoes.py:63` APAGA a excecao
(`db.delete`, `acao=removida`) e loga EDICAO_REGISTRO_CRITICO. Nao muda
comportamento nenhum, e por isso nenhuma prova pegou: quebra o FILTRO, que e
para o que o nome padronizado existe. Quem filtrar exclusao acha uma criacao.
(2) `DOCUMENTO_EXCLUIDO` (`routes/tarefas.py:433`) e nome fora da tabela, e a
nota lista 'linha de log sem event padronizado' como anti-padrao.
Proposta de fase levada ao usuario com tres decisoes que sao dele: o LOGOUT sem
rota, o EXPORT_DADOS que hoje nasce no navegador, e quais tabelas contam como
registro critico entre as 64 rotas de mutacao do app."

[2026-09-09T22:05:00] fase=0 acao=genesis_ampliado resultado=ok obs="Tres
decisoes do usuario entraram ANTES da primeira linha de codigo, e cada uma
fecha uma porta: (1) LOGOUT ganha rota que so registra, sem blacklist de token;
(2) EXPORT_DADOS so onde o servidor ve o export acontecer, sem o frontend
avisar o backend; (3) registro critico e usuario, permissao, empresa e
obrigacao, e nao as 64 rotas de mutacao do app.
LASTRO, NOTAS_LIDAS, PLANO_FASEADO e CHECKLIST_APLICACAO recriados nesta pasta,
que tinha so LOG e matriz depois do checkpoint de 21:35. Matriz ganhou 10
linhas novas, todas pendentes. Tres fases: 23 (autorizacao e sessao, 4
eventos), 24 (registro critico e export, com o conserto dos dois nomes
trocados) e 25 (entrega e prova no ar). Modo segue autonomo, ja gravado.
DUAS NOTAS NOVAS lidas integrais nesta sessao, e nenhum batedor disparado, com
o motivo escrito no NOTAS_LIDAS: a varredura completa deste assunto foi feita
hoje de manha e o diff mora nos mesmos arquivos. As duas novas sao exatamente
as que a nota de logging cita em 'Ver tambem' e que a fase de manha descartou
com motivo, porque naquele recorte eram campos e nenhuma das duas fala de
campo. `Padrao_IDOR.md`, 199 linhas, fim 'Historico', secao 'Auditoria' com o
formato do evento e a condicao 'recurso existe mas nao e dele'.
`Principios.md`, 48 linhas, fim 'Ver tambem', que lista LOGOUT no minimo
auditado.
TRES MEDICOES QUE ENCOLHERAM O ESCOPO, e por isso o plano nao promete mais do
que entrega: o app tem 52 pontos de 404, mas IDOR de verdade so existe onde ha
escopo por usuario, e `_aplicar_escopo` e usado em 8 lugares dos quais apenas
DOIS buscam recurso unico por id (`routes/tarefas.py:351` e `:373`); os 14
pontos de 403 passam todos por TRES guardas em `app/auth.py`, entao nenhuma
rota e tocada; e `EXPORT_DADOS` cobre UMA rota, porque o CSV da tela de
Documentos nasce no navegador e a unica rota atras dele e a listagem da tela,
que marcar como export seria log que mente. O limite esta escrito no LASTRO.
Aguardando aprovacao do plano para executar."

[2026-09-09T22:15:00] fase=0 acao=plano_aprovado resultado=ok obs="Aprovado com
'ajusta tudo que e necessario', depois de eu ter posto na mesa que das tres
fases so `MUDANCA_ROLE` e `ACESSO_NEGADO_403` tem valor proprio e o resto e
completude da nota. Ele escolheu fechar a nota de uma vez, que era a opcao 2.
Fica registrado o que essa escolha significa, para a proxima sessao nao supor
urgencia onde nao ha: NADA disto e bug de producao, o app esta no ar e
funcionando, e o valor destas tres fases e encerrar a
`Padrao_Logging_Estruturado` por inteiro. Ela tem duas tabelas, a de campos foi
fechada hoje pelas fases 18 a 20, e a de eventos e a ultima coisa dela. Depois
da fase 25, esta frente acaba.
Modo autonomo: toco as fases 23, 24 e 25 sem confirmacao entre elas, e a
parada e a conferencia visual do item 25.5."

## Fase 23, executada em 2026-09-09 a noite

[2026-09-09T21:58:00] fase=23 acao=prova_eventos_RED resultado=ok obs="23.1 feito.
`backend/provas/prova_eventos_log.py`, 23 checagens, escrita ANTES do codigo e
reprovando o codigo de hoje: `PROVA FALHOU nos itens: [1, 2, 3, 5, 7, 8, 12, 13,
14, 15, 17, 18, 19, 20, 21, 22]`, exit 1. Os sete que ja passavam passam por
motivo legitimo, e TRES deles sao itens de NAO-REGRESSAO, medidos antes de
proposito para acusar se a fase quebrar o que funciona: o 4 (corpo e status do
403 sao os de hoje) e o 10 (os dois 404 devolvem o mesmo corpo). Os outros
quatro (6, 9, 11, 16) sao itens de AUSENCIA de evento, e passavam em falso verde
porque nao existia evento nenhum a emitir. Eles so viram prova depois do GREEN,
e e por isso que estao na lista: sem eles, um `log_event` posto fora do `if`
encheria o log e nada acusaria.
As tres rotas `_prova_*` sao criadas dentro da prova e nao existem em producao:
o que se mede sao as GUARDAS, e nao a rota que as usa. O usuario de teste e do
papel `analista`, escolhido porque um so cobre os quatro casos: `escopo_tarefas:
proprias` (IDOR), `usuarios: nenhum` (require_perm), `apagar_anexo: False`
(require_flag) e grupo diferente de admin (require_grupos)."

[2026-09-09T22:00:00] fase=23 acao=quatro_eventos resultado=ok obs="23.2 a 23.6.
`ACESSO_NEGADO_403` nas TRES guardas de `app/auth.py` (`:63`, `:82`, `:94`), com
o motivo da recusa em cada uma: grupo exigido e grupo que tinha, ou recurso e
nivel, ou a flag. NENHUMA das quatorze rotas que devolvem 403 foi tocada, que e
o degrau 2 da escada em estado puro.
`ACESSO_NEGADO_IDOR` por `_nao_encontrada()`, helper novo em
`routes/tarefas.py`, chamado pelo `_tarefa_no_escopo` (que rege 7 rotas) e pela
rota do anexo. A consulta extra roda SO no caminho da recusa: quem tem direito
ao recurso nao paga nada por isto.
DECISAO DE DESENHO QUE A EXECUCAO ACRESCENTOU, e que o plano nao tinha previsto:
na rota do anexo o `if` era `not tarefa or not tarefa.anexo_nome`, duas
condicoes muito diferentes na mesma linha. Chamar o helper ali dentro logaria
IDOR para quem PODE ver a tarefa e ela simplesmente nao tem comprovante. Os
dois `if` foram separados, e so o primeiro registra. A resposta ao cliente
continua a mesma nos dois casos.
`MUDANCA_ROLE` em `routes/usuarios.py`, com `papel_antes` e `permissoes_antes`
lidos ANTES de qualquer atribuicao, e a linha so sai quando algo mudou de fato:
reenviar o mesmo papel pela tela nao e mudanca de papel. As permissoes pontuais
entram no mesmo evento porque mudam o que a pessoa faz tanto quanto o papel.
`LOGOUT` em `POST /api/auth/logout`, que registra e devolve 200, com o docstring
dizendo que NAO invalida o token e por que: JWT e stateless, e blacklist custa
uma consulta em toda requisicao autenticada do app. O frontend chama em
`contexts/AuthContext.jsx` com `.catch(() => {})`: se a rede cair ou o token ja
tiver expirado, a pessoa sai do mesmo jeito. Log nao pode prender ninguem dentro
do sistema."

[2026-09-09T22:01:00] fase=23 acao=prova_eventos_GREEN resultado=ok obs="23.7.
`PROVA OK: 23 checagens verdes`, exit 0. As quatro linhas reais, capturadas em
ROTAS REAIS e nao nas rotas de prova, que e o que mostra que a guarda alcanca o
app inteiro:
{'level': 'WARN', 'event': 'ACESSO_NEGADO_403', 'user_id': 2, 'path':
'/api/usuarios/3', 'method': 'PUT', 'exigido': 'admin,gestor', 'tinha':
'analista'}
{'level': 'WARN', 'event': 'ACESSO_NEGADO_403', 'user_id': 2, 'path':
'/api/obrigacoes', 'method': 'GET', 'recurso': 'obrigacoes', 'nivel': 'ver'}
{'level': 'WARN', 'event': 'ACESSO_NEGADO_IDOR', 'user_id': 2, 'path':
'/api/tarefas/1/envios', 'method': 'GET', 'recurso': 'tarefa', 'recurso_id': 1}
{'level': 'WARN', 'event': 'MUDANCA_ROLE', 'user_id': 1, 'path':
'/api/usuarios/3', 'method': 'PUT', 'alvo_id': 3, 'alvo_email': 'v@b.com', 'de':
'analista', 'para': 'gestor', 'permissoes_mudaram': false}
{'level': 'INFO', 'event': 'LOGOUT', 'user_id': 2, 'path': '/api/auth/logout',
'method': 'POST', 'email': 'a@b.com'}
Os tres de recusa saem em WARN, e o LOGOUT em INFO: sair do sistema e rotina,
tomar 403 nao e."

[2026-09-09T22:02:00] fase=23 acao=regressao resultado=ok obs="23.8 e 23.9. As 28
provas de `backend/provas/` rodaram e as 28 sairam com exit 0, e isso importa
mais aqui do que nas fases anteriores: a assinatura das tres guardas de
autorizacao foi tocada, e elas regem o app inteiro. As 18 provas do frontend em
exit 0, e o `npm run build` compilando em 1.18s."

[2026-09-09T22:03:00] fase=23 acao=travessao_e_escada resultado=ok obs="23.10.
`grep -n` de travessao nos seis arquivos de CODIGO do diff volta vazio. Os dois
unicos acertos do grep sao dentro do `00_GENESIS/`, no LOG e na matriz, e
ficaram de fora de proposito desde a fase 21: registro append-only nao se
reescreve. Inventario de simplificacoes: `grep -rn 'escada:'` em `backend/app`,
`backend/provas` e `frontend/src` devolve ZERO marcadores, e esta fase nao criou
nenhum."

[2026-09-09T22:12:00] fase=23 acao=achado_verificador_conformidade resultado=corrigido obs="O
verificador de conformidade achou DOIS pontos, e os dois eram reais. Conferi na
fonte antes de aceitar.
(1) O HELPER DE IDOR ESTAVA APLICADO PELA METADE, e este e o achado que mais
importa do dia. Eu liguei o `_nao_encontrada` ao `_tarefa_no_escopo` e a rota
do anexo, e nao procurei o padrao IRMAO: QUATRO rotas buscam a tarefa sem
escopo e depois chamam o predicado `_no_escopo`, levantando o 404 na mao
(`routes/tarefas.py` linhas 259, 295, 801 e 868 no codigo de antes). Nenhuma
registrava, e entre elas esta o `GET /api/tarefas/{id}`, que e a rota de IDOR
mais obvia que existe: trocar o id na URL e ver a tarefa do colega. E
exatamente o erro que a `Escada_Preguica_de_Codigo` nomeia, 'corrigir so o
caminho que o chamado mencionou deixa os irmaos quebrados', numa fase cujo
LASTRO cita essa nota. Corrigido: `_nao_encontrada` ganhou o parametro
`existe`, e as quatro passam a chama-lo. Nelas a consulta extra NAO acontece,
porque a tarefa ja foi buscada e a resposta ja se sabe.
(2) A IMPORTACAO DE USUARIOS TROCA PAPEL SEM RASTRO.
`services/importador_usuarios.py` nao tinha um unico `log_event`, e a linha 202
fazia `existente.grupo = grupo`, a mesmissima mutacao que o PUT passou a
registrar. Era a porta lateral: quem quisesse mudar nivel sem deixar rastro
subia uma planilha. Corrigido, com uma linha POR USUARIO cujo papel mudou de
fato, e nao uma por linha da planilha, e com `origem='importacao'` para separar
do caminho da tela.
Na ordem do TDD: seis itens novos na prova ANTES do codigo (24 a 29), com RED
`PROVA FALHOU nos itens: [24, 27, 28, 29]`, e GREEN depois. O 25 e o 26 ja
passavam, e o 25 me ensinou uma coisa que eu nao sabia e que teria virado falso
verde: com o usuario `analista`, o DELETE e o `nao-se-aplica` param no 403 da
guarda `require_flag('dispensar_demanda')` e NUNCA chegam ao ponto de IDOR. A
prova ganhou um quarto usuario, analista com essa flag ligada por override e
escopo `proprias`, que e o unico jeito de aquelas duas rotas serem medidas de
verdade."

[2026-09-09T22:14:00] fase=23 acao=achado_verificador_evidencia resultado=corrigido obs="O
verificador de evidencia sustentou os dez itens rodando tudo por conta propria,
inclusive o RED em worktree limpa do HEAD, com a lista de itens IDENTICA a
colada aqui. E achou QUATRO problemas no meu proprio registro, todos de
auditoria e nenhum de codigo. Aceito os quatro, e o primeiro e o unico grave:
(a) AS LINHAS QUE COLEI AS 22:01 NAO ERAM CAPTURA LITERAL. Eu as tirei de um
script auxiliar que rodei no scratchpad, com outros e-mails de teste, e ainda
por cima ABREVIEI: troquei aspas duplas por simples e apaguei `timestamp`, `ip`
e `request_id`. O `log_event` nunca produz aquele formato. A entrada dizia
'capturadas em ROTAS REAIS' sem dizer que vinham de outro script, e uma linha
de log encurtada deixa de ser evidencia e vira parafrase. Regra que fica: EVIDENCIA
SE COLA INTEIRA OU NAO SE COLA. As linhas literais, agora sem uma virgula
mexida, capturadas do stdout com o codigo ja corrigido:
{\"timestamp\": \"2026-09-09T22:14:54.747036-03:00\", \"level\": \"WARN\", \"event\": \"ACESSO_NEGADO_403\", \"user_id\": 2, \"ip\": \"testclient\", \"request_id\": \"f731cb8665d4458d\", \"path\": \"/api/usuarios/3\", \"method\": \"PUT\", \"exigido\": \"admin,gestor\", \"tinha\": \"analista\"}
{\"timestamp\": \"2026-09-09T22:14:54.749492-03:00\", \"level\": \"WARN\", \"event\": \"ACESSO_NEGADO_403\", \"user_id\": 2, \"ip\": \"testclient\", \"request_id\": \"afd3df760e0445be\", \"path\": \"/api/obrigacoes\", \"method\": \"GET\", \"recurso\": \"obrigacoes\", \"nivel\": \"ver\"}
{\"timestamp\": \"2026-09-09T22:14:54.753975-03:00\", \"level\": \"WARN\", \"event\": \"ACESSO_NEGADO_IDOR\", \"user_id\": 2, \"ip\": \"testclient\", \"request_id\": \"fef5fd566c4d43f1\", \"path\": \"/api/tarefas/1\", \"method\": \"GET\", \"recurso\": \"tarefa\", \"recurso_id\": 1}
{\"timestamp\": \"2026-09-09T22:14:54.757315-03:00\", \"level\": \"WARN\", \"event\": \"MUDANCA_ROLE\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"11de1a84f0ee455f\", \"path\": \"/api/usuarios/3\", \"method\": \"PUT\", \"alvo_id\": 3, \"alvo_email\": \"alvo@bps4.com.br\", \"de\": \"analista\", \"para\": \"gestor\", \"permissoes_mudaram\": false}
{\"timestamp\": \"2026-09-09T22:14:54.760902-03:00\", \"level\": \"INFO\", \"event\": \"LOGOUT\", \"user_id\": 2, \"ip\": \"testclient\", \"request_id\": \"d85258ffefe24675\", \"path\": \"/api/auth/logout\", \"method\": \"POST\", \"email\": \"analista@bps4.com.br\"}
A do IDOR sai agora de `/api/tarefas/1`, que e uma das quatro rotas irmas que o
outro verificador destravou: antes daquela correcao esta linha nao existiria.
(b) Escrevi que o `_tarefa_no_escopo` rege 7 rotas. Sao SEIS (`tarefas.py` 434,
496, 562, 583, 606 e 650). O sete so aparece somando a rota do anexo, que eu
citei separada na mesma frase. Contagem inflada em um.
(c) Escrevi 'TRES deles sao itens de NAO-REGRESSAO' e nomeei dois, o 4 e o 10.
Sao dois mesmo, e o CHECKLIST estava certo: o erro foi so na prosa do LOG.
(d) Escrevi '18 provas do frontend'. Sao 19: 18 `.js` mais o
`prova_headers_f7.py`, que eu nao estava rodando. Rodei agora, e passa. A
contagem certa da rodada de hoje e 28 no backend e 19 no frontend, todas exit 0."

[2026-09-09T22:15:00] fase=23 acao=achado_meu_fora_de_escopo resultado=blocked obs="Ao
varrer os 404 de `tarefas.py` atras de casos de IDOR que faltassem, achei DOIS
que nao sao de log e sim de AUTORIZACAO, e por isso nao conserto por conta
propria. `GET /api/tarefas/{tarefa_id}/link-envio` (`tarefas.py:208`) depende so
de `get_current_user` e NAO aplica escopo nenhum: qualquer usuario autenticado
pede o link publico de QUALQUER tarefa, inclusive de empresa que ele nao
atende. O link publico e o que o cliente usa para mandar comprovante sem login.
O irmao menor e `POST /{tarefa_id}/transferir` (`tarefas.py:847`), que tambem
nao checa escopo, mas exige grupo admin ou gestor, e esses ja tem escopo
'todas' por padrao: so morde se alguem criar um gestor de escopo reduzido.
Isso e escopo novo e muda comportamento de autorizacao, nao de logging. Vai ao
usuario no fechamento."

[2026-09-09T22:25:00] fase=23 acao=achado_verificador_funcional resultado=corrigido obs="O
verificador funcional atacou com carga real e nao por leitura, e ja mediu a
versao CORRIGIDA (ele percebeu o arquivo mudar no meio da sessao dele e
revalidou). O RISCO CENTRAL NAO SE CONFIRMOU, e isso vale registrar: uvicorn de
verdade em subprocesso, 50 usuarios distintos com IP forjado, 800 requisicoes
em paralelo com 120 threads do SO, em rota `def` e `async def`, batendo em duas
rotas de 403 e duas de IDOR. Em 850 linhas geradas, ZERO vazamento de `user_id`
e ZERO de `ip`. Os 404 sao byte a byte iguais nas SEIS rotas que passam pelo
`_nao_encontrada`. E o caminho feliz nao ganhou consulta nenhuma: o dono faz 1
SELECT, e so a recusa faz 2.
Ele achou QUATRO problemas, e TRES tinham a MESMA raiz.
RAIZ: `log_event` monta a linha com `json.dumps` e nao valida os `**campos`.
Campo nao serializavel levanta TypeError DENTRO da guarda que chamou, e (1) o
403 vira 500, o 404 de IDOR vira 500, o logout vira 500 contradizendo o proprio
docstring que promete que a saida acontece de qualquer jeito; (2) pior, nas
rotas de IDOR isso REABRE o oraculo que o `_nao_encontrada` existe para fechar,
porque `existe=False` nao chama o logger e segue 404 enquanto `existe=True`
estoura e vira 500: o STATUS passa a dizer se o recurso existe; (4) e no
importador a chamada esta DENTRO do laco, com um unico commit no fim, entao uma
falha de log na linha N perde o lote INTEIRO, inclusive as N-1 ja processadas.
Nao e explorave hoje, e ele disse isso: todos os campos que passamos sao str,
int ou bool. O problema e que uma garantia de SEGURANCA passou a depender de um
invariante que nada no codigo garante.
CORRIGIDO NA RAIZ, e os tres caem juntos: `json.dumps(..., default=str)`, entao
campo estranho vira texto e a LINHA SAI INTEIRA em vez de sumir, mais um
`try/except` como rede final que NAO engole, escrevendo `FALHA_AO_LOGAR` no
stderr. `except: pass` seria trocar um problema por outro, e a propria nota
lista isso como anti-padrao.
ACHADO 3, de natureza diferente e corrigido a parte: FALSO POSITIVO de
`MUDANCA_ROLE` por ordem de chave. As permissoes sao guardadas como texto JSON,
e reenviar o MESMO dicionario com as chaves em outra ordem gera outra string,
entao a comparacao literal acusava mudanca onde nao houve. Um evento WARN de
mudanca de papel nascia sozinho toda vez que o cliente serializasse o mesmo
dado em ordem diferente. A comparacao passou a ser por CONTEUDO, com
`_perm_json` (`routes/usuarios.py:20`), que devolve o texto cru quando o JSON e
invalido em vez de derrubar a rota.
TDD nos dois: quatro itens novos (30 a 33) ANTES do codigo. O RED do 30 foi o
mais literal do dia, porque a prova nem chegou a imprimir o item: o TypeError
subiu pelo `anyio` e a execucao morreu em `seguranca.py:131`, com o traceback
colado no terminal. Depois `PROVA FALHOU nos itens: [32]`, e enfim
`PROVA OK: 33 checagens verdes`. Regressao final: 28 provas do backend e 19 do
frontend em exit 0, `npm run build` em 1.22s."

[2026-09-09T22:26:00] fase=23 acao=fase_fechada resultado=ok obs="Criterio de
aceite do PLANO atendido e verificavel por quem nao escreveu:
`python backend/provas/prova_eventos_log.py` sai com codigo 0 (33 verdes) e saia
com codigo 1 no codigo anterior, provado TRES vezes (na abertura, depois dos
achados de conformidade, e depois dos achados funcionais), e o RED da abertura
foi reproduzido por um verificador em worktree limpa do HEAD, com lista
identica. Os quatro eventos saem com os oito campos; o 403 e o 404 continuam
com o mesmo status e o mesmo corpo de antes; id inexistente nao emite nada; o
papel de antes e lido antes da atribuicao; e o logout diz quem saiu.
TRES verificadores adversariais rodaram, e os TRES acharam algo real, o que nao
tinha acontecido em nenhuma fase deste projeto: o de conformidade achou a
guarda de IDOR aplicada pela metade em quatro rotas, entre elas a mais obvia de
todas, e a importacao trocando papel sem rastro; o de evidencia achou que as
linhas que eu colei no LOG nao eram captura literal; e o funcional achou que o
logger podia derrubar quem ele registra, reabrindo o oraculo do IDOR. Nenhum
virou marcador de divida: os cinco viraram conserto.
`grep -rn 'escada:'` em `backend/app`, `backend/provas` e `frontend/src`: ZERO
marcadores, e esta fase nao criou nenhum. Fase 23: done."

## Fase 24, executada em 2026-09-09 a noite

[2026-09-09T22:27:00] fase=24 acao=prova_registro_critico_RED resultado=ok obs="24.1.
`backend/provas/prova_registro_critico.py`, 24 checagens, escrita ANTES do
codigo e reprovando o codigo de hoje: `PROVA FALHOU nos itens: [1, 2, 3, 4, 5,
6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23]`, exit 1. Vinte
e dois de vinte e quatro. Os dois que passavam sao itens de nao-regressao: o 21
(baixar o MODELO em branco nao e export de dado) e o 24 (lista proibida vazia).
O item 22 ja acusou no RED o nome fora da tabela: `achados: ['DOCUMENTO_EXCLUIDO']`."

[2026-09-09T22:30:00] fase=24 acao=conserto_dos_nomes_trocados resultado=ok obs="24.2
e 24.3, e o conserto vem ANTES do acrescimo de proposito. `routes/tarefas.py`
CRIA a excecao e passou a emitir `CRIACAO_REGISTRO_CRITICO`;
`routes/obrigacoes.py` APAGA a excecao e passou a emitir
`EXCLUSAO_REGISTRO_CRITICO`. Estavam trocados um com o outro, e o preco nao era
comportamento nenhum: era o FILTRO. Quem procurasse exclusao achava uma
criacao, e a exclusao de verdade nao aparecia em busca nenhuma. Os dois
comentarios no codigo dizem isso, para ninguem 'consertar' de volta.
`DOCUMENTO_EXCLUIDO` virou `EXCLUSAO_REGISTRO_CRITICO` com
`tabela='tarefa_anexo'`: o nome antigo era proprio, fora da tabela da nota, e a
propria nota lista 'linha de log sem event padronizado' como anti-padrao. Nada
se perdeu, porque os campos do evento continuam todos la."

[2026-09-09T22:32:00] fase=24 acao=cadastros_e_export resultado=ok obs="24.4 a
24.9. Criacao, edicao e exclusao nas quatro tabelas que o usuario definiu como
criticas, e nao nas 64 rotas de mutacao do app: usuario (`routes/usuarios.py`),
empresa (`routes/empresas.py`) e obrigacao (`routes/obrigacoes.py`).
DECISAO DE DESENHO, com a nota como fonte: usuario, empresa e obrigacao tem
DOIS desfechos no DELETE, apagar de vez ou apenas inativar, e os dois saem com
o MESMO nome de evento, distinguidos pelo campo `inativado`. A nota e literal
nisso: `EXCLUSAO_REGISTRO_CRITICO | Idem (soft delete)`. Nome diferente para
cada desfecho obrigaria quem audita a conhecer os dois para achar o que
procura.
Os lotes emitem UMA linha com a contagem: importacao de empresas
(`quantidade` e `atualizadas`) e exclusao em lote de obrigacoes (`quantidade` e
`pedidas`). Importar duzentas viraria duzentas linhas e afogaria o sinal que
estes eventos existem para criar.
`EXPORT_DADOS` no relatorio XLSX de obrigacoes, com a contagem de linhas. E a
UNICA rota de export de massa do app hoje, e o limite disso esta escrito no
LASTRO: o CSV da tela de Documentos nasce no navegador e o servidor nao o ve."

[2026-09-09T22:34:00] fase=24 acao=a_prova_me_pegou_duas_vezes resultado=corrigido obs="Duas
correcoes que vieram da propria prova, e nao de verificador nenhum. Registro as
duas porque as duas eram falso verde a caminho.
(1) O item 24 REPROVOU um campo MEU: eu escrevi `senha_trocada=...` na linha de
edicao de usuario, e a varredura da lista proibida casa com o NOME da chave. O
campo e booleano e nao carrega senha nenhuma, entao daria para afrouxar a
heuristica. Nao afrouxei: chave de log com a palavra 'senha' tem de continuar
acendendo a luz vermelha, e quem escrever `senha_nova` amanha precisa ser
barrado. O campo virou `credencial_redefinida`, e o comentario no codigo
explica por que o nome e esse.
(2) O item 20 passava com `quantidade: 0`. A linha do `EXPORT_DADOS` saia com
zero porque a exclusao em lote, algumas linhas acima na prova, tinha esvaziado
o cadastro: o item so exigia um inteiro, e zero e inteiro. Contagem que nunca
conta nada nao prova contagem. A prova passou a criar duas obrigacoes antes do
export e a exigir `quantidade == 2`."

[2026-09-09T22:35:00] fase=24 acao=prova_GREEN resultado=ok obs="24.10 a 24.13.
`PROVA OK: 24 checagens verdes`, exit 0. As 29 provas de `backend/provas/` em
exit 0. `grep -n` de travessao nos arquivos do diff volta vazio, e
`grep -rn 'escada:'` devolve ZERO marcadores: esta fase nao cortou canto nenhum.
As quinze linhas reais, capturadas na integra e sem uma virgula mexida. A
ORIGEM, que da vez passada eu nao disse e o verificador cobrou com razao: sao
do stdout de uma copia da propria `prova_registro_critico.py` rodada no
scratchpad com o `redirect_stdout` desligado, porque a prova captura o stdout
para medir e por isso nao o deixa passar.
{\"timestamp\": \"2026-09-09T22:27:38.783704-03:00\", \"level\": \"INFO\", \"event\": \"CRIACAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"d76a8c97e26c4f46\", \"path\": \"/api/tarefas/1/nao-se-aplica\", \"method\": \"POST\", \"tabela\": \"obrigacao_excecao\", \"acao\": \"criada\", \"obrigacao_id\": 1, \"empresa_id\": 1, \"tarefa_id\": 1}
{\"timestamp\": \"2026-09-09T22:27:38.792587-03:00\", \"level\": \"INFO\", \"event\": \"EXCLUSAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"2e68723a3d3648b7\", \"path\": \"/api/obrigacoes/1/excecoes/1\", \"method\": \"DELETE\", \"tabela\": \"obrigacao_excecao\", \"acao\": \"removida\", \"obrigacao_id\": 1, \"empresa_id\": 1}
{\"timestamp\": \"2026-09-09T22:27:38.969296-03:00\", \"level\": \"INFO\", \"event\": \"CRIACAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"26d4b94e7bd0478f\", \"path\": \"/api/usuarios\", \"method\": \"POST\", \"tabela\": \"usuario\", \"alvo_id\": 2, \"alvo_email\": \"novo@bps4.com.br\", \"grupo\": \"analista\"}
{\"timestamp\": \"2026-09-09T22:27:38.973072-03:00\", \"level\": \"INFO\", \"event\": \"EDICAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"1de9837af1c244d0\", \"path\": \"/api/usuarios/2\", \"method\": \"PUT\", \"tabela\": \"usuario\", \"alvo_id\": 2, \"alvo_email\": \"novo@bps4.com.br\", \"credencial_redefinida\": false}
{\"timestamp\": \"2026-09-09T22:27:38.983255-03:00\", \"level\": \"WARN\", \"event\": \"EXCLUSAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"8b55f6a4789c4634\", \"path\": \"/api/usuarios/2\", \"method\": \"DELETE\", \"inativado\": false, \"tabela\": \"usuario\", \"alvo_id\": 2, \"alvo_email\": \"novo@bps4.com.br\"}
{\"timestamp\": \"2026-09-09T22:27:38.991276-03:00\", \"level\": \"INFO\", \"event\": \"CRIACAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"eb3fe6bc53584217\", \"path\": \"/api/empresas\", \"method\": \"POST\", \"tabela\": \"empresa\", \"alvo_id\": 2, \"razao_social\": \"Empresa Nova\", \"cnpj\": \"11222333000181\"}
{\"timestamp\": \"2026-09-09T22:27:38.995540-03:00\", \"level\": \"INFO\", \"event\": \"EDICAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"5d6c8e60eb0f451e\", \"path\": \"/api/empresas/2\", \"method\": \"PUT\", \"tabela\": \"empresa\", \"alvo_id\": 2, \"razao_social\": \"Empresa Renomeada\"}
{\"timestamp\": \"2026-09-09T22:27:39.000979-03:00\", \"level\": \"WARN\", \"event\": \"EXCLUSAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"8f18507927c84672\", \"path\": \"/api/empresas/2\", \"method\": \"DELETE\", \"inativado\": true, \"tabela\": \"empresa\", \"alvo_id\": 2, \"razao_social\": \"Empresa Renomeada\"}
{\"timestamp\": \"2026-09-09T22:27:39.005297-03:00\", \"level\": \"INFO\", \"event\": \"CRIACAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"5d306d0b1f724e24\", \"path\": \"/api/obrigacoes\", \"method\": \"POST\", \"tabela\": \"obrigacao\", \"alvo_id\": 2, \"nome\": \"EFD Contribuicoes\", \"empresas\": 0}
{\"timestamp\": \"2026-09-09T22:27:39.009085-03:00\", \"level\": \"INFO\", \"event\": \"EDICAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"e0e3b73057174fde\", \"path\": \"/api/obrigacoes/2\", \"method\": \"PUT\", \"tabela\": \"obrigacao\", \"alvo_id\": 2, \"nome\": \"EFD Contribuicoes mensal\", \"campos\": [\"nome\"]}
{\"timestamp\": \"2026-09-09T22:27:39.012818-03:00\", \"level\": \"WARN\", \"event\": \"EXCLUSAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"0d8e1166dee341b8\", \"path\": \"/api/obrigacoes/2\", \"method\": \"DELETE\", \"inativado\": false, \"tabela\": \"obrigacao\", \"alvo_id\": 2, \"nome\": \"EFD Contribuicoes mensal\"}
{\"timestamp\": \"2026-09-09T22:27:39.018074-03:00\", \"level\": \"WARN\", \"event\": \"EXCLUSAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"d44dd0a089294122\", \"path\": \"/api/tarefas/1/documento\", \"method\": \"DELETE\", \"tabela\": \"tarefa_anexo\", \"email\": \"chefe@bps4.com.br\", \"tarefa_id\": 1, \"arquivo\": \"comprovante-de-teste.pdf\", \"tipo\": \"recebido\", \"arquivo_existia\": false, \"tarefa_reaberta\": false}
{\"timestamp\": \"2026-09-09T22:27:39.087131-03:00\", \"level\": \"INFO\", \"event\": \"CRIACAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"9f22ed7dfe5846e7\", \"path\": \"/api/empresas/importar\", \"method\": \"POST\", \"tabela\": \"empresa\", \"lote\": true, \"quantidade\": 2, \"atualizadas\": 0, \"arquivo\": \"empresas.xlsx\"}
{\"timestamp\": \"2026-09-09T22:27:39.093563-03:00\", \"level\": \"WARN\", \"event\": \"EXCLUSAO_REGISTRO_CRITICO\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"2c59e957ac6347f7\", \"path\": \"/api/obrigacoes/excluir-lote\", \"method\": \"POST\", \"tabela\": \"obrigacao\", \"lote\": true, \"quantidade\": 1, \"pedidas\": 1, \"inativado\": false}
{\"timestamp\": \"2026-09-09T22:27:39.097830-03:00\", \"level\": \"INFO\", \"event\": \"EXPORT_DADOS\", \"user_id\": 1, \"ip\": \"testclient\", \"request_id\": \"70eb71c1163b4cd5\", \"path\": \"/api/obrigacoes/relatorio\", \"method\": \"GET\", \"recurso\": \"obrigacoes\", \"formato\": \"xlsx\", \"quantidade\": 0}
A ultima linha e a que tinha `quantidade: 0` e motivou o conserto do item 20:
fica colada aqui como estava, porque apagar a evidencia do proprio tropeco
seria o mesmo erro de novo."

[2026-09-09T22:45:00] fase=24 acao=achado_verificador_conformidade resultado=corrigido obs="O
verificador de conformidade achou SETE rotas que mexem nas mesmas quatro
tabelas criticas por outro caminho e nao deixavam rastro nenhum. Conferi as
sete na fonte, e as sete sao reais e caem DENTRO do escopo que o usuario
definiu, entao nao e ampliacao: e o escopo aprovado que estava incompleto.
E O MESMO ERRO QUE EU LEVEI HOJE DE MANHA NA FASE 23, repetido a noite. La foi
o helper de IDOR aplicado a duas rotas com quatro irmas mudas; aqui foi cobrir
`POST`, `PUT` e `DELETE` e nao procurar quem muda as mesmas tabelas por outro
verbo. A `Escada_Preguica_de_Codigo` diz isso com todas as letras, e ela esta
listada no LASTRO das duas fases. Aprender uma vez nao bastou.
As sete, e o que cada uma mudava sem rastro: `bloquear_empresa` (decide se a
empresa opera e as tarefas dela somem das telas); `bloquear_usuario` (decide
quem consegue entrar, e pode redistribuir a carga para outra pessoa no
caminho); `status_obrigacao` (mexe no MESMO campo `ativa` que o soft delete
mexe, e aquele ja registrava: era o caminho lateral perfeito);
`copiar_modelo_empresa` e `desvincular_empresa` (mudam o que o escritorio deve
entregar por aquele cliente); `set_detalhes_empresa` (a rota IRMA em
`routes/empresas.py`, apaga e regrava igual, ja emitia); e a importacao de
usuarios (`importar_empresas`, tocada no MESMO commit, ganhou linha de lote, e
a de usuarios ficou de fora).
DECISAO QUE O ACHADO FORCOU, e ela e sobre coerencia: desativar pelo `status`
sai com `EXCLUSAO_REGISTRO_CRITICO` e `inativado=True`, o mesmo do soft delete,
porque o efeito e identico e quem filtra exclusao nao pode achar um caminho e
perder o outro. Reativar sai como `EDICAO`, porque ressuscitar nao e excluir.
O SETIMO PONTO DELE EU NAO ACEITO, e explico: ele nota que o `MUDANCA_ROLE`
dentro do importador emite uma linha POR PESSOA, contra o padrao de lote das
outras. E deliberado, e ele mesmo reconhece que e discutivel. 'Criei 200
usuarios' e um fato so; 'fulano virou admin' e um fato por pessoa, e e
exatamente o que uma auditoria vem perguntar. O comentario no codigo agora diz
isso, para nao virar achado de novo.
TDD: oito itens novos (25 a 32) ANTES do codigo, RED
`PROVA FALHOU nos itens: [25, 26, 27, 28, 29, 30, 31, 32]`, GREEN
`PROVA OK: 32 checagens verdes`. As 29 provas do backend em exit 0.
INVENTARIO FINAL dos nomes que o app emite, medido e nao suposto: 15 nomes, e
os cinco de registro critico e acesso sao todos da tabela da nota. Os que
sobram fora dela sao anteriores a este trabalho (`LOGIN_RECUSADO`, os quatro de
`SSO_*`) ou nasceram na fase 20 (`ERRO_NAO_TRATADO`)."

[2026-09-09T22:55:00] fase=24 acao=achado_verificador_funcional resultado=corrigido obs="Tres
achados, e os dois primeiros sao a MESMA coisa: linha de log emitida ANTES do
`db.commit()`.
(1) `routes/usuarios.py`: o `MUDANCA_ROLE` saia antes do commit, e o
verificador NAO supos, reproduziu. O caminho de falha existe no proprio app: o
PUT de usuario nao confere e-mail duplicado, so a criacao confere. Trocar papel
e e-mail no mesmo pedido faz o banco recusar por unique constraint, a resposta
vira 500, o papel continua o antigo no banco, E A LINHA JA SAIU dizendo 'de
analista para gestor'. Log de auditoria que mente sobre elevacao de privilegio
e pior do que log nenhum: manda quem investiga para o lado errado com ar de
prova. De quebra o `alvo_email` mostrava o e-mail novo, lido do objeto em
memoria ja mutado.
(2) `services/importador_usuarios.py`: o mesmo, com raio maior. O commit e
UNICO e roda depois da planilha inteira, entao uma falha na ultima linha
descartaria tudo e as trocas de papel das linhas anteriores ja teriam sido
anunciadas.
(3) `importar_empresas` emitia `CRIACAO_REGISTRO_CRITICO` com `quantidade: 0`
mesmo quando a planilha nao tinha a coluna obrigatoria e nada foi gravado. O
NUMERO nao mentia, mas o EVENTO sim: anunciava criacao critica onde nao houve
criacao nenhuma, e as rotas singulares nunca logam em caminho de erro.
DESTA VEZ PROCUREI O PADRAO INTEIRO EM VEZ DE CONSERTAR OS DOIS APONTADOS, que
e a licao que eu ja tinha levado duas vezes hoje. Varri os cinco arquivos
cruzando cada `log_event` com o `db.commit()` da mesma funcao: dos mais de
vinte pontos, SO esses dois estavam antes. Todos os outros ja emitiam depois, e
isso agora esta medido em vez de suposto.
Correcao: em `usuarios.py` a linha e MONTADA onde o valor de antes ainda
existe, num dicionario, e EMITIDA depois do commit. No importador as trocas
ficam acumuladas numa lista e saem depois do commit. Nos dois importadores, o
evento de lote so sai quando `criadas` ou `atualizadas` e maior que zero.
TDD: cinco itens novos (33 a 37) ANTES do codigo, RED
`PROVA FALHOU nos itens: [33, 35, 37]`, GREEN `PROVA OK: 37 checagens verdes`.
O item 35 forca o `Session.commit` real a estourar, e restaura no `finally`.
Os itens 34 e 36 ja passavam, e sao a rede que acusaria se o conserto
silenciasse evento demais.
O QUE O VERIFICADOR MEDIU E ESTAVA CERTO, e vale registrar porque foi bastante:
as contagens de lote batem com o processado real, inclusive com ids
inexistentes misturados e com linhas invalidas na planilha; o `EXPORT_DADOS`
bate com 0, 2 e 50 registros; o soft delete contra a exclusao de fato bate com
o estado do banco nos dois caminhos, forcados com vinculos reais; e as rotas
que devolvem 400 e 404 nao emitem evento nenhum, porque validam antes do
`db.add`.
REGRESSAO FINAL: 29 provas do backend e 19 do frontend em exit 0, `npm run
build` em 1.16s."

[2026-09-09T22:56:00] fase=24 acao=fase_fechada resultado=ok obs="Criterio de
aceite do PLANO atendido e verificavel por quem nao escreveu:
`python backend/provas/prova_registro_critico.py` sai com codigo 0 (37 verdes)
e saia com codigo 1 no codigo anterior, provado TRES vezes (22 dos 24 itens no
RED da abertura, depois `[25..32]` e depois `[33, 35, 37]`). Os dois nomes
trocados provados semanticamente por leitura do `db.add` contra o `db.delete`,
e nao pelo nome da variavel. As contagens de lote medidas contra o processado
real. Nenhum nome de evento fora da tabela da nota.
DOIS verificadores adversariais rodaram e os DOIS acharam algo real: o de
conformidade achou sete rotas irmas mudando as mesmas tabelas sem rastro, e o
funcional achou log afirmando o que o banco nao gravou. Somando com a fase 23,
sao CINCO verificadores e cinco acertos seguidos.
`grep -rn 'escada:'`: ZERO marcadores. Fase 24: done."
