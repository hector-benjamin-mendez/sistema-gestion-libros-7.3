-- ============================================================
-- Sistema de Gestion Bibliotecaria - Grupo 7.3
-- Script de creacion del esquema
-- Fuente de verdad: diagrama entidad-relacion (documentacion/)
--
-- Requiere MySQL 8.0 o superior (usa CHECK y columnas generadas).
-- Ejecutar:  mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS biblioteca
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE biblioteca;

-- Se borra en orden inverso a las dependencias para poder re-ejecutar el script.
DROP TABLE IF EXISTS prestamos;
DROP TABLE IF EXISTS libro_autor;
DROP TABLE IF EXISTS ejemplar;
DROP TABLE IF EXISTS libro;
DROP TABLE IF EXISTS socio;
DROP TABLE IF EXISTS rango;
DROP TABLE IF EXISTS autor;
DROP TABLE IF EXISTS editoriagl;
DROP TABLE IF EXISTS grupo_editorial;
DROP TABLE IF EXISTS subgenero;
DROP TABLE IF EXISTS genero;


-- ---------- 1. Tablas sin dependencias ----------

CREATE TABLE genero (
    id     INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE grupo_editorial (
    id     INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE autor (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    nombre              VARCHAR(100) NOT NULL,
    apellido            VARCHAR(100) NOT NULL,
    fecha_nacimiento    DATE         NULL,     -- de muchos autores no se conoce
    fecha_fallecimiento DATE         NULL,
    nacionalidad        VARCHAR(60)  NOT NULL,

    -- No se puede morir antes de nacer.
    CONSTRAINT chk_autor_fechas CHECK (
        fecha_fallecimiento IS NULL
        OR fecha_nacimiento IS NULL
        OR fecha_fallecimiento >= fecha_nacimiento
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rango (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL UNIQUE,
    max_prestamos INT          NOT NULL,
    dias_prestamo INT          NOT NULL,

    CONSTRAINT chk_rango_valores CHECK (max_prestamos > 0 AND dias_prestamo > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ---------- 2. Tablas de segundo nivel ----------

CREATE TABLE subgenero (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    nombre    VARCHAR(100) NOT NULL,
    id_genero INT          NOT NULL,

    CONSTRAINT fk_subgenero_genero
        FOREIGN KEY (id_genero) REFERENCES genero(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    -- No puede haber dos subgeneros con el mismo nombre dentro de un genero.
    CONSTRAINT uq_subgenero_nombre_genero UNIQUE (id_genero, nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE editorial (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    nombre             VARCHAR(100) NOT NULL,
    direccion          VARCHAR(255) NULL,
    fecha_fundacion    DATE         NULL,
    id_grupo_editorial INT          NOT NULL,

    CONSTRAINT fk_editorial_grupo_editorial
        FOREIGN KEY (id_grupo_editorial) REFERENCES grupo_editorial(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT uq_editorial_nombre_grupo UNIQUE (id_grupo_editorial, nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE socio (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    nombre     VARCHAR(100) NOT NULL,
    apellido   VARCHAR(100) NOT NULL,
    dni        VARCHAR(15)  NOT NULL UNIQUE,
    email      VARCHAR(150) NOT NULL UNIQUE,
    telefono   VARCHAR(30)  NULL,
    id_rango   INT          NOT NULL,
    fecha_alta DATE         NOT NULL,
    fecha_baja DATE         NULL,          -- NULL = socio activo (baja logica)

    CONSTRAINT fk_socio_rango
        FOREIGN KEY (id_rango) REFERENCES rango(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    -- No se puede dar de baja antes de dar de alta.
    CONSTRAINT chk_socio_fechas CHECK (fecha_baja IS NULL OR fecha_baja >= fecha_alta)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ---------- 3. Libro y sus dependientes ----------

CREATE TABLE libro (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    titulo            VARCHAR(255) NOT NULL,
    isbn              VARCHAR(20)  NULL UNIQUE,   -- MySQL admite varios NULL en UNIQUE
    id_subgenero      INT          NOT NULL,
    id_editorial      INT          NOT NULL,
    fecha_publicacion DATE         NOT NULL,
    idioma            VARCHAR(50)  NOT NULL,
    numero_edicion    VARCHAR(20)  NOT NULL,

    CONSTRAINT fk_libro_subgenero
        FOREIGN KEY (id_subgenero) REFERENCES subgenero(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_libro_editorial
        FOREIGN KEY (id_editorial) REFERENCES editorial(id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Relacion N:M entre libro y autor. PK compuesta: un autor no puede figurar
-- dos veces en el mismo libro. CASCADE porque la fila no tiene sentido sola.
CREATE TABLE libro_autor (
    id_libro INT NOT NULL,
    id_autor INT NOT NULL,

    PRIMARY KEY (id_libro, id_autor),
    CONSTRAINT fk_libro_autor_libro
        FOREIGN KEY (id_libro) REFERENCES libro(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_libro_autor_autor
        FOREIGN KEY (id_autor) REFERENCES autor(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Un ejemplar es una COPIA FISICA de un libro. Es lo que se presta.
CREATE TABLE ejemplar (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    id_libro          INT         NOT NULL,
    codigo_inventario VARCHAR(30) NOT NULL UNIQUE,
    estado            VARCHAR(20) NOT NULL DEFAULT 'disponible',
    fecha_alta        DATE        NOT NULL,

    CONSTRAINT fk_ejemplar_libro
        FOREIGN KEY (id_libro) REFERENCES libro(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    -- La lista cerrada de estados vivia SOLO en Python. Cualquiera que entrara
    -- por phpMyAdmin podia escribir 'prestadoo'. Una regla de integridad tiene
    -- que estar en la base.
    CONSTRAINT chk_ejemplar_estado CHECK (
        estado IN ('disponible', 'prestado', 'en_reparacion', 'baja')
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ---------- 4. Prestamos ----------

CREATE TABLE prestamos (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    id_socio          INT  NOT NULL,
    id_ejemplar       INT  NOT NULL,
    fecha_prestamo    DATE NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    fecha_devolucion  DATE NULL,      -- NULL = prestamo activo

    -- Columna generada: vale id_ejemplar mientras el prestamo esta activo y
    -- NULL cuando ya se devolvio. Como los NULL no colisionan en un indice
    -- UNIQUE, la base garantiza que un ejemplar no pueda estar en dos
    -- prestamos activos a la vez. Antes esto se confiaba al codigo Python.
    ejemplar_en_curso INT
        GENERATED ALWAYS AS (IF(fecha_devolucion IS NULL, id_ejemplar, NULL)) STORED,

    CONSTRAINT fk_prestamos_socio
        FOREIGN KEY (id_socio) REFERENCES socio(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_prestamos_ejemplar
        FOREIGN KEY (id_ejemplar) REFERENCES ejemplar(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT uq_prestamo_ejemplar_en_curso UNIQUE (ejemplar_en_curso),

    CONSTRAINT chk_prestamo_vencimiento CHECK (fecha_vencimiento >= fecha_prestamo),
    CONSTRAINT chk_prestamo_devolucion  CHECK (
        fecha_devolucion IS NULL OR fecha_devolucion >= fecha_prestamo
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ---------- 5. Indices ----------
-- No cambian la estructura: son optimizacion para las consultas reales
-- del sistema. Estan elegidos mirando los WHERE y ORDER BY que ejecuta
-- la aplicacion, no puestos "por las dudas".

-- Ordenamiento del catalogo (ORDER BY titulo).
-- Aclaracion: NO sirve para LIKE '%texto%' porque el comodin va adelante.
-- Para eso esta el FULLTEXT de mas abajo.
CREATE INDEX idx_libro_titulo   ON libro(titulo);
CREATE INDEX idx_libro_subgenero ON libro(id_subgenero);
CREATE INDEX idx_libro_editorial ON libro(id_editorial);

-- Busqueda por substring de titulo: MATCH ... AGAINST usa este indice,
-- LIKE '%x%' no puede usar ninguno.
CREATE FULLTEXT INDEX ftx_libro_titulo ON libro(titulo);

-- ORDER BY apellido, nombre del padron de socios.
CREATE INDEX idx_socio_apellido_nombre ON socio(apellido, nombre);
CREATE INDEX idx_autor_apellido_nombre ON autor(apellido, nombre);

-- COMPUESTOS: son las dos consultas mas frecuentes del sistema.
--   "esta prestado este ejemplar?"  -> WHERE id_ejemplar = ? AND fecha_devolucion IS NULL
--   "cuantos activos tiene el socio?" -> WHERE id_socio = ? AND fecha_devolucion IS NULL
-- Un indice solo sobre fecha_devolucion tiene baja selectividad y casi no ayuda.
CREATE INDEX idx_prestamos_ejemplar_activo ON prestamos(id_ejemplar, fecha_devolucion);
CREATE INDEX idx_prestamos_socio_activo    ON prestamos(id_socio, fecha_devolucion);

-- Listado de vencidos del panel de estadisticas.
CREATE INDEX idx_prestamos_vencimiento ON prestamos(fecha_devolucion, fecha_vencimiento);

-- "que copias disponibles hay de este titulo?"
CREATE INDEX idx_ejemplar_libro_estado ON ejemplar(id_libro, estado);
