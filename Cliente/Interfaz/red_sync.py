"""
Sincronizacion de jugadores remotos (US-11 / US-13).

El servidor entrega la lista de jugadores ordenada por llegada, y cada cliente es uno de ellos.
Estas funciones puras (sin pygame ni red) deciden a que jugador local corresponde cada
jugador del servidor, usando el id de cada uno y NO la posicion en la lista.
"""
from __future__ import annotations

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
