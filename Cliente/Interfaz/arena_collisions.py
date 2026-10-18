"""
Definicion y exportacion de colisiones (pygame.Rect) para el Lobby y la Arena.
Cumple con US-07 (CA-07.3, CA-07.4, CA-07.6).
Mapa ampliado a 3600x2600 px para soportar comodamente 4 jugadores y guardianes.
"""
from __future__ import annotations
import math
import pygame

# Dimensiones amplias del mundo de la Arena (3600 x 2600 px)
WORLD_WIDTH = 3600
WORLD_HEIGHT = 2600

# Posicion y radios del Reactor Central en el centro exacto del mapa
REACTOR_CENTER = (1800, 1300)
REACTOR_COLLISION_RADIUS = 110
REACTOR_EXTRACTION_RADIUS = 210

# 4 Plataformas de inicio (Spawn Pads) - Norte, Sur, Oeste, Este
SPAWN_POINTS = {
    0: (1800, 260),   # Norte
    1: (1800, 2340),  # Sur
    2: (300, 1300),   # Oeste
    3: (3300, 1300),  # Este
}


def obtener_colisiones_lobby(zona_caminable: pygame.Rect) -> dict[str, list[pygame.Rect] | pygame.Rect]:
    """
    Genera los muros perimetrales y las 3 zonas interactivas caminables del Lobby
    pensadas para usarse con Mando (Gamepad):
    - Centro: Mesa de Comando (Configuracion de Colores, Mapas y Audio).
    - Derecha: Zona de Despegue (Iniciar Partida hacia la Arena).
    - Izquierda: Zona de Salida (Volver al Menu Principal).
    """
    grosor = max(12, int(zona_caminable.width * 0.02))
    x, y, w, h = zona_caminable.x, zona_caminable.y, zona_caminable.width, zona_caminable.height

    muros = [
        pygame.Rect(x, y, w, grosor),                      # Pared Superior
        pygame.Rect(x, y + h - grosor, w, grosor),         # Pared Inferior
        pygame.Rect(x, y, grosor, h),                      # Pared Izquierda
        pygame.Rect(x + w - grosor, y, grosor, h),         # Pared Derecha
    ]

    # 1. Centro: Mesa de Comando
    mesa_w = int(w * 0.18)
    mesa_h = int(h * 0.18)
    mesa_x = x + (w - mesa_w) // 2
    mesa_y = y + (h - mesa_h) // 2
    mesa_rect = pygame.Rect(mesa_x, mesa_y, mesa_w, mesa_h)

    margen_interaccion = max(32, int(min(w, h) * 0.08))
    zona_interaccion = mesa_rect.inflate(margen_interaccion * 2, margen_interaccion * 2)

    # 2. Derecha: Plataforma caminable de Despegue (Iniciar Partida)
    pad_w = int(w * 0.21)
    pad_h = int(h * 0.15)
    zona_despegue = pygame.Rect(
        x + w - pad_w - grosor - int(w * 0.03),
        y + (h - pad_h) // 2,
        pad_w,
        pad_h,
    )

    # 3. Izquierda: Plataforma caminable de Salida (Volver al Menu Principal con mando)
    zona_salida = pygame.Rect(
        x + grosor + int(w * 0.03),
        y + (h - pad_h) // 2,
        pad_w,
        pad_h,
    )

    return {
        "muros": muros + [mesa_rect],
        "bordes": muros,
        "mesa": mesa_rect,
        "zona_interaccion": zona_interaccion,
        "zona_despegue": zona_despegue,
        "zona_salida": zona_salida,
    }


def obtener_muros_arena(tipo_mapa: str = "Estacion Estandar") -> list[pygame.Rect]:
    """
    Exporta la lista de pygame.Rect que representan los muros exteriores
    y los bloques de salas/pasillos internos de la Arena de 3600x2600 px.
    Disenado con corredores amplios para 4 jugadores y patrullaje de guardianes.
    """
    grosor_borde = 50
    muros = [
        # Limites exteriores de la estacion (3600 x 2600)
        pygame.Rect(0, 0, WORLD_WIDTH, grosor_borde),
        pygame.Rect(0, WORLD_HEIGHT - grosor_borde, WORLD_WIDTH, grosor_borde),
        pygame.Rect(0, 0, grosor_borde, WORLD_HEIGHT),
        pygame.Rect(WORLD_WIDTH - grosor_borde, 0, grosor_borde, WORLD_HEIGHT),

        # Bloques estructurales Noroeste
        pygame.Rect(520, 380, 480, 340),
        pygame.Rect(1140, 380, 360, 480),
        pygame.Rect(520, 860, 480, 220),

        # Bloques estructurales Noreste
        pygame.Rect(2100, 380, 360, 480),
        pygame.Rect(2600, 380, 480, 340),
        pygame.Rect(2600, 860, 480, 220),

        # Bloques estructurales Suroeste
        pygame.Rect(520, 1520, 480, 220),
        pygame.Rect(520, 1880, 480, 340),
        pygame.Rect(1140, 1740, 360, 480),

        # Bloques estructurales Sureste
        pygame.Rect(2100, 1740, 360, 480),
        pygame.Rect(2600, 1520, 480, 220),
        pygame.Rect(2600, 1880, 480, 340),
    ]

    if tipo_mapa == "Reactor Inestable":
        muros.extend([
            pygame.Rect(1420, 960, 110, 110),
            pygame.Rect(2070, 960, 110, 110),
            pygame.Rect(1420, 1530, 110, 110),
            pygame.Rect(2070, 1530, 110, 110),
        ])
    elif tipo_mapa == "Laberinto Cerrado":
        muros.extend([
            pygame.Rect(1720, 620, 160, 70),
            pygame.Rect(1720, 1910, 160, 70),
            pygame.Rect(820, 1250, 70, 140),
            pygame.Rect(2710, 1250, 70, 140),
            pygame.Rect(1360, 1120, 70, 120),
            pygame.Rect(2170, 1360, 70, 120),
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
