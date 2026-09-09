# LASTRO

Trabalho: **varios responsaveis por (empresa, setor)** no cadastro de empresa.
Aberto em 2026-09-09 pela `genesis-iniciar`, modo AMPLIACAO.

O projeto e anterior a este GENESIS na parte antiga: as fases 0 a 7 (SSO do Hub)
foram fechadas em 2026-08-17 e o material delas esta em
`checkpoint 20260817 152106.zip`, nesta pasta. Este LASTRO cobre daqui pra frente.

## Tipo e regime

- Tipo de projeto: **App Online Auth (single-tenant)**, nota
  `01_SISTEMAS/04_Tipos_de_App/App_Online_Auth.md`
- Regime de seguranca: **WEB (seguranca obrigatoria)**
- Stack ja decidida, nao se repergunta: FastAPI + SQLAlchemy + Postgres no backend,
  React + Vite + Tailwind no frontend, deploy EasyPanel por webhook.

## Cor e icones (o que este projeto usa de fato)

- Token de cor: paleta `primary` do `frontend/tailwind.config.js` (Sage e Creme,
  verde oliva `primary-600 #5f7057`), mais a familia `gray` reescrita em creme.
- Arquivo do token: `frontend/tailwind.config.js`, bloco `theme.extend.colors`
- PROIBIDO: hex escrito direto em JSX. Cor sai de classe Tailwind (`text-primary-600`).
- Icones: `lucide-react`. **DESVIO DECLARADO** de `Icones_Phosphor` ("Phosphor unico"):
  o app nasceu com lucide em todas as 17 telas. Trocar a biblioteca inteira nao e
  escopo desta melhoria. Item novo usa lucide, para nao criar a segunda linguagem
  de icone que a nota justamente combate.

## Doutrinas (carregam sempre, nao entram por rota)

- `00B_DOUTRINAS/Anti_Puxa_Saco.md` : verdade util antes de tom agradavel; erro se
  reporta como local, causa e correcao.
- `00B_DOUTRINAS/Leitura_e_Retencao_de_Notas.md` : nota se le integral, citacao so
  com leitura na sessao, LASTRO com contagem de linhas e titulo da ultima secao.

## Notas de padrao que regem este trabalho

| Nota | Por que rege |
|---|---|
| `01_SISTEMAS/07_Regras_de_Ouro/Escada_Preguica_de_Codigo.md` | poda do plano; achou componente pronto no proprio projeto |
| `01_SISTEMAS/08_Processo_Dev/Brainstorming_Socratico_por_Tarefa.md` | as 5 perguntas feitas antes de planejar |
| `01_SISTEMAS/01_Padroes_Gerais/Padrao_Selecao_em_Lote.md` | checkbox de marcar varios nao e o do sistema operacional |
| `01_SISTEMAS/01_Padroes_Gerais/Padrao_Toggle_OnOff.md` | fronteira toggle x checkbox; o "atende" fica checkbox |
| `01_SISTEMAS/01_Padroes_Gerais/Padrao_Toggle_Tipos.md` | multi selecao esta fora da taxonomia de toggle |
| `01_SISTEMAS/01_Padroes_Gerais/Padrao_Tabela.md` | a aba de setores e GRADE, nao listagem: nao instrumentar |
| `01_SISTEMAS/01_Padroes_Gerais/Componente_SelectBusca.md` | nao tem modo multiplo; nao ha o que reusar da vault |
| `01_SISTEMAS/01_Padroes_Gerais/Padrao_Modal_Popup_Centrado.md` | popover dentro de modal corta sem overflow visivel |
| `01_SISTEMAS/01_Padroes_Gerais/Padrao_Modal_Nao_Fecha_Sozinho.md` | fechar o popover nao pode fechar o modal |
| `01_SISTEMAS/01_Padroes_Gerais/Sistema_de_Estilos.md` | cor por token, nunca hex na tela |
| `01_SISTEMAS/02_Seguranca/Padrao_IDOR.md` | id que chega no body se valida antes de gravar |
| `01_SISTEMAS/02_Seguranca/Padrao_Mass_Assignment.md` | whitelist do que o body pode gravar |
| `01_SISTEMAS/02_Seguranca/Padrao_Validacao_de_Input.md` | tres camadas: string crua, validacao tipada, regra |
| `01_SISTEMAS/02_Seguranca/Padrao_Logging_Estruturado.md` | mutacao de dado critico vira log_event |
| `01_SISTEMAS/07_Regras_de_Ouro/Verificacoes_Mecanicas_de_Tela.md` | os greps da matriz de conformidade |

## Regras locais deste trabalho (decisoes, nao vem da vault)

1. **Uma tarefa por competencia com N responsaveis**, nunca uma tarefa por pessoa.
   Decisao do usuario em 2026-09-09. Nao muda contagem de tarefa nem dashboard.
2. **Modelo: principal mais M2M**, espelhando o que a Tarefa ja faz. A linha de
   `empresa_setor_responsavel` continua sendo o registro de "a empresa atende este
   setor", com `responsavel_id` = principal; os demais entram numa tabela
   associativa nova. Dado existente segue valido sem conversao.
3. **O principal e SEMPRE o primeiro da lista**, gravado num unico ponto. Risco
   conhecido: dois lugares guardando a mesma verdade divergem. A prova trava isso.
4. **Supervisor sai do primeiro da lista**, mantendo a escada atual (gestor da
   pessoa, gestor do setor, supervisor padrao da obrigacao). Decisao do usuario.
5. **Nao ha efeito retroativo.** Mexer no cadastro nao altera tarefa ja gerada.
   Decisao do usuario.
6. **Planilha aceita varios nomes separados por ponto e virgula.** Decisao do usuario.
7. **Precedencia de stack:** as notas de UI da vault sao escritas para Flask com CSS
   puro (`.cv-sw`, `.tsel`, `static/css/`). Aqui vale o PRINCIPIO delas escrito em
   Tailwind, nao a classe literal. Precedente ja firmado neste projeto em
   2026-08-20 (barra de filtros da tela de Tarefas), registrado no LOG.

8. **Dono de tarefa nao mora na obrigacao.** A obrigacao serve varias empresas, entao
   o responsavel padrao dela sai (fases 13). Quem atende vem so da matriz da empresa.
   Obrigacao sem setor gera tarefa SEM dono, e a geracao avisa quantas ficaram assim.
   Decisao do usuario em 2026-09-09.
9. **Obrigacao interna pode exigir documento.** A flag explicita vence o `sentido`.
   Reversao declarada de `models.py:302-306`. `NULL` continua derivando, entao interna
   de hoje nao muda sozinha. Decisao do usuario em 2026-09-09.
10. **Desconsiderar marca, nao apaga.** A tarefa vai para `CANCELADA` com motivo e
   autor, sai das pendencias e fica no historico; a empresa entra na excecao daquela
   obrigacao, com caminho de volta. Decisao do usuario em 2026-09-09.
11. **Vincular empresa desmarca "aplicar a todas"** e poe `alvo_modo='vinculadas'`.
   Desvincular a ultima volta atras. Decisao do usuario em 2026-09-09.

## Graphify

Mapa atualizado em 2026-09-09 antes de planejar: 1336 nos, 2977 arestas.
