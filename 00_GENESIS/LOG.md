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
