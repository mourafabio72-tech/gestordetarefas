from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text, Boolean, Enum, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from datetime import datetime
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
    gestor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    setor_id = Column(Integer, ForeignKey("setores.id"), nullable=True)  # departamento interno do colaborador
    convite_token = Column(String(64), nullable=True)  # link de 1º acesso (define a própria senha)
    ativado = Column(Boolean, nullable=True)  # True=ativou; False=pendente; NULL=legado (considerado ativo)
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
    # Marco de fechamento contábil do mês DESTA empresa (ex.: "10º dia útil").
    # As obrigações que fazem parte do processo de fechamento se posicionam em
    # relação a ele, em vez de cada uma trazer a própria data: muda o marco, a
    # cadeia inteira desloca junto. Vazio = a empresa não usa marco, e toda
    # obrigação cai no prazo legal próprio, como sempre foi.
    fechamento_tipo = Column(String(20))   # dia_util|dia_fixo|ultimo_dia_util|primeiro_dia_util
    fechamento_dia = Column(Integer)       # qual dia (útil ou do mês), quando o tipo pede
    bloqueado = Column(Boolean, default=False)  # bloqueada -> tarefas somem, gerador ignora
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tarefas = relationship("Tarefa", back_populates="empresa")
    responsavel = relationship("Usuario", foreign_keys=[responsavel_id])
    supervisor = relationship("Usuario", foreign_keys=[supervisor_id])
    setor_responsaveis = relationship("EmpresaSetorResponsavel", cascade="all, delete-orphan")


class EmpresaSetorResponsavel(Base):
    """Responsável (analista) por setor, específico de cada empresa. O gestor da
    tarefa sai do gestor_id desse responsável — não se cadastra aqui."""
    __tablename__ = "empresa_setor_responsavel"
    __table_args__ = (UniqueConstraint("empresa_id", "setor_id", name="uq_empresa_setor"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    setor_id = Column(Integer, ForeignKey("setores.id"), nullable=False, index=True)
    responsavel_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    responsavel = relationship("Usuario", foreign_keys=[responsavel_id])


class EmpresaObrigacaoDetalhe(Base):
    """Detalhe/complemento fixo de uma empresa numa obrigação (ex.: 'Empréstimo —
    Banco Itaú'). Herdado na descrição de toda tarefa gerada dessa obrigação
    para essa empresa."""
    __tablename__ = "empresa_obrigacao_detalhe"
    __table_args__ = (UniqueConstraint("empresa_id", "obrigacao_id", name="uq_empresa_obrigacao_det"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    obrigacao_id = Column(Integer, ForeignKey("obrigacoes.id"), nullable=False, index=True)
    observacao = Column(Text)


class SaidaAcesso(Base):
    """Cada abertura do link do documento pelo cliente.

    O contador e a data ficam na tarefa para a tela mostrar sem consultar isto;
    aqui fica o detalhe de auditoria, que é o que responde "quem baixou e
    quando" quando o cliente diz que nunca recebeu.
    """
    __tablename__ = "saida_acessos"

    id = Column(Integer, primary_key=True, index=True)
    tarefa_id = Column(Integer, ForeignKey("tarefas.id"), nullable=False, index=True)
    ip = Column(String(60))
    user_agent = Column(String(300))
    # Nem toda requisição é o cliente abrindo. O WhatsApp busca o link para
    # montar a prévia, e visualizador de PDF pede o arquivo em partes. Tudo
    # fica registrado para auditoria; só o que é abertura de gente conta.
    contado = Column(Boolean, default=True)
    quando = Column(DateTime(timezone=True), server_default=func.now())


class TarefaEnvio(Base):
    """Cada vez que um documento saiu do escritório para o cliente.

    Tabela em vez de campos na tarefa porque reenvio acontece — o cliente
    perdeu, o número estava errado, a guia foi retificada — e sobrescrever o
    registro anterior apagaria justamente a prova de que a primeira via foi
    entregue no prazo.
    """
    __tablename__ = "tarefa_envios"

    id = Column(Integer, primary_key=True, index=True)
    tarefa_id = Column(Integer, ForeignKey("tarefas.id"), nullable=False, index=True)
    arquivo = Column(String(200))
    canal = Column(String(20))                 # whatsapp | email
    endereco = Column(String(200))
    destinatario = Column(String(200))         # nome de quem recebeu, para o histórico ler bem
    sucesso = Column(Boolean, default=False)
    detalhe = Column(Text)                     # erro do provedor, quando falha
    enviado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    enviado_em = Column(DateTime(timezone=True), server_default=func.now())


class Setor(Base):
    __tablename__ = "setores"

    # Setor = departamento INTERNO do escritório (Fiscal, Contábil, DP...).
    # Global — não pertence a nenhuma empresa cliente.
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    # Gestor do departamento. Vira supervisor das tarefas do setor quando o
    # responsável não tem gestor próprio — um cadastro por setor cobre a equipe
    # inteira, em vez de depender do gestor_id estar preenchido pessoa a pessoa.
    gestor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    gestor = relationship("Usuario", foreign_keys=[gestor_id])
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
    # index=True em tudo que a listagem filtra: `tarefas` é a tabela grande.
    # Base já existente não ganha índice por aqui (create_all só cria tabela
    # nova) -- quem cria em produção é `init_db.criar_indices()`.
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    setor_id = Column(Integer, ForeignKey("setores.id"), index=True)
    responsavel_id = Column(Integer, ForeignKey("usuarios.id"), index=True)  # principal (= 1º dos responsaveis); mantido p/ escopo/compat
    supervisor_id = Column(Integer, ForeignKey("usuarios.id"), index=True)
    obrigacao_id = Column(Integer, ForeignKey("obrigacoes.id"), nullable=True, index=True)  # de qual modelo veio
    competencia = Column(String(7), index=True)  # "MM/AAAA" — chave de baixa do e-validador
    # Fechamento contábil DO CLIENTE no mês desta tarefa, gravado na geração.
    # Fica no card para dar a régua: "vence dia 10, e o cliente fecha dia 15".
    # Gravado, e não calculado na hora, porque é a foto do que valia quando a
    # tarefa nasceu -- mudar o marco da empresa depois não reescreve o passado.
    fechamento_cliente = Column(Date)
    # Baixa pelo e-validador (comprovante de entrega)
    protocolo_entrega = Column(String(120))
    data_entrega = Column(DateTime(timezone=True))
    anexo_nome = Column(String(200))
    upload_token = Column(String(64), unique=True, index=True)  # link público de envio do comprovante
    # Documento que o ESCRITÓRIO entrega ao cliente (guia, boleto, relatório).
    # Campo separado do `anexo_nome` de propósito: um é o que entra, outro é o
    # que sai, e misturar os dois faria a tela mostrar comprovante de pagamento
    # onde deveria mostrar a guia a pagar.
    saida_nome = Column(String(200))
    # Link público do documento de saída. Existe para o WhatsApp levar um
    # endereço em vez do arquivo -- e, de quebra, é o que torna o download
    # rastreável: anexo sai do nosso alcance no instante do envio, link é uma
    # requisição ao nosso servidor.
    saida_token = Column(String(64), unique=True, index=True)
    saida_baixada_em = Column(DateTime(timezone=True))   # último acesso
    saida_downloads = Column(Integer, default=0)
    status = Column(Enum(StatusTarefa), default=StatusTarefa.PENDENTE, index=True)
    prioridade = Column(Enum(PrioridadeTarefa), default=PrioridadeTarefa.MEDIA)
    data_inicio = Column(DateTime(timezone=True))
    data_prazo = Column(DateTime(timezone=True), index=True)  # prazo interno — comanda alertas (nulo em tarefa-modelo copiada)
    data_vencimento = Column(DateTime(timezone=True))             # vencimento fiscal/legal
    gera_multa = Column(Boolean, default=False)
    data_conclusao = Column(DateTime(timezone=True))
    observacoes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="tarefas")
    setor = relationship("Setor", back_populates="tarefas")

    @property
    def sentido(self) -> str:
        """"receber" (comprovante do cliente) ou "entregar" (guia ao cliente).

        Sai da obrigação. Tarefa avulsa, sem obrigação, é "receber": é o
        comportamento que o sistema sempre teve, e mudar o padrão faria toda
        tarefa solta pedir um documento para enviar.
        """
        o = self.obrigacao
        return (o.sentido or "receber") if o else "receber"

    @property
    def setor_nome(self):
        """Nome do setor para a resposta da API.

        A tela não pode depender da listagem de setores para isto: aquela rota
        só devolve os ATIVOS, e desativar um setor apagaria o nome dele de todas
        as tarefas já existentes — o dado continua no banco, mas some da tela.
        """
        return self.setor.nome if self.setor else None
    responsavel = relationship("Usuario", foreign_keys=[responsavel_id], back_populates="tarefas")
    supervisor = relationship("Usuario", foreign_keys=[supervisor_id])
    responsaveis = relationship("Usuario", secondary=tarefa_responsaveis)
    obrigacao = relationship("Obrigacao", foreign_keys=[obrigacao_id])

    @property
    def exige_documento(self) -> bool:
        """Baixa só pelo e-validador? Flag da obrigação manda; NULL deriva de
        'identificadores'. Tarefa sem obrigação nunca exige."""
        o = self.obrigacao
        if o is None:
            return False
        if o.exige_documento is None:
            return bool((o.identificadores or "").strip())
        return bool(o.exige_documento)


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

    # Ancoragem no marco de fechamento da empresa. NULL (o padrão) = obrigação
    # com prazo legal próprio -- SPED, DEFIS e a maioria. 'fechamento' = etapa
    # do processo contábil, cujo vencimento sai do marco da empresa recuado por
    # `ancora_dias_antes` (0 = é o próprio marco, caso do balancete).
    ancora = Column(String(20))                       # NULL|fechamento
    ancora_dias_antes = Column(Integer, default=0)
    ancora_tipo_dias = Column(String(10), default="uteis")   # uteis|corridos

    exige_robo = Column(Boolean, default=False)
    # Baixa só pelo e-validador (documento). NULL = deriva de 'identificadores'.
    exige_documento = Column(Boolean, nullable=True)
    # Para que lado o documento anda. "receber" é o padrão histórico: o cliente
    # manda o comprovante e a tarefa baixa pelo e-validador. "entregar" é o
    # contrário — o escritório anexa a guia e envia ao cliente, e é o envio que
    # conclui a tarefa. Guia do Simples, DARF e boleto são deste segundo tipo.
    sentido = Column(String(10), default="receber")   # receber | entregar
    passivel_multa = Column(Boolean, default=False)
    alerta_guia_nao_lida = Column(Boolean, default=False)
    ativa = Column(Boolean, default=True)
    comentario_padrao = Column(Text)

    # Como a obrigação encontra as empresas:
    #   'regra'      (padrão) empresas que casam regime/segmento UNIÃO as vinculadas
    #   'vinculadas' SOMENTE as vinculadas explicitamente
    # Sem o segundo modo não havia como dizer "só estes clientes": campo de regra
    # vazio significa TODOS, então o vínculo só somava e nunca restringia.
    alvo_modo = Column(String(12), default="regra")

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


class SSOBilheteUsado(Base):
    """Uso único do bilhete que vem do Hub Zoaria.

    O `jti` é a chave primária de propósito: é o banco, e não o código Python,
    quem decide o vencedor quando o mesmo bilhete chega em duas requisições no
    mesmo instante. O segundo INSERT não passa, e a rota confere isso pela
    quantidade de linhas afetadas.

    Linha antiga vira rastro de auditoria, não trava: o bilhete morre em 60
    segundos, então guardar por dias serve para saber quem entrou, não para
    impedir a segunda entrada."""
    __tablename__ = "sso_bilhetes_usados"

    jti = Column(String(64), primary_key=True)
    usado_em = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip = Column(String(45))


class LoginTentativa(Base):
    """Toda tentativa de entrar, por qualquer porta, com sucesso ou sem.

    Serve a dois propósitos: contar falhas recentes por e-mail ou IP para travar
    força bruta, e deixar rastro de quem tentou entrar e de onde."""
    __tablename__ = "login_tentativas"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), index=True)
    ip = Column(String(45), index=True)
    origem = Column(String(20), default="sso")   # sso | senha
    sucesso = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)