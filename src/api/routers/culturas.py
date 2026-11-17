"""Router de Culturas Agrícolas.

Listagem e busca abertas; criação, atualização e deleção restritas a ADMIN.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.exceptions import ConflictException, NotFoundException
from src.api.models import CulturaModel, PlantioModel
from src.api.schemas import Cultura, CulturaInput, PerfilUsuarioEnum
from src.api.security import require_roles

router = APIRouter(prefix="/culturas", tags=["Culturas"])


@router.get(
    "",
    response_model=List[Cultura],
    status_code=status.HTTP_200_OK,
    summary="Lista todas as culturas",
)
def list_culturas(db: Session = Depends(get_db)) -> List[Cultura]:
    culturas = db.query(CulturaModel).order_by(CulturaModel.id_cultura).all()
    return [Cultura.model_validate(c) for c in culturas]


@router.post(
    "",
    response_model=Cultura,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma nova cultura",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def create_cultura(payload: CulturaInput, db: Session = Depends(get_db)) -> Cultura:
    existente = db.query(CulturaModel).filter(CulturaModel.nome == payload.nome).first()
    if existente:
        raise ConflictException(detail=f"A cultura '{payload.nome}' já existe no catálogo.")

    cultura = CulturaModel(
        nome=payload.nome,
        tempo_maturacao_dias=payload.tempo_maturacao_dias,
        espacamento_ideal=payload.espacamento_ideal,
    )
    db.add(cultura)
    db.commit()
    db.refresh(cultura)
    return Cultura.model_validate(cultura)


@router.get(
    "/{id}",
    response_model=Cultura,
    status_code=status.HTTP_200_OK,
    summary="Busca uma cultura pelo ID",
)
def get_cultura(id: int, db: Session = Depends(get_db)) -> Cultura:
    cultura = db.query(CulturaModel).filter(CulturaModel.id_cultura == id).first()
    if not cultura:
        raise NotFoundException(detail=f"Cultura com ID {id} não encontrada.")
    return Cultura.model_validate(cultura)


@router.put(
    "/{id}",
    response_model=Cultura,
    status_code=status.HTTP_200_OK,
    summary="Atualiza uma cultura",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def update_cultura(id: int, payload: CulturaInput, db: Session = Depends(get_db)) -> Cultura:
    cultura = db.query(CulturaModel).filter(CulturaModel.id_cultura == id).first()
    if not cultura:
        raise NotFoundException(detail=f"Cultura com ID {id} não encontrada.")

    if payload.nome != cultura.nome:
        existente = db.query(CulturaModel).filter(CulturaModel.nome == payload.nome).first()
        if existente:
            raise ConflictException(detail=f"Outra cultura já possui o nome '{payload.nome}'.")

    cultura.nome = payload.nome
    cultura.tempo_maturacao_dias = payload.tempo_maturacao_dias
    cultura.espacamento_ideal = payload.espacamento_ideal

    db.commit()
    db.refresh(cultura)
    return Cultura.model_validate(cultura)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deleta uma cultura",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def delete_cultura(id: int, db: Session = Depends(get_db)) -> None:
    cultura = db.query(CulturaModel).filter(CulturaModel.id_cultura == id).first()
    if not cultura:
        raise NotFoundException(detail=f"Cultura com ID {id} não encontrada.")

    plantios_vinculados = db.query(PlantioModel).filter(PlantioModel.id_cultura == id).first()
    if plantios_vinculados:
        raise ConflictException(
            detail="Não é possível excluir esta cultura pois existem plantios vinculados a ela."
        )

    db.delete(cultura)
    db.commit()
