"""
Componente de Obstaculos y Trampas de la Arena (US-20).

Gestiona la representacion grafica, estados y colisiones de:
- Barreras solidas y vallas de advertencia industrial (CA-20.1, CA-20.2, CA-20.3).
- Puertas y esclusas dinamicas con estados abierta/cerrada (CA-20.4).
- 3 tipos de trampas activas en la arena (CA-20.5, CA-20.9):
  1. Jaula electrificada (inmovilizacion con barrotes superpuestos).
  2. Inversion de gravedad (rota el sprite del avatar 180 grados).
  3. Charco radiactivo / fango (tinte toxico y ralentizacion).
"""
from __future__ import annotations
import math
import time
from typing import Dict, List, Tuple
import pygame

from Cliente.Interfaz.Components.sprite_loader import (
    obtener_frame_particula,
    obtener_sprite_entorno,
)


def obtener_obstaculos_por_mapa(tipo_mapa: str = "Estacion Estandar") -> dict:
    """
    Descripcion:
        Genera la configuracion de puertas, barreras y 3 trampas para la variante
        de escenario seleccionada (US-20, CA-23.2, CA-23.6).
        Todas las posiciones estan situadas en zonas limpias, lejos del Reactor
        Central (1800, 1300) y de los 4 Spawns cardinales.
    Entradas:
        tipo_mapa (str): Nombre del escenario ('Estacion Estandar', 'Reactor Inestable' o 'Laberinto Cerrado').
    Salidas:
        dict: Diccionario con listas de 'puertas', 'barreras' y 'trampas'.
    Restricciones:
        Ninguna. Si el mapa no es reconocido, retorna la configuracion de 'Estacion Estandar'.
    """
    if tipo_mapa == "Reactor Inestable":
        puertas = [
            {"id": "p1", "rect": pygame.Rect(1650, 960, 120, 28), "estado": "cerrada", "orientacion": "horizontal", "periodo": 8.0},
            {"id": "p2", "rect": pygame.Rect(1830, 1610, 120, 28), "estado": "abierta", "orientacion": "horizontal", "periodo": 8.0},
            {"id": "p3", "rect": pygame.Rect(1320, 1240, 28, 120), "estado": "cerrada", "orientacion": "vertical", "periodo": 6.0},
            {"id": "p4", "rect": pygame.Rect(2250, 1240, 28, 120), "estado": "abierta", "orientacion": "vertical", "periodo": 6.0},
        ]
        barreras = [
            {"id": "b1", "rect": pygame.Rect(1420, 900, 110, 24), "tipo": "peligro"},
            {"id": "b2", "rect": pygame.Rect(2070, 900, 110, 24), "tipo": "peligro"},
            {"id": "b3", "rect": pygame.Rect(1420, 1675, 110, 24), "tipo": "peligro"},
            {"id": "b4", "rect": pygame.Rect(2070, 1675, 110, 24), "tipo": "peligro"},
        ]
        trampas = [
            {"id": "t_jaula", "tipo": "jaula", "rect": pygame.Rect(1100, 1150, 64, 64), "activa": True},
            {"id": "t_grav", "tipo": "gravedad", "rect": pygame.Rect(2440, 1150, 72, 72), "activa": True},
            {"id": "t_charco", "tipo": "charco", "rect": pygame.Rect(1800, 780, 80, 80), "activa": True},
        ]
    elif tipo_mapa == "Laberinto Cerrado":
        puertas = [
            {"id": "p1", "rect": pygame.Rect(1720, 700, 160, 28), "estado": "cerrada", "orientacion": "horizontal", "periodo": 7.0},
            {"id": "p2", "rect": pygame.Rect(1720, 1870, 160, 28), "estado": "abierta", "orientacion": "horizontal", "periodo": 7.0},
            {"id": "p3", "rect": pygame.Rect(900, 1250, 28, 140), "estado": "cerrada", "orientacion": "vertical", "periodo": 7.0},
            {"id": "p4", "rect": pygame.Rect(2670, 1250, 28, 140), "estado": "abierta", "orientacion": "vertical", "periodo": 7.0},
        ]
        barreras = [
            {"id": "b1", "rect": pygame.Rect(1360, 1080, 70, 24), "tipo": "peligro"},
            {"id": "b2", "rect": pygame.Rect(2170, 1490, 70, 24), "tipo": "peligro"},
        ]
        trampas = [
            {"id": "t_jaula", "tipo": "jaula", "rect": pygame.Rect(1480, 1450, 64, 64), "activa": True},
            {"id": "t_grav", "tipo": "gravedad", "rect": pygame.Rect(2060, 1100, 72, 72), "activa": True},
            {"id": "t_charco", "tipo": "charco", "rect": pygame.Rect(1800, 1800, 80, 80), "activa": True},
        ]
    else:  # Estacion Estandar por defecto
        puertas = [
            {"id": "p1", "rect": pygame.Rect(1730, 920, 140, 28), "estado": "cerrada", "orientacion": "horizontal", "periodo": 8.0},
            {"id": "p2", "rect": pygame.Rect(1730, 1650, 140, 28), "estado": "abierta", "orientacion": "horizontal", "periodo": 8.0},
            {"id": "p3", "rect": pygame.Rect(1380, 1240, 28, 120), "estado": "cerrada", "orientacion": "vertical", "periodo": 6.0},
            {"id": "p4", "rect": pygame.Rect(2190, 1240, 28, 120), "estado": "abierta", "orientacion": "vertical", "periodo": 6.0},
        ]
        barreras = [
            {"id": "b1", "rect": pygame.Rect(1520, 520, 180, 24), "tipo": "peligro"},
            {"id": "b2", "rect": pygame.Rect(1900, 520, 180, 24), "tipo": "peligro"},
            {"id": "b3", "rect": pygame.Rect(1520, 2060, 180, 24), "tipo": "peligro"},
            {"id": "b4", "rect": pygame.Rect(1900, 2060, 180, 24), "tipo": "peligro"},
        ]
        trampas = [
            {"id": "t_jaula", "tipo": "jaula", "rect": pygame.Rect(1280, 1050, 64, 64), "activa": True},
            {"id": "t_grav", "tipo": "gravedad", "rect": pygame.Rect(2260, 1480, 72, 72), "activa": True},
            {"id": "t_charco", "tipo": "charco", "rect": pygame.Rect(1800, 820, 80, 80), "activa": True},
        ]

    return {"puertas": puertas, "barreras": barreras, "trampas": trampas}


def actualizar_estados_puertas(puertas: list[dict], tiempo_actual: float) -> None:
    """
    Descripcion:
        Alterna ciclicamente el estado (abierta / cerrada) de cada compuerta segun su periodo temporal,
        a menos que el estado este fijado externamente por el servidor de red (CA-20.4).
    Entradas:
        puertas (list[dict]): Lista de diccionarios que definen cada puerta.
        tiempo_actual (float): Marca de tiempo en segundos (time.time()).
    Salidas:
        None: Modifica in-place la clave 'estado' de cada puerta.
    """
    for p in puertas:
        periodo = p.get("periodo", 8.0)
        # Si el servidor no impone un estado forzado, alterna de forma predecible
        if "estado_fijado" not in p:
            ciclo = int(tiempo_actual / periodo) % 2
            p["estado"] = "cerrada" if ciclo == 0 else "abierta"


def obtener_colisiones_obstaculos(obstaculos: dict) -> list[pygame.Rect]:
    """
    Descripcion:
        Calcula la lista de rectangulos solidos con los que el avatar colisiona.
        Incluye todas las barreras y UNICAMENTE las puertas que se encuentren en estado 'cerrada'
        (CA-20.3, CA-20.4). Las puertas abiertas permiten el paso libremente.
    Entradas:
        obstaculos (dict): Diccionario con claves 'puertas' y 'barreras'.
    Salidas:
        list[pygame.Rect]: Lista de cajas de colision intransitables.
    """
    solidos: list[pygame.Rect] = []
    for b in obstaculos.get("barreras", []):
        solidos.append(b["rect"])

    for p in obstaculos.get("puertas", []):
        if p.get("estado") == "cerrada":
            solidos.append(p["rect"])

    return solidos


def detectar_trampa_activa(hitbox_jugador: pygame.Rect, trampas: list[dict]) -> str | None:
    """
    Descripcion:
        Verifica mediante interseccion de rectangulos si el centro del jugador
        esta pisando alguna de las trampas activas (CA-20.5).
    Entradas:
        hitbox_jugador (pygame.Rect): Rectangulo de colision del avatar.
        trampas (list[dict]): Lista de trampas del escenario.
    Salidas:
        str | None: Tipo de trampa detectada ('jaula', 'gravedad', 'charco') o None si no hay colision.
    """
    for t in trampas:
        if t.get("activa", True) and t["rect"].collidepoint(hitbox_jugador.center):
            return t.get("tipo")
    return None


DURACION_JAULA = 3.0      # segundos que la jaula retiene al jugador
INMUNIDAD_JAULA = 4.0     # segundos tras liberarse en los que la jaula no vuelve a atraparlo


def resolver_trampa_local(jugador: dict, trampa_detectada: str | None, ahora: float) -> str | None:
    """
    Descripcion:
        Decide que trampa afecta ahora al jugador. La jaula lo retiene solo DURACION_JAULA
        segundos y, al liberarlo, queda inmune INMUNIDAD_JAULA segundos para que pueda salir de
        ella; antes se quedaba atrapado para siempre. Al salir de cualquier trampa el efecto termina.
    Entradas:
        jugador (dict): Estado del jugador (se guardan 'jaula_hasta' y 'jaula_inmune_hasta').
        trampa_detectada (str | None): Trampa que esta pisando ('jaula', 'gravedad', 'charco') o None.
        ahora (float): Tiempo actual en segundos.
    Salidas:
        str | None: Trampa que debe aplicarse, o None si no hay efecto.
    """
    if trampa_detectada != "jaula":
        jugador["jaula_hasta"] = None
        return trampa_detectada
    if ahora < jugador.get("jaula_inmune_hasta", 0.0):
        return None
    if jugador.get("jaula_hasta") is None:
        jugador["jaula_hasta"] = ahora + DURACION_JAULA
        return "jaula"
    if ahora >= jugador["jaula_hasta"]:
        jugador["jaula_hasta"] = None
        jugador["jaula_inmune_hasta"] = ahora + INMUNIDAD_JAULA
        return None
    return "jaula"


def dibujar_obstaculos_arena(surface: pygame.Surface, obstaculos: dict, tiempo_actual: float) -> None:
    """
    Descripcion:
        Renderiza en la superficie del mundo todos los obstaculos (barreras, puertas y trampas)
        con sprites y superficies estilizadas con canal alfa (CA-20.1, CA-20.2, CA-20.4).
    Entradas:
        surface (pygame.Surface): Lienzo del mundo de Pygame (3600x2600 px).
        obstaculos (dict): Diccionario con 'barreras', 'puertas' y 'trampas'.
        tiempo_actual (float): Tiempo actual para animaciones fluidas a 60 FPS.
    Salidas:
        None: Dibuja directamente sobre 'surface'.
    """
    # 1. DIBUJAR TRAMPAS EN EL PISO (se dibujan antes de muros y jugadores)
    for t in obstaculos.get("trampas", []):
        rect = t["rect"]
        tipo = t.get("tipo")

        if tipo == "gravedad":
            # Vortice gravitacional: anillos concentricos violeta/cian pulsantes
            centro = rect.center
            radio_base = rect.width // 2
            pulsacion = 0.5 + 0.5 * math.sin(tiempo_actual * 4.0)
            radio_dinamico = int(radio_base * (0.85 + 0.15 * pulsacion))
            vortice_surf = pygame.Surface((rect.width * 2, rect.height * 2), pygame.SRCALPHA)
            cx, cy = rect.width, rect.height
            pygame.draw.circle(vortice_surf, (114, 9, 183, 70), (cx, cy), radio_dinamico)
            pygame.draw.circle(vortice_surf, (76, 201, 240, 140), (cx, cy), int(radio_dinamico * 0.65), 2)
            pygame.draw.circle(vortice_surf, (247, 37, 133, 180), (cx, cy), int(radio_dinamico * 0.35), 2)
            # Lineas espirales
            for ang in range(0, 360, 60):
                rad = math.radians(ang + tiempo_actual * 120.0)
                ex = cx + int(math.cos(rad) * radio_dinamico)
                ey = cy + int(math.sin(rad) * radio_dinamico)
                pygame.draw.line(vortice_surf, (180, 120, 255, 120), (cx, cy), (ex, ey), 1)
            surface.blit(vortice_surf, (centro[0] - cx, centro[1] - cy))

        elif tipo == "jaula":
            # Placa metalica con rejilla electrificada
            pygame.draw.rect(surface, (32, 38, 48), rect, border_radius=6)
            pygame.draw.rect(surface, (230, 180, 30), rect, 2, border_radius=6)
            # Rejilla interna
            for gx in range(rect.left + 8, rect.right, 12):
                pygame.draw.line(surface, (70, 85, 105), (gx, rect.top + 4), (gx, rect.bottom - 4), 1)
            for gy in range(rect.top + 8, rect.bottom, 12):
                pygame.draw.line(surface, (70, 85, 105), (rect.left + 4, gy), (rect.right - 4, gy), 1)
            # Chispa electrica ocasional
            if int(tiempo_actual * 8) % 3 == 0:
                p_surf = obtener_frame_particula(t_offset=0.2)
                if p_surf:
                    surface.blit(p_surf, (rect.centerx - 16, rect.centery - 16))

        elif tipo == "charco":
            # Charco radiactivo verde toxico
            charco_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.ellipse(charco_surf, (57, 255, 20, 110), (0, 0, rect.width, rect.height))
            pygame.draw.ellipse(charco_surf, (150, 255, 100, 170), (4, 4, rect.width - 8, rect.height - 8), 2)
            # Burbujas flotantes animadas
            for b_idx in range(3):
                f_b = (tiempo_actual * 2.0 + b_idx * 1.5) % 3.0
                bx = int(rect.width * (0.25 + b_idx * 0.25))
                by = int(rect.height * 0.7 - f_b * 6)
                pygame.draw.circle(charco_surf, (200, 255, 180, int(200 - f_b * 50)), (bx, by), 3)
            surface.blit(charco_surf, rect.topleft)

    # 2. DIBUJAR BARRERAS PELIGRO (franjas amarillas / negras industriales)
    sp_hazard = obtener_sprite_entorno("hazard_stripe_bar")
    for b in obstaculos.get("barreras", []):
        r = b["rect"]
        if sp_hazard:
            scaled = pygame.transform.scale(sp_hazard, (r.width, r.height))
            surface.blit(scaled, r.topleft)
        else:
            pygame.draw.rect(surface, (230, 180, 20), r)
            # Rayas alternadas
            for rx in range(r.left, r.right, 24):
                puntos_poligono = [
                    (rx, r.bottom),
                    (min(r.right, rx + 12), r.top),
                    (min(r.right, rx + 20), r.top),
                    (min(r.right, rx + 8), r.bottom),
                ]
                pygame.draw.polygon(surface, (20, 20, 20), puntos_poligono)
        pygame.draw.rect(surface, (255, 215, 0), r, 2)

    # 3. DIBUJAR PUERTAS (Abiertas vs Cerradas - CA-20.4)
    for p in obstaculos.get("puertas", []):
        r = p["rect"]
        abierta = (p.get("estado") == "abierta")

        if abierta:
            # Puerta Abierta: estructura replegada con senaletica verde brillante
            pygame.draw.rect(surface, (18, 28, 24), r, border_radius=4)
            pygame.draw.rect(surface, (46, 204, 113), r, 2, border_radius=4)
            # Luz central verde
            pygame.draw.circle(surface, (46, 204, 113), r.center, 5)
            # Indicadores de paso libre
            if p.get("orientacion") == "horizontal":
                pygame.draw.line(surface, (46, 204, 113), (r.left + 8, r.centery), (r.left + 24, r.centery), 3)
                pygame.draw.line(surface, (46, 204, 113), (r.right - 24, r.centery), (r.right - 8, r.centery), 3)
            else:
                pygame.draw.line(surface, (46, 204, 113), (r.centerx, r.top + 8), (r.centerx, r.top + 24), 3)
                pygame.draw.line(surface, (46, 204, 113), (r.centerx, r.bottom - 24), (r.centerx, r.bottom - 8), 3)
        else:
            # Puerta Cerrada: compuerta solida metalica blindada con rojo de advertencia
            pygame.draw.rect(surface, (45, 52, 65), r, border_radius=4)
            # Franja central de bloqueo
            if p.get("orientacion") == "horizontal":
                pygame.draw.rect(surface, (231, 76, 60), (r.left + 6, r.centery - 3, r.width - 12, 6), border_radius=2)
            else:
                pygame.draw.rect(surface, (231, 76, 60), (r.centerx - 3, r.top + 6, 6, r.height - 12), border_radius=2)
            pygame.draw.rect(surface, (231, 76, 60), r, 2, border_radius=4)
            # Luz LED roja central
            pygame.draw.circle(surface, (255, 50, 50), r.center, 5)


def aplicar_efecto_visual_avatar(
    sprite_base: pygame.Surface,
    tamano: tuple[int, int],
    tipo_trampa: str | None,
    tiempo_actual: float,
) -> pygame.Surface:
    """
    Descripcion:
        Aplica sobre el sprite del avatar la transformacion grafica correspondiente
        segun la trampa en la que haya caido (CA-20.5, CA-20.9):
        - 'gravedad': Rota el sprite 180 grados (de cabeza).
        - 'jaula': Superpone barrotes de celda electrificados con parpadeo.
        - 'charco': Aplica un filtro verde fosforescente de contaminacion.
    Entradas:
        sprite_base (pygame.Surface): Superficie original del personaje hazmat.
        tamano (tuple[int, int]): Resolucion esperada (ancho, alto).
        tipo_trampa (str | None): Identificador de la trampa activa o None.
        tiempo_actual (float): Para animar los destellos y efectos.
    Salidas:
        pygame.Surface: Nueva superficie transformada lista para blit.
    Restricciones:
        Garantiza que el tamano final nunca supere los limites del avatar.
    """
    if not tipo_trampa:
        return sprite_base

    surf = sprite_base.copy()

    if tipo_trampa == "gravedad":
        # CA-20.5: Rotar el sprite del avatar 180 grados si esta de cabeza
        surf = pygame.transform.rotate(surf, 180)
        # Resplandor violeta sutil en los pies/cabeza
        aura = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(aura, (180, 50, 255, 70), (surf.get_width() // 2, surf.get_height() // 2), surf.get_width() // 2)
        surf.blit(aura, (0, 0))

    elif tipo_trampa == "jaula":
        # Barrotes de contencion encima del avatar
        w, h = surf.get_size()
        barrotes = pygame.Surface((w, h), pygame.SRCALPHA)
        # Marco exterior de reja
        pygame.draw.rect(barrotes, (240, 240, 255, 210), (0, 0, w, h), 2)
        # Barras verticales
        for bx in range(8, w, 10):
            pygame.draw.line(barrotes, (240, 240, 255, 210), (bx, 2), (bx, h - 2), 2)
        # Chispa superior parpadeante
        if int(tiempo_actual * 10) % 2 == 0:
            pygame.draw.line(barrotes, (255, 220, 50, 240), (4, 4), (w - 4, 4), 2)
        surf.blit(barrotes, (0, 0))

    elif tipo_trampa == "charco":
        # Tinte verde acido radiactivo sobre el traje
        w, h = surf.get_size()
        filtro_toxico = pygame.Surface((w, h), pygame.SRCALPHA)
        filtro_toxico.fill((57, 255, 20, 80))
        surf.blit(filtro_toxico, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    return surf
