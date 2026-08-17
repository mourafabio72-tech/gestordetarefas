import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .seguranca import aplicar_headers
from .routes import auth, usuarios, empresas, setores, tarefas, alertas, obrigacoes, evalidador, substituicoes, configuracao, modelos, upload_publico, cronograma, grupos, ativar_publico
from .services.scheduler import start_scheduler
from .init_db import migrate, seed_admin, ensure_admin_grupo, seed_grupos

Base.metadata.create_all(bind=engine)
migrate()
seed_admin()
ensure_admin_grupo()
seed_grupos()

app = FastAPI(
    title="Gestor de Tarefas API",
    description="API para gestão de tarefas contábeis",
    version="1.0.0",
    redirect_slashes=False
)

# Origens que podem chamar esta API do navegador. Lista explícita, e não "*":
# com "*" qualquer site aberto pelo usuário fala com a API a partir do navegador
# dele. Em produção o React é servido pelo mesmo domínio e nem precisaria de
# CORS; a lista existe para o desenvolvimento local e para um eventual domínio
# próprio do backend.
_ORIGENS_PADRAO = (
    "https://gestordetarefas.zoaria.com.br,"
    "http://localhost:5173,http://localhost:3000"
)
# `or` e não o segundo argumento do getenv: o docker-compose define a variável
# como string vazia quando ninguém a preenche, e vazio aqui bloquearia tudo.
CORS_ORIGENS = [
    o.strip() for o in (os.getenv("CORS_ORIGINS") or _ORIGENS_PADRAO).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGENS,
    # Sem credencial de navegador: este projeto autentica por
    # `Authorization: Bearer` guardado no localStorage, não por cookie. Ligar
    # `allow_credentials` sem cookie nenhum só amplia o que o CORS permite.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _headers_de_seguranca(request: Request, call_next):
    """Cabeçalhos de segurança em toda resposta, inclusive nas de erro."""
    response = await call_next(request)
    return aplicar_headers(response, request.url.path)

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
app.include_router(modelos.router, prefix="/api")
app.include_router(upload_publico.router, prefix="/api")
app.include_router(cronograma.router, prefix="/api")
app.include_router(grupos.router, prefix="/api")
app.include_router(ativar_publico.router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    start_scheduler()


@app.get("/")
def root():
    return {"message": "Gestor de Tarefas API - Status: Online"}


@app.get("/health")
def health():
    return {"status": "healthy"}
