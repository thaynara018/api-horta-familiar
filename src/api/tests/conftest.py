"""Configurações e Fixtures para a suíte de testes com pytest.

Utiliza banco SQLite isolado em memória com StaticPool para garantir independência entre testes.
"""

from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.database import get_db, hash_password
from src.api.main import app
from src.api.models import Base, UsuarioModel
from src.api.schemas import PerfilUsuarioEnum
from src.api.security import create_access_token

# SQLite em memória compartilhado via StaticPool para o escopo do teste
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Cria as tabelas antes de cada teste e faz rollback/drop ao final."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()

    # Cria usuários iniciais de teste
    admin = UsuarioModel(
        nome="Admin Fatec",
        email="admin@fatec.sp.gov.br",
        senha_hash=hash_password("admin123"),
        perfil=PerfilUsuarioEnum.ADMIN,
    )
    member = UsuarioModel(
        nome="Aluno Fatec",
        email="aluno@fatec.sp.gov.br",
        senha_hash=hash_password("aluno123"),
        perfil=PerfilUsuarioEnum.OPERACIONAL,
    )
    session.add(admin)
    session.add(member)
    session.commit()
    session.refresh(admin)
    session.refresh(member)

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Cliente HTTP de teste com override de dependência do get_db."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session: Session) -> UsuarioModel:
    return db_session.query(UsuarioModel).filter_by(email="admin@fatec.sp.gov.br").first()


@pytest.fixture
def member_user(db_session: Session) -> UsuarioModel:
    return db_session.query(UsuarioModel).filter_by(email="aluno@fatec.sp.gov.br").first()


@pytest.fixture
def admin_token(admin_user: UsuarioModel) -> str:
    return create_access_token({
        "sub": str(admin_user.id_usuario),
        "email": admin_user.email,
        "perfil": admin_user.perfil.value,
        "role": admin_user.perfil.value,
    })


@pytest.fixture
def member_token(member_user: UsuarioModel) -> str:
    return create_access_token({
        "sub": str(member_user.id_usuario),
        "email": member_user.email,
        "perfil": member_user.perfil.value,
        "role": member_user.perfil.value,
    })


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def member_headers(member_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {member_token}"}
