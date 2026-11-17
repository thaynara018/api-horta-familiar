"""Tratamento semântico de erros conforme a RFC 9457 (Problem Details).

Padroniza as respostas de erro HTTP em conformidade com o STYLEGUIDE.md.
"""

from typing import Any, List, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


# ============================================================================
# Hierarquia de Exceções de Domínio
# ============================================================================

class AppException(Exception):
    """Exceção base para erros de aplicação no padrão RFC 9457."""

    def __init__(
        self,
        status_code: int,
        type_uri: str,
        title: str,
        detail: str,
        invalid_params: Optional[List[dict[str, str]]] = None,
    ):
        super().__init__(detail)
        self.status_code = status_code
        self.type_uri = type_uri
        self.title = title
        self.detail = detail
        self.invalid_params = invalid_params


class BadRequestException(AppException):
    """Erro 400 Bad Request."""

    def __init__(
        self,
        detail: str = "A requisição enviada é inválida ou malformada.",
        invalid_params: Optional[List[dict[str, str]]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            type_uri="https://api.hortafamiliar.dev/errors/bad-request",
            title="Bad Request",
            detail=detail,
            invalid_params=invalid_params,
        )


class UnauthorizedException(AppException):
    """Erro 401 Unauthorized."""

    def __init__(
        self,
        detail: str = "Credenciais de autenticação ausentes, expiradas ou inválidas.",
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            type_uri="https://api.hortafamiliar.dev/errors/unauthorized",
            title="Unauthorized",
            detail=detail,
        )


class ForbiddenException(AppException):
    """Erro 403 Forbidden."""

    def __init__(
        self,
        detail: str = "Você não tem permissão para acessar este recurso.",
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            type_uri="https://api.hortafamiliar.dev/errors/forbidden",
            title="Forbidden",
            detail=detail,
        )


class NotFoundException(AppException):
    """Erro 404 Not Found."""

    def __init__(
        self,
        detail: str = "O recurso solicitado não foi encontrado.",
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            type_uri="https://api.hortafamiliar.dev/errors/not-found",
            title="Not Found",
            detail=detail,
        )


class ConflictException(AppException):
    """Erro 409 Conflict."""

    def __init__(
        self,
        detail: str = "Conflito com o estado atual do recurso.",
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            type_uri="https://api.hortafamiliar.dev/errors/conflict",
            title="Conflict",
            detail=detail,
        )


class ValidationException(AppException):
    """Erro 422 Unprocessable Entity."""

    def __init__(
        self,
        detail: str = "Falha na validação semântica dos dados enviados.",
        invalid_params: Optional[List[dict[str, str]]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            type_uri="https://api.hortafamiliar.dev/errors/validation-error",
            title="Unprocessable Entity",
            detail=detail,
            invalid_params=invalid_params,
        )


# ============================================================================
# Construtor de Resposta RFC 9457
# ============================================================================

def build_problem_response(
    status_code: int,
    type_uri: str,
    title: str,
    detail: str,
    instance: str,
    invalid_params: Optional[List[dict[str, str]]] = None,
) -> JSONResponse:
    """Gera um JSONResponse estritamente compatível com o schema ApiError da RFC 9457."""
    payload: dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    if invalid_params is not None:
        payload["invalidParams"] = invalid_params

    return JSONResponse(
        status_code=status_code,
        content=payload,
        media_type="application/problem+json",
    )


# ============================================================================
# Handlers Globais para o FastAPI
# ============================================================================

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handler para todas as subclasses de AppException."""
    return build_problem_response(
        status_code=exc.status_code,
        type_uri=exc.type_uri,
        title=exc.title,
        detail=exc.detail,
        instance=request.url.path,
        invalid_params=exc.invalid_params,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handler para erros de validação do Pydantic (status 422)."""
    invalid_params: List[dict[str, str]] = []

    for err in exc.errors():
        loc = err.get("loc", [])
        field_name = str(loc[-1]) if loc else "body"
        msg = err.get("msg", "Valor inválido")
        invalid_params.append({
            "name": field_name,
            "reason": msg,
        })

    return build_problem_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        type_uri="https://api.hortafamiliar.dev/errors/validation-error",
        title="Unprocessable Entity",
        detail="A validação dos parâmetros enviados falhou.",
        instance=request.url.path,
        invalid_params=invalid_params,
    )


async def starlette_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handler para exceções HTTP genéricas do Starlette/FastAPI."""
    status_map = {
        400: ("https://api.hortafamiliar.dev/errors/bad-request", "Bad Request"),
        401: ("https://api.hortafamiliar.dev/errors/unauthorized", "Unauthorized"),
        403: ("https://api.hortafamiliar.dev/errors/forbidden", "Forbidden"),
        404: ("https://api.hortafamiliar.dev/errors/not-found", "Not Found"),
        409: ("https://api.hortafamiliar.dev/errors/conflict", "Conflict"),
        422: ("https://api.hortafamiliar.dev/errors/validation-error", "Unprocessable Entity"),
    }

    type_uri, title = status_map.get(
        exc.status_code,
        ("https://api.hortafamiliar.dev/errors/internal-error", "Internal Server Error"),
    )

    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    return build_problem_response(
        status_code=exc.status_code,
        type_uri=type_uri,
        title=title,
        detail=detail,
        instance=request.url.path,
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback para qualquer erro 500 não tratado."""
    return build_problem_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        type_uri="https://api.hortafamiliar.dev/errors/internal-error",
        title="Internal Server Error",
        detail="Ocorreu um erro interno no servidor.",
        instance=request.url.path,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos os exception handlers na aplicação FastAPI."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
