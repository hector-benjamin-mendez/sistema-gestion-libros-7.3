"""Fixtures compartidas por todos los tests de la capa de datos.

Corren contra `biblioteca_test`, nunca contra `biblioteca`. Cada test se
ejecuta dentro de una transacción que se deshace al terminar, así ningún
test ve los datos de otro y la base queda siempre limpia.
"""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from config.settings import TEST_DATABASE_URL
from models import (
    Autor,
    Editorial,
    Estado,
    Genero,
    GrupoEditorial,
    Idioma,
    Libro,
    Rango,
    Socio,
    Titulo,
)


@pytest.fixture(scope="session")
def engine():
    """Un solo engine para toda la corrida, apuntando a biblioteca_test."""
    motor = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield motor
    motor.dispose()


@pytest.fixture
def session(engine):
    conexion = engine.connect()
    transaccion = conexion.begin()
    sesion = Session(
        bind=conexion,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield sesion
    finally:
        sesion.close()
        if transaccion.is_active:
            transaccion.rollback()
        conexion.close()


@pytest.fixture
def estados(session):
    """La tabla `estado` con los valores que usa el sistema.

    Se crean acá y no se leen del seed porque los tests tienen que poder
    correr sobre una base vacía.
    """
    filas = {
        "disponible": Estado(nombre="disponible", permite_prestamo=True),
        "prestado": Estado(nombre="prestado", permite_prestamo=False),
        "en_reparacion": Estado(nombre="en_reparacion", permite_prestamo=False),
        "dañado": Estado(nombre="dañado", permite_prestamo=False),
        "baja": Estado(nombre="baja", permite_prestamo=False),
    }
    session.add_all(filas.values())
    session.flush()
    return filas


@pytest.fixture
def catalogo(session, estados):
    """Datos mínimos para poder cargar títulos, copias, socios y préstamos."""
    genero = Genero(nombre="Terror")
    idioma = Idioma(nombre="Español")
    grupo = GrupoEditorial(nombre="Penguin Random House")
    editorial = Editorial(nombre="Plaza & Janés", grupo_editorial=grupo)
    autor = Autor(nombre="Stephen", apellido="King",
                  fecha_nacimiento=date(1947, 9, 21),
                  nacionalidad="Estadounidense")
    rango = Rango(nombre="Estándar", max_prestamos=3, dias_prestamo=14)

    session.add_all([genero, idioma, editorial, autor, rango])
    session.flush()

    return {
        "genero": genero, "idioma": idioma, "grupo": grupo,
        "editorial": editorial, "autor": autor, "rango": rango,
        "estados": estados,
    }


@pytest.fixture
def titulo(session, catalogo):
    """La obra IT, con su autor."""
    obra = Titulo(nombre="IT", id_genero=catalogo["genero"].id)
    obra.autores.append(catalogo["autor"])
    session.add(obra)
    session.flush()
    return obra


@pytest.fixture
def copia(session, titulo, catalogo):
    """Una copia física de IT, disponible."""
    libro = Libro(
        id_titulo=titulo.id,
        id_editorial=catalogo["editorial"].id,
        id_idioma=catalogo["idioma"].id,
        id_estado=catalogo["estados"]["disponible"].id,
        isbn="9788497596718",
        edicion="2",
        codigo_inventario="INV-000001",
        fecha_alta=date(2023, 4, 18),
    )
    session.add(libro)
    session.flush()
    return libro


@pytest.fixture
def socio(session, catalogo):
    """Augusto, el del ejemplo de la corrección 3."""
    nuevo = Socio(
        nombre="Augusto", apellido="Peralta", dni="42444555",
        email="augusto@test.com", id_rango=catalogo["rango"].id,
        fecha_alta=date(2025, 3, 5),
    )
    session.add(nuevo)
    session.flush()
    return nuevo
