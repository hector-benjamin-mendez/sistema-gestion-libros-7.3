# Correcciones aplicadas — capa de datos

Cada corrección del profesor, qué se hizo y dónde mirarlo.
Alcance: capa de acceso a datos (Bautista). Backend, frontend y JS
quedan para Héctor, Melany y Santiago; al final está lo que le cambia a
cada uno.

Verificado corriendo el schema y las 68 pruebas contra una base real, no
por inspección visual.

---

## 1. "Título como tabla aparte con: Id, Nombre, IdGenero"

Tabla nueva `titulo`, exactamente con esos tres campos.

Antes el título era una columna dentro de `libro`. Con tres copias del
mismo libro, el texto del título estaba escrito tres veces y el género
también. Alcanzaba con una letra distinta en una de las copias para que
el buscador devolviera dos resultados que eran la misma obra.

`nombre` es `UNIQUE`: es lo que permite cargar por título sin duplicar.

**Archivos:** `database/schema.sql`, `models/models.py`,
`repositories/titulo_repository.py`.

---

## 2. "Tabla libro con: Id, IdTitulo, IdEditorial, ISBN, IdEstado, Edicion, IdIdioma"

`libro` se rehizo con esos campos y **cambió de significado**: ahora es
la unidad física, no la ficha bibliográfica.

Consecuencias:

- **Se cae `ejemplar`.** Era exactamente esta entidad con otro nombre.
- **Se cae `subgenero`.** El género ahora cuelga del título, que es donde
  tiene sentido.
- **Nacen `idioma` y `estado`** como tablas, porque la corrección pide
  `IdIdioma` e `IdEstado`. Antes los dos eran texto libre y convivían
  "Espanol", "español" y "ES" en la misma columna.
- **El ISBN deja de ser UNIQUE.** Esto es lo más importante del punto: el
  ISBN identifica a la edición, no a la copia. Con el `UNIQUE` anterior
  era **imposible cargar una segunda copia del mismo libro**, la base la
  rechazaba. Ese solo detalle ya rompía el objetivo de la corrección 3.

Se agregaron dos campos que no estaban en la lista: `codigo_inventario`
y `fecha_alta`. El motivo está en el punto 3.

---

## 3. "Objetivo principal: tener control de cada unidad física"

> *"Le prestás a Augusto el día 23 una copia del libro IT y el 26 te lo
> devuelve roto, en el sistema esto figura y podés tomar la decisión de
> suspenderlo."*

Cuatro cambios para que ese caso funcione entero:

| Qué | Por qué |
|---|---|
| `prestamos.id_libro` apunta a la **copia** | No se presta "IT": se presta la copia INV-000009 de IT |
| `prestamos.id_estado_devolucion` | Sin esta columna solo queda registrado que la copia está rota. Nadie sabe **en manos de quién** se rompió |
| `socio.suspendido_hasta` | La sanción del ejemplo. Distinta de la baja: el socio sigue en el padrón. Vence sola |
| `libro.codigo_inventario` | Es la etiqueta del lomo. Es lo único que distingue una copia de otra **en el mostrador**; el id de la base no está escrito en ningún lado |

El caso está cargado en `seed.sql` con esos datos y probado de punta a
punta en `tests/test_prestamos_y_errores.py::test_el_caso_de_augusto_de_punta_a_punta`.

Consultas nuevas que el sistema ahora puede contestar:

```python
prestamo_repository.historial_de_copia(db, id_libro)
prestamo_repository.devoluciones_en_mal_estado(db, id_socio=...)
libro_repository.resumen_inventario(db)
```

---

## 4. "Manejar editoriales y géneros desde el html, cargar POR TITULO"

El alta entra por una sola función que recibe todo escrito:

```python
libro_repository.alta_por_texto(
    db, titulo="IT", genero="Terror", autores="King, Stephen",
    editorial="Plaza & Janés", idioma="Español", cantidad=3,
)
```

Resuelve o crea el título, el género, la editorial, el idioma y los
autores, y devuelve las tres copias con su código. Cargar de nuevo el
mismo título no duplica nada: cada tabla tiene `UNIQUE` en el nombre y la
collation `utf8mb4_unicode_ci` hace que "minotauro" y "Minotauro" sean el
mismo valor.

`cantidad` está porque una biblioteca no compra una copia, compra tres.

---

## 5. "No nos gusta la lista de selección para editorial y autores. Que sea por texto"

Cambios en la base para que el texto libre no ensucie los datos:

- `editorial.nombre` y `autor(apellido, nombre)` pasan a ser `UNIQUE`:
  es la clave con la que se busca antes de crear.
- `editorial.id_grupo_editorial` pasa a admitir `NULL`: nadie va a saber
  el grupo editorial mientras carga un libro.
- `autor.nacionalidad` y las fechas pasan a admitir `NULL` por lo mismo.
- `autor.nombre` es `NOT NULL DEFAULT ''` en vez de nulo, porque en MySQL
  los `NULL` no colisionan en un `UNIQUE` y "Borges" sin nombre de pila
  entraría dos veces.

El parser (`utils/texto.py`) acepta las dos formas que usa la gente:

| Se escribe | Se guarda |
|---|---|
| `Stephen King` | Stephen / King |
| `King, Stephen` | Stephen / King |
| `Ursula K. Le Guin` | Ursula K. / **Le Guin** |
| `Borges` | (vacío) / Borges |

Varios autores se separan con **punto y coma**, no con coma: la coma
queda libre para la forma "Apellido, Nombre".

Para que no se escriban dos variantes del mismo nombre, hay
autocompletado: `editorial_repository.sugerir()`,
`autor_repository.sugerir()`, `titulo_repository.sugerir()`.

---

## 6. "Hay que encontrar la mejor manera para realizar la base de datos"

| Decisión | Motivo |
|---|---|
| `idioma` y `estado` como tablas | Lo pedía el `IdIdioma`/`IdEstado`, y saca el texto libre de `libro` |
| `estado.permite_prestamo` | La regla "qué se puede prestar" vive en la base, no en una constante de Python. Agregar "en encuadernación" es insertar una fila |
| `libro_en_curso` + `UNIQUE` | La **base** impide dos préstamos activos de la misma copia. No depende de que el código lo chequee |
| Triggers en vez de `GENERATED ALWAYS AS` | La versión anterior andaba en MySQL 8 pero MariaDB la rechaza (error 1901). Con triggers corre en los dos, y en el grupo no todos usamos el mismo motor |
| `CHECK` en `autor`, `socio` y `prestamos` | Fechas coherentes garantizadas por la base |
| `ON DELETE RESTRICT` salvo en `titulo_autor` | Borrar un título con copias en el estante dejaría objetos físicos sin ficha |
| `GROUP BY` con todas las columnas | Con `GROUP BY titulo.id` la consulta de stock falla con `ONLY_FULL_GROUP_BY`, que es el modo por defecto de MySQL 8 en adelante |
| Se sacó el índice `FULLTEXT` | InnoDB no lo actualiza hasta el `COMMIT`, así que rompía las pruebas transaccionales. Con `LIKE` y miles de filas no se nota |
| Paginación en todos los listados | Ningún `listar()` devuelve la tabla entera |

**Probado en:** MySQL 9 y MariaDB 10.11, con `ONLY_FULL_GROUP_BY`
activado y desactivado. 68 pruebas en verde en las cuatro combinaciones.

---

## Archivos

**Nuevos:** `repositories/titulo_repository.py`,
`repositories/idioma_repository.py`, `repositories/estado_repository.py`,
`utils/texto.py`, `tests/test_carga_por_texto.py`,
`documentacion/diagrama.dbml`.

**Rehechos:** `database/schema.sql`, `database/seed.sql`,
`models/models.py`, `models/__init__.py`, `repositories/__init__.py`,
`repositories/libro_repository.py` (era la ficha, ahora es la copia),
`repositories/socio_repository.py` (+ suspensión),
`repositories/prestamo_repository.py`, los repositorios de catálogo
(+ alta por texto), `utils/db_errors.py`, los tests,
`backend/README.md`, `documentacion/modelo-relacional.md`.

**Borrar del repo:** `repositories/ejemplar_repository.py` y
`repositories/subgenero_repository.py`. Esas entidades ya no existen.

**Sin cambios:** `config/`, `models/base.py`, `utils/__init__.py`,
`pytest.ini`, `requirements.txt`.

---

## Lo que le cambia a cada uno

**Héctor.** `/api/libros` ahora es el catálogo de **títulos**
(`titulo_repository.listar_con_stock()`); las copias van por
`/api/copias`. El POST de alta recibe **texto**, no ids
(`libro_repository.alta_por_texto()`). El POST de préstamo manda
`id_libro` (la copia) en vez de `id_ejemplar`, y la devolución recibe
además el estado en el que volvió. `/api/catalogo/subgeneros`
desaparece; se agregan `idiomas` y `estados`. Nuevos:
`/api/socios/{id}/suspender` y `/api/copias/{id}/historial`.
`prestar()` y `registrar_devolucion()` ya dejan coherentes las dos tablas
en la misma transacción: alcanza con llamarlas y hacer `commit()`.

**Melany.** Los `<select>` de editorial y autores se reemplazan por
`<input type="text">` con `<datalist>`. El formulario de alta necesita un
campo nuevo: **cantidad de copias**. La pantalla de libros pasa a tener
dos niveles: listado de títulos → detalle con sus copias.

**Santiago.** Ya no hay que poblar los `<select>` de editorial ni de
autores: al tipear se le pega al endpoint de sugerencias y se llena el
`<datalist>`. El flujo de préstamo es en cascada: se busca el título → se
listan sus copias disponibles → se elige el código de inventario.
