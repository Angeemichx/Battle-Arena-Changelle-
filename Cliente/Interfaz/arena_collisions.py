"""
Definicion y exportacion de colisiones (pygame.Rect) para el Lobby y la Arena.
Cumple con US-07 (CA-07.3, CA-07.4, CA-07.6).
Disenado para que tanto la vista como el Integrante 2 puedan consumirlo.
"""
from __future__ import annotations
import math
import pygame

# Dimensiones del mundo de la Arena (US-07)
WORLD_WIDTH = 2000
WORLD_HEIGHT = 1400

# Posicion y radios del Reactor Central (Seccion 5.2 de la guia)
REACTOR_CENTER = (1000, 700)
REACTOR_COLLISION_RADIUS = 90
REACTOR_EXTRACTION_RADIUS = 155

# 4 Plataformas de inicio (Spawn Pads) - Norte, Sur, Oeste, Este
SPAWN_POINTS = {
    0: (1000, 200),   # Norte
    1: (1000, 1200),  # Sur
    2: (250, 700),    # Oeste
    3: (1750, 700),   # Este
}


def obtener_colisiones_lobby(zona_caminable: pygame.Rect) -> dict[str, list[pygame.Rect] | pygame.Rect]:
    """
    Genera los muros perimetrales y la mesa central del Lobby caminable
    adaptandose dinamicamente al rectangulo de la zona caminable en pantalla.
    """
    grosor = max(12, int(zona_caminable.width * 0.02))
    x, y, w, h = zona_caminable.x, zona_caminable.y, zona_caminable.width, zona_caminable.height

    muros = [
        pygame.Rect(x, y, w, grosor),                      # Pared Superior
        pygame.Rect(x, y + h - grosor, w, grosor),         # Pared Inferior
        pygame.Rect(x, y, grosor, h),                      # Pared Izquierda
        pygame.Rect(x + w - grosor, y, grosor, h),         # Pared Derecha
    ]

    # Mesa de Comando en el centro de la zona caminable
    mesa_w = int(w * 0.18)
    mesa_h = int(h * 0.18)
    mesa_x = x + (w - mesa_w) // 2
    mesa_y = y + (h - mesa_h) // 2
    mesa_rect = pygame.Rect(mesa_x, mesa_y, mesa_w, mesa_h)

    # Zona de interaccion un poco mas amplia alrededor de la mesa
    margen_interaccion = max(28, int(min(w, h) * 0.07))
    zona_interaccion = mesa_rect.inflate(margen_interaccion * 2, margen_interaccion * 2)

    return {
        "muros": muros + [mesa_rect],
        "bordes": muros,
        "mesa": mesa_rect,
        "zona_interaccion": zona_interaccion,
    }


def obtener_muros_arena(tipo_mapa: str = "Estacion Estandar") -> list[pygame.Rect]:
    """
    Exporta la lista de pygame.Rect que representan los muros exteriores
    y los bloques de pasillos internos de la Arena de 2000x1400 px.
    Deja corredores amplios hacia los 4 spawns (Norte, Sur, Oeste, Este)
    y el salon central del Reactor.
    """
    grosor_borde = 40
    muros = [
        # Limites exteriores del mapa 2000x1400
        pygame.Rect(0, 0, WORLD_WIDTH, grosor_borde),
        pygame.Rect(0, WORLD_HEIGHT - grosor_borde, WORLD_WIDTH, grosor_borde),
        pygame.Rect(0, 0, grosor_borde, WORLD_HEIGHT),
        pygame.Rect(WORLD_WIDTH - grosor_borde, 0, grosor_borde, WORLD_HEIGHT),

        # 4 Grandes bloques estructurales en los cuadrantes (crean los pasillos en cruz y anillo)
        # Cuadrante Noroeste
        pygame.Rect(380, 220, 420, 300),
        # Cuadrante Noreste
        pygame.Rect(1200, 220, 420, 300),
        # Cuadrante Suroeste
        pygame.Rect(380, 880, 420, 300),
        # Cuadrante Sureste
        pygame.Rect(1200, 880, 420, 300),
    ]

    if tipo_mapa == "Reactor Inestable":
        # Pilares adicionales alrededor del salon central
        muros.extend([
            pygame.Rect(830, 520, 60, 60),
            pygame.Rect(1110, 520, 60, 60),
            pygame.Rect(830, 820, 60, 60),
            pygame.Rect(1110, 820, 60, 60),
        ])
    elif tipo_mapa == "Laberinto Cerrado":
        # Barreras parciales en los corredores laterales
        muros.extend([
            pygame.Rect(180, 420, 120, 50),
            pygame.Rect(180, 930, 120, 50),
            pygame.Rect(1700, 420, 120, 50),
            pygame.Rect(1700, 930, 120, 50),
            pygame.Rect(960, 360, 80, 45),
            pygame.Rect(960, 995, 80, 45),
        ])

    return muros


def obtener_hitbox_reactor() -> pygame.Rect:
    """Devuelve el pygame.Rect de colision solida del Reactor Central."""
    r = REACTOR_COLLISION_RADIUS
    return pygame.Rect(REACTOR_CENTER[0] - r, REACTOR_CENTER[1] - r, r * 2, r * 2)


def esta_en_zona_extraccion(hitbox_jugador: pygame.Rect) -> bool:
    """Verifica si el centro del jugador se encuentra dentro del radio de extraccion del Reactor."""
    dx = hitbox_jugador.centerx - REACTOR_CENTER[0]
    dy = hitbox_jugador.centery - REACTOR_CENTER[1]
    distancia = math.hypot(dx, dy)
    return distancia <= REACTOR_EXTRACTION_RADIUS


def mover_con_colisiones(
    rect: pygame.Rect,
    dx: float,
    dy: float,
    obstaculos: list[pygame.Rect],
    limites: pygame.Rect | None = None,
) -> pygame.Rect:
    """
    Desplaza un pygame.Rect en los ejes X e Y de forma independiente,
    permitiendo deslizarse suavemente contra las paredes sin atascarse.
    """
    nuevo = rect.copy()

    # Movimiento en eje X
    nuevo.x += int(round(dx))
    for obs in obstaculos:
        if nuevo.colliderect(obs):
            if dx > 0:
                nuevo.right = obs.left
            elif dx < 0:
                nuevo.left = obs.right

    # Movimiento en eje Y
    nuevo.y += int(round(dy))
    for obs in obstaculos:
        if nuevo.colliderect(obs):
            if dy > 0:
                nuevo.bottom = obs.top
            elif dy < 0:
                nuevo.top = obs.bottom

    if limites is not None:
        nuevo.clamp_ip(limites)

    return nuevo
