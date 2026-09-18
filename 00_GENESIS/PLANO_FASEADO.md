# PLANO FASEADO: obrigação acessória transmitida ao órgão (fases 27 a 31)

> **modo=autonomo** (escolhido em 2026-09-15)

> Fases 1 a 26 fechadas, planos nos checkpoints. Aberto em 2026-09-15.
> Fase 0 deste trabalho: aprovação do usuário. Fase 1 (CLAUDE.md do projeto)
> já existe desde 16/08 e não se refaz.

## Fase 0: aprovação

- **Status:** done (aprovado sem ajustes em 2026-09-15)
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

## Fora de escopo (cortado pela escada ou por decisão)

- **`alert()` e `prompt()` nativos já existentes em `Tarefas.jsx`** (`:305`, `:498`, `:500`, `:503` e outros): violam `Sem_Popup_Nativo`, mas são anteriores e espalhados pela tela. Código novo deste trabalho não usa nenhum. Volta como trabalho próprio de tela.
- **"Enviar documento ao cliente" aparecendo para toda tarefa ativa** (`Tarefas.jsx:703`): mesmo desenho do link, outra rota e outro fluxo. Volta se o usuário quiser o menu filtrado por sentido.
- **`extra="forbid"` nos schemas de obrigação:** a tela manda o formulário inteiro (`payloadObrigacao.js` espalha `...f`), e proibir campo extra derrubaria o salvar. O defeito real aqui era o campo faltando, e ele entra. Volta se o payload passar a ser montado campo a campo.
- **Contador "transmitidas sem recibo" no painel:** decisão 4 do usuário.
- **Enviar o recibo ao cliente:** decisão 2 do usuário.
- **Invalidar tokens de upload já emitidos para tarefas fora de "receber":** a recusa no `_tarefa_por_token` já os torna inúteis, e apagar a coluna seria destrutivo sem ganho.
- **Checkboxes crus fora do bloco "lado do documento"** (regimes, segmentos, seleção da listagem, `sabado_util`): ajuste pontual não reescreve a tela. Volta num trabalho de revisão da tela de Obrigações.

## Histórico deste plano

- **2026-09-15:** aberto com as fases 27 a 31. Sete decisões do usuário antes da primeira linha, em duas rodadas; a segunda nasceu da `Padrao_Toggle_Tipos`, conferida pelo principal depois de o batedor ter lido errado.
