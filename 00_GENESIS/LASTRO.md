# LASTRO: SSO do Hub Zoaria no Tareffas

> Trabalho novo em projeto que já existe. O GENESIS cobre daqui pra frente, não
> tenta reconstruir a história anterior do Tareffas.

## Tipo e regime

- **Tipo de projeto:** App Online Auth (single-tenant), nota `01_SISTEMAS/04_Tipos_de_App/App_Online_Auth.md`
- **Regime de segurança:** WEB (segurança obrigatória, não negociável por pressa)
- **Stack (já decidida, não se repergunta):** FastAPI + React + Postgres, deploy EasyPanel via Compose
- **Domínio:** gestordetarefas.zoaria.com.br
- **Segundo repositório envolvido:** `aplicações/zoaria-hub` (Flask + SQLite), que emite o bilhete

## Doutrinas (cláusula pétrea, carregam sempre)

- `00B_DOUTRINAS/Anti_Puxa_Saco.md` : discordar primeiro e argumentar depois; erro sai como local, causa, correção
- `00B_DOUTRINAS/Leitura_e_Retencao_de_Notas.md` : nota se lê integral; proibido citar sem Read na sessão; LASTRO com N de linhas e campo `fim:`

## Notas de padrão que regem este trabalho

| Nota | Por que rege |
|---|---|
| `02_Seguranca/Padrao_Impersonacao_Segura.md` | o bilhete é credencial ao portador numa URL. Uso único, validade curta, log dos dois lados, marcar usado ANTES do login, `AND usado=0` com conferência de linhas |
| `02_Seguranca/CSRF_Cookies_Headers.md` | cookie HttpOnly, Secure, SameSite=Lax; CSRF em todo POST; rota de consumo entra na lista de isentas por ser entrada externa |
| `02_Seguranca/Padrao_IDOR.md` | recusa devolve 404, nunca 403; inexistente, expirado e usado respondem igual |
| `02_Seguranca/Forca_Bruta_Login.md` | a rota de consumo é porta de entrada: registra tentativa e limita por IP; mensagem de erro única |
| `02_Seguranca/Vazamento_de_Chaves.md` | a chave do bilhete vai por variável de ambiente nos dois lados, nunca no código |
| `02_Seguranca/Timeout_de_Sessao.md` | entrar pelo Hub não cria sessão eterna: o JWT do Tareffas mantém a validade que já tem |
| `03_Auth_Perfis_Permissoes/Perfis_e_Modulos.md` | o modelo de papel do Tareffas é dele; o Hub não vira dono de permissão |
| `04_Tipos_de_App/App_Online_Auth.md` | tela de login continua existindo; o SSO é caminho adicional, nunca substituto |
| `01_Padroes_Gerais/Padrao_CLAUDE_MD_Projeto.md` | o Tareffas não tem CLAUDE.md; é a Fase 1, antes de qualquer código |
| `07_Regras_de_Ouro/Escada_Preguica_de_Codigo.md` | o plano passou pela escada; o que foi cortado está declarado no PLANO_FASEADO |

## Decisões do usuário (rodada socrática de 2026-08-16)

1. **Confiança:** bilhete curto assinado, entregue na URL pelo `/ir` do Hub. O Hub
   não expõe a sessão dele, e o Tareffas não precisa conhecer o formato interno
   do Flask.
2. **Sem cadastro:** barra e avisa. Nada é criado automaticamente. Cadastrar
   segue sendo ato consciente de quem administra, que é quem sabe setor e empresa.
3. **Quem manda no papel:** o Tareffas. O Hub responde apenas "é fulano e ele
   pode entrar". Grupo, setor, empresa e overrides continuam sendo do Tareffas.

## Regras locais deste trabalho (não vêm da vault)

- O login por e-mail e senha do Tareffas **continua funcionando igual**. Se o SSO
  cair, ninguém fica trancado do lado de fora.
- Casamento de identidade é por **e-mail**, que é único em `usuarios.email`.
- `bloqueado = True` e `ativo = False` no Tareffas **barram a entrada pelo Hub**.
  O Hub não tem poder de ressuscitar acesso revogado localmente.
- O bilhete nunca aparece em log. O que se registra é quem entrou, quando e de qual IP.

## Estado do vizinho (Hub), em 2026-08-16

O Hub tem dois commits prontos e **não deployados** (perfis reutilizáveis, CSRF,
headers). A Fase 2 mexe no Hub e depende desses commits estarem em produção,
senão o deploy do SSO leva junto código que ainda não foi validado no ar.

## Conformidade parcial declarada

A cópia da vault nesta máquina não tem `70_ESTILO/`. O eixo de voz e vocabulário
proibido não pôde ser varrido, então a entrega **não alega conformidade** nesse
ponto. O que se aplica sem a pasta: português com acentuação completa em todo
texto que o usuário lê, e nada de travessão.
