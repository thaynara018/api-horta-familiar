"""Testes de conformidade estrita com a RFC 9457 (Problem Details).

Verifica os códigos de status 400, 401, 403, 404 e 422.
"""

from fastapi.testclient import TestClient


def test_rfc9457_error_400_bad_request(client: TestClient, member_headers: dict[str, str], member_user):
    # Envia hora_inicio maior que hora_fim para disparar 400
    payload = {
        "id_usuario": member_user.id_usuario,
        "descricao": "Tarefa com horário invertido",
        "data_tarefa": "2026-11-20",
        "hora_inicio": "12:00:00",
        "hora_fim": "10:00:00",
        "status": "PENDENTE",
    }
    response = client.post("/api/v1/tasks", json=payload, headers=member_headers)
    assert response.status_code == 400
    data = response.json()
    assert data["type"] == "https://api.hortafamiliar.dev/errors/bad-request"
    assert data["title"] == "Bad Request"
    assert data["status"] == 400
    assert "detail" in data
    assert data["instance"] == "/api/v1/tasks"


def test_rfc9457_error_401_unauthorized(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["type"] == "https://api.hortafamiliar.dev/errors/unauthorized"
    assert data["title"] == "Unauthorized"
    assert data["status"] == 401
    assert "detail" in data
    assert data["instance"] == "/api/v1/auth/me"


def test_rfc9457_error_403_forbidden(client: TestClient, member_headers: dict[str, str]):
    response = client.post(
        "/api/v1/projects",
        json={"identificacao": "Projeto Proibido", "area_m2": 10.0},
        headers=member_headers,
    )
    assert response.status_code == 403
    data = response.json()
    assert data["type"] == "https://api.hortafamiliar.dev/errors/forbidden"
    assert data["title"] == "Forbidden"
    assert data["status"] == 403
    assert "detail" in data
    assert data["instance"] == "/api/v1/projects"


def test_rfc9457_error_404_not_found(client: TestClient):
    response = client.get("/api/v1/projects/999999")
    assert response.status_code == 404
    data = response.json()
    assert data["type"] == "https://api.hortafamiliar.dev/errors/not-found"
    assert data["title"] == "Not Found"
    assert data["status"] == 404
    assert "detail" in data
    assert data["instance"] == "/api/v1/projects/999999"


def test_rfc9457_error_422_unprocessable_entity(client: TestClient, member_headers: dict[str, str]):
    # Envia corpo incompleto e com tipos inválidos para disparar 422
    payload = {
        "descricao": "Tarefa sem campos obrigatórios"
    }
    response = client.post("/api/v1/tasks", json=payload, headers=member_headers)
    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "https://api.hortafamiliar.dev/errors/validation-error"
    assert data["title"] == "Unprocessable Entity"
    assert data["status"] == 422
    assert "invalidParams" in data
    assert isinstance(data["invalidParams"], list)
    assert len(data["invalidParams"]) > 0
    assert "name" in data["invalidParams"][0]
    assert "reason" in data["invalidParams"][0]
