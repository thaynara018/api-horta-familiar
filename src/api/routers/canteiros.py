"""Router de Canteiros da Horta.

Inclui operações CRUD e a rota com eager loading para tarefas associadas.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, selectinload

from src.api.database import get_db
from src.api.exceptions import ConflictException, NotFoundException
from src.api.models import CanteiroModel, PlantioModel, TarefaModel
from src.api.schemas import Canteiro, CanteiroInput, PerfilUsuarioEnum, Tarefa
from src.api.security import require_roles

router = APIRouter(prefix="/canteiros", tags=["Canteiros"])


@router.get(
    "",
    response_model=List[Canteiro],
    status_code=status.HTTP_200_OK,
    summary="Lista canteiros",
)
def list_canteiros(db: Session = Depends(get_db)) -> List[Canteiro]:
    canteiros = db.query(CanteiroModel).order_by(CanteiroModel.id_canteiro).all()
    return [Canteiro.model_validate(c) for c in canteiros]


@router.post(
    "",
    response_model=Canteiro,
    status_code=status.HTTP_201_CREATED,
    summary="Cria canteiro",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def create_canteiro(payload: CanteiroInput, db: Session = Depends(get_db)) -> Canteiro:
    existente = db.query(CanteiroModel).filter(CanteiroModel.identificacao == payload.identificacao).first()
    if existente:
        raise ConflictException(detail=f"Canteiro com identificação '{payload.identificacao}' já cadastrado.")

    canteiro = CanteiroModel(
        identificacao=payload.identificacao,
        area_m2=payload.area_m2,
    )
    db.add(canteiro)
    db.commit()
    db.refresh(canteiro)
    return Canteiro.model_validate(canteiro)


@router.get(
    "/{id}",
    response_model=Canteiro,
    status_code=status.HTTP_200_OK,
    summary="Busca um canteiro pelo ID",
)
def get_canteiro(id: int, db: Session = Depends(get_db)) -> Canteiro:
    canteiro = db.query(CanteiroModel).filter(CanteiroModel.id_canteiro == id).first()
    if not canteiro:
        raise NotFoundException(detail=f"Canteiro com ID {id} não encontrado.")
    return Canteiro.model_validate(canteiro)


@router.get(
    "/{id}/tarefas",
    response_model=List[Tarefa],
    status_code=status.HTTP_200_OK,
    summary="Lista tarefas do canteiro com eager loading (prevenção de N+1)",
)
def get_canteiro_tarefas(id: int, db: Session = Depends(get_db)) -> List[Tarefa]:
    canteiro = (
        db.query(CanteiroModel)
        .options(selectinload(CanteiroModel.tarefas))
        .filter(CanteiroModel.id_canteiro == id)
        .first()
    )
    if not canteiro:
        raise NotFoundException(detail=f"Canteiro com ID {id} não encontrado.")
    return [Tarefa.model_validate(t) for t in canteiro.tarefas]


@router.put(
    "/{id}",
    response_model=Canteiro,
    status_code=status.HTTP_200_OK,
    summary="Atualiza um canteiro",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def update_canteiro(id: int, payload: CanteiroInput, db: Session = Depends(get_db)) -> Canteiro:
    canteiro = db.query(CanteiroModel).filter(CanteiroModel.id_canteiro == id).first()
    if not canteiro:
        raise NotFoundException(detail=f"Canteiro com ID {id} não encontrado.")

    if payload.identificacao != canteiro.identificacao:
        existente = db.query(CanteiroModel).filter(CanteiroModel.identificacao == payload.identificacao).first()
        if existente:
            raise ConflictException(detail=f"Identificação '{payload.identificacao}' já em uso.")

    canteiro.identificacao = payload.identificacao
    canteiro.area_m2 = payload.area_m2

    db.commit()
    db.refresh(canteiro)
    return Canteiro.model_validate(canteiro)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deleta um canteiro",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def delete_canteiro(id: int, db: Session = Depends(get_db)) -> None:
    canteiro = db.query(CanteiroModel).filter(CanteiroModel.id_canteiro == id).first()
    if not canteiro:
        raise NotFoundException(detail=f"Canteiro com ID {id} não encontrado.")

    tem_plantios = db.query(PlantioModel).filter(PlantioModel.id_canteiro == id).first()
    tem_tarefas = db.query(TarefaModel).filter(TarefaModel.id_canteiro == id).first()

    if tem_plantios or tem_tarefas:
        raise ConflictException(
            detail="Não é possível excluir o canteiro pois existem plantios ou tarefas associadas a ele."
        )

    db.delete(canteiro)
    db.commit()
