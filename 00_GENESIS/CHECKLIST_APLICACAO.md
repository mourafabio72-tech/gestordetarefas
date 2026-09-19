# CHECKLIST das fases 27 a 31

Só marcar `[x]` com evidência apontável: arquivo e linha, ou saída de comando.

```
Cor de marca: token primary do Tailwind (frontend/tailwind.config.js:12), nunca hex em JSX
Tema: claro (Sage & Creme)
Acesso: login por perfil
```

## Fase 27: backend

- [x] 27.1 `prova_transmitir_orgao.py` escrita ANTES e saindo com exit 1, saída colada no LOG
      PROIBIDO: prova que passa de primeira; matriz sem os 24 casos
      (TDD_RED_GREEN_REFACTOR)
      EVIDÊNCIA: LOG 2026-09-15T16:20, `PROVA FALHOU nos itens: [2, 3, 4, 5, 6, 7, 10, 19]`, exit 1; item 11 garante os 24 casos
- [x] 27.1 itens de não-regressão (`receber`, `entregar`, `interna` sem flag) verdes JÁ no RED
      EVIDÊNCIA: itens 15 a 18 verdes na mesma saída do RED
      (TDD_RED_GREEN_REFACTOR, precedente da fase 26)
- [x] 27.2 `perfil_documento` em `models.py`, e `painel.py` chama a função em vez de repetir a regra
      PROIBIDO: `if sentido == "interna": return sentido, False` sobrando no `painel.py`
      PROVA: `grep -n 'sentido == "interna"' backend/app/routes/painel.py` volta vazio
      (Escada_Preguica_de_Codigo: "a correção preguiçosa É a correção de causa raiz")
      EVIDÊNCIA: grep rc=1 vazio; definição `models.py:380`, chamadas `models.py:377` e `painel.py:94`
- [x] 27.3 `Literal["receber", "entregar", "interna", "transmitir"]` em `ObrigacaoBase` e `ObrigacaoUpdate`
      PROIBIDO: `sentido: Optional[str]` livre; `sentido` ausente do schema de edição
      PROVA: `grep -n "sentido" backend/app/schemas.py` mostra o `Literal` nos dois schemas
      (Padrao_Validacao_de_Input: "Toda string crua passa por validação tipada antes de tocar regra de negócio")
      EVIDÊNCIA: `schemas.py:226` define, `:244` ObrigacaoBase, `:296` ObrigacaoUpdate; `:329` é a saída, tolerante de propósito (LOG 16:35); vazio vira None por `_sentido_em_branco` (`:229`, aplicada em `:245` e `:297`, LOG 17:25). Linhas remedidas depois do conserto do vazio
- [x] 27.3 valor inválido recusado no servidor com 422, e o banco não muda
      (Padrao_Validacao_de_Input, anti-padrão "Validar só no `<input required>` do HTML")
      EVIDÊNCIA: itens 5, 6, 7 e 8 da prova verdes no GREEN, vermelhos 5 a 7 no RED
- [x] 27.4 comentários de sentido falam em quatro valores
      PROVA: `grep -n "transmitir" backend/app/models.py backend/app/schemas.py`
      EVIDÊNCIA: `models.py:338, :395, :450, :455`; `schemas.py:211, :226`; `validador.py:267`
- [x] 27.5 prova nova em exit 0 e suíte do backend em exit 0
      (Fechar_Tarefa_Rodar_Verifica)
      EVIDÊNCIA: `PROVA OK: 22 checagens verdes` exit 0 (eram 19; itens 20 a 22 vieram dos verificadores, LOG 17:05 e 17:15); `provas=31 falharam=0`
- [x] 27.5 zero travessão nos arquivos tocados
      PROVA: `grep -n "—\|–" <arquivos do diff>` vazio
      (Sem_Travessao)
      EVIDÊNCIA: grep nos 5 arquivos (models, schemas, painel, validador, prova nova) rc=1 vazio

## Fase 28: link só para "receber"

- [x] 28.1 `prova_link_so_receber.py` com exit 1 antes, saída no LOG
      (TDD_RED_GREEN_REFACTOR)
      EVIDÊNCIA: LOG 2026-09-15T17:50, `PROVA FALHOU nos itens: [3, 4, 7, 8, 9, 10, 11, 12]`, exit 1
- [x] 28.1 item (d) de não-regressão: `/api/publico/baixar/{token}` do "entregar" segue 200, medido antes
      (regra local 3 do LASTRO)
      EVIDÊNCIA: item 15 verde no RED, `entregar: o cliente continua baixando a guia pelo link (200)`
- [x] 28.2 `baixar_documento` confirmado FORA do `_tarefa_por_token` antes de pôr a trava no helper
      PROVA: `grep -n "_tarefa_por_token" backend/app/routes/upload_publico.py` só nas rotas de contexto e envio
      (Escada_Preguica_de_Codigo: procurar todos os chamadores)
      EVIDÊNCIA: `grep -rn "_tarefa_por_token" app` ANTES do conserto devolveu `upload_publico.py:16` (definição), `:27` (contexto) e `:42` (enviar); nada em `baixar_documento` (`:62`). No arquivo atual, com o comentário do GREEN, as linhas são `:16`, `:30`, `:45` e `:65` (remedido após o verificador de evidência)
- [x] 28.2 os três pontos do servidor com a mesma checagem de sentido: régua, `link-envio`, token público
      PROIBIDO: travar só a tela ou só a régua, e deixar a rota pública aceitando upload
      (Escada_Preguica_de_Codigo, padrão irmão)
      EVIDÊNCIA: `whatsapp.py:742`, `tarefas.py:226`, `upload_publico.py:21`; grep de irmãos no LOG 18:05 sem quarto ponto; itens 3, 7, 9 e 11 da prova
- [x] 28.2 recusa do token público com o MESMO status e corpo de token inexistente
      (regra local 4 do LASTRO)
      EVIDÊNCIA: itens 10 e 11 (`json()` idêntico ao do token inexistente, GET e POST), vermelhos no RED
- [x] 28.2 `link-envio` recusado não cria `upload_token`
      (fase 26: o GET que muta)
      EVIDÊNCIA: item 8 verde; recusa em `tarefas.py:226` vem antes do `link_publico` em `:229`
- [x] 28.3 menu "Copiar link de envio" condicionado a `tarefa.sentido === 'receber'`
      PROIBIDO: `alert(` ou `prompt(` novos
      PROVA: `git diff frontend/src/pages/Tarefas.jsx | grep "^+" | grep -c "alert(\|prompt(\|confirm("` devolve 0
      (Sem_Popup_Nativo)
      EVIDÊNCIA: `Tarefas.jsx:709` `{ativa && tarefa.sentido === 'receber' && (`; o grep de popup devolve 0
- [x] 28.4 prova nova, `prova_escopo_link.py`, `prova_entrega_cliente.py` e suíte em exit 0
      EVIDÊNCIA: `PROVA OK: 16 checagens verdes` exit 0; `provas=32 falharam=0` (as duas citadas dentro); frontend 19 e build ok

## Fase 29: tela

- [x] 29.1 `prova_sentido_obrigacao.js` falhando antes de `sentidoObrigacao.js` existir
      (TDD_RED_GREEN_REFACTOR)
      EVIDÊNCIA: LOG 2026-09-18T19:08:53, `ERR_MODULE_NOT_FOUND` rc=1 antes de `sentidoObrigacao.js` existir; GREEN `PROVA OK: 9 checagens verdes`
- [x] 29.2 seletor tipo 1: wrapper `role="radiogroup"` com `aria-label`, opções em `<button type="button">` com `aria-checked`
      PROIBIDO: `type="radio"` com `name="sentido"`; visual de aba (sublinhado); sólido invertido (é do tipo 2)
      PROVA: `grep -n 'name="sentido"' frontend/src/pages/Obrigacoes.jsx` vazio e `grep -n 'role="radiogroup"'` acha 1
      (Padrao_Toggle_Tipos: "Sempre `<button type="button">`" e "Wrapper com `role="radiogroup"` + `aria-label`")
      EVIDÊNCIA: `grep name="sentido"` rc=1; `role="radiogroup"` em `Obrigacoes.jsx:935` (o grep acha 2: o outro é o da fase 33, `:1036`, que não existia quando este item foi escrito); quatro `<button type="button" role="radio" aria-checked>`
- [x] 29.2 escolhido com borda, fundo suave e texto escuro do token: `border-primary-600 bg-primary-50 text-primary-800`
      (Padrao_Toggle_Tipos, tipo 1: "borda `var(--cor-primaria)` + fundo `var(--cor-primaria-suave)` + texto `var(--cor-primaria-escura)`", traduzido para o token `primary` do Tailwind)
      EVIDÊNCIA: classe condicional no botão do seletor, `Obrigacoes.jsx:935` em diante, mesma string do seletor da fase 33
- [x] 29.2 explicação de cada opção no `title`, sem parágrafo fixo embaixo
      (Tela_Nao_Tem_Manual: "O rótulo do campo, o título da coluna e o `title` do botão carregam a informação.")
      EVIDÊNCIA: `title={s.dica}` no botão; as três descrições fixas em `<span class="block text-xs">` saíram da tela e viraram a `dica` de `SENTIDOS` (`sentidoObrigacao.js`); item 2 da prova exige dica em todas
- [x] 29.2 `bg-[#faf7f0]` removido do bloco
      PROVA: `grep -nE "#[0-9a-fA-F]{6}" frontend/src/pages/Obrigacoes.jsx frontend/src/pages/sentidoObrigacao.js` vazio
      (Sistema_de_Estilos: "o hex nunca aparece na tela")
      EVIDÊNCIA: grep nos dois arquivos rc=1 (LOG 19:11)
- [x] 29.3 identificadores visíveis por `mostraIdentificadores(form)`, e "Exige documento" por `exigeDocumentoMarcado(form)`
      PROVA: itens (b) e (c) da prova Node
      EVIDÊNCIA: `Obrigacoes.jsx:501` `mostraIdentificadores(form)`; checkbox Exige documento com `exigeDocumentoMarcado(form)`; itens 5 a 9 da prova, o 8 com as 24 combinações contra oráculo à mão
- [x] 29.4 quatro checkboxes do bloco com `check-app`
      PROIBIDO: `className="h-4 w-4"` nos checkboxes de Passível de multa, Exige robô, Alerta guia não-lida e Ativa
      PROVA: `grep -n "Passível de multa\|Exige robô\|Alerta guia não-lida\|/> Ativa" -B1 frontend/src/pages/Obrigacoes.jsx` mostra `check-app` nos quatro
      (Verificacoes_Mecanicas_de_Tela: checkbox cru é "o Windows 98")
      EVIDÊNCIA: grep dos quatro rótulos: `Obrigacoes.jsx:923, :950, :964, :967`, todos `className="check-app"`; `h-4 w-4` nas linhas `+`: 0
- [x] 29.5 aba "Comprovantes e recibos" e subtítulo coerente
      PROVA: `grep -n "Recebidos do cliente" frontend/src` vazio
      EVIDÊNCIA: grep rc=1; aba em `Documentos.jsx:175` "Comprovantes e recibos"; subtítulo cita comprovantes do cliente e recibos do órgão
- [x] 29.6 prova Node e as 19 provas do frontend em exit 0; `npm run build` compilando
      EVIDÊNCIA: `provas_front=21 falharam=0` (20 + a nova); `✓ built in 1.16s`
- [x] 29.6 língua: acento completo no texto novo, zero travessão e en-dash
      PROVA: `grep -n "—\|–"` vazio nos arquivos tocados; leitura do diff frase a frase
      (Portugues_BR_Acentuacao; Revisao_Professor_Pasquale, sem executor nesta vault)
      EVIDÊNCIA: travessão e en-dash rc=1 nos 4 arquivos, depois de trocar o travessão LITERAL que eu tinha deixado no regex da prova (LOG 19:10:07); leitura frase a frase das strings novas: 4 rótulos, 4 dicas, subtítulo e aba de Documentos; `pasquale.py` ausente, declarado
- [x] 29.8 entregar segue a regra geral: com identificadores e flag nula, exige a guia anexada (reescrito em 2026-09-19; a regra de 18/09 caiu)
      PROIBIDO: consertar só a tela; a trava da baixa manual lê o servidor
      (TDD_RED_GREEN_REFACTOR; Escada_Preguica_de_Codigo, causa raiz)
      EVIDÊNCIA: LOG 2026-09-19 prova_RED da decisão nova, `PROVA FALHOU nos itens: [15, 20, 23, 24]` rc=1, o 24 com (200); front AssertionError no 7b; GREEN `PROVA OK: 25 checagens verdes` e `PROVA OK: 10 checagens verdes`; `perfil_documento` sem ramo de entregar (`models.py`); `provas=35 falharam=0`, `provas_front=22 falharam=0`
- [x] 29.10 entregar mostra identificadores e "Exige documento"
      PROVA: item 7b da prova Node; `grep -n "!== 'entregar'" frontend/src/pages/Obrigacoes.jsx` vazio
      EVIDÊNCIA: 7b verde (flag nula, true e false); `mostraIdentificadores` sem ramo de entregar (`sentidoObrigacao.js:47-51`)
- [x] 29.7 conferência visual local registrada no LOG com data e tela
      (Protocolo_Revisao_de_Tela)
      EVIDÊNCIA: LOG 2026-09-19 conferencia_visual, tela Obrigações > editar obrigação na cópia local; itens 1, 2 e 4 conferidos pelo usuário; 3, 5 e 6 declarados como provados só pelo mecânico

## Fase 30: produção

- [x] 30.1 suíte completa e build verdes
      EVIDÊNCIA: provas=35 falharam=0, provas_front=22 falharam=0, build ok antes do commit (LOG fase=30 publicado)
- [x] 30.2 arquivos novos dentro da imagem (`COPY . .` nos dois Dockerfile)
      EVIDÊNCIA: `COPY . .` em backend/Dockerfile:17 e frontend/Dockerfile:8
- [x] 30.3 carimbo antes e depois, igual ao HEAD; `git ls-remote` confirmando
      EVIDÊNCIA: carimbo 20260918-2132 -> 20260919-1209, igual ao commit af0b6dd; ls-remote d3111f7b6858...
- [x] 30.4 `curl` do token público inventado devolve 404; bundle servido contém `Transmitir ao órgão`
      EVIDÊNCIA: token inventado: GET 404 e POST com arquivo 404; bundle index-BP1q-IXu.js com 'Transmitir ao órgão' (1)
- [x] 30.5 conferência do usuário: trocar para Transmitir, salvar, reabrir, e a escolha ficou
      EVIDÊNCIA: provado pelo banco: entrega_defis gravada como transmitir pela tela de produção (SELECT do 31.1)
      (Fechar_Tarefa_Rodar_Verifica)

## Fase 31: reclassificação

- [x] 31.1 `SELECT` só de leitura entregue
      EVIDÊNCIA: SELECT entregue e rodado pelo usuário no console do EasyPanel (84 ativas)
- [x] 31.2 lista de candidatas com motivo, aprovada pelo usuário no chat
      EVIDÊNCIA: 9 candidatas com motivo; 'aprovo todas' (LOG fase=31 lista_aprovada)
- [x] 31.3 troca pela tela, com `EDICAO_REGISTRO_CRITICO` saindo
      EVIDÊNCIA: PUT pela rota de edição com o login do usuário (autorizado: 'pode corrigir tudo'), e não UPDATE no console; 23 respostas 200 com EDICAO_REGISTRO_CRITICO; desvio declarado: não foi a tela, foi a API que a tela usa
      PROIBIDO: `UPDATE obrigacoes` no console
      (Padrao_Logging_Estruturado: mutação de dado crítico sempre entra)
- [x] 31.4 segundo `SELECT` bate com a lista aprovada
      EVIDÊNCIA: releitura GET: transmitir = [159, 168, 169, 170, 171, 172, 173, 178, 181, 185], a lista aprovada mais a DEFIS

---

# Recorte por regime na geração (fases 32 a 34, aberto em 2026-09-18)

## Fase 32: log da geração em lote

- [x] 32.1 `prova_gerar_log.py` escrita ANTES e saindo com exit 1, saída colada no LOG
      PROIBIDO: prova que passa de primeira
      (TDD_RED_GREEN_REFACTOR)
      EVIDÊNCIA: LOG 2026-09-18T18:50, `PROVA FALHOU nos itens: [2, 3, 4, 5, 6, 7, 8, 9, 10]`, rc=1; verdes no RED só o cenário (1) e a não-regressão (11 a 13)
- [x] 32.1 a linha é UMA por chamada, `CRIACAO_REGISTRO_CRITICO`, `tabela="tarefa"`, `lote=True`, com usuário, `mes_entrega`, `criadas`, `puladas`, nº de obrigações e nº de empresas do recorte
      PROIBIDO: uma linha por tarefa; razão social ou CNPJ na linha
      (Padrao_Logging_Estruturado: "Senha, token e PII NUNCA entram em log", "mutação de dado crítico SEMPRE entram")
      EVIDÊNCIA: itens 2 a 8 e 10 verdes no GREEN; linha única em `routes/obrigacoes.py:234`; campos `obrigacoes_no_recorte` e `empresas_no_recorte` (None sem recorte, item 10); item 7 procura as 3 razões sociais e os 3 CNPJs na linha serializada; item 8 recusa lista na linha
- [x] 32.1 geração com zero criadas também registra
      EVIDÊNCIA: item 9, segunda chamada igual com `criadas=0`, `puladas=4` e uma linha
- [x] 32.2 `log_event` só em `gerar_competencia` (`routes/obrigacoes.py`); `services/gerador.py` sem diff
      EVIDÊNCIA: `routes/obrigacoes.py:234-237`; `git diff --stat -- backend/app/services/gerador.py` vazio; `git diff --stat` mostra só `obrigacoes.py | 10`
      AMPLIADO pelo verificador de segurança (LOG 19:20): o irmão `create_empresa` também gera em lote e ganhou a mesma linha com `origem="cadastro_empresa"`, `routes/empresas.py:318`. O texto "só em `gerar_competencia`" deste item ficou superado; o que ele protegia, `gerador.py` sem diff, segue valendo
- [x] 32.3 suíte do backend em exit 0
      EVIDÊNCIA: `PROVA OK: 13 checagens verdes`; `provas=33 falharam=0` (32 + a nova); travessão rc=1 nos 2 arquivos; `escada:` rc=1
      REFEITO depois do irmão: `PROVA OK: 16 checagens verdes`; `provas=33 falharam=0`, com `prova_registro_critico.py` dentro; travessão rc=1 nos 3 arquivos

## Fase 33: tela

- [x] 33.1 `prova_recorte_regime.js` escrita ANTES e saindo com erro, saída no LOG
      (TDD_RED_GREEN_REFACTOR)
      EVIDÊNCIA: LOG 19:40, `ERR_MODULE_NOT_FOUND` rc=1 antes de `recorteGeracao.js` existir; segundo RED para `nomesDosRegimes` (`does not provide an export`), LOG 19:50
- [x] 33.1 `REGIMES_GERACAO` com 7 valores de `models.py:101`: `simples_nacional`, `lucro_real`, `lucro_presumido`, `mei`, `isento`, `imune`, `terceiro_setor`
      PROIBIDO: `indefinido` na lista; rótulo inventado fora dos que a tela de Empresas já usa
      (decisão 2b do usuário)
      EVIDÊNCIA: itens 1 a 3 da prova (valores, rótulos iguais a `Empresas.jsx:27-36`, `indefinido` fora); `recorteGeracao.js:12-20`
- [x] 33.1 `podeGerar` falso quando o modo não é `todas` e os ids saem vazios (regime sem empresa, nenhum regime marcado, nenhuma empresa escolhida)
      PROIBIDO: `empresa_ids: []` saindo da tela, que o backend lê como "todas"
      (armadilha medida em `Obrigacoes.jsx:1123-1125`)
      EVIDÊNCIA: itens 11, 12, 14, 15 e 16 da prova bloqueiam (15 é a não-regressão de "escolhidas" vazia, 16 é empresa bloqueada, LOG 20:25); o 13 é o lado que libera; modo desconhecido falha fechado (item 14); botão em `Obrigacoes.jsx:1165` usa `podeGerar`
- [x] 33.2 `gerTodasEmp` substituído por `gerModo` + `gerRegimes`; `grep -n "gerTodasEmp" frontend/src/pages/Obrigacoes.jsx` vazio
      EVIDÊNCIA: grep rc=1 vazio; `Obrigacoes.jsx:140` (`gerModo`), `:151` (`idsDoRecorte` na chamada)
- [x] 33.3 seletor "Para quais empresas?" no tipo 1, multi opções (decisão 5 do usuário, 2026-09-18): `role="radiogroup"` + `aria-label="Para quais empresas?"`, `<button type="button">` com `aria-checked`, `title` com a dica, escolhido em `border-primary-600 bg-primary-50 text-primary-800`
      PROIBIDO: `name="ger_alvo_emp"` (os radios crus); estilo escolhido sem pergunta
      PROVA: `grep -n 'name="ger_alvo_emp"' frontend/src/pages/Obrigacoes.jsx` vazio
      (Padrao_Toggle_Tipos: "NUNCA escolher o estilo sozinho")
      EVIDÊNCIA: `grep 'name="ger_alvo_emp"'` rc=1; wrapper em `Obrigacoes.jsx:1059`; três `<button type="button" role="radio" aria-checked>` com `title`; estilo decidido pelo usuário no LOG 18:35
- [x] 33.4 checkboxes de regime com `className="check-app"`, rótulo com contagem, "N empresa(s) no recorte" abaixo
      PROIBIDO: `h-4 w-4` nos checkboxes novos; switch `cv-sw` (não é liga/desliga)
      (Padrao_Toggle_OnOff: "checkbox é para MULTI SELEÇÃO"; precedente `check-app`, fase 8)
      EVIDÊNCIA: `Obrigacoes.jsx:1080` `check-app`; linhas `+` do diff sem `h-4 w-4` nem `cv-sw` (rc=1). A lista de "Somente as escolhidas", no mesmo bloco, também trocou `h-4 w-4` por `check-app` (LOG 20:00): no modal inteiro, `h-4 w-4` e `type="radio"` voltam vazios
- [x] 33.4 nenhum parágrafo novo de explicação fixa; a dica vai no `title`, e a frase de consequência que já existe é reaproveitada
      (Tela_Nao_Tem_Manual)
      EVIDÊNCIA: dicas nos três `title`; a dica fixa "cada obrigação vai para quem ela alcança" saiu do rótulo e foi para o `title`; a frase de consequência que já existia passou a valer para os dois recortes, sem texto novo; o único `<p>` novo é a contagem "N empresa(s) no recorte"
- [x] 33.5 faixa de resumo com o ramo de regime; botão bloqueado com `title` quando `podeGerar` é falso
      EVIDÊNCIA: `Obrigacoes.jsx:1147-1149` ("Para N empresa(s) de Lucro Real e Lucro Presumido", via `nomesDosRegimes`, item 17 da prova); `:1165-1171`, três textos de bloqueio conforme a causa
- [x] 33.6 prova Node em exit 0, provas do frontend em exit 0, `npm run build` ok
      EVIDÊNCIA: `PROVA OK: 17 checagens verdes`; `provas_front=20 falharam=0`; `✓ built in 1.17s` (remedido depois do conserto da bloqueada, LOG 20:25)
- [x] 33.6 `grep -n "—\|–"` e `grep -nE "#[0-9a-fA-F]{6}"` vazios nos arquivos tocados; linhas `+` do diff sem `alert(`, `confirm(`, `prompt(`
      (Sem_Travessao, Sistema_de_Estilos, Sem_Popup_Nativo)
      EVIDÊNCIA: travessão rc=1 nos 3 arquivos; hex em `recorteGeracao.js` rc=1 e nas linhas `+` do diff de `Obrigacoes.jsx` rc=1; popup nas linhas `+`: 0. NO ARQUIVO INTEIRO o hex NÃO volta vazio: `Obrigacoes.jsx:928` tem `bg-[#faf7f0]`, anterior a este trabalho e fora do modal, e é o item 29.2 que o remove. Correção de registro apontada pelo verificador de evidência, LOG 20:25
- [x] 33.7 conferência visual local registrada no LOG
      EVIDÊNCIA: conferido em 2026-09-18 pelo usuário ("ficou bom", print do modal no modo regime) e medido no navegador pelo principal, LOG 20:55 e 21:05: faixa numa linha só, dois regimes mudam contagem e resumo, regime sem empresa trava o botão com o `title` certo, ressalva em verde a pedido dele

## Fase 34: publicar

- [x] 34.1 suíte completa e build verdes
      EVIDÊNCIA: `provas=33 falharam=0`; `provas_front=20 falharam=0`; `✓ built in 1.16s`, antes do commit `b612b2d`
- [x] 34.2 `COPY . .` nos dois Dockerfile, conferido
      EVIDÊNCIA: `backend/Dockerfile:17` e `frontend/Dockerfile:8` com `COPY . .`; `.dockerignore` dos dois sem `provas` nem `src`; e o bundle servido contém o texto do módulo novo (34.4)
- [x] 34.3 `git ls-remote` com o ref; carimbo de `/api/health` igual ao HEAD
      EVIDÊNCIA: `git ls-remote` devolve `b612b2d96ae4...` em `refs/heads/main`; carimbo antes `20260910-1144`, depois `20260918-1847`, igual ao `git log -1` do HEAD (`b612b2d 20260918-1847`)
- [x] 34.4 bundle servido contém `Por regime tributário`; token público inventado devolve 404
      EVIDÊNCIA: `/assets/index-BCa-EY5M.js` com `grep -c "Por regime tribut"` = 1 e o texto `Nenhuma empresa ativa nos regimes marcados`; `GET` e `POST` com arquivo em `/api/publico/tarefa/token-inventado-x` devolvem `404 {"detail":"Link inválido ou expirado."}` (POST sem arquivo dá 422 antes de olhar o token, validação do corpo); `POST /api/obrigacoes/gerar` sem login dá 401
- [x] 34.5 conferência do usuário em produção colada no LOG
      EVIDÊNCIA: usuário respondeu "está ok" em 2026-09-18, depois de abrir o modal em gestordetarefas.zoaria.com.br (LOG da fase 34)
      (Fechar_Tarefa_Rodar_Verifica)

---

# "Não se aplica" e Desvincular pela regra (fases 35 a 37, aberto em 2026-09-18)

## Fase 35: "Não se aplica a esta empresa" no menu

- [x] 35.1 `prova_nao_se_aplica_lote.py` escrita ANTES e saindo com exit 1, saída no LOG
      PROIBIDO: prova que passa de primeira
      (TDD_RED_GREEN_REFACTOR)
      EVIDÊNCIA: LOG da fase 35 (prova_RED), `PROVA FALHOU nos itens: [2, 4, 5, 11, 12, 13]`, rc=1; GREEN `PROVA OK: 17 checagens verdes`; itens 18 e 19 do verificador funcional com RED próprio `[18, 19]`, GREEN `PROVA OK: 19 checagens verdes`
- [x] 35.1 não-regressão verde JÁ no RED: avulsa 422, fora do escopo 404, motivo curto 422
      EVIDÊNCIA: itens 15, 16 e 17 verdes na saída do RED; o 16 usa gestor COM a flag e escopo reduzido
- [x] 35.2 rota com `require_flag("alocar_obrigacao")`; sem a flag, 403 e nada muda
      PROIBIDO: checar a flag só na tela
      (decisão 3a do usuário; Padrao_Validacao_de_Input: "Validação acontece no servidor")
      EVIDÊNCIA: `routes/tarefas.py:807` `require_flag("alocar_obrigacao")`; item 2 (analista com `tarefas: editar` recebe 403, estado e exceções intactos), vermelho no RED com 200 e uma exceção criada
- [x] 35.2 uma função `aplicar_excecao`, usada pela rota; as abertas (pendente, em andamento, atrasada) da mesma obrigação e empresa vão para cancelada com o motivo
      PROIBIDO: `DELETE FROM tarefas`, `db.delete(tarefa)` no caminho novo; concluída mudando de status
      PROVA: `grep -n "delete" <função nova>` vazio; itens (c) e (d) da prova
      (decisão 2a; Nunca_DELETE_Fisico: "Regra inegociável em qualquer sistema, qualquer modo, qualquer tabela.")
      EVIDÊNCIA: `services/gerador.py:210`, chamada em `routes/tarefas.py:844`; grep de `delete` na função acha só a palavra no docstring ("nunca DELETE"), nenhuma chamada; itens 4 e 5 (em andamento e atrasada canceladas com motivo, autor e data), 6 (concluída intacta), 7 (cancelada à mão antes intacta), 8 (15 tarefas de outra empresa ou obrigação intactas)
- [x] 35.2 exceção e cancelamentos num commit só
      (Escada_Preguica_de_Codigo, guardrail "Perda de dados: transacao, rollback")
      EVIDÊNCIA: `aplicar_excecao` não chama `commit` (lida inteira, `gerador.py:210-250`); a rota faz um único `db.commit()` em `routes/tarefas.py:846`, depois da função
- [x] 35.2 log `EDICAO_REGISTRO_CRITICO`, `tabela="tarefa"`, `lote=True`, `acao="nao_se_aplica"`, com a contagem; sem razão social
      (Padrao_Logging_Estruturado)
      EVIDÊNCIA: `routes/tarefas.py:857`; itens 11 (uma linha), 12 (`canceladas: 3`, obrigação, empresa, usuário), 13 (sem razão social nem CNPJ), 14 (linha de criação da exceção continua), os três primeiros vermelhos no RED
- [x] 35.3 item "Não se aplica a esta empresa" com ícone `Ban`, entre Editar e Cancelar tarefa, só com `ativa && tarefa.obrigacao_id && user?.permissoes_efetivas?.alocar_obrigacao`
      PROVA: `grep -n "Não se aplica a esta empresa" -B3 frontend/src/pages/Tarefas.jsx` mostra a condição
      EVIDÊNCIA: `Tarefas.jsx:739` `{ativa && tarefa.obrigacao_id && podeDesvincular && (`, `:740` `icone={Ban}`; `podeDesvincular` em `:154` = `Boolean(user?.permissoes_efetivas?.alocar_obrigacao)`; o item vem depois de Editar e antes de Cancelar tarefa
- [x] 35.4 janela: texto fala das outras abertas; botão primário `btn-danger`, texto de ação e à direita; trifeedback ao enviar (desabilita, texto no gerúndio, spinner); erro dentro da janela
      PROIBIDO: `alert(` e `confirm(` nas linhas `+`; botão "Confirmar" ou "OK"
      (Padrao_Modal: "texto de botão genérico 'OK'/'Sim'" proibido; Sempre_Mostrar_Loading: "Os três juntos. Não basta um."; Acao_Primaria_a_Direita; Sem_Popup_Nativo)
      EVIDÊNCIA: texto da janela cita as outras em aberto; rodapé `justify-end` (`:1289`), `btn-danger` "Marcar como não se aplica" à direita (`:1299-1301`; o texto do plano, "Não se aplica", foi trocado pelo verificador de conformidade, Padrao_Modal regra 4), "Confirmar" saiu; trifeedback: `disabled` com `aplicandoNaoSeAplica`, "Aplicando...", e `Loader2 animate-spin` com texto na área da janela (`:1278-1282`); erro em `role="alert"` (`:1285`); popup nas linhas `+`: 0. Conflito Sempre_Mostrar_Loading x Padrao_Loading_Estado resolvido no LOG (tela). Falta a conferência visual (35.6)
- [x] 35.5 prova em exit 0; suítes do backend e do frontend em exit 0; build ok
      EVIDÊNCIA: `PROVA OK: 19 checagens verdes`; `provas=34 falharam=0` (depois de ajustar o override do usuário 'curioso' em `prova_eventos_log.py`, LOG codigo_GREEN); `provas_front=21 falharam=0`; `✓ built in 1.23s`
- [x] 35.5 `grep -n "—\|–"` vazio nos arquivos tocados; hex e popup nas linhas `+`: 0
      (Sem_Travessao, Sistema_de_Estilos, Sem_Popup_Nativo)
      EVIDÊNCIA: travessão rc=1 em `gerador.py`, `tarefas.py`, a prova nova e `Tarefas.jsx`; nas linhas `+` do `Tarefas.jsx`: hex 0, `alert(`/`confirm(`/`prompt(` 0
- [x] 35.6 conferência visual local registrada no LOG
      EVIDÊNCIA: conferido em 2026-09-18 pelo usuário ("conferi"), tela Tarefas, menu e janela na conferência local; regra dele registrada: só admin e gestor cancelam. Irmão "Cancelar tarefa" escondido sem `dispensar_demanda` (LOG irmao_menu)

## Fase 36: Desvincular pela regra

- [x] 36.1 `prova_desvincular_regra.py` escrita ANTES e saindo com exit 1
      (TDD_RED_GREEN_REFACTOR)
      EVIDÊNCIA: RED `PROVA FALHOU nos itens: [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 20, 21, 22, 24]`, rc=1; GREEN `PROVA OK: 27 checagens verdes` (LOG 20:53 e 20:56); depois dos verificadores, `PROVA OK: 30 checagens verdes` (item 28 motivo em branco; 29 e 30 separam a flag do módulo, e a troca de guarda passou a ser pega). Linhas remedidas depois dos consertos
- [x] 36.1 `alcance-empresa` devolve só obrigações ativas que alcançam a empresa, com `via` e `abertas`, e sem as que já têm exceção
      EVIDÊNCIA: `routes/obrigacoes.py:280` (`_alcance`) e `:298` (rota); `via_alcance` em `gerador.py:203`; itens 2 (inativa, outro regime, com exceção e modo vinculadas de fora não aparecem), 3 (regra, ambos, vinculo, vinculo), 4 (IPI 2 com a concluída fora, ECF 3), 22, 27
- [x] 36.2 body do desvincular com `extra="forbid"`, `obrigacao_ids: List[int]` não vazio, `motivo` 3 a 500; lista vazia, texto e campo a mais dão 422
      (Padrao_Mass_Assignment: "Backend define a whitelist de campos editaveis."; Padrao_Validacao_de_Input)
      EVIDÊNCIA: `routes/obrigacoes.py:133-142` (`extra="forbid"`, `Field(min_length=1, max_length=500)`, `motivo` 3 a 500); itens 6 a 10, todos 422 com o estado inteiro igual
- [x] 36.2 obrigação que não alcança a empresa, ou inexistente, dá 422 e nada muda (tudo ou nada)
      PROIBIDO: aplicar parte do lote e falhar no meio
      (Mapa_de_Conceitos_de_Seguranca, A01: "Validar a CADA requisição se o usuário tem direito ao recurso")
      EVIDÊNCIA: a lista inteira é conferida contra `_alcance` antes de qualquer mudança (`desvincular_empresa`, `routes/obrigacoes.py:315`), um `db.commit()` só (`:352`); itens 11 (fora do regime), 12 (inexistente) e 13 (já com exceção), cada um junto com uma válida, 422 e estado igual
- [x] 36.2 vínculo à mão removido quando existe; exceção criada quando entra pela regra; abertas canceladas por `aplicar_excecao`
      PROVA: itens (b) e (c) da prova; geração seguinte não recria
      EVIDÊNCIA: itens 15 (exceção para IPI e ECF, não para a DIRB), 16 (vínculo sai da ECF e da DIRB, o do relatório fica), 17 (8 abertas canceladas com motivo, autor e data), 18 (concluída intacta), 19 (Alfa e relatório intactos), 20 e 21 (geração de 11/2026). DESVIO DECLARADO no LOG 20:56: obrigação só pelo vínculo cancela por `cancelar_abertas` (`gerador.py:261`), sem exceção; `aplicar_excecao` chama a mesma função (`:258`)
- [x] 36.2 403 sem `alocar_obrigacao` nas duas rotas; uma linha de log por chamada, só contagem
      EVIDÊNCIA: `require_flag("alocar_obrigacao")` em `routes/obrigacoes.py:299` e `:318`; item 5 (403 nas duas, estado igual); linha em `:355`, itens 23 (uma), 24 (3 obrigações, 2 exceções, 2 vínculos, 8 tarefas, empresa, usuário), 25 (sem razão social nem CNPJ). Suíte `provas=35 falharam=0`
- [x] 36.3 `SelectBusca.jsx` em `src/components/`, busca e escolha única, sem `<select>`
      PROIBIDO: `<select` no modal do Desvincular
      PROVA: `grep -n "<select" ` no bloco do modal vazio
      (Sem_Select_Nativo: "Nunca usar `<select>` nativo."; Componente_SelectBusca)
      EVIDÊNCIA: `frontend/src/components/SelectBusca.jsx` novo, usado em `Obrigacoes.jsx:481`; `<select` no bloco do modal rc=1; no navegador, `querySelectorAll('select')` no modal = 0; busca sem acento provada no item 7 de `prova_desvincular_empresa.js`; caixa do modal com `overflow: visible` medido (LOG 21:05:59)
- [x] 36.4 lista com `check-app`, etiqueta de origem e "N em aberto"; "Marcar todas" e "Limpar"; motivo obrigatório
      PROIBIDO: `h-4 w-4` nos checkboxes novos
      (Padrao_Selecao_em_Lote; precedente `check-app`)
      EVIDÊNCIA: `Obrigacoes.jsx:535` `check-app`; `:524` e `:527`; etiqueta por `ETIQUETAS_VIA` com `title`; `N em aberto`; botão travado sem motivo (`podeDesvincular`, item 2 da prova front); `h-4 w-4` nas linhas `+`: 0
- [x] 36.4 estado vazio quando a empresa não recebe nenhuma obrigação, e nada escolhido ainda é outro texto
      (Padrao_Estado_Vazio: "Três estados distintos com textos diferentes")
      EVIDÊNCIA: `Obrigacoes.jsx:495` 'Nenhuma Empresa Escolhida' e `:510` 'Nenhuma Obrigação para Esta Empresa', ícones e subtítulos diferentes; o do meio (`:503`) é o carregando. O primeiro visto no navegador (LOG 21:05:59); o segundo falta na conferência do usuário
- [x] 36.4 botão `btn-danger` "Desvincular N obrigação(ões)" à direita, trifeedback, resultado e erro dentro do modal; o parágrafo de manual do topo sai
      PROIBIDO: `confirm(` e `alert(` no fluxo novo; parágrafo explicando a tela no topo
      (Sem_Popup_Nativo; Tela_Nao_Tem_Manual; Acao_Primaria_a_Direita)
      EVIDÊNCIA: rodapé `justify-end` `Obrigacoes.jsx:591`, `btn-danger` com `textoDoBotao` `:599` ('Desvincular 2 obrigações' visto no navegador); trifeedback: `disabled`, 'Desvinculando...' e spinner com texto na área (`:577`); resultado `role=status` e erro `role=alert` (`:586`); popup nas linhas `+`: 0; o parágrafo 'Remove o vínculo da empresa em todas...' saiu
- [x] 36.4 botão "Desvincular empresa" da tela só com `alocar_obrigacao`
      EVIDÊNCIA: `Obrigacoes.jsx:66` `podeAlocar` de `user?.permissoes_efetivas?.alocar_obrigacao`, envolvendo o botão em `:363`; o servidor recusa sozinho com 403 (item 5 da prova backend)
- [x] 36.5 prova, suítes e build verdes; greps de travessão, hex e popup
      EVIDÊNCIA: `PROVA OK: 30 checagens verdes` (backend) e `PROVA OK: 7 checagens verdes` (front); `provas=35 falharam=0`; `provas_front=22 falharam=0`; `✓ built in 1.20s`; travessão rc=1 nos arquivos tocados; hex, popup e `h-4 w-4` nas linhas `+`: 0
- [x] 36.6 conferência visual local registrada no LOG
      EVIDÊNCIA: conferido em 2026-09-18 pelo usuário ("conferi"), tela Obrigações > Desvincular empresa, na conferência local; medido antes por mim no navegador (LOG 21:05:59)

## Fase 37: publicar

- [x] 37.1 suítes e build verdes; `COPY . .` conferido
      EVIDÊNCIA: recorte só da 35 e 36 numa worktree limpa: build ok, `provas=35 falharam=0`, `provas_front=21 falharam=0`; `COPY . .` em `backend/Dockerfile:17` e `frontend/Dockerfile:8`; commit `7045b5d` (LOG recorte_e_commit)
- [x] 37.2 `git ls-remote` e carimbo igual ao HEAD
      EVIDÊNCIA: `166d59462f5f96d9fdce8edf6e9d042df6bc7798 refs/heads/main`; carimbo `20260918-1847` antes e `20260918-2132` depois, igual ao HEAD
- [x] 37.3 bundle com `Não se aplica a esta empresa` e `pela regra`; 401 sem login nas duas rotas
      EVIDÊNCIA: `index-Dz50vD9F.js` com as duas (3 e 3) e 'Transmitir ao órgão' 0 (a 29 não subiu); alcance e desvincular sem login: 401 e 401
- [x] 37.4 conferência do usuário em produção colada no LOG
      EVIDÊNCIA: teste do usuário na Trops em produção, conferido por leitura da API: tarefas 29965 e 29963 canceladas como não se aplica, exceção da empresa 6 nas obrigações 160 e 161, alcance sem as duas, tela com "Sem canceladas" e "25 tarefas" (LOG conferencia_producao)
      (Fechar_Tarefa_Rodar_Verifica)
