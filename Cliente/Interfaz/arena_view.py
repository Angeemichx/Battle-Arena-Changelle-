"""
Vista de la Arena de Batalla en Pygame (US-07, US-14, US-15, US-16, US-17).
- Mapa amplio de 3600x2600 px pensado para 4 jugadores y guardianes, con camara centrada (Camera Follow).
- Se adapta dinamicamente al tamano de la ventana del computador.
- Reactor Central en (1800, 1300) y 4 plataformas de Spawn (Norte, Sur, Oeste, Este).
- Parametros configurables desde el Lobby (Tiempo de Partida y Meta de Puntos).
- Sistema de puntuacion por segundos:
  * Contador de segundos en movimiento: cada 1 segundo en movimiento multiplica por 10 (+10 pts/seg).
  * Contador de segundos extrayendo en el Reactor: cada 1 segundo extrayendo suma 40 (+40 pts/seg).
- Condicion de Victoria y Desempate Automatico (US-16 / CA-16.4: +2 minutos si hay empate en el 1er lugar).
- Pantalla de Victoria (US-17) con avatar ganador, tabla de posiciones y retorno al Lobby con mando (Command.ACTION).
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
from Cliente.Interfaz.Components.hud import dibujar_hud_arena, hex_to_rgb
from Cliente.Interfaz.Components.sprite_loader import (
    inicializar_sprites,
    obtener_frame_particula,
    obtener_sprite_entorno,
    obtener_sprite_personaje,
)


def _cargar_imagen_avatar(ruta: str | None) -> pygame.Surface | None:
    """
    Descripcion:
        Carga desde disco la imagen personalizada del avatar del jugador local y la
        convierte al formato con canal alfa de Pygame.
    Entradas:
        ruta (str | None): Ruta del archivo de imagen (.png/.jpg/.bmp) o None.
    Salidas:
        pygame.Surface | None: Superficie de Pygame lista para dibujar o None si falla la carga.
    Restricciones:
        Requiere que el modo de video de Pygame ya haya sido inicializado.
    """
    if not ruta or not os.path.exists(ruta):
        return None
    try:
        return pygame.image.load(ruta).convert_alpha()
    except Exception:
        return None


def evaluar_condicion_victoria(
    jugadores: list[dict],
    tiempo_restante: float,
    puntos_meta: int,
    modo_fin: str | None = None,
) -> tuple[bool, dict | None, bool, float]:
    """
    Descripcion:
        Evalua en cada fotograma si la partida debe concluir por alcanzarse la meta de
        puntos o por agotamiento del reloj (US-16), aplicando el desempate automatico
        de +2 minutos (120 segundos) cuando existe empate en el primer lugar (CA-16.4).
    Entradas:
        jugadores (list[dict]): Lista de diccionarios de los jugadores con su clave 'puntos'.
        tiempo_restante (float): Segundos restantes en el temporizador de la partida.
        puntos_meta (int): Puntaje objetivo para ganar la partida (por defecto 500 pts).
        modo_fin (str | None): Configuracion US-08. "tiempo": solo termina al agotarse el reloj;
        "puntos": solo termina al alcanzar la meta; None: cualquiera de las dos (comportamiento original).
    Salidas:
        tuple[bool, dict | None, bool, float]: Tupla con (partida_terminada, jugador_ganador,
        hubo_desempate, nuevo_tiempo_restante).
    Restricciones:
        Si la lista jugadores esta vacia, retorna (False, None, False, tiempo_restante).
    """
    if not jugadores:
        return False, None, False, tiempo_restante

    alguien_alcanzo_meta = any(j.get("puntos", 0) >= puntos_meta for j in jugadores)
    tiempo_agotado = tiempo_restante <= 0.0
    if modo_fin == "tiempo":
        alguien_alcanzo_meta = False
    elif modo_fin == "puntos":
        tiempo_agotado = False

    if not alguien_alcanzo_meta and not tiempo_agotado:
        return False, None, False, tiempo_restante

    max_pts = max(j.get("puntos", 0) for j in jugadores)
    lideres = [j for j in jugadores if j.get("puntos", 0) == max_pts]

    # Regla CA-16.4: Si 2 o mas jugadores empatan en el puntaje maximo, se otorgan +120s de desempate
    if len(lideres) > 1:
        # En modo "puntos" no hay reloj que extender: el desempate sube la meta (lo hace la arena).
        nuevo_tiempo = tiempo_restante if modo_fin == "puntos" else max(tiempo_restante, 0.0) + 120.0
        return False, None, True, nuevo_tiempo

    return True, lideres[0], False, tiempo_restante


def iniciar_arena_pygame(controller, screen: pygame.Surface | None = None) -> None:
    """
    Descripcion:
        Ejecuta el bucle principal de la Arena de Batalla (mundo de 3600x2600 px) con
        seguimiento de camara (Camera Follow), colisiones contra muros y Reactor Central,
        acumulacion de puntaje por segundo en movimiento (+10 pts/s) y extraccion en el
        Reactor (+40 pts/s), y renderizado de la Pantalla de Victoria (US-17).
    Entradas:
        controller (AppController): Instancia del controlador maestro con parametros y red.
        screen (pygame.Surface | None): Superficie de ventana Pygame activa o None para crearla.
    Salidas:
        None: Al finalizar y pulsar volver al Lobby, transfiere el control a iniciar_lobby_pygame.
    Restricciones:
        Exige soltar fisicamente el boton de accion (Command.ACTION) antes de aceptar la
        orden de salir de la Pantalla de Victoria hacia el Lobby.
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

    pygame.display.set_caption(f"Battle Arena Challenge - Arena 3600x2600 ({controller.mapa_seleccionado})")
    clock = pygame.time.Clock()

    # Reutilizar InputManager del Integrante 2
    input_manager = create_default_input_manager(allow_keyboard_fallback=True)
    comandos_previos: set[Command] = set(input_manager.poll())
    esperando_soltar_accion: bool = Command.ACTION in comandos_previos

    # Lienzo completo del mundo (3600 x 2600 px)
    world_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
    limites_mundo = pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT)

    muros_arena = obtener_muros_arena(controller.mapa_seleccionado)
    reactor_rect = obtener_hitbox_reactor()
    obstaculos_totales = muros_arena + [reactor_rect]

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
        spx, spy = SPAWN_POINTS.get(idx, (1800, 260))
        rect_j = pygame.Rect(spx - 24, spy - 24, 48, 48)
        jugadores.append({
            "id": j.get("id", idx + 1),
            "nombre": j.get("nombre", f"Piloto_{idx + 1}"),
            "color_nombre": j.get("color_nombre", "Rojo"),
            "color": j.get("color", "#E63946"),
            "es_local": j.get("es_local", idx == 0),
            "rect": rect_j,
            "segundos_movimiento": 0,
            "acum_mov": 0.0,
            "segundos_reactor": 0,
            "acum_reactor": 0.0,
            "puntos": 0,
            "extrayendo": False,
            "direccion": "down",
        })

    # Verificacion de seguridad: garantizar que no se repitan colores entre jugadores (CA-10.3)
    from Cliente.Interfaz.Components.ui_helpers import COLORES_AVATAR
    colores_asignados = set()
    for jug in jugadores:
        c_actual = str(jug.get("color", "")).strip().upper()
        if not c_actual or c_actual in colores_asignados:
            for nom_c, hex_c in COLORES_AVATAR.items():
                if hex_c.upper() not in colores_asignados:
                    jug["color"] = hex_c
                    jug["color_nombre"] = nom_c
                    c_actual = hex_c.upper()
                    break
        colores_asignados.add(c_actual)

    jugador_local = jugadores[0]
    avatar_img_surface = _cargar_imagen_avatar(controller.avatar_imagen)

    # Parametros de partida configurados en el Lobby (US-09 / US-16)
    tiempo_partida_min = int(getattr(controller, "tiempo_partida_min", 3))
    puntos_meta = int(getattr(controller, "puntos_meta", 500))
    modo_fin = getattr(controller, "modo_fin", None)
    if modo_fin not in ("tiempo", "puntos"):
        modo_fin = None
    # En modo "puntos" el reloj cuenta hacia arriba (tiempo transcurrido); en los demas, hacia abajo.
    tiempo_restante = 0.0 if modo_fin == "puntos" else float(tiempo_partida_min * 60)
    controller.partida_en_curso = True  # bloquea la configuracion hasta salir (CA-08.6)
    velocidad_jugador = 7.0

    # Estado de Victoria y Desempate (US-16 / US-17)
    partida_finalizada = False
    jugador_ganador: dict | None = None
    banner_desempate_timer = 0.0
    rondas_desempate = 0

    font_nombre = pygame.font.SysFont("Segoe UI", 14, bold=True)
    font_accion = pygame.font.SysFont("Segoe UI", 13, bold=True)
    font_reactor = pygame.font.SysFont("Segoe UI", 16, bold=True)

    corriendo = True
    accion_salida = None  # "lobby" | "cerrar"
    btn_volver_victoria_rect: pygame.Rect | None = None
    menu_pausa_activo = False
    opcion_pausa_idx = 0  # 0: REANUDAR, 1: ABANDONAR PARTIDA
    btn_pausa_rects: list[pygame.Rect] = []

    while corriendo:
        dt = clock.tick(60) / 1000.0
        w, h = screen.get_size()
        sx = w / 1280.0
        sy = h / 720.0

        comandos_actuales = input_manager.poll()
        if esperando_soltar_accion:
            if Command.ACTION not in comandos_actuales:
                esperando_soltar_accion = False
            comandos_nuevos = (comandos_actuales - comandos_previos) - {Command.ACTION}
        else:
            comandos_nuevos = comandos_actuales - comandos_previos
        comandos_previos = set(comandos_actuales)

        # Gestion del Menu de Pausa / Configuracion en medio de la partida
        if menu_pausa_activo:
            if Command.UP in comandos_nuevos:
                opcion_pausa_idx = 0
            elif Command.DOWN in comandos_nuevos:
                opcion_pausa_idx = 1
            elif Command.ACTION in comandos_nuevos:
                if opcion_pausa_idx == 0:
                    menu_pausa_activo = False
                    esperando_soltar_accion = True
                elif opcion_pausa_idx == 1:
                    # Abandonar partida:
                    # Si al salir queda solo 1 jugador, ese jugador inmediatamente gana.
                    # Si quedan 2 o mas jugadores, el jugador local solo se sale al lobby.
                    otros_jugadores = [j for j in jugadores if not j.get("es_local", False)]
                    if len(otros_jugadores) == 1:
                        partida_finalizada = True
                        jugador_ganador = otros_jugadores[0]
                        accion_salida = "victoria"
                        corriendo = False
                    else:
                        accion_salida = "lobby"
                        corriendo = False
                    menu_pausa_activo = False

        elif not partida_finalizada:
            if modo_fin == "puntos":
                tiempo_restante += dt
            else:
                tiempo_restante = max(0.0, tiempo_restante - dt)
            if banner_desempate_timer > 0.0:
                banner_desempate_timer = max(0.0, banner_desempate_timer - dt)

            # =====================================================================
            # 1. ENTRADA DEL JUGADOR Y CONTADORES DE SEGUNDOS (MOV x10 / REACTOR x40)
            # =====================================================================
            accion_activa = (Command.ACTION in comandos_actuales) and (not esperando_soltar_accion)
            jugador_local["extrayendo"] = accion_activa

            if not accion_activa:
                dx_unit, dy_unit = direction_from(comandos_actuales)
                if dx_unit != 0 or dy_unit != 0:
                    # Actualizar orientacion del sprite del jugador
                    if abs(dx_unit) >= abs(dy_unit):
                        jugador_local["direccion"] = "right" if dx_unit > 0 else "left"
                    else:
                        jugador_local["direccion"] = "down" if dy_unit > 0 else "up"

                    pos_previa = jugador_local["rect"].topleft
                    jugador_local["rect"] = mover_con_colisiones(
                        jugador_local["rect"],
                        dx_unit * velocidad_jugador,
                        dy_unit * velocidad_jugador,
                        obstaculos_totales,
                        limites_mundo,
                    )
                    # Si el jugador se desplazo efectivamente, contar el tiempo en movimiento
                    if jugador_local["rect"].topleft != pos_previa:
                        jugador_local["acum_mov"] += dt
                        while jugador_local["acum_mov"] >= 1.0:
                            jugador_local["acum_mov"] -= 1.0
                            jugador_local["segundos_movimiento"] += 1
                            jugador_local["puntos"] = (
                                jugador_local["segundos_movimiento"] * 10
                                + jugador_local["segundos_reactor"] * 40
                            )
                        controller.enviar_movimiento_red(dx_unit, dy_unit)
            else:
                controller.enviar_accion_red("[EXTRAYENDO]")
                # Si mantiene presionado el 5to boton dentro de la zona del Reactor, suma 40 pts por cada segundo
                if esta_en_zona_extraccion(jugador_local["rect"]):
                    jugador_local["acum_reactor"] += dt
                    while jugador_local["acum_reactor"] >= 1.0:
                        jugador_local["acum_reactor"] -= 1.0
                        jugador_local["segundos_reactor"] += 1
                        jugador_local["puntos"] = (
                            jugador_local["segundos_movimiento"] * 10
                            + jugador_local["segundos_reactor"] * 40
                        )

            # Sincronizar posiciones/acciones de otros jugadores si el servidor TCP esta activo
            if getattr(controller, "estado_partida_red", None):
                import time
                ahora = time.time()
                with controller.estado_red_lock:
                    remotos = controller.estado_partida_red.get("jugadores", [])
                    for idx_r, datos_r in enumerate(remotos):
                        if idx_r < len(jugadores) and not jugadores[idx_r]["es_local"]:
                            jugadores[idx_r]["nombre"] = datos_r.get("nombre", jugadores[idx_r]["nombre"])
                            jugadores[idx_r]["puntos"] = int(datos_r.get("puntaje", jugadores[idx_r]["puntos"]))
                            rx_rem = datos_r.get("x")
                            ry_rem = datos_r.get("y")
                            if rx_rem is not None and ry_rem is not None and (rx_rem != 0 or ry_rem != 0):
                                jugadores[idx_r]["rect"].topleft = (int(rx_rem), int(ry_rem))
                            id_rem = int(datos_r.get("id", idx_r + 1))
                            jugadores[idx_r]["extrayendo"] = controller.acciones_remotas.get(id_rem, 0) > ahora

            # Evaluar Condicion de Victoria y Desempate Automatico (US-16 / CA-16.4)
            terminada, ganador, hubo_desempate, nuevo_t = evaluar_condicion_victoria(
                jugadores, tiempo_restante, puntos_meta, modo_fin
            )
            if hubo_desempate:
                tiempo_restante = nuevo_t
                rondas_desempate += 1
                banner_desempate_timer = 5.0
                # Si empataron en la meta de puntos, incrementar la meta para el desempate
                max_pts_actual = max(j.get("puntos", 0) for j in jugadores)
                if max_pts_actual >= puntos_meta:
                    puntos_meta = max_pts_actual + 80
            elif terminada and ganador is not None:
                partida_finalizada = True
                jugador_ganador = ganador
                jugador_local["extrayendo"] = False
                # US-17: la pantalla de victoria (victoria_view) toma el control tras este fotograma
                accion_salida = "victoria"
                corriendo = False
                # Si el jugador venia manteniendo presionado el boton de accion en el Reactor,
                # exigir que lo suelte y lo vuelva a presionar para salir de la Pantalla de Victoria
                if Command.ACTION in comandos_actuales:
                    esperando_soltar_accion = True
        else:
            # En la Pantalla de Victoria, el 5to boton del mando (Command.ACTION) regresa al Lobby
            # unicamente tras haber soltado el boton y volverlo a presionar
            if Command.ACTION in comandos_nuevos:
                accion_salida = "lobby"
                corriendo = False

        # =====================================================================
        # 2. RENDERIZADO DEL LIENZO DEL MUNDO CON SPRITES 2D (3600 x 2600 px)
        # =====================================================================
        world_surface.fill((18, 21, 28))

        # Seleccion dinamica de texturas segun la variante de mapa (3 mapas con tematicas unicas)
        mapa_nombre = getattr(controller, "mapa_seleccionado", "Estacion Estandar")
        if mapa_nombre == "Reactor Inestable":
            key_piso = "piso_calor"
            key_muro = "muro_ladrillo"
        elif mapa_nombre == "Laberinto Cerrado":
            key_piso = "piso_hexagonal"
            key_muro = "muro_hormigon"
        else:
            key_piso = "piso_rejilla"
            key_muro = "muro_plomo"

        # A. Piso de la Arena segun la variante tematica seleccionada
        sprite_piso = obtener_sprite_entorno(key_piso)
        if sprite_piso:
            pw, ph = sprite_piso.get_size()
            # Se dibuja la rejilla en pasos regulares para no penalizar rendimiento
            for gx in range(0, WORLD_WIDTH, pw * 2):
                for gy in range(0, WORLD_HEIGHT, ph * 2):
                    world_surface.blit(sprite_piso, (gx, gy))
        else:
            for gx in range(0, WORLD_WIDTH, 120):
                pygame.draw.line(world_surface, (28, 33, 45), (gx, 0), (gx, WORLD_HEIGHT), 1)
            for gy in range(0, WORLD_HEIGHT, 120):
                pygame.draw.line(world_surface, (28, 33, 45), (0, gy), (WORLD_WIDTH, gy), 1)

        # B. Plataformas de Spawn (Norte, Sur, Oeste, Este - CA-07.4) mediante Sprite
        sprite_spawn = obtener_sprite_entorno("spawn_pad", (96, 96))
        nombres_spawns = {0: "SPAWN NORTE", 1: "SPAWN SUR", 2: "SPAWN OESTE", 3: "SPAWN ESTE"}
        for idx, (spx, spy) in SPAWN_POINTS.items():
            if sprite_spawn:
                world_surface.blit(sprite_spawn, (spx - 48, spy - 48))
            else:
                pygame.draw.circle(world_surface, (30, 65, 65), (spx, spy), 48)
                pygame.draw.circle(world_surface, (42, 157, 143), (spx, spy), 48, 3)
            lbl_sp = font_accion.render(nombres_spawns[idx], True, (170, 220, 210))
            world_surface.blit(lbl_sp, (spx - lbl_sp.get_width() // 2, spy + 52))

        # C. Zona de Extraccion y Reactor Central en (1800, 1300) mediante Sprites
        rx, ry = REACTOR_CENTER
        sprite_ring = obtener_sprite_entorno("extraction_ring", (360, 360))
        if sprite_ring:
            world_surface.blit(sprite_ring, (rx - 180, ry - 180))
        else:
            pygame.draw.circle(world_surface, (20, 50, 68), (rx, ry), REACTOR_EXTRACTION_RADIUS)
            pygame.draw.circle(world_surface, (0, 180, 216), (rx, ry), REACTOR_EXTRACTION_RADIUS, 3)

        sprite_reactor = obtener_sprite_entorno("reactor_core", (256, 256))
        if sprite_reactor:
            world_surface.blit(sprite_reactor, (rx - 128, ry - 128))
        else:
            pygame.draw.circle(world_surface, (0, 119, 182), (rx, ry), REACTOR_COLLISION_RADIUS)
            pygame.draw.circle(world_surface, (0, 235, 255), (rx, ry), REACTOR_COLLISION_RADIUS, 4)

        # Hitbox fisica circular visible del Reactor Central (radio de colision)
        pygame.draw.circle(world_surface, (57, 255, 20), (rx, ry), REACTOR_COLLISION_RADIUS, 3)

        lbl_reac = font_reactor.render("REACTOR CENTRAL (+40 PTS/SEG)", True, (255, 255, 255))
        world_surface.blit(lbl_reac, (rx - lbl_reac.get_width() // 2, ry - 146))

        # D. Muros perimetrales e internos mediante Sprites segun variante tematica
        sprite_muro = obtener_sprite_entorno(key_muro)
        for muro in muros_arena:
            if sprite_muro:
                mw_step, mh_step = sprite_muro.get_size()
                for mx in range(muro.left, muro.right, mw_step):
                    for my in range(muro.top, muro.bottom, mh_step):
                        world_surface.blit(sprite_muro, (mx, my))
                pygame.draw.rect(world_surface, (20, 24, 32), muro, 2)
            else:
                pygame.draw.rect(world_surface, (52, 60, 78), muro)
                pygame.draw.rect(world_surface, (88, 100, 126), muro, 2)

        # E. Jugadores (Trajes Hazmat) y Particulas de Extraccion Animadas (US-14)
        for jug in jugadores:
            j_rect = jug["rect"]
            color_hex = jug.get("color", "#E63946")
            color_rgb = hex_to_rgb(color_hex)
            esta_extrayendo = jug.get("extrayendo", False)
            dir_jug = jug.get("direccion", "down")

            # Si el jugador extrae en el Reactor, dibujar particulas de energia radiactiva verde
            if esta_extrayendo:
                en_reactor = esta_en_zona_extraccion(j_rect)
                if en_reactor:
                    # Flujo de 3 particulas animadas entre el Reactor y el jugador
                    for frac in (0.28, 0.58, 0.88):
                        px_part = int(rx + (j_rect.centerx - rx) * frac)
                        py_part = int(ry + (j_rect.centery - ry) * frac)
                        part_surf = obtener_frame_particula(t_offset=frac)
                        if part_surf:
                            world_surface.blit(part_surf, (px_part - 16, py_part - 16))

                txt_estado = "[EXTRAYENDO +40 PTS/S]" if en_reactor else "[ACCION ACTIVA]"
                lbl_ext = font_accion.render(txt_estado, True, (57, 255, 20) if en_reactor else color_rgb)
                bg_ext = pygame.Rect(
                    j_rect.centerx - lbl_ext.get_width() // 2 - 6,
                    j_rect.bottom + 8,
                    lbl_ext.get_width() + 12,
                    lbl_ext.get_height() + 4,
                )
                pygame.draw.rect(world_surface, (15, 18, 24), bg_ext, border_radius=4)
                pygame.draw.rect(world_surface, (57, 255, 20) if en_reactor else color_rgb, bg_ext, 1, border_radius=4)
                world_surface.blit(lbl_ext, (bg_ext.x + 6, bg_ext.y + 2))

            # Dibujar el Sprite del Operador Hazmat segun color y direccion
            sprite_char = None
            if jug["es_local"] and avatar_img_surface is not None:
                sprite_char = pygame.transform.smoothscale(avatar_img_surface, (j_rect.width, j_rect.height))
            else:
                sprite_char = obtener_sprite_personaje(
                    color_hex=color_hex,
                    direccion=dir_jug,
                    extrayendo=esta_extrayendo,
                    size=(j_rect.width, j_rect.height),
                )

            if sprite_char:
                world_surface.blit(sprite_char, j_rect)
            else:
                pygame.draw.rect(world_surface, color_rgb, j_rect, border_radius=6)

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

        dest_x = max(0, (w - WORLD_WIDTH) // 2)
        dest_y = max(0, (h - WORLD_HEIGHT) // 2)
        view_w = min(w, WORLD_WIDTH)
        view_h = min(h, WORLD_HEIGHT)

        camara_rect = pygame.Rect(offset_x, offset_y, view_w, view_h)
        screen.blit(world_surface, (dest_x, dest_y), camara_rect)

        # =====================================================================
        # 4. HUD FIJO SOBRE LA CAMARA (TEMPORIZADOR, AVATAR Y MINI-RADAR)
        # =====================================================================
        dibujar_hud_arena(
            screen,
            controller,
            jugadores,
            tiempo_restante,
            (WORLD_WIDTH, WORLD_HEIGHT),
            muros_arena,
            REACTOR_CENTER,
            avatar_img_surface,
        )

        # Banner de Desempate Automatico (+2 min - CA-16.4)
        if banner_desempate_timer > 0.0:
            font_des = pygame.font.SysFont("Segoe UI", max(14, int(17 * sy)), bold=True)
            txt_des = "EMPATE EN 1ER LUGAR DETECTADO (CA-16.4): +2 MINUTOS DE DESEMPATE AUTOMATICO"
            lbl_des = font_des.render(txt_des, True, (255, 255, 255))
            des_rect = pygame.Rect(
                w // 2 - (lbl_des.get_width() + int(36 * sx)) // 2,
                int(88 * sy),
                lbl_des.get_width() + int(36 * sx),
                int(44 * sy),
            )
            pygame.draw.rect(screen, (180, 95, 20), des_rect, border_radius=8)
            pygame.draw.rect(screen, (255, 210, 110), des_rect, 2, border_radius=8)
            screen.blit(lbl_des, (des_rect.centerx - lbl_des.get_width() // 2, des_rect.centery - lbl_des.get_height() // 2))

        # Panel inferior izquierdo con el desglose en vivo de los segundos, puntos y meta
        font_guia = pygame.font.SysFont("Segoe UI", max(11, int(13 * sy)), bold=True)
        seg_mov = jugador_local["segundos_movimiento"]
        seg_reac = jugador_local["segundos_reactor"]
        pts_tot = jugador_local["puntos"]
        texto_contador = (
            f"Mov: {seg_mov}s (x10 = {seg_mov * 10} pts)  |  "
            f"Reactor: {seg_reac}s (x40 = {seg_reac * 40} pts)  |  "
            f"TOTAL: {pts_tot} / {puntos_meta} pts (META)  |  [CONFIG / PAUSA: ESC]"
        )
        lbl_guia = font_guia.render(texto_contador, True, (233, 196, 106))
        guia_bg = pygame.Rect(int(16 * sx), h - int(44 * sy), lbl_guia.get_width() + 24, int(32 * sy))
        pygame.draw.rect(screen, (20, 24, 34), guia_bg, border_radius=6)
        pygame.draw.rect(screen, (74, 144, 226), guia_bg, 1, border_radius=6)
        screen.blit(lbl_guia, (guia_bg.x + 12, guia_bg.centery - lbl_guia.get_height() // 2))

        # =====================================================================
        # 5. PANTALLA DE VICTORIA (US-17) CON NAVEGACION POR MANDO
        # =====================================================================
        btn_volver_victoria_rect = None
        if partida_finalizada and jugador_ganador is not None and accion_salida != "victoria":
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((8, 10, 16, 220))
            screen.blit(overlay, (0, 0))

            mw = min(w - 40, int(740 * sx))
            mh = min(h - 40, int(520 * sy))
            modal_rect = pygame.Rect(w // 2 - mw // 2, h // 2 - mh // 2, mw, mh)
            pygame.draw.rect(screen, (22, 27, 38), modal_rect, border_radius=14)
            pygame.draw.rect(screen, (233, 196, 106), modal_rect, 3, border_radius=14)

            f_vic_title = pygame.font.SysFont("Segoe UI", max(20, int(28 * sy)), bold=True)
            f_vic_sub = pygame.font.SysFont("Segoe UI", max(14, int(18 * sy)), bold=True)
            f_vic_row = pygame.font.SysFont("Segoe UI", max(12, int(15 * sy)), bold=True)

            t_vic = f_vic_title.render("PARTIDA FINALIZADA - PANTALLA DE VICTORIA", True, (233, 196, 106))
            screen.blit(t_vic, (modal_rect.centerx - t_vic.get_width() // 2, modal_rect.y + int(22 * sy)))

            # Avatar y Felicitacion del Ganador (CA-17.1 y CA-17.2)
            av_size = int(68 * sy)
            av_rect = pygame.Rect(modal_rect.centerx - av_size // 2, modal_rect.y + int(68 * sy), av_size, av_size)
            ganador_rgb = hex_to_rgb(jugador_ganador.get("color", "#E63946"))
            if jugador_ganador.get("es_local") and avatar_img_surface is not None:
                scaled_g = pygame.transform.smoothscale(avatar_img_surface, (av_size, av_size))
                screen.blit(scaled_g, av_rect)
            else:
                pygame.draw.rect(screen, ganador_rgb, av_rect, border_radius=10)
            pygame.draw.rect(screen, (255, 255, 255), av_rect, 3, border_radius=10)

            msg_fel = f"FELICIDADES {jugador_ganador['nombre'].upper()} - CAMPEON DE LA ARENA ({jugador_ganador['puntos']} PTS)"
            lbl_fel = f_vic_sub.render(msg_fel, True, (110, 235, 160))
            screen.blit(lbl_fel, (modal_rect.centerx - lbl_fel.get_width() // 2, av_rect.bottom + int(12 * sy)))

            # Tabla de Posiciones Ordenada (CA-17.3)
            ranking = sorted(jugadores, key=lambda item: item.get("puntos", 0), reverse=True)
            tabla_y = av_rect.bottom + int(50 * sy)
            row_h = int(46 * sy)
            for pos_idx, jug_r in enumerate(ranking):
                r_rect = pygame.Rect(
                    modal_rect.x + int(42 * sx),
                    tabla_y + pos_idx * (row_h + int(8 * sy)),
                    modal_rect.width - int(84 * sx),
                    row_h,
                )
                es_primero = pos_idx == 0
                bg_row = (36, 52, 46) if es_primero else (30, 35, 48)
                borde_row = (42, 157, 143) if es_primero else (65, 75, 95)
                pygame.draw.rect(screen, bg_row, r_rect, border_radius=8)
                pygame.draw.rect(screen, borde_row, r_rect, 2 if es_primero else 1, border_radius=8)

                swatch = pygame.Rect(r_rect.x + int(14 * sx), r_rect.centery - int(12 * sy), int(24 * sx), int(24 * sy))
                pygame.draw.rect(screen, hex_to_rgb(jug_r["color"]), swatch, border_radius=4)
                pygame.draw.rect(screen, (255, 255, 255), swatch, 1, border_radius=4)

                txt_pos = f"#{pos_idx + 1}   {jug_r['nombre']} ({jug_r['color_nombre']})"
                lbl_pos = f_vic_row.render(txt_pos, True, (255, 255, 255))
                screen.blit(lbl_pos, (swatch.right + int(14 * sx), r_rect.centery - lbl_pos.get_height() // 2))

                txt_pts_r = f"{jug_r['puntos']} PTS"
                lbl_pts_r = f_vic_row.render(txt_pts_r, True, (233, 196, 106) if es_primero else (195, 205, 225))
                screen.blit(
                    lbl_pts_r,
                    (r_rect.right - lbl_pts_r.get_width() - int(18 * sx), r_rect.centery - lbl_pts_r.get_height() // 2),
                )

            # Boton Volver al Lobby (CA-17.4 - accionable con mando o clic)
            btn_w = int(460 * sx)
            btn_h = int(46 * sy)
            btn_volver_victoria_rect = pygame.Rect(
                modal_rect.centerx - btn_w // 2,
                modal_rect.bottom - btn_h - int(20 * sy),
                btn_w,
                btn_h,
            )
            pygame.draw.rect(screen, (42, 157, 143), btn_volver_victoria_rect, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255), btn_volver_victoria_rect, 2, border_radius=8)
            lbl_btn_v = f_vic_row.render("VOLVER AL LOBBY [5to Boton Mando / Espacio / Enter]", True, (255, 255, 255))
            screen.blit(
                lbl_btn_v,
                (
                    btn_volver_victoria_rect.centerx - lbl_btn_v.get_width() // 2,
                    btn_volver_victoria_rect.centery - lbl_btn_v.get_height() // 2,
                ),
            )

        # =====================================================================
        # 5.B MODAL DE CONFIGURACION / PAUSA EN MEDIO DE LA PARTIDA (2 OPCIONES)
        # =====================================================================
        btn_pausa_rects = []
        if menu_pausa_activo and not partida_finalizada:
            overlay_pausa = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay_pausa.fill((8, 12, 18, 225))
            screen.blit(overlay_pausa, (0, 0))

            pw = min(w - 40, int(460 * sx))
            ph = min(h - 40, int(300 * sy))
            modal_pausa = pygame.Rect(w // 2 - pw // 2, h // 2 - ph // 2, pw, ph)
            pygame.draw.rect(screen, (22, 27, 38), modal_pausa, border_radius=12)
            pygame.draw.rect(screen, (42, 157, 143), modal_pausa, 3, border_radius=12)

            f_p_tit = pygame.font.SysFont("Segoe UI", max(18, int(22 * sy)), bold=True)
            f_p_sub = pygame.font.SysFont("Segoe UI", max(11, int(13 * sy)))
            f_p_btn = pygame.font.SysFont("Segoe UI", max(13, int(16 * sy)), bold=True)

            t_pt = f_p_tit.render("CONFIGURACION DE PARTIDA", True, (233, 196, 106))
            t_ps = f_p_sub.render("Juego en pausa - Selecciona una opcion con el mando:", True, (190, 200, 215))
            screen.blit(t_pt, (modal_pausa.centerx - t_pt.get_width() // 2, modal_pausa.y + int(20 * sy)))
            screen.blit(t_ps, (modal_pausa.centerx - t_ps.get_width() // 2, modal_pausa.y + int(48 * sy)))

            opciones_pausa = [
                ("1. REANUDAR", (42, 157, 143)),
                ("2. ABANDONAR PARTIDA", (230, 57, 70)),
            ]
            bw = int(380 * sx)
            bh = int(48 * sy)
            b_start_y = modal_pausa.y + int(85 * sy)

            for idx_op, (texto_op, col_base) in enumerate(opciones_pausa):
                by = b_start_y + idx_op * (bh + int(16 * sy))
                b_rect = pygame.Rect(modal_pausa.centerx - bw // 2, by, bw, bh)
                btn_pausa_rects.append(b_rect)

                es_foco = (opcion_pausa_idx == idx_op)
                col_fondo = col_base if es_foco else (30, 35, 48)
                col_borde = (255, 255, 255) if es_foco else (65, 75, 95)
                pygame.draw.rect(screen, col_fondo, b_rect, border_radius=8)
                pygame.draw.rect(screen, col_borde, b_rect, 3 if es_foco else 1, border_radius=8)

                prefijo = ">> " if es_foco else "   "
                lbl_b = f_p_btn.render(f"{prefijo}{texto_op}", True, (255, 255, 255))
                screen.blit(lbl_b, (b_rect.centerx - lbl_b.get_width() // 2, b_rect.centery - lbl_b.get_height() // 2))

            t_pie = f_p_sub.render("[UP/DOWN] Mover  |  [ACCION / ESPACIO] Confirmar  |  [ESC] Salir", True, (160, 175, 190))
            screen.blit(t_pie, (modal_pausa.centerx - t_pie.get_width() // 2, modal_pausa.bottom - int(24 * sy)))

        # =====================================================================
        # 6. EVENTOS DE VENTANA
        # =====================================================================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                accion_salida = "cerrar"
                corriendo = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(800, event.w), max(540, event.h)), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if not partida_finalizada:
                        menu_pausa_activo = not menu_pausa_activo
                        opcion_pausa_idx = 0
                    else:
                        accion_salida = "lobby"
                        corriendo = False
                elif menu_pausa_activo:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        opcion_pausa_idx = 0
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        opcion_pausa_idx = 1
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if opcion_pausa_idx == 0:
                            menu_pausa_activo = False
                        elif opcion_pausa_idx == 1:
                            otros = [j for j in jugadores if not j.get("es_local", False)]
                            if len(otros) == 1:
                                partida_finalizada = True
                                jugador_ganador = otros[0]
                                accion_salida = "victoria"
                                corriendo = False
                            else:
                                accion_salida = "lobby"
                                corriendo = False
                            menu_pausa_activo = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if menu_pausa_activo:
                    for idx_b, b_rect in enumerate(btn_pausa_rects):
                        if b_rect.collidepoint(event.pos):
                            if idx_b == 0:
                                menu_pausa_activo = False
                            elif idx_b == 1:
                                otros = [j for j in jugadores if not j.get("es_local", False)]
                                if len(otros) == 1:
                                    partida_finalizada = True
                                    jugador_ganador = otros[0]
                                    accion_salida = "victoria"
                                    corriendo = False
                                else:
                                    accion_salida = "lobby"
                                    corriendo = False
                                menu_pausa_activo = False
                            break
                elif partida_finalizada and btn_volver_victoria_rect and btn_volver_victoria_rect.collidepoint(event.pos):
                    accion_salida = "lobby"
                    corriendo = False

        pygame.display.flip()

    if accion_salida == "victoria":
        from Cliente.Interfaz.victoria_view import mostrar_pantalla_victoria
        accion_salida = mostrar_pantalla_victoria(
            controller, jugador_ganador, jugadores, screen, avatar_img_surface, input_manager
        )

    controller.partida_en_curso = False  # la configuracion vuelve a ser editable
    if accion_salida == "lobby":
        from Cliente.Interfaz.lobby_view import iniciar_lobby_pygame
        iniciar_lobby_pygame(controller, screen=screen)
    else:
        controller.cerrar_aplicacion()
