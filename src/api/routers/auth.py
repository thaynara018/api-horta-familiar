"""Router de Autenticação (JWT e RBAC).

Rotas:
- POST /api/v1/auth/login e POST /auth/login
- GET /api/v1/auth/me e GET /auth/me
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.exceptions import UnauthorizedException
from src.api.models import UsuarioModel
from src.api.schemas import LoginRequestDTO, TokenResponseDTO, UserResponse
from src.api.security import (
    check_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(tags=["Autenticação"])


@router.post(
    "/login",
    response_model=TokenResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Login de Usuário",
    description="Autentica usuário por e-mail e senha, gerando um token JWT de acesso.",
)
def login(payload: LoginRequestDTO, db: Session = Depends(get_db)) -> TokenResponseDTO:
    """Realiza a autenticação e retorna o JWT assinado."""
    usuario = db.query(UsuarioModel).filter(UsuarioModel.email == payload.email).first()

    if not usuario or not check_password(payload.senha, usuario.senha_hash):
        raise UnauthorizedException(detail="E-mail ou senha incorretos.")

    user_role = (
        usuario.perfil.value
        if hasattr(usuario.perfil, "value")
        else str(usuario.perfil)
    )

    token = create_access_token(
        data={
            "sub": str(usuario.id_usuario),
            "email": usuario.email,
            "perfil": user_role,
            "role": user_role,
        }
    )

    return TokenResponseDTO(access_token=token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Dados do Usuário Autenticado",
    description="Retorna as informações do perfil do usuário associado ao token JWT ativo.",
)
def get_me(current_user: UsuarioModel = Depends(get_current_user)) -> UserResponse:
    """Retorna o usuário corrente."""
    return UserResponse.model_validate(current_user)
