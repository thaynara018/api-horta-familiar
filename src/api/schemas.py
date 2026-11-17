"""Schemas Pydantic v2 para a API Horta Familiar.

Fonte da Verdade: horta_api.Apidog.json
Padrão Arquitetural: Pydantic v2 com ConfigDict(from_attributes=True, populate_by_name=True)
"""

from datetime import date, time
from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ============================================================================
# Enums de Domínio
# ============================================================================

class PerfilUsuarioEnum(str, Enum):
    """Perfis de acesso de usuário (RBAC)."""
    ADMIN = "ADMIN"
    OPERACIONAL = "OPERACIONAL"


class TipoInsumoEnum(str, Enum):
    """Categorias de insumos agrícolas."""
    SEMENTE = "SEMENTE"
    FERTILIZANTE = "FERTILIZANTE"
    FERRAMENTA = "FERRAMENTA"


class StatusPlantioEnum(str, Enum):
    """Estados do ciclo de vida de um plantio."""
    CRESCIMENTO = "CRESCIMENTO"
    COLHIDO = "COLHIDO"
    PERDIDO = "PERDIDO"


class StatusTarefaEnum(str, Enum):
    """Estados de execução de uma tarefa."""
    PENDENTE = "PENDENTE"
    CONCLUIDA = "CONCLUIDA"
    CANCELADA = "CANCELADA"


# ============================================================================
# Base Model Configurada
# ============================================================================

class BaseSchema(BaseModel):
    """Configuração base herdada por todos os schemas."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


# ============================================================================
# RFC 9457 — Problem Details (Tratamento Semântico de Erros)
# ============================================================================

class InvalidParam(BaseSchema):
    """Representação de parâmetro ou campo inválido."""
    name: str = Field(..., description="Nome do campo que falhou na validação")
    reason: str = Field(..., description="Descrição da falha de validação")


class ApiError(BaseSchema):
    """Schema oficial de erro RFC 9457 (Problem Details)."""
    type: str = Field(..., description="URI identificadora do tipo de erro")
    title: str = Field(..., description="Resumo curto e legível do erro")
    status: int = Field(..., description="Código de status HTTP")
    detail: str = Field(..., description="Explicação detalhada da ocorrência")
    instance: str = Field(..., description="URI requisitada")
    invalidParams: Optional[list[InvalidParam]] = Field(
        default=None,
        description="Lista de campos com falha de validação quando aplicável"
    )


# ============================================================================
# DTOs de Autenticação (JWT & RBAC)
# ============================================================================

class LoginRequestDTO(BaseSchema):
    """DTO para requisição de login."""
    email: EmailStr = Field(..., description="Email cadastrado do usuário")
    senha: str = Field(..., min_length=1, description="Senha do usuário")


class TokenResponseDTO(BaseSchema):
    """DTO com token JWT e tipo."""
    access_token: str = Field(..., description="Token de acesso JWT")
    token_type: str = Field(default="bearer", description="Tipo do token (bearer)")


class TokenPayload(BaseSchema):
    """Dados encapsulados no payload do token JWT."""
    sub: str = Field(..., description="Identificador único (ID) do usuário")
    email: str = Field(..., description="Email do usuário")
    perfil: str = Field(..., description="Perfil de acesso (ADMIN ou OPERACIONAL)")
    exp: int = Field(..., description="Timestamp Unix de expiração")
    iat: int = Field(..., description="Timestamp Unix de emissão")


# ============================================================================
# Schemas de Usuário
# ============================================================================

class UsuarioInput(BaseSchema):
    """Payload para criação ou atualização de usuário."""
    nome: str = Field(..., max_length=100, description="Nome completo do usuário")
    email: EmailStr = Field(..., max_length=150, description="Email único do usuário")
    senha: str = Field(..., min_length=4, max_length=255, description="Senha do usuário em texto puro")
    perfil: PerfilUsuarioEnum = Field(..., description="Perfil de acesso")


class Usuario(BaseSchema):
    """Schema de retorno para visualização de usuário."""
    id_usuario: int = Field(..., description="Identificador único do usuário")
    nome: str = Field(..., description="Nome completo do usuário")
    email: EmailStr = Field(..., description="Email único do usuário")
    perfil: PerfilUsuarioEnum = Field(..., description="Perfil de acesso")


class UserResponse(Usuario):
    """DTO de resposta de usuário (compatível com autenticação /auth/me)."""
    pass


# ============================================================================
# Schemas de Cultura
# ============================================================================

class CulturaInput(BaseSchema):
    """Payload de entrada para criação ou atualização de cultura."""
    nome: str = Field(..., max_length=100, description="Nome da cultura agrícola")
    tempo_maturacao_dias: int = Field(..., ge=1, description="Tempo estimado para maturação em dias")
    espacamento_ideal: float = Field(..., gt=0, description="Espaçamento ideal entre mudas (em metros)")


class Cultura(BaseSchema):
    """Schema de retorno de cultura agrícola."""
    id_cultura: int = Field(..., description="Identificador único da cultura")
    nome: str = Field(..., description="Nome da cultura")
    tempo_maturacao_dias: int = Field(..., description="Tempo estimado para maturação em dias")
    espacamento_ideal: float = Field(..., description="Espaçamento ideal em metros")


# ============================================================================
# Schemas de Canteiro
# ============================================================================

class CanteiroInput(BaseSchema):
    """Payload de entrada para criação ou atualização de canteiro."""
    identificacao: str = Field(..., max_length=50, description="Identificação ou código único do canteiro")
    area_m2: float = Field(..., gt=0, description="Área do canteiro em metros quadrados")


class Canteiro(BaseSchema):
    """Schema de retorno de canteiro."""
    id_canteiro: int = Field(..., description="Identificador único do canteiro")
    identificacao: str = Field(..., description="Identificação do canteiro")
    area_m2: float = Field(..., description="Área em metros quadrados")


# ============================================================================
# Schemas de Insumo
# ============================================================================

class InsumoInput(BaseSchema):
    """Payload de entrada para criação ou atualização de insumo."""
    nome: str = Field(..., max_length=100, description="Nome do insumo")
    tipo: TipoInsumoEnum = Field(..., description="Tipo do insumo")
    quantidade_estoque: float = Field(..., ge=0, description="Quantidade atual disponível em estoque")
    estoque_minimo: float = Field(..., ge=0, description="Quantidade mínima de segurança")


class Insumo(BaseSchema):
    """Schema de retorno de insumo."""
    id_insumo: int = Field(..., description="Identificador único do insumo")
    nome: str = Field(..., description="Nome do insumo")
    tipo: TipoInsumoEnum = Field(..., description="Tipo do insumo")
    quantidade_estoque: float = Field(..., description="Quantidade atual em estoque")
    estoque_minimo: float = Field(..., description="Estoque mínimo de segurança")


class InsumoUsoInput(BaseSchema):
    """Payload para vincular consumo de insumo a plantio ou tarefa."""
    id_insumo: int = Field(..., description="Identificador único do insumo")
    quantidade_utilizada: float = Field(..., gt=0, description="Quantidade consumida (descontada do estoque)")


# ============================================================================
# Schemas de Plantio
# ============================================================================

class PlantioInput(BaseSchema):
    """Payload de entrada para criação ou atualização de plantio."""
    id_cultura: int = Field(..., description="Identificador da cultura associada")
    id_canteiro: int = Field(..., description="Identificador do canteiro associado")
    data_plantio: date = Field(..., description="Data de realização do plantio")
    status: StatusPlantioEnum = Field(..., description="Status do plantio")
    peso_colhido: Optional[float] = Field(default=None, ge=0, description="Peso total colhido em kg")


class Plantio(BaseSchema):
    """Schema de retorno de plantio."""
    id_plantio: int = Field(..., description="Identificador único do plantio")
    id_cultura: int = Field(..., description="ID da cultura")
    id_canteiro: int = Field(..., description="ID do canteiro")
    data_plantio: date = Field(..., description="Data de realização do plantio")
    status: StatusPlantioEnum = Field(..., description="Status atual do plantio")
    peso_colhido: Optional[float] = Field(default=None, description="Peso colhido em kg")


class PlantioInsumo(BaseSchema):
    """Associação de consumo de insumo em um plantio."""
    id_plantio: int = Field(..., description="Identificador do plantio")
    id_insumo: int = Field(..., description="Identificador do insumo utilizado")
    quantidade_utilizada: float = Field(..., description="Quantidade consumida")


# ============================================================================
# Schemas de Tarefa
# ============================================================================

class TarefaInput(BaseSchema):
    """Payload de entrada para criação ou atualização de tarefa."""
    id_usuario: int = Field(..., description="Identificador do usuário responsável")
    id_canteiro: Optional[int] = Field(default=None, description="Identificador do canteiro (opcional)")
    descricao: str = Field(..., max_length=255, description="Descrição detalhada da atividade")
    data_tarefa: date = Field(..., description="Data agendada para a tarefa")
    hora_inicio: time = Field(..., description="Horário de início previsto")
    hora_fim: time = Field(..., description="Horário de término previsto")
    status: StatusTarefaEnum = Field(..., description="Status da tarefa")


class Tarefa(BaseSchema):
    """Schema de retorno de tarefa."""
    id_tarefa: int = Field(..., description="Identificador único da tarefa")
    id_usuario: int = Field(..., description="ID do usuário responsável")
    id_canteiro: Optional[int] = Field(default=None, description="ID do canteiro associado")
    descricao: str = Field(..., description="Descrição da atividade")
    data_tarefa: date = Field(..., description="Data da tarefa")
    hora_inicio: time = Field(..., description="Horário de início")
    hora_fim: time = Field(..., description="Horário de término")
    status: StatusTarefaEnum = Field(..., description="Status da tarefa")


class TarefaInsumo(BaseSchema):
    """Associação de consumo de insumo em uma tarefa."""
    id_tarefa: int = Field(..., description="Identificador da tarefa")
    id_insumo: int = Field(..., description="Identificador do insumo utilizado")
    quantidade_utilizada: float = Field(..., description="Quantidade consumida")


# ============================================================================
# Schemas de Dashboard
# ============================================================================

class DashboardProducaoItem(BaseSchema):
    """Item agregado da view consolidada de produção."""
    cultura: str = Field(..., description="Nome da cultura")
    canteiro: str = Field(..., description="Identificação do canteiro")
    total_plantios: int = Field(..., description="Contagem de plantios já colhidos")
    produtividade_total_kg: float = Field(..., description="Soma do peso colhido")
