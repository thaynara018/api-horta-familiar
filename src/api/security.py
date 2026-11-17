"""Módulo de Segurança, Autenticação JWT e Autorização RBAC.

Padrões:
- Assinatura HS256
- HTTPBearer(auto_error=False) para controle estrito de RFC 9457
- Dependências get_current_user (401) e require_roles (403)
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, List, Optional, Union

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.api.database import get_db, hash_password, verify_password
from src.api.exceptions import ForbiddenException, UnauthorizedException
from src.api.models import UsuarioModel
from src.api.schemas import PerfilUsuarioEnum

# Configurações de JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "horta-familiar-secret-key-super-secure-fatec-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 horas

# Desativar auto_error para interceptar ausência de token e retornar 401 RFC 9457
http_bearer = HTTPBearer(auto_error=False)


# ============================================================================
# Utilitários de Criptografia e Tokens
# ============================================================================

def get_password_hash(password: str) -> str:
    """Retorna o hash seguro da senha."""
    return hash_password(password)


def check_password(plain_password: str, hashed_password: str) -> bool:
    """Valida a senha contra o hash armazenado."""
    return verify_password(plain_password, hashed_password)


def create_access_token(
    data: dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Cria um token JWT assinado com HS256 contendo sub, email, perfil, iat e exp."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica e valida o token JWT. Dispara UnauthorizedException se inválido/expirado."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(detail="Token de autenticação expirado.")
    except jwt.InvalidTokenError:
        raise UnauthorizedException(detail="Token de autenticação inválido.")


# ============================================================================
# Dependências FastAPI para Injeção de Segurança
# ============================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> UsuarioModel:
    """Dependência para obter o usuário autenticado a partir do token Bearer JWT.

    Dispara 401 Unauthorized (RFC 9457) caso o token esteja ausente, inválido ou o usuário não exista.
    """
    if credentials is None or not credentials.credentials:
        raise UnauthorizedException(
            detail="Token de autenticação não fornecido no cabeçalho Authorization."
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(
            detail="Token de autenticação não contém o identificador do usuário."
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise UnauthorizedException(
            detail="Identificador de usuário inválido contido no token."
        )

    usuario = db.query(UsuarioModel).filter(UsuarioModel.id_usuario == user_id).first()
    if not usuario:
        raise UnauthorizedException(
            detail="Usuário associado a este token não foi encontrado no sistema."
        )

    return usuario


def require_roles(
    required_roles: List[Union[str, PerfilUsuarioEnum]]
) -> Callable[..., UsuarioModel]:
    """Fábrica de dependência para autorização baseada em papéis (RBAC).

    Dispara 403 Forbidden (RFC 9457) se o perfil do usuário não estiver na lista permitida.
    """
    # Normaliza lista de perfis permitidos para strings
    allowed_roles = [
        role.value if isinstance(role, PerfilUsuarioEnum) else str(role)
        for role in required_roles
    ]

    def role_checker(
        current_user: UsuarioModel = Depends(get_current_user),
    ) -> UsuarioModel:
        user_role = (
            current_user.perfil.value
            if isinstance(current_user.perfil, PerfilUsuarioEnum)
            else str(current_user.perfil)
        )

        if user_role not in allowed_roles:
            raise ForbiddenException(
                detail=f"Acesso negado: o perfil '{user_role}' não possui permissão para executar esta operação."
            )
        return current_user

    return role_checker


# Alias para require_role no singular
require_role = require_roles
