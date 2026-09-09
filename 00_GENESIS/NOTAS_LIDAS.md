# Notas lidas para as fases 18 e 19

Varredura de 2026-09-09. Dois batedores em paralelo (modelo `sonnet`), mais
leitura integral do principal nas notas centrais. Eixos de tela não foram
varridos, e o motivo está no LASTRO: a fase não produz tela.

## Lidas integralmente pelo agente principal

| Nota | Linhas | Como foi descoberta | O trecho que importa | Onde se aplica |
|---|---|---|---|---|
| `00B_DOUTRINAS/Anti_Puxa_Saco.md` | 189 | doutrina, entra sempre | erro leva local, causa e correção | toda a fase |
| `00B_DOUTRINAS/Leitura_e_Retencao_de_Notas.md` | 236 | doutrina, entra sempre | citação exige leitura nesta sessão | toda a fase |
| `01_SISTEMAS/02_Seguranca/Padrao_Logging_Estruturado.md` | 210 | é o achado que originou a fase | a tabela dos 8 campos obrigatórios | fase 18 |
| `01_SISTEMAS/08_Processo_Dev/Brainstorming_Socratico_por_Tarefa.md` | 126 | a própria skill aponta para ela em modo ampliação | 2 a 4 perguntas objetivas antes da primeira linha | antes do plano |
| `01_SISTEMAS/02_Seguranca/Mapa_de_Conceitos_de_Seguranca.md` | 509 | citada pela nota de logging | Família 6, linha 175 | fase 18 |

A última entrou por conferência do principal sobre a ficha do batedor, como
manda a skill: ficha de segurança não se aceita só pelo resumo. Leitura da
seção, não integral, e por isso declarada assim.

## Fichas dos batedores, notas que APLICAM

| Nota | Linhas | Por que rege |
|---|---|---|
| `07_Regras_de_Ouro/Escada_Preguica_de_Codigo.md` | 241 | guarda na função compartilhada, não em cada chamador |
| `07_Regras_de_Ouro/Sem_Travessao.md` | 43 | vale em qualquer arquivo, inclusive comentário novo |
| `08_Processo_Dev/TDD_RED_GREEN_REFACTOR.md` | 204 | mudança em lógica compartilhada exige teste antes |
| `08_Processo_Dev/Fechar_Tarefa_Rodar_Verifica.md` | 118 | protocolo de fechamento, com ou sem tela |

## Lidas e descartadas, com o motivo

| Nota | Motivo do descarte |
|---|---|
| `02_Seguranca/Principios.md` | trata dos 8 princípios gerais e da tabela `logs_acesso`; não toca campo de log |
| `02_Seguranca/Controle_de_IP.md` | é bloqueio e allowlist de IP; a extração de IP que interessa já está resolvida no projeto |
| `02_Seguranca/Padrao_Validacao_de_Input.md` | input de formulário e upload, não logging |
| `02_Seguranca/Vazamento_de_Chaves.md` | onde guardar segredo; esta fase não cria variável de ambiente |
| `02_Seguranca/Padrao_Container_Seguro.md` | Dockerfile e container, fora do diff |
| `02_Seguranca/Revisao_Vulnerabilidades.md` | checklist de deploy; nenhum item toca o logger |
| `07_Regras_de_Ouro/Verificacoes_Mecanicas_de_Tela.md` | é de tela, e a fase não tem tela |
| `07_Regras_de_Ouro/Nunca_DELETE_Fisico.md` | não há DELETE no diff |
| `07_Regras_de_Ouro/Env_em_Dev_Ambiente_em_Prod.md` | nenhuma variável de ambiente nova |
| `07_Regras_de_Ouro/Portugues_BR_Acentuacao.md` | a própria nota exclui "chave de JSON" e "logs de servidor" do escopo, e os campos são exatamente isso |
| `08_Processo_Dev/Debug_4_Fases.md` | não há defeito a reproduzir; é campo novo, não bug |
| `08_Processo_Dev/Backup_Zip_Antes_e_Depois.md` | é substituto de git para quem ainda não usa git; este projeto tem git e deploy próprio |
