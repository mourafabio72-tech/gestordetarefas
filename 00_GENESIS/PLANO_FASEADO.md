# PLANO FASEADO: obrigação acessória transmitida ao órgão (fases 27 a 31) e recorte por regime na geração (fases 32 a 34)

> **Ordem de execução, decidida pelo usuário em 2026-09-18 (resposta 4a):**
> 32, 33, 34, e só depois 29, 30, 31. As fases 27 e 28 foram commitadas
> localmente antes (`45ac41a`), sem push.

> **modo=autonomo** (escolhido em 2026-09-15)

> **Fases 35 a 37 (2026-09-18, a pedido do usuário):** executar antes das 29, 30 e 31.

> Fases 1 a 26 fechadas, planos nos checkpoints. Aberto em 2026-09-15.
> Fase 0 deste trabalho: aprovação do usuário. Fase 1 (CLAUDE.md do projeto)
> já existe desde 16/08 e não se refaz.

## Fase 0: aprovação

- **Status:** done (aprovado sem ajustes em 2026-09-15; fases 32 a 34 aprovadas em 2026-09-18, estilo tipo 1; fases 35 a 37 aprovadas em 2026-09-18)
- **Critério de aceite:** o usuário aprova este plano por escrito no chat.

---

## Fase 27: backend, a regra do documento e o sentido que grava

- **Status:** done (2026-09-15; prova com 22 itens, dois achados de verificador corrigidos)
- **Duração estimada:** 40 min
- **Notas:** Padrao_Validacao_de_Input, Padrao_Mass_Assignment, Escada_Preguica_de_Codigo, TDD_RED_GREEN_REFACTOR, Sem_Travessao
- **Dependências:** fase 0
- **Output esperado:** `backend/provas/prova_transmitir_orgao.py`; `models.py`, `schemas.py`, `routes/painel.py` alterados.

Itens:

1. **27.1 RED.** Prova escrita antes, com exit 1 no código de hoje:
   (a) PUT trocando `sentido` grava e o GET devolve o valor novo;
   (b) `sentido` fora de `receber|entregar|interna|transmitir` recebe 422 no POST e no PUT, e o banco não muda;
   (c) matriz das 24 combinações (4 sentidos x `exige_documento` None/True/False x identificadores vazio/cheio): `Tarefa.exige_documento` e o perfil do painel dão a MESMA resposta;
   (d) `transmitir` com identificadores e flag nula exige documento;
   (e) `identificar_obrigacao` acha obrigação `transmitir`;
   (f) não-regressão medida antes: `receber`, `entregar` e `interna` sem flag seguem como hoje.
   Verifica: `python provas/prova_transmitir_orgao.py` sai 1, saída colada no LOG.
2. **27.2** Função pura `perfil_documento(sentido, exige_documento, identificadores)` em `models.py`, chamada por `Tarefa.exige_documento` e por `_perfil_obrigacao` do `painel.py`. Verifica: `grep -n "perfil_documento" backend/app/models.py backend/app/routes/painel.py` acha a definição e as duas chamadas.
3. **27.3** `Sentido = Literal["receber", "entregar", "interna", "transmitir"]` em `schemas.py`, usado em `ObrigacaoBase` e acrescentado a `ObrigacaoUpdate` como opcional. Verifica: item (a) e (b) da prova.
4. **27.4** Comentários de sentido atualizados (`models.py:437-443`, `schemas.py:211` e `:227`, docstring de `identificar_obrigacao`). Verifica: `grep -n "transmitir" backend/app/models.py backend/app/schemas.py`.
5. **27.5 GREEN e regressão.** Verifica: a prova nova em exit 0 e as 30 provas de `backend/provas/` em exit 0, com destaque para `prova_sentido_obrigacao.py`, `prova_evalidador_interna.py` e `prova_painel.py`.

**Critério de aceite:** a prova sai 1 antes e 0 depois, com as duas saídas no LOG; as 31 provas do backend em exit 0; `grep -rn "—" ` nos arquivos tocados volta vazio.

---

## Fase 28: link de envio de comprovante só para "receber"

- **Status:** done (2026-09-15; prova com 17 itens, um achado de evidência e uma lacuna de prova corrigidos)
- **Duração estimada:** 30 min
- **Notas:** Escada_Preguica_de_Codigo (padrão irmão), Padrao_Validacao_de_Input, TDD_RED_GREEN_REFACTOR, Sem_Popup_Nativo
- **Dependências:** fase 27 (usa `transmitir` válido)
- **Output esperado:** `backend/provas/prova_link_so_receber.py`; `services/whatsapp.py`, `routes/tarefas.py`, `routes/upload_publico.py`, `frontend/src/pages/Tarefas.jsx` alterados.

Itens:

1. **28.1 RED.** Prova com exit 1 hoje:
   (a) a régua de alerta, em modo `ensaio=True`, monta item COM link só para tarefa `receber`, e SEM link para `entregar`, `interna` e `transmitir`;
   (b) `GET /api/tarefas/{id}/link-envio` devolve 404 para tarefa que não é `receber`, e NÃO cria `upload_token`;
   (c) `GET` e `POST /api/publico/tarefa/{token}` com token de tarefa fora de `receber` devolvem o MESMO 404 e o mesmo corpo de token inexistente;
   (d) não-regressão medida antes: `receber` continua recebendo link, contexto e upload; e `/api/publico/baixar/{token}` de tarefa `entregar` continua 200.
2. **28.2** Uma checagem só, `tarefa.sentido == "receber"`, nos três pontos do servidor: item da régua (`whatsapp.py:740`), rota `link-envio` (`tarefas.py:208`) e `_tarefa_por_token` (`upload_publico.py:16`), depois de conferir com grep que `baixar_documento` NÃO passa por esse helper. Verifica: item (d) da prova.
3. **28.3** Menu "Copiar link de envio" (`Tarefas.jsx:708`) só aparece quando `tarefa.sentido === 'receber'`. Verifica: `grep -n "Copiar link de envio" -B2 frontend/src/pages/Tarefas.jsx` mostra a condição.
4. **28.4 GREEN e regressão.** Prova nova em exit 0, `prova_escopo_link.py` e `prova_entrega_cliente.py` em exit 0, suíte inteira em exit 0.

**Critério de aceite:** RED e GREEN no LOG; suíte do backend em exit 0; o download de guia do "entregar" provado vivo pelo item (d).

---

## Fase 29: a tela

- **Status:** pending
- **Duração estimada:** 50 min
- **Notas:** Padrao_Toggle_Tipos, Tela_Nao_Tem_Manual, Sistema_de_Estilos, Verificacoes_Mecanicas_de_Tela, Protocolo_Revisao_de_Tela, Portugues_BR_Acentuacao, Sem_Travessao, Sem_Popup_Nativo
- **Dependências:** fase 27
- **Output esperado:** `frontend/src/pages/sentidoObrigacao.js` e `frontend/provas/prova_sentido_obrigacao.js` novos; `Obrigacoes.jsx` e `Documentos.jsx` alterados.

Itens:

1. **29.1 RED.** Prova Node de um módulo sem JSX, no molde de `payloadObrigacao.js`:
   (a) `SENTIDOS` tem as 4 opções, na ordem Receber, Entregar, Transmitir, Nenhum, cada uma com `valor`, `rotulo` e `dica`;
   (b) `mostraIdentificadores(form)` é verdadeiro para `receber`, `transmitir` e `interna` com `exige_documento === true`, e falso para `entregar` e para `interna` sem a flag;
   (c) `exigeDocumentoMarcado(form)` reproduz a regra do servidor (flag explícita vence; nula deriva dos identificadores; interna nula é falso).
   Verifica: `node provas/prova_sentido_obrigacao.js` sai com erro antes de o módulo existir.
2. **29.2** Seletor tipo 1 no lugar dos 3 radios (`Obrigacoes.jsx:925-966`): wrapper `role="radiogroup"` com `aria-label="O documento vai para que lado?"`, quatro `<button type="button">` com `aria-checked`, `title` com a dica, escolhido em `border-primary-600 bg-primary-50 text-primary-800`. O fundo `bg-[#faf7f0]` do bloco sai.
3. **29.3** Bloco de identificadores (`Obrigacoes.jsx:497`) passa a obedecer `mostraIdentificadores(form)`, e o "Exige documento" (`:974-981`) a `exigeDocumentoMarcado(form)`.
4. **29.4** Os quatro checkboxes crus do mesmo bloco (Passível de multa, Exige robô, Alerta guia não-lida, Ativa, `:919`, `:969`, `:984`, `:987`) trocam `h-4 w-4` por `check-app`, a classe que já existe em `index.css:36`.
5. **29.5** Documentos: aba `Recebidos do cliente` vira `Comprovantes e recibos`, e o subtítulo da aba (`Documentos.jsx:161`) passa a falar de comprovantes e recibos.
6. **29.6 GREEN, build e gate de língua.** Prova Node em exit 0, as 19 provas do frontend em exit 0, `npm run build` compilando, `grep -rn "—\|–"` e `grep -nE "#[0-9a-fA-F]{6}"` vazios nos arquivos tocados.
7. **29.7 Conferência visual local**, modal de Obrigação: as 4 opções lado a lado, a escolhida na cor da marca, dica ao passar o mouse, identificadores aparecendo ao escolher Transmitir.

**Critério de aceite:** provas e build verdes; greps vazios; conferência visual registrada no LOG com data e tela.

---

## Fase 30: publicar e provar em produção

- **Status:** pending
- **Duração estimada:** 20 min
- **Notas:** Fechar_Tarefa_Rodar_Verifica
- **Dependências:** fases 27, 28 e 29
- **Output esperado:** commit publicado e conferido.

Itens:

1. **30.1** Suíte inteira do backend e do frontend em exit 0, e `npm run build`.
2. **30.2** Arquivo novo entra na imagem: os dois `Dockerfile` usam `COPY . .` (conferido em 2026-09-15), e isso se reconfirma no diff antes do push.
3. **30.3** Push, `git ls-remote` confirmando o ref, carimbo de `/api/health` antes e depois, igual ao HEAD.
4. **30.4** Prova de fora, sem login: `POST /api/publico/tarefa/<token inventado>` devolve 404 como antes; e o bundle servido contém `Transmitir ao órgão` (`curl` do `/assets/index-*.js` com `grep -c`).
5. **30.5 Conferência visual do usuário** em produção: editar uma obrigação, trocar para "Transmitir ao órgão", salvar, reabrir, e a escolha continua lá. É a prova do defeito 1, que curl não alcança.

**Critério de aceite:** carimbo igual ao HEAD; os dois curls; a conferência do item 30.5 relatada pelo usuário e colada no LOG; CONFORMIDADE sem linha pendente das fases 27 a 30.

---

## Fase 31: reclassificar as obrigações acessórias já cadastradas

- **Status:** pending
- **Duração estimada:** 20 min, e depende do tamanho da lista
- **Notas:** Padrao_Logging_Estruturado, decisão 3 do usuário
- **Dependências:** fase 30 (sem ela, trocar pela tela não grava)
- **Output esperado:** lista aprovada, aplicada e conferida.

Itens:

1. **31.1** Entrego um `SELECT` só de leitura para o console do Postgres no EasyPanel, com `id`, `nome`, `mininome`, `sentido`, `exige_documento` e `identificadores` das obrigações ativas.
2. **31.2** Com a saída colada, marco as candidatas a `transmitir` e o motivo de cada uma. O usuário aprova, corta ou acrescenta.
3. **31.3** A troca acontece pela tela de Obrigação, e não por UPDATE no console: a rota de edição registra `EDICAO_REGISTRO_CRITICO` com os campos alterados, e o console não registra nada. Se a lista passar de 15, a decisão volta ao usuário antes de começar.
4. **31.4** O mesmo `SELECT` rodado de novo mostra as aprovadas em `transmitir`, e as outras intactas.

**Critério de aceite:** a contagem de `transmitir` do segundo `SELECT` bate com a lista aprovada, e nenhuma obrigação fora dela mudou.

---

## Fase 32: a geração em lote passa a deixar rastro

- **Status:** done (2026-09-18; prova com 16 itens, o irmão `create_empresa` entrou pelo verificador)
- **Duração estimada:** 25 min
- **Notas:** Padrao_Logging_Estruturado, TDD_RED_GREEN_REFACTOR
- **Dependências:** nenhuma
- **Output esperado:** `backend/provas/prova_gerar_log.py` novo; `routes/obrigacoes.py` alterado.

Achado da descoberta de 2026-09-18: `POST /obrigacoes/gerar` (`routes/obrigacoes.py:221-230`)
cria tarefas em lote e não chama `log_event`. As rotas vizinhas do mesmo arquivo chamam
(`:257`, `:290`, `:308`). Não é defeito introduzido agora, mas o recorte por regime mexe
exatamente nessa ação, e ela fica sem autor registrado.

Itens:

1. **32.1 RED.** `prova_gerar_log.py`, no molde da `capturar()` de `prova_registro_critico.py:102`:
   (a) uma chamada a `/obrigacoes/gerar` emite UMA linha `CRIACAO_REGISTRO_CRITICO`, com `tabela="tarefa"` e `lote=True`;
   (b) a linha leva o usuário, `mes_entrega`, `criadas`, `puladas`, a quantidade de obrigações e a quantidade de empresas do recorte (`None` quando não houver recorte);
   (c) a linha não leva razão social nem CNPJ, só contagem;
   (d) geração que cria zero tarefas também registra, porque a tentativa é o que se audita;
   (e) não-regressão: a resposta da rota continua igual, campo por campo.
   Verifica: exit 1 antes do código, saída colada no LOG.
2. **32.2 GREEN.** Uma chamada a `log_event` em `gerar_competencia`, depois de `gerar_tarefas` e com os números da resposta dele. O serviço `gerador.py` não muda.
3. **32.3** Suíte do backend em exit 0.

**Critério de aceite:** prova em exit 1 no RED e 0 no GREEN, as duas saídas no LOG; suíte verde.

---

## Fase 33: recorte por regime tributário no modal "Gerar tarefas do mês"

- **Status:** done (2026-09-18; prova com 17 itens, conferência visual do usuário, modal em `max-w-xl` e ressalva em verde a pedido dele)
- **Duração estimada:** 50 min
- **Notas:** Padrao_Toggle_Tipos, Padrao_Selecao_em_Lote (precedente `check-app`), Tela_Nao_Tem_Manual, Sistema_de_Estilos, Verificacoes_Mecanicas_de_Tela, Protocolo_Revisao_de_Tela, Padrao_IDOR, Padrao_Mass_Assignment, Portugues_BR_Acentuacao, Sem_Travessao, Sem_Popup_Nativo
- **Dependências:** nenhuma (a 32 é independente)
- **Output esperado:** `frontend/src/pages/recorteGeracao.js` e `frontend/provas/prova_recorte_regime.js` novos; `Obrigacoes.jsx` alterado.

Decisões do usuário (2026-09-18): terceira opção "Por regime tributário" (1a); lista com
7 regimes, os 6 citados mais MEI (2b); vários regimes ao mesmo tempo (3a).
Decisão de arquitetura: **só frontend.** A tela converte os regimes marcados em
`empresa_ids` e chama a rota que já existe. O backend continua decidindo tudo:
flag `alocar_obrigacao` e interseção com `empresas_alvo` (`gerador.py:205`).

Itens:

1. **33.1 RED.** Prova Node de um módulo sem JSX, no molde de `payloadObrigacao.js`:
   (a) `REGIMES_GERACAO` tem 7 entradas, na ordem Simples Nacional, Lucro Real, Lucro Presumido, MEI, Isento, Imune, Terceiro Setor, com os valores de `models.py:101`, e **sem** `indefinido`;
   (b) `empresasDosRegimes(empresas, regimes)` devolve os ids cujo `regime_tributario` está no conjunto; dois regimes somam; empresa `indefinido` ou sem regime nunca entra;
   (c) `idsDoRecorte(modo, escolhidas, regimes, empresas)` devolve `null` em `todas`, a lista em `escolhidas` e os ids do regime em `regime`;
   (d) **a armadilha:** `podeGerar(...)` é falso quando o modo não é `todas` e a lista sai vazia. Isso vale para regime sem empresa e para nenhum regime marcado. Sem essa trava, a tela mandaria `[]`, e o backend lê vazio como "todas";
   (e) não-regressão: `escolhidas` com lista vazia continua bloqueado, como é hoje.
   Verifica: `node provas/prova_recorte_regime.js` sai com erro antes de o módulo existir.
2. **33.2** Estado do modal: `gerTodasEmp` (booleano) vira `gerModo` (`todas`, `escolhidas`, `regime`) mais `gerRegimes`. `gerarTarefas` e o botão passam a usar `idsDoRecorte` e `podeGerar`. O comentário de `Obrigacoes.jsx:134` continua valendo e é atualizado.
3. **33.3** "Para quais empresas?" com 3 opções exclusivas, no tipo 1 (decisão 5 do usuário): wrapper `role="radiogroup"` com `aria-label="Para quais empresas?"`, três `<button type="button">` com `aria-checked`, `title` com a dica, escolhido em `border-primary-600 bg-primary-50 text-primary-800`. Os dois `type="radio"` de `:1053` e `:1059` saem.
4. **33.4** Modo regime: 7 checkboxes com `check-app` (`index.css:36`), cada rótulo com a contagem de empresas ativas daquele regime, por exemplo "Lucro Real (8)". Abaixo, "N empresa(s) no recorte". A frase de consequência que já existe ("A empresa escolhida só recebe as obrigações que já a alcançam") vale também para este modo.
5. **33.5** Faixa de resumo (`:1103-1113`): terceiro ramo, "Para N empresa(s) de Lucro Real e Lucro Presumido". Botão bloqueado com `title` explicando quando `podeGerar` for falso.
6. **33.6 GREEN, build e gate.** Prova Node em exit 0, as provas do frontend em exit 0, `npm run build` compilando. `grep -n "—\|–"` e `grep -nE "#[0-9a-fA-F]{6}"` vazios nos arquivos tocados. Linhas `+` do diff sem `alert(`, `confirm(` ou `prompt(`.
7. **33.7 Conferência visual local.** Abrir o modal, escolher "Por regime tributário", marcar dois regimes e ver a contagem e o resumo mudarem. Marcar um regime sem empresa: o botão bloqueia.

**Critério de aceite:** prova em exit 1 e depois em 0; build verde; greps vazios; conferência visual no LOG com data e tela.

---

## Fase 34: publicar as fases 27, 28, 32 e 33

- **Status:** done (2026-09-18; `b612b2d` no ar, carimbo `20260918-1847`, conferido pelo usuário)
- **Duração estimada:** 20 min
- **Notas:** Fechar_Tarefa_Rodar_Verifica
- **Dependências:** fases 32 e 33
- **Output esperado:** push publicado e conferido.

O push leva junto as fases 27 e 28, que já estão commitadas e provadas. Com isso, a fase 30 passa a publicar só a 29.

Itens:

1. **34.1** Suíte inteira do backend e do frontend em exit 0, e `npm run build`.
2. **34.2** Arquivo novo entra na imagem: `COPY . .` nos dois `Dockerfile`, conferido no diff antes do push.
3. **34.3** Push, `git ls-remote` confirmando o ref, e carimbo de `/api/health` antes e depois, igual ao HEAD.
4. **34.4** Prova de fora, sem login: o bundle servido contém `Por regime tributário` (`curl` do `/assets/index-*.js` com `grep -c`). O `POST /api/publico/tarefa/<token inventado>` devolve 404, prova da fase 28.
5. **34.5 Conferência do usuário em produção.** Abrir o modal e escolher regimes, conferindo contagem e resumo. Se ele quiser gerar de verdade, a linha `CRIACAO_REGISTRO_CRITICO` aparece na aba Logs.

**Critério de aceite:** carimbo igual ao HEAD; os dois curls; conferência do usuário colada no LOG.

---

## Fase 35: "Não se aplica a esta empresa" no menu da tarefa

- **Status:** done (2026-09-18; prova com 19 itens, conferida pelo usuário; botão virou "Marcar como não se aplica" pelo verificador; irmão "Cancelar tarefa" escondido sem a flag)
- **Duração estimada:** 45 min
- **Notas:** TDD_RED_GREEN_REFACTOR, Escada_Preguica_de_Codigo, Padrao_IDOR, Padrao_Logging_Estruturado, Nunca_DELETE_Fisico, Padrao_Validacao_de_Input, Padrao_Modal, Sempre_Mostrar_Loading, Padrao_Loading_Estado, Acao_Primaria_a_Direita, Sem_Popup_Nativo, Portugues_BR_Acentuacao, Sem_Travessao
- **Dependências:** nenhuma
- **Output esperado:** `backend/app/services/excecao.py` novo (ou função no `gerador.py`, decidido no 35.2 pela escada); `routes/tarefas.py` e `Tarefas.jsx` alterados; `backend/provas/prova_nao_se_aplica_lote.py` novo.

O que existe e está desligado: rota `POST /tarefas/{id}/nao-se-aplica` (`routes/tarefas.py:802`) e a janela de motivo (`Tarefas.jsx:1222`). Nenhum item do menu abre a janela desde o commit `3500ca8`, de 09/09.

Itens:

1. **35.1 RED.** Prova escrita antes, com exit 1 no código de hoje:
   (a) sem a flag `alocar_obrigacao`, a rota devolve 403 e nada muda (hoje basta editar tarefa);
   (b) com a flag, a tarefa marcada vai para cancelada com `nao_se_aplica`, motivo, autor e data;
   (c) as OUTRAS tarefas em aberto (pendente, em andamento, atrasada) da mesma obrigação e empresa, de outras competências, também vão para cancelada com o mesmo motivo;
   (d) tarefa concluída da mesma obrigação e empresa não muda; tarefa de outra empresa ou de outra obrigação não muda;
   (e) a exceção nasce uma vez só, e a próxima geração não cria a tarefa para essa empresa;
   (f) uma linha `EDICAO_REGISTRO_CRITICO` com `tabela="tarefa"`, `lote=True`, `acao="nao_se_aplica"` e a contagem de canceladas, além da `CRIACAO_REGISTRO_CRITICO` da exceção que já existe;
   (g) não-regressão medida antes: tarefa avulsa continua 422, tarefa fora do escopo continua 404, motivo com menos de 3 letras continua 422.
2. **35.2** Uma função só, `aplicar_excecao(db, obrigacao_id, empresa_id, motivo, usuario)`, cria a exceção (idempotente, como hoje) e cancela as abertas em uma transação. A rota passa a usar `require_flag("alocar_obrigacao")` e chama a função. Soft sempre: `UPDATE` de status, nunca `DELETE`.
3. **35.3** Menu ⋯ (`Tarefas.jsx:~717`): item "Não se aplica a esta empresa", ícone `Ban`, entre Editar e Cancelar tarefa, só quando `ativa && tarefa.obrigacao_id && user.permissoes_efetivas.alocar_obrigacao` (precedente: `Documentos.jsx:35`).
4. **35.4** Janela existente revisada: texto diz que as outras tarefas em aberto da mesma obrigação também saem; botão primário `btn-danger` com texto de ação ("Não se aplica"), à direita; enquanto envia, botão desabilitado, texto no gerúndio e spinner; erro aparece dentro da janela, sem `alert()`.
5. **35.5 GREEN, suíte, build, gates.** Prova em exit 0; suítes do backend e do frontend em exit 0; build; travessão, hex e popup vazios nas linhas `+`.
6. **35.6 Conferência visual local:** o item aparece para admin e gestor e some para analista; a janela cancela a tarefa e as irmãs abertas.

**Critério de aceite:** prova 1 antes e 0 depois; suítes verdes; conferência visual no LOG.

---

## Fase 36: Desvincular escolhe as obrigações e respeita a regra

- **Status:** pending
- **Duração estimada:** 70 min
- **Notas:** as da fase 35, mais Padrao_Mass_Assignment, Sem_Select_Nativo, Componente_SelectBusca, Padrao_Estado_Vazio, Padrao_Selecao_em_Lote (precedente `check-app`), Tela_Nao_Tem_Manual, Verificacoes_Mecanicas_de_Tela, Protocolo_Revisao_de_Tela
- **Dependências:** fase 35 (usa `aplicar_excecao`)
- **Output esperado:** `routes/obrigacoes.py` e `Obrigacoes.jsx` alterados; `frontend/src/components/SelectBusca.jsx` novo; `backend/provas/prova_desvincular_regra.py` novo.

Itens:

1. **36.1 RED backend.** Prova com exit 1 hoje:
   (a) `GET /obrigacoes/alcance-empresa/{empresa_id}` devolve as obrigações ATIVAS que alcançam a empresa, cada uma com `via` (`regra`, `vinculo` ou `ambos`) e quantas tarefas em aberto ela tem ali; não lista a que já tem exceção;
   (b) `POST /obrigacoes/desvincular-empresa` com `empresa_id`, `obrigacao_ids` (lista de inteiros, não vazia) e `motivo` (3 a 500): tira o vínculo à mão quando existe, cria a exceção quando a empresa entra pela regra, e cancela as tarefas em aberto daquelas obrigações para aquela empresa;
   (c) depois disso, a geração do mês não cria tarefa dessas obrigações para essa empresa, e cria das outras;
   (d) validação: lista vazia, id que não é número, motivo curto, campo a mais (`extra="forbid"`) dão 422; obrigação que não alcança a empresa, ou que não existe, dá 422 e NADA muda (tudo ou nada);
   (e) sem a flag `alocar_obrigacao`, 403 nas duas rotas;
   (f) uma linha de log por chamada, com a contagem de exceções criadas, vínculos removidos e tarefas canceladas, sem razão social.
2. **36.2 GREEN backend.** Rota nova de alcance e a de desvincular reescrita em cima de `aplicar_excecao`, numa transação só.
3. **36.3 SelectBusca.** Componente pequeno em `src/components/SelectBusca.jsx`: campo de busca, lista filtrada, escolha única, sem `<select>`. Usado só neste modal.
4. **36.4 Modal reescrito.** Empresa pelo SelectBusca; lista das obrigações que a alcançam, com `check-app`, etiqueta "pela regra" ou "vinculada" e "N em aberto"; "Marcar todas" e "Limpar"; motivo obrigatório; estado vazio quando a empresa não recebe nenhuma obrigação; botão `btn-danger` "Desvincular N obrigação(ões)" à direita, com spinner e texto no gerúndio; resultado e erro dentro do modal, sem `confirm()` nem `alert()`. O botão "Desvincular empresa" da tela só aparece com a flag.
5. **36.5 GREEN, suíte, build, gates**, com os mesmos greps da fase 35 e `grep -n "<select"` vazio no modal.
6. **36.6 Conferência visual local:** escolher a empresa, ver as obrigações com a origem, desvincular duas e conferir que as tarefas em aberto delas saíram.

**Critério de aceite:** prova 1 antes e 0 depois; suítes verdes; conferência visual no LOG; CONFORMIDADE sem linha pendente das fases 35 e 36.

---

## Fase 37: publicar as fases 35 e 36

- **Status:** pending
- **Duração estimada:** 20 min
- **Notas:** Fechar_Tarefa_Rodar_Verifica
- **Dependências:** fases 35 e 36

Itens:

1. **37.1** Suítes e build verdes; `COPY . .` nos dois Dockerfile conferido (o componente e a prova são arquivos novos).
2. **37.2** Push, `git ls-remote`, carimbo de `/api/health` igual ao HEAD.
3. **37.3** Prova de fora, sem login: o bundle servido contém `Não se aplica a esta empresa` e `pela regra`; as duas rotas sem login devolvem 401.
4. **37.4** Conferência do usuário em produção, na Trops: desvincular `calculo_difal`, `entrega_DeSTDA` e `entrega_dirb` (ou as que ele escolher) e ver as tarefas em aberto delas sumirem da lista.

**Critério de aceite:** carimbo igual ao HEAD; os curls; conferência do usuário no LOG.

---

## Fora de escopo (cortado pela escada ou por decisão)

- **`alert()` e `prompt()` nativos já existentes em `Tarefas.jsx`** (`:305`, `:498`, `:500`, `:503` e outros): violam `Sem_Popup_Nativo`, mas são anteriores e espalhados pela tela. Código novo deste trabalho não usa nenhum. Volta como trabalho próprio de tela.
- **"Enviar documento ao cliente" aparecendo para toda tarefa ativa** (`Tarefas.jsx:703`): mesmo desenho do link, outra rota e outro fluxo. Volta se o usuário quiser o menu filtrado por sentido.
- **`extra="forbid"` nos schemas de obrigação:** a tela manda o formulário inteiro (`payloadObrigacao.js` espalha `...f`), e proibir campo extra derrubaria o salvar. O defeito real aqui era o campo faltando, e ele entra. Volta se o payload passar a ser montado campo a campo.
- **Contador "transmitidas sem recibo" no painel:** decisão 4 do usuário.
- **Enviar o recibo ao cliente:** decisão 2 do usuário.
- **Invalidar tokens de upload já emitidos para tarefas fora de "receber":** a recusa no `_tarefa_por_token` já os torna inúteis, e apagar a coluna seria destrutivo sem ganho.
- **Checkboxes crus fora do bloco "lado do documento"** (regimes, segmentos, seleção da listagem, `sabado_util`): ajuste pontual não reescreve a tela. Volta num trabalho de revisão da tela de Obrigações.

- **Filtro por regime no backend (`regimes` no body de `/gerar`):** o recorte por ids já existe e resolve. Um campo novo seria mais uma entrada para validar, sem ganho. Volta se a geração passar a rodar sem tela, por API ou por agendamento com recorte.
- **Opção "Sem regime cadastrado":** decisão 2b do usuário. Empresa `indefinido` não entra por regime. A contagem por regime mostra quem entra, e isso deixa a ausência visível. Volta se aparecer empresa esquecida na geração.
- **`alert()` do resultado e "Gerando…" dentro do botão, em `gerarTarefas` (`Obrigacoes.jsx:152-154`, `:1130`):** anteriores a este trabalho e fora do padrão (`Sem_Popup_Nativo`, `Padrao_Loading_Estado`). Código novo não usa nenhum dos dois. Volta num trabalho de revisão da tela de Obrigações.
- **Log da geração automática do dia 1 (`scheduler.py:37`):** já sai em `logger.info` com as contagens e não tem usuário para atribuir. Volta se a auditoria pedir o evento estruturado também para o agendamento.
- **Limite de uma geração por vez por usuário (Mapa_de_Conceitos_de_Seguranca, família 7):** o botão já bloqueia durante a chamada, e a geração não duplica tarefa. Volta se aparecer geração concorrente em produção.

## Histórico deste plano

- **2026-09-15:** aberto com as fases 27 a 31. Sete decisões do usuário antes da primeira linha, em duas rodadas; a segunda nasceu da `Padrao_Toggle_Tipos`, conferida pelo principal depois de o batedor ter lido errado.
- **2026-09-18:** acrescentadas as fases 32 a 34 (recorte por regime na geração e log da geração em lote). Quatro decisões do usuário numa rodada (1a, 2b, 3a, 4a). A fase 32 nasceu da ficha de segurança, confirmada no código pelo principal.
- **2026-09-18, fase 32:** o verificador de segurança achou o irmão da geração do mês, `POST /empresas`, que gera as tarefas da empresa nova em lote sem linha de tarefa. Entrou na própria fase, com RED próprio, sem pergunta ao usuário: é achado de verificador sobre o mesmo critério de aceite, e o precedente é a fase 23 (sete rotas irmãs). O item 32.2 dizia `log_event` só em `gerar_competencia`; a trava que ele protegia, `gerador.py` sem diff, continua de pé.
- **2026-09-18, fases 35 a 37:** abertas a pedido do usuário depois de ver 37 tarefas da Trops que não se aplicavam. Diagnóstico medido no código: o Desvincular só tirava vínculo à mão, e a regra de regime em branco alcança todas as empresas; o "Não se aplica" existia sem item de menu desde `3500ca8`. Quatro decisões numa rodada (1a, 2a, 3a, 4a). Executam antes das 29 a 31.

## Fora de escopo das fases 35 a 37

- **Os outros 66 `<select>` nativos do projeto:** o SelectBusca nasce para o modal do Desvincular, e o resto volta num trabalho de revisão das telas.
- **Tamanho de modal em `vw` (Padrao_Modal):** o projeto usa `max-w-*` do Tailwind em todos os modais; trocar só estes criaria dois padrões na mesma tela. Declarado como desvio do projeto.
- **ESC e clique fora:** os modais do projeto já não fecham por nenhum dos dois; nada a fazer.
- **Desfazer em lote:** a exceção se desfaz uma a uma no cadastro da obrigação, como hoje. Tarefa cancelada não volta sozinha ao desfazer (regra de 09/09). Volta se aparecer desvinculação errada em massa.
- **Desvincular a empresa de TODAS de uma vez:** decisão 1a. "Marcar todas" na lista cobre o caso com um clique.
- **Flag nova de permissão:** usa a `alocar_obrigacao`, que já existe. A `Matriz_VER_EDITAR` manda não criar ação além de ver e editar; as flags do projeto são anteriores a este trabalho (`PERMISSOES_SPEC.md`), e nenhuma nova entra.
