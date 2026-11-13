from datetime import datetime, timezone

class Estadisticas:
    def __init__(self, repo):
        self.repo = repo

    def registrar_partida(self, jugadores: list[dict], duracion_seg: int):
        """jugadores: [{'nombre': str, 'puntos': int}, ...]"""
        if len(jugadores) < 1:
            return
        orden = sorted(jugadores, key=lambda j: j["puntos"], reverse=True)
        empate = len(orden) > 1 and orden[0]["puntos"] == orden[1]["puntos"]
        self.repo.agregar({
            "fecha": datetime.now(timezone.utc).isoformat(),
            "duracion": int(duracion_seg),
            "ganador": None if empate else orden[0]["nombre"],
            "jugadores": orden,
        })

    def ranking(self, limite: int = 10) -> list[dict]:
        acc: dict[str, dict] = {}
        for p in self.repo.todas():
            for j in p["jugadores"]:
                a = acc.setdefault(j["nombre"], {"nombre": j["nombre"], "partidas": 0,
                                                 "victorias": 0, "puntos": 0})
                a["partidas"] += 1
                a["puntos"] += j["puntos"]
                if p["ganador"] == j["nombre"]:
                    a["victorias"] += 1
        lista = sorted(acc.values(), key=lambda a: (a["victorias"], a["puntos"]), reverse=True)
        return lista[:limite]

    def historial(self, username: str, limite: int = 20) -> list[dict]:
        u = username.strip().lower()
        salida = []
        for p in reversed(self.repo.todas()):
            mio = next((j for j in p["jugadores"] if j["nombre"].lower() == u), None)
            if mio:
                rivales = [j["nombre"] for j in p["jugadores"] if j is not mio]
                salida.append({
                    "fecha": p["fecha"], "duracion": p["duracion"],
                    "puntos": mio["puntos"], "rivales": rivales,
                    "resultado": ("empate" if p["ganador"] is None
                                  else "victoria" if p["ganador"].lower() == u else "derrota"),
                })
            if len(salida) >= limite:
                break
        return salida