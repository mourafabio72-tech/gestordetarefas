# Checklist de aplicação: fases 23 a 25

Decisão de cor e tema: não se aplica. Estas fases não produzem tela.

Item só recebe `[x]` com evidência apontável: arquivo e linha, saída de comando
ou linha de log real. Marcar sem evidência é fraude com o próprio processo.

## Fase 23: autorização e sessão passam a deixar rastro

- [x] **23.1** Escrever `backend/provas/prova_eventos_log.py` ANTES do código,
      e vê-la REPROVAR o código de hoje (exit 1, com a lista dos itens que
      falharam colada no LOG). Cobre os quatro eventos e, obrigatoriamente, os
      dois itens de não-regressão: o corpo da resposta 403 e o corpo do 404
      continuam idênticos aos de hoje.
- [x] **23.2** `ACESSO_NEGADO_403` nas três guardas de `app/auth.py`
      (`require_grupos:63`, `require_perm:82`, `require_flag:94`), cada uma com
      o motivo da recusa como campo extra. Nenhuma rota tocada.
- [x] **23.3** Helper de IDOR em `routes/tarefas.py`: ao não achar dentro do
      escopo, uma consulta pergunta se o id existe fora dele; se existir, emite
      `ACESSO_NEGADO_IDOR` com `recurso` e `recurso_id`, como o exemplo da
      `Padrao_IDOR`. Aplicado nos dois pontos de busca por id único (`:351` e
      `:373`). A resposta ao cliente não muda.
- [x] **23.4** `MUDANCA_ROLE` em `routes/usuarios.py:252-256`, com o papel
      ANTERIOR lido antes da atribuição, e não depois.
- [x] **23.5** Rota `POST /api/auth/logout` que emite `LOGOUT` e devolve 200,
      com docstring dizendo que não invalida token e por quê.
- [x] **23.6** `contexts/AuthContext.jsx:88` chama a rota antes de apagar o
      token, e ignora falha: erro na chamada não pode prender o usuário dentro
      do sistema.
- [x] **23.7** `prova_eventos_log.py` GREEN, exit 0, com uma linha real de cada
      evento colada no LOG.
- [x] **23.8** Suíte inteira de `backend/provas` em exit 0. A assinatura das
      três guardas de autorização foi tocada, e elas regem o app inteiro:
      rodar só a prova nova aqui seria insuficiente.
- [x] **23.9** Provas do frontend em exit 0 e `npm run build` compilando.
- [x] **23.10** `grep -n` de travessão nos arquivos do diff volta vazio, e
      `grep -rn "escada:" backend/` registrado no LOG com o total e o que esta
      fase acrescentou.
- [x] **23.11** Verificação adversarial: 2 a 3 verificadores em paralelo,
      contexto limpo, sem a minha justificativa. Um deles obrigatoriamente
      funcional, atacando o IDOR com carga concorrente e conferindo que o
      404 de id inexistente não emite evento.

## Fase 24: registro crítico para de mentir, e o export deixa rastro

- [x] **24.1** Escrever `backend/provas/prova_registro_critico.py` ANTES do
      código, e vê-la REPROVAR o código de hoje (exit 1, lista colada no LOG).
- [x] **24.2** Conserto dos dois eventos trocados: `routes/tarefas.py:804`
      passa a emitir `CRIACAO_REGISTRO_CRITICO` e `routes/obrigacoes.py:63`
      passa a emitir `EXCLUSAO_REGISTRO_CRITICO`. Provado contra
      `git show HEAD` que a prova reprovava o nome antigo.
- [x] **24.3** `DOCUMENTO_EXCLUIDO` (`routes/tarefas.py:433`) vira
      `EXCLUSAO_REGISTRO_CRITICO` com `tabela="tarefa_anexo"`. O nome antigo
      vira campo, não some.
- [x] **24.4** Criação e exclusão em `routes/usuarios.py` (`:180` e `:284`),
      com `tabela` e o id do alvo.
- [x] **24.5** Criação e exclusão em `routes/empresas.py` (`:265` e `:332`).
- [x] **24.6** Criação e exclusão em `routes/obrigacoes.py` (`:270`, `:316` e
      `:342`).
- [x] **24.7** Edição das mesmas quatro tabelas: `PUT` de usuários (`:216`),
      empresas (`:295`) e obrigações (`:285`), como
      `EDICAO_REGISTRO_CRITICO`.
- [x] **24.8** Lote emite UMA linha com a contagem, e não uma por registro:
      `POST /importar` de usuários e de empresas, e `POST /excluir-lote` de
      obrigações.
- [x] **24.9** `EXPORT_DADOS` em `routes/obrigacoes.py:157`, com a contagem de
      linhas exportadas.
- [x] **24.10** `prova_registro_critico.py` GREEN, exit 0, com uma linha real
      de cada evento novo colada no LOG.
- [x] **24.11** Nenhum campo da lista proibida da nota (senha, token, CPF,
      cartão, header bruto) aparece em nenhuma linha nova. Item da prova, e não
      leitura de olho.
- [x] **24.12** Suíte inteira de `backend/provas` em exit 0.
- [x] **24.13** `grep -n` de travessão nos arquivos do diff volta vazio, e o
      inventário de `escada:` registrado no LOG.
- [x] **24.14** Verificação adversarial: 2 a 3 verificadores em paralelo. Um
      deles obrigatoriamente de conformidade, confrontando cada evento novo
      contra a tabela da `Padrao_Logging_Estruturado` linha a linha.

## Fase 25: entrega, prova no ar e matriz fechada

- [x] **25.1** `Dockerfile` do backend conferido ANTES do push: `COPY . .`, para
      os arquivos de prova novos entrarem na imagem.
- [x] **25.2** Commit e push, com `git ls-remote` confirmando o ref no
      servidor, e o webhook publicando sozinho.
- [x] **25.3** Carimbo de `/api/health` batendo com o HEAD, comparado nas duas
      pontas: antes do deploy e depois.
- [x] **25.4** `curl` na rota de logout: sem token devolve 401, com token
      devolve 200.
- [ ] **25.5** CONFERENCIA_VISUAL, e é do usuário: fazer logout no app e achar
      a linha `LOGOUT` na aba Logs do serviço `backend`, com o `user_id` dele e
      o `request_id` que o `X-Request-ID` devolveu ao navegador.
- [ ] **25.6** `CONFORMIDADE_VAULT.md` sem nenhuma linha pendente das fases 23
      a 25 (`grep -c '| pendente |'` devolve 0).
