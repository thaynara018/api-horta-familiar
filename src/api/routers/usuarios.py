"""Router de Usuários da Horta.

Acesso restrito a ADMIN para todas as operações conforme RBAC.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.api.database import get_db, hash_password
from src.api.exceptions import ConflictException, NotFoundException
from src.api.models import UsuarioModel
from src.api.schemas import PerfilUsuarioEnum, Usuario, UsuarioInput
from src.api.security import require_roles

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
    dependencies=[Depends(require_roles([PerfilUsuarioEnum.ADMIN]))],
)


@router.get(
    "",
    response_model=List[Usuario],
    status_code=status.HTTP_200_OK,
    summary="Lista todos os usuários",
)
def list_usuarios(db: Session = Depends(get_db)) -> List[Usuario]:
    users = db.query(UsuarioModel).order_by(UsuarioModel.id_usuario).all()
    return [Usuario.model_validate(u) for u in users]


@router.post(
    "",
    response_model=Usuario,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo usuário",
)
def create_usuario(payload: UsuarioInput, db: Session = Depends(get_db)) -> Usuario:
    existente = db.query(UsuarioModel).filter(UsuarioModel.email == payload.email).first()
    if existente:
        raise ConflictException(detail=f"O e-mail '{payload.email}' já está cadastrado no sistema.")

    novo_usuario = UsuarioModel(
        nome=payload.nome,
        email=payload.email,
        senha_hash=hash_password(payload.senha),
        perfil=payload.perfil,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return Usuario.model_validate(novo_usuario)


@router.get(
    "/{id}",
    response_model=Usuario,
    status_code=status.HTTP_200_OK,
    summary="Busca um usuário pelo ID",
)
def get_usuario(id: int, db: Session = Depends(get_db)) -> Usuario:
    user = db.query(UsuarioModel).filter(UsuarioModel.id_usuario == id).first()
    if not user:
        raise NotFoundException(detail=f"Usuário com ID {id} não encontrado.")
    return Usuario.model_validate(user)


@router.put(
    "/{id}",
    response_model=Usuario,
    status_code=status.HTTP_200_OK,
    summary="Atualiza um usuário",
)
def update_usuario(id: int, payload: UsuarioInput, db: Session = Depends(get_db)) -> Usuario:
    user = db.query(UsuarioModel).filter(UsuarioModel.id_usuario == id).first()
    if not user:
        raise NotFoundException(detail=f"Usuário com ID {id} não encontrado.")

    if payload.email != user.email:
        existente = db.query(UsuarioModel).filter(UsuarioModel.email == payload.email).first()
        if existente:
            raise ConflictException(detail=f"O e-mail '{payload.email}' já está em uso.")

    user.nome = payload.nome
    user.email = payload.email
    user.senha_hash = hash_password(payload.senha)
    user.perfil = payload.perfil

    db.commit()
    db.refresh(user)
    return Usuario.model_validate(user)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deleta um usuário",
)
def delete_usuario(id: int, db: Session = Depends(get_db)) -> None:
    user = db.query(UsuarioModel).filter(UsuarioModel.id_usuario == id).first()
    if not user:
        raise NotFoundException(detail=f"Usuário com ID {id} não encontrado.")

    db.delete(user)
    db.commit()
