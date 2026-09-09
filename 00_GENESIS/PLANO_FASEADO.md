# Plano faseado: campos obrigatórios no logger central

modo=<a definir na primeira execução>
plano aprovado em 2026-09-09, sem ajustes

As fases 1 a 17 estão fechadas e arquivadas nos dois checkpoints desta pasta.
A numeração continua de lá.

## Fase 0: aprovação deste plano

- **Status:** pending
- **Critério de aceite:** o usuário aprova, e a aprovação fica registrada no LOG.

## Fase 18: os cinco campos entram sozinhos no `log_event`

- **Status:** pending
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
