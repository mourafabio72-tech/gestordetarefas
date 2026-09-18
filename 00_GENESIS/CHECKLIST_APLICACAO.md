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

- [ ] 29.1 `prova_sentido_obrigacao.js` falhando antes de `sentidoObrigacao.js` existir
      (TDD_RED_GREEN_REFACTOR)
- [ ] 29.2 seletor tipo 1: wrapper `role="radiogroup"` com `aria-label`, opções em `<button type="button">` com `aria-checked`
      PROIBIDO: `type="radio"` com `name="sentido"`; visual de aba (sublinhado); sólido invertido (é do tipo 2)
      PROVA: `grep -n 'name="sentido"' frontend/src/pages/Obrigacoes.jsx` vazio e `grep -n 'role="radiogroup"'` acha 1
      (Padrao_Toggle_Tipos: "Sempre `<button type="button">`" e "Wrapper com `role="radiogroup"` + `aria-label`")
- [ ] 29.2 escolhido com borda, fundo suave e texto escuro do token: `border-primary-600 bg-primary-50 text-primary-800`
      (Padrao_Toggle_Tipos, tipo 1: "borda `var(--cor-primaria)` + fundo `var(--cor-primaria-suave)` + texto `var(--cor-primaria-escura)`", traduzido para o token `primary` do Tailwind)
- [ ] 29.2 explicação de cada opção no `title`, sem parágrafo fixo embaixo
      (Tela_Nao_Tem_Manual: "O rótulo do campo, o título da coluna e o `title` do botão carregam a informação.")
- [ ] 29.2 `bg-[#faf7f0]` removido do bloco
      PROVA: `grep -nE "#[0-9a-fA-F]{6}" frontend/src/pages/Obrigacoes.jsx frontend/src/pages/sentidoObrigacao.js` vazio
      (Sistema_de_Estilos: "o hex nunca aparece na tela")
- [ ] 29.3 identificadores visíveis por `mostraIdentificadores(form)`, e "Exige documento" por `exigeDocumentoMarcado(form)`
      PROVA: itens (b) e (c) da prova Node
- [ ] 29.4 quatro checkboxes do bloco com `check-app`
      PROIBIDO: `className="h-4 w-4"` nos checkboxes de Passível de multa, Exige robô, Alerta guia não-lida e Ativa
      PROVA: `grep -n "Passível de multa\|Exige robô\|Alerta guia não-lida\|/> Ativa" -B1 frontend/src/pages/Obrigacoes.jsx` mostra `check-app` nos quatro
      (Verificacoes_Mecanicas_de_Tela: checkbox cru é "o Windows 98")
- [ ] 29.5 aba "Comprovantes e recibos" e subtítulo coerente
      PROVA: `grep -n "Recebidos do cliente" frontend/src` vazio
- [ ] 29.6 prova Node e as 19 provas do frontend em exit 0; `npm run build` compilando
- [ ] 29.6 língua: acento completo no texto novo, zero travessão e en-dash
      PROVA: `grep -n "—\|–"` vazio nos arquivos tocados; leitura do diff frase a frase
      (Portugues_BR_Acentuacao; Revisao_Professor_Pasquale, sem executor nesta vault)
- [ ] 29.7 conferência visual local registrada no LOG com data e tela
      (Protocolo_Revisao_de_Tela)

## Fase 30: produção

- [ ] 30.1 suíte completa e build verdes
- [ ] 30.2 arquivos novos dentro da imagem (`COPY . .` nos dois Dockerfile)
- [ ] 30.3 carimbo antes e depois, igual ao HEAD; `git ls-remote` confirmando
- [ ] 30.4 `curl` do token público inventado devolve 404; bundle servido contém `Transmitir ao órgão`
- [ ] 30.5 conferência do usuário: trocar para Transmitir, salvar, reabrir, e a escolha ficou
      (Fechar_Tarefa_Rodar_Verifica)

## Fase 31: reclassificação

- [ ] 31.1 `SELECT` só de leitura entregue
- [ ] 31.2 lista de candidatas com motivo, aprovada pelo usuário no chat
- [ ] 31.3 troca pela tela, com `EDICAO_REGISTRO_CRITICO` saindo
      PROIBIDO: `UPDATE obrigacoes` no console
      (Padrao_Logging_Estruturado: mutação de dado crítico sempre entra)
- [ ] 31.4 segundo `SELECT` bate com a lista aprovada

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
