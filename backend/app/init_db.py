from sqlalchemy import text
from .database import engine

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
