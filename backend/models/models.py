"""
Modelos ORM del Sistema de Gestión Bibliotecaria.

Mapean 1 a 1 las tablas de database/schema.sql.

Cambios de esta versión (correcciones del profesor):
  · Nace `Titulo`  (la obra)          -> corrección 1
  · `Libro` pasa a ser la COPIA FÍSICA -> correcciones 2 y 3
  · Muere `Ejemplar` (era lo mismo que el nuevo `Libro`)
  · Muere `Subgenero` (el género ahora cuelga del título)
  · Nacen `Idioma` y `Estado` como tablas -> corrección 2 (IdIdioma / IdEstado)
  · `libro_autor` pasa a ser `titulo_autor` (la autoría es de la obra)
"""

from datetime import date

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


# ============================================================
# Catálogo
# ============================================================

class Genero(Base):
    __tablename__ = "genero"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)

    titulos: Mapped[list["Titulo"]] = relationship(
        back_populates="genero", passive_deletes="all"
    )

    def __repr__(self) -> str:
        return f"<Genero {self.nombre}>"


class Idioma(Base):
    __tablename__ = "idioma"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)

    libros: Mapped[list["Libro"]] = relationship(
        back_populates="idioma", passive_deletes="all"
    )

    def __repr__(self) -> str:
        return f"<Idioma {self.nombre}>"


class Estado(Base):
    """Estado de una copia física: disponible, prestado, dañado, etc.

    `permite_prestamo` evita tener la regla escrita en el código: para
    saber si una copia se puede prestar se mira la fila, no una lista
    hardcodeada en Python.
    """

    __tablename__ = "estado"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True)
    permite_prestamo: Mapped[bool] = mapped_column(Boolean, default=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))

    # Copias que están hoy en este estado.
    libros: Mapped[list["Libro"]] = relationship(
        back_populates="estado",
        foreign_keys="Libro.id_estado",
        passive_deletes="all",
    )
    # Devoluciones que se registraron con este estado (historial).
    devoluciones: Mapped[list["Prestamo"]] = relationship(
        back_populates="estado_devolucion",
        foreign_keys="Prestamo.id_estado_devolucion",
        passive_deletes="all",
    )

    def __repr__(self) -> str:
        return f"<Estado {self.nombre}>"


class GrupoEditorial(Base):
    __tablename__ = "grupo_editorial"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)

    editoriales: Mapped[list["Editorial"]] = relationship(
        back_populates="grupo_editorial", passive_deletes="all"
    )

    def __repr__(self) -> str:
        return f"<GrupoEditorial {self.nombre}>"


class Editorial(Base):
    __tablename__ = "editorial"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    direccion: Mapped[str | None] = mapped_column(String(255))
    fecha_fundacion: Mapped[date | None]
    # Admite NULL: el alta por texto crea la editorial sin obligar a
    # saber el grupo editorial (corrección 5).
    id_grupo_editorial: Mapped[int | None] = mapped_column(
        ForeignKey("grupo_editorial.id")
    )

    grupo_editorial: Mapped["GrupoEditorial | None"] = relationship(
        back_populates="editoriales"
    )
    libros: Mapped[list["Libro"]] = relationship(
        back_populates="editorial", passive_deletes="all"
    )

    def __repr__(self) -> str:
        return f"<Editorial {self.nombre}>"


class Autor(Base):
    __tablename__ = "autor"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Cadena vacía en vez de NULL: es parte de la clave única
    # (apellido, nombre) y en MySQL los NULL no colisionan.
    nombre: Mapped[str] = mapped_column(String(100), default="")
    apellido: Mapped[str] = mapped_column(String(100))
    fecha_nacimiento: Mapped[date | None]
    fecha_fallecimiento: Mapped[date | None]
    nacionalidad: Mapped[str | None] = mapped_column(String(60))

    titulos: Mapped[list["Titulo"]] = relationship(
        secondary="titulo_autor", back_populates="autores"
    )

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()

    def __repr__(self) -> str:
        return f"<Autor {self.nombre_completo}>"


class Rango(Base):
    __tablename__ = "rango"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    max_prestamos: Mapped[int]
    dias_prestamo: Mapped[int]

    socios: Mapped[list["Socio"]] = relationship(
        back_populates="rango", passive_deletes="all"
    )

    def __repr__(self) -> str:
        return f"<Rango {self.nombre}>"


# ============================================================
# Título: la OBRA  (corrección 1)
# ============================================================

class Titulo(Base):
    __tablename__ = "titulo"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True)
    id_genero: Mapped[int] = mapped_column(ForeignKey("genero.id"))

    genero: Mapped["Genero"] = relationship(back_populates="titulos")
    autores: Mapped[list["Autor"]] = relationship(
        secondary="titulo_autor", back_populates="titulos"
    )
    libros: Mapped[list["Libro"]] = relationship(
        back_populates="titulo", passive_deletes="all"
    )

    @property
    def copias_disponibles(self) -> int:
        """Cuántas copias de esta obra se pueden prestar ahora."""
        return sum(1 for libro in self.libros if libro.estado.permite_prestamo)

    def __repr__(self) -> str:
        return f"<Titulo {self.nombre}>"


# Tabla puramente asociativa (N:M), sin clase propia.
# Cuelga de `titulo` y no de `libro`: si hay cinco copias de IT,
# Stephen King no las escribió cinco veces.
titulo_autor = Table(
    "titulo_autor",
    Base.metadata,
    Column("id_titulo", Integer, ForeignKey("titulo.id"), primary_key=True),
    Column("id_autor", Integer, ForeignKey("autor.id"), primary_key=True),
)


# ============================================================
# Libro: la UNIDAD FÍSICA  (correcciones 2 y 3)
# ============================================================

class Libro(Base):
    """Una fila = un objeto de papel que se puede prestar y romper.

    OJO al cambio de significado respecto de la versión anterior: antes
    `Libro` era la ficha bibliográfica y `Ejemplar` la copia. Ahora
    `Libro` ES la copia y la ficha se llama `Titulo`.
    """

    __tablename__ = "libro"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_titulo: Mapped[int] = mapped_column(ForeignKey("titulo.id"))
    id_editorial: Mapped[int] = mapped_column(ForeignKey("editorial.id"))
    # Sin unique: el ISBN identifica a la edición, no a la copia.
    isbn: Mapped[str | None] = mapped_column(String(20))
    id_estado: Mapped[int] = mapped_column(ForeignKey("estado.id"))
    edicion: Mapped[str | None] = mapped_column(String(20))
    id_idioma: Mapped[int] = mapped_column(ForeignKey("idioma.id"))
    codigo_inventario: Mapped[str | None] = mapped_column(String(30), unique=True)
    fecha_alta: Mapped[date]

    titulo: Mapped["Titulo"] = relationship(back_populates="libros")
    editorial: Mapped["Editorial"] = relationship(back_populates="libros")
    idioma: Mapped["Idioma"] = relationship(back_populates="libros")
    estado: Mapped["Estado"] = relationship(
        back_populates="libros", foreign_keys=[id_estado]
    )
    prestamos: Mapped[list["Prestamo"]] = relationship(
        back_populates="libro", passive_deletes="all"
    )

    @property
    def disponible(self) -> bool:
        return self.estado.permite_prestamo

    def __repr__(self) -> str:
        return f"<Libro {self.codigo_inventario or self.id}>"


# ============================================================
# Socios y préstamos
# ============================================================

class Socio(Base):
    __tablename__ = "socio"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    apellido: Mapped[str] = mapped_column(String(100))
    dni: Mapped[str] = mapped_column(String(15), unique=True)
    email: Mapped[str] = mapped_column(String(150), unique=True)
    telefono: Mapped[str | None] = mapped_column(String(30))
    id_rango: Mapped[int] = mapped_column(ForeignKey("rango.id"))
    fecha_alta: Mapped[date]
    fecha_baja: Mapped[date | None]
    # Sanción temporal (ejemplo de la corrección 3). Distinto de la baja.
    suspendido_hasta: Mapped[date | None]

    rango: Mapped["Rango"] = relationship(back_populates="socios")
    prestamos: Mapped[list["Prestamo"]] = relationship(
        back_populates="socio", passive_deletes="all"
    )

    @property
    def activo(self) -> bool:
        return self.fecha_baja is None

    def esta_suspendido(self, al_dia: date | None = None) -> bool:
        """La suspensión vence sola: no hace falta ir a limpiarla."""
        if self.suspendido_hasta is None:
            return False
        return self.suspendido_hasta >= (al_dia or date.today())

    def puede_pedir_prestado(self, al_dia: date | None = None) -> bool:
        return self.activo and not self.esta_suspendido(al_dia)

    def __repr__(self) -> str:
        return f"<Socio {self.apellido}, {self.nombre}>"


class Prestamo(Base):
    __tablename__ = "prestamos"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_socio: Mapped[int] = mapped_column(ForeignKey("socio.id"))
    # Apunta a la COPIA, no al título: es el corazón de la corrección 3.
    id_libro: Mapped[int] = mapped_column(ForeignKey("libro.id"))
    fecha_prestamo: Mapped[date]
    fecha_vencimiento: Mapped[date]
    fecha_devolucion: Mapped[date | None]
    # En qué estado volvió la copia. Sin esto, "está rota" no dice
    # quién la rompió.
    id_estado_devolucion: Mapped[int | None] = mapped_column(ForeignKey("estado.id"))
    observaciones: Mapped[str | None] = mapped_column(String(255))

    # OJO: la tabla tiene una columna más, `libro_en_curso`, que a
    # propósito NO se mapea acá. La mantienen dos triggers (ver
    # schema.sql) y su único trabajo es sostener el índice UNIQUE que
    # impide dos préstamos activos de la misma copia. Si estuviera
    # mapeada, SQLAlchemy la escribiría en cada INSERT y el valor de
    # Python se pisaría con el del trigger: ruido para nada.

    socio: Mapped["Socio"] = relationship(back_populates="prestamos")
    libro: Mapped["Libro"] = relationship(back_populates="prestamos")
    estado_devolucion: Mapped["Estado | None"] = relationship(
        back_populates="devoluciones", foreign_keys=[id_estado_devolucion]
    )

    @property
    def activo(self) -> bool:
        return self.fecha_devolucion is None

    def esta_vencido(self, al_dia: date | None = None) -> bool:
        return self.activo and self.fecha_vencimiento < (al_dia or date.today())

    def __repr__(self) -> str:
        estado = "activo" if self.activo else "devuelto"
        return f"<Prestamo {self.id} ({estado})>"
