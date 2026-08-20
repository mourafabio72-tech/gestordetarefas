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
