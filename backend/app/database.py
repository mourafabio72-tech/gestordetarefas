from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
import os

# Monta a URL a partir das partes, escapando a senha (funciona mesmo com
# caracteres especiais como @, :, / na senha). Se DATABASE_URL vier pronta
# no ambiente, ela tem prioridade.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    _user = os.getenv("DB_USER", "postgres")
    _pwd = quote_plus(os.getenv("DB_PASSWORD", "postgres"))
    _host = os.getenv("DB_HOST", "db")
    _port = os.getenv("DB_PORT", "5432")
    _name = os.getenv("DB_NAME", "gestor_tarefas")
    DATABASE_URL = f"postgresql://{_user}:{_pwd}@{_host}:{_port}/{_name}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()