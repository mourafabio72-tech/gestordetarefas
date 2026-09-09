# LASTRO da Fase 18 e 19: campos obrigatórios no logger central

> As fases 9 a 17 foram fechadas em 2026-09-09 e o lastro delas está em
> `checkpoint 20260909 112849.zip`. Este arquivo cobre daqui para a frente.

## Tipo e regime

- **Tipo de projeto:** app WEB com Postgres (`App_Online_Auth`), já em produção
  em `gestordetarefas.zoaria.com.br`.
- **Regime de segurança:** WEB, obrigatória. Este trabalho é de segurança e
  observabilidade, então ele mesmo é o item que não se corta.
- **Sem tela.** Backend puro. Nenhuma nota de UI rege esta fase, e isso está
  declarado em vez de suposto: a varredura dos eixos de tela foi dispensada
  porque não há arquivo de tela no diff previsto.

## Doutrinas (cláusula pétrea, lidas integralmente em 2026-09-09)

- `00B_DOUTRINAS/Anti_Puxa_Saco.md`, 189 linhas, fim: "Fontes que embasam esta regra".
  Erro leva local, causa e correção, nessa ordem, sem interjeição.
- `00B_DOUTRINAS/Leitura_e_Retencao_de_Notas.md`, 236 linhas, fim: "Historico".
  Nota citada é nota lida nesta sessão, com caminho e trecho.

## A nota que manda nesta fase

`01_SISTEMAS/02_Seguranca/Padrao_Logging_Estruturado.md`, 210 linhas, fim:
"Histórico". Lida integral pelo agente principal, não por batedor.

Tabela de campos obrigatórios, verbatim da nota: `timestamp`, `level`, `event`,
`user_id`, `ip`, `request_id`, `path`, `method`. Hoje o `log_event` de
`backend/app/seguranca.py:57` garante três: `timestamp`, `level` e `event`. Os
outros cinco dependem de o chamador lembrar, e nenhum dos 14 passa os três do
achado.

Trecho que define o `request_id`, verbatim: "UUID gerado por request, ajuda a
correlacionar logs". A nota implementa em Flask com `g.request_id` e
`uuid.uuid4().hex[:16]`.

`01_SISTEMAS/02_Seguranca/Mapa_de_Conceitos_de_Seguranca.md:175`, conferido na
fonte pelo principal: "**Log estruturado em JSON** com `timestamp`, `level`,
`event`, `user_id`, `ip`, `request_id`". É a Família 6, e confirma a mesma lista.

## Regras de ouro que regem a execução

- `07_Regras_de_Ouro/Escada_Preguica_de_Codigo.md`, 241 linhas, fim: "Ver tambem".
  Verbatim: "a correção preguiçosa É a correção de causa raiz. Uma guarda na
  função compartilhada é um diff menor do que uma guarda em cada chamador".
  É exatamente o desenho desta fase: um ponto muda, 14 chamadores não são
  tocados.
- `07_Regras_de_Ouro/Sem_Travessao.md`, 43 linhas, fim: "Cuidado". Vale em
  qualquer arquivo, inclusive comentário e docstring novos.
- `08_Processo_Dev/TDD_RED_GREEN_REFACTOR.md`, 204 linhas, fim: "Historico".
  Verbatim: "Em toda mudanca de logica de negocio ... escreve-se o teste ANTES
  do codigo. RED -> GREEN -> REFACTOR."
- `08_Processo_Dev/Fechar_Tarefa_Rodar_Verifica.md`, 118 linhas, fim: "Historico".
  Verbatim: "'Pronto' nao e uma palavra que se diz sozinho".

## Regras locais, que não vêm da vault

Saíram das respostas do brainstorming socrático em 2026-09-09:

1. **Cinco campos automáticos**, e não os três do achado: `request_id`, `path`,
   `method`, `user_id` e `ip`. Motivo: `ip` e `usuario_id` hoje são passados a
   mão e só em parte dos chamadores, então metade das linhas sai sem eles.
2. **O campo chama `user_id`**, como a nota, e não `usuario_id`, como o código
   legado. A vault vence código legado. Três chamadores mudam de grafia.
3. **Os eventos que faltam ficam fora desta fase.** A nota tem uma tabela de
   eventos que sempre entram em log (`ACESSO_NEGADO_403`, `RATE_LIMIT_HIT`,
   `LOGOUT`, `EXPORT_DADOS`) e o app não emite todos. Vira fase própria, com
   levantamento antes. Misturar as duas coisas incharia o diff.
4. **`X-Request-ID` volta na resposta.** Ampliação declarada, que a nota não
   pede: sem devolver o id, reclamação de usuário não se liga a linha de log,
   e a busca vira horário mais chute.

## Decisão de processo, declarada

O projeto **não tem pytest**: a suíte é `backend/provas/prova_*.py`, executável
direto por `python`. O TDD desta fase segue nesse formato, e não em pytest:
a prova é escrita ANTES, tem que falhar com o código de hoje (RED) e passar
depois (GREEN). Criar infra de pytest aqui seria ampliar escopo, e a nota de
TDD manda o teste antes do código, não manda o framework.

## Escada, aplicada ao desenho antes de virar fase

- Degrau 2, já existe no codebase: o IP sai de `ip_do_cliente(request)`
  (`seguranca.py`), que já trata `X-Forwarded-For` atrás do proxy. Não se
  escreve extração de IP nova.
- Degrau 3, biblioteca padrão resolve: `contextvars` é do Python, e é o que
  carrega o contexto do request até o `log_event` sem passar `request` por 14
  chamadores. **Nenhuma dependência nova entra** (existe pacote pronto de
  correlation-id, e ele é degrau 7 para um problema que o degrau 3 resolve).
- Degrau 6, uma linha resolve: os defaults entram com `setdefault`, então
  chamador que já manda o campo continua mandando o dele.
