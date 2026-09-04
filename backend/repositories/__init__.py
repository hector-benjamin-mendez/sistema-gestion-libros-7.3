"""Repositorios: una función por operación, la sesión siempre primero.

El orden de los imports NO es alfabético a propósito: primero los que no
dependen de nadie y después los que sí. `titulo_repository` usa
`autor_repository` y `genero_repository`; `libro_repository` usa
`titulo_repository`, `editorial_repository`, `idioma_repository` y
`estado_repository`. Importándolos en este orden, cada módulo encuentra
resueltas sus dependencias y no hay import circular.
"""

from repositories import (
    genero_repository,
    idioma_repository,
    estado_repository,
    grupo_editorial_repository,
    editorial_repository,
    autor_repository,
    rango_repository,
    socio_repository,
    titulo_repository,
    libro_repository,
    prestamo_repository,
)

__all__ = [
    "genero_repository",
    "idioma_repository",
    "estado_repository",
    "grupo_editorial_repository",
    "editorial_repository",
    "autor_repository",
    "rango_repository",
    "socio_repository",
    "titulo_repository",
    "libro_repository",
    "prestamo_repository",
]
