# PLANO FASEADO: periodicidade da obrigação (fases 38 a 42)

> **modo=autonomo** (escolhido em 2026-09-15, vale até o usuário pedir troca).
> Fases 1 a 37 fechadas, planos nos checkpoints. Aberto em 2026-09-19.
> O `CLAUDE.md` do projeto existe desde 16/08 e não se refaz.

## Fase 0: aprovação

- **Status:** done (aprovado sem ajustes em 2026-09-19)
- **Critério de aceite:** o usuário aprova este plano por escrito no chat.

---

## Fase 38: medir a competência que o recibo real traz

- **Status:** done (2026-09-19; DEFIS e ECF em 01/AAAA)
- **Duração estimada:** 10 min
- **Notas:** Anti_Puxa_Saco (não construir em cima de suposição)
- **Dependências:** fase 0
- **Output esperado:** a competência lida de um recibo anual real, colada no LOG.

A decisão 2 foi tomada sobre um achado provável. Esta fase prova ou derruba
antes de qualquer código.

1. **38.1** Ler, sem alterar nada, o `competencia_exemplo` dos modelos já salvos
   em produção (DEFIS da Trops e o que houver de ECF), pela API com o login do
   usuário ou pela tela Modelos.
2. **38.2** Se o recibo não trouxer o período, rodar `extrair_dados`
   (`validador.py:108`) sobre o PDF, localmente, se o usuário fornecer o arquivo.

**Critério de aceite:** a competência lida está no LOG. Se for `01/AAAA`, o
plano segue. Se não for, **para** e a regra da anual volta ao usuário antes da
fase 40.

---

## Fase 39: o servidor valida o que a periodicidade grava

- **Status:** done (2026-09-19; prova com 18 itens, o vazio da legada e dois null que derrubavam a listagem entraram pelo verificador)
- **Duração estimada:** 30 min
- **Notas:** Padrao_Validacao_de_Input, TDD_RED_GREEN_REFACTOR, Escada_Preguica_de_Codigo, Sem_Travessao
- **Dependências:** fase 38
- **Output esperado:** `backend/provas/prova_periodicidade_servidor.py`; `schemas.py` e `routes/obrigacoes.py` alterados.

1. **39.1 RED.** Prova com exit 1 hoje:
   (a) `meses_ativos` fora do formato (vazio, `13`, `0`, `a`, `1,,2`) dá 422 no POST e no PUT, e o banco não muda;
   (b) `meses_ativos` com repetido ou fora de ordem é aceito e gravado normalizado (`3,1,3` vira `1,3`);
   (c) `competencia_ref` fora de apelido conhecido ou inteiro entre -24 e 1 dá 422;
   (d) `-14` e `-3` são aceitos, e `calc_competencia(3, 2026, "-14")` dá `01/2025`;
   (e) o rótulo do Excel diz "14 meses antes" para `-14`, e não "-14";
   (f) não-regressão medida antes: os 4 apelidos, `-2`, `-3`, `-6`, e obrigação legada com `competencia_ref` nulo ou vazio, que continua listando e salvando (a lição do sentido vazio, fase 27).
2. **39.2** Validador `mode="before"` nos dois schemas de entrada, no molde do `_sentido_em_branco` (`schemas.py:229`): vazio vira o padrão, lixo vira 422. A saída continua tolerante.
3. **39.3** `_COMP` do Excel passa a usar a mesma regra de rótulo que a tela já usa (`RelacaoObrigacoes.jsx:14-22`).
4. **39.4 GREEN e suíte.** Prova nova em exit 0, suíte do backend em exit 0.

**Critério de aceite:** prova 1 antes e 0 depois, as duas saídas no LOG; suíte verde; travessão vazio nos arquivos tocados.

---

## Fase 40: o seletor Periodicidade na tela

- **Status:** done (2026-09-19; prova com 13 itens, conferida pelo usuário; aviso de competência divergente e rádio nos meses da Anual entraram na execução)
- **Duração estimada:** 60 min
- **Notas:** Padrao_Toggle_Tipos, Tela_Nao_Tem_Manual, Padrao_Formulario, Componente_SelectBusca, Sistema_de_Estilos, Verificacoes_Mecanicas_de_Tela, Protocolo_Revisao_de_Tela, Portugues_BR_Acentuacao, Sem_Travessao, Sem_Popup_Nativo, TDD_RED_GREEN_REFACTOR
- **Dependências:** fases 38 e 39
- **Output esperado:** `frontend/src/pages/periodicidade.js` e `frontend/provas/prova_periodicidade.js` novos; `Obrigacoes.jsx` alterado.

1. **40.1 RED.** Prova Node de um módulo sem JSX, no molde de `sentidoObrigacao.js`:
   (a) `PERIODICIDADES` com 4 opções na ordem Mensal, Trimestral, Anual, Personalizada, cada uma com `valor`, `rotulo` e `dica`;
   (b) `periodicidadeDe(meses)`: 12 meses é mensal; 4 meses a cada 3 é trimestral; 1 mês é anual; qualquer outra coisa é personalizada (inclusive vazio);
   (c) `mesesDe('trimestral', 5)` dá `2,5,8,11`; `mesesDe('anual', 3)` dá `3`; `mesesDe('mensal')` dá os 12;
   (d) `competenciaRefDe('anual', 3)` dá `-14`; `('anual', 7)` dá `-18`; `('trimestral', 4)` dá `-3`; `('trimestral', 5)` dá `-4`; e as competências calculadas batem com um oráculo escrito à mão (DEFIS março: 01 do ano anterior; ECF julho: 01 do ano anterior; trimestral abril: janeiro do mesmo ano; trimestral janeiro: outubro do ano anterior);
   (e) as 81 combinações reais de produção não precisam ser migradas: a prova lê os `meses_ativos` que a tela recebe e só classifica.
2. **40.2** Seletor tipo 1 "Periodicidade" acima dos meses: `role="radiogroup"` + `aria-label="Periodicidade"`, 4 `<button type="button" role="radio" aria-checked>`, `title` com a dica, escolhido em `border-primary-600 bg-primary-50 text-primary-800`.
3. **40.3** Os 12 botões de mês viram a escolha do mês de entrega na Anual e na Trimestral (clique marca o mês e, na trimestral, os de 3 em 3); na Personalizada, ligam e desligam como hoje; na Mensal, ficam todos marcados. O estado ligado sai do sólido `bg-primary-600 text-white` e passa ao visual do tipo 1, porque na Anual o mês é escolha exclusiva.
4. **40.4** "Competência referente a": na Anual e na Trimestral, o `<select>` dá lugar a um texto que diz a competência calculada ("Janeiro do ano anterior", "Primeiro mês do trimestre anterior"); na Mensal e na Personalizada, o `<select>` de hoje fica.
5. **40.5 GREEN, build e gates.** Prova Node em exit 0, provas do frontend em exit 0, `npm run build`. `grep -n "—\|–"` e hex nas linhas `+` vazios; nenhum `<select`, `alert(`, `confirm(` ou `prompt(` novo nas linhas `+`.
6. **40.6 Conferência visual local:** trocar entre as quatro periodicidades, escolher março na Anual e maio na Trimestral, ver os meses e a competência mudarem; abrir a DEFIS e a ECF e ver "Anual" já marcado.

**Critério de aceite:** prova 1 antes e 0 depois; build verde; greps vazios; conferência visual no LOG com data e tela.

---

## Fase 41: publicar e corrigir as anuais em produção

- **Status:** pending
- **Duração estimada:** 30 min, e depende da lista
- **Notas:** Fechar_Tarefa_Rodar_Verifica, Padrao_Logging_Estruturado, Nunca_DELETE_Fisico
- **Dependências:** fase 40

1. **41.1** Suítes e build verdes; `COPY . .` nos dois Dockerfile conferido (arquivos novos).
2. **41.2** Push, `git ls-remote`, carimbo de `/api/health` igual ao HEAD; bundle servido contém `Periodicidade` e `Primeiro mês do trimestre anterior`.
3. **41.3** SELECT só de leitura: obrigações ativas com 1 mês ou com 4 meses a cada 3, e as tarefas abertas delas com a competência de hoje.
4. **41.4** O usuário aprova a lista. As obrigações passam pela tela ou pelo PUT da API com o login dele (sai `EDICAO_REGISTRO_CRITICO`). Tarefa já gerada com competência errada: a correção volta ao usuário com a lista, antes de tocar, porque muda o casamento com recibo que já possa ter sido baixado.
5. **41.5** O mesmo SELECT de novo mostra as aprovadas com a competência nova e as outras intactas.

**Critério de aceite:** carimbo igual ao HEAD; bundle com os textos; contagem do segundo SELECT bate com a lista aprovada.

---

## Fase 42: conferência do usuário em produção

- **Status:** pending
- **Dependências:** fase 41

1. **42.1** O usuário abre a DEFIS, vê "Anual" com março e "Janeiro do ano anterior", e cadastra ou edita uma trimestral.
2. **42.2** CONFORMIDADE sem linha pendente das fases 38 a 42.

**Critério de aceite:** conferência relatada e colada no LOG.

---

## Fora de escopo (cortado pela escada ou por decisão)

- **Coluna `periodicidade` no banco:** decisão 1a. Volta se aparecer periodicidade que não se deduz dos meses (semestral com competência própria, por exemplo).
- **Importador de cronograma sem `log_event` e sem passar pelos schemas** (`importador_cronograma.py:275-293`): anterior a este trabalho e grava sempre os 12 meses. Volta se o importador passar a trazer periodicidade.
- **Os 13 `<select>` nativos do modal** (inclusive o da competência que fica na Mensal): o projeto usa `input-field` nativo em toda a tela; nenhum novo entra. Volta num trabalho de revisão da tela de Obrigações.
- **`alert()` e `confirm()` já existentes em `Obrigacoes.jsx`** (15 pontos): anteriores; nenhum novo entra.
- **Checkbox cru da seleção da listagem** (`Obrigacoes.jsx:411, :424`): anterior, fora do bloco tocado.
- **E-validador casar competência por intervalo** (aceitar qualquer mês do período): a decisão 2a resolve na origem. Volta se aparecer declaração cujo recibo não traga o período.
- **Envio automático da guia ao cliente pelo e-validador:** trabalho próprio, pedido em 19/09.

## Histórico deste plano

- **2026-09-19, fase 39:** entraram, com RED próprio e sem pergunta ao usuário (achado de verificador sobre o mesmo critério de aceite, precedente da fase 32), o vazio de meses da obrigação legada e dois defeitos anteriores: `meses_ativos` null dava 500 e `competencia_ref` null derrubava a listagem inteira. A rota de edição ganhou a decisão sobre o vazio, que o plano punha só no schema.

- **2026-09-19:** aberto com as fases 38 a 42. Quatro decisões do usuário numa rodada (1a, 2a, 3a lido de "3s", estilo 1). A fase 38 existe porque a decisão 2a foi tomada sobre achado provável e não medido.
