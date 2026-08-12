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


def calc_competencia(mes_entrega: int, ano_entrega: int, ref: str) -> str:
    """Competência (MM/AAAA) referida por um mês de entrega."""
    m, a = mes_entrega, ano_entrega
    if ref == "mes_anterior":
        m -= 1
    elif ref == "mes_seguinte":
        m += 1
    elif ref == "ano_anterior":
        a -= 1
    # normaliza virada de ano
    if m < 1:
        m += 12; a -= 1
    elif m > 12:
        m -= 12; a += 1
    return f"{m:02d}/{a:04d}"


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
    """Empresas ativas que casam a regra (regime/segmento) ∪ vínculos explícitos."""
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
                          competencia: str, prazo: date) -> bool:
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
    sup_id = (resp.gestor_id if resp else None) or o.supervisor_id
    nova = Tarefa(
        titulo=o.nome,
        descricao=o.comentario_padrao,
        empresa_id=emp.id,
        setor_id=o.setor_id,
        responsavel_id=(resp.id if resp else None),
        supervisor_id=sup_id,
        obrigacao_id=o.id,
        competencia=competencia,
        status=StatusTarefa.PENDENTE,
        data_prazo=prazo,
        gera_multa=bool(o.passivel_multa),
    )
    if resp:
        nova.responsaveis = [resp]
    db.add(nova)
    return True


def gerar_tarefas(db: Session, mes_entrega: int, ano_entrega: int) -> dict:
    criadas, puladas, por_obrigacao = 0, 0, []
    obrigacoes = db.query(Obrigacao).filter(Obrigacao.ativa == True).all()
    for o in obrigacoes:
        if str(mes_entrega) not in _csv_set(o.meses_ativos):
            continue
        competencia = calc_competencia(mes_entrega, ano_entrega, o.competencia_ref)
        prazo = calc_prazo(mes_entrega, ano_entrega, o.regra_prazo_tipo,
                           o.regra_prazo_dia, o.ajuste_nao_util, bool(o.sabado_util))
        n_o = 0
        for emp in empresas_alvo(db, o):
            if _criar_tarefa_se_nova(db, o, emp, competencia, prazo):
                criadas += 1
                n_o += 1
            else:
                puladas += 1
        if n_o:
            por_obrigacao.append({"obrigacao": o.nome, "competencia": competencia,
                                  "prazo": prazo.isoformat(), "criadas": n_o})
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
        prazo = calc_prazo(mes_entrega, ano_entrega, o.regra_prazo_tipo,
                           o.regra_prazo_dia, o.ajuste_nao_util, bool(o.sabado_util))
        if _criar_tarefa_se_nova(db, o, empresa, competencia, prazo):
            criadas += 1
        else:
            puladas += 1
    db.commit()
    return {"criadas": criadas, "puladas": puladas}


def gerar_empresa_mes_atual(db: Session, empresa: Empresa) -> dict:
    hoje = date.today()
    return gerar_para_empresa(db, empresa, hoje.month, hoje.year)
