"""Configuração de banco de dados SQLAlchemy 2.0 e inicialização de dados (seed).

Banco padrão: SQLite (horta.db)
"""

import hashlib
import os
import secrets
from datetime import date, time
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.api.models import (
    Base,
    CanteiroModel,
    CulturaModel,
    InsumoModel,
    PlantioInsumoModel,
    PlantioModel,
    TarefaInsumoModel,
    TarefaModel,
    UsuarioModel,
)
from src.api.schemas import (
    PerfilUsuarioEnum,
    StatusPlantioEnum,
    StatusTarefaEnum,
    TipoInsumoEnum,
)

# Caminho do banco SQLite padrão
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./horta.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def hash_password(password: str) -> str:
    """Gera hash seguro com PBKDF2-HMAC-SHA256 e salt randômico."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    )
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica senha em texto puro contra o hash armazenado."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        salt = parts[1]
        stored_hash = parts[2]
        new_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        )
        return secrets.compare_digest(new_key.hex(), stored_hash)
    except Exception:
        return False


def get_db() -> Generator[Session, None, None]:
    """Dependency injection para sessões de banco de dados no FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Cria todas as tabelas declaradas no metadata."""
    Base.metadata.create_all(bind=engine)


def seed_database(db: Session | None = None) -> None:
    """Popula o banco com os dados iniciais solicitados e amostras do contrato Apidog."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # 1. Usuários solicitados
        admin_email = "admin@fatec.sp.gov.br"
        user_admin = db.query(UsuarioModel).filter_by(email=admin_email).first()
        if not user_admin:
            user_admin = UsuarioModel(
                nome="Administrador FATEC",
                email=admin_email,
                senha_hash=hash_password("admin123"),
                perfil=PerfilUsuarioEnum.ADMIN,
            )
            db.add(user_admin)

        aluno_email = "aluno@fatec.sp.gov.br"
        user_aluno = db.query(UsuarioModel).filter_by(email=aluno_email).first()
        if not user_aluno:
            user_aluno = UsuarioModel(
                nome="Aluno FATEC",
                email=aluno_email,
                senha_hash=hash_password("aluno123"),
                perfil=PerfilUsuarioEnum.OPERACIONAL,
            )
            db.add(user_aluno)

        db.flush()

        # 2. Culturas Iniciais do Catálogo
        cultura_alface = db.query(CulturaModel).filter_by(nome="Alface Crespa").first()
        if not cultura_alface:
            cultura_alface = CulturaModel(
                nome="Alface Crespa",
                tempo_maturacao_dias=45,
                espacamento_ideal=0.25,
            )
            db.add(cultura_alface)

        cultura_tomate = db.query(CulturaModel).filter_by(nome="Tomate Cereja").first()
        if not cultura_tomate:
            cultura_tomate = CulturaModel(
                nome="Tomate Cereja",
                tempo_maturacao_dias=90,
                espacamento_ideal=0.50,
            )
            db.add(cultura_tomate)

        db.flush()

        # 3. Canteiros Iniciais
        canteiro_a1 = db.query(CanteiroModel).filter_by(identificacao="Canteiro Central A1").first()
        if not canteiro_a1:
            canteiro_a1 = CanteiroModel(
                identificacao="Canteiro Central A1",
                area_m2=12.5,
            )
            db.add(canteiro_a1)

        canteiro_b2 = db.query(CanteiroModel).filter_by(identificacao="Canteiro Estufa B2").first()
        if not canteiro_b2:
            canteiro_b2 = CanteiroModel(
                identificacao="Canteiro Estufa B2",
                area_m2=20.0,
            )
            db.add(canteiro_b2)

        db.flush()

        # 4. Insumos em Estoque
        insumo_semente = db.query(InsumoModel).filter_by(nome="Semente de Alface").first()
        if not insumo_semente:
            insumo_semente = InsumoModel(
                nome="Semente de Alface",
                tipo=TipoInsumoEnum.SEMENTE,
                quantidade_estoque=100.0,
                estoque_minimo=15.0,
            )
            db.add(insumo_semente)

        insumo_adubo = db.query(InsumoModel).filter_by(nome="Fertilizante Orgânico NPK").first()
        if not insumo_adubo:
            insumo_adubo = InsumoModel(
                nome="Fertilizante Orgânico NPK",
                tipo=TipoInsumoEnum.FERTILIZANTE,
                quantidade_estoque=80.0,
                estoque_minimo=10.0,
            )
            db.add(insumo_adubo)

        db.flush()

        # 5. Plantio Inicial
        plantio_existente = db.query(PlantioModel).first()
        if not plantio_existente:
            plantio = PlantioModel(
                id_cultura=cultura_alface.id_cultura,
                id_canteiro=canteiro_a1.id_canteiro,
                data_plantio=date.today(),
                status=StatusPlantioEnum.CRESCIMENTO,
                peso_colhido=None,
            )
            db.add(plantio)
            db.flush()

            # Consumo de insumo no plantio
            db.add(
                PlantioInsumoModel(
                    id_plantio=plantio.id_plantio,
                    id_insumo=insumo_semente.id_insumo,
                    quantidade_utilizada=5.0,
                )
            )

        # 6. Tarefa Inicial
        tarefa_existente = db.query(TarefaModel).first()
        if not tarefa_existente:
            tarefa = TarefaModel(
                id_usuario=user_aluno.id_usuario,
                id_canteiro=canteiro_a1.id_canteiro,
                descricao="Irrigação e adubação foliar no canteiro A1",
                data_tarefa=date.today(),
                hora_inicio=time(8, 0, 0),
                hora_fim=time(10, 0, 0),
                status=StatusTarefaEnum.PENDENTE,
            )
            db.add(tarefa)
            db.flush()

            db.add(
                TarefaInsumoModel(
                    id_tarefa=tarefa.id_tarefa,
                    id_insumo=insumo_adubo.id_insumo,
                    quantidade_utilizada=2.5,
                )
            )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        if should_close:
            db.close()
