"""Testes de autenticação JWT e rotas de perfil."""

from fastapi.testclient import TestClient


def test_login_admin_success(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@fatec.sp.gov.br", "senha": "admin123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_member_success(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"email": "aluno@fatec.sp.gov.br", "senha": "aluno123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@fatec.sp.gov.br", "senha": "senha_errada"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == 401
    assert data["title"] == "Unauthorized"
    assert "type" in data
    assert "instance" in data


def test_login_user_not_found(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inexistente@fatec.sp.gov.br", "senha": "qualquer_senha"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == 401
    assert data["title"] == "Unauthorized"


def test_get_me_authenticated(client: TestClient, admin_headers: dict[str, str]):
    response = client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@fatec.sp.gov.br"
    assert data["perfil"] == "ADMIN"
    assert "id_usuario" in data


def test_get_me_unauthorized_without_token(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == 401
    assert data["title"] == "Unauthorized"


def test_get_me_unauthorized_invalid_token(client: TestClient):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer token_invalido_123"})
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == 401
