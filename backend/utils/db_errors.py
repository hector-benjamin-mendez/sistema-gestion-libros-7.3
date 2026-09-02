"""Excepciones propias de la capa de acceso a datos.

Traducen los errores crudos de MySQL/SQLAlchemy a algo que la capa
de arriba pueda entender sin conocer codigos de error de MySQL.
"""

from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class ErrorDeDatos(Exception):
    """Base de todos los errores de esta capa."""


class RegistroNoEncontrado(ErrorDeDatos):
    """Se pidio un registro por id y no existe."""


class RegistroDuplicado(ErrorDeDatos):
    """Choca contra una restriccion UNIQUE (dni, email, isbn, codigo)."""


class ViolacionDeIntegridad(ErrorDeDatos):
    """Rompe una clave foranea: referencia inexistente o borrado bloqueado."""


# Codigos de error de MySQL
_DUPLICADO = 1062
_FK_ROTA = (1451, 1452)
_COLUMNA_NULA = 1048


@contextmanager
def traducir_errores():
    """Envuelve operaciones de escritura y convierte errores de MySQL."""
    try:
        yield
    except IntegrityError as exc:
        codigo = exc.orig.args[0] if exc.orig and exc.orig.args else None
        if codigo == _DUPLICADO:
            raise RegistroDuplicado(
                "Ya existe un registro con ese valor unico."
            ) from exc
        if codigo in _FK_ROTA:
            raise ViolacionDeIntegridad(
                "La operacion rompe una relacion entre tablas."
            ) from exc
        if codigo == _COLUMNA_NULA:
            raise ViolacionDeIntegridad(
                "Falta un dato obligatorio (columna NOT NULL)."
            ) from exc
        raise ErrorDeDatos("Error de integridad en la base de datos.") from exc
    except SQLAlchemyError as exc:
        raise ErrorDeDatos("Error inesperado en la base de datos.") from exc
