import os
from sqlalchemy import text
from .database import engine, SessionLocal
from .models import Usuario
from .auth import get_password_hash

def migrate():
    migrations = [
        ("telefone", "ALTER TABLE usuarios ADD COLUMN telefone VARCHAR(20)"),
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
            ))
            db.commit()
            print(f"Admin inicial criado: {email}")
    finally:
        db.close()
