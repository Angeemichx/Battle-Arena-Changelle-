"""
Componente HUD para las vistas de Pygame (Lobby y Arena).
Se adapta dinamicamente a las dimensiones de la pantalla (w, h).
Sin botones flotantes en la barra superior: toda la interaccion se realiza
caminando con el mando hacia las zonas del Lobby.
"""
from __future__ import annotations
import pygame


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """
    Descripcion:
        Convierte una cadena de color hexadecimal (#RRGGBB) a una tupla de tres enteros
        RGB compatible con las funciones de dibujo de Pygame.
    Entradas:
        hex_color (str): Cadena hexadecimal con o sin el prefijo '#' (ejemplo: '#E63946').
    Salidas:
        tuple[int, int, int]: Tupla (R, G, B) con valores enteros en el rango [0, 255].
    Restricciones:
        Si la cadena limpia no tiene exactamente 6 caracteres hexadecimales, retorna
        por defecto el color rojo de seguridad (230, 57, 70).
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (230, 57, 70)
    # Se extraen pares de caracteres hexadecimales en base 16 para cada canal de color
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def dibujar_hud_lobby(
    surface: pygame.Surface,
    controller,
    jugadores: list[dict],
    avatar_img_surface: pygame.Surface | None = None,
) -> dict[str, pygame.Rect]:
    """
    Descripcion:
        Renderiza la barra informativa superior del Lobby Caminable escalada a la resolucion
        actual, mostrando el mini-avatar del jugador local, su rol/IP y el conteo de jugadores.
    Entradas:
        surface (pygame.Surface): Superficie principal de la ventana Pygame donde se dibuja el HUD.
        controller (AppController): Instancia del controlador maestro con los datos de sesion y red.
        jugadores (list[dict]): Lista de diccionarios con los jugadores conectados a la sala.
        avatar_img_surface (pygame.Surface | None): Imagen personalizada del avatar local si fue cargada.
    Salidas:
        dict[str, pygame.Rect]: Diccionario vacio (mantenido por compatibilidad de firma de renderizado).
    Restricciones:
        pygame.font debe estar inicializado antes de invocar esta funcion; surface debe tener
        dimensiones mayores a 0.
    """
    w, h = surface.get_size()
    # Factores de escala proporcionales respecto a una resolucion base de 1280x720
    sx = w / 1280.0
    sy = h / 720.0

    bar_h = max(56, int(70 * sy))
    bar_rect = pygame.Rect(0, 0, w, bar_h)
    pygame.draw.rect(surface, (28, 31, 42), bar_rect)
    pygame.draw.line(surface, (58, 64, 82), (0, bar_h), (w, bar_h), 2)

    font_bold = pygame.font.SysFont("Segoe UI", max(14, int(16 * sy)), bold=True)
    font_small = pygame.font.SysFont("Segoe UI", max(11, int(13 * sy)))

    # 1. Izquierda: Mini-Avatar Activo + Nombre de Usuario (CA-06.5)
    av_size = max(32, int(42 * sy))
    av_x = int(20 * sx)
    av_y = (bar_h - av_size) // 2
    av_rect = pygame.Rect(av_x, av_y, av_size, av_size)

    if avatar_img_surface is not None:
        scaled_img = pygame.transform.smoothscale(avatar_img_surface, (av_size, av_size))
        surface.blit(scaled_img, av_rect)
    else:
        from Cliente.Interfaz.Components.sprite_loader import obtener_sprite_personaje
        sp_mini = obtener_sprite_personaje(controller.avatar_color, direccion="down", size=(av_size, av_size))
        if sp_mini is not None:
            surface.blit(sp_mini, av_rect)
        else:
            pygame.draw.rect(surface, hex_to_rgb(controller.avatar_color), av_rect, border_radius=5)
    pygame.draw.rect(surface, (255, 255, 255), av_rect, 2, border_radius=5)

    rol_str = "Anfitrion" if controller.es_creador else "Invitado"
    lbl_user = font_bold.render(f"Piloto: {controller.usuario_actual}", True, (255, 255, 255))
    lbl_rol = font_small.render(
        f"Rol: {rol_str} | IP Sala: {controller.ip_servidor}:{controller.puerto_servidor}",
        True,
        (160, 170, 184),
    )
    surface.blit(lbl_user, (av_rect.right + int(12 * sx), av_y))
    surface.blit(lbl_rol, (av_rect.right + int(12 * sx), av_y + lbl_user.get_height() + 2))

    # 2. Centro: Indicador de Estado de Sala (CA-09.3: verde si hay >= 2 jugadores, amarillo si falta gente)
    num_jug = len(jugadores)
    listo = num_jug >= 2
    color_estado = (42, 157, 143) if listo else (233, 196, 106)
    texto_principal = f"SALA DE ESPERA: {num_jug}/4 JUGADORES"
    texto_sub = "Listo para iniciar partida" if listo else "Camina a las zonas de la sala y presiona Accion"

    surf_prin = font_bold.render(texto_principal, True, color_estado)
    surf_sub = font_small.render(texto_sub, True, (210, 215, 225))
    surface.blit(surf_prin, (w // 2 - surf_prin.get_width() // 2, int(10 * sy)))
    surface.blit(surf_sub, (w // 2 - surf_sub.get_width() // 2, int(12 * sy) + surf_prin.get_height()))

    return {}


def dibujar_hud_arena(
    surface: pygame.Surface,
    controller,
    jugadores: list[dict],
    tiempo_restante: float,
    world_size: tuple[int, int],
    muros_mundo: list[pygame.Rect],
    reactor_center: tuple[int, int],
    avatar_img_surface: pygame.Surface | None = None,
) -> dict[str, pygame.Rect]:
    """
    Descripcion:
        Dibuja el HUD fijo sobre la camara de la Arena de Batalla, incluyendo el mini-avatar
        local (CA-06.5), el temporizador central en formato MM:SS (CA-09.9), las tarjetas
        de puntaje en vivo (CA-15.2) y el mini-radar proporcional en la esquina inferior derecha.
    Entradas:
        surface (pygame.Surface): Superficie de la pantalla donde se renderizan los elementos del HUD.
        controller (AppController): Instancia del controlador maestro con usuario y mapa activo.
        jugadores (list[dict]): Lista de hasta 4 diccionarios con estado, color, posicion y puntaje.
        tiempo_restante (float): Segundos restantes del reloj de la partida.
        world_size (tuple[int, int]): Dimensiones totales del mundo (WORLD_WIDTH, WORLD_HEIGHT).
        muros_mundo (list[pygame.Rect]): Lista de rectangulos de colision para proyectar en el mini-radar.
        reactor_center (tuple[int, int]): Coordenada (x, y) del Reactor Central en el mundo.
        avatar_img_surface (pygame.Surface | None): Imagen de avatar personalizada o None.
    Salidas:
        dict[str, pygame.Rect]: Diccionario vacio reservado para zonas del HUD.
    Restricciones:
        world_size debe contener valores mayores a cero para evitar division por cero al
        calcular la escala del mini-radar.
    """
    w, h = surface.get_size()
    sx = w / 1280.0
    sy = h / 720.0

    font_timer = pygame.font.SysFont("Consolas", max(20, int(28 * sy)), bold=True)
    font_bold = pygame.font.SysFont("Segoe UI", max(12, int(14 * sy)), bold=True)
    font_small = pygame.font.SysFont("Segoe UI", max(11, int(12 * sy)))

    # 1. Esquina Superior Izquierda: Mini-Avatar Local
    panel_local = pygame.Rect(int(16 * sx), int(14 * sy), int(260 * sx), int(54 * sy))
    pygame.draw.rect(surface, (24, 26, 34), panel_local, border_radius=8)
    pygame.draw.rect(surface, (65, 72, 92), panel_local, 2, border_radius=8)

    av_size = max(30, int(38 * sy))
    av_rect = pygame.Rect(
        panel_local.x + int(8 * sx),
        panel_local.centery - av_size // 2,
        av_size,
        av_size,
    )
    if avatar_img_surface is not None:
        scaled = pygame.transform.smoothscale(avatar_img_surface, (av_size, av_size))
        surface.blit(scaled, av_rect)
    else:
        from Cliente.Interfaz.Components.sprite_loader import obtener_sprite_personaje
        sp_mini = obtener_sprite_personaje(controller.avatar_color, direccion="down", size=(av_size, av_size))
        if sp_mini is not None:
            surface.blit(sp_mini, av_rect)
        else:
            pygame.draw.rect(surface, hex_to_rgb(controller.avatar_color), av_rect, border_radius=4)
    pygame.draw.rect(surface, (255, 255, 255), av_rect, 2, border_radius=4)

    lbl_u = font_bold.render(str(controller.usuario_actual), True, (255, 255, 255))
    lbl_m = font_small.render(f"Mapa: {controller.mapa_seleccionado}", True, (160, 170, 184))
    surface.blit(lbl_u, (av_rect.right + int(10 * sx), panel_local.y + int(6 * sy)))
    surface.blit(lbl_m, (av_rect.right + int(10 * sx), panel_local.y + int(28 * sy)))

    # 2. Centro Superior: Temporizador (cambia a color rojo cuando quedan 30 segundos o menos)
    timer_w = max(140, int(170 * sx))
    timer_h = max(42, int(50 * sy))
    timer_rect = pygame.Rect(w // 2 - timer_w // 2, int(14 * sy), timer_w, timer_h)
    pygame.draw.rect(surface, (22, 25, 34), timer_rect, border_radius=8)
    pygame.draw.rect(surface, (58, 134, 255), timer_rect, 2, border_radius=8)

    minutos = max(0, int(tiempo_restante) // 60)
    segundos = max(0, int(tiempo_restante) % 60)
    color_reloj = (255, 255, 255) if tiempo_restante > 30 else (230, 57, 70)
    surf_reloj = font_timer.render(f"{minutos:02d}:{segundos:02d}", True, color_reloj)
    surface.blit(
        surf_reloj,
        (
            timer_rect.centerx - surf_reloj.get_width() // 2,
            timer_rect.centery - surf_reloj.get_height() // 2,
        ),
    )

    # 3. Derecha Superior: Tarjetas Compactas de Jugadores y Puntajes
    card_w = max(175, int(210 * sx))
    card_h = max(32, int(36 * sy))
    start_x = w - card_w - int(16 * sx)
    start_y = int(14 * sy)

    for idx, jug in enumerate(jugadores):
        cy = start_y + idx * (card_h + int(6 * sy))
        c_rect = pygame.Rect(start_x, cy, card_w, card_h)
        pygame.draw.rect(surface, (24, 26, 34), c_rect, border_radius=6)
        pygame.draw.rect(surface, hex_to_rgb(jug["color"]), c_rect, 2, border_radius=6)

        dot = pygame.Rect(c_rect.x + int(8 * sx), c_rect.centery - int(8 * sy), int(16 * sx), int(16 * sy))
        pygame.draw.rect(surface, hex_to_rgb(jug["color"]), dot, border_radius=3)

        pts = int(jug.get("puntos", 0))
        txt_j = f"{jug['nombre'][:11]}: {pts} pts"
        surf_j = font_small.render(txt_j, True, (255, 255, 255))
        surface.blit(surf_j, (dot.right + int(8 * sx), c_rect.centery - surf_j.get_height() // 2))

    # 4. Esquina Inferior Derecha: Mini-Radar en Vivo (proyeccion a escala del mundo 3600x2600)
    radar_w = max(160, int(210 * sx))
    radar_h = max(112, int(145 * sy))
    radar_rect = pygame.Rect(w - radar_w - int(16 * sx), h - radar_h - int(16 * sy), radar_w, radar_h)
    pygame.draw.rect(surface, (18, 22, 30), radar_rect, border_radius=6)
    pygame.draw.rect(surface, (68, 78, 100), radar_rect, 2, border_radius=6)

    rx_scale = radar_w / float(world_size[0])
    ry_scale = radar_h / float(world_size[1])

    for muro in muros_mundo:
        m_rect = pygame.Rect(
            radar_rect.x + int(muro.x * rx_scale),
            radar_rect.y + int(muro.y * ry_scale),
            max(2, int(muro.width * rx_scale)),
            max(2, int(muro.height * ry_scale)),
        )
        pygame.draw.rect(surface, (55, 62, 78), m_rect)

    # Reactor Central proyectado en el radar
    rc_x = radar_rect.x + int(reactor_center[0] * rx_scale)
    rc_y = radar_rect.y + int(reactor_center[1] * ry_scale)
    pygame.draw.circle(surface, (0, 210, 255), (rc_x, rc_y), max(4, int(8 * sy)))

    # Posicion de cada jugador proyectada en el radar con el color de su hitbox
    for jug in jugadores:
        r_rect = jug["rect"]
        jx = radar_rect.x + int(r_rect.centerx * rx_scale)
        jy = radar_rect.y + int(r_rect.centery * ry_scale)
        pygame.draw.circle(surface, hex_to_rgb(jug["color"]), (jx, jy), max(3, int(5 * sy)))

    return {}
