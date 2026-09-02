# Registro de correcciones

Lista de lo que se arregló y dónde, para poder revisar archivo por archivo.
Verificado ejecutando los endpoints, no por inspección visual.

## Errores que devolvían 500

| Archivo | Problema | Corrección |
|---|---|---|
| `routes/catalogo.py` | Llamaba a `obtener_todos()` en cuatro repositorios donde esa función no existe. `AttributeError` en los cuatro endpoints. | Se usa `listar()`, que sí existe. |
| `routes/prestamos.py` | Llamaba a `obtener_prestamos_activos()` y `obtener_todos()`, inexistentes. El módulo entero caía. | Se usan `listar()`, `activos_de_socio()` y `contar_activos_de_socio()`. |
| `routes/libros.py` | `crear(db, data)` contra una firma keyword-only. `TypeError`. | Se pasan los campos con nombre. |
| `routes/socios.py` | Mismo problema en el alta de socios. | Ídem. |
| `routes/libros.py` | `obtener_por_id()` devolvía `None` y rompía el `response_model`. | Se usa `obtener_o_error()`, que produce un 404. |
| `schemas/schemas.py` | Campos `Optional` sobre columnas `NOT NULL`: el error llegaba hasta MySQL. | Alineados con la base; ahora el rechazo es un 422 con mensaje. |

## Errores de lógica

| Archivo | Problema | Corrección |
|---|---|---|
| `routes/socios.py` | El DELETE se declaraba como `/api/socios/{id}` dentro de un router con ese mismo prefijo: la ruta real quedaba `/api/socios/api/socios/{id}` y el front recibía 405. | Ruta relativa al prefijo. |
| `routes/socios.py` | `solo_activos` se pasaba a `incluir_inactivos`: significan lo contrario. El listado mostraba a los dados de baja y el panel los contaba como activos. | Se usa `listar(solo_activos=...)`. |
| `socio_repository.py` | `eliminar()` hacía `commit()` adentro del repositorio, escribía un `datetime` en una columna `DATE` y devolvía `None` en silencio si el socio no existía (la ruta contestaba 200 igual). | Se eliminó; la baja lógica es `dar_de_baja()`. |
| `routes/prestamos.py` | No validaba que el ejemplar existiera ni que estuviera disponible. | Valida antes de tocar la base. |
| `frontend/prestamos.html` | Si el servidor fallaba, guardaba el préstamo en memoria y avisaba "cargado en pantalla". La devolución **nunca llamaba a la API**: cambiaba un booleano y decía "registrada con éxito". | Eliminado el modo demostración. Todo va contra la base. |
| `frontend/prestamos.html` | Mandaba `id_libro` donde la API espera `id_ejemplar`. | Selector en cascada: título → ejemplar disponible. |
| `frontend/prestamos.html` | Calculaba el estado con `p.devuelto`, campo que no existe: todos los préstamos figuraban activos. | Se usa `fecha_devolucion`. |
| `frontend/prestamos.html` | La columna "Devolución estimada" mostraba `fecha_devolucion` en vez de `fecha_vencimiento`. | Corregido. |

## Optimización

| Archivo | Problema | Corrección |
|---|---|---|
| `libro_repository.py` | Un `obtener_todos()` duplicado, sin eager loading ni límite, pisaba al `listar()` que sí los tenía. **24 consultas para 21 libros.** | Eliminado. Ahora **2 consultas**. |
| `prestamo_repository.py` | Sin el salto `ejemplar → libro`: el título obligaba a una consulta por préstamo. | Eager loading anidado. **1 consulta.** |
| `routes/prestamos.py` | Contaba préstamos con `len(lista)`, trayendo los objetos completos. | `SELECT COUNT(*)`. |
| Todas las rutas | Sin paginación: se devolvía la tabla entera. | `limite` y `desplazamiento`. |
| `frontend/*.html` | Los tres buscadores filtraban con `.filter()` sobre el listado ya descargado. | Filtros como query params; filtra la base. |
| `database/schema.sql` | `idx_prestamos_activos(fecha_devolucion)` tiene baja selectividad y no cubre las consultas reales. | Índices compuestos `(id_ejemplar, fecha_devolucion)` y `(id_socio, fecha_devolucion)`. |

## Base de datos

| Problema | Corrección |
|---|---|
| El script no creaba la base: empezaba en `USE biblioteca`. | `CREATE DATABASE IF NOT EXISTS`. |
| La lista de estados válidos vivía solo en Python: por phpMyAdmin se podía escribir cualquier cosa. | `CHECK (estado IN (...))`. |
| Nada impedía dos préstamos activos del mismo ejemplar. | Columna generada `ejemplar_en_curso` + índice `UNIQUE`. |
| Sin control de coherencia de fechas. | `CHECK` en autor, socio y prestamos. |
| `autor.fecha_nacimiento` era `NOT NULL`. | Admite nulo: de muchos autores no se conoce. |
| Búsqueda por título sin índice utilizable (`LIKE '%x%'` no usa B-tree). | Índice `FULLTEXT`. |

## Frontend

| Problema | Corrección |
|---|---|
| `app.js` existía pero **ningún HTML lo cargaba**, y usaba IDs que no existían. Cada página repetía la lógica inline. | Módulo único que todas las páginas cargan, con despacho por `data-pagina`. |
| No había ningún botón "Editar": faltaba la M de ABM. | Modal de edición en libros y socios. |
| Se pedían IDs numéricos a mano ("Editorial (ID): Ej: 1"). | `<select>` poblados desde `/api/catalogo`. |
| `alert()` como único feedback, descartando el mensaje del backend. | Avisos que muestran el motivo real del rechazo. |
| Sin estados de carga, vacío ni error: si la API caía, la tabla quedaba en blanco. | Los tres estados, más un banner de servidor caído. |
| Todo por `innerHTML` sin escapar (XSS). | Función `esc()` en cada interpolación. |
| Tablas de 9 columnas desbordadas en celular. | Contenedor con scroll horizontal. |
| `label` de 140px fijos + `calc(100% - 150px)`: se rompía con etiquetas largas. | Grilla que colapsa a una columna en mobile. |
| El estado se transmitía solo por color y emoji. | Insignias con texto. |
| Foco visible solo en inputs. | `:focus-visible` en todo lo interactivo. |
| `index.html` con estilos inline y colores que no coincidían con el tema; tarjeta de préstamos fija en 0. | Clases del CSS; los cuatro números salen de `/api/catalogo/estadisticas`. |
| `listaSociosGlobal` nunca declarada (global implícita). | Eliminada. |

## Documentación

Se agregó `documentacion/modelo-relacional.md` con la descripción de cada
tabla, clave primaria, claves foráneas y tipo de dato de cada campo. La
consigna lo pide explícitamente y no estaba entregado.

Se reescribió el `README.md` de la raíz, que decía dos líneas.
