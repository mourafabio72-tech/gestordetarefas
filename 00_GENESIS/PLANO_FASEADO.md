# Plano faseado: SSO do Hub Zoaria no Tareffas

**modo=interativo** (escolhido em 2026-08-16). Paro no fim de cada fase, mostro o
que ficou pronto e o que testar, e espero o ok antes de seguir. Não repergunto.

Objetivo em uma frase: quem clica no card do Tareffas dentro do Hub entra direto,
sem digitar senha de novo, e quem não tem cadastro lá recebe um aviso claro.

Dois repositórios: `aplicações/zoaria-hub` (emite) e `_deploy_gestortarefas` (consome).

## Como o bilhete funciona (decisão de arquitetura)

```
pessoa logada no Hub
   clica no card Tareffas
      /ir/<id> confere o acesso no banco (já faz isso hoje)
      gera bilhete: {email, nome, jti, exp 60s} assinado com ZOARIA_SSO_SECRET
      redireciona para https://gestordetarefas.zoaria.com.br/?sso=<bilhete>
         frontend vê ?sso= e chama POST /api/auth/sso
            backend valida assinatura, prazo e jti não usado
            marca o jti como usado ANTES de emitir qualquer coisa
            acha usuario por e-mail; barra se nao existe, bloqueado ou inativo
            devolve o MESMO JWT de sempre (8h)
         frontend guarda o token e limpa a URL
```

O bilhete carrega identidade, nunca permissão. Quem decide o que a pessoa faz
dentro do Tareffas continua sendo o Tareffas.

---

## Fase 0 : aprovação do plano
**Status:** done (aprovado sem ajustes em 2026-08-16)
**Aceite:** o usuário aprova ou pede ajuste. Nenhuma linha de código antes disso.

## Fase 1 : CLAUDE.md do projeto
**Status:** done (2026-08-16, 3 de 3 itens com evidência)
**Duração:** 20 minutos
**Rege:** `Padrao_CLAUDE_MD_Projeto`
**Depende de:** Fase 0

O Tareffas não tem CLAUDE.md. Enquanto não tiver, toda sessão futura reinventa
padrão de auth e segurança, e este plano vira letra morta na próxima conversa.

**Aceite:** existe `CLAUDE.md` na raiz, apontando para a vault, com uma seção de
convenções específicas (stack, mapa de pastas, variáveis de ambiente, o modelo
de grupo e overrides). Não duplica regra que já vive na vault.

## Fase 2 : Hub emite o bilhete
**Status:** done (2026-08-16, 6 de 6 itens com evidência)
**Duração:** 2 horas
**Rege:** `Padrao_Impersonacao_Segura`, `Vazamento_de_Chaves`, `CSRF_Cookies_Headers`
**Depende de:** Fase 1, e dos dois commits do Hub estarem em produção
**Repositório:** `aplicações/zoaria-hub`

Segurança não é fase separada aqui: ela nasce junto com a superfície que cria.

- `ZOARIA_SSO_SECRET` por variável de ambiente, nunca no código, com `.env.example` sem valor
- Apps que participam do SSO marcados no catálogo (uma coluna, não uma tela nova)
- `/ir/<id>` gera o bilhete só para app marcado, e só depois da guarda de acesso que já existe
- Bilhete com `exp` de 60 segundos e `jti` aleatório de `secrets.token_urlsafe`
- Log registra quem entrou em qual app; o bilhete **nunca** entra no log

**Aceite:** clicar no card gera URL com `?sso=`; o bilhete decodifica com a chave
certa e falha com chave errada; app não marcado continua redirecionando puro.

## Fase 3 : Tareffas consome o bilhete
**Status:** done (2026-08-16, 12 de 12 itens com evidência, 25 checagens verdes)
**Duração:** 4 horas
**Rege:** `Padrao_Impersonacao_Segura`, `Padrao_IDOR`, `Forca_Bruta_Login`, `Timeout_de_Sessao`, `Padrao_Validacao_de_Input` (ler antes)
**Depende de:** Fase 2
**Repositório:** `_deploy_gestortarefas`

- Tabela `sso_bilhetes_usados` (jti, usado_em, ip), com limpeza do que passou do prazo
- `POST /api/auth/sso`: recusa bilhete acima do tamanho esperado **antes** de tocar o banco
- Marca o jti como usado **antes** de emitir o JWT, com `AND usado=0` e conferência das linhas afetadas
- Inexistente, expirado, já usado e assinatura inválida devolvem **a mesma** resposta
- Usuário não encontrado, bloqueado ou inativo: mesma mensagem única, sem dizer qual dos três
- Tentativas registradas por IP, com limite, igual ao login por senha
- O JWT emitido é o mesmo de sempre, com a mesma validade. Entrar pelo Hub não dá sessão mais longa
- Rota isenta de CSRF por ser entrada externa, declarada explicitamente

**Aceite:** as 9 provas do `CONFORMIDADE_VAULT.md` passam, incluindo a de corrida
(mesmo bilhete em duas requisições simultâneas: só uma entra).

## Fase 4 : o frontend entra sozinho
**Status:** done (2026-08-17). Código feito em 2026-08-16, 4 de 4 itens com
evidência, mais 1 achado da autoverificação, e 7 casos verdes em
`frontend/provas/prova_sso_f4.js`. Ficou aberta por uma linha da matriz que não
era desta fase (o travessão de 46 ocorrências em código anterior), e essa linha
fechou na Fase 6.
**Duração:** 1 hora
**Rege:** `Padrao_Impersonacao_Segura` (redirecionar logo após consumir)
**Depende de:** Fase 3

- `AuthContext` vê `?sso=` na URL quando não há token guardado, troca pelo JWT e segue
- Limpa a URL com `history.replaceState` logo depois, para o bilhete não ficar na barra nem no histórico
- Falhou: cai na tela de login com aviso legível, em português com acentuação completa
- Quem já tem sessão aberta não é derrubado por um bilhete que chega

**Aceite:** entrar pelo card do Hub abre o Tareffas logado, e a barra de endereço
não mostra mais o bilhete. Entrar direto pela URL continua pedindo senha.

## Fase 5 : entrega e validação
**Status:** done (2026-08-17). Funciona em produção desde 2026-08-16, com os três
casos de teste real conferidos no ar e captura de tela nos dois de recusa. O
quinto item era a matriz sem linha pendente, e fechou junto com a Fase 6.
**Duração:** 1 hora
**Depende de:** Fase 4

## Fase 6 : faxina de travessão no frontend (decidida em 2026-08-16)
**Status:** done (2026-08-17, 3 de 3 itens com evidência, mais os 7 casos de
backend que a autoverificação trouxe por causa raiz)
**Duração:** 40 minutos
**Rege:** `CLAUDE.md` da vault (regra 1), `Revisao_Professor_Pasquale`
**Depende de:** Fase 5

Nasceu do achado da Fase 1, confirmado na Fase 4: `grep -ro "—" frontend/src`
devolve 46 ocorrências em 13 arquivos, todas em código anterior a este trabalho.
Vira fase própria em vez de entrar de carona no deploy do SSO: é texto que o
usuário lê em 13 telas, e merece revisão de língua própria, não um `sed`.

- Trocar os 46 travessões por vírgula, dois pontos ou parêntese, conforme a frase
- Conferir de quebra acentuação e concordância no mesmo texto tocado
- `grep -rn "—" frontend/src` volta vazio, e a linha da matriz fecha

**Aceite:** a linha "CLAUDE.md da vault (regra 1)" do `CONFORMIDADE_VAULT.md`
passa a `ok` com a saída colada, e nenhuma tela mudou de sentido.

- Variáveis nos dois serviços do EasyPanel, mesma chave dos dois lados
- Teste com três pessoas reais: uma com cadastro, uma sem, uma bloqueada
- `CONFORMIDADE_VAULT.md` com evidência colada em cada linha
- Mapa Graphify gerado, se o usuário aceitar instalar

**Aceite:** funciona em produção pelo caminho real, e o login por senha continua
funcionando para quem entra direto.

## Fase 7 : fechar a porta da frente (decidida em 2026-08-17)
**Status:** pending
**Duração:** 3 horas
**Rege:** `Forca_Bruta_Login`, `CSRF_Cookies_Headers` (a parte de headers, que não
depende de cookie), `App_Online_Auth`
**Depende de:** Fase 6
**Repositório:** `_deploy_gestortarefas`

Nasceu de três achados que a Fase 6 encontrou de passagem, e o valor está no
cruzamento deles, não em cada um sozinho. O que amarra tudo é a única linha da
matriz que ficou `parcial`: **o login por e-mail e senha não registra nem limita
tentativa**, enquanto a rota de SSO limita. A porta de trás ficou mais dura que a
porta da frente.

- Ligar `registrar_tentativa` e `falhas_recentes` no login por senha
  (`routes/auth.py:28-40`), usando a coluna `origem` da tabela `login_tentativas`
  que já nasceu genérica na Fase 3 exatamente para isso. É a chamada de duas
  linhas que ficou pendente lá, e o limite tem de ser o mesmo do SSO: 5 falhas em
  15 minutos (`seguranca.py:24-25`)
- Trocar `allow_origins=["*"]` por lista explícita de origens
  (`main.py:21-27`). Hoje qualquer site pode chamar a API do navegador de quem o
  visita. Sozinho é fraco, porque o token vai em header do `localStorage` e site
  terceiro não lê isso, mas cruzado com o item acima significa força bruta
  disparada do navegador de visitantes de qualquer site, sem tocar no seu domínio.
  `allow_credentials=True` com `*` é configuração inválida que o Starlette
  contorna ecoando a origem, o que é pior que o que parece estar escrito
- Headers de segurança em toda resposta: `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `HSTS` e CSP. Hoje **não existe nenhum**,
  nem no nginx que serve o React (`frontend/nginx.conf`, 19 linhas, só `location /`
  e `location /api`) nem no backend. O Hub já tem isso desde o commit de perfis; o
  Tareffas não
- Conferir se o serviço backend tem domínio próprio no EasyPanel. Se tiver, o
  `/docs` e o `/openapi.json` estão públicos e entregam o mapa inteiro da API a
  quem pedir, e aí `docs_url=None` fora de desenvolvimento entra nesta fase. Pelo
  repositório não se decide: o nginx só proxia `/api`, então isso é pergunta de
  painel, não de código

**Aceite:** o login por senha registra e limita igual ao SSO, provado por teste que
erra a senha 6 vezes e recebe 429 na sexta; a API recusa origem não listada,
provado por requisição com `Origin` de outro domínio; e os headers aparecem na
resposta, provados por `curl -I`. Cada um com uma linha própria na matriz.

**Fora desta fase, e declarado:** os 32 travessões que sobram em comentário e
docstring interna de `backend/app`. Não são lidos por nenhum usuário por nenhum
caminho, provado por AST e pelo OpenAPI zerados na Fase 6.

---

## Fora de escopo (cortado pela escada)

| Cortado | Gatilho que faz voltar |
|---|---|
| Criar usuário automaticamente no Tareffas | decisão 2 do usuário foi barrar. Volta se o cadastro manual virar gargalo |
| O Hub definir grupo e permissões no Tareffas | decisão 3 foi o Tareffas mandar. Volta se surgir um terceiro app com o mesmo problema e a tradução virar regra comum |
| Tela de administração do SSO no Hub | uma coluna no catálogo resolve. Volta quando houver muitos apps com regras diferentes |
| Logout único (sair do Hub derruba os satélites) | ninguém pediu, e exige o Hub avisar cada satélite. Volta se virar exigência de auditoria |
| Refresh token e sessão longa | o JWT de 8 horas já existe e resolve. Volta se o pessoal reclamar de cair no meio do expediente |
| SSO no XmlHub | decisão firmada é login próprio lá. Volta se você mudar de ideia |
| Migrar o Tareffas para login só pelo Hub | o login próprio é a rede de segurança se o Hub cair |

## Riscos declarados

1. **O bilhete vai na URL.** É inerente a link compartilhável, e a nota de
   impersonação diz isso na cara. O que fecha: 60 segundos, uso único, e a URL
   ser limpa logo após consumir. Não fecha 100%, e isso está escrito de propósito.
2. **Chave compartilhada entre dois apps.** Se vazar, alguém emite bilhete para
   qualquer e-mail. Por isso é chave própria do SSO, e não a `SECRET_KEY` de nenhum
   dos dois. Trocar a chave derruba só o SSO, não as sessões.
3. **E-mail como chave de identidade.** Se alguém troca o e-mail no Hub para o de
   outra pessoa que existe no Tareffas, entra como ela. Mitiga: só admin edita
   e-mail no Hub, e o log registra a entrada. Vale conferir essa guarda na Fase 2.
