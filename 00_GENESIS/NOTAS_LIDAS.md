# NOTAS LIDAS: fases 38 a 42 (periodicidade)

| Nota | Linhas | Quem leu | Aplica | Trecho chave | Fase |
|---|---|---|---|---|---|
| 00B_DOUTRINAS/Anti_Puxa_Saco | 189 | principal | sim | erro leva local, causa e correção | todas |
| 00B_DOUTRINAS/Leitura_e_Retencao_de_Notas | 236 | principal | sim | nota citada é nota lida nesta sessão | todas |
| 08_Processo_Dev/Brainstorming_Socratico_por_Tarefa | 126 | principal | sim | 2 a 4 perguntas objetivas antes do plano | 0 |
| 01_Padroes_Gerais/Padrao_Toggle_Tipos | 167 | principal | sim | perguntar o estilo; tipo 1 borda + suave | 40 |
| 01_Padroes_Gerais/Tela_Nao_Tem_Manual | 112 | batedor | sim | dica colada ao controle, nunca parágrafo de manual | 40 |
| 01_Padroes_Gerais/Sistema_de_Estilos | 215 | batedor | princípio | cor via token, nunca hex na tela | 40 |
| 07_Regras_de_Ouro/Verificacoes_Mecanicas_de_Tela | 278 | batedor | sim | regra só cumprida com saída colada | 40 |
| 07_Regras_de_Ouro/Protocolo_Revisao_de_Tela | 234 | batedor | sim | checklist antes de tocar tela; domínio LÍNGUA | 40 |
| 07_Regras_de_Ouro/Portugues_BR_Acentuacao | 165 | batedor | sim | texto visível com acento completo | 40 |
| 07_Regras_de_Ouro/Sem_Travessao | 43 | batedor | sim | nenhum travessão | 39, 40 |
| 07_Regras_de_Ouro/Sem_Popup_Nativo | 116 | batedor | sim | nenhum alert/confirm/prompt novo | 40 |
| 01_Padroes_Gerais/Padrao_Formulario | 188 | batedor | contrato | label acima, controles da mesma altura | 40 |
| 01_Padroes_Gerais/Componente_SelectBusca | 84 | batedor | princípio | nunca `<select>` nativo novo | 40 |
| 08_Processo_Dev/TDD_RED_GREEN_REFACTOR | 204 | batedor | sim | prova antes, RED e GREEN | 39, 40 |
| 07_Regras_de_Ouro/Escada_Preguica_de_Codigo | 241 | batedor | sim | reuso antes de construir; guardrails intocáveis | todas |
| 02_Seguranca/Padrao_Validacao_de_Input | 197 | batedor + principal (linhas 16-17) | sim | string crua validada antes da regra | 39 |
| 02_Seguranca/Padrao_Logging_Estruturado | 210 | batedor | sim | mutação crítica sempre loga | 41 |
| 08_Processo_Dev/Fechar_Tarefa_Rodar_Verifica | 118 | batedor | sim | "pronto" só com prova | 42 |
| 07_Regras_de_Ouro/Nunca_DELETE_Fisico | 92 | batedor | sim | correção é UPDATE, nunca DELETE | 41 |

## Descartadas, com motivo

| Nota | Motivo |
|---|---|
| Padrao_Selecao_em_Lote | rege checkbox de linha de tabela para ação em lote; aqui é escolha única |
| Padrao_Mass_Assignment | os campos já estão na whitelist nomeada de `ObrigacaoUpdate`; nada novo entra |
| App_Online_Auth | nada neste trabalho muda o modo do app |

## Varredura

Dois batedores sonnet em paralelo (tela e estilo; processo e segurança), em
2026-09-19. Não houve batedor de auth nem de estrutura de UI: o trabalho não
toca login, menu, tabela nem modal novo. Desvio do "cinco eixos" declarado.
