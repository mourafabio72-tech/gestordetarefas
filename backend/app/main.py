import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .database import engine, Base
from .seguranca import abrir_contexto, aplicar_headers, ip_cliente, log_event
from .versao import BUILD
from .routes import auth, usuarios, empresas, setores, tarefas, alertas, obrigacoes, evalidador, substituicoes, configuracao, modelos, upload_publico, cronograma, grupos, ativar_publico, documentos, painel
from .services.scheduler import start_scheduler
from .init_db import (migrate, criar_indices, seed_admin, ensure_admin_grupo,
                      seed_grupos, alcance_do_alerta,
                      horarios_por_faixa)

Base.metadata.create_all(bind=engine)
migrate()
criar_indices()
alcance_do_alerta()
horarios_por_faixa()
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


@app.middleware("http")
async def _contexto_de_log(request: Request, call_next):
    """Abre o contexto do request para o `log_event`, e devolve o id ao cliente.

    O `X-Request-ID` na resposta não vem da nota da vault: é ampliação decidida
    em 2026-09-09. Sem ele, reclamação de usuário não se liga a linha de log, e
    a busca vira horário mais chute.
    """
    request_id = abrir_contexto(request)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def _erro_nao_tratado(request: Request, exc: Exception):
    """Excecao sem tratamento vira 500 generico, com id e com os cabecalhos.

    O `ServerErrorMiddleware` do Starlette e o mais externo de todos, entao a
    resposta de erro sai por FORA dos dois middlewares acima: sem
    `X-Request-ID` e sem cabecalho de seguranca nenhum. E justo o caso em que o
    id mais serviria, porque e o que liga a tela de erro do usuario a linha do
    log.

    O id vem do `request.state`, e nao da contextvar, porque este tratador roda
    em contexto ancestral ao do request. Ao cliente vai pouco (Familia 6 do
    `Mapa_de_Conceitos_de_Seguranca`, e item 9 da `Revisao_Vulnerabilidades`);
    o detalhe fica no log e no traceback, que o Starlette continua levantando
    depois daqui.
    """
    request_id = getattr(request.state, "request_id", None)
    log_event(
        "ERRO_NAO_TRATADO",
        level="ERROR",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        ip=ip_cliente(request),
        excecao=type(exc).__name__,
    )
    resposta = JSONResponse(
        status_code=500,
        content={"detail": "Erro interno. Tente novamente."},
    )
    if request_id:
        resposta.headers["X-Request-ID"] = request_id
    return aplicar_headers(resposta, request.url.path)


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
app.include_router(documentos.router, prefix="/api")
app.include_router(painel.router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    start_scheduler()


@app.get("/")
def root():
    return {"message": "Gestor de Tarefas API - Status: Online"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/health")
def health_api():
    """Igual ao /health, mas sob /api, que e o unico caminho do backend que
    atravessa o proxy: na raiz quem responde e o React buildado, e o /health
    acima nunca chega aqui em producao.

    O `build` bate com a data do commit e responde, de fora, qual versao esta
    servida. Ver `app/versao.py`.
    """
    return {"status": "healthy", "build": BUILD}
