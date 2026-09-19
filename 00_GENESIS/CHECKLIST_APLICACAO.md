# CHECKLIST: periodicidade da obrigação (fases 38 a 42)

```
Cor de marca: primary do Tailwind (frontend/tailwind.config.js), nunca hex na tela
Tema: claro
Acesso: por perfil (JWT próprio)
Seletor: tipo 1, escolhido em border-primary-600 bg-primary-50 text-primary-800
```

Regra deste arquivo: só marcar `[x]` com evidência apontável (arquivo e linha,
ou saída de comando colada no LOG).

## Fase 38: medir a competência do recibo real

- [x] 38.1 `competencia_exemplo` dos modelos de DEFIS e ECF em produção lido, sem alterar nada, e colado no LOG (decisão 2a). EVIDÊNCIA: LOG fase=38, DEFIS 01/2024 e 01/2025, ECF 01/2025
- [x] 38.2 (dispensado: 38.1 trouxe 01/AAAA, LOG) Se vier vazio: `extrair_dados` rodado sobre o PDF local, saída no LOG; se não for `01/AAAA`, PARAR e levar ao usuário

## Fase 39: servidor valida

- [x] 39.1 RED: `python backend/provas/prova_periodicidade_servidor.py` sai 1, saída no LOG (TDD_RED_GREEN_REFACTOR). EVIDÊNCIA: LOG fase=39 prova_RED, itens [2, 3, 4, 5, 6, 7, 10], rc=1
- [x] 39.2 validador `mode="before"` em `meses_ativos` e `competencia_ref` nos dois schemas de entrada; lixo dá 422; vazio vira o padrão (Padrao_Validacao_de_Input: "Toda string crua passa por validação tipada antes de tocar regra de negócio.")
      PROVA: itens 2, 3, 6, 7 e 12 a 18 da prova (o plano chamava de (a), (c) e (f)). EVIDÊNCIA: 'PROVA OK: 18 checagens verdes'; `_meses_validos` e `_competencia_valida` em `schemas.py`, aplicadas em ObrigacaoCreate e ObrigacaoUpdate
- [x] 39.3 `_COMP` do Excel dá "14 meses antes" para `-14` (achado do batedor, `routes/obrigacoes.py:105, :183`). EVIDÊNCIA: item 10 verde, `_comp_label` em `routes/obrigacoes.py`
- [x] 39.4 GREEN: prova em 0; `for f in backend/provas/*.py` todos em 0; `grep -n "—\|–"` rc=1 nos arquivos tocados (Sem_Travessao). EVIDÊNCIA: 'PROVA OK: 18 checagens verdes' (15 do plano, 16-17 do verificador, 18 da checagem do irmão); provas=36 falharam=0; travessão rc=1

## Fase 40: seletor na tela

- [x] 40.1 RED: `node frontend/provas/prova_periodicidade.js` sai com erro antes do módulo existir. EVIDÊNCIA: LOG fase=40 prova_RED, ERR_MODULE_NOT_FOUND rc=1 (com o erro de ordem declarado)
- [x] 40.2 seletor tipo 1: `role="radiogroup"` + `aria-label="Periodicidade"`, 4 `<button type="button" role="radio" aria-checked>`, `title` com a dica, escolhido `border-primary-600 bg-primary-50 text-primary-800`
      PROIBIDO: fundo sólido na opção escolhida, `type="radio"`, `<select>` (Padrao_Toggle_Tipos)
      PROVA: `grep -n 'aria-label="Periodicidade"' frontend/src/pages/Obrigacoes.jsx` acha 1. EVIDÊNCIA: acha 1 (LOG fase=40 tela)
- [x] 40.3 botões de mês: escolha do mês na Anual e Trimestral, liga/desliga na Personalizada; estado ligado sem `bg-primary-600 text-white`
      PROVA: `grep -n "bg-primary-600 text-white" frontend/src/pages/Obrigacoes.jsx` não acha o bloco dos meses. EVIDÊNCIA: grep sem saída no arquivo inteiro
- [x] 40.4 competência calculada em texto na Anual e Trimestral; `<select>` de hoje na Mensal e Personalizada; nenhum `<select` novo nas linhas `+` (Componente_SelectBusca). EVIDÊNCIA: `<select` nas linhas + : 0; aviso de divergência acrescentado (LOG)
- [x] 40.5 GREEN: prova Node em 0, provas do frontend em 0, `npm run build` ok; travessão, hex, `alert(`, `confirm(`, `prompt(` nas linhas `+`: 0 (Sem_Travessao, Sistema_de_Estilos, Sem_Popup_Nativo); textos novos com acento completo (Portugues_BR_Acentuacao); dica ao lado do controle, sem parágrafo de manual (Tela_Nao_Tem_Manual). EVIDÊNCIA: 'PROVA OK: 13 checagens verdes' (12 + o item 13 do verificador); provas_front=23 falharam=0; build ok; hex, select, popup 0 nas linhas +; travessão rc=1 (LOG gate_40_5). Tela_Nao_Tem_Manual fica para a conferência visual
- [x] 40.6 conferência visual local registrada com data e tela. EVIDÊNCIA: LOG fase=40 conferencia_visual, 2026-09-19, Obrigações > editar

## Fase 41: publicar e corrigir

- [x] 41.1 suítes e build verdes; `COPY . .` em `backend/Dockerfile` e `frontend/Dockerfile`. EVIDÊNCIA: provas=36 e 23 sem falha; backend/Dockerfile:17, frontend/Dockerfile:8 (LOG publicado)
- [x] 41.2 `git ls-remote` com o ref; carimbo de `/api/health` igual ao HEAD; bundle com `Periodicidade` (curl + grep -c). EVIDÊNCIA: ref 9d6be0d, carimbo 20260919-1707, bundle index-CsP7Oo8-.js com os 4 textos
- [x] 41.3 SELECT só de leitura das anuais e trimestrais e das tarefas abertas delas, colado no LOG. EVIDÊNCIA: feito pela API (só leitura): 3 anuais, 0 trimestrais, 1 tarefa aberta (LOG lista_producao)
- [x] 41.4 lista aprovada pelo usuário; correção pela tela ou PUT (sai `EDICAO_REGISTRO_CRITICO`), nunca UPDATE no console nem DELETE (Padrao_Logging_Estruturado, Nunca_DELETE_Fisico). EVIDÊNCIA: 'pode corrigir'; 3 PUT com 200
- [x] 41.5 segundo SELECT bate com a lista aprovada. EVIDÊNCIA: releitura [141,'3','-14'], [185,'3','-14'], [181,'7','-18']

## Fase 42: conferência em produção

- [x] 42.1 conferência do usuário colada no LOG. EVIDÊNCIA: LOG fase=42 conferencia_producao
- [x] 42.2 CONFORMIDADE sem linha pendente das fases 38 a 42. EVIDÊNCIA: grep '| pendente |' volta 0
