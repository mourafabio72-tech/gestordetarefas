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
