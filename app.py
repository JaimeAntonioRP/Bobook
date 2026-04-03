import webview
from flask import Flask, render_template, send_file, request
import sys
import threading
import os
import uuid
from database import db
import ebooklib
from ebooklib import epub

# Configuramos Flask para que busque el HTML en la carpeta templates
# static_folder es para CSS/JS/Imágenes si agregamos luego
app = Flask(__name__, static_folder='./static', template_folder='./templates')

# --- API para comunicar Python y JS ---
class Api:
    def add_book(self):
        """
        Abre un diálogo para seleccionar un archivo EPUB, lo procesa y
        lo agrega a la base de datos.
        """
        file_types = ('Archivos EPUB (*.epub)',)
        # Usamos webview.windows[0] para acceder a la ventana principal
        result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)

        if result:
            ruta_archivo = result[0]
            
            titulo = os.path.splitext(os.path.basename(ruta_archivo))[0]
            autor = "Autor Desconocido"
            generos = ""
            portada_path = None
            sinopsis = ""
            idioma = ""

            try:
                book = epub.read_epub(ruta_archivo)
                # Intenta obtener el título de los metadatos
                titles = book.get_metadata('DC', 'title')
                if titles:
                    titulo = titles[0][0]

                # Obtener Autor
                creators = book.get_metadata('DC', 'creator')
                if creators:
                    autor = creators[0][0]

                # Obtener Género
                subjects = book.get_metadata('DC', 'subject')
                if subjects:
                    generos = ", ".join([s[0] for s in subjects])

                # Obtener Sinopsis (Descripción)
                descriptions = book.get_metadata('DC', 'description')
                if descriptions:
                    sinopsis = descriptions[0][0]

                # Obtener Idioma
                languages = book.get_metadata('DC', 'language')
                if languages:
                    idioma = languages[0][0]

                # Obtener Portada
                covers = list(book.get_items_of_type(ebooklib.ITEM_COVER))
                if not covers:
                    # Alternativa si no está etiquetada específicamente como ITEM_COVER
                    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
                        if 'cover' in item.get_name().lower() or 'portada' in item.get_name().lower():
                            covers = [item]
                            break
                
                if covers:
                    cover_item = covers[0]
                    cover_data = cover_item.get_content()
                    
                    covers_dir = os.path.join(app.static_folder, 'covers')
                    os.makedirs(covers_dir, exist_ok=True)
                    
                    ext = os.path.splitext(cover_item.get_name())[1]
                    if not ext: ext = '.jpg'
                    cover_filename = f"cover_{uuid.uuid4().hex}{ext}"
                    cover_filepath = os.path.join(covers_dir, cover_filename)
                    
                    with open(cover_filepath, 'wb') as f:
                        f.write(cover_data)
                        
                    portada_path = f"covers/{cover_filename}"

            except Exception as e:
                # Si hay un error al leer el EPUB, usa el nombre del archivo
                print(f"Error al procesar metadatos de EPUB: {e}")

            if db.agregar_libro(titulo, ruta_archivo, autor, portada_path, generos, sinopsis, idioma):
                 print(f"Libro agregado: {titulo}")

    def delete_book(self, book_id):
        """Elimina un libro de la base de datos y su portada asociada"""
        db.cursor.execute("SELECT portada FROM libros WHERE id = ?", (book_id,))
        res = db.cursor.fetchone()
        if res and res[0]:
            cover_path = os.path.join(app.static_folder, res[0])
            if os.path.exists(cover_path):
                try:
                    os.remove(cover_path)
                except Exception as e:
                    print(f"No se pudo eliminar la portada: {e}")
        
        db.eliminar_libro(book_id)

    def update_progress(self, book_id, percentage, cfi):
        """Guarda el progreso de lectura y la posición exacta (CFI) en la BD"""
        db.actualizar_progreso(book_id, percentage, cfi)

    def toggle_favorite(self, book_id, current_status):
        """Alterna el estado de favorito de un libro."""
        new_status = db.alternar_favorito(book_id, int(current_status))
        print(f"Libro ID {book_id} cambiado a favorito: {new_status}")
        return new_status

    def search_books(self, query):
        """Busca libros por título, autor o género para la barra de búsqueda global"""
        if not query:
            return []
        q = f"%{query}%"
        db.cursor.execute("""
            SELECT id, titulo, autor, portada 
            FROM libros 
            WHERE titulo LIKE ? OR autor LIKE ? OR genero LIKE ? 
            LIMIT 6
        """, (q, q, q))
        res = db.cursor.fetchall()
        return [{'id': r[0], 'titulo': r[1], 'autor': r[2], 'portada': r[3]} for r in res]

# --- SISTEMA DE TRADUCCIONES ---
TRANSLATIONS = {
    'es': {
        'Home': 'Inicio',
        'Library': 'Biblioteca',
        'Favorites': 'Favoritos',
        'My Lists': 'Mis Listas',
        'Store': 'Tienda',
        'Filters': 'Filtros',
        'Non-Fiction': 'No Ficción',
        'Technology': 'Tecnología',
        'Settings': 'Configuración',
        'Search your library, authors, or genres...': 'Busca en tu biblioteca, autores o géneros...',
        'Premium Plan': 'Plan Premium',
        'Library Synced': 'Biblioteca Sincronizada',
        'No se encontraron coincidencias': 'No se encontraron coincidencias',
        'Recently Added': 'Añadidos Recientemente',
        'Manage Library': 'Gestionar Biblioteca',
        'Your Favorites': 'Tus Favoritos',
        'View All': 'Ver Todo',
        'Aún no tienes libros favoritos. ¡Marca algunos con una estrella en tu biblioteca!': 'Aún no tienes libros favoritos. ¡Marca algunos con una estrella en tu biblioteca!',
        'Aún no has agregado ningún libro a tu biblioteca.': 'Aún no has agregado ningún libro a tu biblioteca.',
        'Mi Biblioteca': 'Mi Biblioteca',
        'Mis Favoritos': 'Mis Favoritos',
        'Agregar Libro': 'Agregar Libro',
        'Tu biblioteca está vacía': 'Tu biblioteca está vacía',
        'Haz clic en "Agregar Libro" para empezar a construir tu colección.': 'Haz clic en "Agregar Libro" para empezar a construir tu colección.',
        'Eliminar libro': 'Eliminar libro',
        '¿Estás seguro? Esta acción no se puede deshacer y perderás tu progreso.': '¿Estás seguro? Esta acción no se puede deshacer y perderás tu progreso.',
        'Cancelar': 'Cancelar',
        'Sí, eliminar': 'Sí, eliminar',
        'Quitar de favoritos': 'Quitar de favoritos',
        'Añadir a favoritos': 'Añadir a favoritos',
        'Volver': 'Volver',
        'Progreso de lectura': 'Progreso de lectura',
        'Sinopsis': 'Sinopsis',
        'No hay sinopsis disponible para este libro.': 'No hay sinopsis disponible para este libro.',
        'Continuar Leyendo': 'Continuar Leyendo',
        'Comenzar a Leer': 'Comenzar a Leer',
        'Configuración': 'Configuración',
        'Apariencia Global': 'Apariencia Global',
        'Modo de Interfaz': 'Modo de Interfaz',
        'Claro': 'Claro',
        'Oscuro': 'Oscuro',
        'Color de Acento (Primario)': 'Color de Acento (Primario)',
        'Color personalizado': 'Color personalizado',
        'Cuadrícula de la Biblioteca': 'Cuadrícula de la Biblioteca',
        'Tamaño de las Portadas': 'Tamaño de las Portadas',
        'Pequeño': 'Pequeño',
        'Mediano': 'Mediano',
        'Grande': 'Grande',
        'General': 'General',
        'Idioma de la Interfaz': 'Idioma de la Interfaz',
        '* La aplicación recargará para aplicar los cambios de configuración al instante.': '* La aplicación recargará para aplicar los cambios de configuración al instante.',
        'Leyendo': 'Leyendo',
        'Índice de Capítulos': 'Índice de Capítulos',
        'Regresar': 'Regresar',
        'Configuración de lectura': 'Configuración de lectura',
        'Pantalla Completa': 'Pantalla Completa',
        'Cargando contenido...': 'Cargando contenido...',
        'Calculando...': 'Calculando...',
        'Índice': 'Índice',
        'Este libro no tiene índice.': 'Este libro no tiene índice.',
        'Apariencia': 'Apariencia',
        'Diseño': 'Diseño',
        '1 Columna': '1 Columna',
        '2 Columnas': '2 Columnas',
        'Fuente': 'Fuente',
        'Serif (Recomendadas)': 'Serif (Recomendadas)',
        'Sans-Serif (Modernas)': 'Sans-Serif (Modernas)',
        'Otras': 'Otras',
        'Tamaño de texto': 'Tamaño de texto',
        'Tema': 'Tema',
        'Sepia': 'Sepia',
        'Detalles': 'Detalles'
    },
    'en': {
        'Home': 'Home', 'Library': 'Library', 'Favorites': 'Favorites', 'My Lists': 'My Lists', 'Store': 'Store', 
        'Filters': 'Filters', 'Non-Fiction': 'Non-Fiction', 'Technology': 'Technology', 'Settings': 'Settings',
        'Search your library, authors, or genres...': 'Search your library, authors, or genres...', 'Premium Plan': 'Premium Plan',
        'Library Synced': 'Library Synced', 'No se encontraron coincidencias': 'No matches found',
        'Recently Added': 'Recently Added', 'Manage Library': 'Manage Library', 'Your Favorites': 'Your Favorites', 'View All': 'View All',
        'Aún no tienes libros favoritos. ¡Marca algunos con una estrella en tu biblioteca!': 'You have no favorite books yet. Star some in your library!',
        'Aún no has agregado ningún libro a tu biblioteca.': 'You haven\'t added any books to your library yet.',
        'Mi Biblioteca': 'My Library', 'Mis Favoritos': 'My Favorites', 'Agregar Libro': 'Add Book',
        'Tu biblioteca está vacía': 'Your library is empty', 'Haz clic en "Agregar Libro" para empezar a construir tu colección.': 'Click "Add Book" to start building your collection.',
        'Eliminar libro': 'Delete book', '¿Estás seguro? Esta acción no se puede deshacer y perderás tu progreso.': 'Are you sure? This action cannot be undone and you will lose your progress.',
        'Cancelar': 'Cancel', 'Sí, eliminar': 'Yes, delete', 'Quitar de favoritos': 'Remove from favorites', 'Añadir a favoritos': 'Add to favorites',
        'Volver': 'Go Back', 'Progreso de lectura': 'Reading progress', 'Sinopsis': 'Synopsis', 'No hay sinopsis disponible para este libro.': 'No synopsis available for this book.',
        'Continuar Leyendo': 'Continue Reading', 'Comenzar a Leer': 'Start Reading', 'Configuración': 'Settings', 'Apariencia Global': 'Global Appearance',
        'Modo de Interfaz': 'Interface Mode', 'Claro': 'Light', 'Oscuro': 'Dark', 'Color de Acento (Primario)': 'Accent Color (Primary)',
        'Color personalizado': 'Custom color', 'Cuadrícula de la Biblioteca': 'Library Grid', 'Tamaño de las Portadas': 'Cover Size',
        'Pequeño': 'Small', 'Mediano': 'Medium', 'Grande': 'Large', 'General': 'General', 'Idioma de la Interfaz': 'Interface Language',
        '* La aplicación recargará para aplicar los cambios de configuración al instante.': '* The application will reload to apply configuration changes instantly.',
        'Leyendo': 'Reading', 'Índice de Capítulos': 'Table of Contents', 'Regresar': 'Go Back', 'Configuración de lectura': 'Reading settings',
        'Pantalla Completa': 'Fullscreen', 'Cargando contenido...': 'Loading content...', 'Calculando...': 'Calculating...', 'Índice': 'Contents',
        'Este libro no tiene índice.': 'This book has no table of contents.', 'Apariencia': 'Appearance', 'Diseño': 'Layout', '1 Columna': '1 Column',
        '2 Columnas': '2 Columns', 'Fuente': 'Font', 'Serif (Recomendadas)': 'Serif (Recommended)', 'Sans-Serif (Modernas)': 'Sans-Serif (Modern)',
        'Otras': 'Other', 'Tamaño de texto': 'Text size', 'Tema': 'Theme', 'Sepia': 'Sepia', 'Detalles': 'Details'
    }
}

@app.context_processor
def inject_translations():
    lang = request.cookies.get('app_lang', 'es')
    def t(key): return TRANSLATIONS.get(lang, TRANSLATIONS['es']).get(key, key)
    return dict(t=t, current_lang=lang)

# --- RUTAS DE LA APP ---

@app.route('/')
def home():
    """
    Esta función se ejecuta al abrir la app.
    Carga tu diseño 'index.html'.
    """
    l = db.obtener_libro_actual()
    current_book = None
    if l:
        current_book = {
            'id': l[0], 'titulo': l[1], 'ruta': l[2], 'es_favorito': l[3],
            'progreso': l[4], 'autor': l[5], 'portada': l[6], 'genero': l[7], 
            'ultimo_cfi': l[8], 'sinopsis': l[9], 'idioma': l[10]
        }
    
    favs_tuplas = db.obtener_favoritos(limite=5) # Pasamos hasta 5 favoritos al inicio
    favoritos = [{
        'id': l[0], 'titulo': l[1], 'ruta': l[2], 'es_favorito': l[3],
        'progreso': l[4], 'autor': l[5], 'portada': l[6], 'genero': l[7], 'ultimo_cfi': l[8], 'idioma': l[9]
    } for l in favs_tuplas]

    recientes_tuplas = db.obtener_recientes(limite=3)
    recientes = [{
        'id': l[0], 'titulo': l[1], 'ruta': l[2], 'es_favorito': l[3],
        'progreso': l[4], 'autor': l[5], 'portada': l[6], 'genero': l[7], 'ultimo_cfi': l[8], 'idioma': l[9]
    } for l in recientes_tuplas]

    return render_template('index.html', current_book=current_book, favoritos=favoritos, recientes=recientes)

@app.route('/library')
def library():
    """
    Muestra la página de la biblioteca con todos los libros.
    """
    libros_tuplas = db.obtener_libros()
    # Convertimos la lista de tuplas a una lista de diccionarios para Jinja2
    libros = [{
        'id': l[0], 'titulo': l[1], 'ruta': l[2], 'es_favorito': l[3],
        'progreso': l[4], 'autor': l[5], 'portada': l[6], 'genero': l[7], 'ultimo_cfi': l[8], 'idioma': l[9]
    } for l in libros_tuplas]
    return render_template('library.html', libros=libros)

@app.route('/favorites')
def favorites():
    """
    Muestra la página de la biblioteca pero con el filtro de favoritos ya activado.
    """
    libros_tuplas = db.obtener_libros()
    libros = [{
        'id': l[0], 'titulo': l[1], 'ruta': l[2], 'es_favorito': l[3],
        'progreso': l[4], 'autor': l[5], 'portada': l[6], 'genero': l[7], 'ultimo_cfi': l[8], 'idioma': l[9]
    } for l in libros_tuplas]
    return render_template('library.html', libros=libros, init_favorites=True)

@app.route('/book/<int:book_id>')
def book_details(book_id):
    """
    Muestra la información detallada de un libro antes de leerlo.
    """
    l = db.obtener_libro(book_id)
    if l:
        libro = {'id': l[0], 'titulo': l[1], 'ruta': l[2], 'es_favorito': l[3], 
                 'progreso': l[4], 'autor': l[5], 'portada': l[6], 'genero': l[7], 'ultimo_cfi': l[8], 'sinopsis': l[9], 'idioma': l[10]}
        return render_template('book_details.html', libro=libro)
    return "Libro no encontrado", 404

@app.route('/settings')
def settings():
    """
    Muestra la página de preferencias globales de la app.
    """
    return render_template('settings.html')

@app.route('/read/<int:book_id>')
def read_book(book_id):
    """
    Muestra la interfaz de lectura para un libro específico.
    """
    l = db.obtener_libro(book_id)
    if l:
        libro = {'id': l[0], 'titulo': l[1], 'ruta': l[2], 'es_favorito': l[3], 
                 'progreso': l[4], 'autor': l[5], 'portada': l[6], 'genero': l[7], 'ultimo_cfi': l[8], 'sinopsis': l[9], 'idioma': l[10]}
        return render_template('reader.html', libro=libro)
    return "Libro no encontrado", 404

@app.route('/serve_book/<int:book_id>.epub')
def serve_book(book_id):
    """Sirve el archivo EPUB directamente para que epub.js pueda leerlo."""
    l = db.obtener_libro(book_id)
    if l and l[2] and os.path.exists(l[2]):
        return send_file(l[2], mimetype='application/epub+zip')
    return "Archivo no encontrado", 404

# --- CONFIGURACIÓN DE ARRANQUE ---

def start_server():
    """Inicia el servidor Flask en segundo plano"""
    # use_reloader=False es importante para evitar problemas con pywebview
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    api = Api()
    # 1. Iniciamos el servidor Flask en un hilo separado
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()

    # 2. Creamos la ventana nativa de escritorio
    window = webview.create_window(
        title='Reader Pro', 
        url='http://127.0.0.1:5000',
        width=1200,
        height=800,
        resizable=True,
        text_select=False, # Evita que el usuario seleccione texto como en una web
        js_api=api # Exponemos la clase Api a JavaScript
    )
    
    # 3. Iniciamos la app
    webview.start()