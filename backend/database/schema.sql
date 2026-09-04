-- ============================================================
-- Sistema de Gestion Bibliotecaria - Grupo 7.3
-- Script de creacion del esquema  (VERSION 2 - correcciones)
--
-- Cambios respecto de la version anterior, uno por correccion:
--
--   1) "Titulo como tabla aparte con: Id, Nombre, IdGenero"
--      -> tabla `titulo`. La obra deja de estar repetida en cada copia.
--
--   2) "Tabla libro con: Id, IdTitulo, IdEditorial, ISBN, IdEstado,
--       Edicion, IdIdioma"
--      -> tabla `libro`. Ahora `libro` ES LA UNIDAD FISICA. Desaparece
--         `ejemplar`: era la misma entidad con otro nombre.
--
--   3) "Objetivo principal: tener control de cada unidad fisica"
--      -> `prestamos` apunta a `libro` (la copia), no al titulo.
--         `prestamos.id_estado_devolucion` guarda en que estado volvio
--         cada copia, asi el sistema sabe QUIEN la rompio y no solo QUE
--         esta rota. `socio.suspendido_hasta` permite la sancion.
--
--   6) "Encontrar la mejor manera para realizar la base de datos"
--      -> `idioma` y `estado` pasan a ser tablas (lo pedia el IdIdioma /
--         IdEstado de la correccion 2), se saco el UNIQUE del ISBN
--         (tres copias de la misma edicion comparten ISBN) y se
--         normalizo `subgenero` fuera del modelo: el genero ahora cuelga
--         del titulo, que es donde tiene sentido.
--
-- Requiere MySQL 8.0+ o MariaDB 10.2+ (usa CHECK y columnas generadas).
-- Ejecutar:  mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS biblioteca
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE biblioteca;

-- ---------- 0. Limpieza ----------
-- Primero las tablas del modelo viejo que ya no existen, despues las
-- actuales en orden inverso a las dependencias. Asi el script se puede
-- re-ejecutar sobre una base que todavia tiene el esquema anterior.

DROP TABLE IF EXISTS prestamos;
DROP TABLE IF EXISTS libro_autor;      -- modelo viejo
DROP TABLE IF EXISTS ejemplar;         -- modelo viejo (ahora es `libro`)
DROP TABLE IF EXISTS titulo_autor;
DROP TABLE IF EXISTS libro;
DROP TABLE IF EXISTS titulo;
DROP TABLE IF EXISTS subgenero;        -- modelo viejo
DROP TABLE IF EXISTS socio;
DROP TABLE IF EXISTS rango;
DROP TABLE IF EXISTS autor;
DROP TABLE IF EXISTS editorial;
DROP TABLE IF EXISTS grupo_editorial;
DROP TABLE IF EXISTS estado;
DROP TABLE IF EXISTS idioma;
DROP TABLE IF EXISTS genero;


-- ============================================================
-- 1. Tablas de catalogo (sin dependencias)
-- ============================================================

-- El nombre es UNIQUE porque el HTML carga generos POR TEXTO
-- (correccion 4): si el bibliotecario escribe "Terror" y ya existe,
-- se reusa la fila en vez de duplicarla. El UNIQUE es lo que hace
-- posible el "buscar o crear" del repositorio.
CREATE TABLE genero (
    id     INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,

    CONSTRAINT uq_genero_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Sale del "IdIdioma" de la correccion 2. Antes era texto libre dentro
-- de libro: convivian 'Espanol', 'espaniol' y 'ES' en la misma columna.
CREATE TABLE idioma (
    id     INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(60) NOT NULL,

    CONSTRAINT uq_idioma_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Sale del "IdEstado" de la correccion 2.
--
-- `permite_prestamo` evita que la regla "que estados se pueden prestar"
-- quede escrita en el codigo Python. Manana la biblioteca agrega el
-- estado "en encuadernacion" y no hay que tocar ni una linea: se
-- inserta la fila con permite_prestamo = 0.
CREATE TABLE estado (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    nombre           VARCHAR(40)  NOT NULL,
    permite_prestamo TINYINT(1)   NOT NULL DEFAULT 0,
    descripcion      VARCHAR(255) NULL,

    CONSTRAINT uq_estado_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE grupo_editorial (
    id     INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,

    CONSTRAINT uq_grupo_editorial_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- `nombre` es UNIQUE por la correccion 5: la editorial se escribe a
-- mano, no se elige de una lista. El UNIQUE es la clave de busqueda.
--
-- `id_grupo_editorial` pasa a admitir NULL, tambien por la correccion 5:
-- si el bibliotecario escribe "Minotauro" y esa editorial todavia no
-- existe, el sistema tiene que poder darla de alta sin obligarlo a
-- averiguar a que grupo editorial pertenece.
CREATE TABLE editorial (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    nombre             VARCHAR(100) NOT NULL,
    direccion          VARCHAR(255) NULL,
    fecha_fundacion    DATE         NULL,
    id_grupo_editorial INT          NULL,

    CONSTRAINT fk_editorial_grupo_editorial
        FOREIGN KEY (id_grupo_editorial) REFERENCES grupo_editorial(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT uq_editorial_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Mismo criterio que editorial (correccion 5): el autor se tipea.
--
-- `nombre` es NOT NULL DEFAULT '' y no NULL: la clave de busqueda es
-- (apellido, nombre) y en MySQL un UNIQUE con NULLs no impide repetidos,
-- asi que "Borges" sin nombre de pila entraria dos veces. Con cadena
-- vacia el UNIQUE si funciona.
CREATE TABLE autor (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    nombre              VARCHAR(100) NOT NULL DEFAULT '',
    apellido            VARCHAR(100) NOT NULL,
    fecha_nacimiento    DATE         NULL,
    fecha_fallecimiento DATE         NULL,
    nacionalidad        VARCHAR(60)  NULL,

    CONSTRAINT uq_autor_nombre_completo UNIQUE (apellido, nombre),
    -- No se puede morir antes de nacer.
    CONSTRAINT chk_autor_fechas CHECK (
        fecha_fallecimiento IS NULL
        OR fecha_nacimiento IS NULL
        OR fecha_fallecimiento >= fecha_nacimiento
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rango (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    max_prestamos INT          NOT NULL,
    dias_prestamo INT          NOT NULL,

    CONSTRAINT uq_rango_nombre UNIQUE (nombre),
    CONSTRAINT chk_rango_valores CHECK (max_prestamos > 0 AND dias_prestamo > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 2. Titulo  (correccion 1)
-- ============================================================
-- La OBRA, no el papel. "IT" es un titulo; las tres copias que hay en
-- el estante son tres filas de `libro`.
--
-- Antes el titulo era una columna de libro: si la biblioteca tenia tres
-- copias, el texto "IT" estaba escrito tres veces y el genero tambien.
-- Con una sola letra distinta en una de las copias, el buscador por
-- titulo devolvia dos libros que en realidad eran el mismo.
--
-- `nombre` UNIQUE: es lo que permite cargar POR TITULO desde el HTML
-- (correccion 4) sin generar duplicados.
CREATE TABLE titulo (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    nombre    VARCHAR(255) NOT NULL,
    id_genero INT          NOT NULL,

    CONSTRAINT fk_titulo_genero
        FOREIGN KEY (id_genero) REFERENCES genero(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT uq_titulo_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- La autoria es de la OBRA, no de la copia: si hay cinco copias de IT,
-- Stephen King no las escribio cinco veces. Por eso la N:M cuelga de
-- titulo y no de libro.
CREATE TABLE titulo_autor (
    id_titulo INT NOT NULL,
    id_autor  INT NOT NULL,

    PRIMARY KEY (id_titulo, id_autor),
    CONSTRAINT fk_titulo_autor_titulo
        FOREIGN KEY (id_titulo) REFERENCES titulo(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_titulo_autor_autor
        FOREIGN KEY (id_autor) REFERENCES autor(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 3. Libro = LA UNIDAD FISICA  (correcciones 2 y 3)
-- ============================================================
-- Una fila = un objeto de papel que se puede tocar, prestar y romper.
-- Es lo que se presta y lo que tiene estado.
--
-- `isbn` NO es UNIQUE, y es a proposito: el ISBN identifica a la
-- edicion, no a la copia. Las tres copias de la misma edicion de IT
-- comparten ISBN. En el modelo anterior el ISBN era UNIQUE en libro, y
-- eso volvia imposible cargar una segunda copia del mismo libro: la
-- base la rechazaba. Ese solo detalle ya rompia el objetivo de la
-- correccion 3.
--
-- `codigo_inventario` es el agregado que no estaba en la lista de la
-- correccion, y esta porque el control fisico lo necesita: es la
-- etiqueta pegada en el lomo, lo unico que distingue una copia de otra
-- en el mostrador. El id de la base no sirve para eso porque no esta
-- escrito en ningun lado. Lo genera el repositorio si no se lo pasan.
CREATE TABLE libro (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    id_titulo         INT         NOT NULL,
    id_editorial      INT         NOT NULL,
    isbn              VARCHAR(20) NULL,
    id_estado         INT         NOT NULL,
    edicion           VARCHAR(20) NULL,
    id_idioma         INT         NOT NULL,
    codigo_inventario VARCHAR(30) NULL,
    fecha_alta        DATE        NOT NULL,

    CONSTRAINT fk_libro_titulo
        FOREIGN KEY (id_titulo) REFERENCES titulo(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_libro_editorial
        FOREIGN KEY (id_editorial) REFERENCES editorial(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_libro_estado
        FOREIGN KEY (id_estado) REFERENCES estado(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_libro_idioma
        FOREIGN KEY (id_idioma) REFERENCES idioma(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT uq_libro_codigo_inventario UNIQUE (codigo_inventario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 4. Socios y prestamos
-- ============================================================

-- `suspendido_hasta` sale del ejemplo de la correccion 3: "podes tomar
-- la decision de suspenderlo". Es distinto de `fecha_baja`: la baja saca
-- al socio del padron, la suspension lo deja adentro pero sin poder
-- pedir libros hasta una fecha.
CREATE TABLE socio (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    nombre           VARCHAR(100) NOT NULL,
    apellido         VARCHAR(100) NOT NULL,
    dni              VARCHAR(15)  NOT NULL,
    email            VARCHAR(150) NOT NULL,
    telefono         VARCHAR(30)  NULL,
    id_rango         INT          NOT NULL,
    fecha_alta       DATE         NOT NULL,
    fecha_baja       DATE         NULL,   -- NULL = sigue en el padron
    suspendido_hasta DATE         NULL,   -- NULL = sin sancion vigente

    CONSTRAINT fk_socio_rango
        FOREIGN KEY (id_rango) REFERENCES rango(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT uq_socio_dni   UNIQUE (dni),
    CONSTRAINT uq_socio_email UNIQUE (email),
    CONSTRAINT chk_socio_fechas CHECK (fecha_baja IS NULL OR fecha_baja >= fecha_alta)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- El prestamo apunta a `libro`, o sea a LA COPIA. Ahi esta la correccion 3
-- entera: no se presta "IT", se presta la copia INV-000009 de IT.
--
-- `id_estado_devolucion` es la otra mitad. Sin esa columna, cuando
-- Augusto devuelve el libro roto lo unico que queda registrado es que la
-- copia esta rota; nadie sabe en manos de quien se rompio. Con la
-- columna, el historial dice: "esta copia volvio DANIADA del prestamo 7,
-- que era de Augusto". Recien con ese dato la suspension es defendible.
CREATE TABLE prestamos (
    id                   INT  AUTO_INCREMENT PRIMARY KEY,
    id_socio             INT  NOT NULL,
    id_libro             INT  NOT NULL,
    fecha_prestamo       DATE NOT NULL,
    fecha_vencimiento    DATE NOT NULL,
    fecha_devolucion     DATE NULL,          -- NULL = prestamo activo
    id_estado_devolucion INT  NULL,          -- como volvio la copia
    observaciones        VARCHAR(255) NULL,

    -- Vale id_libro mientras el prestamo esta activo y NULL cuando ya se
    -- devolvio. Como los NULL no colisionan en un indice UNIQUE, la BASE
    -- garantiza que una copia no pueda estar en dos prestamos activos a
    -- la vez. No depende de que el codigo Python se acuerde de chequearlo.
    --
    -- La llenan los dos triggers de mas abajo, NUNCA la aplicacion.
    -- (La version anterior de este script la resolvia con GENERATED
    -- ALWAYS AS, que anda en MySQL 8 pero MariaDB rechaza porque la
    -- expresion referencia otra columna: error 1901. Con triggers la
    -- garantia es la misma y el script corre en los dos motores, que
    -- importa porque no todos en el grupo tenemos el mismo servidor.)
    libro_en_curso INT NULL,

    CONSTRAINT fk_prestamos_socio
        FOREIGN KEY (id_socio) REFERENCES socio(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_prestamos_libro
        FOREIGN KEY (id_libro) REFERENCES libro(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    -- Esta FK va con ON UPDATE RESTRICT y no CASCADE como las otras:
    -- MariaDB no permite un CHECK sobre una columna que ademas es clave
    -- foranea con ON UPDATE CASCADE (error 1901), porque no puede
    -- evaluar el CHECK mientras propaga la cascada. Se elige conservar
    -- el CHECK: los id son autoincrementales y no se actualizan nunca,
    -- asi que la cascada aca no aportaba nada de todos modos.
    CONSTRAINT fk_prestamos_estado_devolucion
        FOREIGN KEY (id_estado_devolucion) REFERENCES estado(id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,

    CONSTRAINT uq_prestamo_libro_en_curso UNIQUE (libro_en_curso),

    CONSTRAINT chk_prestamo_vencimiento CHECK (fecha_vencimiento >= fecha_prestamo),
    CONSTRAINT chk_prestamo_devolucion  CHECK (
        fecha_devolucion IS NULL OR fecha_devolucion >= fecha_prestamo
    ),
    -- No se puede registrar como volvio algo que todavia no volvio.
    CONSTRAINT chk_prestamo_estado_devolucion CHECK (
        id_estado_devolucion IS NULL OR fecha_devolucion IS NOT NULL
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 5. Triggers de coherencia
-- ============================================================
-- Mantienen `prestamos.libro_en_curso` sin que nadie tenga que
-- acordarse: se dispara igual si el prestamo lo carga la aplicacion, el
-- seed o alguien a mano por phpMyAdmin.
--
-- Son de una sola sentencia a proposito (SET, sin BEGIN...END): asi no
-- hace falta cambiar el DELIMITER y el script se importa sin trucos.

DROP TRIGGER IF EXISTS trg_prestamos_en_curso_ins;
DROP TRIGGER IF EXISTS trg_prestamos_en_curso_upd;

CREATE TRIGGER trg_prestamos_en_curso_ins
BEFORE INSERT ON prestamos
FOR EACH ROW
    SET NEW.libro_en_curso = IF(NEW.fecha_devolucion IS NULL, NEW.id_libro, NULL);

CREATE TRIGGER trg_prestamos_en_curso_upd
BEFORE UPDATE ON prestamos
FOR EACH ROW
    SET NEW.libro_en_curso = IF(NEW.fecha_devolucion IS NULL, NEW.id_libro, NULL);


-- ============================================================
-- 6. Indices
-- ============================================================
-- Estan elegidos mirando los WHERE y los ORDER BY que ejecuta la
-- aplicacion, no puestos por las dudas. Los UNIQUE de arriba ya crean
-- indice, asi que no se repiten aca.

-- Catalogo filtrado por genero.
CREATE INDEX idx_titulo_genero ON titulo(id_genero);

-- "Que copias hay de este titulo, y cuales estan disponibles?": es la
-- consulta que corre cada vez que alguien va a prestar algo.
CREATE INDEX idx_libro_titulo_estado ON libro(id_titulo, id_estado);
CREATE INDEX idx_libro_editorial     ON libro(id_editorial);
CREATE INDEX idx_libro_isbn          ON libro(isbn);

-- ORDER BY apellido, nombre del padron de socios.
CREATE INDEX idx_socio_apellido_nombre ON socio(apellido, nombre);

-- COMPUESTOS: las dos consultas mas frecuentes del sistema.
--   "esta prestada esta copia?"      -> id_libro + fecha_devolucion IS NULL
--   "cuantos activos tiene el socio?" -> id_socio + fecha_devolucion IS NULL
-- Un indice solo sobre fecha_devolucion tiene baja selectividad (la
-- mitad de la tabla es NULL) y practicamente no ayuda.
CREATE INDEX idx_prestamos_libro_activo ON prestamos(id_libro, fecha_devolucion);
CREATE INDEX idx_prestamos_socio_activo ON prestamos(id_socio, fecha_devolucion);

-- Listado de vencidos.
CREATE INDEX idx_prestamos_vencimiento ON prestamos(fecha_devolucion, fecha_vencimiento);

-- NOTA sobre el indice FULLTEXT que tenia la version anterior:
-- se saco. InnoDB no actualiza el indice FULLTEXT hasta el COMMIT, y las
-- pruebas corren dentro de una transaccion que se deshace al terminar,
-- asi que MATCH ... AGAINST no encontraba nada de lo recien insertado.
-- La busqueda por texto usa LIKE, que con el volumen de una biblioteca
-- barrial (miles de filas, no millones) resuelve sin que se note.
