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

- **Status:** done (2026-09-19; `46b622e` no ar, carimbo `20260919-1707`; 3 anuais corrigidas)
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

- **Status:** done (2026-09-19; DEFIS conferida em produção, tarefa 29944 cancelada a pedido)
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

---

# Trabalho novo: e-validador (fases 43 a 46), aberto em 2026-09-19

> Pedido do usuário: "pode implantar os 3 itens que ficaram de fora: 1, 3 e 2". O item 1 (IRPJ e
> CSLL do Presumido em trimestral) foi ajuste de cadastro, feito e registrado no LOG. Os itens 3 e 2
> mexem no e-validador. Decisões numa rodada: 1a, 2a, 3a, 4a.

## Fase 43: o e-validador escolhe a chave mais específica (item 3)

- **Status:** done (2026-09-19; um único par afetado em produção, o do SPED)
- **Duração estimada:** 25 min
- **Notas:** TDD_RED_GREEN_REFACTOR, Escada_Preguica_de_Codigo (padrão irmão)
- **Output esperado:** `backend/provas/prova_chave_especifica.py`; `services/validador.py` alterado.

1. **43.1 RED.** Com as chaves reais de produção: recibo de SPED Contribuições casa só com a 170, e não com a 169; recibo de SPED Fiscal continua casando com a 169; duas obrigações com chaves independentes que casam no mesmo texto continuam ambíguas (o desempate não inventa escolha); `identificar_obrigacao` e a sugestão de Modelos usam a mesma regra.
2. **43.2 GREEN.** Em `identificar_obrigacao`: se a chave que casou numa candidata está contida na chave que casou em outra, a de chave menor sai. Uma função, os dois chamadores herdam.
3. **43.3** Suíte do backend em exit 0.

**Critério de aceite:** prova 1 antes e 0 depois; suíte verde.

## Fase 44: o e-validador guarda o arquivo que baixa (achado de 2026-09-19)

- **Status:** done (2026-09-19; troca de guia virou função única)
- **Duração estimada:** 25 min
- **Notas:** TDD_RED_GREEN_REFACTOR, Nunca_DELETE_Fisico
- **Output esperado:** `backend/provas/prova_evalidador_guarda_arquivo.py`; `services/validador.py` alterado.

Hoje `processar` grava só o nome (`validador.py:556`, `tarefa.anexo_nome = nome_arquivo`) e descarta o conteúdo: o acervo lista o recibo e o download não acha o arquivo.

1. **44.1 RED.** Recibo de `transmitir` e comprovante de `receber` baixados pelo e-validador: o arquivo existe no volume (`caminho_do_anexo` não é None) e o download do acervo devolve 200. Guia de `entregar`: vai para `saida_nome` (`salvar_saida`), que é o que o "Enviar ao cliente" lê.
2. **44.2 GREEN.** `receber`, `transmitir` e interna com documento: `salvar_arquivo` como já faz `registrar_baixa` (`upload.py:188`). `entregar`: `salvar_saida`.
3. **44.3** Suíte em exit 0.

**Critério de aceite:** prova 1 antes e 0 depois; suíte verde.

## Fase 45: a guia reconhecida sai para o cliente (item 2)

- **Status:** done (2026-09-19; prova com 13 itens, exceção de rede no meio do envio consertada pelo verificador)
- **Duração estimada:** 60 min
- **Notas:** TDD_RED_GREEN_REFACTOR, Escada_Preguica_de_Codigo, Padrao_Logging_Estruturado, Portugues_BR_Acentuacao, Sem_Travessao, Sistema_de_Estilos
- **Output esperado:** `backend/provas/prova_evalidador_envia_guia.py`; `routes/tarefas.py`, `routes/evalidador.py`, `services/validador.py`, `frontend/src/pages/EValidador.jsx` alterados.

Decisões: envio automático só se CNPJ e competência lidos na guia baterem com a tarefa (2a); se nenhum contato receber, a tarefa fica aberta com a guia anexada (3a); mesmos canais e destinatários do "Enviar ao cliente" (4a).

1. **45.1 RED**, com WhatsApp e e-mail substituídos por dublês (nada sai para a rede na prova):
   (a) guia de `entregar` reconhecida e conferida: vai aos destinatários do "Enviar ao cliente", um `TarefaEnvio` por destinatário, e a tarefa conclui;
   (b) nenhum envio funciona: tarefa aberta, guia anexada, status `envio_falhou` no resultado;
   (c) CNPJ ou competência da guia divergem da tarefa (`conferir_saida`): nada é enviado, guia anexada, status `aguardando_conferencia` com o motivo;
   (d) empresa sem contato: nada é enviado, guia anexada, status `sem_destinatario`;
   (e) não-regressão: `receber` e `transmitir` continuam baixando como hoje, sem envio nenhum; `ja_baixada` e `cancelada` não enviam;
   (f) uma linha de log por guia enviada, com a contagem de envios, sem endereço nem telefone.
2. **45.2 GREEN.** O miolo de `enviar_ao_cliente` (`routes/tarefas.py:648`) vira função de serviço, chamada pela rota de hoje e pela do e-validador. `processar` continua síncrono e só marca a tarefa como pronta para envio; a rota `/evalidador/processar`, que já é assíncrona, chama o envio. Sem duplicar a regra de "só conclui se alguém recebeu".
3. **45.3** Tela do e-validador: rótulos dos status novos (`Enviada ao cliente`, `Envio falhou`, `Aguardando conferência`, `Sem destinatário`), com os tokens de cor que a tela já usa.
4. **45.4 GREEN, suítes, build, gates** (travessão, hex e popup nas linhas `+`).

**Critério de aceite:** prova 1 antes e 0 depois; suítes verdes; build; gates vazios.

## Fase 45b: a competência da guia (decisões a e b de 2026-09-19)

- **Status:** done (2026-09-19; DARFs 2089 e 2372 em -1 em produção)
- **Notas:** TDD_RED_GREEN_REFACTOR, Padrao_Toggle_Tipos, Portugues_BR_Acentuacao, Sem_Travessao

1. **45b.1 (a)** `extrair_dados` lê "Período de apuração dd/mm/aaaa" quando o documento não traz período de/a; competência = mês/ano da data. RED antes. Não-regressão: recibo com de/a continua lendo o início.
2. **45b.2 (b)** `periodicidade.js`: Trimestral de `entregar` usa o último mês do trimestre anterior, `-(((M-1)%3)+1)`; `transmitir` e `receber` continuam no primeiro. Texto calculado: "Último mês do trimestre anterior". Trocar o sentido com Trimestral escolhida recalcula a competência. A divergência compara o deslocamento, e não o texto (`mes_anterior` é -1). RED antes, no molde da prova da fase 40.
3. **45b.3** Depois de publicar: 199 e 200 com competência -1 (março para entrega em abril), pelo PUT com o login do usuário.

## Fase 46: publicar e conferir

- **Status:** done (2026-09-21; DAS real enviado em produção)
- **Notas:** Fechar_Tarefa_Rodar_Verifica

1. **46.1** Suítes, build, `COPY . .`, push, `git ls-remote`, carimbo igual ao HEAD, bundle com `Enviada ao cliente`.
2. **46.2** Conferência do usuário em produção, com uma guia REAL que já precisa ir ao cliente: subir no e-validador, ver `Enviada ao cliente`, e o cliente recebendo. Não se testa com guia inventada, porque o envio é de verdade.
3. **46.3** Conferência do item 3: um recibo de SPED Contribuições no e-validador baixa a 170 sem ambiguidade.

**Critério de aceite:** carimbo igual ao HEAD; as duas conferências no LOG.

## Fora de escopo das fases 43 a 46

- **Reenvio automático quando o envio falha:** a tarefa fica aberta e o "Enviar ao cliente" da tela reenvia. Volta se falha de envio virar rotina.
- **Recuperar os arquivos que o e-validador descartou até hoje:** não existem mais; o conserto vale daqui para a frente. A lista das tarefas afetadas pode ser levantada se o usuário quiser reenviar algum.

---

# Trabalho novo: mensagem ao cliente (fases 47 a 49), aberto em 2026-09-21

> Decisões: e-mail só com o link (controle de abertura); nome legível pelo Mininome (1a);
> texto proposto aprovado (2a); WhatsApp com o mesmo texto, sem logo (3a).

## Fase 47: a mensagem nova

- **Status:** done (2026-09-21)
- **Notas:** TDD_RED_GREEN_REFACTOR, Portugues_BR_Acentuacao, Sem_Travessao, Padrao_Logging_Estruturado
- **Output esperado:** `backend/provas/prova_mensagem_cliente.py`; `services/entrega_cliente.py`, `services/email.py` alterados; `backend/app/static/logo-bps4.png` novo.

1. **47.1 RED**, com dublês: o e-mail sai SEM anexo; tem versão texto e HTML; o HTML leva o logo por CID e o botão com o link do destinatário; assunto "BPS4 | <nome>, <mês>/<ano>, <empresa>"; o nome é o Mininome quando preenchido e o nome da obrigação quando não; competência por extenso ("agosto/2026"); vencimento em dd/mm/aaaa quando a tarefa tem, e a linha some quando não tem; WhatsApp com o mesmo texto e o link; não-regressão: um TarefaEnvio por destinatário, link único por envio, e o texto do e-mail escapa HTML do nome da empresa.
2. **47.2 GREEN.** `send_email` ganha `html` e `imagens` (inline por CID), sem mudar quem já chama só com texto. A mensagem é montada numa função só, usada pelos dois canais.
3. **47.3** Suíte e travessão.

## Fase 48: mininomes legíveis das obrigações de entregar

- **Status:** done (2026-09-22)
1. **48.1** Leitura das obrigações de entregar em produção (nome, mininome, identificadores).
2. **48.2** Proposta de mininome legível para cada uma, aprovada pelo usuário.
3. **48.3** Gravação pelo PUT com o login dele (sai EDICAO_REGISTRO_CRITICO), releitura conferindo.

## Fase 49: publicar e conferir

- **Status:** done (2026-09-22; conferido no Gmail)
1. **49.1** Suítes, build, `COPY . .` (o logo é arquivo novo), push, carimbo igual ao HEAD.
2. **49.2** Conferência: reenviar a guia da tarefa 29967 pelo "Enviar ao cliente", e o usuário ver no Gmail o assunto, o logo, o botão, e nenhum anexo.

## Fora de escopo das fases 47 a 49

- **Logo por URL pública:** Outlook e parte do Gmail bloqueiam imagem externa por padrão; embutido por CID aparece sempre.
- **Valor da guia no e-mail:** a tarefa não guarda o valor, e ler do PDF a cada envio é outro trabalho.


---

# Trabalho novo: furos de permissão (fases 50 e 51), aberto em 2026-09-23

> Decisões: anexar e enviar guia exigem editar em tarefas; criar tarefa com escopo
> reduzido só para responsável no alcance, e sem responsável fica com quem criou.

## Fase 50: as três rotas exigem permissão

- **Status:** done (2026-09-23; prova com 32 itens, dois verificadores LIMPO)
- **Notas:** TDD_RED_GREEN_REFACTOR, Padrao_IDOR, Escada_Preguica_de_Codigo
- **Output esperado:** `backend/provas/prova_permissao_envio_criacao.py`; `routes/tarefas.py` alterado; botões da tela escondidos para quem não edita.

1. **50.1 RED.** Consulta recebe 403 em anexar guia e em enviar (ensaio e real), e a guia não muda; analista cria tarefa para outro responsável e recebe 403; analista sem responsável fica como responsável; não-regressão: analista anexa e envia na própria, admin cria para qualquer um.
2. **50.2 GREEN.** `require_perm("tarefas", "editar")` nas duas rotas; conferência do alcance em `create_tarefa`.
3. **50.3** Tela: anexar e enviar só aparecem para quem edita tarefas.
4. **50.4** Suítes, build, travessão.

## Fase 51: publicar e conferir

- **Status:** done (2026-09-23; carimbo `20260923-1311`, produção lida: 0 clientes, 0 overrides)
1. **51.1** Push, carimbo igual ao HEAD, prova de fora (sem login 401).
2. **51.2** Conferência dos grupos e overrides em produção, com o login do usuário.

## Fase 52: excluir obrigação só admin e gestor (decisão de 2026-09-23)

- **Status:** done (2026-09-23; carimbo `20260923-1938`)
1. **52.1** RED em `prova_excluir_obrigacao_gestor.py`; `DELETE /obrigacoes/{id}` e `POST /obrigacoes/excluir-lote` com `require_gestor_ou_admin`; tela esconde a exclusão de quem não é admin ou gestor.

## Fase 53: link de envio exige editar em tarefas

- **Status:** done (2026-09-23; carimbo `20260923-2029`)
1. **53.1** RED nos itens 33 a 35; `GET /tarefas/{id}/link-envio` com `require_perm("tarefas", "editar")`; tela esconde "Copiar link de envio".

## Histórico deste trabalho

- **2026-09-23:** fases 52 e 53 entraram por decisão do usuário no chat e foram registradas no LOG, mas não neste plano; escritas aqui em retroativo na retomada de 23/09, junto do status da 51.
