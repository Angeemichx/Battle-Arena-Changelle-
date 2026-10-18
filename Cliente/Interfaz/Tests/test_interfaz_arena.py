"""
Pruebas unitarias positivas y negativas para el modulo del Integrante 1
(Colisiones de Arena y Lobby, Zona de Extraccion del Reactor, Exclusion de Colores y Sincronizacion).
Cumple con el Definition of Done (DoD) del Sprint 2.
"""
import pytest
import pygame

from Cliente.Interfaz.arena_collisions import (
    REACTOR_CENTER,
    REACTOR_EXTRACTION_RADIUS,
    SPAWN_POINTS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    esta_en_zona_extraccion,
    mover_con_colisiones,
    obtener_colisiones_lobby,
    obtener_hitbox_reactor,
    obtener_muros_arena,
)
from Cliente.Interfaz.components.ui_helpers import COLORES_AVATAR
from Cliente.Interfaz.root import AppController


# ---------- Pruebas Positivas ----------

def test_cinco_colores_avatar_obligatorios():
    """Verifica que existan al menos los 5 colores default requeridos por US-06 (CA-06.2)."""
    assert len(COLORES_AVATAR) >= 5
    for nombre in ("Rojo", "Azul", "Verde", "Amarillo", "Morado"):
        assert nombre in COLORES_AVATAR


def test_dimensiones_y_spawns_arena():
    """Verifica los 4 puntos de inicio y el Reactor Central en el mapa ampliado de 3600x2600 (US-07)."""
    assert WORLD_WIDTH == 3600
    assert WORLD_HEIGHT == 2600
    assert REACTOR_CENTER == (1800, 1300)
    assert len(SPAWN_POINTS) == 4
    muros = obtener_muros_arena("Estacion Estandar")
    assert len(muros) >= 8


def test_movimiento_libre_sin_obstaculos():
    """Prueba positiva: el avatar se desplaza libremente en un pasillo despejado."""
    jugador = pygame.Rect(1000, 200, 48, 48)
    nuevo = mover_con_colisiones(jugador, 10, 15, [])
    assert nuevo.x == 1010
    assert nuevo.y == 215


def test_deteccion_positiva_zona_extraccion_reactor():
    """Prueba positiva: un jugador junto al Reactor Central es detectado en zona de extraccion."""
    rx, ry = REACTOR_CENTER
    jugador_cerca = pygame.Rect(rx + 80, ry - 24, 48, 48)
    assert esta_en_zona_extraccion(jugador_cerca) is True


def test_color_disponible_cuando_nadie_lo_usa():
    """Prueba positiva: un color libre puede ser seleccionado por el jugador local."""
    ctrl = AppController()
    jugadores_sala = [
        {"id": 1, "nombre": "Local", "color": "#E63946", "es_local": True},
        {"id": 2, "nombre": "Remoto", "color": "#1D3557", "es_local": False},
    ]
    assert ctrl.validar_color_disponible("#2A9D8F", jugadores_sala) is True


def test_sincronizacion_estado_red():
    """Prueba positiva: actualizar_estado_red procesa el diccionario de estado del servidor."""
    ctrl = AppController()
    paquete_servidor = {
        "tipo": "estado",
        "jugadores": [
            {"id": 1, "nombre": "Piloto1", "x": 250, "y": 300, "puntaje": 12},
            {"id": 2, "nombre": "Piloto2", "x": 450, "y": 500, "puntaje": 8},
        ],
        "activa": True,
        "ganador": None,
    }
    ctrl.actualizar_estado_red(paquete_servidor)
    assert len(ctrl.estado_partida_red["jugadores"]) == 2
    assert ctrl.estado_partida_red["jugadores"][0]["puntaje"] == 12


# ---------- Pruebas Negativas ----------

def test_colision_bloquea_atravesar_muro():
    """Prueba negativa: el jugador no puede atravesar un muro solido ni el Reactor."""
    muro = pygame.Rect(200, 100, 50, 200)
    jugador = pygame.Rect(150, 150, 48, 48)  # Borde derecho en x=198
    nuevo = mover_con_colisiones(jugador, 25, 0, [muro])
    assert nuevo.right == muro.left


def test_jugador_no_puede_salir_de_limites_arena():
    """Prueba negativa (CA-09.1): el avatar no puede salir de los limites del mundo."""
    limites = pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT)
    jugador = pygame.Rect(5, 5, 48, 48)
    nuevo = mover_con_colisiones(jugador, -50, -50, [], limites)
    assert nuevo.left >= 0
    assert nuevo.top >= 0


def test_deteccion_negativa_fuera_de_zona_extraccion():
    """Prueba negativa: un jugador lejos del Reactor no activa extraccion de energia."""
    jugador_lejos = pygame.Rect(200, 200, 48, 48)
    assert esta_en_zona_extraccion(jugador_lejos) is False


def test_color_bloqueado_si_otro_jugador_lo_ocupa():
    """Prueba negativa (CA-10.3): no se permite elegir un color ya ocupado por otro jugador."""
    ctrl = AppController()
    jugadores_sala = [
        {"id": 1, "nombre": "Local", "color": "#E63946", "es_local": True},
        {"id": 2, "nombre": "Remoto", "color": "#1D3557", "es_local": False},
    ]
    assert ctrl.validar_color_disponible("#1D3557", jugadores_sala) is False
