"""
Traduce las excepciones de la capa de datos a codigos HTTP.

Cambios respecto de la version anterior:
  - se agrega el handler de RequestValidationError para que los errores de
    Pydantic lleguen al usuario como una frase en castellano y no como un
    JSON anidado que el frontend terminaba mostrando con JSON.stringify.
  - se agrega una red de contencion para cualquier excepcion no prevista:
    devuelve 500 con un cuerpo JSON en vez de un texto plano que el fetch
    no puede parsear (y que hacia fallar el .json() del frontend).
"""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from utils.db_errors import (
    ErrorDeDatos,
    RegistroDuplicado,
    RegistroNoEncontrado,
    ViolacionDeIntegridad,
)

log = logging.getLogger("biblioteca")

_CAMPOS = {
    "titulo": "titulo", "isbn": "ISBN", "dni": "DNI", "email": "email",
    "id_subgenero": "subgenero", "id_editorial": "editorial",
    "id_rango": "rango", "id_socio": "socio", "id_ejemplar": "ejemplar",
    "fecha_publicacion": "fecha de publicacion",
    "numero_edicion": "numero de edicion",
    "codigo_inventario": "codigo de inventario",
}


def register_exception_handlers(app):

    @app.exception_handler(RegistroNoEncontrado)
    def no_encontrado(request: Request, exc: RegistroNoEncontrado):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(RegistroDuplicado)
    def duplicado(request: Request, exc: RegistroDuplicado):
        return JSONResponse(
            status_code=409,
            content={"detail": "Ya existe un registro con ese dato unico "
                               "(ISBN, DNI, email o codigo de inventario)."},
        )

    @app.exception_handler(ViolacionDeIntegridad)
    def integridad(request: Request, exc: ViolacionDeIntegridad):
        return JSONResponse(
            status_code=409,
            content={"detail": "La operacion rompe una relacion entre tablas. "
                               "Puede que el registro este siendo usado por otro "
                               "(por ejemplo, un libro que todavia tiene ejemplares)."},
        )

    @app.exception_handler(ErrorDeDatos)
    def error_datos(request: Request, exc: ErrorDeDatos):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    def valor_invalido(request: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    def validacion(request: Request, exc: RequestValidationError):
        """Convierte el JSON anidado de Pydantic en una frase legible."""
        partes = []
        for error in exc.errors():
            ubicacion = [str(x) for x in error.get("loc", []) if x not in ("body", "query")]
            campo = ubicacion[-1] if ubicacion else "dato"
            partes.append(f"{_CAMPOS.get(campo, campo)}: {error.get('msg', 'valor invalido')}")
        return JSONResponse(
            status_code=422,
            content={"detail": "Datos invalidos. " + " | ".join(partes)},
        )

    @app.exception_handler(Exception)
    def error_inesperado(request: Request, exc: Exception):
        """Red de contencion: siempre JSON, nunca texto plano."""
        log.exception("Error no controlado en %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor. Revisar la consola de uvicorn."},
        )
