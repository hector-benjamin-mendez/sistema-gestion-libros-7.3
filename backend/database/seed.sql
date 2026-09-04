-- ============================================================
-- Datos de prueba del Sistema de Gestion Bibliotecaria
-- Idempotente: se puede correr las veces que haga falta.
--
-- El seed incluye a proposito el caso exacto de la correccion 3:
-- Augusto pide una copia de IT el 23, la devuelve el 26 rota, la
-- devolucion queda registrada con su estado y el socio queda suspendido.
-- Es el escenario que hay que poder mostrar funcionando.
-- ============================================================

SET NAMES utf8mb4;

USE biblioteca;

-- Limpieza en orden inverso a las dependencias
DELETE FROM prestamos;
DELETE FROM titulo_autor;
DELETE FROM libro;
DELETE FROM titulo;
DELETE FROM socio;
DELETE FROM rango;
DELETE FROM autor;
DELETE FROM editorial;
DELETE FROM grupo_editorial;
DELETE FROM estado;
DELETE FROM idioma;
DELETE FROM genero;


-- ---------- Catalogo ----------

INSERT INTO genero (id, nombre) VALUES
    (1, 'Ficción'),
    (2, 'Terror'),
    (3, 'Ensayo'),
    (4, 'Infantil');

INSERT INTO idioma (id, nombre) VALUES
    (1, 'Español'),
    (2, 'Inglés');

-- Solo 'disponible' habilita el prestamo. El resto no.
INSERT INTO estado (id, nombre, permite_prestamo, descripcion) VALUES
    (1, 'disponible',    1, 'En el estante, se puede prestar.'),
    (2, 'prestado',      0, 'Lo tiene un socio.'),
    (3, 'en_reparacion', 0, 'En encuadernación o arreglo.'),
    (4, 'dañado',        0, 'Volvió roto de un préstamo. No se presta hasta repararlo.'),
    (5, 'extraviado',    0, 'No se sabe dónde está.'),
    (6, 'baja',          0, 'Retirado definitivamente del inventario.');

INSERT INTO grupo_editorial (id, nombre) VALUES
    (1, 'Grupo Planeta'),
    (2, 'Penguin Random House');

INSERT INTO editorial (id, nombre, direccion, fecha_fundacion, id_grupo_editorial) VALUES
    (1, 'Minotauro',      'Av. Independencia 1668, CABA', '1955-01-01', 1),
    (2, 'Emecé',          'Av. Independencia 1668, CABA', '1939-01-01', 1),
    (3, 'Debate',          NULL,                           NULL,        2),
    (4, 'Alfaguara',      'Humberto I 555, CABA',         '1964-01-01', 2),
    -- Sin grupo editorial: asi se ve que el alta por texto puede crear
    -- una editorial sin obligar a completar el grupo (correccion 5).
    (5, 'Plaza & Janés',   NULL,                           NULL,        NULL);

INSERT INTO autor (id, nombre, apellido, fecha_nacimiento, fecha_fallecimiento, nacionalidad) VALUES
    (1, 'Frank',       'Herbert', '1920-10-08', '1986-02-11', 'Estadounidense'),
    (2, 'Ursula K.',   'Le Guin', '1929-10-21', '2018-01-22', 'Estadounidense'),
    (3, 'Jorge Luis',  'Borges',  '1899-08-24', '1986-06-14', 'Argentina'),
    (4, 'Carl',        'Sagan',   '1934-11-09', '1996-12-20', 'Estadounidense'),
    (5, 'Ann',         'Druyan',  '1949-06-13',  NULL,        'Estadounidense'),
    (6, 'María Elena', 'Walsh',   '1930-02-01', '2011-01-10', 'Argentina'),
    (7, 'Stephen',     'King',    '1947-09-21',  NULL,        'Estadounidense');

INSERT INTO rango (id, nombre, max_prestamos, dias_prestamo) VALUES
    (1, 'Estándar', 3, 14),
    (2, 'Premium',  5, 21);


-- ---------- Titulos (las OBRAS) ----------

INSERT INTO titulo (id, nombre, id_genero) VALUES
    (1, 'Dune',                              1),
    (2, 'La mano izquierda de la oscuridad', 1),
    (3, 'Ficciones',                         1),
    (4, 'Cosmos',                            3),
    (5, 'Zoo loco',                          4),
    (6, 'IT',                                2);

-- Cosmos tiene dos autores: ejercita la relacion N:M.
INSERT INTO titulo_autor (id_titulo, id_autor) VALUES
    (1, 1),
    (2, 2),
    (3, 3),
    (4, 4),
    (4, 5),
    (5, 6),
    (6, 7);


-- ---------- Libros (las COPIAS FISICAS) ----------
-- Las tres copias de IT comparten ISBN y edicion: son la misma edicion,
-- tres objetos distintos. Eso es exactamente lo que el ISBN UNIQUE del
-- modelo anterior hacia imposible.

INSERT INTO libro (id, id_titulo, id_editorial, isbn, id_estado,
                   edicion, id_idioma, codigo_inventario, fecha_alta) VALUES
    ( 1, 1, 1, '9788445000472', 2, '1', 1, 'INV-000001', '2024-03-10'),
    ( 2, 1, 1, '9788445000472', 1, '1', 1, 'INV-000002', '2024-03-10'),
    ( 3, 2, 1, '9788445076774', 1, '2', 1, 'INV-000003', '2024-05-22'),
    ( 4, 3, 2, '9789500426190', 1, '1', 1, 'INV-000004', '2023-11-05'),
    ( 5, 3, 2, '9789500426190', 3, '1', 1, 'INV-000005', '2023-11-05'),
    ( 6, 4, 3, '9788499892204', 1, '3', 1, 'INV-000006', '2025-01-15'),
    ( 7, 4, 3, '9788499892204', 1, '3', 1, 'INV-000007', '2025-01-15'),
    ( 8, 5, 4,  NULL,           1, '1', 1, 'INV-000008', '2024-08-30'),
    -- La copia que devolvio rota Augusto.
    ( 9, 6, 5, '9788497596718', 4, '2', 1, 'INV-000009', '2023-04-18'),
    (10, 6, 5, '9788497596718', 1, '2', 1, 'INV-000010', '2023-04-18'),
    (11, 6, 5, '9788497596718', 2, '2', 1, 'INV-000011', '2025-07-02');


-- ---------- Socios ----------

INSERT INTO socio (id, nombre, apellido, dni, email, telefono,
                   id_rango, fecha_alta, fecha_baja, suspendido_hasta) VALUES
    (1, 'Lucía',    'Giménez', '38111222', 'lucia.gimenez@mail.com',   '11-4455-6677', 2, '2023-02-14', NULL,         NULL),
    (2, 'Martín',   'Sosa',    '40222333', 'martin.sosa@mail.com',      NULL,          1, '2024-06-01', NULL,         NULL),
    (3, 'Carolina', 'Ferrer',  '35333444', 'carolina.ferrer@mail.com', '11-2233-4455', 1, '2022-09-19', '2025-04-30', NULL),
    -- Suspendido por haber devuelto la copia de IT rota.
    (4, 'Augusto',  'Peralta', '42444555', 'augusto.peralta@mail.com', '11-6677-8899', 1, '2025-03-05', NULL,         '2026-09-26');


-- ---------- Prestamos ----------

INSERT INTO prestamos (id, id_socio, id_libro, fecha_prestamo, fecha_vencimiento,
                       fecha_devolucion, id_estado_devolucion, observaciones) VALUES
    -- Activo y ya vencido: alimenta el listado de vencidos.
    (1, 1, 1, '2026-08-01', '2026-08-22', NULL, NULL, NULL),

    -- Devuelto en condiciones.
    (2, 2, 4, '2026-06-10', '2026-06-24', '2026-06-20', 1, NULL),

    -- EL CASO DE LA CORRECCION 3:
    -- prestado el 23, devuelto el 26 en estado 'dañado' (id 4).
    -- El sistema conserva de que prestamo y de que socio vino el daño.
    (3, 4, 9, '2026-08-23', '2026-09-06', '2026-08-26', 4,
        'Devuelto con la tapa arrancada y hojas sueltas. Se suspende al socio por 30 días.'),

    -- Activo, en fecha.
    (4, 2, 11, '2026-08-28', '2026-09-11', NULL, NULL, NULL);
