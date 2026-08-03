from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routes import auth, usuarios, empresas, setores, tarefas, alertas, obrigacoes, evalidador, substituicoes, configuracao
from .services.scheduler import start_scheduler
from .init_db import migrate, seed_admin, ensure_admin_grupo

Base.metadata.create_all(bind=engine)
migrate()
seed_admin()
ensure_admin_grupo()

app = FastAPI(
    title="Gestor de Tarefas API",
    description="API para gestão de tarefas contábeis",
    version="1.0.0",
    redirect_slashes=False
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
app.include_router(empresas.router, prefix="/api")
app.include_router(setores.router, prefix="/api")
app.include_router(tarefas.router, prefix="/api")
app.include_router(alertas.router, prefix="/api")
app.include_router(obrigacoes.router, prefix="/api")
app.include_router(evalidador.router, prefix="/api")
app.include_router(substituicoes.router, prefix="/api")
app.include_router(configuracao.router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    start_scheduler()


@app.get("/")
def root():
    return {"message": "Gestor de Tarefas API - Status: Online"}


@app.get("/health")
def health():
    return {"status": "healthy"}
