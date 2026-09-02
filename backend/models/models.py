"""
Modelos ORM del Sistema de Gestión Bibliotecaria.
Mapean 1 a 1 las tablas de database/schema.sql.
Fuente de verdad: diagrama de la base de datos (PDF).
"""

from datetime import date

from sqlalchemy import ForeignKey, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


# ---------- Tablas sin dependencias ----------

class Genero(Base):
    __tablename__ = "genero"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(unique=True)

    subgeneros: Mapped[list["Subgenero"]] = relationship(
        back_populates="genero", passive_deletes="all"
    )


class GrupoEditorial(Base):
    __tablename__ = "grupo_editorial"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str]

    editoriales: Mapped[list["Editorial"]] = relationship(
        back_populates="grupo_editorial", passive_deletes="all"
    )


class Autor(Base):
    __tablename__ = "autor"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str]
    apellido: Mapped[str]
    fecha_nacimiento: Mapped[date]
    fecha_fallecimiento: Mapped[date | None]
    nacionalidad: Mapped[str]

    libros: Mapped[list["Libro"]] = relationship(
        secondary="libro_autor", back_populates="autores"
    )


class Rango(Base):
    __tablename__ = "rango"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(unique=True)
    max_prestamos: Mapped[int]
    dias_prestamo: Mapped[int]

    socios: Mapped[list["Socio"]] = relationship(
        back_populates="rango", passive_deletes="all"
    )


# ---------- Tablas de segundo nivel ----------

class Subgenero(Base):
    __tablename__ = "subgenero"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str]
    id_genero: Mapped[int] = mapped_column(ForeignKey("genero.id"))

    genero: Mapped["Genero"] = relationship(back_populates="subgeneros")
    libros: Mapped[list["Libro"]] = relationship(
        back_populates="subgenero", passive_deletes="all"
    )


class Editorial(Base):
    __tablename__ = "editorial"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str]
    direccion: Mapped[str | None]
    fecha_fundacion: Mapped[date | None]
    id_grupo_editorial: Mapped[int] = mapped_column(ForeignKey("grupo_editorial.id"))

    grupo_editorial: Mapped["GrupoEditorial"] = relationship(back_populates="editoriales")
    libros: Mapped[list["Libro"]] = relationship(
        back_populates="editorial", passive_deletes="all"
    )


class Socio(Base):
    __tablename__ = "socio"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str]
    apellido: Mapped[str]
    dni: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    telefono: Mapped[str | None]
    id_rango: Mapped[int] = mapped_column(ForeignKey("rango.id"))
    fecha_alta: Mapped[date]
    fecha_baja: Mapped[date | None]

    rango: Mapped["Rango"] = relationship(back_populates="socios")
    prestamos: Mapped[list["Prestamo"]] = relationship(
        back_populates="socio", passive_deletes="all"
    )


# ---------- Libro y dependientes ----------

class Libro(Base):
    __tablename__ = "libro"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str]
    isbn: Mapped[str | None] = mapped_column(unique=True)
    id_subgenero: Mapped[int] = mapped_column(ForeignKey("subgenero.id"))
    id_editorial: Mapped[int] = mapped_column(ForeignKey("editorial.id"))
    fecha_publicacion: Mapped[date]
    idioma: Mapped[str]
    numero_edicion: Mapped[str]

    subgenero: Mapped["Subgenero"] = relationship(back_populates="libros")
    editorial: Mapped["Editorial"] = relationship(back_populates="libros")
    autores: Mapped[list["Autor"]] = relationship(
        secondary="libro_autor", back_populates="libros"
    )
    ejemplares: Mapped[list["Ejemplar"]] = relationship(
        back_populates="libro", passive_deletes="all"
    )


# libro_autor: tabla puramente asociativa (N:M), sin clase propia.
libro_autor = Table(
    "libro_autor",
    Base.metadata,
    Column("id_libro", Integer, ForeignKey("libro.id"), primary_key=True),
    Column("id_autor", Integer, ForeignKey("autor.id"), primary_key=True),
)


class Ejemplar(Base):
    __tablename__ = "ejemplar"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_libro: Mapped[int] = mapped_column(ForeignKey("libro.id"))
    codigo_inventario: Mapped[str] = mapped_column(unique=True)
    estado: Mapped[str]
    fecha_alta: Mapped[date]

    libro: Mapped["Libro"] = relationship(back_populates="ejemplares")
    prestamos: Mapped[list["Prestamo"]] = relationship(
        back_populates="ejemplar", passive_deletes="all"
    )


# ---------- Préstamos ----------

class Prestamo(Base):
    __tablename__ = "prestamos"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_socio: Mapped[int] = mapped_column(ForeignKey("socio.id"))
    id_ejemplar: Mapped[int] = mapped_column(ForeignKey("ejemplar.id"))
    fecha_prestamo: Mapped[date]
    fecha_vencimiento: Mapped[date]
    fecha_devolucion: Mapped[date | None]

    socio: Mapped["Socio"] = relationship(back_populates="prestamos")
    ejemplar: Mapped["Ejemplar"] = relationship(back_populates="prestamos")
