"""
Modulo centralizado para la carga, cache y escalado de Sprites 2D en Pygame.
Gestiona personajes Hazmat por color/direccion, particulas radiactivas animadas
y elementos decorativos del entorno (Reactor, Muros, Pisos y Carteles).
"""
from __future__ import annotations
import math
import time
from pathlib import Path
import pygame

_CACHE_SPRITES: dict = {}
_MAPA_COLORES = {
    "#E63946": "rojo",
    "#1D3557": "azul",
    "#2A9D8F": "verde",
    "#E9C46A": "amarillo",
    "#7209B7": "morado",
}


def _get_sprites_dir() -> Path:
    """Retorna la ruta absoluta del directorio de Sprites."""
    return Path(__file__).resolve().parent.parent.parent / "Recursos" / "Sprites"


def _safe_load_img(ruta: Path) -> pygame.Surface | None:
    """Carga una imagen y aplica convert_alpha solo si el display esta activo."""
    if not ruta.exists():
        return None
    try:
        surf = pygame.image.load(str(ruta))
        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            try:
                return surf.convert_alpha()
            except Exception:
                pass
        return surf
    except Exception as e:
        print(f"[SPRITES] Error al cargar {ruta}: {e}")
        return None


def inicializar_sprites(forzar_recarga: bool = False) -> dict:
    """
    Descripcion:
        Carga en memoria todos los sprites PNG de Personajes, Particulas y Entorno,
        almacenandolos en la cache global _CACHE_SPRITES.
    Entradas:
        forzar_recarga (bool): Si es True, limpia la cache previa y recarga desde disco.
    Salidas:
        dict: Diccionario estructurado con todos los sprites cargados.
    Restricciones:
        Ninguna.
    """
    global _CACHE_SPRITES
    if _CACHE_SPRITES and not forzar_recarga:
        return _CACHE_SPRITES

    base_dir = _get_sprites_dir()
    data = {
        "personajes": {},
        "particulas": [],
        "entorno": {},
        "ui": {},
    }

    # 1. Cargar Personajes (5 colores x 4 direcciones + extraccion)
    dir_chars = base_dir / "Personajes"
    for hex_c, nom_c in _MAPA_COLORES.items():
        data["personajes"][hex_c.upper()] = {}
        for estado in ("down", "up", "left", "right", "extract"):
            ruta = dir_chars / f"char_{nom_c}_{estado}.png"
            s = _safe_load_img(ruta)
            if s is not None:
                data["personajes"][hex_c.upper()][estado] = s

    # 2. Cargar Particulas Radiactivas (1 a 5)
    dir_parts = base_dir / "Particulas"
    for i in range(1, 6):
        ruta = dir_parts / f"particle_extract_{i}.png"
        s = _safe_load_img(ruta)
        if s is not None:
            data["particulas"].append(s)

    # 3. Cargar Entorno
    dir_env = base_dir / "Entorno"
    nombres_env = [
        "reactor_core", "extraction_ring", "spawn_pad",
        "muro_plomo", "piso_rejilla", "mesa_comando",
        "muro_ladrillo", "piso_calor", "muro_hormigon", "piso_hexagonal"
    ]
    for n in nombres_env:
        ruta = dir_env / f"{n}.png"
        s = _safe_load_img(ruta)
        if s is not None:
            data["entorno"][n] = s

    # 4. Cargar Carteles y UI de Pygame
    dir_ui = base_dir / "UI"
    nombres_ui = ["sign_despegue", "sign_salida", "sign_mesa_comando", "logo_battle_arena", "logo_letras_puras"]
    for n in nombres_ui:
        ruta = dir_ui / f"{n}.png"
        s = _safe_load_img(ruta)
        if s is not None:
            data["ui"][n] = s

    _CACHE_SPRITES = data
    return _CACHE_SPRITES


def obtener_sprite_personaje(color_hex: str, direccion: str = "down", extrayendo: bool = False, size: tuple[int, int] = (48, 48)) -> pygame.Surface | None:
    """
    Descripcion:
        Retorna la superficie Pygame del personaje hazmat para el color y direccion solicitada,
        escalada a la resolucion indicada.
    Entradas:
        color_hex (str): Codigo hexadecimal del color del jugador (#RRGGBB).
        direccion (str): 'down', 'up', 'left' o 'right'.
        extrayendo (bool): True si el jugador se encuentra extrayendo energia en el Reactor.
        size (tuple[int, int]): Ancho y alto de la hitbox en pixeles.
    Salidas:
        pygame.Surface | None: Superficie lista para dibujar o None si no existe el asset.
    Restricciones:
        Ninguna.
    """
    sprites = inicializar_sprites()
    chars = sprites.get("personajes", {})
    color_dict = chars.get(str(color_hex).strip().upper())
    if not color_dict:
        color_dict = next(iter(chars.values()), {})

    estado = "extract" if extrayendo and "extract" in color_dict else direccion
    surf = color_dict.get(estado) or color_dict.get("down")
    if surf is not None:
        if surf.get_size() != size:
            return pygame.transform.smoothscale(surf, size)
        return surf
    return None


def obtener_frame_particula(t_offset: float = 0.0) -> pygame.Surface | None:
    """
    Descripcion:
        Retorna el frame correspondiente de la animacion de particulas radiactivas
        segun el tiempo actual, ciclando las 5 imagenes a 12 FPS.
    Entradas:
        t_offset (float): Desfase temporal en segundos para desincronizar multiples particulas.
    Salidas:
        pygame.Surface | None: Frame de particula o None.
    Restricciones:
        Ninguna.
    """
    sprites = inicializar_sprites()
    parts = sprites.get("particulas", [])
    if not parts:
        return None
    idx = int((time.time() + t_offset) * 12) % len(parts)
    return parts[idx]


def obtener_sprite_entorno(nombre: str, size: tuple[int, int] | None = None) -> pygame.Surface | None:
    """
    Descripcion:
        Retorna el sprite del entorno o UI solicitado, con escalado opcional.
    Entradas:
        nombre (str): Clave del asset ('reactor_core', 'extraction_ring', 'spawn_pad', etc.).
        size (tuple[int, int] | None): Dimensiones opcionales de escalado.
    Salidas:
        pygame.Surface | None: Superficie de Pygame lista para dibujar.
    Restricciones:
        Ninguna.
    """
    sprites = inicializar_sprites()
    surf = sprites.get("entorno", {}).get(nombre) or sprites.get("ui", {}).get(nombre)
    if surf is not None and size is not None and surf.get_size() != size:
        return pygame.transform.smoothscale(surf, size)
    return surf
