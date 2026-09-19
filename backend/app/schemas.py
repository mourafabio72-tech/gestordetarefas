from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, date
from enum import Enum
import json


class UsuarioMini(BaseModel):
    id: int
    nome: str

    class Config:
        from_attributes = True

class StatusTarefa(str, Enum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    ATRASADA = "atrasada"
    CANCELADA = "cancelada"

class PrioridadeTarefa(str, Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"

# Usuário
class UsuarioBase(BaseModel):
    nome: str
    email: str
    cargo: Optional[str] = None
    telefone: Optional[str] = None
    grupo: Optional[str] = "usuario"   # admin | gestor | analista | consulta | usuario
    permissoes: Optional[Dict[str, Any]] = None  # overrides sobre o preset do papel
    tipo: Optional[str] = "colaborador"  # colaborador | cliente
    empresa_id: Optional[int] = None     # empresa do cliente (quando tipo=cliente)
    gestor_id: Optional[int] = None
    setor_id: Optional[int] = None       # departamento interno (colaborador)

    @field_validator("permissoes", mode="before")
    @classmethod
    def _parse_permissoes(cls, v):
        # No banco vem como string JSON; do cliente vem como dict. Normaliza p/ dict.
        if isinstance(v, str):
            if not v.strip():
                return None
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return None
        return v

class UsuarioCreate(UsuarioBase):
    senha: str

class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    senha: Optional[str] = None
    cargo: Optional[str] = None
    telefone: Optional[str] = None
    grupo: Optional[str] = None
    permissoes: Optional[Dict[str, Any]] = None
    tipo: Optional[str] = None
    empresa_id: Optional[int] = None
    gestor_id: Optional[int] = None
    setor_id: Optional[int] = None

class UsuarioResponse(UsuarioBase):
    id: int
    ativo: bool
    bloqueado: bool = False
    ativado: Optional[bool] = None   # True=ativou; False=pendente; None=legado
    created_at: datetime

    class Config:
        from_attributes = True

class MeResponse(BaseModel):
    """Usuário logado + permissão efetiva já resolvida (preset + overrides)."""
    id: int
    nome: str
    email: str
    cargo: Optional[str] = None
    grupo: Optional[str] = None
    permissoes_efetivas: Dict[str, Any]

# Empresa
class EmpresaBase(BaseModel):
    razao_social: str
    cnpj: Optional[str] = None
    nome_fantasia: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    regime_tributario: Optional[str] = "indefinido"
    segmento: Optional[str] = None
    grupo: Optional[str] = None
    ativo: Optional[bool] = True
    responsavel_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    # Marco de fechamento contábil desta empresa (ver models.Empresa)
    fechamento_tipo: Optional[str] = None
    fechamento_dia: Optional[int] = None

    @field_validator("fechamento_dia", "fechamento_tipo", mode="before")
    @classmethod
    def _vazio_e_nada(cls, v):
        """Campo em branco no formulário chega como "" e não como ausente.

        Sem isto, salvar a empresa com o marco de fechamento vazio derrubava o
        cadastro INTEIRO num 422 -- inclusive quem só queria trocar o segmento,
        porque o formulário envia todos os campos de uma vez.
        """
        if isinstance(v, str) and not v.strip():
            return None
        return v

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: int
    ativo: bool
    bloqueado: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

# Setor (departamento interno do escritório, global, sem empresa)
class SetorBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    gestor_id: Optional[int] = None

class SetorCreate(SetorBase):
    pass

class SetorResponse(SetorBase):
    id: int
    ativo: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Tarefa
class TarefaBase(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    empresa_id: int
    setor_id: Optional[int] = None
    obrigacao_id: Optional[int] = None
    competencia: Optional[str] = None
    responsavel_ids: Optional[List[int]] = None  # múltiplos responsáveis
    supervisor_id: Optional[int] = None
    prioridade: PrioridadeTarefa = PrioridadeTarefa.MEDIA
    data_inicio: Optional[datetime] = None
    data_prazo: Optional[datetime] = None   # prazo interno (limite da equipe), comanda os alertas
    data_vencimento: Optional[datetime] = None  # vencimento fiscal/legal
    gera_multa: bool = False
    observacoes: Optional[str] = None

class TarefaCreate(TarefaBase):
    pass

class TarefaUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    setor_id: Optional[int] = None
    obrigacao_id: Optional[int] = None
    responsavel_ids: Optional[List[int]] = None
    supervisor_id: Optional[int] = None
    status: Optional[StatusTarefa] = None
    prioridade: Optional[PrioridadeTarefa] = None
    data_prazo: Optional[datetime] = None
    data_vencimento: Optional[datetime] = None
    gera_multa: Optional[bool] = None
    data_conclusao: Optional[datetime] = None
    observacoes: Optional[str] = None

class TarefaResponse(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    empresa_id: int
    setor_id: Optional[int] = None
    setor_nome: Optional[str] = None            # vem do relacionamento; vale para setor inativo
    obrigacao_id: Optional[int] = None
    competencia: Optional[str] = None
    fechamento_cliente: Optional[date] = None   # marco do cliente no mês desta tarefa
    responsaveis: List[UsuarioMini] = []
    supervisor: Optional[UsuarioMini] = None
    prioridade: PrioridadeTarefa
    data_inicio: Optional[datetime] = None
    data_prazo: Optional[datetime] = None
    data_vencimento: Optional[datetime] = None
    gera_multa: bool = False
    observacoes: Optional[str] = None
    status: StatusTarefa
    data_conclusao: Optional[datetime] = None
    protocolo_entrega: Optional[str] = None
    data_entrega: Optional[datetime] = None
    anexo_nome: Optional[str] = None
    # Documento que o escritório ENTREGA ao cliente, e o rastro do link dele.
    saida_nome: Optional[str] = None
    saida_downloads: Optional[int] = 0          # quantas vezes o cliente abriu o link
    saida_baixada_em: Optional[datetime] = None
    sentido: Optional[str] = "receber"          # vem da obrigação: receber | entregar | transmitir | interna
    exige_documento: bool = False   # baixa só pelo e-validador (deriva da obrigação)
    # "Não se aplica a esta empresa". A tarefa fica CANCELADA, e é este campo
    # que diz à tela para mostrar o rótulo certo: cancelar é desistir, e isto
    # aqui é uma decisão de que o trabalho nunca coube àquele cliente.
    nao_se_aplica: bool = False
    nao_se_aplica_motivo: Optional[str] = None
    nao_se_aplica_em: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Para que lado o documento anda (ver `Obrigacao.sentido` em models.py). Lista
# fechada na ENTRADA: até 2026-09-15 era texto livre, e qualquer palavra gravava.
Sentido = Literal["receber", "entregar", "interna", "transmitir"]


def _sentido_em_branco(v):
    """Sentido vazio é "não informado", e não valor inválido.

    Obrigação antiga pode ter `""` gravado. A tela abre a obrigação, mostra
    Receber marcado e manda o `""` de volta ao salvar, mesmo que só o nome
    tenha mudado. Recusar o vazio travaria a edição de qualquer campo dela.
    `None` se comporta como `receber` em todo o sistema.
    """
    if isinstance(v, str) and not v.strip():
        return None
    return v

# Obrigação (modelo recorrente)
class ObrigacaoBase(BaseModel):
    nome: str
    sentido: Optional[Sentido] = "receber"
    _sentido_vazio = field_validator("sentido", mode="before")(_sentido_em_branco)
    mininome: Optional[str] = None
    identificadores: Optional[str] = None
    setor_id: Optional[int] = None
    responsavel_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    tempo_previsto_min: Optional[int] = None
    regra_prazo_tipo: str = "ultimo_dia_util"
    alvo_modo: Optional[str] = "regra"           # regra|vinculadas

    @field_validator("regra_prazo_dia", "ancora_dias_antes", "tempo_previsto_min",
                     "lembrar_dias_antes", mode="before")
    @classmethod
    def _numero_em_branco(cls, v):
        """Campo numérico vazio no formulário é "não informado", não erro.

        Terceira vez que este mesmo padrão aparece (marco da empresa, responsável
        por setor, e agora aqui): o formulário manda "" e o campo espera número,
        e o 422 derruba o salvamento INTEIRO -- inclusive de quem mexeu noutro
        campo. Aqui doía especialmente: trocar a regra para "N-ésimo dia útil"
        sem digitar o dia recusava o cadastro em vez de deixar em branco.
        """
        if isinstance(v, str) and not v.strip():
            return None
        return v
    ancora: Optional[str] = None                 # NULL|fechamento
    ancora_dias_antes: Optional[int] = 0
    ancora_tipo_dias: Optional[str] = "uteis"
    regra_prazo_dia: Optional[int] = None
    meses_ativos: str = "1,2,3,4,5,6,7,8,9,10,11,12"
    lembrar_dias_antes: int = 5
    tipo_dias: str = "corridos"
    ajuste_nao_util: str = "antecipar"
    sabado_util: bool = False
    competencia_ref: str = "mes_anterior"
    exige_robo: bool = False
    exige_documento: Optional[bool] = None   # baixa só pelo e-validador; NULL deriva de identificadores
    passivel_multa: bool = False
    alerta_guia_nao_lida: bool = False
    ativa: bool = True
    comentario_padrao: Optional[str] = None
    aplica_regimes: Optional[str] = None
    aplica_segmentos: Optional[str] = None

_COMP_APELIDOS = {"mes_anterior", "mesmo_mes", "mes_seguinte", "ano_anterior"}


def _meses_validos(v):
    """`meses_ativos` é CSV de 1 a 12, e nada mais.

    Até 2026-09-19 era texto livre: "a" gravava e a obrigação parava de gerar
    sem aviso nenhum. Repetido e fora de ordem não são erro, só se arrumam
    ("3,1,3" vira "1,3"). Vazio é erro: obrigação sem mês nunca gera, e quem
    quer isso desativa a obrigação. Por isso o vazio chega à rota, que sabe
    se a obrigação já era vazia no banco (legada, que a tela reenvia como leu)
    ou se alguém está esvaziando agora.
    """
    if v is None:
        return v
    if not str(v).strip():
        return ""        # a rota decide: criar sem mês é erro, legada vazia segue
    partes = [p.strip() for p in str(v).split(",")]
    if not all(p.isdigit() and 1 <= int(p) <= 12 for p in partes):
        raise ValueError("Marque ao menos um mês, de 1 a 12.")
    return ",".join(str(m) for m in sorted({int(p) for p in partes}))


def _competencia_valida(v):
    """Um dos quatro apelidos, ou o deslocamento em meses de -24 a 1.

    A anual usa número (-14 para entrega em março: janeiro do ano anterior,
    que é o que o recibo traz). Vazio é "não informado" e vira o padrão
    histórico, porque obrigação antiga pode ter "" gravado e a tela reenvia o
    que leu (a mesma armadilha do sentido vazio, fase 27).
    """
    texto = "" if v is None else str(v).strip()
    if not texto:
        # null também: gravado como NULL, derrubava a LISTAGEM inteira com
        # 500, porque a resposta exige texto (achado de 2026-09-19).
        return "mes_anterior"
    if texto in _COMP_APELIDOS:
        return texto
    try:
        n = int(texto)
    except ValueError:
        raise ValueError("Competência inválida.")
    if not -24 <= n <= 1:
        raise ValueError("Competência fora do intervalo de 24 meses antes a 1 depois.")
    return str(n)


# Os validadores moram na ENTRADA (Create e Update), e não no ObrigacaoBase:
# a resposta herda do Base, e dado antigo fora do formato derrubaria a
# listagem inteira com 500.
class ObrigacaoCreate(ObrigacaoBase):
    empresa_ids: Optional[List[int]] = []
    _meses = field_validator("meses_ativos", mode="before")(_meses_validos)

    @field_validator("meses_ativos")
    @classmethod
    def _criar_com_mes(cls, v):
        if not v:
            raise ValueError("Marque ao menos um mês, de 1 a 12.")
        return v
    _comp = field_validator("competencia_ref", mode="before")(_competencia_valida)

class ObrigacaoUpdate(BaseModel):
    nome: Optional[str] = None
    # Faltava até 2026-09-15: o Pydantic descarta campo não declarado sem erro,
    # então trocar o lado do documento pela tela devolvia 200 e não gravava.
    sentido: Optional[Sentido] = None
    _sentido_vazio = field_validator("sentido", mode="before")(_sentido_em_branco)
    mininome: Optional[str] = None
    identificadores: Optional[str] = None
    setor_id: Optional[int] = None
    responsavel_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    tempo_previsto_min: Optional[int] = None
    regra_prazo_tipo: Optional[str] = None
    alvo_modo: Optional[str] = None
    ancora: Optional[str] = None
    ancora_dias_antes: Optional[int] = None
    ancora_tipo_dias: Optional[str] = None
    regra_prazo_dia: Optional[int] = None
    meses_ativos: Optional[str] = None
    lembrar_dias_antes: Optional[int] = None
    tipo_dias: Optional[str] = None
    ajuste_nao_util: Optional[str] = None
    sabado_util: Optional[bool] = None
    competencia_ref: Optional[str] = None
    exige_robo: Optional[bool] = None
    exige_documento: Optional[bool] = None
    passivel_multa: Optional[bool] = None
    alerta_guia_nao_lida: Optional[bool] = None
    ativa: Optional[bool] = None
    comentario_padrao: Optional[str] = None
    aplica_regimes: Optional[str] = None
    aplica_segmentos: Optional[str] = None
    empresa_ids: Optional[List[int]] = None
    _meses = field_validator("meses_ativos", mode="before")(_meses_validos)
    _comp = field_validator("competencia_ref", mode="before")(_competencia_valida)

class ObrigacaoResponse(ObrigacaoBase):
    # A SAÍDA não aplica a lista fechada: obrigação antiga pode ter sentido nulo
    # ou vazio no banco, e validar aqui derrubaria a listagem inteira com 500.
    sentido: Optional[str] = "receber"
    id: int
    empresa_ids: List[int] = []
    created_at: datetime

    class Config:
        from_attributes = True

# Dashboard
class DashboardStats(BaseModel):
    total_tarefas: int
    pendentes: int
    em_andamento: int
    concluidas: int
    atrasadas: int
    vencendo_hoje: int
    vencendo_semana: int

# Substituição de responsável
class SubstituicaoCreate(BaseModel):
    usuario_id: int
    substituto_id: int
    tipo: str = "temporaria"          # temporaria | definitiva
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    motivo: Optional[str] = None

class SubstituicaoResponse(BaseModel):
    id: int
    usuario: UsuarioMini
    substituto: UsuarioMini
    tipo: str
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    motivo: Optional[str] = None
    ativa: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Auth
class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: str
    senha: str