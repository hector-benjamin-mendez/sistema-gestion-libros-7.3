"""Excepciones propias de la capa de acceso a datos.

Traducen los errores crudos de MySQL/SQLAlchemy a algo que la capa de
arriba pueda entender sin conocer códigos de error de MySQL.
"""

from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class ErrorDeDatos(Exception):
    """Base de todos los errores de esta capa."""


class RegistroNoEncontrado(ErrorDeDatos):
    """Se pidió un registro por id y no existe."""


class RegistroDuplicado(ErrorDeDatos):
    """Choca contra una restricción UNIQUE (dni, email, código, título)."""


class ViolacionDeIntegridad(ErrorDeDatos):
    """Rompe una clave foránea: referencia inexistente o borrado bloqueado."""


class ReglaDeDatos(ErrorDeDatos):
    """Rompe una regla de coherencia de la propia capa de datos.

    Ejemplos: devolver dos veces el mismo préstamo, o prestar una copia
    cuyo estado no habilita el préstamo. No es una regla de negocio de
    Héctor: es coherencia interna de las tablas.
    """


# Códigos de error de MySQL / MariaDB
_DUPLICADO = 1062
_FK_ROTA = (1451, 1452)
_COLUMNA_NULA = 1048
_CHECK_ROTO = (3819, 4025)   # CHECK constraint violado (MySQL 8 / MariaDB)


@contextmanager
def traducir_errores():
    """Envuelve operaciones de escritura y convierte errores de MySQL."""
    try:
        yield
    except IntegrityError as exc:
        codigo = exc.orig.args[0] if exc.orig and exc.orig.args else None
        if codigo == _DUPLICADO:
            raise RegistroDuplicado(
                "Ya existe un registro con ese valor único."
            ) from exc
        if codigo in _FK_ROTA:
            raise ViolacionDeIntegridad(
                "La operación rompe una relación entre tablas."
            ) from exc
        if codigo == _COLUMNA_NULA:
            raise ViolacionDeIntegridad(
                "Falta un dato obligatorio (columna NOT NULL)."
            ) from exc
        if codigo in _CHECK_ROTO:
            raise ReglaDeDatos(
                "Los datos no cumplen una regla de la base "
                "(fechas incoherentes o valor fuera de rango)."
            ) from exc
        raise ErrorDeDatos("Error de integridad en la base de datos.") from exc
    except SQLAlchemyError as exc:
        raise ErrorDeDatos("Error inesperado en la base de datos.") from exc
