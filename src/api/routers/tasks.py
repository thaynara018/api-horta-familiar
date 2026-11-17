"""Router de compatibilidade para Tasks (/api/v1/tasks).

Exige autenticação no POST/PATCH/PUT e exige papel ADMIN no DELETE /api/v1/tasks/{id}.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, selectinload

from src.api.database import get_db
from src.api.exceptions import BadRequestException, NotFoundException
from src.api.models import TarefaModel, UsuarioModel
from src.api.schemas import PerfilUsuarioEnum, Tarefa, TarefaInput
from src.api.security import get_current_user, require_roles
from src.api.routers.tarefas import check_tarefa_conflict

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


class TaskPatchInput(BaseModel):
    """Payload opcional para atualização parcial via PATCH."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    descricao: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = None


@router.get(
    "",
    response_model=List[Tarefa],
    status_code=status.HTTP_200_OK,
    summary="Lista todas as tarefas",
)
def list_tasks(db: Session = Depends(get_db)) -> List[Tarefa]:
    tasks = (
        db.query(TarefaModel)
        .options(
            selectinload(TarefaModel.usuario),
            selectinload(TarefaModel.canteiro),
        )
        .order_by(TarefaModel.id_tarefa)
        .all()
    )
    return [Tarefa.model_validate(t) for t in tasks]


@router.post(
    "",
    response_model=Tarefa,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma nova tarefa (Requer autenticação)",
    dependencies=[Depends(get_current_user)],
)
def create_task(payload: TarefaInput, db: Session = Depends(get_db)) -> Tarefa:
    if payload.hora_inicio >= payload.hora_fim:
        raise BadRequestException(detail="A hora de início deve ser anterior à hora de término.")

    check_tarefa_conflict(
        db=db,
        id_canteiro=payload.id_canteiro,
        data_tarefa=payload.data_tarefa,
        hora_inicio=payload.hora_inicio,
        hora_fim=payload.hora_fim,
    )

    tarefa = TarefaModel(
        id_usuario=payload.id_usuario,
        id_canteiro=payload.id_canteiro,
        descricao=payload.descricao,
        data_tarefa=payload.data_tarefa,
        hora_inicio=payload.hora_inicio,
        hora_fim=payload.hora_fim,
        status=payload.status,
    )
    db.add(tarefa)
    db.commit()
    db.refresh(tarefa)
    return Tarefa.model_validate(tarefa)


@router.get(
    "/{id}",
    response_model=Tarefa,
    status_code=status.HTTP_200_OK,
    summary="Busca tarefa por ID",
)
def get_task(id: int, db: Session = Depends(get_db)) -> Tarefa:
    tarefa = db.query(TarefaModel).filter(TarefaModel.id_tarefa == id).first()
    if not tarefa:
        raise NotFoundException(detail=f"Tarefa com ID {id} não encontrada.")
    return Tarefa.model_validate(tarefa)


@router.patch(
    "/{id}",
    response_model=Tarefa,
    status_code=status.HTTP_200_OK,
    summary="Atualiza parcialmente uma tarefa (Requer autenticação)",
    dependencies=[Depends(get_current_user)],
)
def patch_task(id: int, payload: TaskPatchInput, db: Session = Depends(get_db)) -> Tarefa:
    tarefa = db.query(TarefaModel).filter(TarefaModel.id_tarefa == id).first()
    if not tarefa:
        raise NotFoundException(detail=f"Tarefa com ID {id} não encontrada.")

    if payload.descricao is not None:
        tarefa.descricao = payload.descricao
    if payload.status is not None:
        tarefa.status = payload.status

    db.commit()
    db.refresh(tarefa)
    return Tarefa.model_validate(tarefa)


@router.put(
    "/{id}",
    response_model=Tarefa,
    status_code=status.HTTP_200_OK,
    summary="Atualiza uma tarefa por completo (Requer autenticação)",
    dependencies=[Depends(get_current_user)],
)
def put_task(id: int, payload: TarefaInput, db: Session = Depends(get_db)) -> Tarefa:
    tarefa = db.query(TarefaModel).filter(TarefaModel.id_tarefa == id).first()
    if not tarefa:
        raise NotFoundException(detail=f"Tarefa com ID {id} não encontrada.")

    tarefa.id_usuario = payload.id_usuario
    tarefa.id_canteiro = payload.id_canteiro
    tarefa.descricao = payload.descricao
    tarefa.data_tarefa = payload.data_tarefa
    tarefa.hora_inicio = payload.hora_inicio
    tarefa.hora_fim = payload.hora_fim
    tarefa.status = payload.status

    db.commit()
    db.refresh(tarefa)
    return Tarefa.model_validate(tarefa)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deleta uma tarefa (Exige papel ADMIN)",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def delete_task(id: int, db: Session = Depends(get_db)) -> None:
    tarefa = db.query(TarefaModel).filter(TarefaModel.id_tarefa == id).first()
    if not tarefa:
        raise NotFoundException(detail=f"Tarefa com ID {id} não encontrada.")

    db.delete(tarefa)
    db.commit()
