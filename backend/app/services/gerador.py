"""Gerador de tarefas a partir das obrigações (modelos recorrentes).

Roda por MÊS DE ENTREGA (o mês em que a demanda é trabalhada/entregue). Para
cada obrigação ativa cujo mês está em `meses_ativos`, calcula a competência
(pela `competencia_ref`) e o prazo (pela regra), resolve as empresas-alvo
(regra de regime/segmento ∪ vínculo explícito) e cria uma tarefa por empresa,
sem duplicar (dedupe por obrigacao_id + empresa_id + competencia).
"""
import calendar
from datetime import date, timedelta
from sqlalchemy.orm import Session
from ..models import Obrigacao, Empresa, Tarefa, StatusTarefa


def _csv_set(s):
    return {x.strip() for x in (s or "").split(",") if x.strip()}


# Apelidos antigos de `competencia_ref`, agora expressos como deslocamento em
# meses. Ficam aceitos para sempre: é o que está gravado nas obrigações já
# cadastradas, e converter dado em produção para ganhar uniformidade seria
# trocar risco por estética.
_REF_APELIDOS = {
    "mes_anterior": -1,
    "mesmo_mes": 0,
    "mes_seguinte": 1,
    "ano_anterior": -12,
}


def deslocamento_competencia(ref) -> int:
    """Quantos meses a competência fica ANTES do mês de entrega (negativo = antes).

    Aceita o apelido antigo ou o número direto ("-2", -2). O número é o que
    destrava a família SPED: EFD-Contribuições, DCTF e afins vencem no segundo
    mês subsequente ao fato gerador, e com os quatro apelidos de antes a
    competência saía um mês adiantada -- fato gerador de julho virava tarefa
    marcada como agosto, e o comprovante não casava na baixa.
    """
    if ref is None or ref == "":
        return -1                      # o padrão histórico do campo
    if isinstance(ref, int):
        return ref
    texto = str(ref).strip()
    if texto in _REF_APELIDOS:
        return _REF_APELIDOS[texto]
    try:
        return int(texto)
    except ValueError:
        return -1                      # valor estranho não pode gerar tarefa fora de hora


def calc_competencia(mes_entrega: int, ano_entrega: int, ref) -> str:
    """Competência (MM/AAAA) referida por um mês de entrega."""
    desloc = deslocamento_competencia(ref)
    # Aritmética em meses absolutos: atravessa qualquer virada de ano, inclusive
    # deslocamento maior que 12. Somar e "corrigir depois" só funcionava para um
    # mês de diferença.
    total = (ano_entrega * 12 + (mes_entrega - 1)) + desloc
    a, m = divmod(total, 12)
    return f"{m + 1:02d}/{a:04d}"


def _e_dia_util(d: date, sabado_util: bool) -> bool:
    wd = d.weekday()  # 0=seg ... 6=dom
    if wd == 6:
        return False
    if wd == 5:
        return sabado_util
    return True


def _nth_dia_util(ano: int, mes: int, n: int, sabado_util: bool) -> date:
    """Data do N-ésimo dia útil do mês (1 = primeiro dia útil).
    Se N passar da quantidade de dias úteis, devolve o último dia útil."""
    ultimo = calendar.monthrange(ano, mes)[1]
    conta, ultima_util = 0, date(ano, mes, 1)
    for dia in range(1, ultimo + 1):
        d = date(ano, mes, dia)
        if _e_dia_util(d, sabado_util):
            ultima_util = d
            conta += 1
            if conta >= max(int(n or 1), 1):
                return d
    return ultima_util


def calc_prazo(mes: int, ano: int, tipo: str, dia_fixo, ajuste: str, sabado_util: bool) -> date:
    """Data-limite no mês de entrega, ajustada a dia útil conforme a regra."""
    ultimo = calendar.monthrange(ano, mes)[1]
    if tipo == "dia_util":
        # N-ésimo dia útil — já é dia útil, não precisa de ajuste
        return _nth_dia_util(ano, mes, int(dia_fixo or 1), sabado_util)
    if tipo == "primeiro_dia_util":
        d = date(ano, mes, 1)
    elif tipo == "dia_fixo":
        d = date(ano, mes, min(int(dia_fixo or ultimo), ultimo))
    else:  # ultimo_dia_util (default)
        d = date(ano, mes, ultimo)

    if ajuste == "nenhum":
        return d
    passo = timedelta(days=-1) if ajuste == "antecipar" else timedelta(days=1)
    # limite de segurança para não estourar o mês em casos degenerados
    for _ in range(31):
        if _e_dia_util(d, sabado_util):
            return d
        d += passo
    return d


def calc_marco_fechamento(empresa, mes: int, ano: int, sabado_util: bool = False):
    """Data do fechamento contábil DESTA empresa no mês de entrega, ou None.

    None quer dizer "esta empresa não usa marco" -- e aí toda obrigação dela cai
    no prazo legal próprio, que é o comportamento de sempre.
    """
    tipo = (getattr(empresa, "fechamento_tipo", None) or "").strip()
    if not tipo:
        return None
    return calc_prazo(mes, ano, tipo, getattr(empresa, "fechamento_dia", None),
                      "antecipar", sabado_util)


def calc_vencimento(o, empresa, mes: int, ano: int):
    """Vencimento da tarefa: ancorado no marco da empresa, ou regra própria.

    Duas obrigações convivem no mesmo escritório e não se parecem:

      · SPED, DEFIS, DARF -- prazo é lei, igual para toda empresa. Regra própria,
        e nada muda para elas (é o caso da imensa maioria, e o padrão).
      · Etapas do fechamento -- lançar notas, conciliar, fechar balancete. Não
        têm data legal: têm que caber ANTES do fechamento daquele cliente, que
        varia de cliente para cliente.

    Para as segundas, a data sai do marco da empresa recuado por
    `ancora_dias_antes`. Muda o marco de um cliente e a cadeia inteira dele
    desloca junto, sem revisar obrigação por obrigação.

    Empresa ancorada mas SEM marco definido cai na regra própria da obrigação:
    falta de cadastro não pode impedir a tarefa de nascer.
    """
    sab = bool(o.sabado_util)
    if (o.ancora or "") == "fechamento":
        marco = calc_marco_fechamento(empresa, mes, ano, sab)
        if marco is not None:
            dias = int(o.ancora_dias_antes or 0)
            if dias <= 0:
                return marco                     # é o próprio marco (o balancete)
            # Recuar N dias a partir do marco é a MESMA conta do prazo interno.
            return calc_prazo_interno(marco, dias, o.ancora_tipo_dias or "uteis", sab)
    return calc_prazo(mes, ano, o.regra_prazo_tipo, o.regra_prazo_dia,
                      o.ajuste_nao_util, sab)


def _dia_util_anterior(d: date, sabado_util: bool) -> date:
    """Recua até cair num dia útil (inclui o próprio d se já for útil)."""
    for _ in range(31):
        if _e_dia_util(d, sabado_util):
            return d
        d -= timedelta(days=1)
    return d


def calc_prazo_interno(vencimento: date, dias_antes, tipo_dias: str, sabado_util: bool) -> date:
    """Prazo interno (técnico) = vencimento antecipado por `dias_antes`.
    tipo_dias='uteis' conta só dias úteis; 'corridos' conta corridos e depois
    ajusta para o dia útil anterior. dias_antes<=0 → cai no próprio vencimento."""
    n = int(dias_antes or 0)
    if n <= 0:
        return _dia_util_anterior(vencimento, sabado_util)
    if (tipo_dias or "corridos") == "uteis":
        d = vencimento
        recuados = 0
        for _ in range(365):
            d -= timedelta(days=1)
            if _e_dia_util(d, sabado_util):
                recuados += 1
                if recuados >= n:
                    return d
        return d
    # corridos: recua N dias corridos e cai no dia útil anterior
    return _dia_util_anterior(vencimento - timedelta(days=n), sabado_util)


def _no_alvo(o: Obrigacao, e: Empresa) -> bool:
    """A empresa `e` é alvo da obrigação `o`? Casa a regra (regime/segmento)
    OU está vinculada explicitamente. (Não checa ativo/bloqueado — quem chama filtra.)"""
    regimes = _csv_set(o.aplica_regimes)
    segmentos = _csv_set(o.aplica_segmentos)
    ok_reg = (not regimes) or (e.regime_tributario in regimes)
    ok_seg = (not segmentos) or (e.segmento in segmentos)
    if ok_reg and ok_seg:
        return True
    return any(x.id == e.id for x in o.empresas)  # inclusão explícita


def empresas_alvo(db: Session, o: Obrigacao):
    """Empresas que esta obrigação alcança.

    Dois modos, porque as duas perguntas existem no escritório:

    · 'regra' (padrão) -- empresas que casam regime/segmento UNIÃO as vinculadas
      à mão. É como sempre funcionou. Campo de regra vazio quer dizer TODOS.
    · 'vinculadas' -- SOMENTE as vinculadas. Para obrigação que é de um cliente
      específico, e não de um perfil. Antes isso era impossível: com a regra
      vazia a obrigação pegava todo mundo, e vincular empresas só somava.
    """
    if (o.alvo_modo or "regra") == "vinculadas":
        return [e for e in o.empresas if e.ativo and not e.bloqueado]

    alvo = {}
    for e in db.query(Empresa).filter(Empresa.ativo == True, Empresa.bloqueado == False).all():
        if _no_alvo(o, e):
            alvo[e.id] = e
    for e in o.empresas:            # inclusões explícitas (mesmo fora da regra)
        if e.ativo and not e.bloqueado:
            alvo[e.id] = e
    return list(alvo.values())


def _resp_do_setor(db: Session, empresa_id: int, setor_id):
    """Responsável (analista) da empresa naquele setor, pela matriz. None se não definido."""
    if not setor_id:
        return None
    from ..models import EmpresaSetorResponsavel
    vin = (db.query(EmpresaSetorResponsavel)
           .filter(EmpresaSetorResponsavel.empresa_id == empresa_id,
                   EmpresaSetorResponsavel.setor_id == setor_id)
           .first())
    return vin.responsavel if (vin and vin.responsavel) else None


def _gestor_do_setor(db: Session, setor_id):
    """Gestor cadastrado no setor, ou None."""
    if not setor_id:
        return None
    from ..models import Setor
    s = db.query(Setor.gestor_id).filter(Setor.id == setor_id).first()
    return s[0] if s else None


def _detalhe_empresa(db: Session, empresa_id: int, obrigacao_id: int):
    """Detalhe/complemento fixo desta empresa nesta obrigação (ou None)."""
    from ..models import EmpresaObrigacaoDetalhe
    d = (db.query(EmpresaObrigacaoDetalhe)
         .filter(EmpresaObrigacaoDetalhe.empresa_id == empresa_id,
                 EmpresaObrigacaoDetalhe.obrigacao_id == obrigacao_id).first())
    return (d.observacao or "").strip() if d and d.observacao else None


def _empresa_atende(db: Session, empresa_id: int, setor_id) -> bool:
    """A empresa atende (contratou) o serviço deste setor? Empresa sem nenhuma
    configuração atende todos (retrocompatível); com configuração, só os marcados.
    Obrigação sem setor sempre gera."""
    if not setor_id:
        return True
    from ..models import EmpresaSetorResponsavel
    total = db.query(EmpresaSetorResponsavel).filter(EmpresaSetorResponsavel.empresa_id == empresa_id).count()
    if total == 0:
        return True
    return db.query(EmpresaSetorResponsavel).filter(
        EmpresaSetorResponsavel.empresa_id == empresa_id,
        EmpresaSetorResponsavel.setor_id == setor_id).count() > 0


def _criar_tarefa_se_nova(db: Session, o: Obrigacao, emp: Empresa,
                          competencia: str, prazo: date, vencimento: date = None) -> bool:
    """Cria a tarefa (obrigação × empresa × competência) se ainda não existir.
    Retorna True se criou, False se já existia (dedupe)."""
    # Empresa não atende (não contratou) o setor desta obrigação → não gera.
    if not _empresa_atende(db, emp.id, o.setor_id):
        return False
    existe = (db.query(Tarefa)
              .filter(Tarefa.obrigacao_id == o.id,
                      Tarefa.empresa_id == emp.id,
                      Tarefa.competencia == competencia)
              .first())
    if existe:
        return False
    # Responsável = analista da empresa no setor da obrigação (matriz); fallback
    # no responsável padrão da obrigação. Supervisor = gestor desse responsável.
    resp = _resp_do_setor(db, emp.id, o.setor_id) or o.responsavel
    # Supervisor, do mais específico ao mais geral -- a mesma escada que o app
    # já usa para o responsável (matriz da empresa vence o padrão da obrigação):
    #   1. gestor da própria pessoa;
    #   2. gestor do SETOR, que cobre a equipe inteira com um cadastro só;
    #   3. supervisor padrão da obrigação.
    # Sem o degrau do meio, quem não tem gestor_id preenchido gerava tarefa sem
    # supervisor -- e ninguém era avisado do atraso.
    sup_id = ((resp.gestor_id if resp else None)
              or _gestor_do_setor(db, o.setor_id)
              or o.supervisor_id)
    # Detalhe fixo da empresa nesta obrigação (ex.: "Banco Itaú") entra na descrição.
    descricao = o.comentario_padrao or ""
    det = _detalhe_empresa(db, emp.id, o.id)
    if det:
        descricao = f"{descricao}\n{det}".strip() if descricao else det
    nova = Tarefa(
        titulo=o.nome,
        descricao=descricao,
        empresa_id=emp.id,
        setor_id=o.setor_id,
        responsavel_id=(resp.id if resp else None),
        supervisor_id=sup_id,
        obrigacao_id=o.id,
        competencia=competencia,
        status=StatusTarefa.PENDENTE,
        data_prazo=prazo,
        data_vencimento=vencimento,
        gera_multa=bool(o.passivel_multa),
    )
    if resp:
        nova.responsaveis = [resp]
    db.add(nova)
    return True


def gerar_tarefas(db: Session, mes_entrega: int, ano_entrega: int, obrigacao_ids: list = None) -> dict:
    criadas, puladas, por_obrigacao = 0, 0, []
    q = db.query(Obrigacao).filter(Obrigacao.ativa == True)
    # Recorte opcional: gerar só as obrigações escolhidas na tela. Sem isso, a
    # única opção era gerar TODAS as ativas -- e num escritório com dezenas de
    # obrigações e dezenas de clientes isso são milhares de tarefas de uma vez,
    # mesmo quando se quer só a obrigação que acabou de ser cadastrada.
    if obrigacao_ids:
        q = q.filter(Obrigacao.id.in_(obrigacao_ids))
    obrigacoes = q.all()
    for o in obrigacoes:
        if str(mes_entrega) not in _csv_set(o.meses_ativos):
            continue
        competencia = calc_competencia(mes_entrega, ano_entrega, o.competencia_ref)
        n_o = 0
        for emp in empresas_alvo(db, o):
            # Vencimento POR EMPRESA: obrigação ancorada no fechamento tem data
            # diferente em cada cliente, então o cálculo entra no laço.
            vencimento = calc_vencimento(o, emp, mes_entrega, ano_entrega)
            prazo_interno = calc_prazo_interno(vencimento, o.lembrar_dias_antes,
                                               o.tipo_dias, bool(o.sabado_util))
            if _criar_tarefa_se_nova(db, o, emp, competencia, prazo_interno, vencimento):
                criadas += 1
                n_o += 1
            else:
                puladas += 1
        if n_o:
            por_obrigacao.append({"obrigacao": o.nome, "competencia": competencia,
                                  "ancorada": (o.ancora or "") == "fechamento",
                                  "criadas": n_o})
    db.commit()
    return {"mes_entrega": f"{mes_entrega:02d}/{ano_entrega:04d}",
            "criadas": criadas, "puladas": puladas, "detalhe": por_obrigacao}


def gerar_mes_atual(db: Session) -> dict:
    hoje = date.today()
    return gerar_tarefas(db, hoje.month, hoje.year)


def gerar_para_empresa(db: Session, empresa: Empresa, mes_entrega: int, ano_entrega: int) -> dict:
    """Gera as tarefas de UMA empresa para o mês de entrega informado — usada quando
    a empresa é cadastrada (vínculo automático por regime/segmento). Percorre todas as
    obrigações ativas do mês cuja regra bate com a empresa e cria as tarefas faltantes."""
    if not empresa.ativo or empresa.bloqueado:
        return {"criadas": 0, "puladas": 0}
    criadas, puladas = 0, 0
    for o in db.query(Obrigacao).filter(Obrigacao.ativa == True).all():
        if str(mes_entrega) not in _csv_set(o.meses_ativos):
            continue
        if not _no_alvo(o, empresa):
            continue
        competencia = calc_competencia(mes_entrega, ano_entrega, o.competencia_ref)
        vencimento = calc_vencimento(o, empresa, mes_entrega, ano_entrega)
        prazo_interno = calc_prazo_interno(vencimento, o.lembrar_dias_antes,
                                           o.tipo_dias, bool(o.sabado_util))
        if _criar_tarefa_se_nova(db, o, empresa, competencia, prazo_interno, vencimento):
            criadas += 1
        else:
            puladas += 1
    db.commit()
    return {"criadas": criadas, "puladas": puladas}


def gerar_empresa_mes_atual(db: Session, empresa: Empresa) -> dict:
    hoje = date.today()
    return gerar_para_empresa(db, empresa, hoje.month, hoje.year)
