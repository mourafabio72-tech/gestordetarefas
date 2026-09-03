# Spec — Obrigação (modelo recorrente) + gerador de tarefas

> Origem: tela "Cadastro de obrigação" do Acessórias. Objetivo: separar o
> **modelo recorrente** (obrigação) da **instância** (tarefa), vincular a
> obrigação a N empresas, e gerar as tarefas por competência automaticamente.
> O `mininome` + `competencia` são as chaves que o **e-validador** usa para
> achar e baixar a tarefa pelo comprovante de entrega.
>
> Decisões (2026-08-02): (1) criar entidade Obrigação + gerador; (2) recorrência
> por **regra única + meses ativos** (não 12 campos por mês); (3) vincular a uma
> **lista de empresas**.

## Fluxo
```
OBRIGAÇÃO (modelo) --vínculo N empresas--> GERADOR --> TAREFA (empresa+competência) --e-validador--> baixada
```

## 1. Entidade `Obrigacao` (modelo)
| Campo | Tipo | Origem no print |
|---|---|---|
| id | int PK | — |
| nome | str(200) | Nome da obrigação |
| mininome | str(50) | Mininome — **chave e-validador** |
| setor_id | FK setores (null) | Departamento |
| responsavel_id | FK usuarios (null) | Responsável (default) |
| tempo_previsto_min | int (null) | Tempo previsto (min) |
| regra_prazo_tipo | str | Entrega: `ultimo_dia_util` \| `dia_fixo` \| `primeiro_dia_util` \| `dia_util` (N-ésimo dia útil — `regra_prazo_dia` diz qual) |
| regra_prazo_dia | int (null) | dia do mês quando `dia_fixo` (ex.: 20) |
| meses_ativos | str CSV | "1,2,…,12" — quais meses ocorre |
| lembrar_dias_antes | int (5) | Lembrar X dias antes |
| tipo_dias | str | `corridos` \| `uteis` |
| ajuste_nao_util | str | `antecipar` \| `postergar` \| `nenhum` |
| sabado_util | bool (False) | Sábado é útil? |
| competencia_ref | str | Deslocamento em meses entre a entrega e o fato gerador: `-1` (ou `mes_anterior`), `0` (`mesmo_mes`), `-2` (SPED, EFD-Contribuições), `-3`, `1` (`mes_seguinte`), `-12` (`ano_anterior`). Apelidos antigos seguem aceitos. |
| **ancora** | str (null) | `fechamento` = etapa do processo, vence em relação ao marco da empresa; null = prazo legal próprio (padrão) |
| **ancora_dias_antes** | int (0) | dias antes do marco; 0 = no próprio dia do fechamento |
| **ancora_tipo_dias** | str | `uteis` \| `corridos` |
| exige_robo | bool (False) | Exigir Robô? |
| passivel_multa | bool (False) | Passível de multa? → vira `gera_multa` na tarefa |
| alerta_guia_nao_lida | bool (False) | Alerta guia ñ-lida? |
| ativa | bool (True) | Ativa? |
| comentario_padrao | text (null) | Comentário Padrão → `descricao` da tarefa |
| **aplica_regimes** | str CSV (null) | público-alvo por regime; vazio = todos |
| **aplica_segmentos** | str CSV (null) | público-alvo por segmento; vazio = todos |
| created_at / updated_at | datetime | — |

Vocabulários (alinhados ao cadastro de empresa):
- regimes: `lucro_real`, `lucro_presumido`, `simples_nacional`, `mei`, `terceiro_setor`
- segmentos: `comercio`, `industria`, `servico`, `terceiro_setor`
  (⚠️ hoje o empresa usa também `comercio_servico`; reconciliar no cadastro de empresa.)

## 1b. Prazo que varia por empresa — o marco de fechamento

Duas famílias de obrigação convivem e não se parecem:

- **Prazo em lei** (SPED, DEFIS, DARF): a data é a mesma para toda empresa.
  `ancora` fica NULL e vale a regra própria da obrigação. É o padrão e a maioria.
- **Etapa do fechamento** (lançar notas, conciliar, balancete): não tem data
  legal — tem que caber ANTES do fechamento daquele cliente, que varia.

Para as segundas, a data sai do **marco da empresa** (`empresas.fechamento_tipo`
+ `fechamento_dia`) recuado por `ancora_dias_antes`:

```
vencimento = marco_da_empresa − ancora_dias_antes (úteis ou corridos)
```

O cadastro é **um por empresa** (o marco) mais **um por obrigação** (a folga),
e não o produto dos dois. Muda o marco de um cliente e a cadeia inteira dele
desloca junto.

Empresa ancorada mas SEM marco definido cai na regra própria da obrigação:
falta de cadastro não impede a tarefa de nascer.

Exemplo (set/2026, marco A = dia 15, marco B = 5º dia útil):

| Obrigação | dias antes | Empresa A | Empresa B |
|---|---|---|---|
| Lançar notas | 6 úteis | 07/09 | 28/08 |
| Conciliar banco | 3 úteis | 10/09 | 02/09 |
| Balancete | 0 | 15/09 | 07/09 |
| EFD-Contribuições (sem âncora) | — | 14/09 | 14/09 |

Fora do escopo por ora: **dependência** entre obrigações (bloquear a conclusão
de uma etapa cuja anterior não foi concluída). Trava o trabalho durante a
implantação; aqui só se calcula data.

## 2. Público-alvo (targeting) e vínculo com empresas
A obrigação define a QUEM se aplica de dois modos, combináveis:
1. **Por regra** — `aplica_regimes` e `aplica_segmentos` (CSV). Empresa entra se
   `(regime ∈ aplica_regimes ou vazio) E (segmento ∈ aplica_segmentos ou vazio)`.
   Ex.: DAS → regimes=[simples_nacional], segmentos=[] (todos). ICMS →
   regimes=[], segmentos=[comercio,industria].
2. **Por exceção** — tabela `obrigacao_empresa` (obrigacao_id, empresa_id) para
   incluir empresas específicas fora da regra.

Empresas-alvo do gerador = (empresas que casam a regra) ∪ (vínculos explícitos).

## 3. Campos novos na `Tarefa` (instância)
- `obrigacao_id` FK obrigacoes (null) — de qual modelo veio.
- `competencia` str "MM/AAAA" — referência (chave de baixa do e-validador).
- (fase e-validador) `protocolo_entrega`, `data_entrega`, `anexo_path`.

## 4. Gerador
Para uma competência-alvo (mês/ano): para cada obrigação `ativa` cujo mês-alvo
está em `meses_ativos`, para cada empresa vinculada, cria uma `Tarefa` se ainda
não existir (dedupe por obrigacao_id + empresa_id + competencia). Preenche:
título=nome, mininome herdado, setor/responsável default, `data_prazo` calculada
pela regra de prazo (ajustada a dia útil), `gera_multa`=passivel_multa,
`descricao`=comentario_padrao, `competencia`.
- Execução **automática** via scheduler (mensal) + gatilho manual "gerar competência".

## 5. Permissão
CRUD de obrigação sob `require_perm("obrigacoes", ...)`. Vincular empresas e
gerar = editar. (matriz de permissões já implementada.)

## 6. Fases
- **A (backend base):** modelo Obrigacao + vínculo empresas + campos na Tarefa + CRUD. ✅ FEITO
  - inclui campo `identificadores` (chave e-validador) e endpoint `POST /obrigacoes/copiar-empresa`.
- **C (tela):** página `frontend/src/pages/Obrigacoes.jsx` (lista + modal completo,
  multi-select de empresas, alvo por regime/segmento, meses ativos, botão "Copiar
  de outra empresa"); rota `/obrigacoes` + item na sidebar (Cadastro). ✅ FEITO
- **B (gerador):** `services/gerador.py` (competência + prazo dia-útil + alvo + dedupe),
  endpoint `POST /obrigacoes/gerar {mes,ano,obrigacao_ids?,empresa_ids?}` (flag
  alocar_obrigacao), e job automático no scheduler (dia 1, 6:00). ✅ FEITO
  Os dois recortes são opcionais e vazio significa "todas": `obrigacao_ids` gera só
  as obrigações marcadas na lista, `empresa_ids` só as empresas escolhidas no modal.
  O recorte por empresa é **interseção** com o alvo da obrigação, nunca soma — escolher
  a empresa ali não a inscreve na obrigação. Prova: `provas/prova_gerar_recorte_empresas.py`.
- **D (e-validador):** `services/validador.py` (extrai CNPJ + competência + protocolo;
  casa obrigação por palavra-chave com limite de palavra; baixa a tarefa),
  `routes/evalidador.py` (`POST /evalidador/processar`, upload multi-PDF, perm evalidador),
  campos na Tarefa (protocolo_entrega/data_entrega/anexo_nome), tela
  `frontend/src/pages/EValidador.jsx` (upload + resultado). ✅ FEITO e testado com 2 recibos reais.

## 7.1 Tarefa: responsáveis múltiplos + supervisor + vínculo de obrigação (FEITO)
- Tarefa: M2M `responsaveis` (tabela `tarefa_responsaveis`) + `supervisor_id`; `responsavel_id`
  mantido como "principal" sincronizado (= 1º responsável) para escopo/compat.
- Obrigação ganhou `supervisor_id` (+ responsavel_id) → gerador propaga ambos para a tarefa.
- Escopo "proprias"/"setor" considera responsáveis (M2M) + supervisor.
- Alertas: todos os responsáveis + supervisor por e-mail; empresa por WhatsApp+e-mail.
- Tela Tarefas: obrigação (opcional, auto-preenche), responsáveis (checkboxes), supervisor.
- Setores agora são internos/globais (sem empresa) — corrigido conceito.

## 8. Pendências
- ~~Usuário-cliente + alertas por canal~~ ✅ FEITO: `usuario.tipo` (colaborador|cliente) +
  `usuario.empresa_id`; tela Usuários com tipo + empresa condicional; roteamento em
  `services/whatsapp.py::destinatarios_alerta` (colaborador→email; cliente/empresa→WhatsApp+email);
  `services/email.py` (SMTP por env). Testado: colaborador só email, cliente email+whatsapp.
  Falta só configurar SMTP_* / ZAP_* em produção para enviar de fato.
- Botão "Gerar competência" na tela de Obrigações (hoje só via API/scheduler).
- Reconciliar vocabulário de `segmento` (empresa usa `comercio_servico`; obrigação usa terceiro_setor).
- Armazenamento do anexo do comprovante em volume (produção) — hoje só grava o nome.

## 7. Identificação pelo e-validador (Fase D)
Trio extraído do documento recebido → baixa a tarefa:
- **CNPJ** → `empresa.cnpj`
- **identificador** (código de receita / palavra-chave) → `obrigacao.identificadores`
- **competência** (período de apuração) → `tarefa.competencia`
Acha `Tarefa(empresa+obrigação+competência)` pendente e grava protocolo+anexo+data.

## Fora de escopo (Acessórias)
12 campos de entrega por mês (usamos regra única), integrações específicas do
Acessórias.
