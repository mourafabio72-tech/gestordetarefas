# LASTRO das fases 23 a 25: os eventos que faltam na tabela da nota

> As fases 1 a 22 foram fechadas e o lastro delas está nos três checkpoints
> desta pasta. Este arquivo cobre daqui para a frente.

## Tipo e regime

- **Tipo de projeto:** app WEB com Postgres (`App_Online_Auth`), já em produção
  em `gestordetarefas.zoaria.com.br`.
- **Regime de segurança:** WEB, obrigatória. Este trabalho é de segurança e
  observabilidade, então ele mesmo é o item que não se corta.
- **Sem tela.** Backend, com uma exceção de uma linha: o `logout` do
  `AuthContext.jsx` passa a chamar a rota nova antes de apagar o token. Não
  muda pixel nenhum, e por isso nenhuma nota de UI rege estas fases. Declarado
  em vez de suposto.

## Doutrinas (cláusula pétrea, lidas integralmente em 2026-09-09)

- `00B_DOUTRINAS/Anti_Puxa_Saco.md`, 189 linhas, fim: "Fontes que embasam esta
  regra". Erro leva local, causa e correção, nessa ordem, sem interjeição.
- `00B_DOUTRINAS/Leitura_e_Retencao_de_Notas.md`, 236 linhas, fim: "Historico".
  Nota citada é nota lida nesta sessão, com caminho e trecho.

## A nota que manda nestas fases

`01_SISTEMAS/02_Seguranca/Padrao_Logging_Estruturado.md`, 210 linhas, fim:
"Histórico". Lida integral pelo agente principal nesta sessão.

A tabela dos oito campos já foi cumprida pelas fases 18 a 20. O que resta é a
outra tabela dela, "O que SEMPRE entra em log", com treze eventos. O
levantamento de 2026-09-09 está no LOG e diz o estado exato: quatro cobertos,
um coberto com outro nome (`LOGIN_FALHA` sai como `LOGIN_RECUSADO`), dois que
não se aplicam a este app pelo motivo escrito, e **seis ausentes de fato**.

Trecho que rege o anti-padrão que estas fases também corrigem, verbatim:
"Linha de log sem `event` padronizado | Não dá pra filtrar".

## A nota que a de logging aponta, e que rege o evento de IDOR

`01_SISTEMAS/02_Seguranca/Padrao_IDOR.md`, 199 linhas, fim: "Histórico". Lida
integral nesta sessão. A seção "Auditoria" dá o formato do evento, verbatim:

> "Quando o usuário recebe 404 por IDOR (recurso existe mas não é dele), vale
> logar como tentativa suspeita."

E o exemplo dela grava `recurso` e `recurso_id` como campos extras.

**A condição importa e muda o código:** só é tentativa quando o recurso
EXISTE e não é do usuário. Id que não existe é 404 comum, e logar os dois
juntos encheria o log de digitação errada. O app hoje resolve escopo dentro do
próprio SELECT, então essa distinção não existe de graça: ela custa uma
segunda consulta, e isso está declarado no plano em vez de aparecer como
surpresa na execução.

A mesma nota confirma a divisão de níveis: vertical é o 403 das guardas,
horizontal é o IDOR. São dois eventos porque são duas perguntas.

`01_SISTEMAS/02_Seguranca/Principios.md`, 48 linhas, fim: "Ver também". Lida
integral nesta sessão. Confirma que `LOGOUT` faz parte do mínimo auditado, e
que a auditoria legal mora em tabela própria. Este app não tem `logs_acesso`, e
não é este trabalho que vai criá-la: aqui é application log em stdout.

## Regras de ouro que regem a execução

As mesmas do trabalho das fases 18 a 22, relidas nesta sessão pelo caminho:

- `07_Regras_de_Ouro/Escada_Preguica_de_Codigo.md`: guarda na função
  compartilhada, e não em cada chamador. É o desenho do `ACESSO_NEGADO_403`,
  onde três dependências cobrem quatorze pontos de 403.
- `07_Regras_de_Ouro/Sem_Travessao.md`: vale em qualquer arquivo, inclusive
  comentário e docstring novos.
- `08_Processo_Dev/TDD_RED_GREEN_REFACTOR.md`: a prova é escrita ANTES e tem
  que falhar com o código de hoje.
- `08_Processo_Dev/Fechar_Tarefa_Rodar_Verifica.md`: "pronto" não se diz
  sozinho.

## Regras locais, que não vêm da vault

Saíram das três decisões do usuário em 2026-09-09, e cada uma fecha uma porta:

1. **`LOGOUT` ganha rota que só registra.** `POST /api/auth/logout` emite o
   evento e devolve 200. Não invalida token, porque o JWT é stateless e
   blacklist é escopo de outro trabalho. O que a rota entrega é o fim de sessão
   na trilha, e é isso que a nota pede.
2. **`EXPORT_DADOS` só onde o servidor vê o export acontecer.** Nada de o
   frontend avisar o backend.
3. **Registro crítico é usuário, permissão, empresa e obrigação.** Tarefa,
   documento, setor, grupo e substituição ficam de fora por decisão do usuário,
   e não por esquecimento: são o dia a dia da equipe, e logar tudo afogaria o
   sinal que estas fases existem para criar.

## O limite que a decisão 2 deixa aberto, dito agora e não depois

O CSV da tela de Documentos é montado no navegador
(`frontend/src/pages/Documentos.jsx:103`), a partir de dados que já estavam na
tela. Do lado do servidor não existe evento nenhum: a única rota é
`GET /api/documentos`, que é a listagem chamada a cada filtro. Marcar aquela
rota como `EXPORT_DADOS` seria registrar "exportou" toda vez que alguém abriu a
tela, e log que mente é pior que log ausente.

Então, com a decisão 2, `EXPORT_DADOS` cobre **uma rota**: o relatório XLSX de
obrigações (`routes/obrigacoes.py:157`), que é export de massa de verdade. O CSV
de Documentos fica **descoberto e declarado**. Se um dia valer cobrir, o
conserto é barato e já tem nome: é a opção que o usuário não escolheu, uma
chamada do frontend antes do download.

Download de arquivo unitário (`tarefas.py:368`, `:544`,
`upload_publico.py:124`) não entra: a nota fala de export "de massa". E os
`modelo_importacao_*.xlsx` são planilhas vazias de layout, não são dado.

## Escada, aplicada ao desenho antes de virar fase

- Degrau 1, o problema já está resolvido: `RATE_LIMIT_HIT` e `CSRF_INVALIDO`
  não viram código nenhum. O primeiro já existe com outro nome e outro escopo
  (`LOGIN_BLOQUEADO` e `SSO_BLOQUEADO`, que são o único limite do app), e o
  segundo não se aplica a autenticação por `Authorization: Bearer`, o que o
  próprio `routes/auth.py:137` já registra.
- Degrau 2, já existe no codebase: as três guardas de 403 (`auth.py:63`, `:82`,
  `:94`) são o ponto único por onde passa toda negativa vertical do app. Uma
  linha em cada, e os quatorze pontos de 403 ficam cobertos sem tocar em rota
  nenhuma.
- Degrau 6, uma linha resolve: `LOGIN_RECUSADO` não vira `LOGIN_FALHA`. O nome
  atual já é padronizado, já é filtrável, e está em produção há semanas. Trocar
  o nome quebraria qualquer busca antiga por ganho zero. Registrado aqui para
  não voltar como achado.
