"""Ponto de entrada principal da API Horta Familiar.

Configura:
- Lifespan (init_db e seed_database)
- Middleware CORS
- Handlers semânticos RFC 9457 (Problem Details)
- Inclusão dos roteadores da aplicação
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.database import init_db, seed_database
from src.api.exceptions import register_exception_handlers
from src.api.routers import (
    auth,
    canteiros,
    culturas,
    dashboard,
    insumos,
    plantios,
    projects,
    tarefas,
    tasks,
    usuarios,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia a inicialização e encerramento da aplicação (banco de dados e seed)."""
    init_db()
    seed_database()
    yield


app = FastAPI(
    title="API Horta Familiar",
    description="API para gestão de uma Horta Familiar, incluindo controle de usuários, culturas, canteiros, insumos, plantios e tarefas.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de Exception Handlers (RFC 9457)
register_exception_handlers(app)

# Inclusão de Rotas de Autenticação (suporta /auth e /api/v1/auth)
app.include_router(auth.router, prefix="/auth")
app.include_router(auth.router, prefix="/api/v1/auth")

# Inclusão dos Roteadores de Negócio
app.include_router(usuarios.router)
app.include_router(culturas.router)
app.include_router(canteiros.router)
app.include_router(projects.router)
app.include_router(insumos.router)
app.include_router(plantios.router)
app.include_router(tarefas.router)
app.include_router(tasks.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["Monitoramento"], summary="Health check da API")
def health_check() -> dict[str, str]:
    """Verifica se a API está online."""
    return {"status": "ok", "app": "API Horta Familiar"}
