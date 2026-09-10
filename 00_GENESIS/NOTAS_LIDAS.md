# Notas lidas para as fases 23 a 25

Leitura de 2026-09-09, à noite, toda pelo agente principal. **Nenhum batedor
foi disparado, e o motivo está escrito:** a varredura completa da vault para
este assunto foi feita hoje de manhã, para as fases 18 e 19, com dois batedores
em paralelo, 17 fichas e 12 descartes com motivo. O assunto é o mesmo, o diff
mora nos mesmos arquivos, e repetir a varredura seria gastar duas vezes pelo
mesmo resultado. O que mudou é o recorte: saiu campo de log, entrou evento de
log. Por isso duas notas novas entraram, e essas foram lidas integrais agora.

## Lidas integralmente nesta sessão

| Nota | Linhas | Como foi descoberta | O trecho que importa | Onde se aplica |
|---|---|---|---|---|
| `00B_DOUTRINAS/Anti_Puxa_Saco.md` | 189 | doutrina, entra sempre | erro leva local, causa e correção | todas as fases |
| `00B_DOUTRINAS/Leitura_e_Retencao_de_Notas.md` | 236 | doutrina, entra sempre | citação exige leitura nesta sessão | todas as fases |
| `02_Seguranca/Padrao_Logging_Estruturado.md` | 210 | é a nota que originou o trabalho | a tabela "O que SEMPRE entra em log", 13 eventos | fases 23 e 24 |
| `02_Seguranca/Padrao_IDOR.md` | 199 | **nova**, apontada pela nota de logging no verbete `ACESSO_NEGADO_IDOR` | a seção "Auditoria", com `recurso` e `recurso_id`, e a condição "recurso existe mas não é dele" | fase 23 |
| `02_Seguranca/Principios.md` | 48 | **nova**, apontada pela nota de logging na seção "Audit log vs application log" | princípio 4 e a linha da auditoria, que lista `LOGOUT` no mínimo | fase 23 |

As duas notas novas são exatamente as que a `Padrao_Logging_Estruturado` cita
em "Ver também" e que o trabalho anterior tinha descartado com motivo: naquela
fase eram campos, e nenhuma das duas fala de campo. Agora são eventos, e as
duas definem evento. O descarte de manhã estava certo para aquele recorte, e
está errado para este.

## Reaproveitadas da varredura de 2026-09-09 pela manhã

Lidas integrais naquela sessão, listadas no `NOTAS_LIDAS` que foi para o
`checkpoint 20260909 213548.zip`, e aplicáveis sem mudança aqui:

| Nota | Linhas | Por que rege |
|---|---|---|
| `07_Regras_de_Ouro/Escada_Preguica_de_Codigo.md` | 241 | guarda na função compartilhada, não em cada chamador |
| `07_Regras_de_Ouro/Sem_Travessao.md` | 43 | vale em qualquer arquivo, inclusive comentário novo |
| `08_Processo_Dev/TDD_RED_GREEN_REFACTOR.md` | 204 | mudança em lógica compartilhada exige teste antes |
| `08_Processo_Dev/Fechar_Tarefa_Rodar_Verifica.md` | 118 | protocolo de fechamento, com ou sem tela |
| `02_Seguranca/Mapa_de_Conceitos_de_Seguranca.md` | 509 | Família 6, que confirma a lista de campos |
| `02_Seguranca/CSRF_Cookies_Headers.md` | 117 | os cabeçalhos que a resposta de erro carrega |

## Descartadas de novo, e por quê

| Nota | Motivo do descarte |
|---|---|
| `02_Seguranca/Forca_Bruta_Login.md` | é o limite de tentativas de login, que este app já implementa e já loga como `LOGIN_BLOQUEADO`. Nenhum evento novo sai dela |
| `02_Seguranca/Controle_de_IP.md` | bloqueio e allowlist de IP, que o app não usa |
| `02_Seguranca/Timeout_de_Sessao.md` | expiração por inatividade; o app expira por `exp` do JWT, e a decisão de não fazer blacklist já está no LASTRO |
| `07_Regras_de_Ouro/Verificacoes_Mecanicas_de_Tela.md` | é de tela, e a única mudança de frontend é uma chamada de API |
| `07_Regras_de_Ouro/Nunca_DELETE_Fisico.md` | as fases não criam nem mudam DELETE, só registram o que já acontece |
| `08_Processo_Dev/Debug_4_Fases.md` | não há defeito a reproduzir. Os dois eventos trocados são erro de nome, achado por leitura, e o conserto é a troca do literal |
