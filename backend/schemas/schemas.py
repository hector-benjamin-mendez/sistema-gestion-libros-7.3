"""
Esquemas Pydantic (contrato de la API).

REGLA: si la columna es NOT NULL en schema.sql, el campo es obligatorio aca.
Si no, el error se escapa hasta MySQL y vuelve como 500 en vez de 422.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Validacion simple de email sin dependencias extra (no usamos EmailStr
# para no agregar email-validator a requirements.txt).
_PATRON_EMAIL = r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$"


# ---------------------------------------------------------------- CATALOGOS

class ItemCatalogo(BaseModel):
    """Par id/nombre para poblar los <select> del frontend."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


# ------------------------------------------------------------------- LIBROS

class AutorMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    apellido: str


class LibroCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    isbn: Optional[str] = Field(default=None, max_length=20)
    id_subgenero: int = Field(gt=0)
    id_editorial: int = Field(gt=0)
    fecha_publicacion: date                       # NOT NULL en la base
    idioma: str = Field(default="Espanol", max_length=50)
    numero_edicion: str = Field(default="1", max_length=20)
    autores_ids: List[int] = []

    @field_validator("isbn")
    @classmethod
    def isbn_sin_guiones(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        limpio = v.replace("-", "").replace(" ", "").strip()
        return limpio or None

    @field_validator("fecha_publicacion")
    @classmethod
    def no_futura(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("La fecha de publicacion no puede ser futura.")
        return v


class LibroUpdate(BaseModel):
    """Todos opcionales: se actualiza solo lo que viene."""
    titulo: Optional[str] = Field(default=None, min_length=1, max_length=255)
    isbn: Optional[str] = Field(default=None, max_length=20)
    id_subgenero: Optional[int] = Field(default=None, gt=0)
    id_editorial: Optional[int] = Field(default=None, gt=0)
    fecha_publicacion: Optional[date] = None
    idioma: Optional[str] = Field(default=None, max_length=50)
    numero_edicion: Optional[str] = Field(default=None, max_length=20)
    autores_ids: Optional[List[int]] = None


class LibroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    isbn: Optional[str] = None
    fecha_publicacion: date
    idioma: str
    numero_edicion: str
    id_editorial: int
    id_subgenero: int
    editorial: Optional[ItemCatalogo] = None
    subgenero: Optional[ItemCatalogo] = None
    autores: List[AutorMini] = []


# ------------------------------------------------------------------- SOCIOS

class SocioCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    dni: str = Field(pattern=r"^\d{7,9}$")
    email: str = Field(pattern=_PATRON_EMAIL, max_length=150)   # NOT NULL
    telefono: Optional[str] = Field(default=None, max_length=30)
    id_rango: int = Field(gt=0)                                 # sin default magico

    @field_validator("dni")
    @classmethod
    def dni_sin_puntos(cls, v: str) -> str:
        return v.replace(".", "").strip()


class SocioUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(default=None, min_length=1, max_length=100)
    dni: Optional[str] = Field(default=None, pattern=r"^\d{7,9}$")
    email: Optional[str] = Field(default=None, pattern=_PATRON_EMAIL, max_length=150)
    telefono: Optional[str] = Field(default=None, max_length=30)
    id_rango: Optional[int] = Field(default=None, gt=0)


class SocioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    apellido: str
    dni: str
    email: str
    telefono: Optional[str] = None
    id_rango: int
    fecha_alta: date
    fecha_baja: Optional[date] = None


# --------------------------------------------------------------- EJEMPLARES

class EjemplarCreate(BaseModel):
    id_libro: int = Field(gt=0)
    codigo_inventario: str = Field(min_length=1, max_length=30)
    estado: str = Field(default="disponible")


class EjemplarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_libro: int
    codigo_inventario: str
    estado: str
    fecha_alta: date


class EjemplarConLibro(EjemplarOut):
    """Ejemplar con el titulo resuelto, para no obligar al front a otro fetch."""
    titulo_libro: Optional[str] = None


# ---------------------------------------------------------------- PRESTAMOS

class PrestamoCreate(BaseModel):
    """Ojo: se presta un EJEMPLAR (una copia fisica), no un libro."""
    id_socio: int = Field(gt=0)
    id_ejemplar: int = Field(gt=0)


class PrestamoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_socio: int
    id_ejemplar: int
    fecha_prestamo: date
    fecha_vencimiento: date
    fecha_devolucion: Optional[date] = None

    # Campos denormalizados SOLO para la respuesta (no se guardan en la base).
    # Los arma la ruta a partir de las relaciones ya cargadas con eager loading.
    socio_nombre: Optional[str] = None
    libro_titulo: Optional[str] = None
    codigo_inventario: Optional[str] = None
    devuelto: bool = False
    vencido: bool = False
    dias_atraso: int = 0


# ------------------------------------------------------------- ESTADISTICAS

class Estadisticas(BaseModel):
    """La consigna marca 'No existen estadisticas de prestamos' como problema."""
    total_libros: int
    total_ejemplares: int
    ejemplares_disponibles: int
    total_socios_activos: int
    prestamos_activos: int
    prestamos_vencidos: int
