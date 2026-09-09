# LOG

Projeto fechado em 2026-08-17: SSO do Hub Zoaria no Tareffas, 8 fases (0 a 7) em
done, validado em producao. O historico completo (LASTRO, NOTAS_LIDAS,
PLANO_FASEADO, CHECKLIST_APLICACAO, o LOG integral e a matriz) esta em
`checkpoint 20260817 152106.zip`, nesta mesma pasta. O CONFORMIDADE_VAULT.md
segue aberto aqui de proposito: e a prova de que a entrega obedeceu o padrao.

---

## 2026-08-20 — correcao pos-fechamento: entrada pelo Hub pedindo senha

Sintoma relatado: "algumas vezes, acessando pelo hub esta pedindo senha".
Nao era intermitente. Era diario, para quem usa o sistema todo dia.

Causa, em `frontend/src/contexts/AuthContext.jsx`: a abertura olhava o token do
localStorage ANTES do bilhete e, havendo token, descartava o bilhete. Com JWT de
8 horas (`backend/app/auth.py:15`), o token vence de um dia para o outro. Quem
clicava no card do Hub na manha seguinte tinha o bilhete valido jogado fora, o
`/me` respondia 401, o token era apagado e a pessoa caia na tela de senha.

O SSO em si estava correto nas duas pontas: o Hub gera o bilhete no clique
(`/ir/<app_id>`, nao no render do card), e a leitura de 60s com uso unico
funciona. Nada mudou em `sso.py` de nenhum dos lados.

Correcao: a decisao de entrada saiu do JSX para `frontend/src/contexts/entrada.js`
(mesmo motivo de `bilhete.js`: prova em Node puro). O bilhete passa a vencer a
sessao guardada, e o token anterior volta como RESERVA -- bilhete recusado nao
custa a sessao de quem ja estava dentro.

Decisao do usuario nesta rodada: bilhete de OUTRA pessoa troca a conta, em vez de
ser ignorado. Em maquina compartilhada, quem clicava no card entrava como a
pessoa anterior sem perceber.

Provas: `frontend/provas/prova_entrada_sso.js` (7 casos, Node puro). As provas
anteriores seguem passando: `prova_sso_f4.js` (7 casos) e `backend/app/sso.py`.
Build do frontend refeito sem erro.

---

## 2026-08-20 — consultas lentas: N+1 na listagem, laco no painel, zero indices

Sintoma: "as consultas estao lentas".

Medido antes de mexer, contando idas ao banco (nao tempo, que varia com a
maquina): listagem de 500 tarefas = **503 consultas**. Uma por tarefa.

Causa 1 — N+1 na serializacao. `TarefaResponse` expoe `responsaveis` e
`supervisor`, e a query so trazia `joinedload(Tarefa.obrigacao)`. O Pydantic
buscava cada um no banco na hora de serializar. Em SQLite local custava 78 ms e
passava despercebido; contra o Postgres do servidor cada consulta e um
ida-e-volta de rede, e a tela levava segundos. Corrigido com `selectinload` nos
responsaveis (colecao — joinedload multiplicaria as linhas) e `joinedload` no
supervisor. **503 -> 2 consultas, constante em qualquer volume.**

Causa 2 — laco no painel. `stats-por-setor` percorria os setores fazendo cinco
`count()` em cada um, mais a montagem do escopo. Virou um `GROUP BY` com
contagem condicional. **~40 -> 1 consulta.**

Causa 3 — `tarefas`, a tabela grande, nao tinha indice em NENHUMA chave
estrangeira, nem em status/data_prazo/competencia. Toda listagem filtrada
varria a tabela. `Base.metadata.create_all` so cria tabela nova, entao marcar
`index=True` no model nao alcanca base existente: os indices entram por
`init_db.criar_indices()`, no mesmo mecanismo idempotente das colunas, chamado
no boot. Onze indices, incluindo `(status, data_prazo)` — que andam sempre
juntos na conta de atrasadas — e `tarefa_responsaveis(usuario_id)`, porque a PK
comeca por `tarefa_id` e o escopo busca por usuario.

Prova: `backend/provas/prova_consultas_rapidas.py`. Ela mede CONSULTAS, nao
segundos, e trava o custo constante: se alguem acrescentar campo no
`TarefaResponse` sem o carregamento correspondente, o N+1 volta e a prova
quebra. As provas anteriores seguem passando (seguranca_f7: 19, sso_f3: 25).

Nao mexido de proposito: paginacao da listagem. Muda o contrato da API e o
front junto, e com 2 consultas constantes o problema imediato saiu.

---

## 2026-08-20 — competencia de referencia vira deslocamento em meses

Pergunta do usuario: SPED entregue ate o decimo dia do SEGUNDO mes subsequente
ao fato gerador — julho gera entrega em setembro. Isso era representavel?

Nao era. `competencia_ref` tinha quatro apelidos (mes_anterior, mesmo_mes,
mes_seguinte, ano_anterior) e nenhum diz "dois meses antes". Gerando as tarefas
de setembro com mes_anterior, a competencia saia 08/2026: a tarefa nascia um mes
adiantada. Como a competencia e a chave de baixa do e-validador, o comprovante
do SPED de julho nao casaria com a tarefa. Vale para toda a familia SPED —
EFD-Contribuicoes, DCTF — que vence no 2o mes subsequente.

Agora o campo e um deslocamento em meses, e os apelidos continuam aceitos
(e o que esta gravado nas obrigacoes ja cadastradas; converter dado em producao
para ganhar uniformidade seria trocar risco por estetica). A aritmetica passou a
ser em meses absolutos com divmod: atravessa virada de ano e deslocamento maior
que 12, coisa que o "soma e corrige depois" so fazia para um mes.

Achado no caminho: `regra_prazo_tipo` ja tinha `dia_util` (N-esimo dia util,
via `_nth_dia_util`) implementado no backend, mas nunca foi exposto na tela nem
documentado no spec. Era exatamente a regra que o SPED usa. Agora esta no select,
com o campo "qual dia util". Em set/2026 a diferenca e concreta: dia fixo 10 cai
em 10/09, o 10o dia util cai em 14/09.

Modelo confirmado ao usuario: a REGRA fica na obrigacao, as DATAS ficam em cada
tarefa (`competencia`, `data_vencimento` legal, `data_prazo` interno derivado do
vencimento por `lembrar_dias_antes`).

Provas: `backend/provas/prova_competencia_prazo.py`. As demais seguem passando
(consultas_rapidas, seguranca_f7 19, sso_f3 25). Build do frontend sem erro.

---

## 2026-08-20 — filtro por competencia e por vencimento na tela de Tarefas

Pedido: filtrar tarefas por competencia e por vencimento.

Entregue na barra de filtros: **Competencia** (select alimentado pelas
competencias que EXISTEM nas tarefas carregadas, mais uma entrada "sem
competencia" para as avulsas) e **faixa de vencimento** (vence de / ate), com
tres atalhos — Vencidas, Prox. 7 dias, Este mes. Somam-se aos filtros que ja
havia (empresa, setor, status), mais contador "N de M" e botao de limpar.

Padrao: o `Padrao_Barra_de_Filtros` da vault e escrito para o stack Flask com
CSS puro (classes `fu-bar`, `--fu-h`). Esta tela e React + Tailwind e ja tinha
barra propria. Aplicados os PRINCIPIOS do padrao — altura unica (h-38px em todo
elemento), label em cima do campo em 11px uppercase, um grupo por filtro,
presets de periodo, acao alinhada a direita — escritos em Tailwind. Copiar o CSS
literal criaria duas linguagens visuais na mesma tela.

Decisao: filtragem em memoria, como os filtros que ja existiam nesta tela. A
listagem ja vem inteira do backend e agora custa 2 consultas fixas, entao
filtrar no cliente responde na hora, sem ida ao servidor a cada tecla. Se o
volume crescer a ponto de o payload pesar, o caminho e paginacao no servidor —
anotado, nao feito.

Dois detalhes que a prova trava:
- vencimento chega como ISO COM HORA; a comparacao e so de data, senao tarefa
  que vence as 12:30 do proprio dia escolhido em "ate" ficaria de fora;
- tarefa SEM vencimento nao entra em faixa nenhuma, em vez de aparecer em todas
  como se fosse data zero.

A logica saiu do JSX para `frontend/src/pages/filtroTarefas.js`, pelo mesmo
motivo de `contexts/bilhete.js`: roda em prova Node pura.

Provas: `frontend/provas/prova_filtro_tarefas.js` (13 casos). Demais passando —
entrada_sso 7, sso_f4 7, e no backend competencia_prazo, consultas_rapidas,
seguranca_f7 19, sso_f3 25. Build sem erro.

---

## 2026-08-20 — prazo por empresa: marco de fechamento

Pergunta do usuario: mesma obrigacao, prazo diferente por empresa (balancete dia
15 na A, 5o dia util na B, dia 18 na C). E, mais que isso: as etapas que
antecedem o balancete precisam caber antes do prazo daquele cliente.

Preocupacoes que ele levantou, e que definiram o desenho:
1. "vou ter que verificar cada obrigacao?" — nao. O padrao continua sendo prazo
   legal proprio; marca-se so as etapas do fechamento, que sao poucas.
2. "dependencia trava o processo na implantacao?" — trava. Por isso ficou de
   fora: aqui so se CALCULA DATA, nada bloqueia conclusao fora de ordem.

Desenho: a EMPRESA ganha um marco (`fechamento_tipo` + `fechamento_dia`) e a
OBRIGACAO diz quantos dias antes dele vence (`ancora`, `ancora_dias_antes`,
`ancora_tipo_dias`). Cadastro = um por empresa + um por obrigacao, e nao o
produto dos dois. Muda o marco, a cadeia inteira daquele cliente desloca junto.

`calc_vencimento(o, empresa, mes, ano)` decide: ancorada e com marco -> sai do
marco; senao -> regra propria. O calculo do vencimento entrou no laco das
empresas no gerador, porque agora a mesma obrigacao tem data diferente em cada
uma. Empresa ancorada sem marco cai na regra propria: falta de cadastro nao
impede tarefa de nascer.

Telas: campo "Fechamento contabil" no cadastro da empresa; caixa "Esta obrigacao
e etapa do fechamento contabil" no cadastro da obrigacao, com dias antes e
uteis/corridos.

Provas: `backend/provas/prova_marco_fechamento.py`, com o cenario do usuario
(tres empresas, tres marcos) e a cadeia de tres etapas deslocando junto. Demais
passando. Spec atualizada (secao 1b).

[2026-09-03T13:20:00] fase=ajuste acao=fonte_dashboard resultado=ok obs="Dashboard.jsx: fonteDoCentro(centro,raio,largura) calcula a fonte do miolo da rosca a partir do vao real do anel, teto 26; antes era fontSize 28 fixo e 4 digitos encostavam no anel. Legenda da rosca da faixa: valor passou de w-5 para w-9, que era onde 6693 invadia o 35%. Build do frontend ok (vite, 2290 modules)."

[2026-09-03T13:45:00] fase=correcao acao=excluir_competencia_500 resultado=ok obs="500 ao excluir tarefas do mes era FOREIGN KEY: tarefa_envios e saida_acessos apontam para tarefas com FK NOT NULL e nao havia relationship declarada no modelo Tarefa, entao o ORM apagava so a tarefa. Causa raiz corrigida em models.py (envios/acessos com cascade all,delete-orphan), o que conserta junto o mesmo bug na lixeira de tarefa unica (tarefas.py:782). prova_excluir_tarefa.py ganhou PRAGMA foreign_keys=ON (sem ele o SQLite era mais permissivo que o Postgres de producao e a prova nao via o erro) e os casos 7 e 8. Verificado que a prova reprova sem o fix e passa com ele. 16 provas rc=0."

[2026-09-03T14:15:00] fase=correcao acao=arquivos_orfaos_no_volume resultado=ok obs="Exclusao deixava arquivo orfao em /app/data em dois lugares: a lixeira de tarefa unica apagava so o anexo_nome e deixava o saida_nome (a guia entregue ao cliente), e a exclusao por competencia nao apagava nada, entao apagar um mes inteiro deixava centenas. Helper up.remover_arquivos(nomes) em services/upload.py, usado pelos dois. Os nomes se leem antes do delete e os arquivos saem depois do commit, para commit recusado nao deixar tarefa sem arquivo. As respostas ganharam arquivos_removidos; anexo_removido continua significando so o comprovante. prova_excluir_tarefa.py casos 9 e 10; verificado que reprovam sem o fix. 16 provas rc=0, app.main importa."

[2026-09-03T14:40:00] fase=correcao acao=carimbo_mentia resultado=ok obs="O /api/health respondia 20260901-1155 havia tres dias enquanto tres deploys entravam, e quase demos o webhook como morto. Causa: versao.py lia o mtime do PROPRIO arquivo, e o EasyPanel faz checkout por cima do diretorio existente -- so arquivo alterado ganha mtime novo, entao commit que nao toca o versao.py congela o carimbo. Provado que o deploy tinha chegado comparando o hash do bundle (index-CYY6OxuH.js em producao == build local). Carimbo passa a sair do mtime mais recente de todo o pacote app/, ignorando __pycache__ (o .pyc nasce no import e carimbaria a hora do boot). prova_carimbo_build.py com 6 casos. 17 provas rc=0. CLAUDE.md item 7 corrigido: a conclusao 'qualquer deploy move o carimbo' era falsa. XmlHub e FinControl tem o mesmo defeito, verificado no codigo dos dois."

[2026-09-03T15:40:00] fase=feature acao=gerar_recorte_por_empresa resultado=ok obs="O botao 'Gerar tarefas do mes' ja recortava por OBRIGACAO e nao por EMPRESA: era o escritorio inteiro ou nada. gerar_tarefas() ganhou empresa_ids, aplicado como INTERSECAO sobre empresas_alvo(db,o) -- nunca soma, porque escolher a empresa no botao de gerar nao pode inscreve-la na obrigacao (isso seria porta lateral para burlar o alvo). Vazio/None = todas, igual ao recorte de obrigacao. A resposta ganhou empresas_no_recorte, porque zero criadas com recorte e ambiguo entre 'ja existiam' e 'a obrigacao nao pega essas'. Na tela: radio Todas/Somente as escolhidas + lista com busca, no mesmo idioma do seletor que ja existe no cadastro da obrigacao. TRAVA: 'somente as escolhidas' com lista vazia desabilita o botao, senao mandaria [] e o backend leria como 'todas' -- geraria tudo dizendo o contrario. prova_gerar_recorte_empresas.py com 8 cenarios. 18 provas rc=0, build do front ok. Spec atualizada."

---

## 2026-09-09, aberto o trabalho de varios responsaveis por (empresa, setor)

[2026-09-09T00:00:00] fase=8 acao=genesis_ampliacao_criado resultado=ok obs="modo AMPLIACAO detectado pela pasta (83 arquivos de codigo, 00_GENESIS fechado em 17/08). Graphify atualizado antes de planejar: 1336 nos, 2977 arestas, contra um mapa de 17/08 com 57 arquivos mudados depois. Varredura da vault em 5 batedores paralelos (sonnet): UI-dados, UI-estrutura, estilo, seguranca (16 notas de 02_Seguranca lidas), auth (7 notas). Ficha de seguranca conferida na fonte (Padrao_IDOR:120, 'IDOR via body'). Criados LASTRO, NOTAS_LIDAS, PLANO_FASEADO e CHECKLIST_APLICACAO; CONFORMIDADE_VAULT ganhou 15 linhas novas. 5 fases planejadas (9 a 13)."

[2026-09-09T00:00:00] fase=8 acao=perguntas_socraticas resultado=ok obs="5 perguntas em 2 rodadas, todas com opcoes objetivas. Respostas: (1) UMA tarefa por competencia com N responsaveis, nao uma por pessoa; (2) escolha por checkbox em popover com busca, chips na linha; (3) SEM efeito retroativo em tarefa ja gerada; (4) planilha aceita varios nomes separados por ponto e virgula; (5) supervisor sai do primeiro da lista, escada atual intacta."

[2026-09-09T00:00:00] fase=8 acao=escada_podou_o_plano resultado=ok obs="Degrau 2 achou o seletor de responsaveis JA PRONTO em pages/Tarefas.jsx:1287 (checkbox por pessoa, contador 'N selecionado(s)'). O plano deixou de construir componente novo e passou a extrair o existente para components/SeletorResponsaveis.jsx, servindo as duas telas. Degrau 5 achou log_event pronto em seguranca.py:57. Cortados por escada e registrados em 'Fora de escopo': componente do zero, troca de lucide por Phosphor, aplicacao retroativa, paginacao, tela de parametros de seguranca, trilha de auditoria com tela."

[2026-09-09T00:00:00] fase=8 acao=achados_do_codigo resultado=ok obs="Tres coisas que o plano incorporou e que nao estavam no pedido. (a) O PUT /empresas/{id}/responsaveis-setor grava setor_id e responsavel_id vindos do body SEM validar existencia nem elegibilidade (empresas.py:105); com N ids isso piora, e virou item da fase 9. (b) routes/tarefas.py:37 esconde a tarefa quando o responsavel PRINCIPAL esta bloqueado: com dois responsaveis, bloquear um faria a tarefa sumir tendo outro ativo; virou item da fase 10. (c) o filtro de escopo (tarefas.py:43) JA considera o M2M, entao 'minhas tarefas' nao precisa de mudanca nenhuma."

[2026-09-09T00:00:00] fase=8 acao=desvio_declarado_icones resultado=ok obs="Icones_Phosphor manda 'Phosphor unico'. O projeto usa lucide-react nas 17 telas desde a origem. Trocar a biblioteca inteira nao tem relacao com responsavel multiplo e atingiria o app todo: fica desvio declarado no LASTRO e linha na matriz, com o item novo usando lucide para nao criar a segunda linguagem de icone que a nota combate."

[2026-09-09T00:00:00] fase=8 acao=vault_sem_regra resultado=ok obs="Buscado e NAO encontrado na vault, declarado em vez de inventado: limite de tamanho de lista em payload JSON (so ha limite de upload de arquivo), regra sobre delete-e-reinsere versus diff, regra sobre campo principal redundante ao lado de N-N, e regra sobre escopo 'proprias' com varios donos. As decisoes correspondentes sao locais e estao no LASTRO. A pasta 70_ESTILO nao existe nesta vault: o indice _MAPA_ESTILO.md tem os titulos mascarados e o conteudo e voz de ensino, nao copy de interface."

[2026-09-09T00:00:00] fase=8 acao=escopo_ampliado_antes_da_aprovacao resultado=ok obs="O usuario trouxe quatro frentes novas na mesma conversa, antes de aprovar o plano. Viraram as fases 13 a 16, e a entrega virou 17. (1) O responsavel padrao SAI da obrigacao: ela serve varias empresas, entao quem atende passa a vir so da matriz da empresa. Isso REVOGA a suposicao do plano original, que mantinha o fallback de gerador.py:305. (2) Obrigacao interna passa a poder exigir documento e baixar pelo e-validador. (3) Acao de desconsiderar a tarefa, que vira excecao permanente daquela empresa na obrigacao. (4) O check 'Aplicar a todas as empresas' passa a desmarcar sozinho quando ha empresa vinculada."

[2026-09-09T00:00:00] fase=8 acao=reversao_declarada_evalidador_interna resultado=ok obs="models.py:302-306 devolve exige_documento=False para sentido=interna MESMO com a flag ligada, e o comentario diz o motivo: 'exigir um travaria a baixa por algo que nunca vai existir'. O usuario mandou tirar a trava, e a premissa dela estava incompleta: interna tem documento sim, so que quem anexa e o analista, nao o cliente. A fase 14 faz a flag EXPLICITA vencer o sentido, e NULL continua derivando de identificadores, entao nenhuma obrigacao interna de hoje muda sozinha. O comentario do codigo sera reescrito junto, porque comentario que contradiz o codigo e pior que comentario nenhum."

[2026-09-09T00:00:00] fase=8 acao=achado_check_aplicar_todas resultado=ok obs="Medido o motivo do incomodo do usuario, e nao era so o check. Em Obrigacoes.jsx:694 o 'Aplicar a todas as empresas' e DERIVADO de !aplica_regimes && !aplica_segmentos, entao fica marcado mesmo com empresas vinculadas, afirmando o contrario do que a tela faz. E em :707 desmarcar FORCA o primeiro regime, entao nao existe caminho por ali para 'so estas empresas': isso mora no alvo_modo, que a tela quase nao expoe. A fase 16 liga as duas coisas: vincular empresa desmarca e troca o modo, e desvincular a ultima volta atras, para a obrigacao nao ficar presa em vinculadas com lista vazia, que nao geraria para ninguem."

[2026-09-09T00:00:00] fase=8 acao=escada_na_frente_nova resultado=ok obs="Duas podas nas fases novas. (a) 'Nao se aplica' reusa o status CANCELADA, que ja existe, ja tem lixeira e ja e ignorado pelo e-validador (routes/tarefas.py:392), com um campo proprio marcando o motivo. Status novo exigiria ALTER TYPE no enum nativo do Postgres, que e risco sem ganho. (b) A excecao ganha tabela propria em vez de uma coluna 'excluida' na obrigacao_empresa: aquela tabela alimenta o relationship Obrigacao.empresas, que significa inclusao, e misturar os dois sentidos no mesmo relationship quebraria empresas_alvo() de um jeito silencioso."

[2026-09-09T00:00:00] fase=8 acao=decisoes_do_usuario_rodada_2 resultado=ok obs="Tres perguntas, todas com opcoes objetivas. (1) Obrigacao SEM setor: a tarefa nasce sem dono e a geracao avisa quantas ficaram assim; o campo sai da tela de vez, em vez de sobreviver so para esse caso. (2) Desconsiderar MARCA a tarefa como 'nao se aplica' e ela sai das pendencias, ficando no historico com motivo e autor, em vez de ser apagada. (3) Vincular empresa desmarca o check sozinho."

[2026-09-09T00:00:00] fase=8 acao=plano_aprovado resultado=ok obs="Aprovado pelo usuario sem ajustes, com as 9 fases de trabalho (9 a 17). Fase 8 fechada. A execucao comeca pela fase 9 (modelo e API), em conversa nova."

[2026-09-09T10:05:00] fase=9 acao=modo_escolhido resultado=ok obs="modo=autonomo. Toco as fases 9 a 17 sem pedir confirmacao de rotina, com uma linha no LOG ao fechar cada fase. Escopo novo, criterio impossivel, falta de credencial e conflito com a vault continuam parando e perguntando."

[2026-09-09T10:40:00] fase=9 acao=modelo_e_rota resultado=ok obs="Tabela associativa empresa_setor_resp_usuarios (vinculo_id, usuario_id, ordem) em models.py:41-49, com ondelete=CASCADE nas duas pontas. A LISTA INTEIRA mora nela, inclusive o principal: responsavel_id passa a ser derivado, sempre o primeiro. Indice ix_resp_setor_usuario em init_db.py:181, pelo mesmo motivo do ix_tarefa_resp_usuario de 20/08 (a PK comeca pelo outro lado). A tabela NAO ganhou DDL no migrate(): create_all cria tabela nova, inclusive em base existente, e o motivo escrito no CHECKLIST na abertura estava errado. Corrigido la, com a prova em banco vazio (sqlite_master mostra a tabela e o indice)."

[2026-09-09T10:45:00] fase=9 acao=ponto_unico_de_gravacao resultado=ok obs="A funcao que grava saiu da rota para services/resp_setor.py:gravar, porque o importador de planilha (importador_resp_setor.py:103) era um SEGUNDO lugar escrevendo responsavel_id, e a regra 3 do LASTRO promete um so. Correcao na causa raiz, como manda a Escada: os dois chamadores passam pelo mesmo ponto agora (empresas.py:203 e importador_resp_setor.py:107), o importador ainda com um id so. A fase 12 so troca o que le a celula."

[2026-09-09T10:50:00] fase=9 acao=validacao_do_body resultado=ok obs="O PUT gravava setor_id e responsavel_id direto do corpo. Agora valida ANTES de qualquer gravacao (empresas.py:164-183, contra o primeiro delete em :185): setor existe e esta ativo, setor nao repetido, cada usuario existe, nao e tipo cliente, nao esta bloqueado e nao esta inativo. Elegibilidade avaliada em PYTHON de proposito: tipo, bloqueado e ativo sao NULL em conta antiga, e comparacao com NULL no SQL some com a linha em vez de recusa-la. Teto de 20 ids e extra=forbid no Pydantic, antes da rota. Recusa e 404 com mensagem unica. log_event na regravacao."

[2026-09-09T10:55:00] fase=9 acao=prova_criada resultado=ok obs="backend/provas/prova_responsaveis_multiplos.py, 19 casos, contra as rotas reais em SQLite temporario com PRAGMA foreign_keys=ON (sem ele o banco da prova e mais permissivo que o Postgres e a linha orfa passa). REPROVA sem a validacao, verificado: retirando empresas.py:164-183 a saida vira 'HOUVE FALHA nos itens [6, 7, 8, 9, 11]'; com o bloco de volta, 'TODAS AS PROVAS PASSARAM'. 19 de 19 provas do backend rc=0."

[2026-09-09T11:05:00] fase=9 acao=verificacao_adversarial resultado=ok obs="Tres verificadores em paralelo (sonnet, contexto limpo, sem a minha justificativa): conformidade com as 4 notas de seguranca, evidencia do checklist, e corretude funcional. SEIS achados, cinco corrigidos. (1) O GET da matriz pedia so get_current_user: usuario tipo=cliente de outra empresa lia a matriz de qualquer empresa. Virou require_perm('empresas','ver') em empresas.py:122; so pages/Empresas.jsx consome, e para abrir aquela tela ja e preciso a permissao, entao nao ha regressao. (2) A importacao por planilha regravava a MESMA matriz sem log nenhum: log_event acrescentado em :115. (3) O comentario de models.py apontava para uma funcao que a extracao tinha movido, e comentario que mente e pior que comentario nenhum: corrigido. (4) Excluir usuario nao contava a matriz de setor, entao quem respondia por um setor era APAGADO e a matriz ficava apontando para id inexistente; pior com varios, porque o secundario nem aparece em responsavel_id. Causa raiz em routes/usuarios.py:_usuario_em_uso, que passou a contar os dois papeis. (5) Apagar a EMPRESA deixava linha penderada na associativa: o cascade do ORM chega ao vinculo mas nao carrega as linhas do meio. Fechado no BANCO com ondelete=CASCADE, que vale tambem para DELETE em massa. (6) O item 10 da prova era tautologia: a rota nao usa 403 em lugar nenhum, entao o teste passaria com a validacao inteira removida. Reescrito para exigir status exatamente 404 E mensagem unica entre 'nao existe', 'e cliente' e 'esta bloqueado'. Casos 17, 18 e 19 acrescentados para os achados 4 e 5."

[2026-09-09T11:10:00] fase=9 acao=achado_nao_corrigido resultado=ok obs="DISCORDANCIA REGISTRADA, sem apagar o achado. O verificador de conformidade apontou que log_event (seguranca.py:57) nao carrega request_id, path e method, que Padrao_Logging_Estruturado lista como obrigatorios em TODA linha. O achado esta certo. Nao corrigi porque isso e o logger central do app inteiro, criado e auditado na Fase 7, e mexer nele agora atinge todas as chamadas de um projeto que nao tem nada a ver com responsavel multiplo. Fica como desvio declarado na matriz e como item para uma varredura propria, se o usuario quiser. Registrado tambem o achado 4 do verificador funcional: gerador.py:_resp_do_setor ainda devolve so o principal, entao cadastrar dois nao muda a tarefa gerada. Nao e furo, e a Fase 10, que comeca agora."

[2026-09-09T11:12:00] fase=9 acao=inventario_escada resultado=ok obs="grep -rn 'escada:' em backend/app e frontend/src devolve ZERO marcadores. Nada foi cortado com teto conhecido nesta fase: o teto de 20 ids nao e marcador de escada, e regra de validacao com motivo escrito no codigo."

[2026-09-09T11:15:00] fase=9 acao=fase_fechada resultado=ok obs="Criterio de aceite atendido: prova nova passa e reprova sem a validacao, as 18 antigas seguem passando (19 de 19 rc=0), e as 5 linhas da matriz que tocam esta fase estao com evidencia real colada (4 ok, 1 desvio declarado). Fase 9 = done. Comeca a Fase 10 (gerador)."

[2026-09-09T11:40:00] fase=10 acao=gerador_com_lista resultado=ok obs="_resp_do_setor devolve LISTA na ordem cadastrada (gerador.py:222-241) e a tarefa nasce com todos (:330), UMA tarefa por competencia. Supervisor sai do PRIMEIRO e a escada de tres degraus continua inteira, com um caso de prova para cada. O fallback em o.responsavel continua ali: sai na fase 13. Vinculo antigo, gravado antes da tabela nova, cai no vin.responsavel e nao fica sem ninguem."

[2026-09-09T11:45:00] fase=10 acao=visibilidade_por_todos resultado=ok obs="A regra 'tarefa some quando o responsavel esta bloqueado' passou a ser 'quando TODOS estao'. Escrita uma vez em app/visibilidade.py, e nao em cada lugar: routes/tarefas.py:41 e services/whatsapp.py:720 chamavam a mesma coisa por conta propria, e regra duplicada diverge na primeira mudanca -- a tarefa apareceria na tela sem gerar alerta. Tarefa SEM dono continua aparecendo de proposito: esconder buraco de cadastro e o que faz ninguem arrumar. Coberto tambem o caso legado (responsavel_id preenchido, lista vazia)."

[2026-09-09T11:50:00] fase=10 acao=varredura_consumidores resultado=ok obs="Varredura do backend e do frontend por verificador de contexto limpo. TRES corrigidos, todos por causa de N: (a) routes/alertas.py, o disparo manual filtrava Tarefa.responsavel_id, entao o segundo responsavel via a tarefa na tela e nao recebia cobranca nenhuma; passou a usar visibilidade.tarefas_abertas_do_usuario, que alcanca a lista e ainda respeita o que a tela esconde (antes cobrava por tarefa de empresa bloqueada); (b) whatsapp.py:764, o ensaio mostrava responsaveis[0].nome, um nome de dois, justamente na tela que existe para o escritorio conferir quem vai receber; (c) whatsapp.py:651, destinatarios_alerta iterava so a lista, entao tarefa antiga sem lista entrava na varredura e nao tinha destinatario -- o alerta nao saia e ninguem percebia."

[2026-09-09T11:52:00] fase=10 acao=achados_nao_corrigidos resultado=ok obs="Registrados sem corrigir, com o motivo. (1) usuarios.py:_usuario_em_uso conta a mesma tarefa duas vezes (principal e M2M), e agora tambem a matriz duas vezes; o valor so e usado como '> 0' para decidir entre inativar e excluir (usuarios.py:299), entao o numero inflado nao chega a lugar nenhum. Corrigir seria mexer por estetica. (2) usuarios.py:_carga_aberta conta tarefa de empresa bloqueada, que a tela ja esconde: e anterior a este trabalho e nao tem relacao com N responsaveis. (3) validador.py:513 acha a tarefa por empresa+obrigacao+competencia sem filtro de bloqueio: e proposital, dar baixa por documento recebido nao depende de quem esta bloqueado. (4) substituicao.py nao troca responsavel na matriz de setor, so em tarefa, empresa e obrigacao: substituicao e temporaria e a matriz e cadastro permanente, entao esta certo como esta; a fase 13 toca esse arquivo por outro motivo. (5) A prova prova_alerta_destinatarios tinha um duble de tarefa sem o campo `responsavel`, que a tarefa real tem; o duble foi completado, e nao o codigo afrouxado com getattr."

[2026-09-09T11:55:00] fase=10 acao=fase_fechada resultado=ok obs="prova_gerador_multiplos.py com 7 blocos passa, e REPROVA sem o fix (voltando a regra antiga de visibilidade e o responsavel unico no gerador, falham 4 casos). prova_gestor_setor.py e prova_marco_fechamento.py seguem passando. 20 de 20 provas rc=0. Zero marcadores 'escada:'. Fase 10 = done."

[2026-09-09T12:20:00] fase=11 acao=componente_extraido resultado=ok obs="O seletor de responsaveis saiu de dentro do JSX da tela de Tarefas (linha 1287, que ja existia com checkbox por pessoa e contador) para components/SeletorResponsaveis.jsx, com duas apresentacoes: inline, que e a caixa com rolagem de sempre, e popover, que e o da linha do setor no cadastro de empresa. Degrau 2 da Escada: componente que ja existe se extrai, nao se reescreve. A logica (marcar, desmarcar, buscar, estado do popover) foi para pages/seletorResponsaveis.js, pelo mesmo motivo de contexts/bilhete.js: roda em prova Node pura."

[2026-09-09T12:25:00] fase=11 acao=popover_por_portal resultado=ok obs="O painel do popover e desenhado com createPortal no document.body, e nao dentro do modal. Motivo: o modal de cadastro e um div com overflow-y-auto, e filho posicionado dentro dele sai CORTADO na borda -- o mesmo problema que Padrao_Modal_Popup_Centrado resolve com overflow:visible no <dialog>. A nota e escrita para Flask com CSS puro; aqui a traducao do principio e sair do fluxo do modal. A posicao vem do botao e e refeita no scroll e no resize, senao o painel fica parado enquanto o modal rola."

[2026-09-09T12:30:00] fase=11 acao=checkbox_proprio resultado=ok obs="Classe .check-app em index.css (o CSS central deste projeto, nao a tela): appearance-none com o check desenhado num ::after de borda em L girada 45 graus, exatamente a tecnica da nota, e cor por theme('colors.primary.600') em vez de hex. Substituiu o checkbox cru nos dois lugares: a lista de pessoas e o 'atende' da grade de setores. O 'atende' CONTINUA checkbox, e nao virou toggle, porque so grava no submit do modal: o teste de uma pergunta da nota responde 'nao muda nada agora'."

[2026-09-09T12:40:00] fase=11 acao=conferencia_visual resultado=ok obs="Feita por mim, com o app rodando local (uvicorn na 8000 e vite na 3000, SQLite temporario com 2 empresas, 5 setores e 6 pessoas), em vez de pedir ao usuario para olhar. O que foi visto, na ordem: o popover aberto no ULTIMO setor da lista aparece INTEIRO, atravessando a borda de baixo do modal, sem corte; marcar duas pessoas poe os dois chips na linha, com o primeiro destacado e a etiqueta PRINCIPAL ao lado dele na lista; ESC fecha SO o popover e o modal fica aberto com os chips no lugar; clique fora faz o mesmo; salvar e reabrir traz os dois de volta, e o banco confirma 'Societario: principal=2 lista=[(2,Ana Paula),(4,Carla)]'; o log do servidor registrou a mutacao. Na tela de Tarefas, o modal continua com a mesma cara. Os servidores locais foram encerrados no fim."

[2026-09-09T12:45:00] fase=11 acao=travessao_regrediu resultado=ok obs="ACHADO que nao e deste trabalho, e que fica declarado em vez de maquiado. A linha da matriz manda 'grep -rn — frontend/src volta vazio', e nao volta: sao 126 ocorrencias em 23 arquivos, das quais 59 em TEXTO QUE O USUARIO LE, em 11 telas (Notificacoes 18, Documentos 9, Modelos 7, Dashboard 7, Obrigacoes 7). A Fase 6 zerou isso em 17/08 e voltou no trabalho de agosto e setembro. Nos quatro arquivos DESTA fase o resultado e zero: os oito que havia em Tarefas.jsx e Empresas.jsx foram reescritos (dois pontos, parenteses, hifen simples), porque sao arquivos que eu estava editando de qualquer jeito. Limpar as outras 11 telas e trabalho proprio, nao item desta fase: a linha da matriz ficou 'parcial (escopo desta fase ok)' com o numero medido."

[2026-09-09T12:50:00] fase=11 acao=verificacao_adversarial resultado=ok obs="Dois verificadores em paralelo (sonnet, contexto limpo). O de conformidade com as 7 notas de UI devolveu LIMPO, com cada regra confrontada. O de corretude achou DOIS defeitos reais, os dois corrigidos: (1) o estado do popover nao era limpo ao fechar o modal, e como o setor_id e o mesmo em toda empresa, o popover reabriria SOZINHO na proxima empresa editada, com a busca digitada na anterior dentro dele; corrigido num ponto so, com um efeito que zera o popover quando o modal fecha, e nao em cada um dos quatro caminhos de fechamento; (2) os checkboxes da lista nao respeitavam o 'desabilitado', entao desmarcar 'atende' com o popover aberto deixava a lista clicavel sobre um setor que o submit descartaria. Casos 17 e 18 acrescentados a prova. Ele tambem confirmou que nenhum dos 16 casos anteriores passava por acidente."

[2026-09-09T12:55:00] fase=11 acao=fase_fechada resultado=ok obs="Criterio de aceite atendido: prova_seletor_responsaveis.js com 18 casos passa, npm run build sem erro (1.16s), 16 provas Node do frontend rc=0, e as 8 linhas da matriz que tocam esta fase estao fechadas com saida real ou com data e tela da conferencia visual (7 ok, 1 desvio declarado de icone). A linha do travessao ficou PARCIAL, com o alcance declarado. Fase 11 = done."

[2026-09-09T13:10:00] fase=12 acao=planilha_com_varios resultado=ok obs="A celula da planilha passou a aceitar varios nomes separados por ponto e virgula, com a ordem da celula virando a ordem da lista. Sem isso a planilha seria o caminho que DESFAZ o que a tela permite: o escritorio cadastra a matriz inteira por Excel, e reimportar apagaria o segundo responsavel de cada setor sem dizer nada. Nome que nao casa vira aviso nomeando quem ficou de fora, e os que casaram entram assim mesmo; celula vazia continua desmarcando o setor. O modelo baixavel ganhou o exemplo 'Ana Paula; Bruno Sa' e tres linhas explicando a regra, porque recurso que o modelo nao ensina e recurso que ninguem usa."

[2026-09-09T13:15:00] fase=12 acao=prova_criada resultado=ok obs="prova_importar_resp_multiplos.py, 7 blocos, gerando XLSX de verdade em memoria e lendo o resultado no banco. Alem do que o item pedia, cobre tres coisas que valia travar: desmarcar nao deixa linha orfa na tabela do meio, reimportar SUBSTITUI a lista em vez de empilhar, e o mesmo nome duas vezes na celula colapsa. O bloco 7 ABRE o modelo gerado e le o texto, o que e mais forte que a conferencia visual prevista no checklist. REPROVA sem o fix, verificado: trocando o split por [valor.strip()] falham 4 casos. 21 de 21 provas do backend rc=0."

[2026-09-09T13:16:00] fase=12 acao=fase_fechada resultado=ok obs="Criterio de aceite atendido nos tres casos que ele pedia (celula com dois nomes, nome desconhecido no meio, celula vazia desmarcando). Fase 12 = done."

[2026-09-09T13:50:00] fase=13 acao=fallback_removido resultado=ok obs="O gerador parou de cair em o.responsavel: quem atende sai SO da matriz (empresa, setor). Junto saiu o select do cadastro da obrigacao, o campo do estado da tela e o campo do PAYLOAD -- este ultimo e o cuidado que quase passou: a rota grava o que vier (model_dump(exclude_unset=True)), entao mandar responsavel_id=null apagaria o valor legado de toda obrigacao que alguem editasse. A coluna fica no banco marcada como legado em models.py:359-363. A substituicao parou de trocar responsavel em obrigacao, e continua trocando o supervisor, que e da obrigacao mesmo."

[2026-09-09T13:52:00] fase=13 acao=buraco_de_cadastro_visivel resultado=ok obs="Tirar o fallback sem contar nada trocaria um erro visivel por um invisivel: antes, empresa sem responsavel no setor herdava o da obrigacao e a falta nao aparecia em lugar nenhum. A resposta da geracao passou a trazer sem_responsavel (quantas) e empresas_sem_responsavel (quais), e a tarefa nasce assim mesmo, sem dono, em vez de nao ser gerada. Isso casa com a regra de visibilidade da fase 10, que deixa tarefa sem dono APARECENDO."

[2026-09-09T13:55:00] fase=13 acao=duas_provas_antigas_atualizadas resultado=ok obs="prova_gestor_setor.py e o bloco 5 da prova_gerador_multiplos.py quebraram, e QUEBRARAM CERTO: as duas afirmavam o fallback que o usuario mandou tirar. Nao foi a prova afrouxada para o codigo passar. prova_gestor_setor passou a cadastrar o analista na MATRIZ em vez de na obrigacao, e o que ela mede (a escada do supervisor, tres degraus) continua igual e continua passando. O bloco 5 da outra dizia 'o fallback continua valendo (sai na fase 13)', escrito por mim na fase 10 prevendo isto, e agora afirma o oposto com o motivo escrito. Tarefas.jsx passou a puxar a lista da matriz da empresa ao escolher a obrigacao, pela mesma rota que a tela de Empresas usa."

[2026-09-09T14:20:00] fase=14 acao=flag_vence_sentido resultado=ok obs="REVERSAO declarada de uma decisao escrita no codigo. models.py devolvia exige_documento=False para sentido=interna MESMO com a flag ligada, com o motivo escrito de que 'interna nao troca documento com ninguem'. A premissa estava incompleta: interna tem documento sim, so que quem anexa e o analista, e nao o cliente (balancete fechado, conciliacao assinada). Agora a flag EXPLICITA vence o sentido, e NULL continua derivando: interna em NULL nao exige NEM com identificadores cadastrados, que e o caso que impede obrigacao interna de hoje mudar sozinha no deploy. O comentario foi reescrito junto, porque comentario que contradiz o codigo e pior que comentario nenhum."

[2026-09-09T14:25:00] fase=14 acao=achado_evalidador_travaria resultado=ok obs="ACHADO que o item do plano nao previa, e que teria transformado a melhoria em armadilha. validador.py:265 tirava TODA obrigacao interna da busca por identificador. Ligar a flag, sem mexer nisso, faria a tarefa EXIGIR documento e o e-validador nunca achar a obrigacao para dar a baixa: o trabalho ficaria travado, pior do que antes. Interna com exige_documento=True passou a entrar na busca; interna em NULL continua fora, sem ambiguidade com quem de fato recebe documento do cliente."

[2026-09-09T14:28:00] fase=14 acao=prova_antiga_reescrita resultado=ok obs="prova_sentido_obrigacao.py nao passou de primeira, e nao podia: ela afirmava 'interna nem com a flag ligada, o sentido e mais forte', que e exatamente a regra revertida. O caso foi reescrito para o oposto, com o motivo, e ganhou um caso novo provando que interna com a flag entra na busca do e-validador. Segunda vez neste trabalho que uma prova antiga cai porque a REGRA mudou por decisao do usuario, e nao porque o codigo quebrou: registrado das duas vezes para nao virar habito de afrouxar prova."
