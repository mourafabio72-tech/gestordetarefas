from sqlalchemy import text
from .database import engine

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN telefone VARCHAR(20)"))
            conn.commit()
            print("Coluna 'telefone' adicionada com sucesso!")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("Coluna 'telefone' já existe.")
            else:
                print(f"Erro: {e}")

        try:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN teams_webhook TEXT"))
            conn.commit()
            print("Coluna 'teams_webhook' adicionada com sucesso!")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("Coluna 'teams_webhook' já existe.")
            else:
                print(f"Erro: {e}")
