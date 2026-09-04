"""Los modelos mapean bien y las relaciones navegan en las dos puntas."""

from datetime import date, timedelta

from sqlalchemy import text

from models import Libro


def test_la_conexion_ve_las_doce_tablas(session):
    tablas = session.execute(text("SHOW TABLES")).scalars().all()
    assert len(tablas) == 12


def test_la_copia_navega_hasta_el_titulo_y_el_genero(copia):
    # Es la cadena que creó la corrección 1: copia -> obra -> género.
    assert copia.titulo.nombre == "IT"
    assert copia.titulo.genero.nombre == "Terror"


def test_la_copia_navega_hasta_editorial_idioma_y_estado(copia):
    assert copia.editorial.nombre == "Plaza & Janés"
    assert copia.editorial.grupo_editorial.nombre == "Penguin Random House"
    assert copia.idioma.nombre == "Español"
    assert copia.estado.nombre == "disponible"


def test_la_autoria_es_del_titulo_no_de_la_copia(titulo, catalogo):
    assert catalogo["autor"] in titulo.autores
    assert titulo in catalogo["autor"].titulos


def test_varias_copias_del_mismo_titulo_comparten_isbn(session, titulo, copia, catalogo):
    """Lo que el UNIQUE del modelo anterior hacía imposible."""
    segunda = Libro(
        id_titulo=titulo.id,
        id_editorial=catalogo["editorial"].id,
        id_idioma=catalogo["idioma"].id,
        id_estado=catalogo["estados"]["disponible"].id,
        isbn=copia.isbn,                 # el MISMO ISBN
        edicion=copia.edicion,
        codigo_inventario="INV-000002",
        fecha_alta=date.today(),
    )
    session.add(segunda)
    session.flush()

    assert len(titulo.libros) == 2
    assert segunda.isbn == copia.isbn


def test_la_propiedad_disponible_sale_de_la_tabla_estado(copia, catalogo):
    assert copia.disponible is True
    copia.id_estado = catalogo["estados"]["dañado"].id
    copia.estado = catalogo["estados"]["dañado"]
    assert copia.disponible is False


def test_copias_disponibles_del_titulo_cuenta_solo_las_prestables(titulo, copia, catalogo):
    assert titulo.copias_disponibles == 1
    copia.estado = catalogo["estados"]["en_reparacion"]
    assert titulo.copias_disponibles == 0


def test_socio_navega_hasta_su_rango(socio):
    assert socio.rango.max_prestamos == 3
    assert socio.rango.dias_prestamo == 14


def test_la_suspension_vence_sola(socio):
    """No hace falta un proceso que limpie suspensiones vencidas."""
    socio.suspendido_hasta = date.today() + timedelta(days=10)
    assert socio.esta_suspendido() is True
    assert socio.puede_pedir_prestado() is False

    socio.suspendido_hasta = date.today() - timedelta(days=1)
    assert socio.esta_suspendido() is False
    assert socio.puede_pedir_prestado() is True


def test_baja_y_suspension_son_cosas_distintas(socio):
    socio.suspendido_hasta = date.today() + timedelta(days=5)
    assert socio.activo is True          # sigue en el padrón
    assert socio.puede_pedir_prestado() is False


def test_los_campos_opcionales_aceptan_null(socio, catalogo):
    assert socio.telefono is None
    assert socio.fecha_baja is None
    assert socio.suspendido_hasta is None
    assert catalogo["autor"].fecha_fallecimiento is None
