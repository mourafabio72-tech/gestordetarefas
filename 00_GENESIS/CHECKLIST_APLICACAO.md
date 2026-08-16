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

- [ ] Ler `Padrao_Validacao_de_Input` e `Padrao_Logging_Estruturado` ANTES de escrever a rota
- [ ] Tabela `sso_bilhetes_usados` (jti, usado_em, ip) com limpeza do que venceu
- [ ] Recusa bilhete acima do tamanho esperado ANTES de consultar o banco
      (`Padrao_Impersonacao_Segura`, bloco Consumo)
- [ ] Marca o jti como usado ANTES de emitir o JWT
      PROIBIDO: emitir o token e marcar depois
      (`Padrao_Impersonacao_Segura`: "Marcar como usado ANTES do login, e nunca depois")
- [ ] `UPDATE ... WHERE jti=%s AND usado=0` **e o código confere as linhas afetadas**
      PROVA: teste de corrida com duas requisições simultâneas, só uma entra
      (`Padrao_Impersonacao_Segura`, cenário 6)
- [ ] Inexistente, expirado, já usado e assinatura inválida devolvem a MESMA resposta
      (`Padrao_Impersonacao_Segura`: "Mensagem diferente para expirado, usado e inexistente vira oráculo")
- [ ] Usuário ausente, bloqueado ou inativo: mesma mensagem única
      (`Forca_Bruta_Login` regra 3: "Mensagem de erro é única")
- [ ] Recusa devolve 404, nunca 403
      (`Padrao_IDOR`: "Retornar 403 em vez de 404 quando não é dono: confirma que o recurso existe")
- [ ] Tentativas registradas e limitadas por IP, como no login por senha
      (`Forca_Bruta_Login` regra 2: "Toda tentativa, sucesso ou falha, é registrada")
- [ ] O JWT emitido tem a MESMA validade do login normal (8 horas)
      PROIBIDO: sessão mais longa por ter entrado pelo Hub
      (`Timeout_de_Sessao`)
- [ ] Rota de consumo declarada como isenta de CSRF, por ser entrada externa
      (`CSRF_Cookies_Headers`, seção "Rotas isentas")
- [ ] Log de entrada com e-mail, IP e resultado; bilhete fora do log

## Fase 4 : frontend

- [ ] `AuthContext` troca `?sso=` por JWT quando não há token guardado
- [ ] `history.replaceState` limpa a URL logo após consumir
      (`Padrao_Impersonacao_Segura`: "redirecionar logo após consumir, para o token
      não ficar na barra nem no histórico")
- [ ] Quem já está logado não é derrubado por um bilhete que chega
- [ ] Mensagem de recusa em português com acentuação completa, legível para quem
      não é técnico (vault `CLAUDE.md` regra 1)
      PROIBIDO: travessão em qualquer texto, inclusive dentro de JSX

## Fase 5 : entrega

- [ ] Mesma chave nos dois serviços do EasyPanel
- [ ] Teste real: pessoa com cadastro entra; sem cadastro vê o aviso; bloqueada é barrada
- [ ] Login por e-mail e senha continua funcionando para quem entra pela URL direta
- [ ] `CONFORMIDADE_VAULT.md` com evidência colada em cada linha
- [ ] Mapa Graphify gerado, se o usuário aceitar instalar
