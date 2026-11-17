"""Router de Tarefas da Horta.

Inclui validação de sobreposição de horários por canteiro,
controle atômico de estoque de insumos e proteção RBAC (ADMIN obrigatório para DELETE).
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy import and_
from sqlalchemy.orm import Session, selectinload

from src.api.database import get_db
from src.api.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from src.api.models import (
    CanteiroModel,
    InsumoModel,
    TarefaInsumoModel,
    TarefaModel,
    UsuarioModel,
)
from src.api.schemas import (
    InsumoUsoInput,
    PerfilUsuarioEnum,
    StatusTarefaEnum,
    Tarefa,
    TarefaInput,
    TarefaInsumo,
)
from src.api.security import get_current_user, require_roles

router = APIRouter(prefix="/tarefas", tags=["Tarefas"])


def check_tarefa_conflict(
    db: Session,
    id_canteiro: int | None,
    data_tarefa,
    hora_inicio,
    hora_fim,
    tarefa_id_ignore: int | None = None,
) -> None:
    """Verifica se há conflito de agendamento no mesmo canteiro e data."""
    if not id_canteiro:
        return

    query = db.query(TarefaModel).filter(
        TarefaModel.id_canteiro == id_canteiro,
        TarefaModel.data_tarefa == data_tarefa,
        TarefaModel.status != StatusTarefaEnum.CANCELADA,
        and_(
            TarefaModel.hora_inicio < hora_fim,
            TarefaModel.hora_fim > hora_inicio,
        ),
    )

    if tarefa_id_ignore:
        query = query.filter(TarefaModel.id_tarefa != tarefa_id_ignore)

    conflito = query.first()
    if conflito:
        raise ConflictException(
            detail=f"Conflito de agendamento no canteiro {id_canteiro}: já existe a tarefa #{conflito.id_tarefa} ({conflito.hora_inicio} - {conflito.hora_fim}) neste horário."
        )


@router.get(
    "",
    response_model=List[Tarefa],
    status_code=status.HTTP_200_OK,
    summary="Lista tarefas",
)
def list_tarefas(db: Session = Depends(get_db)) -> List[Tarefa]:
    tarefas = (
        db.query(TarefaModel)
        .options(
            selectinload(TarefaModel.usuario),
            selectinload(TarefaModel.canteiro),
        )
        .order_by(TarefaModel.id_tarefa)
        .all()
    )
    return [Tarefa.model_validate(t) for t in tarefas]


@router.post(
    "",
    response_model=Tarefa,
    status_code=status.HTTP_201_CREATED,
    summary="Cria tarefa",
    dependencies=[Depends(get_current_user)],
)
def create_tarefa(payload: TarefaInput, db: Session = Depends(get_db)) -> Tarefa:
    usuario = db.query(UsuarioModel).filter(UsuarioModel.id_usuario == payload.id_usuario).first()
    if not usuario:
        raise NotFoundException(detail=f"Usuário com ID {payload.id_usuario} não encontrado.")

    if payload.id_canteiro:
        canteiro = db.query(CanteiroModel).filter(CanteiroModel.id_canteiro == payload.id_canteiro).first()
        if not canteiro:
            raise NotFoundException(detail=f"Canteiro com ID {payload.id_canteiro} não encontrado.")

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
    summary="Busca tarefa pelo ID",
)
def get_tarefa(id: int, db: Session = Depends(get_db)) -> Tarefa:
    tarefa = db.query(TarefaModel).filter(TarefaModel.id_tarefa == id).first()
    if not tarefa:
        raise NotFoundException(detail=f"Tarefa com ID {id} não encontrada.")
    return Tarefa.model_validate(tarefa)


@router.put(
    "/{id}",
    response_model=Tarefa,
    status_code=status.HTTP_200_OK,
    summary="Atualiza uma tarefa",
    dependencies=[Depends(get_current_user)],
)
def update_tarefa(id: int, payload: TarefaInput, db: Session = Depends(get_db)) -> Tarefa:
    tarefa = db.query(TarefaModel).filter(TarefaModel.id_tarefa == id).first()
    if not tarefa:
        raise NotFoundException(detail=f"Tarefa com ID {id} não encontrada.")

    usuario = db.query(UsuarioModel).filter(UsuarioModel.id_usuario == payload.id_usuario).first()
    if not usuario:
        raise NotFoundException(detail=f"Usuário com ID {payload.id_usuario} não encontrado.")

    if payload.id_canteiro:
        canteiro = db.query(CanteiroModel).filter(CanteiroModel.id_canteiro == payload.id_canteiro).first()
        if not canteiro:
            raise NotFoundException(detail=f"Canteiro com ID {payload.id_canteiro} não encontrado.")

    if payload.hora_inicio >= payload.hora_fim:
        raise BadRequestException(detail="A hora de início deve ser anterior à hora de término.")

    check_tarefa_conflict(
        db=db,
        id_canteiro=payload.id_canteiro,
        data_tarefa=payload.data_tarefa,
        hora_inicio=payload.hora_inicio,
        hora_fim=payload.hora_fim,
        tarefa_id_ignore=id,
    )

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
    summary="Deleta uma tarefa",
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)
def delete_tarefa(id: int, db: Session = Depends(get_db)) -> None:
    tarefa = db.query(TarefaModel).filter(TarefaModel.id_tarefa == id).first()
    if not tarefa:
        raise NotFoundException(detail=f"Tarefa com ID {id} não encontrada.")

    db.delete(tarefa)
    db.commit()


# ============================================================================
# Sub-rotas: Insumos da Tarefa com Desconto e Estorno Atômico
# ============================================================================

@router.get(
    "/{id}/insumos",
    response_model=List[TarefaInsumo],
    status_code=status.HTTP_200_OK,
    summary="Lista insumos usados na tarefa",
)
def list_tarefa_insumos(id: int, db: Session = Depends(get_db)) -> List[TarefaInsumo]:
    tarefa = db.query(TarefaModel).filter(TarefaModel.id_tarefa == id).first()
    if not tarefa:
        raise NotFoundException(detail=f"Tarefa com ID {id} não encontrada.")

    itens = db.query(TarefaInsumoModel).filter(TarefaInsumoModel.id_tarefa == id).all()
    return [TarefaInsumo.model_validate(i) for i in itens]


@router.post(
    "/{id}/insumos",
    response_model=TarefaInsumo,
    status_code=status.HTTP_201_CREATED,
    summary="Vincula um insumo à tarefa e desconta do estoque",
    dependencies=[Depends(get_current_user)],
)
def add_tarefa_insumo(
    id: int, payload: InsumoUsoInput, db: Session = Depends(get_db)
) -> TarefaInsumo:
    tarefa = db.query(TarefaModel).filter(TarefaModel.id_tarefa == id).first()
    if not tarefa:
        raise NotFoundException(detail=f"Tarefa com ID {id} não encontrada.")

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
        db.query(TarefaInsumoModel)
        .filter(
            TarefaInsumoModel.id_tarefa == id,
            TarefaInsumoModel.id_insumo == payload.id_insumo,
        )
        .first()
    )

    if vinculo:
        vinculo.quantidade_utilizada += payload.quantidade_utilizada
    else:
        vinculo = TarefaInsumoModel(
            id_tarefa=id,
            id_insumo=payload.id_insumo,
            quantidade_utilizada=payload.quantidade_utilizada,
        )
        db.add(vinculo)

    db.commit()
    db.refresh(vinculo)
    return TarefaInsumo.model_validate(vinculo)


@router.delete(
    "/{id}/insumos/{id_insumo}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um insumo da tarefa e estorna estoque",
    dependencies=[Depends(get_current_user)],
)
def remove_tarefa_insumo(id: int, id_insumo: int, db: Session = Depends(get_db)) -> None:
    vinculo = (
        db.query(TarefaInsumoModel)
        .filter(
            TarefaInsumoModel.id_tarefa == id,
            TarefaInsumoModel.id_insumo == id_insumo,
        )
        .first()
    )
    if not vinculo:
        raise NotFoundException(
            detail=f"Vínculo do insumo {id_insumo} com a tarefa {id} não encontrado."
        )

    insumo = db.query(InsumoModel).filter(InsumoModel.id_insumo == id_insumo).first()
    if insumo:
        # Estorno atômico
        insumo.quantidade_estoque += vinculo.quantidade_utilizada

    db.delete(vinculo)
    db.commit()
