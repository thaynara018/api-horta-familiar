"""Testes da coleção de Projetos / Canteiros e prevenção de N+1 queries."""

from datetime import date, time
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.models import CanteiroModel, TarefaModel
from src.api.schemas import StatusTarefaEnum


def test_list_projects(client: TestClient):
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_project_forbidden_for_member(
    client: TestClient, member_headers: dict[str, str]
):
    response = client.post(
        "/api/v1/projects",
        json={"identificacao": "Canteiro Teste Proibido", "area_m2": 15.0},
        headers=member_headers,
    )
    assert response.status_code == 403
    assert response.json()["status"] == 403


def test_create_project_success_for_admin(
    client: TestClient, admin_headers: dict[str, str]
):
    response = client.post(
        "/api/v1/projects",
        json={"identificacao": "Canteiro Central Novo", "area_m2": 25.0},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["identificacao"] == "Canteiro Central Novo"
    assert "id_canteiro" in data


def test_get_project_tasks_with_eager_loading(
    client: TestClient, db_session: Session, admin_user
):
    # 1. Cria canteiro/projeto
    canteiro = CanteiroModel(identificacao="Canteiro N+1 Prevenção", area_m2=30.0)
    db_session.add(canteiro)
    db_session.commit()
    db_session.refresh(canteiro)

    # 2. Cria 3 tarefas associadas
    for i in range(3):
        task = TarefaModel(
            id_usuario=admin_user.id_usuario,
            id_canteiro=canteiro.id_canteiro,
            descricao=f"Atividade {i + 1} no canteiro",
            data_tarefa=date(2026, 11, 14),
            hora_inicio=time(8 + i, 0, 0),
            hora_fim=time(9 + i, 0, 0),
            status=StatusTarefaEnum.PENDENTE,
        )
        db_session.add(task)
    db_session.commit()

    # 3. Consulta as tarefas do projeto utilizando a rota otimizada com selectinload
    response = client.get(f"/api/v1/projects/{canteiro.id_canteiro}/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 3
    assert tasks[0]["id_canteiro"] == canteiro.id_canteiro


def test_delete_project_with_tasks_returns_conflict(
    client: TestClient, db_session: Session, admin_headers: dict[str, str], admin_user
):
    canteiro = CanteiroModel(identificacao="Canteiro Com Tarefa", area_m2=10.0)
    db_session.add(canteiro)
    db_session.commit()
    db_session.refresh(canteiro)

    task = TarefaModel(
        id_usuario=admin_user.id_usuario,
        id_canteiro=canteiro.id_canteiro,
        descricao="Tarefa bloqueadora",
        data_tarefa=date(2026, 11, 15),
        hora_inicio=time(10, 0, 0),
        hora_fim=time(11, 0, 0),
        status=StatusTarefaEnum.PENDENTE,
    )
    db_session.add(task)
    db_session.commit()

    # Tenta excluir -> Conflito 409
    del_resp = client.delete(f"/api/v1/projects/{canteiro.id_canteiro}", headers=admin_headers)
    assert del_resp.status_code == 409
    assert del_resp.json()["status"] == 409
