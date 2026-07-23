from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routes import auth, usuarios, empresas, setores, tarefas

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gestor Contábil API",
    description="API para gestão de tarefas contábeis",
    version="1.0.0"
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

@app.get("/")
def root():
    return {"message": "Gestor Contábil API - Status: Online"}

@app.get("/health")
def health():
    return {"status": "healthy"}