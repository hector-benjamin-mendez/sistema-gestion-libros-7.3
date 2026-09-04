"""Ciclo de préstamo/devolución y traducción de errores de MySQL.

El archivo entero gira alrededor de la corrección 3: el control de cada
unidad física, incluido el ejemplo textual del profesor (se presta una
copia de IT, vuelve rota, el sistema lo registra y permite suspender).
"""

from datetime import date, timedelta

import pytest

from repositories import (
    libro_repository,
    prestamo_repository,
    socio_repository,
    titulo_repository,
)
from utils.db_errors import (
    RegistroDuplicado,
    ReglaDeDatos,
    ViolacionDeIntegridad,
)


# ---------- Ciclo normal ----------

def test_prestar_marca_la_copia_como_prestada(session, socio, copia):
    prestamo = prestamo_repository.prestar(session, id_socio=socio.id,
                                           id_libro=copia.id)
    assert prestamo.activo is True
    assert copia.estado.nombre == "prestado"
    assert copia.disponible is False


def test_el_vencimiento_sale_del_rango_del_socio(session, socio, copia):
    hoy = date.today()
    prestamo = prestamo_repository.prestar(
        session, id_socio=socio.id, id_libro=copia.id, fecha_prestamo=hoy
    )
    assert prestamo.fecha_vencimiento == hoy + timedelta(days=14)


def test_la_devolucion_en_buen_estado_libera_la_copia(session, socio, copia):
    prestamo = prestamo_repository.prestar(session, id_socio=socio.id,
                                           id_libro=copia.id)
    prestamo_repository.registrar_devolucion(session, prestamo.id)

    assert prestamo.activo is False
    assert copia.estado.nombre == "disponible"
    assert prestamo_repository.contar_activos_de_socio(session, socio.id) == 0


def test_no_se_puede_devolver_dos_veces(session, socio, copia):
    prestamo = prestamo_repository.prestar(session, id_socio=socio.id,
                                           id_libro=copia.id)
    prestamo_repository.registrar_devolucion(session, prestamo.id)
    with pytest.raises(ReglaDeDatos):
        prestamo_repository.registrar_devolucion(session, prestamo.id)


def test_no_se_puede_prestar_una_copia_que_no_esta_disponible(session, socio, copia):
    libro_repository.cambiar_estado(session, copia.id, nombre_estado="en_reparacion")
    with pytest.raises(ReglaDeDatos):
        prestamo_repository.prestar(session, id_socio=socio.id, id_libro=copia.id)


def test_la_base_impide_dos_prestamos_activos_de_la_misma_copia(session, socio, copia):
    """No depende de que el código se acuerde de chequearlo: lo garantiza
    el índice UNIQUE sobre la columna generada `libro_en_curso`."""
    hoy = date.today()
    prestamo_repository.crear(session, id_socio=socio.id, id_libro=copia.id,
                              fecha_prestamo=hoy,
                              fecha_vencimiento=hoy + timedelta(days=14))
    with pytest.raises(RegistroDuplicado):
        prestamo_repository.crear(session, id_socio=socio.id, id_libro=copia.id,
                                  fecha_prestamo=hoy,
                                  fecha_vencimiento=hoy + timedelta(days=14))


def test_la_misma_copia_se_puede_volver_a_prestar_despues_de_devuelta(
    session, socio, copia
):
    primero = prestamo_repository.prestar(session, id_socio=socio.id,
                                          id_libro=copia.id)
    prestamo_repository.registrar_devolucion(session, primero.id)
    segundo = prestamo_repository.prestar(session, id_socio=socio.id,
                                          id_libro=copia.id)
    assert segundo.id != primero.id


# ---------- El ejemplo de la corrección 3 ----------

def test_el_caso_de_augusto_de_punta_a_punta(session, socio, copia):
    """"Le prestás a Augusto el día 23 una copia del libro IT y el 26 te
    lo devuelve roto, en el sistema esto figura y podés tomar la decisión
    de suspenderlo."""

    prestamo = prestamo_repository.prestar(
        session, id_socio=socio.id, id_libro=copia.id,
        fecha_prestamo=date(2026, 8, 23),
    )

    prestamo_repository.registrar_devolucion(
        session, prestamo.id,
        fecha_devolucion=date(2026, 8, 26),
        nombre_estado="dañado",
        observaciones="Volvió con la tapa arrancada.",
    )

    # 1. La copia queda fuera de circulación.
    assert copia.estado.nombre == "dañado"
    assert copia.disponible is False

    # 2. En el sistema FIGURA de quién y de qué préstamo vino el daño.
    assert prestamo.estado_devolucion.nombre == "dañado"
    assert prestamo.socio.nombre == "Augusto"
    assert prestamo.observaciones == "Volvió con la tapa arrancada."

    # 3. Se puede tomar la decisión de suspenderlo.
    socio_repository.suspender_por_dias(session, socio.id, 30)
    assert socio.puede_pedir_prestado() is False
    assert socio.activo is True          # suspendido, no dado de baja


def test_el_historial_de_la_copia_dice_quien_la_tuvo(session, socio, copia):
    prestamo = prestamo_repository.prestar(session, id_socio=socio.id,
                                           id_libro=copia.id)
    prestamo_repository.registrar_devolucion(session, prestamo.id,
                                             nombre_estado="dañado")

    historial = prestamo_repository.historial_de_copia(session, copia.id)
    assert len(historial) == 1
    assert historial[0].socio.apellido == "Peralta"
    assert historial[0].estado_devolucion.nombre == "dañado"


def test_las_devoluciones_en_mal_estado_son_consultables(session, socio, copia):
    prestamo = prestamo_repository.prestar(session, id_socio=socio.id,
                                           id_libro=copia.id)
    prestamo_repository.registrar_devolucion(session, prestamo.id,
                                             nombre_estado="dañado")

    antecedentes = prestamo_repository.devoluciones_en_mal_estado(
        session, id_socio=socio.id
    )
    assert [p.id for p in antecedentes] == [prestamo.id]


def test_un_socio_suspendido_sigue_apareciendo_en_el_padron(session, socio):
    socio_repository.suspender_por_dias(session, socio.id, 30)
    assert socio.id in [s.id for s in socio_repository.listar(session, solo_activos=True)]
    assert socio.id in [s.id for s in socio_repository.listar(session, solo_suspendidos=True)]


def test_la_segunda_sancion_se_suma_a_la_anterior(session, socio):
    primera = socio_repository.suspender_por_dias(session, socio.id, 10)
    fin_primera = primera.suspendido_hasta
    segunda = socio_repository.suspender_por_dias(session, socio.id, 10)
    assert segunda.suspendido_hasta == fin_primera + timedelta(days=10)


# ---------- Listados ----------

def test_el_prestamo_vencido_aparece_en_el_listado(session, socio, copia):
    prestamo_repository.prestar(session, id_socio=socio.id, id_libro=copia.id,
                                fecha_prestamo=date(2026, 1, 1), dias=14)
    vencidos = prestamo_repository.listar(session, vencidos_al=date(2026, 6, 1))
    assert len(vencidos) == 1


def test_el_historial_del_socio_conserva_los_devueltos(session, socio, copia):
    prestamo = prestamo_repository.prestar(session, id_socio=socio.id,
                                           id_libro=copia.id)
    prestamo_repository.registrar_devolucion(session, prestamo.id)
    assert len(prestamo_repository.listar(session, id_socio=socio.id)) == 1


def test_se_pueden_listar_los_prestamos_de_un_titulo(session, socio, copia, titulo):
    prestamo_repository.prestar(session, id_socio=socio.id, id_libro=copia.id)
    assert len(prestamo_repository.listar(session, id_titulo=titulo.id)) == 1


# ---------- Traducción de errores de MySQL ----------

def test_dni_repetido_levanta_registro_duplicado(session, socio, catalogo):
    with pytest.raises(RegistroDuplicado):
        socio_repository.crear(
            session, nombre="Otro", apellido="Socio", dni=socio.dni,
            email="otro@test.com", id_rango=catalogo["rango"].id,
        )


def test_email_repetido_levanta_registro_duplicado(session, socio, catalogo):
    with pytest.raises(RegistroDuplicado):
        socio_repository.crear(
            session, nombre="Otro", apellido="Socio", dni="99999999",
            email=socio.email, id_rango=catalogo["rango"].id,
        )


def test_referencia_a_un_titulo_inexistente_rompe_integridad(session, catalogo):
    with pytest.raises(ViolacionDeIntegridad):
        libro_repository.crear(
            session, id_titulo=999999,
            id_editorial=catalogo["editorial"].id,
            id_idioma=catalogo["idioma"].id,
        )


def test_borrar_una_copia_con_prestamos_esta_bloqueado(session, socio, copia):
    prestamo_repository.prestar(session, id_socio=socio.id, id_libro=copia.id)
    with pytest.raises(ViolacionDeIntegridad):
        libro_repository.eliminar(session, copia.id)


def test_borrar_un_estado_en_uso_esta_bloqueado(session, copia, catalogo):
    from repositories import estado_repository
    with pytest.raises(ViolacionDeIntegridad):
        estado_repository.eliminar(session, catalogo["estados"]["disponible"].id)
