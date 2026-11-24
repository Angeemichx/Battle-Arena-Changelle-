"""Sitio movil de Battle Arena (US-30): ranking, ultimas partidas e historial por jugador.

Lee el mismo historial.json que escribe el servidor y reutiliza su logica de ranking,
asi el sitio movil y el juego de escritorio siempre muestran los mismos numeros.
Se adapta a pantallas pequenas (meta viewport + tabla que se desplaza). Puerto 8080.
"""
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template_string, request

from Servidor.adapters.json_historial import JsonHistorial
from Servidor.use_cases.estadisticas import Estadisticas

app = Flask(__name__)

RUTA_HISTORIAL = os.getenv(
    "HISTORIAL_FILE",
    str(Path(__file__).resolve().parent / "Servidor" / "infraestructure" / "data" / "historial.json"),
)

PLANTILLA = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Battle Arena - Ranking</title>
    <style>
        body { font-family: Arial, sans-serif; background: #121212; color: #fff; margin: 0; padding: 16px; }
        h1 { text-align: center; color: #4CAF50; font-size: 1.4em; }
        h2 { color: #4CAF50; font-size: 1.1em; margin-top: 28px; }
        .tabla { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        th, td { padding: 8px; border: 1px solid #333; text-align: center; font-size: .95em; }
        th { background: #1f1f1f; color: #3CAF50; }
        form { display: flex; gap: 8px; margin-top: 8px; }
        input { flex: 1; padding: 10px; border-radius: 6px; border: 1px solid #333; background: #1f1f1f; color: #fff; }
        button { padding: 10px 14px; border: 0; border-radius: 6px; background: #4CAF50; color: #000; font-weight: bold; }
        .vacio { color: #999; text-align: center; margin-top: 12px; }
    </style>
</head>
<body>
    <h1>Battle Arena</h1>

    <h2>Ranking global</h2>
    {% if ranking %}
    <div class="tabla"><table>
        <tr><th>#</th><th>Jugador</th><th>Victorias</th><th>Partidas</th><th>Puntos</th></tr>
        {% for j in ranking %}
        <tr><td>{{ loop.index }}</td><td>{{ j.nombre }}</td><td>{{ j.victorias }}</td><td>{{ j.partidas }}</td><td>{{ j.puntos }}</td></tr>
        {% endfor %}
    </table></div>
    {% else %}<p class="vacio">Aun no hay partidas registradas.</p>{% endif %}

    <h2>Ultimas partidas</h2>
    {% if partidas %}
    <div class="tabla"><table>
        <tr><th>Fecha</th><th>Ganador</th><th>Puntos</th></tr>
        {% for p in partidas %}
        <tr><td>{{ p.fecha }}</td><td>{{ p.ganador }}</td><td>{{ p.puntos }}</td></tr>
        {% endfor %}
    </table></div>
    {% else %}<p class="vacio">Sin partidas todavia.</p>{% endif %}

    <h2>Mi historial</h2>
    <form method="get">
        <input name="usuario" placeholder="Nombre de usuario" value="{{ usuario }}">
        <button type="submit">Ver</button>
    </form>
    {% if usuario %}
        {% if historial %}
        <div class="tabla"><table>
            <tr><th>Fecha</th><th>Resultado</th><th>Puntos</th><th>Rivales</th></tr>
            {% for h in historial %}
            <tr><td>{{ h.fecha }}</td><td>{{ h.resultado }}</td><td>{{ h.puntos }}</td><td>{{ h.rivales|join(', ') }}</td></tr>
            {% endfor %}
        </table></div>
        {% else %}<p class="vacio">No hay partidas para "{{ usuario }}".</p>{% endif %}
    {% endif %}
</body>
</html>
"""


def _fecha_legible(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return str(iso or "")


def _cargar_historial(ruta: str):
    """Devuelve la lista de partidas; un archivo ausente o danado cuenta como sin partidas."""
    try:
        return JsonHistorial(ruta).todas()
    except (OSError, ValueError):
        return []


def construir_vista(ruta: str, usuario: str = "", limite_partidas: int = 10) -> dict:
    """Arma los datos de la pagina: ranking, ultimas partidas e historial del usuario pedido."""
    historial = _cargar_historial(ruta)

    class _Repo:  # entrega el historial ya leido para no abrir el archivo varias veces
        def todas(self):
            return historial

    stats = Estadisticas(_Repo())
    partidas = []
    for p in reversed(historial[-limite_partidas:]):
        jugadores = p.get("jugadores") or [{"puntos": 0}]
        partidas.append({
            "fecha": _fecha_legible(p.get("fecha")),
            "ganador": p.get("ganador") or "Empate",
            "puntos": max(j.get("puntos", 0) for j in jugadores),
        })
    usuario = (usuario or "").strip()
    return {
        "ranking": stats.ranking(),
        "partidas": partidas,
        "usuario": usuario,
        "historial": [dict(h, fecha=_fecha_legible(h["fecha"])) for h in stats.historial(usuario)] if usuario else [],
    }


@app.route("/")
def ranking():
    return render_template_string(PLANTILLA, **construir_vista(RUTA_HISTORIAL, request.args.get("usuario", "")))

@app.route("/jugador/<nombre>")
def jugador(nombre):
    hist = []
    for p in reversed(leer()):
        mio = next((j for j in p.get("jugadores", []) if j["nombre"].lower() == nombre.lower()), None)
        if mio:
            hist.append({
                "fecha": p["fecha"][:16].replace("T", " "),
                "puntos": mio["puntos"],
                "resultado": "Empate" if not p.get("ganador")
                             else "Victoria" if p["ganador"].lower() == nombre.lower() else "Derrota",
            })
    return render_template_string(HTML_JUGADOR, nombre=nombre, historial=hist[:30])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)  # puerto 8080 para abrirlo desde el celular