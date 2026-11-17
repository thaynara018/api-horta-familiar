"""Router de compatibilidade para Projects (/api/v1/projects).

Mapeia CanteiroModel com eager loading selectinload(CanteiroModel.tarefas) para prevenir queries N+1.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, selectinload

from src.api.database import get_db
from src.api.exceptions import ConflictException, NotFoundException
from src.api.models import CanteiroModel, PlantioModel, TarefaModel
from src.api.schemas import Canteiro, CanteiroInput, PerfilUsuarioEnum, Tarefa
from src.api.security import require_roles

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])


@router.get(
    "",
    response_model=List[Canteiro],
    status_code=status.HTTP_200_OK,
    summary="Lista todos os projetos / canteiros",
)
def list_projects(db: Session = Depends(get_db)) -> List[Canteiro]:
    canteiros = db.query(CanteiroModel).order_by(CanteiroModel.id_canteiro).all()
    return [Canteiro.model_validate(c) for c in canteiros]


@router.post(
    "",
    response_model=Canteiro,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo projeto / canteiro",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def create_project(payload: CanteiroInput, db: Session = Depends(get_db)) -> Canteiro:
    existente = db.query(CanteiroModel).filter(CanteiroModel.identificacao == payload.identificacao).first()
    if existente:
        raise ConflictException(detail=f"Projeto com identificação '{payload.identificacao}' já cadastrado.")

    canteiro = CanteiroModel(
        identificacao=payload.identificacao,
        area_m2=payload.area_m2,
    )
    db.add(canteiro)
    db.commit()
    db.refresh(canteiro)
    return Canteiro.model_validate(canteiro)


@router.get(
    "/{projectId}/tasks",
    response_model=List[Tarefa],
    status_code=status.HTTP_200_OK,
    summary="Lista tarefas do projeto com eager loading (prevenção de queries N+1)",
)
def get_project_tasks(projectId: int, db: Session = Depends(get_db)) -> List[Tarefa]:
    """Utiliza selectinload para carregar as tarefas do projeto em apenas duas queries otimizadas."""
    project = (
        db.query(CanteiroModel)
        .options(selectinload(CanteiroModel.tarefas))
        .filter(CanteiroModel.id_canteiro == projectId)
        .first()
    )
    if not project:
        raise NotFoundException(detail=f"Projeto com ID {projectId} não encontrado.")

    return [Tarefa.model_validate(t) for t in project.tarefas]


@router.get(
    "/{projectId}",
    response_model=Canteiro,
    status_code=status.HTTP_200_OK,
    summary="Busca projeto por ID",
)
def get_project(projectId: int, db: Session = Depends(get_db)) -> Canteiro:
    project = db.query(CanteiroModel).filter(CanteiroModel.id_canteiro == projectId).first()
    if not project:
        raise NotFoundException(detail=f"Projeto com ID {projectId} não encontrado.")
    return Canteiro.model_validate(project)


@router.delete(
    "/{projectId}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deleta um projeto",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def delete_project(projectId: int, db: Session = Depends(get_db)) -> None:
    project = db.query(CanteiroModel).filter(CanteiroModel.id_canteiro == projectId).first()
    if not project:
        raise NotFoundException(detail=f"Projeto com ID {projectId} não encontrado.")

    tem_vinculos = (
        db.query(PlantioModel).filter(PlantioModel.id_canteiro == projectId).first()
        or db.query(TarefaModel).filter(TarefaModel.id_canteiro == projectId).first()
    )
    if tem_vinculos:
        raise ConflictException(
            detail="Não é possível excluir o projeto pois existem plantios ou tarefas associadas a ele."
        )

    db.delete(project)
    db.commit()
