from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Dict, Any, List
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

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: int
    ativo: bool
    bloqueado: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

# Setor (departamento interno do escritório — global, sem empresa)
class SetorBase(BaseModel):
    nome: str
    descricao: Optional[str] = None

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
    data_prazo: Optional[datetime] = None   # prazo interno (limite da equipe) — comanda os alertas
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
    obrigacao_id: Optional[int] = None
    competencia: Optional[str] = None
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
    created_at: datetime

    class Config:
        from_attributes = True

# Obrigação (modelo recorrente)
class ObrigacaoBase(BaseModel):
    nome: str
    mininome: Optional[str] = None
    identificadores: Optional[str] = None
    setor_id: Optional[int] = None
    responsavel_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    tempo_previsto_min: Optional[int] = None
    regra_prazo_tipo: str = "ultimo_dia_util"
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

class ObrigacaoCreate(ObrigacaoBase):
    empresa_ids: Optional[List[int]] = []

class ObrigacaoUpdate(BaseModel):
    nome: Optional[str] = None
    mininome: Optional[str] = None
    identificadores: Optional[str] = None
    setor_id: Optional[int] = None
    responsavel_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    tempo_previsto_min: Optional[int] = None
    regra_prazo_tipo: Optional[str] = None
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

class ObrigacaoResponse(ObrigacaoBase):
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