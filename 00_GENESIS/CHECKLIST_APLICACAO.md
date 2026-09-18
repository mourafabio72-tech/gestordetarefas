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
