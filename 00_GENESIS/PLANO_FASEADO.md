# PLANO FASEADO

Trabalho: **varios responsaveis por (empresa, setor)**.
Aberto em 2026-09-09. Numeracao segue as fases 0 a 7 do SSO, fechadas em 2026-08-17.

modo=autonomo (escolhido pelo usuario em 2026-09-09)

## O que muda, em uma frase

Hoje cada par (empresa, setor) tem UM responsavel, e a tarefa gerada nasce com ele.
Passa a ter N, e a tarefa nasce com todos, numa tarefa so.

## Decisoes que ja estao fechadas (nao reabrir sem o usuario)

1. Uma tarefa por competencia com N responsaveis, nunca uma por pessoa.
2. Na tela, checkbox por pessoa dentro de um popover com busca, chips na linha.
3. Sem efeito retroativo: tarefa ja gerada nao muda.
4. Planilha aceita varios nomes separados por ponto e virgula.
5. Supervisor sai do primeiro da lista, mantendo a escada atual.

---

## Fase 8: aprovacao do plano

- status: **done** (aprovado pelo usuario em 2026-09-09, sem ajustes)
- duracao: o tempo de o usuario ler
- criterio de aceite: o usuario escreve que aprova, e a linha entra no LOG
- output: este arquivo aprovado

## Fase 9: modelo e API

- status: **done** (2026-09-09; 19 provas rc=0, matriz com as 5 linhas fechadas)
- depende de: Fase 8
- duracao estimada: 2h
- notas que regem: `Padrao_IDOR`, `Padrao_Mass_Assignment`, `Padrao_Validacao_de_Input`,
  `Padrao_Logging_Estruturado`
- o que entra:
  - tabela associativa nova ligando o vinculo (empresa, setor) a N usuarios, criada
    pelo `init_db.migrate()`, que e onde coluna e indice entram neste projeto (nao ha
    migration de Alembic no repositorio)
  - `responsavel_id` continua existindo como PRINCIPAL, e passa a ser sempre o
    primeiro da lista, gravado num unico ponto
  - GET `/empresas/{id}/responsaveis-setor` passa a devolver `responsavel_ids`
  - PUT passa a aceitar `responsavel_ids`, com validacao que hoje nao existe:
    setor existe e esta ativo, cada usuario existe, nao e do tipo cliente e nao esta
    bloqueado, ids repetidos colapsam, lista com teto de tamanho
  - `extra="forbid"` no schema do body
  - `log_event` na regravacao da matriz, usando o que ja existe em `seguranca.py:57`
- criterio de aceite: `backend/provas/prova_responsaveis_multiplos.py` passa, e
  reprova se a validacao for removida. As 18 provas antigas seguem passando.
- output: `models.py`, `init_db.py`, `routes/empresas.py`, a prova nova

## Fase 10: gerador de tarefas

- status: **done** (2026-09-09; 20 provas rc=0, e a prova reprova sem o fix)
- depende de: Fase 9
- duracao estimada: 1h30
- o que entra:
  - `_resp_do_setor` devolve LISTA, e o gerador escreve `nova.responsaveis` com todos
  - supervisor sai do primeiro, mantendo a escada (gestor da pessoa, gestor do setor,
    supervisor padrao da obrigacao)
  - correcao de bug adjacente: `routes/tarefas.py:37` esconde a tarefa quando o
    responsavel PRINCIPAL esta bloqueado. Com dois responsaveis, bloquear um faria a
    tarefa sumir mesmo havendo outro ativo. A tarefa so some quando TODOS estiverem
    bloqueados.
  - varredura dos outros consumidores de responsavel unico (alertas, WhatsApp,
    e-mail, documentos), corrigindo o que passa a estar errado com N
- criterio de aceite: `backend/provas/prova_gerador_multiplos.py` passa, com o cenario
  de dois responsaveis num setor gerando UMA tarefa com os dois, e com o caso de um
  deles bloqueado sem sumir a tarefa. `prova_gestor_setor.py` e `prova_marco_fechamento.py`
  seguem passando.
- output: `services/gerador.py`, `routes/tarefas.py`, a prova nova

## Fase 11: tela

- status: **done** (2026-09-09; 18 casos na prova, build ok, conferencia visual feita)
- depende de: Fase 9
- duracao estimada: 2h30
- notas que regem: `Padrao_Selecao_em_Lote`, `Padrao_Toggle_OnOff`, `Padrao_Tabela`,
  `Padrao_Modal_Popup_Centrado`, `Padrao_Modal_Nao_Fecha_Sozinho`, `Sistema_de_Estilos`
- o que entra:
  - extrair o seletor de responsaveis que JA existe em `pages/Tarefas.jsx:1287` para
    `components/SeletorResponsaveis.jsx`, com duas apresentacoes: inline (como esta
    hoje na tela de Tarefas) e popover (na linha do setor). Mesma logica, mesma
    marcacao. A tela de Tarefas passa a usar o componente extraido, sem mudar de cara.
  - na aba, cada setor mostra os escolhidos como chips e um botao que abre o popover
    com busca
  - o popover fecha no ESC e no clique fora SEM fechar o modal de cadastro
  - a logica de marcar, desmarcar e filtrar sai do JSX para
    `pages/seletorResponsaveis.js`, pelo mesmo motivo de `contexts/bilhete.js`:
    roda em prova Node pura
- criterio de aceite: `frontend/provas/prova_seletor_responsaveis.js` passa;
  `npm run build` sem erro; a matriz de conformidade fecha as linhas desta fase com
  saida real de comando colada
- output: `components/SeletorResponsaveis.jsx`, `pages/seletorResponsaveis.js`,
  `pages/Empresas.jsx`, `pages/Tarefas.jsx`, a prova nova

## Fase 12: importador de planilha

- status: **done** (2026-09-09; 21 provas rc=0, e a prova reprova sem o separador)
- depende de: Fase 9
- duracao estimada: 1h
- o que entra:
  - celula com varios nomes separados por ponto e virgula
  - nome nao encontrado vira aviso na linha, sem derrubar a importacao, como ja e hoje
  - o modelo XLSX baixavel ganha a instrucao do ponto e virgula
- criterio de aceite: `backend/provas/prova_importar_resp_multiplos.py` passa, com o
  caso de celula com dois nomes, com nome desconhecido no meio, e com celula vazia
  desmarcando o setor
- output: `services/importador_resp_setor.py`, `routes/empresas.py`, a prova nova

## Fase 13: o responsavel sai da obrigacao

- status: **done** (2026-09-09; 22 provas rc=0, e a prova reprova com o fallback de volta)
- depende de: Fase 10
- duracao estimada: 1h30
- pedido do usuario em 2026-09-09: "nao podemos vincular a obrigacao a um usuario,
  pois ela pode ser utilizada por varios outros"
- o que entra:
  - o gerador para de usar `o.responsavel` como fallback (`services/gerador.py:305`).
    Quem atende sai SO da matriz da empresa
  - o select de responsavel sai do cadastro da obrigacao (`pages/Obrigacoes.jsx:525`)
  - a coluna `obrigacoes.responsavel_id` FICA no banco, marcada como legado no
    modelo. Apagar coluna e destrutivo e nao traz ganho nenhum aqui
  - `pages/Tarefas.jsx:338` para de puxar o responsavel da obrigacao ao escolher uma;
    passa a puxar da matriz da empresa, quando a empresa ja estiver escolhida
  - `services/substituicao.py:58` para de trocar responsavel em obrigacao, que passa
    a nao ter um
  - a resposta da geracao informa QUANTAS tarefas nasceram sem responsavel, e de que
    empresas. Sem isso, tirar o fallback esconde o buraco de cadastro em vez de
    revelar: hoje a empresa sem responsavel no setor herda o da obrigacao e ninguem ve
- criterio de aceite: `prova_responsavel_so_da_matriz.py` passa, com o caso de empresa
  sem responsavel no setor gerando tarefa SEM dono e o contador saindo na resposta.
  `prova_gestor_setor.py` e `prova_marco_fechamento.py` seguem passando.
- output: `services/gerador.py`, `services/substituicao.py`, `pages/Obrigacoes.jsx`,
  `pages/Tarefas.jsx`, a prova nova

## Fase 14: e-validador em obrigacao interna

- status: **done** (2026-09-09; 23 provas rc=0)
- depende de: Fase 8
- duracao estimada: 45min
- pedido do usuario em 2026-09-09: "dentro da obrigacao, daqueles que sao internas
  precisam ter a opcao de baixar pelo e-validador tbm"
- REVERSAO DECLARADA: `models.py:302-306` hoje devolve False para `sentido=interna`
  MESMO com a flag ligada, com o motivo escrito de que "exigir um travaria a baixa por
  algo que nunca vai existir". A premissa era que interna nao tem documento; na pratica
  tem, so que quem anexa e o proprio analista, nao o cliente.
- o que entra:
  - a flag EXPLICITA vence o sentido: `exige_documento=True` vale mesmo em interna.
    `NULL` continua derivando de `identificadores`, e interna sem flag continua sem
    documento, entao nenhuma obrigacao interna de hoje muda de comportamento
  - a tela da obrigacao libera o campo de documento quando o sentido e interna
  - o comentario de `models.py` e reescrito para dizer a regra nova e por que mudou
- criterio de aceite: `prova_evalidador_interna.py` passa, com tres casos: interna sem
  flag (sem documento, como hoje), interna com flag (com documento), e nao interna
  (inalterada). `prova_sentido_obrigacao.py` e `prova_tipo_documento.py` seguem passando.
- output: `models.py`, `pages/Obrigacoes.jsx`, a prova nova

## Fase 15: desconsiderar a tarefa e virar excecao da obrigacao

- status: pending
- depende de: Fase 8
- duracao estimada: 2h
- pedido do usuario em 2026-09-09: "caso uma obrigacao/tarefa seja gerada para uma
  empresa, devido a regra, e preciso criar uma opcao dentro dela para desconsiderar,
  e assim atualiza a regra dentro do cadastro da obrigacao para nao gerar mais"
- o que entra:
  - tabela de EXCECAO por (obrigacao, empresa), separada da `obrigacao_empresa` que ja
    existe. Motivo de nao reusar a mesma tabela: ela alimenta o relationship
    `Obrigacao.empresas`, que significa inclusao; uma coluna "excluida" ali faria o
    mesmo relationship devolver inclusao e exclusao misturadas
  - `empresas_alvo()` (`services/gerador.py:208`) subtrai as excecoes nos DOIS modos,
    regra e vinculadas
  - a tarefa ganha a acao "nao se aplica a esta empresa", que pede motivo, grava quem
    decidiu e quando, e leva a tarefa para `CANCELADA`
  - reuso de `CANCELADA` em vez de status novo: ela ja existe, ja tem fluxo de lixeira
    e ja e ignorada pelo e-validador (`routes/tarefas.py:392`). Status novo exigiria
    `ALTER TYPE` no enum nativo do Postgres, que e risco sem ganho. A marca de "nao se
    aplica" e um campo proprio, e a tela mostra esse rotulo em vez de "cancelada"
  - no cadastro da obrigacao, a lista de excecoes com o motivo, e o botao de remover.
    Sem a volta, um clique errado prende a empresa fora da obrigacao para sempre
  - `log_event` na criacao e na remocao da excecao
- criterio de aceite: `prova_excecao_obrigacao.py` passa, com: desconsiderar tira a
  empresa da geracao seguinte nos dois modos de alvo, remover a excecao faz a empresa
  voltar, e a tarefa desconsiderada nao conta como pendente nem atrasada
- output: `models.py`, `init_db.py`, `services/gerador.py`, `routes/tarefas.py`,
  `routes/obrigacoes.py`, `pages/Tarefas.jsx`, `pages/Obrigacoes.jsx`, a prova nova

## Fase 16: o check "Aplicar a todas as empresas"

- status: pending
- depende de: Fase 15
- duracao estimada: 1h
- pedido do usuario em 2026-09-09: "na obrigacao que pode ser aplicada para algumas
  empresas, o check de aplicar em todas precisa ser desflegado"
- o buraco de hoje, medido: o check e derivado de `!aplica_regimes && !aplica_segmentos`
  (`pages/Obrigacoes.jsx:694`), entao ele fica MARCADO mesmo com empresas vinculadas,
  dizendo o contrario do que a tela faz. E desmarcar forca um regime
  (`pages/Obrigacoes.jsx:707`), entao nao existe caminho por ali para "so estas
  empresas": isso mora no `alvo_modo`, que a tela quase nao mostra.
- o que entra:
  - vincular empresa na lista desmarca o check e poe `alvo_modo='vinculadas'`
  - desvincular a ultima empresa devolve o estado anterior, sem deixar a obrigacao
    presa em "vinculadas" com lista vazia, que nao geraria para ninguem
  - o aviso ambar que ja existe passa a explicar o que aconteceu
- criterio de aceite: `frontend/provas/prova_alvo_check.js` passa, com: vincular
  desmarca e troca o modo, desvincular a ultima volta atras, e o estado que vai para a
  API bate com o que a tela mostra. `prova_alvo_vinculadas.py` segue passando.
- output: `pages/Obrigacoes.jsx`, `pages/alvoObrigacao.js`, a prova nova

## Fase 17: entrega e validacao

- status: pending
- depende de: 10, 11, 12, 13, 14, 15, 16
- duracao estimada: 40min
- o que entra:
  - `CONFORMIDADE_VAULT.md` sem linha pendente
  - inventario da escada: `grep -rn "escada:" .` registrado no LOG
  - `graphify update .` para o mapa nao envelhecer
  - `OBRIGACOES_SPEC.md` e `CLAUDE.md` do projeto atualizados no que mudou
  - deploy pelo push, e conferencia do carimbo contra o HEAD:
    `curl -s https://gestordetarefas.zoaria.com.br/api/health` comparado com
    `git log -1 --date=format:'%Y%m%d-%H%M'`
- criterio de aceite: a aba salva dois responsaveis, o mes gerado traz UMA tarefa com
  os dois nomes, e o carimbo de producao bate com o HEAD
- output: producao no ar com a funcionalidade

---

## Historico de alteracao do plano

- **2026-09-09**: plano ampliado ANTES da aprovacao, a pedido do usuario, com quatro
  frentes novas (fases 14 a 17). A fase de entrega virou 18. A frente 13 revoga uma
  decisao do plano original: o responsavel deixa de ter fallback na obrigacao.

## Fora de escopo (cortado pela escada)

- **Componente de multi selecao novo do zero**: cortado no degrau 2. Ja existe em
  `pages/Tarefas.jsx:1287`, e vai ser extraido em vez de reescrito. Volta a ser
  construcao nova so se a extracao mostrar que as duas telas precisam de logica
  incompativel.
- **Trocar lucide-react por Phosphor**: cortado. A vault manda "Phosphor unico", mas
  a troca atinge as 17 telas e nao tem relacao com responsavel multiplo. Volta quando
  houver uma fase de padronizacao visual do app inteiro.
- **Aplicar o responsavel novo nas tarefas ja geradas**: cortado por decisao do
  usuario em 2026-09-09. Volta se ele pedir o botao "aplicar as pendentes".
- **Paginacao da listagem de tarefas**: continua fora, como ja estava desde
  2026-08-20. Volta se o payload pesar.
- **Tela de parametros de seguranca** (teto da lista configuravel): cortado. O teto
  fica constante no codigo, como `MAX_TENTATIVAS` ja e. Volta se o escritorio crescer
  a ponto de o teto atrapalhar.
- **Trilha de auditoria com tela**: cortado. `log_event` grava; nao ha tela para ler,
  e criar uma e outro trabalho.
