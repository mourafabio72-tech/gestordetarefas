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
