# Plano faseado: campos obrigatórios no logger central

modo=autonomo (escolhido em 2026-09-09)
plano aprovado em 2026-09-09, sem ajustes

As fases 1 a 17 estão fechadas e arquivadas nos dois checkpoints desta pasta.
A numeração continua de lá.

## Fase 0: aprovação deste plano

- **Status:** pending
- **Critério de aceite:** o usuário aprova, e a aprovação fica registrada no LOG.

## Fase 18: os cinco campos entram sozinhos no `log_event`

- **Status:** done (2026-09-09)
- **Duração estimada:** 1 sessão curta
- **Notas que regem:** `Padrao_Logging_Estruturado`, `Mapa_de_Conceitos_de_Seguranca`
  (Família 6), `Escada_Preguica_de_Codigo`, `TDD_RED_GREEN_REFACTOR`, `Sem_Travessao`
- **Dependências:** nenhuma
- **Output esperado:** toda linha de log do app sai com `timestamp`, `level`,
  `event`, `request_id`, `path`, `method`, `user_id` e `ip`, sem que nenhum dos
  14 chamadores tenha sido reescrito para isso.

O desenho, para o critério não ficar vago: um middleware ASGI abre o request,
gera o `request_id` e guarda o contexto em `contextvars`; o `log_event` lê esse
contexto e preenche o que faltar com `setdefault`, de modo que chamador que já
manda o campo continua mandando o dele. O `user_id` é gravado no contexto quando
a dependência de autenticação resolve o usuário, que é o único ponto do app onde
ele existe.

**Critério de aceite, verificável por quem não escreveu:** rodar
`python backend/provas/prova_logging.py` devolve todos os itens `ok` e sai com
código 0, e a mesma prova sai com código 1 no código de hoje. Entre os itens,
obrigatoriamente: uma linha de log emitida dentro de um request tem os oito
campos; duas requisições distintas têm `request_id` diferente; a mesma requisição
tem o mesmo `request_id` em duas linhas; log emitido fora de request (scheduler)
não quebra e traz os campos como `null`; e nenhum campo da lista proibida da
nota aparece na linha.

## Fase 19: entrega, prova no ar e matriz fechada

- **Status:** pending
- **Duração estimada:** 1 sessão curta
- **Notas que regem:** `Fechar_Tarefa_Rodar_Verifica`, `Padrao_Logging_Estruturado`
- **Dependências:** fase 18
- **Output esperado:** a mudança publicada e provada em produção, não só na
  máquina.

**Critério de aceite:** as provas de regressão que tocam autenticação
(`prova_sso_f3.py`, `prova_seguranca_f7.py`) continuam verdes; o carimbo de
`/api/health` avança para o commit desta fase; e
`curl -sI https://gestordetarefas.zoaria.com.br/api/health` devolve o cabeçalho
`X-Request-ID` com valor diferente a cada chamada. A matriz
`CONFORMIDADE_VAULT.md` fecha sem linha pendente das fases 18 e 19.

## Fase 20: a resposta de erro para de sair pelada

- **Status:** done (2026-09-09)
- **Aberta em:** 2026-09-09, a pedido do usuário, depois do achado do verificador
  funcional da Fase 18. Não estava no plano aprovado de manhã.
- **Duração estimada:** 1 sessão curta
- **Notas que regem:** `CSRF_Cookies_Headers` (seção "Headers de segurança (em
  toda resposta)"), `Padrao_Logging_Estruturado`, `Mapa_de_Conceitos_de_Seguranca`
  (Família 6), `Revisao_Vulnerabilidades` (item 9), `Escada_Preguica_de_Codigo`,
  `TDD_RED_GREEN_REFACTOR`, `Fechar_Tarefa_Rodar_Verifica`, `Sem_Travessao`
- **Dependências:** fase 18 (o contexto de log é o que essa fase carrega para o
  handler)
- **Output esperado:** exceção não tratada devolve 500 com corpo genérico, com os
  cabeçalhos de segurança e com o `X-Request-ID` que liga aquela tela de erro à
  linha de log do request que quebrou.

O problema, medido e não suposto: `ServerErrorMiddleware` do Starlette é o mais
externo de todos, então quando a rota levanta exceção sem tratamento a resposta
sai por fora dos nossos dois middlewares. Prova do verificador: `GET` numa rota
que só faz `raise ValueError` volta 500 sem `X-Request-ID` e sem
`X-Content-Type-Options`. A parte dos cabeçalhos é anterior a esta fase e vale
para todo erro 500 que o app já deu.

O desenho, para o critério não ficar vago: `abrir_contexto` passa a gravar o id
também em `request.state`, que vive no `scope` e por isso atravessa a fronteira
de task; e um `@app.exception_handler(Exception)` emite `ERRO_NAO_TRATADO` e monta
a resposta genérica, reusando o `aplicar_headers` que já existe. O handler lê o id
do `state`, e não da `contextvar`, justamente porque roda em contexto ancestral.

**Ponto que a execução tem de medir, e não presumir:** registrar handler de
`Exception` não pode fazer o traceback sumir do stdout. Se sumir, o conserto trocou
um problema por outro pior, e a fase muda de desenho.

**Critério de aceite, verificável por quem não escreveu:**
`python backend/provas/prova_erro_500.py` sai com código 0, e com código 1 no
código de hoje. Entre os itens, obrigatoriamente: a resposta de erro traz
`X-Request-ID` igual ao `request_id` da linha de log daquele request; traz os
cabeçalhos de segurança da nota; o corpo NÃO carrega traceback, nome de exceção,
caminho de arquivo nem query; a linha `ERRO_NAO_TRATADO` sai com os oito campos; e
o traceback continua aparecendo no stdout do servidor. Publicado, com o carimbo de
`/api/health` batendo com o HEAD.

## Fase 21: travessão fora de comentário e docstring

- **Status:** pending
- **Aberta em:** 2026-09-09, a pedido do usuário, junto com a Fase 20.
- **Duração estimada:** 1 sessão curta
- **Notas que regem:** `Sem_Travessao`, `Escada_Preguica_de_Codigo` (mudança
  cirúrgica), `Fechar_Tarefa_Rodar_Verifica`
- **Dependências:** nenhuma. Roda depois da 20 só para não misturar diff de
  segurança com diff de escrita.
- **Output esperado:** zero travessão no projeto inteiro, e não só no texto que
  aparece na tela.

O que a varredura de 2026-09-09 de manhã fez, e o que ela não fez: zerou 51
travessões no frontend e 3 no backend, medindo pela AST só as STRINGS DE DADO. A
nota diz outra coisa, verbatim: "Nunca usar o caractere travessão (em-dash) em
lugar nenhum: Código, Comentários, Templates, Documentação". Sobraram cerca de 90
em comentário e docstring do backend, e o frontend não foi medido desse jeito.

Escada aplicada antes de virar fase: a prova é `grep -rn` e não precisa de
ferramenta nova, porque o alvo é zero em qualquer lugar, e aí não é preciso
distinguir comentário de string. A reescrita em si é a mão, porque trocar
travessão por dois-pontos, vírgula ou parênteses é decisão de pontuação, uma por
uma, e substituição cega deixa frase errada.

**Critério de aceite:** `grep -rn "—" backend/app backend/provas frontend/src`
volta vazio; a suíte inteira de `backend/provas` continua em exit 0; o
`npm run build` do frontend continua compilando; e nenhum arquivo teve mudança
além da pontuação, provado pelo `git diff` lido antes do commit.

## Fase 22: o boot para de escrever 45 erros falsos no log do banco

- **Status:** pending
- **Aberta em:** 2026-09-09, a pedido do usuário, a partir do log de produção que
  ele mesmo trouxe ao conferir o item 19.4.
- **Duração estimada:** 1 sessão curta
- **Notas que regem:** `Padrao_Logging_Estruturado` (log existe para investigar,
  e a nota trata `except` que engole erro como anti-padrão),
  `Escada_Preguica_de_Codigo` (degrau 2 e 5, usar o que já está instalado),
  `TDD_RED_GREEN_REFACTOR`, `Fechar_Tarefa_Rodar_Verifica`, `Sem_Travessao`
- **Dependências:** nenhuma
- **Output esperado:** boot contra banco já migrado não gera linha de erro nenhuma,
  nem no Postgres nem no stdout do app.

O que foi medido, e não suposto: `init_db.py:65` roda as 64 migrações SEMPRE, uma
transação por item, e usa o erro do banco como forma de descobrir que a coluna já
existe (`init_db.py:70-73`). O Postgres registra cada tentativa como `ERROR:
column ... already exists`, e o log de produção nasce com cerca de 45 erros falsos
a cada deploy. Não quebra nada hoje. O preço é que erro de migração de verdade
passa a morar no meio de 45 iguais, e ninguém olha.

O desenho, com a armadilha declarada: **não é trocar por `ADD COLUMN IF NOT
EXISTS`**. As provas locais rodam em SQLite, que não aceita essa forma, e a suíte
inteira quebraria. O caminho que serve aos dois bancos é perguntar antes, com o
`inspect(engine)` do SQLAlchemy, que já está instalado: lê as colunas existentes
de cada tabela uma vez e executa só o que falta.

**Três migrações não são `ADD COLUMN` e precisam de tratamento próprio, senão a
fase promete um zero que não entrega:** `data_prazo_nullable` e
`setor_empresa_nullable` (`ALTER COLUMN ... DROP NOT NULL`) e
`identificadores_maior` (`ALTER COLUMN ... TYPE`). Elas hoje falham com erro de
sintaxe em SQLite a cada rodada de prova, e no Postgres já foram aplicadas. O
inspector também sabe responder por elas: `nullable` e o tipo da coluna vêm no
mesmo `get_columns`. Os índices ficam como estão, porque já usam `IF NOT EXISTS`
e por isso nunca aparecem no log.

**Critério de aceite, verificável por quem não escreveu:**
`python backend/provas/prova_migrate_silencioso.py` sai com código 0, e com código
1 no código de hoje. Ela roda o `migrate()` DUAS vezes contra um SQLite temporário
e captura o stdout: na segunda rodada não sai nenhuma linha com `já existe` nem
com `Erro na coluna`, e na primeira as colunas são criadas de fato. A suíte inteira
de `backend/provas` continua em exit 0. Publicado, com o carimbo de `/api/health`
batendo com o HEAD. E, como o log do banco não sai por curl, uma conferência
visual na aba Logs depois do deploy seguinte: zero `already exists`.

## Fora de escopo (cortado pela escada)

- **Os eventos que faltam na tabela da nota** (`ACESSO_NEGADO_403`,
  `RATE_LIMIT_HIT`, `LOGOUT`, `EXPORT_DADOS`): decisão do usuário em 2026-09-09.
  Volta como fase própria, e o gatilho é o levantamento de quais já existem
  hoje. Fase de campo e fase de evento não se misturam.
- **Dependência nova de correlation-id** (existe pacote pronto): cortada no
  degrau 3 da escada, porque `contextvars` da biblioteca padrão resolve. Volta
  se um dia o app precisar propagar o id para serviço externo.
- **Retenção e envio de log para Loki, Datadog ou similar**: a nota cita, o
  EasyPanel hoje segura o `stdout`. Volta quando alguém precisar consultar log
  de mais de 30 dias atrás.
- **Migrar o `email` que já é gravado no log**: a própria nota registra
  `email_tentado` no exemplo de `LOGIN_FALHA`, então não é violação. Volta se a
  política de PII do escritório mudar.
- **Infra de pytest**: o projeto testa por `provas/prova_*.py` executável.
  Trocar de padrão no meio de uma fase de logging é escopo de outro trabalho.

## Histórico deste plano

- **2026-09-09, manhã:** plano aberto com as fases 18 e 19, aprovado sem ajustes.
- **2026-09-09, noite:** fase 22 acrescentada a pedido do usuário, a partir do
  log de produção que ele trouxe ao conferir o item 19.4. Achado dele, não meu:
  eu tinha olhado o carimbo e os cabeçalhos, e nunca o log do banco.
- **2026-09-09, tarde:** fases 20 e 21 acrescentadas a pedido do usuário, depois
  que a verificação adversarial da Fase 18 achou a resposta 500 saindo sem
  cabeçalho nenhum, e a varredura de travessões achou que a medição de manhã
  cobria só string de dado. Nenhuma fase anterior mudou de escopo.
