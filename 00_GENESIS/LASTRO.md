# LASTRO das fases 27 a 31: obrigação acessória transmitida ao órgão

> As fases 1 a 26 estão fechadas, e o lastro delas está nos quatro checkpoints
> desta pasta. Este arquivo cobre daqui para a frente.

## Tipo e regime

- **Tipo de projeto:** app WEB com Postgres (`04_Tipos_de_App/App_Online_Auth.md`),
  single-tenant, em produção em `gestordetarefas.zoaria.com.br`.
- **Regime de segurança:** WEB, obrigatória. Validação de entrada no servidor
  e rota pública de upload fazem parte deste trabalho, e não se cortam.
- **Tem tela:** formulário de Obrigação, menu da tarefa e aba de Documentos.

## Decisões visuais já firmadas no projeto (não se reperguntam)

```
Token de cor: primary do Tailwind (primary-50 a primary-800)
Arquivo do token: frontend/tailwind.config.js:12
Valor: verde-oliva do tema Sage & Creme, definido no arquivo acima
PROIBIDO: hex em JSX (hoje há um, bg-[#faf7f0] em Obrigacoes.jsx:925, dentro do bloco tocado)
Tema: claro. Acesso: login por perfil (JWT próprio).
Ícones: lucide-react, desvio declarado desde a fase 8.
```

## Doutrinas (lidas integralmente em 2026-09-15)

- `00B_DOUTRINAS/Anti_Puxa_Saco.md`, 189 linhas, fim: "Fontes que embasam esta regra".
  Erro leva local, causa e correção, nessa ordem.
- `00B_DOUTRINAS/Leitura_e_Retencao_de_Notas.md`, 236 linhas, fim: "Historico".
  Nota citada é nota lida nesta sessão.

## O problema, medido no código em 2026-09-15

O usuário tem obrigação acessória (SPED, DCTFWeb, EFD) que o escritório
transmite, e a baixa é pelo recibo no e-validador. Nenhuma das três opções de
"O documento vai para que lado?" descreve isso. A combinação que devia servir,
"Nenhum" com "Exige documento", está quebrada por três defeitos:

1. **A edição nunca gravou o sentido.** `update_obrigacao` (`routes/obrigacoes.py:313`)
   lê `ObrigacaoUpdate` (`schemas.py:274`), que não declara `sentido`. O
   Pydantic descarta campo não declarado sem erro. Na criação grava, na edição não.
2. **A tela esconde os identificadores da interna** (`Obrigacoes.jsx:497`), e o
   e-validador acha a obrigação justamente por eles (`validador.py:274-276`).
   Interna com documento trava a baixa manual e nunca casa com o recibo.
3. **O painel ficou para trás na reversão de 09/09.** `painel.py:94` devolve
   `False` para toda interna, e o `models.py:377` diz que a flag vence.

E um quarto, que só aparece com o sentido novo: **o link público de envio de
comprovante sai para toda tarefa** (`whatsapp.py:740`, `Tarefas.jsx:710`), sem
olhar o sentido.

## Decisões do usuário (2026-09-15)

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Como a obrigação acessória aparece | **Quarta opção**, "Transmitir ao órgão". Valor gravado: `transmitir` |
| 2 | O recibo vai ao cliente | **Não**, fica no acervo da tarefa |
| 3 | Obrigações já cadastradas | **Eu listo as candidatas, ele aprova antes de alterar** |
| 4 | Contador próprio no painel | **Não** |
| 5 | Estilo do seletor (Padrao_Toggle_Tipos) | **Tipo 1, multi opções**; a explicação de cada opção vai para o `title` |
| 6 | Link de envio de comprovante | **Só para "receber"**, o que muda também "entregar" e "interna" |
| 7 | Aba do acervo | **"Comprovantes e recibos"** no lugar de "Recebidos do cliente" |

## Notas que regem, e o trecho que manda

- `01_Padroes_Gerais/Padrao_Toggle_Tipos.md`, 167 linhas, fim: "Ver também". Lida
  integral pelo principal. Linha 11: "Todo 'menu para escolher algo' que não é
  dropdown ... cai em UM destes 3 tipos. Não existe 4º estilo." Tipo 1: "borda
  `var(--cor-primaria)` + fundo `var(--cor-primaria-suave)` + texto
  `var(--cor-primaria-escura)`". Acessibilidade: "Sempre `<button type="button">`"
  e "Wrapper com `role="radiogroup"` + `aria-label`".
- `02_Seguranca/Padrao_Validacao_de_Input.md`, 197 linhas, fim: "Histórico". Lida
  integral pelo principal. "Toda string crua passa por validação tipada antes de
  tocar regra de negócio." Anti-padrão: "Validar só no `<input required>` do HTML".
- `02_Seguranca/Padrao_Mass_Assignment.md`: "Backend define a whitelist de campos
  editaveis." Aqui o defeito é o inverso: o campo editável ficou FORA da whitelist.
- `02_Seguranca/Padrao_Logging_Estruturado.md`: mutação de dado crítico sempre
  entra. A edição de obrigação já emite `EDICAO_REGISTRO_CRITICO`
  (`obrigacoes.py:331`), e por isso a reclassificação passa pela tela, e não
  por UPDATE no console.
- `01_Padroes_Gerais/Tela_Nao_Tem_Manual.md`: "O rótulo do campo, o título da
  coluna e o `title` do botão carregam a informação."
- `01_Padroes_Gerais/Sistema_de_Estilos.md`: "o hex nunca aparece na tela".
- `07_Regras_de_Ouro/Sem_Popup_Nativo.md`: nada de `alert(`, `confirm(`, `prompt(`
  em código NOVO. Os que já existem em `Tarefas.jsx` ficam fora (ver plano).
- `07_Regras_de_Ouro/Escada_Preguica_de_Codigo.md`: "procure todos os chamadores
  da função que você vai tocar" e "a correção preguiçosa É a correção de causa raiz".
- `08_Processo_Dev/TDD_RED_GREEN_REFACTOR.md`: prova escrita antes, falhando.
- `08_Processo_Dev/Fechar_Tarefa_Rodar_Verifica.md`: "'Pronto' nao e uma palavra
  que se diz sozinho".
- `07_Regras_de_Ouro/Protocolo_Revisao_de_Tela.md`: domínio LÍNGUA dispara em
  todo pedido de tela; ajuste pontual não reescreve a tela.
- `07_Regras_de_Ouro/Portugues_BR_Acentuacao.md` e `Sem_Travessao.md`: texto de
  tela com acento completo; zero travessão em qualquer arquivo tocado.

## Regras locais, que não vêm da vault

1. **Uma regra de documento, num lugar só.** Função pura em `models.py`, usada
   pela propriedade `Tarefa.exige_documento` e pelo `painel.py`. A duplicação
   existia "por economia" e foi ela que deixou o painel para trás.
2. **`transmitir` se comporta como `receber` para exigir documento e para o
   e-validador**, e diferente em duas coisas só: não entra em "aguardando
   cliente" no painel, e não gera link de envio.
3. **A trava do link não entra no download da guia.** `/publico/baixar` é o
   caminho do "entregar", e uma prova de não-regressão mede isso antes.
4. **Recusa de link fora de "receber" devolve o mesmo 404** que link inválido,
   para não dizer ao visitante que a tarefa existe.

## Não coberto, e declarado

- `70_ESTILO/` não existe nesta cópia da vault: voz e vocabulário proibido sem varredura.
- `scripts/pasquale.py` e `checar_classes_css.py` não existem: gate de língua
  por grep de travessão e leitura do diff.
- A vault é Flask e CSS central; o projeto é React e Tailwind. Onde a nota dá
  classe CSS (`.xx-presets`), a tradução é por classe utilitária com o token
  `primary`, e isso fica escrito no checklist.

---

# Acréscimo de 2026-09-18: recorte por regime na geração (fases 32 a 34)

## O pedido

No modal "Gerar tarefas do mês", em "Para quais empresas?", gerar também por
regime tributário.

## Medido no código em 2026-09-18

- O regime já existe: `Empresa.regime_tributario` (`models.py:101`), com os valores
  `indefinido|lucro_real|lucro_presumido|mei|simples_nacional|terceiro_setor|imune|isento`.
  A listagem de empresas que a tela recebe traz o campo e só as ativas (`empresas.py:267`).
- O recorte por empresa já existe e é INTERSEÇÃO com `empresas_alvo` (`gerador.py:368-384`).
  O regime entra como outro jeito de montar a mesma lista de ids.
- **Armadilha:** lista de ids vazia no body é lida pelo backend como "todas"
  (`GerarRequest`, `routes/obrigacoes.py:142`). A tela já bloqueia isso em "somente as
  escolhidas" (`Obrigacoes.jsx:1123-1125`), e o modo regime precisa do mesmo bloqueio.
- **Lacuna antiga:** `POST /obrigacoes/gerar` não chama `log_event` (fase 32).

## Decisões do usuário (2026-09-18)

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Onde o regime aparece | **Terceira opção**, "Por regime tributário" |
| 2 | Quais regimes | **Os 6 citados mais MEI**, sem "sem regime cadastrado" |
| 3 | Mais de um regime por vez | **Sim** |
| 4 | Trabalho aberto | **Commitar 27 e 28 antes** (feito: `45ac41a`, `4d1a669`, sem push); esta demanda antes da 29 |
| 5 | Estilo do seletor "Para quais empresas?" (Padrao_Toggle_Tipos) | **Tipo 1, multi opções**, igual ao da fase 29 |

## Regras locais novas

1. **Só frontend no recorte.** A tela converte regimes em `empresa_ids`. Nenhum campo novo
   no body, e `gerador.py` não muda. A autorização continua sendo a flag
   `alocar_obrigacao` mais a interseção com `empresas_alvo`.
2. **Recorte vazio nunca sai da tela.** Modo diferente de `todas` com zero ids bloqueia o botão.
3. **A regra do recorte mora num módulo sem JSX** (`src/pages/recorteGeracao.js`), provado por Node.
   É o mesmo molde de `payloadObrigacao.js`.
4. **Checkbox de multisseleção usa `check-app`**, o precedente da fase 8.

## Notas que regem este acréscimo

Lidas pelos batedores em 2026-09-18, com as fichas conferidas pelo principal:
`Padrao_Toggle_Tipos`, `Padrao_Toggle_OnOff`, `Padrao_Modal`, `Padrao_Formulario`,
`Padrao_Loading_Estado`, `Sempre_Mostrar_Loading`, `Sem_Popup_Nativo`,
`Protocolo_Revisao_de_Tela`, `Verificacoes_Mecanicas_de_Tela`, `Sistema_de_Estilos`,
`Tela_Nao_Tem_Manual`, `Portugues_BR_Acentuacao`, `Sem_Travessao`, `Padrao_IDOR`,
`Padrao_Mass_Assignment`, `Padrao_Validacao_de_Input`, `Padrao_Logging_Estruturado`,
`Mapa_de_Conceitos_de_Seguranca`, `Perfis_e_Modulos`, `Matriz_VER_EDITAR`.
Lida pelo principal: `08_Processo_Dev/Brainstorming_Socratico_por_Tarefa.md` (126 linhas),
e `02_Seguranca/Padrao_IDOR.md` conferida nos trechos citados (`:22`, `:26`, `:122`).
