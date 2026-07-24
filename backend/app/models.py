from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

class StatusTarefa(str, enum.Enum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    ATRASADA = "atrasada"
    CANCELADA = "cancelada"

class PrioridadeTarefa(str, enum.Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    cargo = Column(String(50))
    telefone = Column(String(20))
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tarefas = relationship("Tarefa", back_populates="responsavel")

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    razao_social = Column(String(200), nullable=False)
    cnpj = Column(String(18), unique=True, index=True)
    nome_fantasia = Column(String(100))
    email = Column(String(100))
    telefone = Column(String(20))
    endereco = Column(Text)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    setores = relationship("Setor", back_populates="empresa")
    tarefas = relationship("Tarefa", back_populates="empresa")

class Setor(Base):
    __tablename__ = "setores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="setores")
    tarefas = relationship("Tarefa", back_populates="setor")

class Tarefa(Base):
    __tablename__ = "tarefas"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    setor_id = Column(Integer, ForeignKey("setores.id"))
    responsavel_id = Column(Integer, ForeignKey("usuarios.id"))
    status = Column(Enum(StatusTarefa), default=StatusTarefa.PENDENTE)
    prioridade = Column(Enum(PrioridadeTarefa), default=PrioridadeTarefa.MEDIA)
    data_inicio = Column(DateTime(timezone=True))
    data_prazo = Column(DateTime(timezone=True), nullable=False)
    data_conclusao = Column(DateTime(timezone=True))
    observacoes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="tarefas")
    setor = relationship("Setor", back_populates="tarefas")
    responsavel = relationship("Usuario", back_populates="tarefas")