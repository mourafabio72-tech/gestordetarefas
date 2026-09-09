# NOTAS LIDAS

Varredura de 2026-09-09, para o trabalho "varios responsaveis por (empresa, setor)".
Cinco batedores em paralelo (sonnet), mais leitura direta do principal.

## Lidas pelo agente principal

| Nota | Como foi descoberta | O que importa aqui | Fase |
|---|---|---|---|
| `00B_DOUTRINAS/Anti_Puxa_Saco.md` | doutrina, carrega sempre | erro se reporta como local, causa, correcao | todas |
| `00B_DOUTRINAS/Leitura_e_Retencao_de_Notas.md` | doutrina, carrega sempre | LASTRO com N de linhas e titulo da ultima secao | todas |
| `01_SISTEMAS/08_Processo_Dev/Brainstorming_Socratico_por_Tarefa.md` | a skill A3 aponta | 2 a 4 perguntas objetivas numa mensagem so, antes de codar | 8 |
| `01_SISTEMAS/07_Regras_de_Ouro/Escada_Preguica_de_Codigo.md` | filtro obrigatorio do plano | degrau 2 achou o componente pronto; item de padrao nao entra na escada | todas |
| `01_SISTEMAS/02_Seguranca/Padrao_IDOR.md` | conferencia da ficha do batedor | "IDOR via body (POST/PUT). Nao e so na URL" | 9 |

LASTRO: Anti_Puxa_Saco.md | 189 linhas | fim: "## Fontes que embasam esta regra"
LASTRO: Leitura_e_Retencao_de_Notas.md | 236 linhas | fim: "## Historico"
LASTRO: Brainstorming_Socratico_por_Tarefa.md | 126 linhas | fim: "## Historico"
LASTRO: Escada_Preguica_de_Codigo.md | 241 linhas | fim: "## Ver tambem"
LASTRO: Padrao_IDOR.md | 199 linhas | fim: "## Historico"

## Lidas pelos batedores (ficha devolvida, nota fica na vault)

### Eixo UI-dados

| Nota | Aplica | Regra que sobrevive aqui |
|---|---|---|
| `Componente_SelectBusca.md` | sim | **nao tem modo multiplo**: nao ha o que reusar da vault |
| `Padrao_Selecao_em_Lote.md` | parcial | checkbox de marcacao nunca e o do sistema operacional; a faixa de acoes em lote nao se aplica |
| `Padrao_Toggle_OnOff.md` | sim | "Toggle e para ESTADO; checkbox e para MULTI SELECAO" |
| `Padrao_Toggle_Tipos.md` | sim | "Fora desta taxonomia": multi selecao nao e toggle, entao nao ha pergunta de estilo a fazer |
| `Padrao_Tabela.md` | sim | "as linhas sao registros comparaveis entre si? Se nao sao, e grade": a aba fica fora das ferramentas de tabela |
| `Padrao_Formulario.md` | nao | trata de barra horizontal de filtro, nao de linha de cadastro |
| `Verificacoes_Mecanicas_de_Tela.md` | sim | "Regra listada nao e regra cumprida. So vira cumprida quando alguem prova" |

### Eixo UI-estrutura

| Nota | Aplica | Regra que sobrevive aqui |
|---|---|---|
| `Padrao_Modal_Popup_Centrado.md` | sim | popover dentro de modal fica CORTADO sem overflow visivel |
| `Padrao_Modal_Nao_Fecha_Sozinho.md` | sim | "O modal sai pelo X ou pelo Cancelar, e por mais nada" |
| `Padrao_Modal.md` | sim | `.modal-caixa` tem overflow-y auto; a variante de popover e a excecao |
| `Padrao_Tabs.md` | nao | trata de troca de view, nao de popover |
| `Padrao_Box_Card.md` | nao | so a linha de sombra de dropdown se aproveita |

### Eixo estilo e linguagem

| Nota | Aplica | Regra que sobrevive aqui |
|---|---|---|
| `Sistema_de_Estilos.md` | sim | "PROIBIDO: o hex aparecer em qualquer template" |
| `Icones_Phosphor.md` | sim, com desvio | "Phosphor unico" e "nada de emoji"; o projeto usa lucide, desvio declarado no LASTRO |
| `70_ESTILO/` | NAO ENCONTRADA | a pasta nao existe nesta vault; o indice `_MAPA_ESTILO.md` tem os titulos mascarados, e o conteudo e voz de ensino, nao copy de interface |

### Eixo seguranca (16 notas de `02_Seguranca/` lidas; os 4 arquivos de `_Materiais_Thales/` nao, por serem material bruto de terceiro ja destilado pelo Mapa)

| Nota | Aplica | Regra que sobrevive aqui |
|---|---|---|
| `Padrao_IDOR.md` | sim | id de recurso no body se valida ANTES de gravar; recusa e 404, nao 403 |
| `Padrao_Mass_Assignment.md` | sim | "Backend define a whitelist de campos editaveis" |
| `Padrao_Validacao_de_Input.md` | sim | "Tres camadas, nunca duas, nunca uma" |
| `Padrao_Logging_Estruturado.md` | parcial | "mutacao de dado critico SEMPRE entra" no log |
| `Revisao_Vulnerabilidades.md` | sim | checklist a cada feature nova e antes de cada deploy |
| `Principios.md` | parcial | rota que muda dado exige login; CSRF nao se aplica (JWT em header, sem cookie) |
| `Padrao_Impersonacao_Segura.md` | analogia | unica nota que discute corrida em escrita |
| `CSRF_Cookies_Headers`, `Controle_de_IP`, `Forca_Bruta_Login`, `Timeout_de_Sessao`, `Vazamento_de_Chaves`, `Padrao_CI_CD_Seguro`, `Padrao_Container_Seguro`, `Padrao_Dependencias_Lockfile`, `Mapa_de_Conceitos_de_Seguranca` | nao | fora do eixo desta mudanca |

**Buscado e NAO encontrado na vault**, declarado em vez de inventado:
- limite de tamanho de lista em payload JSON (so existe limite de upload de arquivo)
- regra sobre "apagar tudo e reinserir" versus diff
- regra sobre campo "principal" redundante ao lado de uma relacao N para N

### Eixo auth e permissoes (7 notas de `03_Auth_Perfis_Permissoes/` lidas)

Nenhuma aplica. A pasta trata de perfil x modulo (VER/EDITAR), convite, admin inicial
e impersonacao. **Nao existe na vault regra sobre escopo "proprias" quando o registro
tem varios donos, nem sobre quem pode atribuir responsavel.** O proprio codigo ja
respondeu: `routes/tarefas.py:43` ja considera o M2M no filtro de escopo.

## Lidas e descartadas

- `PASSO_0_Pergunta_Obrigatoria.md`: e a nota de projeto NOVO. Em ampliacao vale a
  `Brainstorming_Socratico_por_Tarefa`, e tipo, stack, cor e acesso ja estao decididos.
