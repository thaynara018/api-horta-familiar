"""Router do Dashboard de Produção da Horta.

Retorna relatório consolidado de produtividade agrupado por cultura e canteiro.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.models import CanteiroModel, CulturaModel, PlantioModel
from src.api.schemas import DashboardProducaoItem

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/producao",
    response_model=List[DashboardProducaoItem],
    status_code=status.HTTP_200_OK,
    summary="Relatório de produção consolidado",
)
def get_dashboard_producao(db: Session = Depends(get_db)) -> List[DashboardProducaoItem]:
    """Agrega a contagem de plantios e a produtividade total por cultura e canteiro."""
    resultados = (
        db.query(
            CulturaModel.nome.label("cultura"),
            CanteiroModel.identificacao.label("canteiro"),
            func.count(PlantioModel.id_plantio).label("total_plantios"),
            func.coalesce(func.sum(PlantioModel.peso_colhido), 0.0).label(
                "produtividade_total_kg"
            ),
        )
        .join(CulturaModel, PlantioModel.id_cultura == CulturaModel.id_cultura)
        .join(CanteiroModel, PlantioModel.id_canteiro == CanteiroModel.id_canteiro)
        .group_by(CulturaModel.nome, CanteiroModel.identificacao)
        .all()
    )

    return [
        DashboardProducaoItem(
            cultura=r.cultura,
            canteiro=r.canteiro,
            total_plantios=r.total_plantios,
            produtividade_total_kg=float(r.produtividade_total_kg),
        )
        for r in resultados
    ]
