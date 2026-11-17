"""Router de Plantios da Horta.

Inclui operações CRUD e controle transacional de insumos (desconto e estorno de estoque).
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, selectinload

from src.api.database import get_db
from src.api.exceptions import BadRequestException, NotFoundException
from src.api.models import (
    CanteiroModel,
    CulturaModel,
    InsumoModel,
    PlantioInsumoModel,
    PlantioModel,
    UsuarioModel,
)
from src.api.schemas import (
    InsumoUsoInput,
    PerfilUsuarioEnum,
    Plantio,
    PlantioInput,
    PlantioInsumo,
)
from src.api.security import get_current_user, require_roles

router = APIRouter(prefix="/plantios", tags=["Plantios"])


@router.get(
    "",
    response_model=List[Plantio],
    status_code=status.HTTP_200_OK,
    summary="Lista plantios",
)
def list_plantios(db: Session = Depends(get_db)) -> List[Plantio]:
    plantios = (
        db.query(PlantioModel)
        .options(
            selectinload(PlantioModel.cultura),
            selectinload(PlantioModel.canteiro),
        )
        .order_by(PlantioModel.id_plantio)
        .all()
    )
    return [Plantio.model_validate(p) for p in plantios]


@router.post(
    "",
    response_model=Plantio,
    status_code=status.HTTP_201_CREATED,
    summary="Cria plantio",
    dependencies=[Depends(get_current_user)],
)
def create_plantio(payload: PlantioInput, db: Session = Depends(get_db)) -> Plantio:
    cultura = db.query(CulturaModel).filter(CulturaModel.id_cultura == payload.id_cultura).first()
    if not cultura:
        raise NotFoundException(detail=f"Cultura com ID {payload.id_cultura} não encontrada.")

    canteiro = db.query(CanteiroModel).filter(CanteiroModel.id_canteiro == payload.id_canteiro).first()
    if not canteiro:
        raise NotFoundException(detail=f"Canteiro com ID {payload.id_canteiro} não encontrado.")

    plantio = PlantioModel(
        id_cultura=payload.id_cultura,
        id_canteiro=payload.id_canteiro,
        data_plantio=payload.data_plantio,
        status=payload.status,
        peso_colhido=payload.peso_colhido,
    )
    db.add(plantio)
    db.commit()
    db.refresh(plantio)
    return Plantio.model_validate(plantio)


@router.get(
    "/{id}",
    response_model=Plantio,
    status_code=status.HTTP_200_OK,
    summary="Busca plantio pelo ID",
)
def get_plantio(id: int, db: Session = Depends(get_db)) -> Plantio:
    plantio = db.query(PlantioModel).filter(PlantioModel.id_plantio == id).first()
    if not plantio:
        raise NotFoundException(detail=f"Plantio com ID {id} não encontrado.")
    return Plantio.model_validate(plantio)


@router.put(
    "/{id}",
    response_model=Plantio,
    status_code=status.HTTP_200_OK,
    summary="Atualiza um plantio",
    dependencies=[Depends(get_current_user)],
)
def update_plantio(id: int, payload: PlantioInput, db: Session = Depends(get_db)) -> Plantio:
    plantio = db.query(PlantioModel).filter(PlantioModel.id_plantio == id).first()
    if not plantio:
        raise NotFoundException(detail=f"Plantio com ID {id} não encontrado.")

    cultura = db.query(CulturaModel).filter(CulturaModel.id_cultura == payload.id_cultura).first()
    if not cultura:
        raise NotFoundException(detail=f"Cultura com ID {payload.id_cultura} não encontrada.")

    canteiro = db.query(CanteiroModel).filter(CanteiroModel.id_canteiro == payload.id_canteiro).first()
    if not canteiro:
        raise NotFoundException(detail=f"Canteiro com ID {payload.id_canteiro} não encontrado.")

    plantio.id_cultura = payload.id_cultura
    plantio.id_canteiro = payload.id_canteiro
    plantio.data_plantio = payload.data_plantio
    plantio.status = payload.status
    plantio.peso_colhido = payload.peso_colhido

    db.commit()
    db.refresh(plantio)
    return Plantio.model_validate(plantio)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deleta um plantio",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def delete_plantio(id: int, db: Session = Depends(get_db)) -> None:
    plantio = db.query(PlantioModel).filter(PlantioModel.id_plantio == id).first()
    if not plantio:
        raise NotFoundException(detail=f"Plantio com ID {id} não encontrado.")

    db.delete(plantio)
    db.commit()


# ============================================================================
# Sub-rotas: Insumos do Plantio com Desconto / Estorno Atômico de Estoque
# ============================================================================

@router.get(
    "/{id}/insumos",
    response_model=List[PlantioInsumo],
    status_code=status.HTTP_200_OK,
    summary="Lista insumos usados no plantio",
)
def list_plantio_insumos(id: int, db: Session = Depends(get_db)) -> List[PlantioInsumo]:
    plantio = db.query(PlantioModel).filter(PlantioModel.id_plantio == id).first()
    if not plantio:
        raise NotFoundException(detail=f"Plantio com ID {id} não encontrado.")

    itens = db.query(PlantioInsumoModel).filter(PlantioInsumoModel.id_plantio == id).all()
    return [PlantioInsumo.model_validate(i) for i in itens]


@router.post(
    "/{id}/insumos",
    response_model=PlantioInsumo,
    status_code=status.HTTP_201_CREATED,
    summary="Vincula um insumo ao plantio e desconta do estoque",
    dependencies=[Depends(get_current_user)],
)
def add_plantio_insumo(
    id: int, payload: InsumoUsoInput, db: Session = Depends(get_db)
) -> PlantioInsumo:
    plantio = db.query(PlantioModel).filter(PlantioModel.id_plantio == id).first()
    if not plantio:
        raise NotFoundException(detail=f"Plantio com ID {id} não encontrado.")

    insumo = db.query(InsumoModel).filter(InsumoModel.id_insumo == payload.id_insumo).first()
    if not insumo:
        raise NotFoundException(detail=f"Insumo com ID {payload.id_insumo} não encontrado.")

    if insumo.quantidade_estoque < payload.quantidade_utilizada:
        raise BadRequestException(
            detail=f"Estoque insuficiente: disponível {insumo.quantidade_estoque}, solicitado {payload.quantidade_utilizada}."
        )

    # Desconto atômico
    insumo.quantidade_estoque -= payload.quantidade_utilizada

    vinculo = (
        db.query(PlantioInsumoModel)
        .filter(
            PlantioInsumoModel.id_plantio == id,
            PlantioInsumoModel.id_insumo == payload.id_insumo,
        )
        .first()
    )

    if vinculo:
        vinculo.quantidade_utilizada += payload.quantidade_utilizada
    else:
        vinculo = PlantioInsumoModel(
            id_plantio=id,
            id_insumo=payload.id_insumo,
            quantidade_utilizada=payload.quantidade_utilizada,
        )
        db.add(vinculo)

    db.commit()
    db.refresh(vinculo)
    return PlantioInsumo.model_validate(vinculo)


@router.delete(
    "/{id}/insumos/{id_insumo}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um insumo do plantio e estorna estoque",
    dependencies=[Depends(get_current_user)],
)
def remove_plantio_insumo(id: int, id_insumo: int, db: Session = Depends(get_db)) -> None:
    vinculo = (
        db.query(PlantioInsumoModel)
        .filter(
            PlantioInsumoModel.id_plantio == id,
            PlantioInsumoModel.id_insumo == id_insumo,
        )
        .first()
    )
    if not vinculo:
        raise NotFoundException(
            detail=f"Vínculo do insumo {id_insumo} com o plantio {id} não encontrado."
        )

    insumo = db.query(InsumoModel).filter(InsumoModel.id_insumo == id_insumo).first()
    if insumo:
        # Estorno atômico
        insumo.quantidade_estoque += vinculo.quantidade_utilizada

    db.delete(vinculo)
    db.commit()
