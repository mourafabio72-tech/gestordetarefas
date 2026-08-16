# Notas lidas na descoberta

Vault: `/Users/fabiomoura/ObsidianJovi` (caminho do `obsidian-jovi.json`).
Varredura **serial**, sem subagentes: a instrução global desta máquina proíbe
disparar agentes sem pedido explícito, e ela vence skill na precedência da vault.

## Lidas integral, e que regem o trabalho

| Nota | Trecho que importa | Fase |
|---|---|---|
| `CLAUDE.md` (vault, 408 linhas) | precedência: doutrina > pedido do usuário > este arquivo > 01_SISTEMAS; regra 12 manda o 00_GENESIS existir também em trabalho novo dentro de projeto que já existe | todas |
| `00B_DOUTRINAS/Anti_Puxa_Saco.md` (189) | "Fale a verdade util, nao a verdade agradavel"; erro se reporta como local, causa, correção, sem interjeição de susto | todas |
| `00B_DOUTRINAS/Leitura_e_Retencao_de_Notas.md` (236) | leitura integral por padrão; proibido citar nota sem Read na sessão; LASTRO com N de linhas e `fim:` como prova de fim de leitura | todas |
| `00A_MAPAS/_MAPA_ROTA.md` (239) | rota `_MAPA_CHAVES` cobre auth, segurança e tipos de app; doutrinas não entram por rota, entram sempre | descoberta |
| `08_Processo_Dev/Brainstorming_Socratico_por_Tarefa.md` (126) | 2 a 4 perguntas com opções objetivas antes da primeira linha de código, numa mensagem só, com padrão declarado se não responder | fase 0 |
| `02_Seguranca/Padrao_Impersonacao_Segura.md` (285) | link que é credencial ao portador: uso único, validade curta, log dos dois lados, marcar usado ANTES do login, `UPDATE ... AND usado=0` **com conferência das linhas afetadas**, redirecionar logo após consumir, mesma resposta para inexistente/expirado/usado, token nunca em log | 2 e 3 |
| `02_Seguranca/CSRF_Cookies_Headers.md` (117) | `SESSION_COOKIE_HTTPONLY/SECURE/SAMESITE="Lax"`; CSRF em todo POST/PUT/PATCH/DELETE; webhook e entrada externa ficam em rota isenta declarada | 2 e 3 |
| `02_Seguranca/Padrao_IDOR.md` (199) | "Retornar 403 em vez de 404 quando não é dono: confirma que o recurso existe"; validar ownership antes de devolver dado | 3 |
| `02_Seguranca/Forca_Bruta_Login.md` (65) | conta falhas por e-mail **ou** IP; toda tentativa registrada; mensagem de erro única, nunca revelando qual campo falhou | 3 |
| `02_Seguranca/Vazamento_de_Chaves.md` (84) | "Se uma chave aparece no código, ela está vazada"; tudo por variável de ambiente, com `.env.example` sem valores | 2 e 3 |
| `02_Seguranca/Timeout_de_Sessao.md` (40) | `PERMANENT_SESSION_LIFETIME` e timeout por inatividade são independentes; o segundo é o que protege sessão esquecida aberta | 3 |
| `03_Auth_Perfis_Permissoes/Perfis_e_Modulos.md` (85) | perfil concede módulo com VER e EDITAR; toda rota protegida aponta para uma chave de módulo | 3 |
| `03_Auth_Perfis_Permissoes/Auto_Liberacao_por_Grupo.md` (83) | módulo novo já nasce liberado para o perfil que marcou auto-liberação no grupo | descartada, ver abaixo |
| `04_Tipos_de_App/App_Online_Auth.md` (82) | app auth nasce com tela de login, painel admin, força bruta, CSRF, headers e timeout. O SSO não substitui nada disso | 1 e 3 |
| `01_Padroes_Gerais/Padrao_CLAUDE_MD_Projeto.md` (182) | todo projeto de código tem CLAUDE.md na raiz apontando para a vault; sem ele os padrões ficam invisíveis e cada sessão reinventa | 1 |
| `07_Regras_de_Ouro/Escada_Preguica_de_Codigo.md` (241) | 7 degraus antes de propor implementação; guardrails intocáveis (validação em trust boundary, segurança, perda de dado) nunca entram na poda; corte deliberado leva comentário `escada:` com teto e saída | plano |

## Lidas e descartadas, com motivo

- `03_Auth_Perfis_Permissoes/Auto_Liberacao_por_Grupo.md` : descreve auto-liberar
  módulo novo por grupo de perfil. Não se aplica porque a decisão foi que o Hub
  **não** concede papel dentro do Tareffas. Fica registrada porque é a nota que
  alguém abriria se um dia a decisão virar "o Hub semeia o grupo".

## Não lidas, e por isso não citadas

`Matriz_VER_EDITAR`, `Instrucao_Replicar_Sistema_Perfis`, `Admin_Inicial_Padrao`,
`Padrao_Convite_de_Acesso`, `Painel_Desenvolvedor`, `Padrao_Validacao_de_Input`,
`Padrao_Logging_Estruturado`, `Controle_de_IP`, `Padrao_Mass_Assignment`.

Duas delas provavelmente entram na execução e devem ser lidas antes da fase que
tocam: `Padrao_Validacao_de_Input` (fase 3, o bilhete é entrada não confiável) e
`Padrao_Logging_Estruturado` (fase 3, campos fixos do log e o que nunca entra nele).

## Ausente nesta cópia da vault

`70_ESTILO/` não existe aqui. Eixo de voz e vocabulário proibido não varrido.
