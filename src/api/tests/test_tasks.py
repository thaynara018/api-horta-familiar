"""Testes da coleção de Tarefas / Tasks, controle RBAC e consumo de insumos."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.models import CanteiroModel, InsumoModel, TarefaModel
from src.api.schemas import TipoInsumoEnum


def test_list_tasks_empty(client: TestClient):
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_task_unauthorized(client: TestClient):
    payload = {
        "id_usuario": 1,
        "descricao": "Capina de canteiro",
        "data_tarefa": "2026-11-12",
        "hora_inicio": "08:00:00",
        "hora_fim": "10:00:00",
        "status": "PENDENTE",
    }
    response = client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 401
    assert response.json()["status"] == 401


def test_create_task_authenticated(
    client: TestClient, member_headers: dict[str, str], member_user
):
    payload = {
        "id_usuario": member_user.id_usuario,
        "descricao": "Adubação foliar matinal",
        "data_tarefa": "2026-11-12",
        "hora_inicio": "08:00:00",
        "hora_fim": "10:00:00",
        "status": "PENDENTE",
    }
    response = client.post("/api/v1/tasks", json=payload, headers=member_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["descricao"] == payload["descricao"]
    assert "id_tarefa" in data


def test_rbac_delete_task_forbidden_for_member(
    client: TestClient,
    member_headers: dict[str, str],
    admin_headers: dict[str, str],
    admin_user,
):
    # 1. Cria tarefa como Admin
    create_resp = client.post(
        "/api/v1/tasks",
        json={
            "id_usuario": admin_user.id_usuario,
            "descricao": "Tarefa para teste de RBAC",
            "data_tarefa": "2026-11-12",
            "hora_inicio": "14:00:00",
            "hora_fim": "16:00:00",
            "status": "PENDENTE",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id_tarefa"]

    # 2. Usuário MEMBER (OPERACIONAL) tenta deletar -> Deve retornar 403 Forbidden RFC 9457
    del_member_resp = client.delete(f"/api/v1/tasks/{task_id}", headers=member_headers)
    assert del_member_resp.status_code == 403
    err_data = del_member_resp.json()
    assert err_data["status"] == 403
    assert err_data["title"] == "Forbidden"

    # 3. Usuário ADMIN deleta -> Deve retornar 204 No Content
    del_admin_resp = client.delete(f"/api/v1/tasks/{task_id}", headers=admin_headers)
    assert del_admin_resp.status_code == 204


def test_patch_task(client: TestClient, member_headers: dict[str, str], member_user):
    create_resp = client.post(
        "/api/v1/tasks",
        json={
            "id_usuario": member_user.id_usuario,
            "descricao": "Tarefa para patch",
            "data_tarefa": "2026-11-15",
            "hora_inicio": "09:00:00",
            "hora_fim": "11:00:00",
            "status": "PENDENTE",
        },
        headers=member_headers,
    )
    task_id = create_resp.json()["id_tarefa"]

    patch_resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "CONCLUIDA", "descricao": "Tarefa concluída com sucesso"},
        headers=member_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "CONCLUIDA"
    assert patch_resp.json()["descricao"] == "Tarefa concluída com sucesso"


def test_task_insumo_stock_consumption_and_refund(
    client: TestClient, db_session: Session, member_headers: dict[str, str], member_user
):
    # 1. Cria insumo no banco com 20 unidades
    insumo = InsumoModel(
        nome="Adubo Teste",
        tipo=TipoInsumoEnum.FERTILIZANTE,
        quantidade_estoque=20.0,
        estoque_minimo=5.0,
    )
    db_session.add(insumo)
    db_session.commit()
    db_session.refresh(insumo)

    # 2. Cria tarefa
    create_task = client.post(
        "/tarefas",
        json={
            "id_usuario": member_user.id_usuario,
            "descricao": "Adubação com insumo",
            "data_tarefa": "2026-11-20",
            "hora_inicio": "08:00:00",
            "hora_fim": "09:00:00",
            "status": "PENDENTE",
        },
        headers=member_headers,
    )
    task_id = create_task.json()["id_tarefa"]

    # 3. Consome 6.5 unidades do insumo
    add_insumo_resp = client.post(
        f"/tarefas/{task_id}/insumos",
        json={"id_insumo": insumo.id_insumo, "quantidade_utilizada": 6.5},
        headers=member_headers,
    )
    assert add_insumo_resp.status_code == 201

    # Valida estoque restante: 20 - 6.5 = 13.5
    db_session.refresh(insumo)
    assert insumo.quantidade_estoque == 13.5

    # 4. Estorna o insumo
    del_insumo_resp = client.delete(
        f"/tarefas/{task_id}/insumos/{insumo.id_insumo}",
        headers=member_headers,
    )
    assert del_insumo_resp.status_code == 204

    # Valida estoque estornado de volta para 20.0
    db_session.refresh(insumo)
    assert insumo.quantidade_estoque == 20.0
