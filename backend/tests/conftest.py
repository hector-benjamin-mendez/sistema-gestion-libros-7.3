"""Fixtures compartidas por todos los tests de la capa de datos."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from config.settings import TEST_DATABASE_URL
from models import (
    Genero, Subgenero, GrupoEditorial, Editorial,
    Autor, Libro, Ejemplar, Rango, Socio,
)


@pytest.fixture(scope="session")
def engine():
    """Un solo engine para toda la corrida, apuntando a biblioteca_test."""
    motor = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield motor
    motor.dispose()


@pytest.fixture
def session(engine):
    """Sesion aislada por test.

    Cada test corre dentro de una transaccion que se deshace al terminar,
    asi ningun test ve los datos de otro y la base queda siempre limpia.
    """
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
def catalogo(session):
    """Datos minimos para poder crear libros, socios y prestamos."""
    genero = Genero(nombre="Ficcion")
    subgenero = Subgenero(nombre="Ciencia Ficcion", genero=genero)
    grupo = GrupoEditorial(nombre="Grupo Planeta")
    editorial = Editorial(nombre="Minotauro", grupo_editorial=grupo)
    autor = Autor(nombre="Frank", apellido="Herbert",
                  fecha_nacimiento=date(1920, 10, 8), nacionalidad="Estadounidense")
    rango = Rango(nombre="Estandar", max_prestamos=3, dias_prestamo=14)

    session.add_all([subgenero, editorial, autor, rango])
    session.flush()

    return {
        "genero": genero, "subgenero": subgenero, "grupo": grupo,
        "editorial": editorial, "autor": autor, "rango": rango,
    }


@pytest.fixture
def libro(session, catalogo):
    ejemplar_libro = Libro(
        titulo="Dune", isbn="9788445000472",
        id_subgenero=catalogo["subgenero"].id,
        id_editorial=catalogo["editorial"].id,
        fecha_publicacion=date(1965, 8, 1),
        idioma="Espanol", numero_edicion="1",
    )
    ejemplar_libro.autores.append(catalogo["autor"])
    session.add(ejemplar_libro)
    session.flush()
    return ejemplar_libro


@pytest.fixture
def socio(session, catalogo):
    nuevo = Socio(
        nombre="Lucia", apellido="Gimenez", dni="38111222",
        email="lucia@test.com", id_rango=catalogo["rango"].id,
        fecha_alta=date(2023, 2, 14),
    )
    session.add(nuevo)
    session.flush()
    return nuevo


@pytest.fixture
def ejemplar(session, libro):
    nuevo = Ejemplar(
        id_libro=libro.id, codigo_inventario="INV-0001",
        estado="disponible", fecha_alta=date(2024, 3, 10),
    )
    session.add(nuevo)
    session.flush()
    return nuevo
