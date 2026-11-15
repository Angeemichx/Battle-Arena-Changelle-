"""
Sincronizacion de jugadores remotos (US-11 / US-13).

El servidor entrega la lista de jugadores ordenada por llegada, y cada cliente es uno de ellos.
Estas funciones puras (sin pygame ni red) deciden a que jugador local corresponde cada
jugador del servidor, usando el id de cada uno y NO la posicion en la lista.
"""
from __future__ import annotations

import math
import re
from typing import Callable, Iterable, Mapping

_HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def _entero(valor) -> int | None:
    """Entero valido (no bool) o None."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    return int(valor)


def _ordenados(jugadores_servidor: Iterable[Mapping]) -> list[Mapping]:
    validos = [d for d in jugadores_servidor if isinstance(d, Mapping) and _entero(d.get("id")) is not None]
    return sorted(validos, key=lambda d: _entero(d["id"]))


def otros_jugadores(jugadores_servidor: Iterable[Mapping], mi_id: int | None) -> list[Mapping]:
    """
    Los jugadores del servidor que NO soy yo, ordenados por id.
    Si aun no se quien soy (sin identificar), se asume el comportamiento anterior: yo soy el primero.
    """
    ordenados = _ordenados(jugadores_servidor)
    if mi_id is None or mi_id not in [_entero(d["id"]) for d in ordenados]:
        return ordenados[1:]
    return [d for d in ordenados if _entero(d["id"]) != mi_id]


def asignar_spawns(jugadores_servidor: Iterable[Mapping], mi_id: int | None) -> list[int] | None:
    """
    Indices de punto de salida para [yo, otro1, otro2...], segun el orden de id en el servidor,
    de modo que todos los clientes coloquen a cada jugador en el mismo lugar.
    Devuelve None si aun no sabemos quien somos (sin conexion o sin identificar).
    """
    ordenados = _ordenados(jugadores_servidor)
    ids = [_entero(d["id"]) for d in ordenados]
    if mi_id is None or mi_id not in ids:
        return None
    otros = [i for i in ids if i != mi_id]
    return [ids.index(mi_id)] + [ids.index(i) for i in otros]


def aplicar_estado_remoto(
    jugadores_locales: list[dict],
    jugadores_servidor: Iterable[Mapping],
    mi_id: int | None,
    acciones_remotas: Mapping[int, float],
    ahora: float,
    nombre_color: Callable[[str], str] | None = None,
) -> int:
    """
    Copia nombre, puntos, posicion, color y accion de cada jugador remoto a su casilla local.

    - Salta al propio jugador (id == mi_id).
    - Los demas jugadores del servidor, ordenados por id, ocupan en orden las casillas no locales.
    - Posicion (0, 0) significa "aun no se ha movido": se conserva la de salida.
    - Un color repetido o invalido se ignora (se conserva el ya asignado, sin duplicados).
    Devuelve cuantos jugadores remotos se actualizaron.
    """
    if mi_id is None:
        return 0
    casillas = [j for j in jugadores_locales if not j.get("es_local")]
    remotos = [d for d in _ordenados(jugadores_servidor) if _entero(d["id"]) != mi_id]
    usados = {str(j.get("color", "")).upper() for j in jugadores_locales}
    n = 0
    for casilla, d in zip(casillas, remotos):
        if d.get("nombre"):
            casilla["nombre"] = str(d["nombre"])
        puntos = _entero(d.get("puntaje"))
        if puntos is not None and puntos >= 0:
            casilla["puntos"] = puntos
        x, y = _entero(d.get("x")), _entero(d.get("y"))
        if x is not None and y is not None and (x != 0 or y != 0):
            casilla["objetivo"] = (x, y)
            if "_pos" not in casilla:  # primera muestra: se coloca de inmediato, sin deslizar desde la salida
                casilla["_pos"] = (float(x), float(y))
                casilla["rect"].topleft = (x, y)
        color = d.get("color")
        if isinstance(color, str) and _HEX.fullmatch(color):
            propio = str(casilla.get("color", "")).upper()
            if color.upper() == propio or color.upper() not in usados:
                casilla["color"] = color
                usados.add(color.upper())
                if nombre_color:
                    casilla["color_nombre"] = nombre_color(color)
        casilla["extrayendo"] = acciones_remotas.get(_entero(d["id"]), 0) > ahora
        n += 1
    return n


def direccion_de(dx: float, dy: float, anterior: str = "down") -> str:
    """Orientacion del sprite segun el desplazamiento (misma regla que usa el jugador local)."""
    if dx == 0 and dy == 0:
        return anterior
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


def suavizar_remotos(
    jugadores_locales: list[dict],
    dt: float,
    rapidez: float = 18.0,
    salto_maximo: float = 800.0,
    umbral_direccion: float = 2.0,
) -> None:
    """
    Desliza a cada jugador remoto hacia la ultima posicion recibida en lugar de teletransportarlo.

    La red entrega posiciones a saltos (cada mensaje llega con una pequena variacion de tiempo);
    sin esto el rival se ve entrecortado. Ademas orienta su sprite segun hacia donde se mueve.
    Distancias muy grandes (reaparicion, perdida de mensajes) se aplican de golpe.
    """
    if dt <= 0:
        return
    for casilla in jugadores_locales:
        if casilla.get("es_local") or "objetivo" not in casilla:
            continue
        ox, oy = casilla["objetivo"]
        px, py = casilla.get("_pos", (float(ox), float(oy)))
        dx, dy = ox - px, oy - py
        distancia = math.hypot(dx, dy)
        if distancia > salto_maximo or distancia < 0.5:
            nx, ny = float(ox), float(oy)
        else:
            alfa = 1.0 - math.exp(-rapidez * dt)
            nx, ny = px + dx * alfa, py + dy * alfa
        if distancia >= umbral_direccion:
            casilla["direccion"] = direccion_de(dx, dy, casilla.get("direccion", "down"))
        casilla["_pos"] = (nx, ny)
        casilla["rect"].topleft = (int(round(nx)), int(round(ny)))
