import os
from sqlalchemy import text
from .database import engine, SessionLocal
from .models import Usuario
from .auth import get_password_hash

def migrate():
    migrations = [
        ("telefone", "ALTER TABLE usuarios ADD COLUMN telefone VARCHAR(20)"),
        ("gestor_id", "ALTER TABLE usuarios ADD COLUMN gestor_id INTEGER REFERENCES usuarios(id)"),
        ("grupo", "ALTER TABLE usuarios ADD COLUMN grupo VARCHAR(20) DEFAULT 'usuario'"),
        ("data_vencimento", "ALTER TABLE tarefas ADD COLUMN data_vencimento TIMESTAMP"),
        ("gera_multa", "ALTER TABLE tarefas ADD COLUMN gera_multa BOOLEAN DEFAULT FALSE"),
        ("regime_tributario", "ALTER TABLE empresas ADD COLUMN regime_tributario VARCHAR(30) DEFAULT 'indefinido'"),
        ("segmento", "ALTER TABLE empresas ADD COLUMN segmento VARCHAR(30)"),
        ("data_prazo_nullable", "ALTER TABLE tarefas ALTER COLUMN data_prazo DROP NOT NULL"),
        ("permissoes", "ALTER TABLE usuarios ADD COLUMN permissoes TEXT"),
        ("obrigacao_id", "ALTER TABLE tarefas ADD COLUMN obrigacao_id INTEGER REFERENCES obrigacoes(id)"),
        ("competencia", "ALTER TABLE tarefas ADD COLUMN competencia VARCHAR(7)"),
        ("identificadores", "ALTER TABLE obrigacoes ADD COLUMN identificadores VARCHAR(200)"),
        ("protocolo_entrega", "ALTER TABLE tarefas ADD COLUMN protocolo_entrega VARCHAR(120)"),
        ("data_entrega", "ALTER TABLE tarefas ADD COLUMN data_entrega TIMESTAMP"),
        ("anexo_nome", "ALTER TABLE tarefas ADD COLUMN anexo_nome VARCHAR(200)"),
        ("usuario_tipo", "ALTER TABLE usuarios ADD COLUMN tipo VARCHAR(20) DEFAULT 'colaborador'"),
        ("usuario_empresa_id", "ALTER TABLE usuarios ADD COLUMN empresa_id INTEGER REFERENCES empresas(id)"),
        ("tarefa_supervisor_id", "ALTER TABLE tarefas ADD COLUMN supervisor_id INTEGER REFERENCES usuarios(id)"),
        ("obrigacao_supervisor_id", "ALTER TABLE obrigacoes ADD COLUMN supervisor_id INTEGER REFERENCES usuarios(id)"),
        ("empresa_responsavel_id", "ALTER TABLE empresas ADD COLUMN responsavel_id INTEGER REFERENCES usuarios(id)"),
        ("empresa_supervisor_id", "ALTER TABLE empresas ADD COLUMN supervisor_id INTEGER REFERENCES usuarios(id)"),
        ("empresa_bloqueado", "ALTER TABLE empresas ADD COLUMN bloqueado BOOLEAN DEFAULT FALSE"),
        ("usuario_bloqueado", "ALTER TABLE usuarios ADD COLUMN bloqueado BOOLEAN DEFAULT FALSE"),
        # setor virou interno/global: relaxa o NOT NULL antigo em produção
        ("setor_empresa_nullable", "ALTER TABLE setores ALTER COLUMN empresa_id DROP NOT NULL"),
        ("empresa_grupo", "ALTER TABLE empresas ADD COLUMN grupo VARCHAR(80)"),
        ("tarefa_upload_token", "ALTER TABLE tarefas ADD COLUMN upload_token VARCHAR(64)"),
        ("usuario_setor_id", "ALTER TABLE usuarios ADD COLUMN setor_id INTEGER REFERENCES setores(id)"),
        ("usuario_convite_token", "ALTER TABLE usuarios ADD COLUMN convite_token VARCHAR(64)"),
        ("usuario_ativado", "ALTER TABLE usuarios ADD COLUMN ativado BOOLEAN"),
        ("obrigacao_exige_documento", "ALTER TABLE obrigacoes ADD COLUMN exige_documento BOOLEAN"),
    ]

    for col_name, sql in migrations:
        with engine.begin() as conn:
            try:
                conn.execute(text(sql))
                print(f"Coluna '{col_name}' adicionada com sucesso!")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"Coluna '{col_name}' já existe.")
                else:
                    print(f"Erro na coluna '{col_name}': {e}")


def criar_indices():
    """Índices das colunas por que se filtra e se ordena.

    `Base.metadata.create_all` só cria tabela que não existe -- em base já
    criada, marcar `index=True` no model não faz nada. Por isso os índices
    entram aqui, no mesmo mecanismo idempotente das colunas.

    `tarefas` é a tabela grande e a mais consultada, e não tinha índice em
    nenhuma chave estrangeira: toda listagem filtrada por empresa, setor ou
    responsável varria a tabela inteira. `CREATE INDEX IF NOT EXISTS` funciona
    tanto no Postgres do servidor quanto no SQLite local.
    """
    indices = [
        # tarefas: filtros da listagem e do escopo por responsável
        ("ix_tarefas_empresa_id",     "CREATE INDEX IF NOT EXISTS ix_tarefas_empresa_id ON tarefas (empresa_id)"),
        ("ix_tarefas_setor_id",       "CREATE INDEX IF NOT EXISTS ix_tarefas_setor_id ON tarefas (setor_id)"),
        ("ix_tarefas_responsavel_id", "CREATE INDEX IF NOT EXISTS ix_tarefas_responsavel_id ON tarefas (responsavel_id)"),
        ("ix_tarefas_supervisor_id",  "CREATE INDEX IF NOT EXISTS ix_tarefas_supervisor_id ON tarefas (supervisor_id)"),
        ("ix_tarefas_obrigacao_id",   "CREATE INDEX IF NOT EXISTS ix_tarefas_obrigacao_id ON tarefas (obrigacao_id)"),
        ("ix_tarefas_status",         "CREATE INDEX IF NOT EXISTS ix_tarefas_status ON tarefas (status)"),
        ("ix_tarefas_data_prazo",     "CREATE INDEX IF NOT EXISTS ix_tarefas_data_prazo ON tarefas (data_prazo)"),
        # atrasadas = status pendente/andamento COM prazo vencido, sempre juntos
        ("ix_tarefas_status_prazo",   "CREATE INDEX IF NOT EXISTS ix_tarefas_status_prazo ON tarefas (status, data_prazo)"),
        # e-validador procura por (empresa, obrigação, competência)
        ("ix_tarefas_competencia",    "CREATE INDEX IF NOT EXISTS ix_tarefas_competencia ON tarefas (competencia)"),
        # M2M: a PK é (tarefa_id, usuario_id), então buscar POR USUÁRIO -- que é
        # o que o escopo faz -- não aproveita a chave primária.
        ("ix_tarefa_resp_usuario",    "CREATE INDEX IF NOT EXISTS ix_tarefa_resp_usuario ON tarefa_responsaveis (usuario_id)"),
        # subordinados diretos, lidos a cada request para montar o escopo
        ("ix_usuarios_gestor_id",     "CREATE INDEX IF NOT EXISTS ix_usuarios_gestor_id ON usuarios (gestor_id)"),
    ]
    for nome, sql in indices:
        with engine.begin() as conn:
            try:
                conn.execute(text(sql))
            except Exception as e:
                print(f"Erro no índice '{nome}': {e}")


def seed_admin():
    """Cria o admin inicial a partir de ADMIN_EMAIL/ADMIN_PASSWORD apenas
    quando a tabela de usuários está vazia. Sem essas envs, não faz nada."""
    email = os.getenv("ADMIN_EMAIL")
    senha = os.getenv("ADMIN_PASSWORD")
    if not email or not senha:
        return
    db = SessionLocal()
    try:
        if db.query(Usuario).count() == 0:
            db.add(Usuario(
                nome=os.getenv("ADMIN_NOME", "Administrador"),
                email=email,
                senha_hash=get_password_hash(senha),
                cargo="admin",
                grupo="admin",
            ))
            db.commit()
            print(f"Admin inicial criado: {email}")
    finally:
        db.close()


def ensure_admin_grupo():
    """Garante que o admin (por cargo ou pelo ADMIN_EMAIL) fique no grupo 'admin'.
    Necessário porque a coluna 'grupo' nasce com default 'usuario' para linhas antigas."""
    email = os.getenv("ADMIN_EMAIL")
    db = SessionLocal()
    try:
        cond = Usuario.cargo == "admin"
        if email:
            cond = cond | (Usuario.email == email)
        promovidos = 0
        for u in db.query(Usuario).filter(cond).all():
            if u.grupo != "admin":
                u.grupo = "admin"
                promovidos += 1
        if promovidos:
            db.commit()
            print(f"{promovidos} usuário(s) promovido(s) ao grupo admin.")
    finally:
        db.close()


def seed_grupos():
    """Semeia os papéis nativos na tabela `grupos` (uma vez) e carrega o cache
    de permissões. Idempotente: só cria os slugs que ainda não existem."""
    import json
    from .models import Grupo
    from . import permissoes
    db = SessionLocal()
    try:
        existentes = {g.slug for g in db.query(Grupo).all()}
        criados = 0
        for slug, perm in permissoes.PRESETS.items():
            if slug in existentes:
                continue
            label, desc = permissoes.LABELS_NATIVOS.get(slug, (slug.capitalize(), ""))
            db.add(Grupo(slug=slug, label=label, descricao=desc,
                         permissoes=json.dumps(perm), sistema=True, ativo=True))
            criados += 1
        if criados:
            db.commit()
            print(f"{criados} grupo(s) nativo(s) semeado(s).")
        permissoes.carregar_do_banco(db)
    finally:
        db.close()
