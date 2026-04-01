import webview
from flask import Flask, render_template
import sys
import threading
import os

# Configuramos Flask para que busque el HTML en la carpeta templates
# static_folder es para CSS/JS/Imágenes si agregamos luego
app = Flask(__name__, static_folder='./static', template_folder='./templates')

# --- RUTAS DE LA APP ---

@app.route('/')
def home():
    """
    Esta función se ejecuta al abrir la app.
    Carga tu diseño 'index.html'.
    """
    # Aquí más adelante enviaremos los libros de la base de datos al HTML
    return render_template('index.html')

# --- CONFIGURACIÓN DE ARRANQUE ---

def start_server():
    """Inicia el servidor Flask en segundo plano"""
    app.run(host='127.0.0.1', port=5000, debug=False)

if __name__ == '__main__':
    # 1. Iniciamos el servidor Flask en un hilo separado
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()

    # 2. Creamos la ventana nativa de escritorio
    webview.create_window(
        title='Reader Pro', 
        url='http://127.0.0.1:5000',
        width=1200,
        height=800,
        resizable=True,
        text_select=False # Evita que el usuario seleccione texto como en una web
    )
    
    # 3. Iniciamos la app
    webview.start()