# Conformidade com a vault

Uma linha por REGRA, não por fase. `Status` só vira `ok` com a saída real do
comando colada em `Evidência`, ou com a frase `conferência visual feita em <data>,
tela <qual>` quando a prova for visual. Fase não fecha com linha pendente.

| Nota | Regra literal | Proibido | Onde aplica | Prova | Evidência | Status |
|---|---|---|---|---|---|---|
| Padrao_Impersonacao_Segura | "Marcar como usado ANTES do login, e nunca depois" | emitir o JWT e só então marcar o jti | rota de consumo | teste: bilhete válido consumido, jti já consta usado antes de o token existir | | pendente |
| Padrao_Impersonacao_Segura | "O `AND usado=0` faz o banco decidir o vencedor com a trava de linha" mais conferir linhas afetadas | `UPDATE` sem `AND usado=0`, ou sem checar rowcount | rota de consumo | duas requisições simultâneas com o mesmo bilhete: exatamente uma entra | | pendente |
| Padrao_Impersonacao_Segura | "Inexistente, expirado e já usado devolvem a MESMA resposta" | mensagem distinta por caso | rota de consumo | 4 chamadas (inválido, expirado, usado, assinatura errada) devolvem corpo e status idênticos | | pendente |
| Padrao_Impersonacao_Segura | "Recusa token acima do tamanho esperado ANTES de consultar o banco" | validar tamanho depois da consulta | rota de consumo | bilhete de 10 KB recusado sem query no banco | | pendente |
| Padrao_Impersonacao_Segura | "O token NUNCA entra em log" | bilhete em log, print ou mensagem de erro | Hub e Tareffas | `grep -rn "sso" --include="*.py" . \| grep -i "log\|print"` sem o valor do bilhete | LADO HUB: o grep devolve 8 linhas, todas falso positivo (a palavra "logado", cabeçalhos de prova, e o comentário de `app.py:473` dizendo que o bilhete não entra). Nenhuma passa o bilhete a log ou print. Prova executável, mais forte que o grep: item 7b da `provas/prova_sso_f2.py` confere que o valor do bilhete emitido não aparece em nenhuma linha da tabela `acessos`. A nota exige também "grava QUEM gerou e o IP": era o que faltava, e o IP passou a ser gravado nos 4 caminhos de entrada (item 12 da prova). LADO TAREFFAS: Fase 3 | parcial (Hub ok) |
| Padrao_Impersonacao_Segura | "Redireciona logo após consumir" | bilhete permanecer na barra de endereço | frontend | após entrar, `window.location.search` está vazio | | pendente |
| Padrao_IDOR | "Retornar 403 em vez de 404 quando não é dono: confirma que o recurso existe" | 403 na recusa do SSO | rota de consumo | resposta de recusa é 404 | | pendente |
| Forca_Bruta_Login | "Mensagem de erro é única: nunca dizer se foi email ou senha que errou" | dizer "usuário não cadastrado" ou "usuário bloqueado" | rota de consumo | os três casos devolvem texto idêntico | | pendente |
| Forca_Bruta_Login | "Toda tentativa, sucesso ou falha, é registrada" | consumo sem rastro | rota de consumo | linha na tabela de tentativas após sucesso e após falha | | pendente |
| Vazamento_de_Chaves | "Toda chave, senha, token ou URL sensível vai em variável de ambiente" | chave do SSO literal no código | Hub e Tareffas | `grep -rn "ZOARIA_SSO_SECRET" --include="*.py" .` só acha leitura de ambiente | LADO HUB: 4 linhas, nenhuma com valor. `config.py:34` é `os.environ.get("ZOARIA_SSO_SECRET", "").strip()`; `sso.py:94` é comentário; `provas/prova_sso_f2.py:7` é docstring e `:28` define chave de teste no ambiente da própria prova. O Hub não tinha `.env.example` e passou a ter, com as 15 variáveis do código e nenhum valor real. LADO TAREFFAS: Fase 3 | parcial (Hub ok) |
| CSRF_Cookies_Headers | CSRF em todo POST, com rotas isentas declaradas explicitamente | rota de consumo sem estar na lista de isentas | Tareffas | a rota consta na lista de isentas, e as demais seguem exigindo token | | pendente |
| Timeout_de_Sessao | vida do cookie e inatividade são independentes | JWT mais longo por ter vindo do Hub | rota de consumo | `exp` do JWT do SSO igual ao do login por senha | | pendente |
| App_Online_Auth | "Tela de login" é item obrigatório do tipo | remover ou esconder o login por senha | Tareffas | entrar pela URL direta ainda pede e-mail e senha | | pendente |
| CLAUDE.md da vault (regra 1) | "Nunca use travessao (em-dash)" e acentuação completa no que o usuário lê | travessão em mensagem de tela, inclusive em JSX | frontend | `grep -rn "—" frontend/src` volta vazio | | pendente |
| Padrao_CLAUDE_MD_Projeto | "Todo projeto de código DEVE TER um CLAUDE.md na raiz" com o bloco que aponta para a vault | projeto seguir sem o arquivo | raiz do Tareffas | o arquivo existe e abre com o bloco padronizado | `ls -la CLAUDE.md` devolveu `-rw-r--r-- 9787 Aug 16 18:47 CLAUDE.md`; `head -6` mostra o título na linha 1 e o bloco `> Antes de TUDO: existe uma vault Obsidian em /Users/fabiomoura/ObsidianJovi/` nas linhas 3-6. Os 5 caminhos citados no bloco foram testados com `[ -f ]`: 5 de 5 existem | ok |

## Não coberto, e declarado

- `70_ESTILO/` não existe nesta cópia da vault. O eixo de voz e vocabulário
  proibido não foi varrido, então nenhuma linha acima alega conformidade com ele.
