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
REACTOR_COLLISION_RADIUS = 85
REACTOR_EXTRACTION_RADIUS = 210

# 4 Plataformas de inicio (Spawn Pads) ubicadas en los puntos cardinales (Norte, Sur, Oeste, Este)
SPAWN_POINTS = {
    0: (1800, 260),   # Norte
    1: (1800, 2340),  # Sur
    2: (300, 1300),   # Oeste
    3: (3300, 1300),  # Este
}


def obtener_colisiones_lobby(zona_caminable: pygame.Rect) -> dict[str, list[pygame.Rect] | pygame.Rect]:
    """
    Descripcion:
        Genera dinamicamente los muros perimetrales y las 3 zonas fisicas interactivas
        del Lobby Caminable (Mesa de Comando al centro, Despegue a la derecha y Salida
        a la izquierda) proporcionales al tamano de la zona caminable.
    Entradas:
        zona_caminable (pygame.Rect): Rectangulo delimitador del piso caminable del Lobby.
    Salidas:
        dict[str, list[pygame.Rect] | pygame.Rect]: Diccionario con las claves 'muros',
        'bordes', 'mesa', 'zona_interaccion', 'zona_despegue' y 'zona_salida'.
    Restricciones:
        zona_caminable debe poseer un ancho y alto positivos mayores a 100 pixeles.
    """
    grosor = max(12, int(zona_caminable.width * 0.02))
    x, y, w, h = zona_caminable.x, zona_caminable.y, zona_caminable.width, zona_caminable.height

    muros = [
        pygame.Rect(x, y, w, grosor),                      # Pared Superior
        pygame.Rect(x, y + h - grosor, w, grosor),         # Pared Inferior
        pygame.Rect(x, y, grosor, h),                      # Pared Izquierda
        pygame.Rect(x + w - grosor, y, grosor, h),         # Pared Derecha
    ]

    # 1. Centro: Mesa de Comando solida y su perimetro de interaccion expandido (inflate)
    mesa_w = int(w * 0.18)
    mesa_h = int(h * 0.18)
    mesa_x = x + (w - mesa_w) // 2
    mesa_y = y + (h - mesa_h) // 2
    mesa_rect = pygame.Rect(mesa_x, mesa_y, mesa_w, mesa_h)

    margen_interaccion = max(32, int(min(w, h) * 0.08))
    zona_interaccion = mesa_rect.inflate(margen_interaccion * 2, margen_interaccion * 2)

    # 2. Derecha: Plataforma caminable de Despegue (Iniciar Partida hacia la Arena)
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
    Descripcion:
        Construye y exporta la lista de rectangulos de colision (pygame.Rect) que conforman
        los bordes exteriores y los bloques estructurales internos de la Arena de 3600x2600 px
        segun la variante de mapa seleccionada por el anfitrion.
    Entradas:
        tipo_mapa (str): Nombre de la configuracion del mapa ('Estacion Estandar',
        'Reactor Inestable' o 'Laberinto Cerrado').
    Salidas:
        list[pygame.Rect]: Lista de rectangulos solidos no atravesables por los jugadores.
    Restricciones:
        Si tipo_mapa no coincide con una variante especial conocida, retorna la disposicion
        base de 'Estacion Estandar'.
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

    # Se agregan pilares o bloqueos tacticos adicionales segun la variante elegida en el Lobby
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
    """
    Descripcion:
        Calcula y devuelve el rectangulo delimitador solido (hitbox) del nucleo del
        Reactor Central ubicado en REACTOR_CENTER.
    Entradas:
        Ninguna.
    Salidas:
        pygame.Rect: Rectangulo centrado en (1800, 1300) con tamano 2*REACTOR_COLLISION_RADIUS.
    Restricciones:
        REACTOR_COLLISION_RADIUS debe ser mayor que cero.
    """
    r = REACTOR_COLLISION_RADIUS
    return pygame.Rect(REACTOR_CENTER[0] - r, REACTOR_CENTER[1] - r, r * 2, r * 2)


def esta_en_zona_extraccion(hitbox_jugador: pygame.Rect) -> bool:
    """
    Descripcion:
        Determina mediante distancia euclidiana si el centro de la hitbox del jugador
        se encuentra dentro del anillo de extraccion de energia del Reactor Central.
    Entradas:
        hitbox_jugador (pygame.Rect): Rectangulo de posicion y tamano actual del jugador.
    Salidas:
        bool: True si la distancia al centro del Reactor es menor o igual a REACTOR_EXTRACTION_RADIUS;
        False en caso contrario.
    Restricciones:
        hitbox_jugador debe ser una instancia valida de pygame.Rect.
    """
    dx = hitbox_jugador.centerx - REACTOR_CENTER[0]
    dy = hitbox_jugador.centery - REACTOR_CENTER[1]
    # Formula de distancia euclidiana hipotenusa sqrt(dx^2 + dy^2)
    distancia = math.hypot(dx, dy)
    return distancia <= REACTOR_EXTRACTION_RADIUS


def mover_con_colisiones(
    rect: pygame.Rect,
    dx: float,
    dy: float,
    obstaculos: list[pygame.Rect],
    limites: pygame.Rect | None = None,
    circulo_reactor: tuple[int, int, int] | None = None,
) -> pygame.Rect:
    """
    Descripcion:
        Aplica el desplazamiento (dx, dy) a un rectangulo evaluando de forma independiente
        el eje X y el eje Y contra muros rectangulares, y resolviendo de forma radial
        la colision circular contra el Reactor para permitir un deslizamiento suave y continuo
        sin atascos en esquinas cuadradas ficticias.
    Entradas:
        rect (pygame.Rect): Rectangulo original del jugador antes del movimiento.
        dx (float): Desplazamiento horizontal solicitado en pixeles.
        dy (float): Desplazamiento vertical solicitado en pixeles.
        obstaculos (list[pygame.Rect]): Lista de muros y objetos solidos con los que colisionar.
        limites (pygame.Rect | None): Rectangulo opcional que confina al jugador dentro del mapa.
        circulo_reactor (tuple[int, int, int] | None): Tupla opcional (cx, cy, radio) para colision circular.
    Salidas:
        pygame.Rect: Nuevo rectangulo con la posicion final corregida tras resolver colisiones.
    Restricciones:
        Ninguna.
    """
    nuevo = rect.copy()

    # Resolucion independiente en el eje X: evita que una colision horizontal bloquee el eje Y
    step_x = int(round(dx))
    if step_x != 0:
        nuevo.x += step_x
        for obs in obstaculos:
            if nuevo.colliderect(obs):
                if step_x > 0:
                    nuevo.right = obs.left
                elif step_x < 0:
                    nuevo.left = obs.right

    # Resolucion independiente en el eje Y: permite deslizarse a lo largo de muros horizontales
    step_y = int(round(dy))
    if step_y != 0:
        nuevo.y += step_y
        for obs in obstaculos:
            if nuevo.colliderect(obs):
                if step_y > 0:
                    nuevo.bottom = obs.top
                elif step_y < 0:
                    nuevo.top = obs.bottom

    # Resolucion fisica circular continua para el Reactor Central (elimina huecos y esquinas invisibles)
    if circulo_reactor is not None:
        rx, ry, radio_col = circulo_reactor
        px, py = nuevo.centerx, nuevo.centery
        diff_x = px - rx
        diff_y = py - ry
        dist = math.hypot(diff_x, diff_y)
        # Radio de colision efectiva (radio del reactor + radio de la hitbox del personaje)
        min_dist = radio_col + (rect.width / 2.0)
        if dist < min_dist:
            if dist > 0.001:
                nx = diff_x / dist
                ny = diff_y / dist
            else:
                nx, ny = 1.0, 0.0
            nuevo.centerx = int(round(rx + nx * min_dist))
            nuevo.centery = int(round(ry + ny * min_dist))

    if limites is not None:
        nuevo.clamp_ip(limites)

    return nuevo
