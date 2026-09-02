-- ============================================================
-- Datos de prueba del Sistema de Gestion Bibliotecaria
-- Idempotente: se puede correr las veces que haga falta.
-- ============================================================

USE biblioteca;

-- Limpieza en orden inverso a las dependencias
DELETE FROM prestamos;
DELETE FROM libro_autor;
DELETE FROM ejemplar;
DELETE FROM libro;
DELETE FROM socio;
DELETE FROM rango;
DELETE FROM autor;
DELETE FROM editorial;
DELETE FROM grupo_editorial;
DELETE FROM subgenero;
DELETE FROM genero;

-- ---------- Catalogo ----------

INSERT INTO genero (id, nombre) VALUES
    (1, 'Ficcion'),
    (2, 'Ensayo'),
    (3, 'Infantil');

INSERT INTO subgenero (id, nombre, id_genero) VALUES
    (1, 'Ciencia Ficcion',        1),
    (2, 'Cuento',                 1),
    (3, 'Divulgacion Cientifica', 2),
    (4, 'Cuento Infantil',        3);

INSERT INTO grupo_editorial (id, nombre) VALUES
    (1, 'Grupo Planeta'),
    (2, 'Penguin Random House');

INSERT INTO editorial (id, nombre, direccion, fecha_fundacion, id_grupo_editorial) VALUES
    (1, 'Minotauro',  'Av. Independencia 1668, CABA', '1955-01-01', 1),
    (2, 'Emece',      'Av. Independencia 1668, CABA', '1939-01-01', 1),
    (3, 'Debate',     NULL,                            NULL,        2),
    (4, 'Alfaguara',  'Humberto I 555, CABA',         '1964-01-01', 2);

INSERT INTO autor (id, nombre, apellido, fecha_nacimiento, fecha_fallecimiento, nacionalidad) VALUES
    (1, 'Frank',        'Herbert',  '1920-10-08', '1986-02-11', 'Estadounidense'),
    (2, 'Ursula K.',    'Le Guin',  '1929-10-21', '2018-01-22', 'Estadounidense'),
    (3, 'Jorge Luis',   'Borges',   '1899-08-24', '1986-06-14', 'Argentina'),
    (4, 'Carl',         'Sagan',    '1934-11-09', '1996-12-20', 'Estadounidense'),
    (5, 'Ann',          'Druyan',   '1949-06-13', NULL,         'Estadounidense'),
    (6, 'Maria Elena',  'Walsh',    '1930-02-01', '2011-01-10', 'Argentina');

INSERT INTO rango (id, nombre, max_prestamos, dias_prestamo) VALUES
    (1, 'Estandar', 3, 14),
    (2, 'Premium',  5, 21);

-- ---------- Libros ----------

INSERT INTO libro (id, titulo, isbn, id_subgenero, id_editorial,
                   fecha_publicacion, idioma, numero_edicion) VALUES
    (1, 'Dune',                             '9788445000472', 1, 1, '1965-08-01', 'Espanol', '1'),
    (2, 'La mano izquierda de la oscuridad','9788445076774', 1, 1, '1969-03-01', 'Espanol', '2'),
    (3, 'Ficciones',                        '9789500426190', 2, 2, '1944-01-01', 'Espanol', '1'),
    (4, 'Cosmos',                           '9788499892204', 3, 3, '1980-09-28', 'Espanol', '3'),
    (5, 'Zoo loco',                          NULL,           4, 4, '1964-01-01', 'Espanol', '1');

-- Cosmos tiene dos autores: ejercita la relacion N:M
INSERT INTO libro_autor (id_libro, id_autor) VALUES
    (1, 1),
    (2, 2),
    (3, 3),
    (4, 4),
    (4, 5),
    (5, 6);

-- ---------- Ejemplares ----------

INSERT INTO ejemplar (id, id_libro, codigo_inventario, estado, fecha_alta) VALUES
    (1, 1, 'INV-0001', 'prestado',      '2024-03-10'),
    (2, 1, 'INV-0002', 'disponible',    '2024-03-10'),
    (3, 2, 'INV-0003', 'disponible',    '2024-05-22'),
    (4, 3, 'INV-0004', 'disponible',    '2023-11-05'),
    (5, 3, 'INV-0005', 'en_reparacion', '2023-11-05'),
    (6, 4, 'INV-0006', 'disponible',    '2025-01-15'),
    (7, 4, 'INV-0007', 'disponible',    '2025-01-15'),
    (8, 5, 'INV-0008', 'disponible',    '2024-08-30');

-- ---------- Socios ----------

INSERT INTO socio (id, nombre, apellido, dni, email, telefono,
                   id_rango, fecha_alta, fecha_baja) VALUES
    (1, 'Lucia',    'Gimenez', '38111222', 'lucia.gimenez@mail.com',  '11-4455-6677', 2, '2023-02-14', NULL),
    (2, 'Martin',   'Sosa',    '40222333', 'martin.sosa@mail.com',    NULL,           1, '2024-06-01', NULL),
    (3, 'Carolina', 'Ferrer',  '35333444', 'carolina.ferrer@mail.com','11-2233-4455', 1, '2022-09-19', '2025-04-30');

-- ---------- Prestamos ----------
-- Uno activo (sin fecha_devolucion) y uno ya devuelto.

INSERT INTO prestamos (id, id_socio, id_ejemplar, fecha_prestamo,
                       fecha_vencimiento, fecha_devolucion) VALUES
    (1, 1, 1, '2026-08-01', '2026-08-22', NULL),
    (2, 2, 4, '2026-06-10', '2026-06-24', '2026-06-20');
