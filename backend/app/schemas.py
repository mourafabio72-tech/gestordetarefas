from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum

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
    grupo: Optional[str] = "usuario"   # admin | gestor | usuario
    gestor_id: Optional[int] = None

class UsuarioCreate(UsuarioBase):
    senha: str

class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    senha: Optional[str] = None
    cargo: Optional[str] = None
    telefone: Optional[str] = None
    grupo: Optional[str] = None
    gestor_id: Optional[int] = None

class UsuarioResponse(UsuarioBase):
    id: int
    ativo: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Empresa
class EmpresaBase(BaseModel):
    razao_social: str
    cnpj: Optional[str] = None
    nome_fantasia: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: int
    ativo: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Setor
class SetorBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    empresa_id: int

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
    responsavel_id: Optional[int] = None
    prioridade: PrioridadeTarefa = PrioridadeTarefa.MEDIA
    data_inicio: Optional[datetime] = None
    data_prazo: datetime                    # prazo interno (limite da equipe) — comanda os alertas
    data_vencimento: Optional[datetime] = None  # vencimento fiscal/legal
    gera_multa: bool = False
    observacoes: Optional[str] = None

class TarefaCreate(TarefaBase):
    pass

class TarefaUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    setor_id: Optional[int] = None
    responsavel_id: Optional[int] = None
    status: Optional[StatusTarefa] = None
    prioridade: Optional[PrioridadeTarefa] = None
    data_prazo: Optional[datetime] = None
    data_vencimento: Optional[datetime] = None
    gera_multa: Optional[bool] = None
    data_conclusao: Optional[datetime] = None
    observacoes: Optional[str] = None

class TarefaResponse(TarefaBase):
    id: int
    status: StatusTarefa
    data_conclusao: Optional[datetime] = None
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

# Auth
class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: str
    senha: str