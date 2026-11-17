"""Router de Insumos da Horta.

Operações sobre estoque e catálogo de sementes, fertilizantes e ferramentas.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.exceptions import ConflictException, NotFoundException
from src.api.models import InsumoModel, PlantioInsumoModel, TarefaInsumoModel
from src.api.schemas import Insumo, InsumoInput, PerfilUsuarioEnum
from src.api.security import require_roles

router = APIRouter(prefix="/insumos", tags=["Insumos"])


@router.get(
    "",
    response_model=List[Insumo],
    status_code=status.HTTP_200_OK,
    summary="Lista insumos",
)
def list_insumos(db: Session = Depends(get_db)) -> List[Insumo]:
    insumos = db.query(InsumoModel).order_by(InsumoModel.id_insumo).all()
    return [Insumo.model_validate(i) for i in insumos]


@router.post(
    "",
    response_model=Insumo,
    status_code=status.HTTP_201_CREATED,
    summary="Cria insumo",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def create_insumo(payload: InsumoInput, db: Session = Depends(get_db)) -> Insumo:
    insumo = InsumoModel(
        nome=payload.nome,
        tipo=payload.tipo,
        quantidade_estoque=payload.quantidade_estoque,
        estoque_minimo=payload.estoque_minimo,
    )
    db.add(insumo)
    db.commit()
    db.refresh(insumo)
    return Insumo.model_validate(insumo)


@router.get(
    "/{id}",
    response_model=Insumo,
    status_code=status.HTTP_200_OK,
    summary="Busca insumo pelo ID",
)
def get_insumo(id: int, db: Session = Depends(get_db)) -> Insumo:
    insumo = db.query(InsumoModel).filter(InsumoModel.id_insumo == id).first()
    if not insumo:
        raise NotFoundException(detail=f"Insumo com ID {id} não encontrado.")
    return Insumo.model_validate(insumo)


@router.put(
    "/{id}",
    response_model=Insumo,
    status_code=status.HTTP_200_OK,
    summary="Atualiza um insumo",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def update_insumo(id: int, payload: InsumoInput, db: Session = Depends(get_db)) -> Insumo:
    insumo = db.query(InsumoModel).filter(InsumoModel.id_insumo == id).first()
    if not insumo:
        raise NotFoundException(detail=f"Insumo com ID {id} não encontrado.")

    insumo.nome = payload.nome
    insumo.tipo = payload.tipo
    insumo.quantidade_estoque = payload.quantidade_estoque
    insumo.estoque_minimo = payload.estoque_minimo

    db.commit()
    db.refresh(insumo)
    return Insumo.model_validate(insumo)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deleta um insumo",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def delete_insumo(id: int, db: Session = Depends(get_db)) -> None:
    insumo = db.query(InsumoModel).filter(InsumoModel.id_insumo == id).first()
    if not insumo:
        raise NotFoundException(detail=f"Insumo com ID {id} não encontrado.")

    em_plantio = db.query(PlantioInsumoModel).filter(PlantioInsumoModel.id_insumo == id).first()
    em_tarefa = db.query(TarefaInsumoModel).filter(TarefaInsumoModel.id_insumo == id).first()

    if em_plantio or em_tarefa:
        raise ConflictException(
            detail="Não é possível excluir o insumo pois ele já foi utilizado em plantios ou tarefas."
        )

    db.delete(insumo)
    db.commit()
