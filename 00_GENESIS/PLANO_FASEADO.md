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
**Status:** pending
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
**Status:** pending
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
**Status:** pending
**Duração:** 1 hora
**Depende de:** Fase 4

- Variáveis nos dois serviços do EasyPanel, mesma chave dos dois lados
- Teste com três pessoas reais: uma com cadastro, uma sem, uma bloqueada
- `CONFORMIDADE_VAULT.md` com evidência colada em cada linha
- Mapa Graphify gerado, se o usuário aceitar instalar

**Aceite:** funciona em produção pelo caminho real, e o login por senha continua
funcionando para quem entra direto.

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
