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

- [ ] **18.1 (RED, vem antes do código)** `backend/provas/prova_logging.py` criada e
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

- [ ] **18.2** Contexto de request em `backend/app/seguranca.py`: três
      `contextvars` (`_request_id`, `_rota`, `_usuario`) e uma função que abre o
      contexto. `request_id` gerado com `uuid.uuid4().hex[:16]`, exatamente o
      que a nota usa.
      PROIBIDO: passar `request` como parâmetro para os 14 chamadores do
      `log_event`; instalar biblioteca de correlation-id
      PROVA: `grep -n "contextvars" backend/app/seguranca.py` acha o import, e
      `git diff --stat` não mostra os 14 arquivos de rota
      (Padrao_Logging_Estruturado, Escada_Preguica_de_Codigo degrau 3)

- [ ] **18.3** Middleware em `backend/app/main.py` que abre o contexto por
      request, ao lado do `_headers_de_seguranca` que já existe. O IP sai de
      `ip_do_cliente(request)`, que já trata `X-Forwarded-For` atrás do proxy.
      PROIBIDO: escrever extração de IP nova
      PROVA: `grep -n "ip_do_cliente" backend/app/main.py backend/app/seguranca.py`
      mostra reuso, e não função nova
      (Escada_Preguica_de_Codigo degrau 2, "Ja existe no codebase?")

- [ ] **18.4** `log_event` preenche por `setdefault` os cinco campos:
      `user_id`, `ip`, `request_id`, `path`, `method`. Ordem da linha JSON
      seguindo a tabela da nota.
      PROIBIDO: sobrescrever campo que o chamador passou; `except Exception: pass`
      em volta da leitura do contexto (anti-padrão nomeado na Família 6)
      PROVA: item (e) da `prova_logging.py`, e
      `grep -n "except Exception:" backend/app/seguranca.py` sem `pass` na
      linha seguinte
      (Padrao_Logging_Estruturado, tabela "Campos obrigatórios em todo log")

- [ ] **18.5** `user_id` gravado no contexto quando a autenticação resolve o
      usuário (`get_current_user` e o que dela deriva), e os três chamadores que
      hoje passam `usuario_id=` migram para não duplicar campo.
      PROIBIDO: `usuario_id` sobrando em linha de log depois desta fase
      PROVA: `grep -rn "usuario_id=" backend/app/routes/ | grep log_event` volta
      vazio
      (decisão do usuário em 2026-09-09: a vault vence o código legado)

- [ ] **18.6** `X-Request-ID` na resposta, no mesmo middleware.
      PROVA: item da prova que confere o cabeçalho na resposta, e valor igual ao
      `request_id` da linha de log daquele request
      (ampliação declarada, não vem da nota)

- [ ] **18.7 (GREEN)** `python backend/provas/prova_logging.py` sai com código 0,
      com a saída colada no LOG.

- [ ] **18.8 (regressão)** As provas que tocam autenticação continuam verdes:
      `prova_sso_f3.py` e `prova_seguranca_f7.py`, saída colada no LOG.
      (Fechar_Tarefa_Rodar_Verifica: "'Pronto' nao e uma palavra que se diz sozinho")

- [ ] **18.9** Sem travessão no que foi escrito: `grep -rn "—"` nos arquivos do
      diff volta vazio.
      (Sem_Travessao, "qualquer arquivo")

- [ ] **18.10** Inventário de simplificações: `grep -rn "escada:" backend/` com o
      número anotado no LOG, e o gatilho de upgrade de cada marcador novo.

## Fase 19: entrega e prova no ar

- [ ] **19.1** Commit e push. O auto-deploy publica sozinho, e o webhook deste
      repositório já está provado desde 2026-09-01.

- [ ] **19.2** Carimbo de produção bate com o HEAD:
      `curl -s https://gestordetarefas.zoaria.com.br/api/health` traz o `build`
      do commit desta fase. Comparar com
      `git log -1 --date=format:'%Y%m%d-%H%M'` antes de acusar qualquer coisa.

- [ ] **19.3** `X-Request-ID` provado no ar:
      `curl -sI https://gestordetarefas.zoaria.com.br/api/health | grep -i x-request-id`
      duas vezes, com valores diferentes.

- [ ] **19.4** Linha de log real conferida na aba Logs do EasyPanel, com os oito
      campos. CONFERENCIA_VISUAL, porque o log de produção não sai por curl.

- [ ] **19.5** `CONFORMIDADE_VAULT.md` sem linha pendente das fases 18 e 19.
