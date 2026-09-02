"""Los modelos mapean bien y las relaciones navegan en ambas direcciones."""

from sqlalchemy import text


def test_la_conexion_ve_las_once_tablas(session):
    tablas = session.execute(text("SHOW TABLES")).scalars().all()
    assert len(tablas) == 11


def test_libro_navega_hacia_subgenero_y_genero(libro):
    assert libro.subgenero.nombre == "Ciencia Ficcion"
    assert libro.subgenero.genero.nombre == "Ficcion"


def test_libro_navega_hacia_editorial_y_grupo(libro):
    assert libro.editorial.nombre == "Minotauro"
    assert libro.editorial.grupo_editorial.nombre == "Grupo Planeta"


def test_relacion_n_a_m_funciona_en_las_dos_puntas(libro, catalogo):
    assert catalogo["autor"] in libro.autores
    assert libro in catalogo["autor"].libros


def test_socio_navega_hacia_su_rango(socio):
    assert socio.rango.max_prestamos == 3
    assert socio.rango.dias_prestamo == 14


def test_los_campos_opcionales_aceptan_null(socio, catalogo):
    assert socio.telefono is None
    assert socio.fecha_baja is None
    assert catalogo["autor"].fecha_fallecimiento is None
