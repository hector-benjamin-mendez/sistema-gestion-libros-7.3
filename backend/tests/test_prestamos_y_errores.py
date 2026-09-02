"""Ciclo de prestamo/devolucion y traduccion de errores de MySQL."""

from datetime import date, timedelta

import pytest

from repositories import prestamo_repository, socio_repository, ejemplar_repository
from utils.db_errors import RegistroDuplicado, ViolacionDeIntegridad


def _prestar(session, socio, ejemplar, dias=14):
    prestamo = prestamo_repository.crear(
        session, id_socio=socio.id, id_ejemplar=ejemplar.id,
        fecha_prestamo=date.today(),
        fecha_vencimiento=date.today() + timedelta(days=dias),
    )
    ejemplar_repository.actualizar_estado(session, ejemplar.id, "prestado")
    return prestamo


def test_un_prestamo_nuevo_queda_activo(session, socio, ejemplar):
    _prestar(session, socio, ejemplar)
    assert prestamo_repository.ejemplar_esta_prestado(session, ejemplar.id) is True
    assert prestamo_repository.contar_activos_de_socio(session, socio.id) == 1


def test_la_devolucion_cierra_el_prestamo(session, socio, ejemplar):
    prestamo = _prestar(session, socio, ejemplar)
    prestamo_repository.registrar_devolucion(session, prestamo.id, date.today())
    ejemplar_repository.actualizar_estado(session, ejemplar.id, "disponible")

    assert prestamo_repository.ejemplar_esta_prestado(session, ejemplar.id) is False
    assert prestamo_repository.contar_activos_de_socio(session, socio.id) == 0


def test_no_se_puede_devolver_dos_veces(session, socio, ejemplar):
    prestamo = _prestar(session, socio, ejemplar)
    prestamo_repository.registrar_devolucion(session, prestamo.id, date.today())
    with pytest.raises(ValueError):
        prestamo_repository.registrar_devolucion(session, prestamo.id, date.today())


def test_prestamo_vencido_aparece_en_el_listado(session, socio, ejemplar):
    prestamo_repository.crear(
        session, id_socio=socio.id, id_ejemplar=ejemplar.id,
        fecha_prestamo=date(2026, 1, 1), fecha_vencimiento=date(2026, 1, 15),
    )
    vencidos = prestamo_repository.listar(session, vencidos_al=date(2026, 6, 1))
    assert len(vencidos) == 1


def test_el_historial_del_socio_conserva_los_devueltos(session, socio, ejemplar):
    prestamo = _prestar(session, socio, ejemplar)
    prestamo_repository.registrar_devolucion(session, prestamo.id, date.today())
    assert len(prestamo_repository.listar(session, id_socio=socio.id)) == 1


def test_dni_repetido_levanta_registro_duplicado(session, socio, catalogo):
    with pytest.raises(RegistroDuplicado):
        socio_repository.crear(
            session, nombre="Otro", apellido="Socio", dni=socio.dni,
            email="otro@test.com", id_rango=catalogo["rango"].id,
            fecha_alta=date.today(),
        )


def test_email_repetido_levanta_registro_duplicado(session, socio, catalogo):
    with pytest.raises(RegistroDuplicado):
        socio_repository.crear(
            session, nombre="Otro", apellido="Socio", dni="99999999",
            email=socio.email, id_rango=catalogo["rango"].id,
            fecha_alta=date.today(),
        )


def test_referencia_a_libro_inexistente_rompe_integridad(session):
    with pytest.raises(ViolacionDeIntegridad):
        ejemplar_repository.crear(session, id_libro=999999,
                                  codigo_inventario="INV-FALSO",
                                  fecha_alta=date.today())


def test_borrar_socio_con_prestamos_esta_bloqueado(session, socio, ejemplar):
    _prestar(session, socio, ejemplar)
    with pytest.raises(ViolacionDeIntegridad):
        socio_repository.eliminar(session, socio.id)
