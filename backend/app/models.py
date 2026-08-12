from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text, Boolean, Enum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

# Vínculo N:N entre obrigação (modelo) e empresas (exceções/inclusões explícitas)
obrigacao_empresa = Table(
    "obrigacao_empresa",
    Base.metadata,
    Column("obrigacao_id", Integer, ForeignKey("obrigacoes.id"), primary_key=True),
    Column("empresa_id", Integer, ForeignKey("empresas.id"), primary_key=True),
)

# Tarefa pode ter vários responsáveis (M2M).
tarefa_responsaveis = Table(
    "tarefa_responsaveis",
    Base.metadata,
    Column("tarefa_id", Integer, ForeignKey("tarefas.id"), primary_key=True),
    Column("usuario_id", Integer, ForeignKey("usuarios.id"), primary_key=True),
)

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
    grupo = Column(String(20), default="usuario")  # admin | gestor | analista | consulta | usuario(legado)
    permissoes = Column(Text, nullable=True)  # JSON de overrides sobre o preset do papel; NULL = herda 100%
    tipo = Column(String(20), default="colaborador")  # colaborador | cliente
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)  # cliente pertence a uma empresa
    bloqueado = Column(Boolean, default=False)  # bloqueado -> não loga, não aparece, tarefas somem
    gestor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    setor_id = Column(Integer, ForeignKey("setores.id"), nullable=True)  # departamento interno do colaborador
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    gestor = relationship("Usuario", remote_side=[id], foreign_keys=[gestor_id])
    setor = relationship("Setor", foreign_keys=[setor_id])
    empresa = relationship("Empresa", foreign_keys=[empresa_id])
    tarefas = relationship("Tarefa", back_populates="responsavel", foreign_keys="Tarefa.responsavel_id")

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    razao_social = Column(String(200), nullable=False)
    cnpj = Column(String(20), unique=True, index=True)
    nome_fantasia = Column(String(100))
    email = Column(String(100))
    telefone = Column(String(20))
    endereco = Column(Text)
    regime_tributario = Column(String(30), default="indefinido")  # indefinido|lucro_real|lucro_presumido|mei|simples_nacional|terceiro_setor|imune|isento
    segmento = Column(String(30))  # comercio|servico|comercio_servico|industria
    grupo = Column(String(80))     # grupo econômico (ex.: Markbuilding)
    # Responsável/supervisor padrão do cliente — as tarefas geradas herdam daqui.
    responsavel_id = Column(Integer, ForeignKey("usuarios.id"))
    supervisor_id = Column(Integer, ForeignKey("usuarios.id"))
    bloqueado = Column(Boolean, default=False)  # bloqueada -> tarefas somem, gerador ignora
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tarefas = relationship("Tarefa", back_populates="empresa")
    responsavel = relationship("Usuario", foreign_keys=[responsavel_id])
    supervisor = relationship("Usuario", foreign_keys=[supervisor_id])

class Setor(Base):
    __tablename__ = "setores"

    # Setor = departamento INTERNO do escritório (Fiscal, Contábil, DP...).
    # Global — não pertence a nenhuma empresa cliente.
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tarefas = relationship("Tarefa", back_populates="setor")


class Grupo(Base):
    __tablename__ = "grupos"

    # Papel/grupo de acesso. A matriz de permissões (recursos + escopo + flags)
    # fica no JSON `permissoes`. 'sistema' protege os papéis nativos de exclusão.
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(30), unique=True, nullable=False, index=True)
    label = Column(String(60), nullable=False)
    descricao = Column(Text)
    permissoes = Column(Text)          # JSON da matriz completa
    sistema = Column(Boolean, default=False)  # nativo — não pode ser excluído
    ativo = Column(Boolean, default=True)     # bloqueado -> não pode ser atribuído
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Tarefa(Base):
    __tablename__ = "tarefas"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    setor_id = Column(Integer, ForeignKey("setores.id"))
    responsavel_id = Column(Integer, ForeignKey("usuarios.id"))  # principal (= 1º dos responsaveis); mantido p/ escopo/compat
    supervisor_id = Column(Integer, ForeignKey("usuarios.id"))
    obrigacao_id = Column(Integer, ForeignKey("obrigacoes.id"), nullable=True)  # de qual modelo veio
    competencia = Column(String(7))  # "MM/AAAA" — chave de baixa do e-validador
    # Baixa pelo e-validador (comprovante de entrega)
    protocolo_entrega = Column(String(120))
    data_entrega = Column(DateTime(timezone=True))
    anexo_nome = Column(String(200))
    upload_token = Column(String(64), unique=True, index=True)  # link público de envio do comprovante
    status = Column(Enum(StatusTarefa), default=StatusTarefa.PENDENTE)
    prioridade = Column(Enum(PrioridadeTarefa), default=PrioridadeTarefa.MEDIA)
    data_inicio = Column(DateTime(timezone=True))
    data_prazo = Column(DateTime(timezone=True))  # prazo interno — comanda alertas (nulo em tarefa-modelo copiada)
    data_vencimento = Column(DateTime(timezone=True))             # vencimento fiscal/legal
    gera_multa = Column(Boolean, default=False)
    data_conclusao = Column(DateTime(timezone=True))
    observacoes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="tarefas")
    setor = relationship("Setor", back_populates="tarefas")
    responsavel = relationship("Usuario", foreign_keys=[responsavel_id], back_populates="tarefas")
    supervisor = relationship("Usuario", foreign_keys=[supervisor_id])
    responsaveis = relationship("Usuario", secondary=tarefa_responsaveis)


class Obrigacao(Base):
    """Modelo recorrente que gera tarefas por competência (ver OBRIGACOES_SPEC.md)."""
    __tablename__ = "obrigacoes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False)
    mininome = Column(String(50))                 # nome curto (ex.: "DARF 0220")
    identificadores = Column(String(200))          # códigos/palavras que o e-validador procura no PDF (CSV: "0220,IRPJ")
    setor_id = Column(Integer, ForeignKey("setores.id"), nullable=True)
    responsavel_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)  # responsável padrão da tarefa gerada
    supervisor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)   # supervisor padrão da tarefa gerada
    tempo_previsto_min = Column(Integer)

    # Regra de prazo
    regra_prazo_tipo = Column(String(20), default="ultimo_dia_util")  # ultimo_dia_util|dia_fixo|primeiro_dia_util
    regra_prazo_dia = Column(Integer)             # dia do mês quando dia_fixo
    meses_ativos = Column(String(40), default="1,2,3,4,5,6,7,8,9,10,11,12")  # CSV
    lembrar_dias_antes = Column(Integer, default=5)
    tipo_dias = Column(String(10), default="corridos")     # corridos|uteis
    ajuste_nao_util = Column(String(12), default="antecipar")  # antecipar|postergar|nenhum
    sabado_util = Column(Boolean, default=False)
    competencia_ref = Column(String(15), default="mes_anterior")  # mes_anterior|mesmo_mes|mes_seguinte|ano_anterior

    exige_robo = Column(Boolean, default=False)
    passivel_multa = Column(Boolean, default=False)
    alerta_guia_nao_lida = Column(Boolean, default=False)
    ativa = Column(Boolean, default=True)
    comentario_padrao = Column(Text)

    # Público-alvo por regra (CSV; vazio = todos)
    aplica_regimes = Column(String(120))
    aplica_segmentos = Column(String(120))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    setor = relationship("Setor")
    responsavel = relationship("Usuario", foreign_keys=[responsavel_id])
    supervisor = relationship("Usuario", foreign_keys=[supervisor_id])
    empresas = relationship("Empresa", secondary=obrigacao_empresa)

    @property
    def empresa_ids(self):
        return [e.id for e in self.empresas]


class Substituicao(Base):
    """Substituição de responsável — temporária (férias/doença) ou definitiva."""
    __tablename__ = "substituicoes"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)     # quem se ausenta
    substituto_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)  # quem cobre
    tipo = Column(String(12), default="temporaria")  # temporaria | definitiva
    data_inicio = Column(Date)
    data_fim = Column(Date)       # só temporária
    motivo = Column(String(120))
    ativa = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", foreign_keys=[usuario_id])
    substituto = relationship("Usuario", foreign_keys=[substituto_id])


class Configuracao(Base):
    """Configurações do sistema (chave-valor). Ex.: notificações/alertas."""
    __tablename__ = "configuracoes"

    chave = Column(String(60), primary_key=True)
    valor = Column(Text)


class Modelo(Base):
    """Repositório de documentos-modelo do e-validador.
    Você sobe um comprovante/recibo/relatório, o sistema lê e guarda a
    'impressão digital' (texto + campos identificados). Cada modelo casa com
    uma Empresa (via CNPJ) e uma Obrigação (via identificador), e alimenta o
    reconhecimento automático do e-validador. Só a leitura é guardada — não o
    arquivo original (sem necessidade de volume em produção)."""
    __tablename__ = "modelos"

    id = Column(Integer, primary_key=True, index=True)
    nome_arquivo = Column(String(200))
    cnpj = Column(String(14))                       # só dígitos (extraído do texto)
    razao_social_extraida = Column(String(200))     # nome lido no documento
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    obrigacao_id = Column(Integer, ForeignKey("obrigacoes.id"), nullable=True)
    tipo_documento = Column(String(30))             # recibo_entrega|comprovante_pagamento|relatorio|outro
    identificador = Column(String(120))             # trecho distintivo escolhido
    competencia_exemplo = Column(String(7))         # ex.: "05/2026"
    protocolo_exemplo = Column(String(120))
    texto_extraido = Column(Text)                   # fingerprint (texto lido)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa")
    obrigacao = relationship("Obrigacao")