"""CRUD y búsquedas de los repositorios principales."""

from datetime import date

import pytest

from repositories import (
    estado_repository,
    libro_repository,
    socio_repository,
    titulo_repository,
)
from utils.db_errors import RegistroDuplicado, RegistroNoEncontrado, ViolacionDeIntegridad


# ---------- Títulos ----------

def test_crear_titulo_le_asigna_id_y_autores(session, catalogo):
    creado = titulo_repository.crear(
        session, nombre="El resplandor",
        id_genero=catalogo["genero"].id,
        autores_ids=[catalogo["autor"].id],
    )
    assert creado.id is not None
    assert [autor.apellido for autor in creado.autores] == ["King"]


def test_buscar_titulo_por_texto_parcial(session, titulo):
    resultados = titulo_repository.listar(session, texto="I")
    assert titulo.nombre in [fila.nombre for fila in resultados]


def test_no_se_puede_repetir_el_nombre_del_titulo(session, titulo, catalogo):
    """El UNIQUE es lo que hace confiable la carga por texto."""
    with pytest.raises(RegistroDuplicado):
        titulo_repository.crear(session, nombre="IT", id_genero=catalogo["genero"].id)


def test_listar_con_stock_cuenta_copias_y_disponibles(session, titulo, copia, catalogo):
    libro_repository.crear(
        session, id_titulo=titulo.id,
        id_editorial=catalogo["editorial"].id,
        id_idioma=catalogo["idioma"].id,
        id_estado=catalogo["estados"]["dañado"].id,
    )
    fila = next(f for f in titulo_repository.listar_con_stock(session)
                if f["titulo"].id == titulo.id)

    assert fila["copias"] == 2          # dos objetos de papel
    assert fila["disponibles"] == 1     # uno solo se puede prestar


def test_listar_con_stock_muestra_titulos_sin_copias(session, catalogo):
    """Un título recién cargado, sin copias todavía, no puede desaparecer
    del catálogo (es un LEFT JOIN, no un INNER)."""
    titulo_repository.crear(session, nombre="Sin copias",
                            id_genero=catalogo["genero"].id)
    fila = next(f for f in titulo_repository.listar_con_stock(session)
                if f["titulo"].nombre == "Sin copias")
    assert fila["copias"] == 0
    assert fila["disponibles"] == 0


def test_no_se_puede_borrar_un_titulo_con_copias(session, titulo, copia):
    with pytest.raises(ViolacionDeIntegridad):
        titulo_repository.eliminar(session, titulo.id)


# ---------- Copias físicas ----------

def test_el_codigo_de_inventario_se_genera_solo(session, titulo, catalogo):
    creada = libro_repository.crear(
        session, id_titulo=titulo.id,
        id_editorial=catalogo["editorial"].id,
        id_idioma=catalogo["idioma"].id,
    )
    assert creada.codigo_inventario == f"INV-{creada.id:06d}"


def test_la_copia_nueva_entra_disponible(session, titulo, catalogo):
    creada = libro_repository.crear(
        session, id_titulo=titulo.id,
        id_editorial=catalogo["editorial"].id,
        id_idioma=catalogo["idioma"].id,
    )
    assert creada.estado.nombre == estado_repository.DISPONIBLE


def test_no_se_puede_repetir_el_codigo_de_inventario(session, titulo, copia, catalogo):
    with pytest.raises(RegistroDuplicado):
        libro_repository.crear(
            session, id_titulo=titulo.id,
            id_editorial=catalogo["editorial"].id,
            id_idioma=catalogo["idioma"].id,
            codigo_inventario=copia.codigo_inventario,
        )


def test_disponibles_de_titulo_excluye_las_no_prestables(session, titulo, copia, catalogo):
    segunda = libro_repository.crear(
        session, id_titulo=titulo.id,
        id_editorial=catalogo["editorial"].id,
        id_idioma=catalogo["idioma"].id,
    )
    libro_repository.cambiar_estado(session, copia.id, nombre_estado="en_reparacion")

    disponibles = libro_repository.disponibles_de_titulo(session, titulo.id)
    assert [c.id for c in disponibles] == [segunda.id]


def test_cambiar_estado_a_uno_inexistente_falla(session, copia):
    with pytest.raises(RegistroNoEncontrado):
        libro_repository.cambiar_estado(session, copia.id,
                                        nombre_estado="hecho_pomada")


def test_buscar_copia_por_codigo_de_inventario(session, copia):
    encontrada = libro_repository.obtener_por_codigo(session, "  INV-000001 ")
    assert encontrada is not None and encontrada.id == copia.id


def test_listar_copias_escribiendo_el_titulo(session, copia):
    """Se busca por texto, no por id (correcciones 4 y 5)."""
    resultados = libro_repository.listar(session, texto_titulo="it")
    assert copia.id in [fila.id for fila in resultados]


def test_resumen_de_inventario(session, titulo, copia, catalogo):
    libro_repository.crear(
        session, id_titulo=titulo.id,
        id_editorial=catalogo["editorial"].id,
        id_idioma=catalogo["idioma"].id,
        id_estado=catalogo["estados"]["dañado"].id,
    )
    resumen = libro_repository.resumen_inventario(session)
    assert resumen["copias"] == 2
    assert resumen["disponibles"] == 1
    assert resumen["fuera_de_circulacion"] == 1


def test_actualizar_campo_inexistente_falla(session, copia):
    with pytest.raises(ValueError):
        libro_repository.actualizar(session, copia.id, campo_inventado="x")


# ---------- Socios ----------

def test_buscar_socio_por_apellido(session, socio):
    assert socio_repository.listar(session, texto="Peral")[0].id == socio.id


def test_buscar_socio_por_dni(session, socio):
    assert socio_repository.listar(session, texto="42444")[0].id == socio.id


def test_baja_logica_conserva_el_socio(session, socio):
    socio_repository.dar_de_baja(session, socio.id, date(2026, 1, 31))
    assert socio_repository.obtener_o_error(session, socio.id).fecha_baja is not None
    assert socio_repository.listar(session, solo_activos=True) == []


def test_pedir_un_id_inexistente_levanta_no_encontrado(session):
    with pytest.raises(RegistroNoEncontrado):
        titulo_repository.obtener_o_error(session, 999999)
