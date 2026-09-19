# LASTRO das fases 38 a 42: periodicidade da obrigação

> Fases 1 a 37 fechadas; o lastro delas está nos checkpoints desta pasta, o mais
> recente `checkpoint 20260919 160450.zip`. Este arquivo cobre daqui para a frente.

## Tipo e regime

- **Tipo de projeto:** app WEB com Postgres (`04_Tipos_de_App/App_Online_Auth.md`),
  single-tenant, em produção em `gestordetarefas.zoaria.com.br`.
- **Regime de segurança:** WEB, obrigatória. A validação de `meses_ativos` e
  `competencia_ref` no servidor é guardrail de trust boundary e não se corta.
- **Tem tela:** modal de Obrigação (`frontend/src/pages/Obrigacoes.jsx`).

## Decisões visuais já firmadas no projeto (não se reperguntam)

```
Token de cor: primary do Tailwind (primary-50 a primary-800)
Arquivo do token: frontend/tailwind.config.js
PROIBIDO: hex em JSX
Tema: claro. Acesso: login por perfil (JWT próprio). Ícones: lucide-react (desvio declarado desde a fase 8).
Seletor tipo 1 do projeto: role="radiogroup" + aria-label, <button type="button" role="radio" aria-checked>,
escolhido em border-primary-600 bg-primary-50 text-primary-800 (precedentes: fases 29 e 33).
```

## O problema, medido no código em 2026-09-19

1. Toda obrigação nasce com os 12 meses (`models.py:434`, `schemas.py:274`,
   `Obrigacoes.jsx:47`, `importador_cronograma.py:291`), e a tela não diz se ela
   é mensal, trimestral ou anual: só mostra 12 botões de mês
   (`Obrigacoes.jsx:843-857`). A DEFIS rodou com 12 meses até 19/09.
2. **A competência da anual não casa com o recibo.** O e-validador lê a
   competência do documento pelo INÍCIO do período, `01/01/2025 a 31/12/2025`
   vira `01/2025` (`validador.py:115-118`), e procura a tarefa por igualdade
   exata (`validador.py:519-531`). A anual nasce com o mesmo mês do ano
   anterior (`ano_anterior` = -12, `gerador.py:22-28`): DEFIS `03/2025`, ECF
   `07/2025`. A trimestral tem o mesmo defeito. Provável, a confirmar com
   recibo real na fase 38.
3. `competencia_ref` e `meses_ativos` são texto livre na entrada
   (`schemas.py:274, :279, :310, :315`), e o gerador engole lixo em silêncio
   (`gerador.py:44-47`, texto não numérico vira -1).
4. O Excel da relação de obrigações só conhece os 4 apelidos (`_COMP`,
   `routes/obrigacoes.py:105`): deslocamento numérico sai cru ("-14"). A tela
   da relação já trata (`RelacaoObrigacoes.jsx:14-22`).

## Decisões do usuário (2026-09-19)

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Onde a periodicidade mora | **Em lugar nenhum**: a tela deduz dos meses marcados. Sem coluna nova |
| 2 | Competência da anual e da trimestral | **A periodicidade define**: anual = janeiro do ano anterior; trimestral = primeiro mês do trimestre anterior. Conferido antes com recibo real |
| 3 | Meses da trimestral | **Escolhe o primeiro mês de entrega, o sistema marca de 3 em 3** (resposta "3s", lida como 3a e declarada) |
| 4 | Estilo do seletor | **Tipo 1, multi opções** |

## Regras locais que saem das decisões

- Deslocamento da anual com entrega no mês M: `-(M + 11)`. Março: -14, `01/2025`.
- Deslocamento da trimestral com entrega no mês M: `-(((M - 1) % 3) + 3)`.
  Abril: -3 (jan); maio: -4 (jan); julho: -3 (abr). Constante para os 4 meses
  de uma mesma série, porque eles distam 3.
- Mensal e Personalizada: a competência continua escolhida à mão, como hoje.
- A escolha do mês na anual e na trimestral usa os próprios 12 botões de mês.
  Nenhum `<select>` novo.

## Doutrinas (lidas integralmente em 2026-09-19)

- `00B_DOUTRINAS/Anti_Puxa_Saco.md`, 189 linhas, fim: "Fontes que embasam esta regra".
- `00B_DOUTRINAS/Leitura_e_Retencao_de_Notas.md`, 236 linhas, fim: "Historico".

## Notas que regem

Lidas integrais nesta sessão pelo principal: `Brainstorming_Socratico_por_Tarefa`
(126), `Padrao_Toggle_Tipos` (167). Pelos batedores sonnet, com ficha: as demais
em `NOTAS_LIDAS.md`. A `genesis-continuar` relê integral as da fase que executa.

- **Padrao_Toggle_Tipos:** "Wrapper com `role=\"radiogroup\"` + `aria-label`";
  "Sempre `<button type=\"button\">`"; tipo 1 marca com borda + fundo suave.
- **TDD_RED_GREEN_REFACTOR:** prova antes do código, RED e GREEN no LOG.
- **Escada_Preguica_de_Codigo:** sem coluna nova (degrau 2); validação em trust
  boundary é guardrail.
- **Padrao_Validacao_de_Input:** "Toda string crua passa por validação tipada
  antes de tocar regra de negócio." (linha 17, conferida pelo principal).
- **Padrao_Logging_Estruturado:** a edição já emite `EDICAO_REGISTRO_CRITICO`
  (`routes/obrigacoes.py:398`); correção em produção passa pela tela ou pela API.
- **Tela_Nao_Tem_Manual, Sem_Travessao, Portugues_BR_Acentuacao, Sem_Popup_Nativo,
  Verificacoes_Mecanicas_de_Tela, Protocolo_Revisao_de_Tela, Fechar_Tarefa_Rodar_Verifica.**
- **Nunca_DELETE_Fisico:** correção de dado é UPDATE pela rota, nunca DELETE.
