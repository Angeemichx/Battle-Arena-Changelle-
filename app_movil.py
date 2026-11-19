from flask import Flask, render_template_string
import os
import json
from pathlib import Path

app = Flask(__name__)

@app.route('/')

def ranking(): #leer el archivo del historial que se genera desde el servidor
    base_dir = Path(__file__).resolve().parent
    ruta = base_dir / 'Servidor' / 'infraestructure' / 'data' / 'historial.json'
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)

    else:
        datos = []  # Si el archivo no existe, se crea una lista vacía

    #Adaptar html para mostrar en móvil
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Battle Arena - Ranking</title>
        <style>
            body {font-family: Arial, sans-serif; background: #121212; color:white; padding:20px; }
            h1 {text-align: center; color: #4CAF50;}
            table {width: 100%; border-collapse: collapse; margin-top: 20px;}
            th, td {padding: 10px; border: 1px solid #333;text-align: center;}
            th {background: #1f1f1f; color: #3CAF50;}
        </style>
    </head>

    <body>
        <h1>Ranking de Jugadores de Battle Arena</h1>
        <table>
            <tr><th>Partida</th><th>Ganador</th><th>Puntos</th></tr>
            {% for partida in partidas %}
            <tr>
                <td>{{ partida.fecha }}</td>
                <td>{{ partida.ganador }}</td>
                <td>{{ partida.puntaje }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html, partidas=datos)

if __name__ == '__main__':
    #Abrir el puerto 8080
    app.run(host='0.0.0.0', port=8080)

            