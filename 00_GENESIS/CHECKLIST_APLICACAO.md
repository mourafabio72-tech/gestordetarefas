# Checklist de aplicação

Regra: só marcar `[x]` com evidência apontável (arquivo e linha, ou saída de teste
colada). Item marcado sem evidência é item não feito.

**Decisões que valem para tudo:**

```
Confiança:    bilhete curto assinado na URL, gerado pelo /ir do Hub
Sem cadastro: barra e avisa, nada é criado automaticamente
Papel:        o Tareffas manda; o Hub só diz quem é a pessoa
Identidade:   casamento por e-mail (usuarios.email é único)
```

## Fase 1 : CLAUDE.md do projeto

- [x] `CLAUDE.md` na raiz do Tareffas, com o bloco que aponta para a vault
      (`Padrao_CLAUDE_MD_Projeto`)
      EVIDÊNCIA: `CLAUDE.md:1-21`. Título na linha 1, bloco `> Antes de TUDO`
      apontando `/Users/fabiomoura/ObsidianJovi/` nas linhas 3-6, e a lista dos 5
      arquivos obrigatórios nas linhas 10-14. Os 5 caminhos foram testados um a um
      com `[ -f ]` e todos existem (saída: 6x `ok`, nenhum `FALTA`). Divergência
      declarada: a nota escreve `D:\Obsidian\Jovi\_MAPA_CHAVES.md` na raiz, mas
      nesta cópia o arquivo está em `00A_MAPAS/_MAPA_CHAVES.md`. Usado o caminho
      real, porque caminho que não abre não é ponteiro.
- [x] Seção "convenções específicas" com stack, mapa de pastas, variáveis de
      ambiente e o modelo de grupo mais overrides JSON
      EVIDÊNCIA: `CLAUDE.md:78-183`. Stack em tabela de 4 linhas (conferida contra
      `backend/requirements.txt`: fastapi 0.104.1, sqlalchemy 2.0.23,
      python-jose 3.3.0, bcrypt 4.0.1, apscheduler 3.10.4). Mapa de pastas conferido
      por contagem real: 15 routers em `main.py:29-43`, 11 tabelas em `models.py`
      (`grep -n __tablename__`), 17 páginas em `frontend/src/pages`. Env vars saíram
      de varredura do código (`grep -rhoE "os\.(getenv|environ\.get)"`, 27 nomes)
      mais `VITE_HUB_URL` em `Layout.jsx:27`. Modelo de grupo descrito a partir de
      `permissoes.py:20-131` e `models.py:45-54`.
- [x] NÃO repete regra de auth, segurança ou visual que já vive na vault
      (`Padrao_CLAUDE_MD_Projeto`: "mover pra vault e deixar ponteiro")
      EVIDÊNCIA: o arquivo não contém regra de CSRF, força bruta, headers, timeout,
      hashing nem token visual. Onde o assunto aparece, aparece como ponteiro
      (`CLAUDE.md:8-14` e a tabela de padrões de UI em `CLAUDE.md:22-36`, que manda
      ler a nota em vez de descrever o padrão). O que está descrito é a matriz
      própria deste projeto (`permissoes.py`), que é quirk de projeto e o próprio
      checklist exige no item acima.

## Fase 2 : Hub emite o bilhete

- [x] `ZOARIA_SSO_SECRET` lida de variável de ambiente, com `.env.example` sem valor real
      PROIBIDO: chave literal em `config.py` ou em qualquer template
      PROVA: `grep -rn "ZOARIA_SSO_SECRET" --include="*.py" .` só acha `os.environ.get`
      (`Vazamento_de_Chaves`)
      EVIDÊNCIA: o grep devolve 4 linhas e nenhuma é valor literal: `config.py:34`
      (`os.environ.get("ZOARIA_SSO_SECRET", "").strip()`), `sso.py:94` (comentário),
      `provas/prova_sso_f2.py:7` (docstring) e `:28` (define chave de teste no
      ambiente da prova). O Hub não tinha `.env.example`; foi criado com as 15
      variáveis levantadas por varredura do código, todas sem valor.
- [x] Coluna no catálogo marcando qual app participa do SSO; app não marcado
      continua com redirecionamento simples
      EVIDÊNCIA: `schema.sql:32` (`sso INTEGER NOT NULL DEFAULT 0`), migração
      idempotente em `db.py:85-87`, gravação em `app.py:952-970`, caixa na tela em
      `templates/admin_app_form.html:33-43` e marca na listagem em
      `templates/admin_apps.html:16`. Itens 2 e 6b da `provas/prova_sso_f2.py`:
      app sem marca redireciona puro, e a tela recusa marcar destino interno.
      Nenhum app nasce marcado, o Tareffas inclusive: ligar é ato consciente na
      tela, depois da Fase 3 estar no ar.
- [x] Bilhete com `exp` de 60 segundos e `jti` de `secrets.token_urlsafe`
      (`Padrao_Impersonacao_Segura`: validade curta gravada, token por gerador criptográfico)
      EVIDÊNCIA: `sso.py:36` (`VALIDADE_SEGUNDOS = 60`) e `sso.py:59-64`, que grava
      `jti` de `secrets.token_urlsafe(16)` e `exp` DENTRO do bilhete, além do
      timestamp que o itsdangerous já assina. O prazo é decisão de quem emite, e
      não do consumidor que escolhe o `max_age` na leitura. `python3 sso.py`
      devolve PROVA OK com 8 casos, entre eles exp vencido e jti que varia.
- [x] Bilhete gerado só DEPOIS da guarda de acesso que o `/ir` já faz hoje
      EVIDÊNCIA: `app.py:434-477`. A guarda `acessos_efetivos` e o `abort(403)`
      estão nas linhas 451-454; o `gerar_bilhete` só aparece na linha 475, depois
      do registro do acesso. Item 5 da prova: quem não tem acesso recebe 403 e
      nada é emitido.
- [x] O bilhete NUNCA entra em log; registra-se quem entrou em qual app
      PROVA: `grep -rn "bilhete\|sso_token" app.py | grep -i "log\|print"` volta vazio
      (`Padrao_Impersonacao_Segura`: "O token NUNCA entra em log")
      EVIDÊNCIA: o grep alargado (`"bilhete\|sso"` cruzado com `log|print`) devolve
      só falsos positivos: a palavra "logado" dentro de outras frases e o próprio
      comentário de `app.py:473` que diz que o bilhete não entra. Prova executável
      vale mais que o grep: item 7b confere que o valor do bilhete emitido não
      aparece em nenhuma linha da tabela `acessos`.
      A NOTA pedia mais do que este item: "grava QUEM gerou e o IP". A tabela
      `acessos` não tinha IP. Corrigido: coluna em `schema.sql:63`, migração em
      `db.py:89-94`, e gravação nos QUATRO caminhos de entrada (`app.py:167`
      login, `:209` 2FA, `:253` primeiro 2FA, `:458` entrada em app). Item 12 da
      prova confere que grava o IP do cliente e não o do proxy.
- [x] Só admin edita e-mail de usuário no Hub (conferir se já é assim; se não for, virar item)
      EVIDÊNCIA: NÃO era assim, e virou item. `admin_usuario_form` é
      `@gestor_required` (`app.py:578`, decorator da rota que abre em `app.py:580`),
      e até aqui o gestor gravava `email` livre, direto do formulário. Como o e-mail é a chave de identidade do
      outro lado e o nível de lá não é decidido por este Hub, isso era escalada
      por cadastro: bastava apontar o e-mail para o do administrador do satélite
      e definir a senha aqui. Fechado em `app.py:616-626`, na criação E na edição,
      com guarda de servidor (o `disabled` do template é conforto, não guarda).
      Itens 10 e 10b da prova: gestor não troca nem por POST forjado, admin troca.
      Achado extra da autoverificação: `usuarios.email` não tem UNIQUE, então duas
      contas daqui virariam a MESMA pessoa lá. Fechado por validação de aplicação
      em `app.py:663-676` (índice único derrubaria o deploy se produção já tiver
      repetido). Itens 11 e 11b da prova.

**Fechamento da fase:** `provas/prova_sso_f2.py` com 18 checagens verdes,
`provas/prova_migracao_sso_f2.py` provando o banco antigo, `python3 sso.py` com
8 casos, e as 5 provas anteriores mais `security.py` sem regressão.
Balanço da escada: `grep -rn "escada:"` no Hub devolve 1 marcador, pré-existente
de `app.py:497`. Nenhum corte novo nesta fase.

## Fase 3 : Tareffas consome o bilhete

- [x] Ler `Padrao_Validacao_de_Input` e `Padrao_Logging_Estruturado` ANTES de escrever a rota
      EVIDÊNCIA: bloco FONTES LIDAS da sessão, com as duas integrais (197 e 210
      linhas, conferidas por `wc -l` antes do Read) mais as outras 6 notas do
      LASTRO. O que veio de cada uma: da validação, o teto de comprimento antes
      da regra de negócio (`routes/auth.py:114-117`) e o valor padrão no schema
      (`:63-66`); do logging, os campos fixos e a lista do que nunca entra em log
      (`seguranca.py:57-66`).
- [x] Tabela `sso_bilhetes_usados` (jti, usado_em, ip) com limpeza do que venceu
      EVIDÊNCIA: `models.py:296-311`, com `jti` como CHAVE PRIMÁRIA (é ela que dá
      a trava) e índice em `usado_em`. Limpeza em `routes/auth.py:168-175`,
      retenção de 7 dias (`:26`), que também varre `login_tentativas` (30 dias,
      `seguranca.py:105-110`). Item 19 da prova: linha fora da retenção some na
      entrada seguinte. Tabela nova nasce pelo `Base.metadata.create_all` de
      `main.py:8`; o `migrate()` continua sendo só para coluna nova.
- [x] Recusa bilhete acima do tamanho esperado ANTES de consultar o banco
      (`Padrao_Impersonacao_Segura`, bloco Consumo)
      EVIDÊNCIA: `routes/auth.py:114-117`, primeira coisa depois de ler o IP, e
      `sso.py:58` no leitor. Item 9 da prova não confia na leitura do código: um
      ouvinte de `before_cursor_execute` conta as queries e exige ZERO.
- [x] Marca o jti como usado ANTES de emitir o JWT
      PROIBIDO: emitir o token e marcar depois
      (`Padrao_Impersonacao_Segura`: "Marcar como usado ANTES do login, e nunca depois")
      EVIDÊNCIA: `routes/auth.py:135-137` (marca) vem antes de `:161` (emite), com
      a busca do usuário no meio. Item 10 da prova: bilhete de e-mail sem cadastro
      recusa a entrada E deixa o jti gravado, o que só é possível se a marcação
      acontece antes de existir sessão.
- [x] `UPDATE ... WHERE jti=%s AND usado=0` **e o código confere as linhas afetadas**
      PROVA: teste de corrida com duas requisições simultâneas, só uma entra
      (`Padrao_Impersonacao_Segura`, cenário 6)
      EVIDÊNCIA: `routes/auth.py:80-96`. DIVERGÊNCIA DE FORMA, declarada: a nota
      descreve `UPDATE ... AND usado=0` porque no caso dela a linha do token já
      existe na tabela. Aqui o consumidor não sabe do bilhete até ele chegar, e o
      equivalente é `INSERT ... ON CONFLICT (jti) DO NOTHING` com `res.rowcount == 1`
      (`:96`). A propriedade exigida é a mesma e está atendida: quem decide o
      vencedor é o banco, e o código obedece ao veredito em vez de seguir em
      frente. Item 11 da prova dispara duas requisições de verdade com
      `threading.Barrier`, e exige `[200, 404]`.
      PROVA DE QUE A PROVA TEM DENTE: trocando `:96` por `return True`, a prova
      falha nos itens 4, 5, 6 e 11. Restaurado depois, 25 verdes de novo.
- [x] Inexistente, expirado, já usado e assinatura inválida devolvem a MESMA resposta
      (`Padrao_Impersonacao_Segura`: "Mensagem diferente para expirado, usado e inexistente vira oráculo")
      EVIDÊNCIA: uma constante só, `routes/auth.py:22`, usada em todos os caminhos
      de recusa (`:77` e `:117`, os dois únicos). O motivo real vai só para o log. Item 6 da
      prova compara o corpo das NOVE recusas (lixo, expirado, já usado, chave
      errada, salt alheio, sem cadastro, bloqueada, inativa, convite pendente) e
      exige um único texto distinto entre elas.
- [x] Usuário ausente, bloqueado ou inativo: mesma mensagem única
      (`Forca_Bruta_Login` regra 3: "Mensagem de erro é única")
      EVIDÊNCIA: `routes/auth.py:146-157`, quatro casos e um só retorno. Entrou um
      quarto que o plano não previa: `ativado is False` (`:156-157`), que é convite de
      primeiro acesso pendente. Quem nunca definiu a própria senha não passa a ter
      conta ativa por ter clicado no card do Hub. Itens 7 e 8 da prova.
- [x] Recusa devolve 404, nunca 403
      (`Padrao_IDOR`: "Retornar 403 em vez de 404 quando não é dono: confirma que o recurso existe")
      EVIDÊNCIA: `routes/auth.py:77` e `:117`, os dois únicos pontos de recusa,
      ambos 404. Item 5 da prova varre as nove respostas.
- [x] Tentativas registradas e limitadas por IP, como no login por senha
      (`Forca_Bruta_Login` regra 2: "Toda tentativa, sucesso ou falha, é registrada")
      EVIDÊNCIA: tabela `login_tentativas` em `models.py:314-321`, gravação em
      `seguranca.py:68-78`, contagem da janela em `:80-103` e o corte em
      `routes/auth.py:119-125` (5 falhas em 15 minutos, `seguranca.py:24-25`).
      Itens 12, 13, 14 e 15 da prova, incluindo o 15, que confere que o bloqueio
      é do IP que errou e não do sistema inteiro.
      CORREÇÃO DO ENUNCIADO: "como no login por senha" não era cumprível, porque
      o login por senha deste projeto NÃO registra nem limita nada
      (`routes/auth.py:28-40`, e `grep -rni "tentativa\|rate_limit"` no backend
      voltava vazio antes desta fase). A tabela e os helpers nasceram genéricos,
      com coluna `origem`, para o login por senha entrar depois numa chamada de
      duas linhas. Ligar lá é decisão do usuário, e está na lista de pendências.
- [x] O JWT emitido tem a MESMA validade do login normal (8 horas)
      PROIBIDO: sessão mais longa por ter entrado pelo Hub
      (`Timeout_de_Sessao`)
      EVIDÊNCIA: `routes/auth.py:161` chama `create_access_token(data={"sub": ...})`
      sem `expires_delta`, exatamente como a rota de senha em `:39`. O padrão é
      `ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8` em `auth.py:16`. Item 2 da prova não
      confia nisso: decodifica os dois JWTs e compara o `exp`.
- [x] Rota de consumo declarada como isenta de CSRF, por ser entrada externa
      (`CSRF_Cookies_Headers`, seção "Rotas isentas")
      EVIDÊNCIA: NÃO HÁ LISTA DE ISENTAS NESTE PROJETO, e o motivo está escrito na
      docstring da rota (`routes/auth.py:106-110`). `grep -rni "csrf" backend/app`
      volta vazio: o Tareffas não usa cookie de sessão. O token vai em
      `Authorization: Bearer` a partir do `localStorage`
      (`frontend/src/contexts/AuthContext.jsx:11,32`), e cabeçalho não é anexado
      sozinho pelo navegador em pedido de outro site. A nota rege app com cookie
      de sessão; aqui a superfície não existe. Declarado em vez de fingir cumprido.
- [x] Log de entrada com e-mail, IP e resultado; bilhete fora do log
      EVIDÊNCIA: `seguranca.py:57-66` (uma linha JSON por evento, com timestamp,
      nível e campos fixos) e os três eventos em `routes/auth.py:116`, `:121`,
      `:75` e `:163`: `SSO_OK`, `SSO_RECUSADO` (com o motivo real, que não vai
      para o usuário) e `SSO_BLOQUEADO`. O bilhete nunca é passado a `log_event`:
      `grep -n "log_event\|print" routes/auth.py | grep -i "bilhete\|body\."`
      volta vazio. Item 16 da prova é mais forte que o grep: varre as duas tabelas
      de rastro e exige que nenhum pedaço do bilhete apareça.

**Achados da autoverificação (três furos meus, fechados antes de fechar a fase):**

- [x] `X-Forwarded-For` era lido do começo da lista, e o nginx ANEXA em vez de
      substituir (`frontend/nginx.conf:14`, `$proxy_add_x_forwarded_for`). Quem
      mandasse `X-Forwarded-For: 1.2.3.4` ganhava um IP novo a cada tentativa e
      passava por cima do limite de força bruta, além de sujar o rastro com IP
      inventado. Fechado em `seguranca.py:38-56`, que lê de trás para frente
      descontando os saltos nossos (`PROXIES_ANEXADOS = 1`, `:35`). Item 18a da
      prova manda uma cadeia forjada de três IPs e exige que o contado seja o
      real.
- [x] Comparação de e-mail era exata, e o Postgres diferencia maiúscula. Conta
      cadastrada como `Fulano@bps4.com.br` seria barrada por um bilhete com
      `fulano@bps4.com.br`, que é a mesma pessoa. Fechado em
      `routes/auth.py:146-151` com `func.lower` nos dois lados. O efeito colateral
      veio junto: duas contas que só diferem por caixa tornam a identidade
      ambígua, e nesse caso NINGUÉM entra (`:147-148`), porque escolher uma seria
      escolher no escuro de quem é a sessão. Itens 18b e 18c da prova.
- [x] `SSORequest.bilhete` era obrigatório, e corpo sem o campo respondia 422 do
      pydantic, diferente das outras recusas. Fechado com valor padrão em
      `routes/auth.py:63-66`. Item 18d da prova compara o corpo com o da recusa
      por lixo.

**Fechamento da fase:** `provas/prova_sso_f3.py` com 25 checagens verdes (rota
real, SQLite temporário, sem deixar arquivo), `python app/sso.py` com 7 casos, e
o app inteiro subindo com a rota registrada (`/api/auth/sso` aparece em
`app.routes`). Balanço da escada: `grep -rn "escada:"` no backend devolve 0
marcadores; nenhum corte deliberado nesta fase.

## Fase 4 : frontend

- [x] `AuthContext` troca `?sso=` por JWT quando não há token guardado
      EVIDÊNCIA: `contexts/AuthContext.jsx:27` colhe o bilhete, `:37-40` só entra
      por ele quando `localStorage.getItem('token')` voltou vazio em `:28`, e
      `entrarPorBilhete` (`:59-71`) chama `authAPI.sso`, guarda o `access_token` e
      carrega o usuário. A chamada em `services/api.js:47` usa a instância
      `apiPublico` de propósito: a recusa da rota é 404 e o limite por IP é 429,
      e nenhum dos dois pode cair no interceptor de 401 (`api.js:18-27`), que
      apaga o token e redireciona.
      Enquanto o consumo corre, `loading` continua `true`, então o `PrivateRoute`
      (`App.jsx:25-27`) segura a tela em vez de piscar o login.
- [x] `history.replaceState` limpa a URL logo após consumir
      (`Padrao_Impersonacao_Segura`: "redirecionar logo após consumir, para o token
      não ficar na barra nem no histórico")
      EVIDÊNCIA: `contexts/bilhete.js:26-34`. MAIS FORTE QUE O ITEM PEDIA, e
      declarado: a limpeza acontece ANTES da chamada ao servidor, e não depois do
      consumo dar certo. Enquanto o bilhete estiver na barra ele vaza pelo
      histórico, pelo `Referer` da página seguinte e por captura de tela, e a
      recusa não é motivo para deixá-lo lá. O que se perde numa falha é um
      bilhete de 60 segundos e uso único.
      Item 3 da `frontend/provas/prova_sso_f4.js`: `ok 3. a URL é limpa e o
      bilhete some do endereço`. Itens 4 e 7 conferem que a limpeza não leva
      junto outros parâmetros, o hash nem a rota.
      PROVA DE QUE A PROVA TEM DENTE: trocando `bilhete.js:34` por um comentário,
      a prova falha no item 3 (`expected: 1` de chamadas de `replaceState`).
      Restaurado, 7 verdes de novo.
- [x] Quem já está logado não é derrubado por um bilhete que chega
      EVIDÊNCIA: `contexts/AuthContext.jsx:30-35`. O ramo do token guardado vem
      ANTES do ramo do bilhete e faz `return`, então a sessão aberta segue por
      `loadUser()` e o bilhete não é consumido. A URL é limpa do mesmo jeito
      (`:27` roda antes dos dois ramos), porque bilhete na barra é vazamento
      mesmo quando ninguém o usa.
      Consequência aceita e registrada: quem está logado como uma pessoa e clica
      no card do Hub como outra continua na primeira sessão. É o que este item
      manda, e trocar de conta se faz por Sair.
      TRAVA EXTRA: `:24-25`. O `StrictMode` (`main.jsx:7`) monta duas vezes em
      desenvolvimento, e bilhete é de uso único: sem o `useRef`, a segunda
      montagem gastaria o mesmo bilhete e a pessoa veria o aviso de recusa depois
      de já ter entrado.
- [x] Mensagem de recusa em português com acentuação completa, legível para quem
      não é técnico (vault `CLAUDE.md` regra 1)
      PROIBIDO: travessão em qualquer texto, inclusive dentro de JSX
      EVIDÊNCIA: `contexts/AuthContext.jsx:11-12`, uma constante só
      (`AVISO_SSO`), usada nos dois caminhos de falha (`:64` e `:68`). Texto:
      "Não foi possível entrar pelo portal Zoaria. Entre com seu e-mail e senha,
      ou procure quem administra o sistema." Sem jargão, sem código de erro, e
      espelhando a recusa única do servidor: não diz se o problema foi o bilhete
      ou a conta.
      Aparece em `pages/Login.jsx:36-40`, em bloco âmbar separado do vermelho de
      erro de senha, e some quando a pessoa tenta entrar (`:15`, `limparAviso`).
      `grep -n "—"` nos cinco arquivos desta fase (`bilhete.js`, `AuthContext.jsx`,
      `Login.jsx`, `api.js`, `prova_sso_f4.js`): vazio.
- [x] Caminho triste achado na autoverificação: `loadUser` engole a própria falha
      e apaga o token (`AuthContext.jsx:48-56`). Um bilhete ACEITO cujo `/me`
      falhasse depois jogaria a pessoa no login sem uma palavra. Fechado em
      `:61-64`, que confere se o token sobreviveu e mostra o mesmo aviso se não.

**Fechamento da fase:** `node provas/prova_sso_f4.js` com 7 casos verdes, e
`npm run build` transformando 2276 módulos sem erro. Balanço da escada:
`grep -rn "escada:"` no frontend devolve 0 marcadores; nenhum corte deliberado
nesta fase.
PENDÊNCIA QUE NÃO É DESTA FASE, e por isso a matriz segue com uma linha aberta:
`grep -rn "—" frontend/src` acha 46 travessões em 13 arquivos pré-existentes.
Código novo nasce conforme a regra; a faxina do código velho é decisão do usuário.

## Fase 5 : entrega

- [x] Mesma chave nos dois serviços do EasyPanel
      EVIDÊNCIA: `ZOARIA_SSO_SECRET` criada pelo usuário nos dois serviços, com o
      mesmo valor, e deploy rodado nos dois (2026-08-16). A terceira condição, que
      não é do EasyPanel e é a que mais se esquece, também foi feita: o app
      Tareffas marcado como "Entrada direta" em `/admin/apps` do Hub. Prova de
      ponta a ponta abaixo: sem as três, o card não entraria.
- [x] Teste real: pessoa com cadastro entra; sem cadastro vê o aviso; bloqueada é barrada
      OS TRÊS CASOS FECHADOS em produção, 2026-08-16, com captura de tela nos dois
      de recusa. Identidade conferida antes de dar por bom: o usuário de teste no
      Hub é `mourafabio72@gmail.com` e a conta real do usuário no Tareffas é
      `fabio@bps4.com.br`, então o caso "sem cadastro" foi mesmo sem cadastro, e
      não um descasamento de e-mail fazendo os dois testes provarem a mesma coisa.
      RESSALVA DE PRECISÃO: a conta de teste foi criada sem senha, então era
      bloqueada E pendente na hora da recusa, e os dois casos barram
      (`routes/auth.py:152-157`). A recusa está certa; qual dos dois motivos
      disparou não se distingue de fora, porque a mensagem é única de propósito.
      O caminho feliz é o registro de `sso_no_ar`: o usuário entrou pelo card com
      a própria conta, no mesmo ambiente e no mesmo dia em que as outras duas
      foram barradas. Entrar um e recusar outros é a prova de que a rota
      discrimina, e não de que ela recusa todo mundo. O usuário clicou no
      card do Hub e entrou no Tareffas sem digitar senha ("funcionou", 2026-08-16),
      que é o aceite do PLANO_FASEADO para a Fase 4 e o primeiro dos três casos
      desta. Faltam os outros dois: e-mail sem cadastro no Tareffas, e conta
      bloqueada, os dois esperando o mesmo aviso âmbar e nunca a entrada.
      CASO 2 FECHADO (2026-08-16, captura de tela em produção): conta com acesso
      ao card no Hub e sem cadastro no Tareffas NÃO entrou, e a tela de login
      exibiu o aviso âmbar com o texto literal de `AuthContext.jsx:11-12`. A mesma
      captura prova de novo a URL limpa (`/login`, sem `?sso=`), e prova o bloco
      de `Login.jsx:36-40` renderizando de verdade, que era conferência visual e
      não sairia de grep nenhum. Falta só a conta bloqueada.
- [x] Login por e-mail e senha continua funcionando para quem entra pela URL direta
      EVIDÊNCIA: conferência em produção pelo usuário, 2026-08-16, em janela
      anônima do navegador: `https://gestordetarefas.zoaria.com.br` pediu e-mail e
      senha. A janela anônima é o que dá valor à prova: na janela normal ele tinha
      acabado de entrar pelo card, e o JWT de 8 horas no `localStorage` responderia
      pela sessão, o que provaria só que a sessão existia. Fecha o item obrigatório
      "Tela de login" do tipo `App_Online_Auth`: o SSO é caminho adicional, nunca
      substituto.
- [x] `CONFORMIDADE_VAULT.md` com evidência colada em cada linha
      EVIDÊNCIA: as 15 linhas da matriz estão preenchidas, e nenhuma segue
      pendente. Contagem por status: 13 `ok`, 1 `não se aplica` (CSRF, com o
      motivo escrito na docstring da rota) e 1 `parcial (SSO ok)` (força bruta:
      o login por senha continua sem registro e sem limite, e ligar lá é
      ampliação declarada, não item desta fase). A última que faltava era a do
      travessão, fechada pela Fase 6 abaixo.
- [x] Mapa Graphify gerado, se o usuário aceitar instalar
      EVIDÊNCIA: `graphify` instalado em `~/.local/bin/graphify` e mapa gerado na
      Fase 0 com `--code-only`: `graphify-out/` tem `GRAPH_REPORT.md`, `graph.json`,
      `graph.html` e `manifest.json`. 66 arquivos de código, 739 nós, 1694 arestas,
      40 comunidades. A pasta está no `.gitignore` por ser mapa gerado localmente.
      PENDENTE, e é decisão do usuário: `graphify claude install`, que escreve
      configuração do Claude Code nesta máquina, não foi rodado.

## Fase 6 : faxina de travessão

- [x] Trocar os 46 travessões por vírgula, dois pontos ou parêntese, conforme a frase
      (`Sem_Travessao`: "Nunca usar o caractere travessão em lugar nenhum", com a
      tabela de substituições; `Revisao_Professor_Pasquale` código E4)
      EVIDÊNCIA: 42 trechos reescritos em 13 arquivos de `frontend/src`, cobrindo
      os 46 caracteres (quatro linhas de `<option>` tinham travessão duplo
      emoldurando a opção nula). `git diff --stat` do frontend fecha em
      **42 inserções e 42 remoções**, simetria que prova que nenhuma linha foi
      criada nem removida: cada uma foi reescrita no lugar.
      As três formas usadas, decididas por leitura de cada frase e não por `sed`:
      (a) travessão que separa oração virou **dois pontos** quando o segundo
      trecho explica o primeiro (`Bloqueado: não loga e as tarefas dele somem.`,
      `Definitiva: reatribui tudo agora`, `IA: reforço do e-validador (OpenAI)`)
      ou **vírgula** quando é aposto (`(guardada, deixe vazio p/ manter)`,
      `Função, ex.: Assistente, Coordenadora, Sócio`);
      (b) travessão que emoldurava opção nula de `<select>` virou **parêntese**
      (`(não vinculada)`, `(sem responsável)`, `(escolher)`), que é o que a tabela
      de `Sem_Travessao` manda para o caso de moldura;
      (c) travessão que representava valor ausente em célula de tabela virou
      **hífen simples** (`{m.identificador || '-'}`), e não en-dash, porque o
      en-dash é aviso A2 do Pasquale.
      ÚNICA troca que acrescentou palavra, declarada: o `placeholder` de
      `Obrigacoes.jsx:653` era `Ex.: Empréstimo — Banco Itaú, conta 123` e virou
      `Ex.: Empréstimo do Banco Itaú, conta 123`. Dois pontos ali colidiria com o
      `Ex.:` da própria frase, e hífen num exemplo de texto livre lê pior que a
      preposição.
- [x] Conferir de quebra acentuação e concordância no mesmo texto tocado
      (`Revisao_Professor_Pasquale`, seção "O que só se prova lendo")
      EVIDÊNCIA: `git diff -U0` das 49 linhas lido integralmente, par a par.
      Nenhum ajuste de concordância foi necessário: as 42 trocas do frontend
      substituem um separador, e em nenhuma delas o travessão sustentava
      concordância verbal ou nominal. As 7 do backend estão no item abaixo, e
      três delas foram reescritas de fato, não só pontuadas (`... vinculados —
      foi inativada (não excluída)` virou `... vinculados, então foi inativada e
      não excluída`, que troca o parêntese por oração e lê melhor em voz ativa).
      Encoding conferido nos 13 arquivos do frontend com `file -I`: 13 de 13 em
      `charset=utf-8`, nenhum `iso-8859-1`. Mojibake: `grep -rlnP` do padrão
      `Ã|Â|â` seguido de continuação UTF-8 volta vazio em `frontend/src` e em
      `backend/app`. En-dash em `frontend/src`: vazio.
      O executor `scripts/pasquale.py` continua indisponível nesta cópia da vault
      (`ls scripts/` devolve só `atualizar_mapa.py`), então a entrega **não alega
      conformidade com o script**, só com a regra, e a parte de dicionário de
      acentuação que só o script cobre fica declarada como não verificada.
- [x] `grep -rn "—" frontend/src` volta vazio, e a linha da matriz fecha
      EVIDÊNCIA: o comando devolve saída vazia com exit code 1, contra as 46
      ocorrências em 13 arquivos medidas na Fase 4. Colado na linha do travessão
      da `CONFORMIDADE_VAULT.md`, que passou de `pendente (código anterior)` a
      `ok`. Regressão conferida: `node provas/prova_sso_f4.js` com os 7 casos
      verdes, `npm run build` transformando 2276 módulos sem erro (mesmo número
      da Fase 4), `backend/provas/prova_sso_f3.py` com as 25 checagens verdes no
      venv do projeto, e `python app/sso.py` com os 7 casos.

**Achado da autoverificação, e é causa raiz, não escopo novo:** a mesma frase que
eu limpei em `Tarefas.jsx:224` também é emitida pelo servidor, em
`backend/app/routes/tarefas.py:257`, como `detail` de um `HTTPException 403`. O
usuário lê as duas. Limpar só o lado do React deixaria o travessão saindo pelo
caminho do servidor, que é o "corrigir só o caminho reclamado deixa os irmãos
quebrados" do `Escada_Preguica_de_Codigo`, nota do próprio LASTRO. Varredura
completa do backend por texto lido pelo usuário (`detail=`, `"message"`, valor
devolvido para a tela) achou **7 casos**, todos fechados:

- [x] `routes/tarefas.py:257` (a frase gêmea da tela), `routes/usuarios.py:292`,
      `routes/empresas.py:224` e `routes/setores.py:86`, que são as mensagens de
      "tem vínculos, então foi inativado" que o front exibe direto ao usuário
- [x] `routes/obrigacoes.py:73`, `services/importador_cronograma.py:115` e `:203`,
      que devolvem o marcador de valor ausente para a célula da tabela
      EVIDÊNCIA: `grep -rn "—" backend/app` cruzado com `detail=|"message"|
      prazo_label|or "—"` volta vazio. Os 6 arquivos compilam
      (`python -m py_compile`, 6 de 6) e o app inteiro sobe com as 5 rotas
      tocadas presentes em `app.routes` (68 rotas no total), usando
      `DATABASE_URL` de SQLite porque o host `db` do Compose não existe nesta
      máquina.
      EIXO ADVERSARIAL que autorizou trocar o glifo: `grep` por comparação com o
      caractere (`== '—'`, `=== '—'` e as variantes com aspas duplas) volta vazio
      em `frontend/src` e em `backend/app`. Ninguém compara contra o marcador de
      vazio, então trocá-lo por hífen não muda lógica nenhuma, só o que se lê.

**SEGUNDA RODADA no backend, autorizada pelo usuário, e ela existe porque a minha
primeira varredura estava fraca.** Eu tinha afirmado que sobravam 44 travessões
"todos em comentário e docstring", e que só 5 chegavam ao usuário. Errado nos dois
números, e o erro é de método: eu grepava por **nome de chave** (`detail=`,
`"message"`, `prazo_label`), e nome de chave é adivinhação. Uma string exibida na
tela sob a chave `"motivo"` passou por baixo, com o comentário da linha acima
dizendo literalmente "motivo curto para a UI". Refeita por **AST**, procurando
toda constante `str` com travessão e excluindo docstring de módulo, classe e
função, apareceram **7 strings de dado**, não uma. Afirmar ausência com varredura
fraca é o furo da regra 4 da `Leitura_e_Retencao_de_Notas`, e eu cometi ele com um
grep que parecia específico.

- [x] 7 strings de dado, e duas são piores que tela
      EVIDÊNCIA: `whatsapp.py:188` era a **linha de assunto do e-mail** que sai
      para o cliente (`[Tareffas] título — empresa`), e `whatsapp.py:62` é o prazo
      mostrado na mensagem de WhatsApp quando a tarefa não tem data. E-mail
      transacional e WhatsApp automático estão nomeados no gatilho do
      `Revisao_Professor_Pasquale` e na lista do `Sem_Travessao`: eram os menos
      discutíveis de todos, e foram os últimos que eu achei. Os outros cinco:
      `permissoes.py:85`, que é a frase **gêmea** de `frontend/src/permissoes.js:80`
      já limpa (a segunda frase gêmea desta fase); `modelos.py:114`, o motivo
      exibido na tela do e-validador; e três avisos de importação que o front
      lista na tela de resultado (`importador_empresas.py:136`,
      `importador_resp_setor.py:99`, `importador_usuarios.py:187`).
- [x] 5 docstrings de rota
      EVIDÊNCIA: `modelos.py:69`, `obrigacoes.py:29` e `:208`, `tarefas.py:127` e
      `:370`. Docstring de rota no FastAPI vira a descrição do endpoint no
      OpenAPI, então é texto lido por gente e não comentário. A prova é direta e
      melhor que grep de arquivo: o app sobe e `str(app.openapi())` tem **zero**
      travessões, o que cobre de uma vez toda docstring de rota e todo schema que
      entra na documentação. RESSALVA DE ALCANCE, para o item não alegar mais do
      que vale: o `/docs` **não sai pelo domínio público hoje**, porque o nginx do
      frontend só proxia `/api` (`frontend/nginx.conf:12`). Se o serviço backend
      tiver domínio próprio no EasyPanel, sai, e isso não se vê do repositório.
- [x] Prova de fechamento das duas classes, por comando e não por leitura
      EVIDÊNCIA: a varredura por AST devolve **0** strings de dado com travessão
      em `backend/app`, e o OpenAPI devolve **0**. Os 6 arquivos tocados compilam
      (`py_compile`, 6 de 6) e o app sobe com 92 rotas. Regressão: 25 checagens da
      `prova_sso_f3.py` e 7 casos do `app/sso.py`, verdes.

**PENDÊNCIA DECLARADA, com o número corrigido:** sobram **32 travessões em 13
arquivos** de `backend/app`, e agora a classificação está provada, não suposta:
AST devolve zero string de dado e o OpenAPI devolve zero, então o que resta é
comentário com `#` e docstring de model, de schema e de função auxiliar, que
nenhum usuário lê por nenhum caminho. `Sem_Travessao` diz "qualquer arquivo" e
inclui comentário, então a regra os alcança e isso fica escrito em vez de
disfarçado. Decisão do usuário: ficam.

**Fechamento da fase:** aceite do `PLANO_FASEADO` atendido (`grep` vazio e a linha
da matriz em `ok`), nenhuma tela mudou de sentido, e as quatro provas do projeto
seguem verdes. Balanço da escada: `grep -rn "escada:"` em `frontend/src` e
`backend/app` devolve 0 marcadores; nenhum corte deliberado nesta fase.

## Fase 7 : fechar a porta da frente

- [x] Ligar `registrar_tentativa` e `falhas_recentes` no login por e-mail e senha,
      com o MESMO limite do SSO
      (`Forca_Bruta_Login` regras 1 e 2: conta por e-mail OU IP, e toda tentativa
      deixa linha)
      EVIDÊNCIA: `routes/auth.py:29-66`. O corte vem em `:40`, ANTES de buscar o
      usuário e antes do `verify_password`, com `MAX_TENTATIVAS = 5` e
      `JANELA_MINUTOS = 15` (`seguranca.py:24-25`), que são os mesmos números do
      SSO. As três chamadas de `registrar_tentativa` cobrem os três desfechos:
      credenciais erradas (`:50`), conta bloqueada ou inativa (`:58`) e entrada
      bem sucedida (`:64`). Três eventos no log estruturado: `LOGIN_BLOQUEADO`
      (`:41`), `LOGIN_RECUSADO` (`:51` e `:59`) e `LOGIN_OK` (`:65`).
      A `origem="senha"` separa esta contagem da do SSO: quem errou a senha cinco
      vezes não perde o caminho do card do Hub, que é outra credencial. Item 7 da
      `provas/prova_seguranca_f7.py` prova a separação.
      Itens 1 a 8 da prova: entrada correta (1), registro do sucesso (2) e da
      falha (3), o 429 na sexta (4), o 429 valendo até para a senha CERTA porque
      o corte vem antes de conferi-la (5), o bloqueio sendo de quem errou e não
      do sistema (6), e o corpo do 429 igual para e-mail que existe e que não
      existe (8).
      PREÇO DECLARADO, e é da regra da vault, não da implementação: contar por
      e-mail OU IP significa que dá para travar a conta de outra pessoa errando a
      senha dela cinco vezes, de qualquer IP. Item 6b da prova mostra isso
      acontecendo. A nota manda contar pelos dois (`Forca_Bruta_Login` regra 1) e
      a vault vence, mas o efeito fica escrito em vez de descoberto em produção.
      DESVIO HERDADO DA FASE 3, repetido aqui: a regra 4 da nota diz "tempo de
      bloqueio é configurável, sem redeploy", e aqui os dois números são
      constantes em `seguranca.py:21-25`, com o motivo no comentário. Valor de
      segurança que só muda com deploy é problema menor do que valor de segurança
      que qualquer um afrouxa pela tela.
      PROVA DE QUE A PROVA TEM DENTE: trocando o `>= MAX_TENTATIVAS` de `:40` por
      `>= 9999`, a prova falha nos itens 4, 5 e 8. Restaurado, 19 verdes de novo.
- [x] Trocar `allow_origins=["*"]` por lista explícita
      EVIDÊNCIA: `main.py:29-45`. A lista sai de `CORS_ORIGINS` (variável de
      ambiente, `:36`) e cai no padrão do código quando ninguém a define, que
      cobre produção mais o desenvolvimento local (`:29-33`).
      `allow_credentials` passou a `False` (`:45`): este projeto autentica por
      `Authorization: Bearer` do `localStorage`, sem cookie, e ligar credencial
      sem cookie nenhum só amplia o que o CORS permite. Item 16 da prova.
      Itens 13, 14 e 15: a lista não tem coringa, o preflight de origem estranha
      não recebe permissão, e o da origem de produção recebe.
      FURO MEU, achado antes de subir e fechado: eu tinha escrito
      `os.getenv("CORS_ORIGINS", _ORIGENS_PADRAO)`, e o `docker-compose.yml:24`
      entrega a variável como string VAZIA quando ninguém a preenche. O segundo
      argumento do `getenv` só vale quando a variável não existe, então a lista
      sairia vazia e a API recusaria toda origem em produção. Fechado com `or`
      (`:36`). Item 13b da prova recarrega o módulo com a variável vazia e exige
      a lista padrão; com o `getenv` antigo ele falha.
- [x] Cabeçalhos de segurança em toda resposta, nos DOIS lugares que respondem
      (`CSRF_Cookies_Headers`, seção "Headers de segurança (em toda resposta)`)
      EVIDÊNCIA: antes desta fase não existia nenhum, nem no nginx nem no backend.
      LADO API: `seguranca.py:109-131`, com os seis da nota
      (`X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy`,
      `Strict-Transport-Security`, `Permissions-Policy` e CSP), aplicados por
      middleware em `main.py:51-55`, que pega inclusive a resposta de erro.
      A CSP da API é `default-src 'none'` e não a do site: resposta de API é JSON
      e não carrega script, estilo nem imagem. Exceção declarada em
      `seguranca.py:121`: `/docs`, `/redoc` e `/openapi.json` ficam fora da CSP
      porque a documentação interativa carrega script e estilo de CDN, e os
      outros cinco cabeçalhos continuam saindo lá.
      Itens 9 a 12 da prova: os seis presentes na resposta comum, presentes
      também na de erro 404, a CSP da API sendo `default-src 'none'`, e o
      `/openapi.json` sem CSP mas com o resto.
      Item 17, que é o caminho triste deste desenho: middleware que reembrulha
      resposta é lugar clássico de download sair truncado. A prova baixa o modelo
      de importação de empresas e exige assinatura `PK` de xlsx,
      `content-length` igual ao corpo recebido, e o cabeçalho presente.
      LADO NAVEGADOR: `frontend/nginx.conf:14-22`, os mesmos seis no `location /`,
      todos com `always` (sem ele o nginx omite o cabeçalho nas respostas de
      erro). A rota `/api` não repete nada: quem responde ali é o backend.
      A CSP do site é fechada, com `script-src 'self'` e sem `unsafe-eval`. O
      `'unsafe-inline'` aparece só em `style-src`, e é necessário: o React escreve
      estilo em atributo `style` do elemento, e atributo herda dessa diretiva.
      Script não precisa, porque o build do Vite não injeta script inline no
      `index.html` (conferido no `dist/index.html` gerado).
      CONFERÊNCIA VISUAL, feita em 2026-08-17, tela: login servida com a CSP real:
      `frontend/provas/prova_headers_f7.py --servir` sobe o `dist/` com os
      cabeçalhos LIDOS do `nginx.conf`, e a tela abriu completa (fundo, tipografia,
      ícones, campos e botão) com o console do navegador sem uma única violação de
      CSP. Isso é o que grep nenhum prova: CSP errada não quebra teste, quebra a
      tela do usuário.
      NÃO PROVADO, e declarado: esta máquina não tem nginx nem docker, então a
      SINTAXE do `nginx.conf` não foi validada por `nginx -t`. O que a
      `prova_headers_f7.py` confere é o conteúdo dos cabeçalhos e a presença do
      `always`, por leitura do arquivo. A conferência visual cobriu a tela de
      login; as telas internas usam o mesmo bundle e o mesmo CSS, e a varredura
      por recurso externo em `frontend/src` achou só um link para o Hub e um texto
      de exemplo, nenhum script ou folha de estilo de fora.
- [x] Conferir se o serviço backend tem domínio próprio no EasyPanel
      EVIDÊNCIA: captura de tela do painel (`meuprojeto / gestor-de-tarefas`,
      2026-08-17), seção Domínios, com duas entradas e **nenhuma apontando para o
      backend**: `https://gestordetarefas.zoaria.com.br/` vai para
      `http://meuprojeto_gestor-de-tarefas_frontend:80/`, e o domínio automático
      `https://meuprojeto-gestor-de-tarefas.ocue6h.easy...` vai para
      `http://meuprojeto_gestor-de-tarefas:80/`. Os dois na porta 80, que é a do
      nginx; o backend responde em 8000 e não é destino de nenhum.
      Logo o `/docs` e o `/openapi.json` NÃO saem pela internet, porque o nginx
      do frontend só proxia `/api` (`frontend/nginx.conf:25`). `docs_url=None`
      não entra nesta fase, e a exceção de CSP de `seguranca.py:121` continua
      valendo para quem abre a documentação por dentro da rede do projeto.
      ACHADO DE PASSAGEM, não alterado: o domínio automático aponta para
      `meuprojeto_gestor-de-tarefas`, sem o sufixo `_frontend` que o outro tem.
      Se ele responder, é uma segunda entrada pública para o mesmo app. Não muda
      nada do que esta fase entregou, porque requisição de mesma origem não passa
      por CORS, mas é porta a mais e vale saber se está aberta de propósito.

**Fechamento da fase:** 4 de 4 itens com evidência.
`backend/provas/prova_seguranca_f7.py` com 19 checagens
verdes contra as rotas reais, `frontend/provas/prova_headers_f7.py` com 4, e a
conferência visual da CSP no navegador. Regressão sem nenhuma queda:
`prova_sso_f3.py` com 25, `app/sso.py` com 7, `prova_sso_f4.js` com 7 e
`npm run build` transformando os mesmos 2276 módulos.
CORREÇÃO NA PROVA DA FASE 3, e é consequência legítima desta fase: o item 17
exigia zero linha com IP `testclient`, e as duas chamadas de `/api/auth/login`
daquela prova iam sem `X-Forwarded-For`. Elas não registravam nada antes, e
passaram a registrar. O cabeçalho entrou nas duas (`provas/prova_sso_f3.py:137-139`
e `:313-315`), que é o que o nginx faz em produção. O item 17 segue com dente:
foi ele que acusou a mudança.
Balanço da escada: `grep -rn "escada:"` em `backend/app` e `frontend/src` devolve
0 marcadores; nenhum corte deliberado nesta fase.
