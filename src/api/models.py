"""Modelos ORM SQLAlchemy 2.0 para a API Horta Familiar.

Fonte da Verdade: horta_api.Apidog.json e STYLEGUIDE.md
Padrão: DeclarativeBase, Mapped, mapped_column, relationship e ForeignKey
"""

from datetime import date, time
from typing import List, Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Time, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.api.schemas import (
    PerfilUsuarioEnum,
    StatusPlantioEnum,
    StatusTarefaEnum,
    TipoInsumoEnum,
)


class Base(DeclarativeBase):
    """Classe base declarativa do SQLAlchemy 2.0."""
    pass


class UsuarioModel(Base):
    """Modelo ORM para usuários do sistema."""
    __tablename__ = "usuarios"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[PerfilUsuarioEnum] = mapped_column(
        SQLEnum(PerfilUsuarioEnum, name="perfil_usuario_enum"),
        nullable=False,
        default=PerfilUsuarioEnum.OPERACIONAL,
    )

    # Relacionamentos
    tarefas: Mapped[List["TarefaModel"]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
    )


class CulturaModel(Base):
    """Modelo ORM para culturas agrícolas."""
    __tablename__ = "culturas"

    id_cultura: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tempo_maturacao_dias: Mapped[int] = mapped_column(Integer, nullable=False)
    espacamento_ideal: Mapped[float] = mapped_column(Float, nullable=False)

    # Relacionamentos
    plantios: Mapped[List["PlantioModel"]] = relationship(
        back_populates="cultura",
    )


class CanteiroModel(Base):
    """Modelo ORM para canteiros da horta."""
    __tablename__ = "canteiros"

    id_canteiro: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identificacao: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    area_m2: Mapped[float] = mapped_column(Float, nullable=False)

    # Relacionamentos
    plantios: Mapped[List["PlantioModel"]] = relationship(
        back_populates="canteiro",
    )
    tarefas: Mapped[List["TarefaModel"]] = relationship(
        back_populates="canteiro",
    )


class InsumoModel(Base):
    """Modelo ORM para insumos agrícolas em estoque."""
    __tablename__ = "insumos"

    id_insumo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[TipoInsumoEnum] = mapped_column(
        SQLEnum(TipoInsumoEnum, name="tipo_insumo_enum"),
        nullable=False,
    )
    quantidade_estoque: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estoque_minimo: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relacionamentos
    plantios_vinculados: Mapped[List["PlantioInsumoModel"]] = relationship(
        back_populates="insumo",
    )
    tarefas_vinculadas: Mapped[List["TarefaInsumoModel"]] = relationship(
        back_populates="insumo",
    )


class PlantioModel(Base):
    """Modelo ORM para plantios nos canteiros."""
    __tablename__ = "plantios"

    id_plantio: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_cultura: Mapped[int] = mapped_column(Integer, ForeignKey("culturas.id_cultura"), nullable=False)
    id_canteiro: Mapped[int] = mapped_column(Integer, ForeignKey("canteiros.id_canteiro"), nullable=False)
    data_plantio: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[StatusPlantioEnum] = mapped_column(
        SQLEnum(StatusPlantioEnum, name="status_plantio_enum"),
        nullable=False,
        default=StatusPlantioEnum.CRESCIMENTO,
    )
    peso_colhido: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relacionamentos com eager loading e navigability
    cultura: Mapped["CulturaModel"] = relationship(back_populates="plantios")
    canteiro: Mapped["CanteiroModel"] = relationship(back_populates="plantios")
    insumos_utilizados: Mapped[List["PlantioInsumoModel"]] = relationship(
        back_populates="plantio",
        cascade="all, delete-orphan",
    )


class PlantioInsumoModel(Base):
    """Tabela associativa de insumos consumidos em um plantio."""
    __tablename__ = "plantios_insumos"

    id_plantio: Mapped[int] = mapped_column(
        Integer, ForeignKey("plantios.id_plantio"), primary_key=True
    )
    id_insumo: Mapped[int] = mapped_column(
        Integer, ForeignKey("insumos.id_insumo"), primary_key=True
    )
    quantidade_utilizada: Mapped[float] = mapped_column(Float, nullable=False)

    # Relacionamentos
    plantio: Mapped["PlantioModel"] = relationship(back_populates="insumos_utilizados")
    insumo: Mapped["InsumoModel"] = relationship(back_populates="plantios_vinculados")


class TarefaModel(Base):
    """Modelo ORM para tarefas e agendamento da horta."""
    __tablename__ = "tarefas"

    id_tarefa: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_canteiro: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("canteiros.id_canteiro"), nullable=True)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    data_tarefa: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fim: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[StatusTarefaEnum] = mapped_column(
        SQLEnum(StatusTarefaEnum, name="status_tarefa_enum"),
        nullable=False,
        default=StatusTarefaEnum.PENDENTE,
    )

    # Relacionamentos
    usuario: Mapped["UsuarioModel"] = relationship(back_populates="tarefas")
    canteiro: Mapped[Optional["CanteiroModel"]] = relationship(back_populates="tarefas")
    insumos_utilizados: Mapped[List["TarefaInsumoModel"]] = relationship(
        back_populates="tarefa",
        cascade="all, delete-orphan",
    )


class TarefaInsumoModel(Base):
    """Tabela associativa de insumos consumidos em uma tarefa."""
    __tablename__ = "tarefas_insumos"

    id_tarefa: Mapped[int] = mapped_column(
        Integer, ForeignKey("tarefas.id_tarefa"), primary_key=True
    )
    id_insumo: Mapped[int] = mapped_column(
        Integer, ForeignKey("insumos.id_insumo"), primary_key=True
    )
    quantidade_utilizada: Mapped[float] = mapped_column(Float, nullable=False)

    # Relacionamentos
    tarefa: Mapped["TarefaModel"] = relationship(back_populates="insumos_utilizados")
    insumo: Mapped["InsumoModel"] = relationship(back_populates="tarefas_vinculadas")


# ============================================================================
# Aliases de compatibilidade arquitetural
# ============================================================================
UserModel = UsuarioModel
TaskModel = TarefaModel
ProjectModel = CanteiroModel
