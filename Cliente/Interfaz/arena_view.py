"""
Vista de la Arena de Batalla en Pygame (US-07 y US-14).
- Mapa amplio de 2000x1400 px con camara centrada en el jugador local (Camera Follow).
- Se adapta dinamicamente al tamano de la ventana del computador.
- Reactor Central en (1000, 700) y 4 plataformas de Spawn (Norte, Sur, Oeste, Este).
- Feedback funcional e inequivoco del 5to boton de accion (circulo del color de la hitbox + [EXTRAYENDO]).
- Reutiliza InputManager del Integrante 2 (Cliente/Inputs/gamepad_manager.py).
"""
from __future__ import annotations
import os
import pygame

from Cliente.Inputs.gamepad_manager import (
    Command,
    create_default_input_manager,
    direction_from,
)
from Cliente.Interfaz.arena_collisions import (
    REACTOR_CENTER,
    REACTOR_COLLISION_RADIUS,
    REACTOR_EXTRACTION_RADIUS,
    SPAWN_POINTS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    esta_en_zona_extraccion,
    mover_con_colisiones,
    obtener_hitbox_reactor,
    obtener_muros_arena,
)
from Cliente.Interfaz.components.hud import dibujar_hud_arena, hex_to_rgb


def _cargar_imagen_avatar(ruta: str | None) -> pygame.Surface | None:
    if not ruta or not os.path.exists(ruta):
        return None
    try:
        return pygame.image.load(ruta).convert_alpha()
    except Exception:
        return None


def iniciar_arena_pygame(controller, screen: pygame.Surface | None = None):
    """
    Ejecuta el bucle principal de la Arena en Pygame con camara dinamica,
    colisiones de muros, Reactor Central y accion fisica del 5to boton.
    """
    pygame.init()

    if screen is None:
        info = pygame.display.Info()
        comp_w = info.current_w if info.current_w > 0 else 1280
        comp_h = info.current_h if info.current_h > 0 else 720
        win_w = max(1024, int(comp_w * 0.92))
        win_h = max(640, int(comp_h * 0.86))
        os.environ["SDL_VIDEO_CENTERED"] = "1"
        screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)

    pygame.display.set_caption(f"Battle Arena Challenge - Arena ({controller.mapa_seleccionado})")
    clock = pygame.time.Clock()

    # Reutilizar InputManager del Integrante 2
    input_manager = create_default_input_manager(allow_keyboard_fallback=True)

    # Lienzo completo del mundo (2000 x 1400 px)
    world_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
    limites_mundo = pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT)

    muros_arena = obtener_muros_arena(controller.mapa_seleccionado)
    reactor_rect = obtener_hitbox_reactor()
    obstaculos_totales = muros_arena + [reactor_rect]

    # Preparar jugadores y ubicarlos en los 4 Spawn Pads (Norte, Sur, Oeste, Este)
    jugadores_base = getattr(controller, "jugadores_sala", None)
    if not jugadores_base or len(jugadores_base) < 2:
        jugadores_base = [
            {
                "id": 1,
                "nombre": str(controller.usuario_actual),
                "color_nombre": controller.obtener_nombre_color(controller.avatar_color),
                "color": controller.avatar_color,
                "es_local": True,
                "puntos": 0,
            },
            {
                "id": 2,
                "nombre": "Piloto_2",
                "color_nombre": "Azul",
                "color": "#1D3557",
                "es_local": False,
                "puntos": 0,
            },
        ]

    jugadores = []
    for idx, j in enumerate(jugadores_base[:4]):
        spx, spy = SPAWN_POINTS.get(idx, (1000, 200))
        rect_j = pygame.Rect(spx - 24, spy - 24, 48, 48)
        jugadores.append({
            "id": j.get("id", idx + 1),
            "nombre": j.get("nombre", f"Piloto_{idx + 1}"),
            "color_nombre": j.get("color_nombre", "Rojo"),
            "color": j.get("color", "#E63946"),
            "es_local": j.get("es_local", idx == 0),
            "rect": rect_j,
            "puntos": float(j.get("puntos", 0)),
            "extrayendo": False,
        })

    jugador_local = jugadores[0]
    avatar_img_surface = _cargar_imagen_avatar(controller.avatar_imagen)

    # Temporizador de 5 minutos (300 segundos) - CA-09.9
    tiempo_restante = 300.0
    velocidad_jugador = 6.0

    font_nombre = pygame.font.SysFont("Segoe UI", 14, bold=True)
    font_accion = pygame.font.SysFont("Segoe UI", 13, bold=True)
    font_reactor = pygame.font.SysFont("Segoe UI", 16, bold=True)

    corriendo = True
    accion_salida = None  # "lobby" | "cerrar"

    while corriendo:
        dt = clock.tick(60) / 1000.0
        tiempo_restante = max(0.0, tiempo_restante - dt)

        w, h = screen.get_size()

        # =====================================================================
        # 1. ENTRADA DEL JUGADOR Y ACCION FISICA DEL 5TO BOTON (US-14)
        # =====================================================================
        comandos = input_manager.poll()
        accion_activa = Command.ACTION in comandos
        jugador_local["extrayendo"] = accion_activa

        if not accion_activa:
            dx_unit, dy_unit = direction_from(comandos)
            if dx_unit != 0 or dy_unit != 0:
                jugador_local["rect"] = mover_con_colisiones(
                    jugador_local["rect"],
                    dx_unit * velocidad_jugador,
                    dy_unit * velocidad_jugador,
                    obstaculos_totales,
                    limites_mundo,
                )
        else:
            # Si mantiene presionado el 5to boton de accion cerca del Reactor, suma puntos
            if esta_en_zona_extraccion(jugador_local["rect"]):
                jugador_local["puntos"] += 10.0 * dt

        # =====================================================================
        # 2. RENDERIZADO DEL LIENZO DEL MUNDO (2000 x 1400 px)
        # =====================================================================
        world_surface.fill((20, 24, 33))

        # Cuadricula de piso de la Estacion Espacial
        for gx in range(0, WORLD_WIDTH, 100):
            pygame.draw.line(world_surface, (28, 33, 45), (gx, 0), (gx, WORLD_HEIGHT), 1)
        for gy in range(0, WORLD_HEIGHT, 100):
            pygame.draw.line(world_surface, (28, 33, 45), (0, gy), (WORLD_WIDTH, gy), 1)

        # Dibujar 4 Plataformas de Spawn (Norte, Sur, Oeste, Este - CA-07.4)
        nombres_spawns = {0: "SPAWN NORTE", 1: "SPAWN SUR", 2: "SPAWN OESTE", 3: "SPAWN ESTE"}
        for idx, (spx, spy) in SPAWN_POINTS.items():
            pygame.draw.circle(world_surface, (30, 65, 65), (spx, spy), 58)
            pygame.draw.circle(world_surface, (42, 157, 143), (spx, spy), 58, 3)
            pygame.draw.circle(world_surface, (25, 45, 50), (spx, spy), 36)
            lbl_sp = font_accion.render(nombres_spawns[idx], True, (170, 220, 210))
            world_surface.blit(lbl_sp, (spx - lbl_sp.get_width() // 2, spy + 64))

        # Dibujar Zona de Extraccion y Reactor Central en (1000, 700) - CA-07.3 y CA-07.5
        rx, ry = REACTOR_CENTER
        pygame.draw.circle(world_surface, (20, 50, 68), (rx, ry), REACTOR_EXTRACTION_RADIUS)
        pygame.draw.circle(world_surface, (0, 180, 216), (rx, ry), REACTOR_EXTRACTION_RADIUS, 2)

        # Nucleo solido del Reactor Central
        pygame.draw.circle(world_surface, (0, 119, 182), (rx, ry), REACTOR_COLLISION_RADIUS)
        pygame.draw.circle(world_surface, (0, 235, 255), (rx, ry), REACTOR_COLLISION_RADIUS, 4)
        pygame.draw.circle(world_surface, (180, 248, 255), (rx, ry), 38)

        lbl_reac = font_reactor.render("REACTOR CENTRAL", True, (255, 255, 255))
        world_surface.blit(lbl_reac, (rx - lbl_reac.get_width() // 2, ry - lbl_reac.get_height() // 2))

        # Dibujar Muros y Pasillos de la Estacion
        for muro in muros_arena:
            pygame.draw.rect(world_surface, (52, 60, 78), muro)
            pygame.draw.rect(world_surface, (88, 100, 126), muro, 2)

        # Dibujar Jugadores y Feedback Funcional del 5to Boton (US-14)
        for jug in jugadores:
            j_rect = jug["rect"]
            color_rgb = hex_to_rgb(jug["color"])

            # Si el jugador tiene activa la accion (5to boton), dibujar aro notorio de su color
            if jug["extrayendo"]:
                pygame.draw.circle(world_surface, color_rgb, j_rect.center, 46, 5)
                pygame.draw.circle(world_surface, (255, 255, 255), j_rect.center, 50, 2)

                en_reactor = esta_en_zona_extraccion(j_rect)
                txt_estado = "[EXTRAYENDO ENERGIA]" if en_reactor else "[ACCION ACTIVA]"
                lbl_ext = font_accion.render(txt_estado, True, color_rgb)
                bg_ext = pygame.Rect(
                    j_rect.centerx - lbl_ext.get_width() // 2 - 6,
                    j_rect.bottom + 8,
                    lbl_ext.get_width() + 12,
                    lbl_ext.get_height() + 4,
                )
                pygame.draw.rect(world_surface, (15, 18, 24), bg_ext, border_radius=4)
                pygame.draw.rect(world_surface, color_rgb, bg_ext, 1, border_radius=4)
                world_surface.blit(lbl_ext, (bg_ext.x + 6, bg_ext.y + 2))

            # Hitbox de 48x48 px o imagen cargada
            if jug["es_local"] and avatar_img_surface is not None:
                scaled_av = pygame.transform.smoothscale(avatar_img_surface, (j_rect.width, j_rect.height))
                world_surface.blit(scaled_av, j_rect)
            else:
                pygame.draw.rect(world_surface, color_rgb, j_rect, border_radius=6)

            borde_w = 3 if jug["es_local"] else 1
            borde_c = (255, 255, 255) if jug["es_local"] else (20, 20, 20)
            pygame.draw.rect(world_surface, borde_c, j_rect, borde_w, border_radius=6)

            lbl_n = font_nombre.render(jug["nombre"], True, (255, 255, 255))
            world_surface.blit(lbl_n, (j_rect.centerx - lbl_n.get_width() // 2, j_rect.top - lbl_n.get_height() - 6))

        # =====================================================================
        # 3. CAMARA CON SEGUIMIENTO AL JUGADOR LOCAL (CAMERA FOLLOW - US-07)
        # =====================================================================
        screen.fill((12, 14, 20))

        max_off_x = max(0, WORLD_WIDTH - w)
        max_off_y = max(0, WORLD_HEIGHT - h)
        offset_x = max(0, min(jugador_local["rect"].centerx - w // 2, max_off_x))
        offset_y = max(0, min(jugador_local["rect"].centery - h // 2, max_off_y))

        # Si el monitor es mas grande que el mapa en algun eje, centrar el lienzo
        dest_x = max(0, (w - WORLD_WIDTH) // 2)
        dest_y = max(0, (h - WORLD_HEIGHT) // 2)
        view_w = min(w, WORLD_WIDTH)
        view_h = min(h, WORLD_HEIGHT)

        camara_rect = pygame.Rect(offset_x, offset_y, view_w, view_h)
        screen.blit(world_surface, (dest_x, dest_y), camara_rect)

        # =====================================================================
        # 4. HUD FIJO SOBRE LA CAMARA (TEMPORIZADOR, AVATAR Y MINI-RADAR)
        # =====================================================================
        rects_hud = dibujar_hud_arena(
            screen,
            controller,
            jugadores,
            tiempo_restante,
            (WORLD_WIDTH, WORLD_HEIGHT),
            muros_arena,
            REACTOR_CENTER,
            avatar_img_surface,
        )

        # Guia rapida de controles en la parte inferior izquierda
        sx = w / 1280.0
        sy = h / 720.0
        font_guia = pygame.font.SysFont("Segoe UI", max(11, int(13 * sy)))
        lbl_guia = font_guia.render(
            "Controles: WASD / Flechas / Mando para mover | ESPACIO (5to Boton) para Extraer en el Reactor",
            True,
            (185, 195, 210),
        )
        guia_bg = pygame.Rect(int(16 * sx), h - int(40 * sy), lbl_guia.get_width() + 20, int(28 * sy))
        pygame.draw.rect(screen, (20, 24, 34), guia_bg, border_radius=6)
        screen.blit(lbl_guia, (guia_bg.x + 10, guia_bg.centery - lbl_guia.get_height() // 2))

        # =====================================================================
        # 5. EVENTOS DE VENTANA
        # =====================================================================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                accion_salida = "cerrar"
                corriendo = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(800, event.w), max(540, event.h)), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    accion_salida = "lobby"
                    corriendo = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if rects_hud["btn_lobby"].collidepoint(event.pos):
                    accion_salida = "lobby"
                    corriendo = False

        pygame.display.flip()

    if accion_salida == "lobby":
        from Cliente.Interfaz.lobby_view import iniciar_lobby_pygame
        iniciar_lobby_pygame(controller, screen=screen)
    else:
        controller.cerrar_aplicacion()
