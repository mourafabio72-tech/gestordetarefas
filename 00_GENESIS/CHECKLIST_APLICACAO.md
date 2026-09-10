# Checklist de aplicação: fases 18 e 19

Decisões que valem para as duas fases, tiradas do brainstorming de 2026-09-09:

```
Campos automáticos: request_id, path, method, user_id, ip (os cinco, não só os três do achado)
Nome do campo de usuário: user_id (como a nota; usuario_id sai de circulação)
Eventos que faltam na tabela da nota: FORA desta fase, viram fase própria
X-Request-ID na resposta: SIM, ampliação declarada
Formato de teste: backend/provas/prova_logging.py, executável por python. Sem pytest.
```

Regra deste arquivo: só marcar `[x]` com evidência apontável, que é arquivo e
linha, ou saída de comando colada no LOG. Marcar sem evidência é fraudar o
próprio processo.

## Fase 18: os cinco campos entram sozinhos

- [x] **18.1 (RED, vem antes do código)** `backend/provas/prova_logging.py` criada e
      FALHANDO com o código de hoje. Ela captura o `stdout` do `log_event` e
      confere a linha JSON.
      Itens obrigatórios: (a) linha emitida dentro de request tem os 8 campos da
      nota; (b) dois requests têm `request_id` diferente; (c) duas linhas do
      MESMO request têm o mesmo `request_id`; (d) `log_event` fora de request
      não levanta exceção e traz os cinco como `null`; (e) chamador que passa o
      campo a mão continua vencendo o default; (f) nenhuma chave da lista
      proibida aparece.
      PROVA: `python backend/provas/prova_logging.py` sai com código 1 hoje
      (TDD_RED_GREEN_REFACTOR: "escreve-se o teste ANTES do codigo")

- [x] **18.2** Contexto de request em `backend/app/seguranca.py`: três
      `contextvars` (`_request_id`, `_rota`, `_usuario`) e uma função que abre o
      contexto. `request_id` gerado com `uuid.uuid4().hex[:16]`, exatamente o
      que a nota usa.
      PROIBIDO: passar `request` como parâmetro para os 14 chamadores do
      `log_event`; instalar biblioteca de correlation-id
      PROVA: `grep -n "contextvars" backend/app/seguranca.py` acha o import, e
      `git diff --stat` não mostra os 14 arquivos de rota
      (Padrao_Logging_Estruturado, Escada_Preguica_de_Codigo degrau 3)

- [x] **18.3** Middleware em `backend/app/main.py` que abre o contexto por
      request, ao lado do `_headers_de_seguranca` que já existe. O IP sai de
      `ip_do_cliente(request)`, que já trata `X-Forwarded-For` atrás do proxy.
      PROIBIDO: escrever extração de IP nova
      PROVA: `grep -n "ip_do_cliente" backend/app/main.py backend/app/seguranca.py`
      mostra reuso, e não função nova
      (Escada_Preguica_de_Codigo degrau 2, "Ja existe no codebase?")

- [x] **18.4** `log_event` preenche por `setdefault` os cinco campos:
      `user_id`, `ip`, `request_id`, `path`, `method`. Ordem da linha JSON
      seguindo a tabela da nota.
      PROIBIDO: sobrescrever campo que o chamador passou; `except Exception: pass`
      em volta da leitura do contexto (anti-padrão nomeado na Família 6)
      PROVA: item (e) da `prova_logging.py`, e
      `grep -n "except Exception:" backend/app/seguranca.py` sem `pass` na
      linha seguinte
      (Padrao_Logging_Estruturado, tabela "Campos obrigatórios em todo log")

- [x] **18.5** `user_id` gravado no contexto quando a autenticação resolve o
      usuário (`get_current_user` e o que dela deriva), e os três chamadores que
      hoje passam `usuario_id=` migram para não duplicar campo.
      PROIBIDO: `usuario_id` sobrando em linha de log depois desta fase
      PROVA: item 17 da `prova_logging.py`, que le o codigo por AST. O grep
      desta linha, que era a prova original, e cego a chamada quebrada em duas
      linhas, e por isso deixou passar `tarefas.py:433`
      (decisão do usuário em 2026-09-09: a vault vence o código legado)

- [x] **18.6** `X-Request-ID` na resposta, no mesmo middleware.
      PROVA: item da prova que confere o cabeçalho na resposta, e valor igual ao
      `request_id` da linha de log daquele request
      (ampliação declarada, não vem da nota)

- [x] **18.7 (GREEN)** `python backend/provas/prova_logging.py` sai com código 0,
      com a saída colada no LOG.

- [x] **18.8 (regressão)** As provas que tocam autenticação continuam verdes:
      `prova_sso_f3.py` e `prova_seguranca_f7.py`, saída colada no LOG.
      (Fechar_Tarefa_Rodar_Verifica: "'Pronto' nao e uma palavra que se diz sozinho")

- [x] **18.9** Sem travessão no que foi escrito: `grep -rn "—"` nos arquivos do
      diff volta vazio.
      (Sem_Travessao, "qualquer arquivo")

- [x] **18.10** Inventário de simplificações: `grep -rn "escada:" backend/` com o
      número anotado no LOG, e o gatilho de upgrade de cada marcador novo.

## Fase 19: entrega e prova no ar

- [x] **19.1** Commit e push. O auto-deploy publica sozinho, e o webhook deste
      repositório já está provado desde 2026-09-01.

- [x] **19.2** Carimbo de produção bate com o HEAD:
      `curl -s https://gestordetarefas.zoaria.com.br/api/health` traz o `build`
      do commit desta fase. Comparar com
      `git log -1 --date=format:'%Y%m%d-%H%M'` antes de acusar qualquer coisa.

- [x] **19.3** `X-Request-ID` provado no ar:
      `curl -sI https://gestordetarefas.zoaria.com.br/api/health | grep -i x-request-id`
      duas vezes, com valores diferentes.

- [ ] **19.4** Linha de log real conferida na aba Logs do EasyPanel, com os oito
      campos. CONFERENCIA_VISUAL, porque o log de produção não sai por curl.

- [x] **19.5** `CONFORMIDADE_VAULT.md` sem linha pendente das fases 18 e 19.

## Fase 20: a resposta de erro para de sair pelada

Decisões desta fase, tiradas do achado do verificador funcional de 2026-09-09:

```
Onde o id viaja:        request.state, e nao a contextvar, porque o handler roda em contexto ancestral
Corpo do erro:          generico, sem traceback, sem nome de excecao, sem caminho de arquivo
Cabecalhos:             reusa aplicar_headers, nao escreve lista nova
Traceback no servidor:  tem de CONTINUAR saindo no stdout. Se sumir, a fase muda de desenho
Formato de teste:       backend/provas/prova_erro_500.py, executavel por python. Sem pytest
```

- [x] **20.1 (RED, vem antes do código)** `backend/provas/prova_erro_500.py` criada
      e FALHANDO com o código de hoje. Usa `TestClient(app, raise_server_exceptions=False)`,
      porque o padrão re-levanta a exceção no teste em vez de devolver a resposta.
      Itens obrigatórios: (a) status 500; (b) `X-Request-ID` presente na resposta de
      erro; (c) esse valor é igual ao `request_id` da linha de log daquele request;
      (d) os cabeçalhos de segurança da nota vêm na resposta de erro; (e) o corpo
      não contém traceback, nome da exceção, caminho de arquivo nem SQL; (f) a linha
      `ERRO_NAO_TRATADO` sai com os oito campos.
      PROVA: `python backend/provas/prova_erro_500.py` sai com código 1 hoje
      (TDD_RED_GREEN_REFACTOR)

- [x] **20.2** `abrir_contexto` grava o id também em `request.state.request_id`,
      sem parar de gravar na contextvar.
      PROIBIDO: trocar a contextvar pelo `state`; o `log_event` continua lendo do
      contexto, senão volta a depender de quem chama
      PROVA: `grep -n "state" backend/app/seguranca.py`, e a `prova_logging.py`
      continua em 17 verdes

- [x] **20.3** `@app.exception_handler(Exception)` em `main.py`, que emite
      `ERRO_NAO_TRATADO` em nível ERROR e devolve JSON genérico com 500.
      PROIBIDO: devolver `str(exc)` ao cliente (Revisao_Vulnerabilidades item 9,
      e a Família 6: "o cliente recebe pouca informação, o log do servidor recebe
      muita"); `except Exception: pass`
      PROVA: itens (a), (e) e (f) da prova

- [x] **20.4** Os cabeçalhos de segurança na resposta de erro saem do
      `aplicar_headers` que já existe.
      PROIBIDO: escrever lista de cabeçalhos nova
      PROVA: `grep -n "aplicar_headers" backend/app/main.py` mostra reuso, e o
      item (d) da prova
      (Escada_Preguica_de_Codigo degrau 2)

- [x] **20.5** O traceback CONTINUA saindo no stdout do servidor depois do
      handler entrar. Se não continuar, parar e mudar o desenho.
      PROVA: item da prova que captura o stderr/stdout do servidor durante a
      exceção e acha a palavra `Traceback`

- [x] **20.6 (GREEN)** `python backend/provas/prova_erro_500.py` sai com código 0,
      saída colada no LOG.

- [x] **20.7 (regressão)** As 26 provas de `backend/provas/` continuam em exit 0,
      com a `prova_logging.py` e a `prova_seguranca_f7.py` citadas por nome no LOG.

- [x] **20.8** Sem travessão nos arquivos do diff, e inventário
      `grep -rn "escada:" backend/` anotado no LOG.

- [x] **20.9** Publicado: commit, push, e o carimbo de
      `curl -s https://gestordetarefas.zoaria.com.br/api/health` batendo com
      `git log -1 --date=format:'%Y%m%d-%H%M'`.

- [x] **20.10** Matriz `CONFORMIDADE_VAULT.md` com as linhas desta fase
      preenchidas e sem pendência.

## Fase 21: travessão fora de comentário e docstring

- [x] **21.1** Inventário antes de tocar em nada: contagem por arquivo em
      `backend/app`, `backend/provas` e `frontend/src`, colada no LOG.
      PROVA: `grep -rc "—" <caminhos> | grep -v ":0"`

- [x] **21.2** Reescrita do backend, arquivo por arquivo, trocando travessão por
      dois-pontos, vírgula, parênteses ou hífen conforme a frase pede.
      PROIBIDO: substituição cega por um único caractere; tocar em `venv/`,
      `node_modules/`, `00_GENESIS/` ou histórico
      PROVA: `grep -rn "—" backend/app backend/provas` volta vazio

- [x] **21.3** Reescrita do frontend, mesma regra.
      PROVA: `grep -rn "—" frontend/src` volta vazio

- [x] **21.4** `git diff` lido inteiro antes do commit: nenhuma mudança além de
      pontuação. Qualquer linha que mude sentido volta atrás.
      (Escada_Preguica_de_Codigo: mudanças cirúrgicas)

- [x] **21.5 (regressão)** As 26 provas do backend e as 18 do frontend em exit 0,
      e `npm run build` compilando, saída colada no LOG.

- [x] **21.6** Publicado e conferido: carimbo do `/api/health` batendo com o HEAD.
      CRITÉRIO CORRIGIDO EM 2026-09-09, depois de medido: este item pedia também
      "o hash do bundle do Vite mudando, que é o que prova frontend novo no ar",
      e isso está ERRADO para esta fase. As ocorrências do frontend estavam todas
      em comentário, que o minificador remove, então o bundle é o mesmo e tem de
      ser: `npm run build` depois da mudança gera o mesmo `index-DwKXh0Cp.js`, e
      o md5 do arquivo local bate com o do arquivo baixado de produção
      (`85c80e27b50cc269e4a87fa7689127e3` nos dois). Aqui, hash igual é a prova
      de que não havia frontend novo a subir. A correção estava só no LOG, e o
      verificador cobrou que ela entrasse também aqui, no item marcado.

- [x] **21.7** Matriz com a linha da `Sem_Travessao` desta fase preenchida.

## Fase 22: o boot para de escrever 45 erros falsos no log do banco

Decisões desta fase, tiradas do log de produção de 2026-09-09:

```
NAO usar ADD COLUMN IF NOT EXISTS: SQLite das provas nao aceita, quebraria a suite
Perguntar antes:                   inspect(engine).get_columns(), que ja esta instalado
As tres ALTER COLUMN:              tratadas pelo mesmo inspector (nullable e tipo)
Os indices:                        ficam como estao, ja usam IF NOT EXISTS
Formato de teste:                  backend/provas/prova_migrate_silencioso.py
```

- [ ] **22.1 (RED, vem antes do código)** `backend/provas/prova_migrate_silencioso.py`
      criada e FALHANDO com o código de hoje. Roda `migrate()` duas vezes contra um
      SQLite temporário, capturando o stdout.
      Itens obrigatórios: (a) na 1a rodada as colunas nascem; (b) na 2a rodada o
      stdout não tem `já existe`; (c) em rodada nenhuma o stdout tem
      `Erro na coluna`, o que hoje falha por causa das três `ALTER COLUMN`;
      (d) o schema final tem as mesmas colunas que o código de hoje produz, que é
      a prova de que a fase não perdeu migração pelo caminho.
      PROVA: `python backend/provas/prova_migrate_silencioso.py` sai com código 1 hoje

- [ ] **22.2** `migrate()` lê as colunas existentes com `inspect(engine)` e executa
      só o que falta.
      PROIBIDO: `ADD COLUMN IF NOT EXISTS`; SQL de `information_schema` escrito a
      mão; uma consulta por migração quando uma por tabela resolve
      PROVA: `grep -n "inspect" backend/app/init_db.py`, e o item (b)
      (Escada_Preguica_de_Codigo degrau 5, dependência já instalada)

- [ ] **22.3** As três `ALTER COLUMN` (`data_prazo_nullable`,
      `setor_empresa_nullable`, `identificadores_maior`) só rodam quando o
      inspector disser que ainda são necessárias.
      PROVA: item (c), e o stdout limpo nas duas rodadas em SQLite

- [ ] **22.4** O `except` que sobrar continua REPORTANDO erro de verdade, e não
      vira silêncio.
      PROIBIDO: `except Exception: pass` (anti-padrão nomeado na nota de logging)
      PROVA: uma migração propositalmente inválida, dentro da prova, ainda imprime
      a linha de erro

- [ ] **22.5 (GREEN)** `python backend/provas/prova_migrate_silencioso.py` sai com
      código 0, saída colada no LOG.

- [ ] **22.6 (regressão)** As provas de `backend/provas/` continuam em exit 0. Vale
      olhar o cabeçalho da saída: hoje toda prova começa cuspindo 45 linhas de
      `Coluna ... já existe`, e depois desta fase não deve mais.

- [ ] **22.7** Sem travessão nos arquivos do diff, e `grep -rn "escada:" backend/`
      anotado no LOG.

- [ ] **22.8** Publicado: carimbo de `/api/health` batendo com o HEAD.

- [ ] **22.9** CONFERENCIA_VISUAL, porque log de banco não sai por curl: na aba
      Logs do EasyPanel, depois do deploy, o serviço `db` não mostra nenhum
      `already exists`. Registrar `conferido em <data>`.

- [ ] **22.10** Matriz `CONFORMIDADE_VAULT.md` com as linhas desta fase preenchidas.
