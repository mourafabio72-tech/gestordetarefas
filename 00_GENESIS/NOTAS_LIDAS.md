# Notas lidas na descoberta das fases 27 a 31 (2026-09-15)

Como foram descobertas: boot da vault (`CLAUDE.md` + doutrinas + `_MAPA_ROTA`,
rota `_MAPA_CHAVES`), `CLAUDE.md` do projeto, e quatro batedores `sonnet` em
paralelo, um por eixo. As fichas de UI e de segurança foram conferidas pelo
principal abrindo uma nota de cada.

## Lidas pelo principal, integral

| Nota | Linhas | Trecho chave | Fase |
|---|---|---|---|
| `00B_DOUTRINAS/Anti_Puxa_Saco.md` | 189 | erro leva local, causa e correção | todas |
| `00B_DOUTRINAS/Leitura_e_Retencao_de_Notas.md` | 236 | nota citada é nota lida; LASTRO com N e `fim:` | todas |
| `00A_MAPAS/_MAPA_ROTA.md` | 239 | rota `_MAPA_CHAVES` para sistema e tela | descoberta |
| `08_Processo_Dev/Brainstorming_Socratico_por_Tarefa.md` | 126 | 2 a 4 perguntas, opções objetivas, numa mensagem | descoberta |
| `01_Padroes_Gerais/Padrao_Toggle_Tipos.md` | 167 | escolha não suspensa cai em 1 dos 3 tipos; perguntar o estilo | 29 |
| `02_Seguranca/Padrao_Validacao_de_Input.md` | 197 | validação tipada no servidor antes da regra | 27, 28 |

**Correção de batedor, registrada:** o batedor de UI disse que radio fica fora
da `Padrao_Toggle_Tipos`. A nota só tira o checkbox (linha 33); a linha 11 põe
todo seletor não suspenso nos 3 tipos. A pergunta de estilo subiu ao usuário
por causa desta conferência, e a resposta foi o tipo 1.

## Lidas por batedor (fichas no chat de 2026-09-15)

| Nota | Linhas | Aplica | Por quê | Fase |
|---|---|---|---|---|
| `01_Padroes_Gerais/Padrao_Formulario.md` | 188 | sim, parcial | label e alinhamento; a barra `.ra-bar` de 40px é de filtro em linha, e o modal não usa | 29 |
| `01_Padroes_Gerais/Padrao_Toggle_OnOff.md` | 234 | não | nenhum liga/desliga que grava ao clicar; os checkboxes do modal gravam no Salvar | - |
| `01_Padroes_Gerais/Padrao_Modal_Popup_Centrado.md` | 172 | não | o trecho tocado não tem SelectBusca | - |
| `07_Regras_de_Ouro/Sem_Popup_Nativo.md` | 116 | sim | nada de `alert(` em código novo | 28, 29 |
| `01_Padroes_Gerais/Tela_Nao_Tem_Manual.md` | 112 | sim | explicação da opção vai para o `title` | 29 |
| `07_Regras_de_Ouro/Verificacoes_Mecanicas_de_Tela.md` | 278 | sim | provas de hex e checkbox cru | 29 |
| `02_Seguranca/Padrao_Mass_Assignment.md` | 210 | sim | whitelist do schema de edição | 27 |
| `02_Seguranca/Padrao_Logging_Estruturado.md` | 210 | sim | reclassificação passa pela rota que loga | 31 |
| `01_Padroes_Gerais/Convencoes_de_Banco.md` | 67 | não | nenhuma tabela nova; UPDATE pela tela e não por SQL | - |
| `07_Regras_de_Ouro/Nunca_DELETE_Fisico.md` | 92 | não | não há exclusão | - |
| `04_Tipos_de_App/App_Online_Auth.md` | 82 | sim | confirma regime WEB single-tenant | todas |
| `01_Padroes_Gerais/Sistema_de_Estilos.md` | 215 | sim | hex nunca na tela; cor via token | 29 |
| `01_Padroes_Gerais/Icones_Phosphor.md` | 174 | não | ícone não muda; lucide é desvio já declarado | - |
| `07_Regras_de_Ouro/Portugues_BR_Acentuacao.md` | 165 | sim | texto novo de tela | 29 |
| `07_Regras_de_Ouro/Sem_Travessao.md` | 43 | sim | todos os arquivos tocados | todas |
| `07_Regras_de_Ouro/Revisao_Professor_Pasquale.md` | 152 | sim, sem executor | `pasquale.py` ausente na vault | 29 |
| `07_Regras_de_Ouro/Classe_Sem_CSS.md` | 137 | não | só classe utilitária do Tailwind e a `check-app` que já existe | - |
| `07_Regras_de_Ouro/Escada_Preguica_de_Codigo.md` | 241 | sim | causa raiz e padrão irmão | todas |
| `08_Processo_Dev/TDD_RED_GREEN_REFACTOR.md` | 204 | sim | RED antes do código | 27, 28, 29 |
| `08_Processo_Dev/Fechar_Tarefa_Rodar_Verifica.md` | 118 | sim | protocolo de fechamento | 30 |
| `08_Processo_Dev/Plano_Antes_de_Codar.md` | 146 | sim | item com arquivo e verificação | todas |
| `08_Processo_Dev/Backup_Zip_Antes_e_Depois.md` | 121 | não | projeto usa git e checkpoint no 00_GENESIS | - |
| `07_Regras_de_Ouro/Protocolo_Revisao_de_Tela.md` | 234 | sim | domínio LÍNGUA junto; ajuste pontual | 29 |

## Cogitadas e não abertas

- `Padrao_Selecao_em_Lote.md`: a classe `check-app` que ela originou já está
  provada no projeto (CONFORMIDADE, fase 8). Não reaberta.
- `Padrao_IDOR.md`: a rota `link-envio` já passa por `_tarefa_no_escopo` (fase 26),
  e este trabalho só acrescenta uma recusa depois dela.

## Acréscimo de 2026-09-18 (fases 32 a 34)

Descoberta: `CLAUDE.md` do projeto, LASTRO, fim do LOG, mapa Graphify atualizado
(`graphify update .`, 18/09 18:04), e três batedores `sonnet` em paralelo: UI
(estrutura e dados juntos, porque a mudança não toca menu, topbar nem abas),
segurança com auth, e estilo com linguagem.

| Nota | Por quem | Trecho chave | Fase |
|---|---|---|---|
| `08_Processo_Dev/Brainstorming_Socratico_por_Tarefa.md` | principal, integral | "2 a 4 perguntas curtas ... mesmo que o pedido pareça claro" | abertura |
| `02_Seguranca/Padrao_IDOR.md` | batedor, conferida pelo principal | "Não é só na URL. Body também" | 33 |
| `02_Seguranca/Padrao_Logging_Estruturado.md` | batedor | "mutação de dado crítico SEMPRE entram" | 32 |
| `02_Seguranca/Padrao_Mass_Assignment.md` | batedor | "Backend define a whitelist de campos editaveis." | 33 |
| `02_Seguranca/Mapa_de_Conceitos_de_Seguranca.md` | batedor | "Operações custosas ... 1 por vez por usuário" | fora de escopo, declarado |
| `01_Padroes_Gerais/Padrao_Toggle_Tipos.md` | batedor | "NUNCA escolher o estilo sozinho"; checkbox "fora desta taxonomia" | 33 |
| `01_Padroes_Gerais/Padrao_Toggle_OnOff.md` | batedor | "Toggle é para ESTADO; checkbox é para MULTI SELEÇÃO" | 33 |
| `01_Padroes_Gerais/Tela_Nao_Tem_Manual.md` | batedor | "PROIBIDO usar o parágrafo para compensar rótulo ruim" | 33 |
| `07_Regras_de_Ouro/Verificacoes_Mecanicas_de_Tela.md` | batedor | checkbox cru "-> zero" | 33 |

Descartadas, com motivo: `Padrao_Modal_Popup_Centrado` (não há SelectBusca no modal),
`Padrao_Marca_IA` (não há IA), `Icones_Phosphor` (desvio lucide-react já declarado),
`Forca_Bruta_Login`, `Timeout_de_Sessao`, `Vazamento_de_Chaves`, `Controle_de_IP`,
`Admin_Inicial_Padrao`, `Auto_Liberacao_por_Grupo`, `Painel_Desenvolvedor` (nenhuma toca
esta mudança). `Padrao_Texto_e_Linguagem` e `70_ESTILO/` não existem nesta vault.
