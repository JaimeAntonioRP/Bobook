import sqlite3

class Database:
    def __init__(self, db_name="biblioteca.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.crear_tablas()

    def crear_tablas(self):
        # Creamos una tabla para guardar la info de los libros
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS libros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT,
                ruta_archivo TEXT UNIQUE,
                es_favorito INTEGER DEFAULT 0,
                progreso INTEGER DEFAULT 0,
                autor TEXT DEFAULT 'Autor Desconocido',
                portada TEXT,
                genero TEXT
            )
        """)
        # Intentamos agregar las columnas por si la base de datos ya existía de antes
        try:
            self.cursor.execute("ALTER TABLE libros ADD COLUMN autor TEXT DEFAULT 'Autor Desconocido'")
            self.cursor.execute("ALTER TABLE libros ADD COLUMN portada TEXT")
            self.cursor.execute("ALTER TABLE libros ADD COLUMN genero TEXT")
        except sqlite3.OperationalError:
            pass # Las columnas ya existen
        self.conn.commit()

    def agregar_libro(self, titulo, ruta, autor="Autor Desconocido", portada=None, genero=""):
        try:
            self.cursor.execute("INSERT INTO libros (titulo, ruta_archivo, autor, portada, genero) VALUES (?, ?, ?, ?, ?)", (titulo, ruta, autor, portada, genero))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # El libro ya existe (la ruta es única)
            return False

    def obtener_libros(self):
        self.cursor.execute("SELECT id, titulo, ruta_archivo, es_favorito, progreso, autor, portada, genero FROM libros")
        return self.cursor.fetchall()

    def obtener_libro(self, id_libro):
        self.cursor.execute("SELECT id, titulo, ruta_archivo, es_favorito, progreso, autor, portada, genero FROM libros WHERE id = ?", (id_libro,))
        return self.cursor.fetchone()

    def eliminar_libro(self, id_libro):
        self.cursor.execute("DELETE FROM libros WHERE id = ?", (id_libro,))
        self.conn.commit()

    def alternar_favorito(self, libro_id, estado_actual):
        nuevo_estado = 0 if estado_actual == 1 else 1
        self.cursor.execute("UPDATE libros SET es_favorito = ? WHERE id = ?", (nuevo_estado, libro_id))
        self.conn.commit()
        return nuevo_estado

# Instancia global para usar en la app
db = Database()