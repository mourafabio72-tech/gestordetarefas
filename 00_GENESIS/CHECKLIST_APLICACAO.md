# CHECKLIST DE APLICACAO

Trabalho: varios responsaveis por (empresa, setor). Aberto em 2026-09-09.

**So marcar `[x]` com evidencia apontavel: arquivo e linha, ou saida de teste.**

## Decisoes do topo, para nao esquecer no meio do caminho

```
Cor de marca: paleta `primary` do tailwind.config.js (Sage e Creme, oliva #5f7057)
              PROIBIDO hex escrito direto em JSX
Icones:       lucide-react (desvio declarado de Icones_Phosphor, ver LASTRO)
Tema:         light
Acesso:       login proprio por perfil (JWT de 8h), ja existente
Modelo:       principal (responsavel_id) mais M2M, espelhando a Tarefa
Retroativo:   NAO. Tarefa ja gerada nao muda.
```

## Fase 9: modelo e API

- [x] tabela associativa nova ligando o vinculo (empresa, setor) a N usuarios,
      declarada em `models.py:41-49` e criada pelo `Base.metadata.create_all` de
      `main.py:14`, que roda ANTES do `migrate()`
      MOTIVO CORRIGIDO EM 2026-09-09: o motivo escrito aqui na abertura estava
      errado, e o verificador de evidencia pegou. `Base.metadata.create_all` cria
      sim tabela nova, inclusive em base ja existente. O que ele NAO faz e
      acrescentar coluna em tabela que ja existe, e e por isso que coluna entra
      no `migrate()`. Escrever o DDL a mao no `migrate()` seria uma segunda
      definicao da mesma tabela, para divergir da primeira no dia que uma coluna
      mudar. O que precisa entrar no `init_db` e o INDICE, que o `create_all` nao
      cria em tabela pre-existente, e esse esta la
      PROVA: banco vazio, `DATABASE_URL=sqlite:///novo.db python -c "import app.main"`
      e depois `select name from sqlite_master`:
      TABELAS: ['empresa_setor_responsavel', 'empresa_setor_resp_usuarios', 'tarefa_responsaveis']
      INDICES: ['ix_resp_setor_usuario']
- [x] indice em `usuario_id` da tabela nova
      EVIDENCIA: `init_db.py:181` -- `("ix_resp_setor_usuario", "CREATE INDEX IF NOT EXISTS ix_resp_setor_usuario ON empresa_setor_resp_usuarios (usuario_id)")`, e o indice aparece no `sqlite_master` do banco novo (saida acima)
      MOTIVO: mesmo caso de `tarefa_responsaveis(usuario_id)`, resolvido em 2026-08-20:
      a PK comeca pelo outro lado e a busca por usuario varre a tabela
      PROVA: `grep -n "ix_.*resp_setor.*usuario" backend/app/init_db.py`
- [x] `responsavel_id` continua na tabela como PRINCIPAL, gravado num unico ponto,
      sempre igual ao primeiro da lista
      EVIDENCIA: o ponto unico e `services/resp_setor.py:gravar`, e os DOIS chamadores
      passam por ele: `routes/empresas.py:203` (tela) e
      `services/importador_resp_setor.py:107` (planilha). O importador gravava o
      `responsavel_id` por conta propria e era a segunda verdade que a regra 3 do
      LASTRO teme; foi ligado ao mesmo ponto agora, ainda com um id so, e a fase 12
      so troca o que le a celula. Itens 3 e 4 da prova: `ok 3. responsavel_id
      continua saindo, e vale o primeiro da lista` e `ok 4. inverter a lista inverte
      o principal`
      PROVA: a prova nova tem um caso que grava tres pessoas e confere que o
      `responsavel_id` e o primeiro; trocar a ordem muda o principal
- [x] GET devolve `responsavel_ids` (lista), mantendo `responsavel_id` para nao
      quebrar quem le o campo antigo
      EVIDENCIA: `routes/empresas.py:139-142` devolve as duas chaves; itens 2 e 3 da
      prova leem as duas pelo HTTP real. O `curl` previsto aqui nao roda contra
      producao porque a funcionalidade ainda nao foi publicada: a fase 17 confere no ar
      PROVA: `curl` do GET traz as duas chaves
- [x] PUT aceita `responsavel_ids: List[int]`
      EVIDENCIA: `grep -n "responsavel_ids" backend/app/routes/empresas.py` devolve 7
      linhas, a declaracao em `44: responsavel_ids: List[int] = Field(...)`
      PROVA: `grep -n "responsavel_ids" backend/app/routes/empresas.py`
- [x] o body valida ANTES de gravar: setor existe e esta ativo; cada usuario existe,
      nao e `tipo == "cliente"` e nao esta bloqueado; ids repetidos colapsam
      EVIDENCIA: `routes/empresas.py:164-183`, tudo antes do primeiro `delete` (`:185`).
      Itens 6 a 9 e 12 da prova. O item 11 e o que prova a ordem: `ok 11. recusa nao
      altera o que ja estava gravado`
      PROIBIDO: `db.add(...)` com id vindo do body sem checagem previa
      MOTIVO: "Todo endpoint que receber ID de recurso na URL ou no body deve validar
      que o usuario autenticado tem direito ao recurso ANTES de retornar dado.
      Sem excecao." (Padrao_IDOR:22-26)
      PROVA: a prova manda id inexistente e id de usuario cliente, e exige recusa
- [x] teto de tamanho na lista de ids
      EVIDENCIA: `MAX_RESP_POR_SETOR = 20` em `routes/empresas.py:36`, aplicado no
      schema (`:45`). Item 13: `ok 13. lista acima de 20 e recusada` (422, vindo do
      Pydantic, antes da funcao da rota)
      MOTIVO: a vault NAO tem regra para isso (buscado e nao encontrado, ver
      NOTAS_LIDAS). O teto entra por decisao local, com o numero escrito no codigo
      PROVA: a prova manda uma lista acima do teto e exige recusa
- [x] `extra = "forbid"` no schema do body
      EVIDENCIA: `grep -n "forbid"` devolve `40:` e `88:`, um por schema. Item 14 da prova
      MOTIVO: "Backend define a whitelist de campos editaveis. Tudo que veio no body
      e nao esta na whitelist eh ignorado." (Padrao_Mass_Assignment)
      PROVA: `grep -n "forbid" backend/app/routes/empresas.py`
- [x] recusa devolve 404, nunca 403
      EVIDENCIA: item 10, reforcado depois do verificador apontar que a versao
      anterior era tautologia. Agora exige que os cinco status sejam exatamente
      `{404}` E que o `detail` seja UM so entre "nao existe", "e cliente" e "esta
      bloqueado"
      MOTIVO: 403 confirma que o recurso existe (Padrao_IDOR)
      PROVA: a prova confere o status
- [x] `log_event` na regravacao da matriz, reusando `backend/app/seguranca.py:57`
      EVIDENCIA: `routes/empresas.py:205` (tela) e `:115` (planilha, achado do
      verificador: regravava a mesma matriz sem deixar rastro). Linha real capturada
      na saida da prova, com ids e contagem, sem nome, e-mail, senha ou token.
      NAO COBERTO: `request_id`, `path` e `method` nao existem no `log_event` deste
      projeto desde a Fase 7. Registrado na matriz como desvio declarado
      MOTIVO: "mutacao de dado critico SEMPRE entra" (Padrao_Logging_Estruturado)
      PROIBIDO: senha, token ou PII dentro do log
      PROVA: `grep -n "log_event" backend/app/routes/empresas.py`
- [x] `backend/provas/prova_responsaveis_multiplos.py` criada, com 19 casos, e
      verificado que ela REPROVA com a validacao removida
      EVIDENCIA: com o bloco `routes/empresas.py:164-183` retirado, a saida foi
      `HOUVE FALHA nos itens [6, 7, 8, 9, 11]`; com ele de volta, `TODAS AS PROVAS
      PASSARAM`. As duas saidas estao no LOG de 2026-09-09
      MOTIVO: "Regra listada nao e regra cumprida. So vira cumprida quando alguem
      prova." (Verificacoes_Mecanicas_de_Tela)
- [x] as 18 provas antigas do backend seguem passando
      EVIDENCIA: laco por `provas/prova_*.py` com o venv, rodado tres vezes (depois
      da rota, depois da extracao do ponto unico, e depois das correcoes dos
      verificadores): `provas com falha: 0 de 19`

## Fase 10: gerador

- [x] `_resp_do_setor` devolve lista, e `nova.responsaveis` recebe todos
      EVIDENCIA: `services/gerador.py:222-241` (lista, com o `responsavel` do vinculo
      servindo de rede para cadastro antigo sem lista) e `:296-300` + `:330`.
      `prova_gerador_multiplos.py`, bloco 1: `OK gerou UMA tarefa, e nao uma por
      pessoa (1)`, `OK os tres responsaveis estao na tarefa ([Ana, Bruno, Carla])`,
      `OK a ordem do cadastro e a ordem da tarefa`
- [x] supervisor sai do primeiro da lista, escada intacta (gestor da pessoa, gestor
      do setor, supervisor padrao da obrigacao)
      EVIDENCIA: bloco 2 da prova nova, um caso por degrau: `OK degrau 1: gestor da
      primeira pessoa da lista`, `OK degrau 2: sem gestor na pessoa, entra o gestor
      do setor`, `OK degrau 3: sem os dois, entra o supervisor da obrigacao`.
      `prova_gestor_setor.py` segue passando
- [x] `routes/tarefas.py:41` deixa de esconder a tarefa quando so o principal esta
      bloqueado; some apenas quando TODOS estiverem
      EVIDENCIA: a regra virou `app/visibilidade.py:responsavel_visivel()`, usada
      pela listagem (`routes/tarefas.py:41`), pela varredura de alertas
      (`services/whatsapp.py:720`) e pelo disparo manual. Fica num arquivo so
      porque a mesma regra em dois lugares diverge, e ai a tarefa aparece na tela
      sem gerar alerta. Bloco 3 da prova: `OK bloquear o principal NAO some com a
      tarefa`, `OK com TODOS bloqueados, ai sim a tarefa some (0)`, `OK desbloquear
      um traz a tarefa de volta`. Bloco 4: tarefa SEM dono nenhum continua
      aparecendo, porque buraco de cadastro escondido nao se arruma.
      REPROVA sem o fix, verificado: voltando a regra antiga, falham 4 casos
- [x] varridos os outros consumidores de responsavel unico (alertas, whatsapp, email,
      documentos) e corrigido o que passa a estar errado com N
      EVIDENCIA: varredura do backend E do frontend por um verificador de contexto
      limpo, mais os greps. TRES corrigidos: `routes/alertas.py:58` (disparo manual
      filtrava so `responsavel_id`, entao o segundo responsavel nao recebia nada e
      via a tarefa na tela), `services/whatsapp.py:764` (o ensaio mostrava so o
      primeiro nome de dois, mentindo por omissao na tela feita para conferir) e
      `services/whatsapp.py:651` (tarefa sem lista ficava sem destinatario nenhum).
      Blocos 6 e 7 da prova. Os demais ja tratavam a lista, e o que ficou de fora
      esta com o motivo no LOG

## Fase 11: tela

- [x] `components/SeletorResponsaveis.jsx` criado a partir do que ja existe em
      `pages/Tarefas.jsx:1287`, com modo inline e modo popover
      EVIDENCIA: o componente tem a MESMA marcacao da caixa antiga no modo inline
      (`SeletorResponsaveis.jsx:67-76`) e o popover no outro modo. A lista de
      pessoas, o checkbox e o contador "N selecionado(s)" sao literalmente os que
      estavam na tela de Tarefas
- [x] `pages/Tarefas.jsx` passa a usar o componente extraido, sem mudar de aparencia
      EVIDENCIA: `grep -c "responsavel_ids.includes" frontend/src/pages/Tarefas.jsx`
      devolve `0` (era a logica inline do JSX). CONFERENCIA VISUAL em 2026-09-09,
      modal Nova Tarefa: a caixa com rolagem, a lista de pessoas e o "0
      selecionado(s)" continuam iguais, agora com o checkbox proprio
- [x] cada linha de setor mostra os escolhidos como chips e abre o popover num botao
      EVIDENCIA: CONFERENCIA VISUAL em 2026-09-09. Com Ana Paula e Carla escolhidas
      no setor Societario, a linha mostra os dois chips, o primeiro destacado na cor
      da marca (e o principal). Salvar e reabrir o cadastro traz os dois de volta, e
      no banco: `Societario: principal=2 lista=[(2, Ana Paula), (4, Carla)]`
- [x] o checkbox de marcar pessoa nao e o cru do sistema operacional
      MOTIVO: ".tsel{ appearance:none; ...} Nunca o do sistema operacional."
      (Padrao_Selecao_em_Lote). Aqui vale o PRINCIPIO em Tailwind (`appearance-none`
      ou `accent-primary-600`), nao a classe `.tsel` de CSS puro, pelo precedente de
      2026-08-20 registrado no LOG
      PROVA: `grep -rn 'type="checkbox"' frontend/src/components/SeletorResponsaveis.jsx`
      e conferir que toda ocorrencia tem classe de aparencia propria
- [x] o checkbox "atende" CONTINUA checkbox, nao vira toggle
      MOTIVO: "O teste de uma pergunta: clicar nisso muda alguma coisa agora? Sim ->
      toggle. Nao, so marca para depois -> checkbox." (Padrao_Selecao_em_Lote). O
      "atende" so grava no submit do modal (`Empresas.jsx:147`), entao e checkbox
- [x] a aba NAO ganha filtro por coluna, ordenacao, exportar nem menu sanduiche
      MOTIVO: "as linhas sao registros comparaveis entre si? Se nao sao, e grade, nao
      tabela de listagem." (Padrao_Tabela). Um comentario no codigo diz por que
      PROVA: `grep -n "data-col-key\|TabelaAvancada" frontend/src/pages/Empresas.jsx`
      volta vazio
- [x] o popover nao fica cortado dentro do modal
      MOTIVO: "SEM `overflow:visible` o dropdown do SelectBusca fica CORTADO pelas
      bordas do modal" (Padrao_Modal_Popup_Centrado)
      PROVA: CONFERENCIA_VISUAL, tela de cadastro de empresa, aba de responsaveis,
      com o popover aberto no ultimo setor da lista
- [x] ESC e clique fora fecham o POPOVER e nao o modal
      MOTIVO: "O modal sai pelo X ou pelo Cancelar, e por mais nada." (Padrao_Modal_
      Nao_Fecha_Sozinho)
      PROVA: CONFERENCIA_VISUAL, mais caso na prova Node do estado do popover
- [x] nenhum hex escrito na tela
      MOTIVO: "PROIBIDO: o hex aparecer em qualquer template" (Sistema_de_Estilos)
      PROVA: `grep -rniE "#[0-9a-f]{6}" frontend/src/components/SeletorResponsaveis.jsx`
      volta vazio
- [x] nenhum travessao no texto que o usuario le NOS ARQUIVOS DESTA FASE
      MOTIVO: regra do CLAUDE.md da vault, fechada na Fase 6 e que REGREDIU depois
      PROVA: zero nos quatro arquivos desta fase (medido tirando comentario antes de
      contar). Mas `grep -rn "—" frontend/src` NAO volta vazio: sao 59 ocorrencias
      em texto visivel, em 11 telas, nenhuma delas deste trabalho. Numero e lista na
      matriz de conformidade, e a limpeza e trabalho proprio
- [x] logica fora do JSX, em `pages/seletorResponsaveis.js`, com
      `frontend/provas/prova_seletor_responsaveis.js` rodando em Node puro
      EVIDENCIA: 18 casos, todos passando, sem navegador e sem build. Os casos 17 e
      18 entraram depois do verificador achar que o popover sobrevivia ao fechamento
      do modal
- [x] `npm run build` sem erro
      EVIDENCIA: `built in 1.16s`, e as 16 provas Node do frontend com rc=0

## Fase 12: importador

- [x] celula aceita varios nomes separados por ponto e virgula
      EVIDENCIA: `importador_resp_setor.py:97-99`, e o bloco 1 da
      `prova_importar_resp_multiplos.py`: `OK os dois entraram, na ordem da celula
      ([Ana Paula, Bruno Sa])` e `OK a primeira da celula e a principal`. A ordem da
      celula e a ordem da lista, entao a planilha decide o principal igual a tela
- [x] nome desconhecido no meio vira aviso e nao derruba a linha
      EVIDENCIA: bloco 2 da prova. Com "Ana Paula; Fulano Que Nao Existe; Carla" a
      lista fica `[Ana Paula, Carla]` e sai UM aviso nomeando quem ficou de fora:
      `Fiscal: nao encontrei 'Fulano Que Nao Existe', os demais foram gravados.`
      `erros: 0`, porque aviso nao e erro. O bloco 3 cobre o caso de nenhum nome
      casar, que marca o setor sem responsavel
- [x] celula vazia continua desmarcando o setor, como e hoje
      EVIDENCIA: bloco 4 da prova, e com ele um caso que o item nao pedia e que
      valia conferir: desmarcar NAO deixa linha orfa na tabela do meio. O bloco 5
      prova que reimportar SUBSTITUI a lista em vez de empilhar, e o 6 que o mesmo
      nome duas vezes na celula colapsa
- [x] o modelo XLSX baixavel traz a instrucao do ponto e virgula
      EVIDENCIA: bloco 7 da prova, que ABRE o arquivo gerado e le o conteudo, o que
      e mais forte do que a conferencia visual prevista: a linha de exemplo passou a
      ser `Ana Paula; Bruno Sa`, e o rodape explica a regra por extenso, inclusive
      que a primeira e a principal. Sem isso, quem abre o modelo nao tem como
      adivinhar que cabe mais de um nome na celula, e o recurso existiria sem
      ninguem usar

## Fase 13: o responsavel sai da obrigacao

- [x] `services/gerador.py:296` deixa de cair em `o.responsavel`; quem atende sai SO da
      matriz da empresa
      EVIDENCIA: `grep -n "or o.responsavel" backend/app/services/gerador.py` volta
      vazio (exit 1). Bloco 1 da `prova_responsavel_so_da_matriz.py`: `OK a empresa
      SEM responsavel no setor NAO herda o da obrigacao (([], None))`. REPROVA com o
      fallback de volta, verificado: falham 3 casos
      MOTIVO: pedido do usuario, 2026-09-09. Obrigacao serve varias empresas, entao
      dono de tarefa nao mora nela
      PROVA: `grep -n "or o.responsavel" backend/app/services/gerador.py` volta vazio
- [x] o select de responsavel sai do cadastro da obrigacao
      EVIDENCIA: `grep -n "form.responsavel_id" frontend/src/pages/Obrigacoes.jsx`
      volta vazio (exit 1). O campo saiu do formulario, do estado e do payload. Um
      comentario no lugar dele diz por que, para ninguem recolocar
- [x] a coluna `obrigacoes.responsavel_id` FICA no banco, com comentario de legado
      EVIDENCIA: `models.py:359-363`, com o comentario dizendo que NADA mais le o
      campo. E o cuidado que quase passou: o payload da tela parou de MANDAR o
      campo, em vez de mandar `null`. O servidor grava o que vier
      (`model_dump(exclude_unset=True)`), entao um `null` apagaria o valor legado de
      toda obrigacao que alguem editasse. Caso na `prova_payload_obrigacao.js`
- [x] `pages/Tarefas.jsx:338` para de puxar responsavel da obrigacao, e passa a puxar
      da matriz da empresa quando ela ja estiver escolhida
      EVIDENCIA: `Tarefas.jsx:331-355`. Com a empresa escolhida, chama o mesmo
      `getResponsaveisSetor` que a tela de Empresas usa e preenche a lista; sem
      empresa, deixa o campo como estava para a pessoa escolher na mao. Falha na
      consulta nao trava o cadastro. A legenda do campo foi reescrita: dizia que
      puxava responsaveis da obrigacao
- [x] `services/substituicao.py:58` para de trocar responsavel em obrigacao
      EVIDENCIA: bloco 5 da prova: `OK o responsavel legado da obrigacao fica onde
      estava` e `OK a substituicao nao conta obrigacao trocada por responsavel`. O
      supervisor padrao da obrigacao CONTINUA sendo substituido, porque ele e da
      obrigacao mesmo
- [x] a resposta da geracao diz quantas tarefas nasceram sem responsavel, e de quais
      empresas
      EVIDENCIA: bloco 2 da prova: `sem_responsavel: 2` e
      `empresas_sem_responsavel: [Beta, Gama]`. O bloco 3 prova o contrario, com a
      matriz completa: contador zero e lista VAZIA, e nao ausente
      MOTIVO: sem isso, tirar o fallback ESCONDE o buraco de cadastro em vez de
      revelar. Era o fallback que mascarava empresa sem responsavel no setor
      PROVA: caso na prova conferindo o contador na resposta
- [x] `prova_responsavel_so_da_matriz.py` criada, e verificado que REPROVA com o
      fallback de volta
      EVIDENCIA: com o fallback recolocado, a saida traz `FALHA a empresa SEM
      responsavel no setor NAO herda o da obrigacao ((Padrao da Obrigacao, 1))`,
      `FALHA o contador bate com as duas empresas sem cadastro (0)` e `FALHA e
      nomeia as empresas`. 22 de 22 provas do backend rc=0 depois de restaurar

## Fase 14: e-validador em obrigacao interna

- [ ] `models.py:305` passa a deixar a flag EXPLICITA vencer o sentido interna
      MOTIVO: pedido do usuario, 2026-09-09. REVERSAO declarada de uma decisao escrita
      no codigo com o motivo "exigir um travaria a baixa por algo que nunca vai
      existir". A premissa era que interna nao tem documento; tem, so que quem anexa e
      o analista, nao o cliente
- [ ] `exige_documento = NULL` continua derivando de `identificadores`, e interna sem
      flag continua sem documento
      MOTIVO: nenhuma obrigacao interna de hoje pode mudar de comportamento sozinha
      PROVA: caso na prova com interna sem flag
- [ ] a tela da obrigacao libera o campo de documento quando o sentido e interna
- [ ] o comentario de `models.py:302-306` reescrito com a regra nova e o porque
      MOTIVO: comentario que contradiz o codigo e pior que comentario nenhum
- [ ] `prova_evalidador_interna.py` com tres casos (interna sem flag, interna com flag,
      nao interna)
- [ ] `prova_sentido_obrigacao.py` e `prova_tipo_documento.py` seguem passando

## Fase 15: desconsiderar a tarefa e virar excecao

- [ ] tabela de excecao por (obrigacao, empresa), SEPARADA de `obrigacao_empresa`
      MOTIVO: `obrigacao_empresa` alimenta o relationship `Obrigacao.empresas`, que
      significa inclusao. Coluna "excluida" ali faria o mesmo relationship devolver
      inclusao e exclusao misturadas
      PROVA: `grep -n "excecao" backend/app/init_db.py` acha o DDL
- [ ] `empresas_alvo()` subtrai as excecoes nos DOIS modos, `regra` e `vinculadas`
      PROIBIDO: subtrair so no modo `regra`, deixando a excecao furada no outro
      PROVA: a prova cobre os dois modos
- [ ] a tarefa ganha a acao "nao se aplica a esta empresa", pedindo motivo
- [ ] a acao grava quem decidiu, quando e o motivo, e leva a tarefa para `CANCELADA`
      MOTIVO: `CANCELADA` ja existe, ja tem lixeira e ja e ignorada pelo e-validador
      (`routes/tarefas.py:392`). Status novo exigiria `ALTER TYPE` no enum nativo do
      Postgres, risco sem ganho (Escada, degrau 2)
- [ ] a tela mostra "nao se aplica" no lugar de "cancelada" quando for esse o caso
- [ ] no cadastro da obrigacao, a lista de excecoes com motivo e botao de remover
      MOTIVO: sem a volta, um clique errado prende a empresa fora da obrigacao para
      sempre
      PROVA: caso na prova removendo a excecao e vendo a empresa voltar a geracao
- [ ] `log_event` na criacao e na remocao da excecao
      MOTIVO: "mutacao de dado critico SEMPRE entra" (Padrao_Logging_Estruturado)
- [ ] tarefa desconsiderada nao conta como pendente nem atrasada
      PROVA: caso na prova conferindo os contadores do painel
- [ ] `prova_excecao_obrigacao.py` criada

## Fase 16: o check "Aplicar a todas as empresas"

- [ ] vincular empresa desmarca o check e poe `alvo_modo='vinculadas'`
      MOTIVO: hoje o check e derivado de `!aplica_regimes && !aplica_segmentos`
      (`Obrigacoes.jsx:694`) e fica MARCADO mesmo com empresas vinculadas, dizendo o
      contrario do que a tela faz
- [ ] desvincular a ultima empresa devolve o estado anterior
      MOTIVO: obrigacao presa em `vinculadas` com lista vazia nao gera para ninguem
      PROVA: caso na prova
- [ ] desmarcar o check para de FORCAR um regime (`Obrigacoes.jsx:707`)
- [ ] o aviso ambar que ja existe passa a explicar o que aconteceu
- [ ] a logica sai do JSX para `pages/alvoObrigacao.js`, com
      `frontend/provas/prova_alvo_check.js` em Node puro
- [ ] `prova_alvo_vinculadas.py` segue passando

## Fase 17: entrega

- [ ] `CONFORMIDADE_VAULT.md` sem nenhuma linha pendente
- [ ] `grep -rn "escada:" .` registrado no LOG, com o gatilho de cada marcador
- [ ] `graphify update .` rodado
- [ ] `OBRIGACOES_SPEC.md` e `CLAUDE.md` do projeto atualizados
- [ ] carimbo de producao conferido contra o HEAD do repositorio
      PROVA: `curl -s https://gestordetarefas.zoaria.com.br/api/health` comparado com
      `git log -1 --date=format:'%Y%m%d-%H%M'`
