import webview
from flask import Flask, render_template, send_file
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

            if db.agregar_libro(titulo, ruta_archivo, autor, portada_path, generos, sinopsis):
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
            'ultimo_cfi': l[8], 'sinopsis': l[9]
        }
    return render_template('index.html', current_book=current_book)

@app.route('/library')
def library():
    """
    Muestra la página de la biblioteca con todos los libros.
    """
    libros_tuplas = db.obtener_libros()
    # Convertimos la lista de tuplas a una lista de diccionarios para Jinja2
    libros = [{
        'id': l[0], 'titulo': l[1], 'ruta': l[2], 'es_favorito': l[3],
        'progreso': l[4], 'autor': l[5], 'portada': l[6], 'genero': l[7], 'ultimo_cfi': l[8]
    } for l in libros_tuplas]
    return render_template('library.html', libros=libros)

@app.route('/read/<int:book_id>')
def read_book(book_id):
    """
    Muestra la interfaz de lectura para un libro específico.
    """
    l = db.obtener_libro(book_id)
    if l:
        libro = {'id': l[0], 'titulo': l[1], 'ruta': l[2], 'es_favorito': l[3], 
                 'progreso': l[4], 'autor': l[5], 'portada': l[6], 'genero': l[7], 'ultimo_cfi': l[8]}
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