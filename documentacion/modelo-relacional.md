# Modelo relacional — Sistema de Gestión Bibliotecaria

Documento de diseño de la base de datos. La consigna lo pide
explícitamente: descripción de cada tabla, clave primaria, claves
foráneas y tipo de dato de cada campo.

Versión 2, rehecha sobre las correcciones del profesor.
Motor: MySQL 8+ / MariaDB 10.2+, InnoDB, `utf8mb4_unicode_ci`.

---

## 1. La decisión de fondo

El modelo separa **la obra** de **el objeto de papel**:

```
genero ──< titulo ──< libro >── editorial >── grupo_editorial
             │          │
             │          ├── idioma
             │          └── estado
             │
        titulo_autor >── autor

rango ──< socio ──< prestamos >── libro
                        │
                        └── estado   (en qué estado volvió)
```

- **`titulo`** es "IT, de Stephen King, género terror". Existe una vez.
- **`libro`** es la copia que está en el estante, con su código de
  inventario y su estado. Existe una vez por cada objeto.

Esa separación es la corrección 1 y es la que hace posible el objetivo
de la corrección 3: si la biblioteca tiene tres copias de IT, el sistema
sabe cuál de las tres prestó, a quién y cómo volvió.

**Por qué no alcanzaba el modelo anterior:** tenía `libro` (la ficha) y
`ejemplar` (la copia), que es la misma idea con otros nombres, pero el
título y el género vivían repetidos en cada fila de `libro` y el `isbn`
era `UNIQUE`. Con el ISBN único era literalmente imposible cargar una
segunda copia de la misma edición: la base la rechazaba.

---

## 2. Tablas

### 2.1 `genero`

Clasificación de las obras. Se carga escribiéndola desde el formulario.

| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** |
| `nombre` | VARCHAR(100) | No | **UNIQUE**. Clave de búsqueda del alta por texto |

---

### 2.2 `idioma`

| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** |
| `nombre` | VARCHAR(60) | No | **UNIQUE** |

Sale del `IdIdioma` de la corrección 2. Antes era texto libre dentro de
`libro` y convivían "Espanol", "español" y "ES" en la misma columna.

---

### 2.3 `estado`

Estado de una copia física.

| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** |
| `nombre` | VARCHAR(40) | No | **UNIQUE**. `disponible`, `prestado`, `en_reparacion`, `dañado`, `extraviado`, `baja` |
| `permite_prestamo` | TINYINT(1) | No | Si es 1, una copia en este estado se puede prestar |
| `descripcion` | VARCHAR(255) | Sí | Texto de ayuda para la pantalla |

Sale del `IdEstado` de la corrección 2. `permite_prestamo` evita que la
regla "qué se puede prestar" quede escrita en el código: agregar
"en encuadernación" es insertar una fila.

---

### 2.4 `grupo_editorial`

| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** |
| `nombre` | VARCHAR(100) | No | **UNIQUE** |

---

### 2.5 `editorial`

| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** |
| `nombre` | VARCHAR(100) | No | **UNIQUE**. Se escribe, no se elige |
| `direccion` | VARCHAR(255) | Sí | |
| `fecha_fundacion` | DATE | Sí | |
| `id_grupo_editorial` | INT | **Sí** | **FK →** `grupo_editorial(id)`, ON DELETE SET NULL |

Admite `NULL` en el grupo por la corrección 5: si la editorial se crea
mientras se carga un libro, nadie va a saber a qué grupo pertenece.

---

### 2.6 `autor`

| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** |
| `nombre` | VARCHAR(100) | No, default `''` | Nombre de pila |
| `apellido` | VARCHAR(100) | No | |
| `fecha_nacimiento` | DATE | Sí | De muchos autores no se conoce |
| `fecha_fallecimiento` | DATE | Sí | |
| `nacionalidad` | VARCHAR(60) | Sí | |

- **UNIQUE (apellido, nombre)**: es la clave del alta por texto.
- **CHECK**: no se puede fallecer antes de nacer.

`nombre` es `NOT NULL DEFAULT ''` y no nulo a propósito: en MySQL los
`NULL` no colisionan en un índice `UNIQUE`, así que con `NULL` un autor
sin nombre de pila ("Borges") entraría dos veces.

---

### 2.7 `rango`

Categoría de socio. Define el límite de préstamos y el plazo.

| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** |
| `nombre` | VARCHAR(100) | No | **UNIQUE** |
| `max_prestamos` | INT | No | **CHECK** > 0 |
| `dias_prestamo` | INT | No | **CHECK** > 0 |

---

### 2.8 `titulo` — la OBRA (corrección 1)

| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** |
| `nombre` | VARCHAR(255) | No | **UNIQUE**. Permite cargar POR TÍTULO sin duplicar |
| `id_genero` | INT | No | **FK →** `genero(id)`, ON DELETE RESTRICT |

---

### 2.9 `titulo_autor` — N:M

| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id_titulo` | INT | No | **PK compuesta** · **FK →** `titulo(id)`, ON DELETE CASCADE |
| `id_autor` | INT | No | **PK compuesta** · **FK →** `autor(id)`, ON DELETE CASCADE |

La PK compuesta impide que el mismo autor figure dos veces en la misma
obra. Cuelga de `titulo` y no de `libro`: si hay cinco copias de IT,
Stephen King no las escribió cinco veces.

---

### 2.10 `libro` — la UNIDAD FÍSICA (correcciones 2 y 3)

Una fila = un objeto de papel que se puede prestar y romper.

| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** |
| `id_titulo` | INT | No | **FK →** `titulo(id)`, ON DELETE RESTRICT |
| `id_editorial` | INT | No | **FK →** `editorial(id)`, ON DELETE RESTRICT |
| `isbn` | VARCHAR(20) | Sí | **Sin UNIQUE**: identifica a la edición, no a la copia |
| `id_estado` | INT | No | **FK →** `estado(id)`, ON DELETE RESTRICT |
| `edicion` | VARCHAR(20) | Sí | |
| `id_idioma` | INT | No | **FK →** `idioma(id)`, ON DELETE RESTRICT |
| `codigo_inventario` | VARCHAR(30) | Sí | **UNIQUE**. La etiqueta del lomo |
| `fecha_alta` | DATE | No | Cuándo entró la copia a la biblioteca |

Los dos últimos campos no estaban en la lista de la corrección y se
agregaron por una razón concreta: el control físico necesita poder
identificar una copia **en el mostrador**, y el `id` de la base no está
escrito en ningún lado. El repositorio lo genera solo (`INV-000042`) si
no se lo pasan.

---

### 2.11 `socio`

| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** |
| `nombre` | VARCHAR(100) | No | |
| `apellido` | VARCHAR(100) | No | |
| `dni` | VARCHAR(15) | No | **UNIQUE** |
| `email` | VARCHAR(150) | No | **UNIQUE** |
| `telefono` | VARCHAR(30) | Sí | |
| `id_rango` | INT | No | **FK →** `rango(id)`, ON DELETE RESTRICT |
| `fecha_alta` | DATE | No | |
| `fecha_baja` | DATE | Sí | NULL = sigue en el padrón. Baja lógica |
| `suspendido_hasta` | DATE | Sí | NULL = sin sanción vigente |

**CHECK**: `fecha_baja >= fecha_alta`.

`suspendido_hasta` sale del ejemplo de la corrección 3. Es distinto de
la baja: el socio sigue en el padrón pero no puede pedir libros hasta esa
fecha. Vence solo, sin ningún proceso que lo limpie.

El DNI es `VARCHAR` y no `INT` a propósito: no se hacen cuentas con él,
puede tener ceros a la izquierda y puede venir con puntos.

---

### 2.12 `prestamos`

| Campo | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id` | INT AUTO_INCREMENT | No | **PK** |
| `id_socio` | INT | No | **FK →** `socio(id)`, ON DELETE RESTRICT |
| `id_libro` | INT | No | **FK →** `libro(id)`. Apunta a la COPIA |
| `fecha_prestamo` | DATE | No | |
| `fecha_vencimiento` | DATE | No | |
| `fecha_devolucion` | DATE | Sí | **NULL = préstamo activo** |
| `id_estado_devolucion` | INT | Sí | **FK →** `estado(id)`. En qué estado volvió |
| `observaciones` | VARCHAR(255) | Sí | |
| `libro_en_curso` | INT | Sí | **UNIQUE**. La mantienen triggers, la app no la toca |

**CHECK:**
- `fecha_vencimiento >= fecha_prestamo`
- `fecha_devolucion IS NULL OR fecha_devolucion >= fecha_prestamo`
- `id_estado_devolucion IS NULL OR fecha_devolucion IS NOT NULL`
  (no se registra cómo volvió algo que todavía no volvió)

**`id_estado_devolucion` es la mitad que faltaba de la corrección 3.**
Sin esa columna, cuando Augusto devuelve la copia rota lo único que queda
registrado es que la copia está rota: nadie sabe en manos de quién se
rompió. Con la columna, el historial dice "esta copia volvió dañada del
préstamo 3, que era de Augusto", y recién ahí la suspensión es
defendible.

**`libro_en_curso`** vale `id_libro` mientras el préstamo está activo y
`NULL` cuando ya se devolvió. Como los `NULL` no colisionan en un índice
`UNIQUE`, la base garantiza sola que una copia no pueda estar en dos
préstamos activos a la vez, sin depender de que el código lo chequee.

La primera versión lo resolvía con `GENERATED ALWAYS AS`, que funciona
en MySQL 8 pero MariaDB rechaza (error 1901). Se pasó a dos triggers
`BEFORE INSERT` / `BEFORE UPDATE`: la garantía es la misma y el script
corre en los dos motores, que importa porque no todos en el grupo
tenemos el mismo servidor.

---

## 3. Resumen de claves foráneas

| Tabla | Columna | Referencia | ON DELETE |
|---|---|---|---|
| `titulo` | `id_genero` | `genero(id)` | RESTRICT |
| `editorial` | `id_grupo_editorial` | `grupo_editorial(id)` | SET NULL |
| `titulo_autor` | `id_titulo` | `titulo(id)` | CASCADE |
| `titulo_autor` | `id_autor` | `autor(id)` | CASCADE |
| `libro` | `id_titulo` | `titulo(id)` | RESTRICT |
| `libro` | `id_editorial` | `editorial(id)` | RESTRICT |
| `libro` | `id_estado` | `estado(id)` | RESTRICT |
| `libro` | `id_idioma` | `idioma(id)` | RESTRICT |
| `socio` | `id_rango` | `rango(id)` | RESTRICT |
| `prestamos` | `id_socio` | `socio(id)` | RESTRICT |
| `prestamos` | `id_libro` | `libro(id)` | RESTRICT |
| `prestamos` | `id_estado_devolucion` | `estado(id)` | RESTRICT |

**Criterio:** `CASCADE` solo en `titulo_autor`, porque una fila de esa
tabla no significa nada sola. En todo lo demás, `RESTRICT`: borrar un
título que tiene copias en el estante dejaría objetos físicos sin ficha,
y borrar un socio con préstamos borraría el historial.

La FK `prestamos.id_estado_devolucion` va con `ON UPDATE RESTRICT` y no
`CASCADE` como las demás: MariaDB no permite un `CHECK` sobre una columna
que además es FK con `ON UPDATE CASCADE`. Se eligió conservar el `CHECK`,
porque los id son autoincrementales y no se actualizan nunca.

---

## 4. Índices

Elegidos mirando los `WHERE` y `ORDER BY` que ejecuta la aplicación, no
puestos por las dudas. Los `UNIQUE` ya crean índice y no se repiten.

| Índice | Columnas | Para qué |
|---|---|---|
| `idx_titulo_genero` | `titulo(id_genero)` | Filtrar el catálogo por género |
| `idx_libro_titulo_estado` | `libro(id_titulo, id_estado)` | "¿Qué copias disponibles hay de este título?" |
| `idx_libro_editorial` | `libro(id_editorial)` | Filtro por editorial |
| `idx_libro_isbn` | `libro(isbn)` | Búsqueda por ISBN |
| `idx_socio_apellido_nombre` | `socio(apellido, nombre)` | Orden del padrón |
| `idx_prestamos_libro_activo` | `prestamos(id_libro, fecha_devolucion)` | "¿Está prestada esta copia?" |
| `idx_prestamos_socio_activo` | `prestamos(id_socio, fecha_devolucion)` | "¿Cuántos activos tiene el socio?" |
| `idx_prestamos_vencimiento` | `prestamos(fecha_devolucion, fecha_vencimiento)` | Listado de vencidos |

Los dos de `prestamos` son compuestos porque un índice solo sobre
`fecha_devolucion` tiene baja selectividad: la mitad de la tabla es
`NULL` y el motor termina leyendo casi todo igual.

**Sobre el índice FULLTEXT que tenía la versión anterior:** se sacó.
InnoDB no actualiza el índice FULLTEXT hasta el `COMMIT`, y las pruebas
corren dentro de una transacción que se deshace al terminar, así que
`MATCH ... AGAINST` no encontraba nada de lo recién insertado. La
búsqueda por texto usa `LIKE`, que con el volumen de una biblioteca
barrial (miles de filas, no millones) resuelve sin que se note.

---

## 5. Cómo regenerar el diagrama

El archivo `diagrama.dbml` de esta misma carpeta se pega en
[dbdiagram.io](https://dbdiagram.io) y genera el diagrama
entidad-relación actualizado para la entrega.
