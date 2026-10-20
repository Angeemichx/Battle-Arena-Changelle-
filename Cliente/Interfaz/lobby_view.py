"""
Vista del Lobby Caminable en Pygame (US-09, US-06 y US-08).
- Se adapta dinamicamente a las dimensiones de la pantalla del computador.
- Restriccion notoria de minimo 2 jugadores para iniciar partida (CA-09.2 / CA-09.3).
- Zonas fisicas caminables pensadas para control con Mando (Gamepad / Teclado):
  1) Centro (Mesa de Comando): Abre el modal de Colores, Mapa/Parametros y Musica con Command.ACTION.
  2) Derecha (Zona de Despegue): Inicia la partida si hay >= 2 jugadores; si hay 1 jugador muestra rechazo notorio.
  3) Izquierda (Zona de Salida): Regresa al Menu Principal con Command.ACTION.
"""
from __future__ import annotations
import os
import time
import pygame

from Cliente.Inputs.gamepad_manager import (
    Command,
    create_default_input_manager,
    direction_from,
)
from Cliente.Interfaz.arena_collisions import (
    REACTOR_CENTER,
    SPAWN_POINTS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    mover_con_colisiones,
    obtener_colisiones_lobby,
    obtener_muros_arena,
)
from Cliente.Interfaz.Components.hud import dibujar_hud_lobby, hex_to_rgb
from Cliente.Interfaz.Components.ui_helpers import COLORES_AVATAR
from Cliente.Interfaz.Components.sprite_loader import (
    obtener_sprite_entorno,
    obtener_sprite_personaje,
)

TIPOS_MAPA = [
    "Estacion Estandar",
    "Reactor Inestable",
    "Laberinto Cerrado",
]
OPCIONES_TIEMPO_MIN = [1, 3, 5]
OPCIONES_PUNTOS_META = [300, 500, 800]
OPCIONES_CONGELAMIENTO_SEG = [3, 5, 10]
MODOS_FIN = ["tiempo", "puntos"]
NUM_OPCIONES_MAPAS = 7  # 3 mapas + duracion + meta + modo de fin + congelamiento (US-08)


def _siguiente_opcion(opciones: list, actual) -> object:
    """Siguiente valor de la lista circular; si el actual no esta en la lista (p. ej. venia del
    archivo guardado), empieza por el primero."""
    if actual in opciones:
        return opciones[(opciones.index(actual) + 1) % len(opciones)]
    return opciones[0]


def aplicar_opcion_configuracion(controller, op_idx: int) -> str:
    """
    Descripcion:
        Cicla el parametro de partida asociado a la opcion 3..6 del modal (US-08) y
        persiste la configuracion. Devuelve el mensaje a mostrar.
    Restricciones:
        Solo el creador puede cambiar y unicamente antes de iniciar la partida (CA-08.6).
    """
    if not controller.es_creador:
        return "ACCESO BLOQUEADO: Solo el creador puede cambiar mapa y parametros."
    if not controller.configuracion_editable():
        return "BLOQUEADO: la partida ya inicio, la configuracion no se puede cambiar."
    if op_idx == 3:
        controller.tiempo_partida_min = _siguiente_opcion(OPCIONES_TIEMPO_MIN, controller.tiempo_partida_min)
        msg = f"Duracion de partida: {controller.tiempo_partida_min} min"
    elif op_idx == 4:
        controller.puntos_meta = _siguiente_opcion(OPCIONES_PUNTOS_META, controller.puntos_meta)
        msg = f"Meta de puntos para ganar: {controller.puntos_meta} pts"
    elif op_idx == 5:
        controller.modo_fin = _siguiente_opcion(MODOS_FIN, controller.modo_fin)
        msg = "La partida termina por: " + ("tiempo" if controller.modo_fin == "tiempo" else "puntos")
    elif op_idx == 6:
        controller.tiempo_congelado_seg = _siguiente_opcion(OPCIONES_CONGELAMIENTO_SEG, controller.tiempo_congelado_seg)
        msg = f"Congelamiento: {controller.tiempo_congelado_seg} s"
    else:
        return ""
    if not controller.guardar_configuracion_partida():
        msg += " (no se pudo guardar)"
    return msg


def _generar_superficie_minimapa(tipo_mapa: str) -> pygame.Surface:
    """
    Descripcion:
        Renderiza en memoria una superficie a escala (540x390 px) que representa la vista
        previa del mapa de la Arena (3600x2600 px) con sus muros, spawns y Reactor Central.
    Entradas:
        tipo_mapa (str): Nombre de la variante del mapa seleccionada ('Estacion Estandar',
        'Reactor Inestable' o 'Laberinto Cerrado').
    Salidas:
        pygame.Surface: Superficie de Pygame con el minimapa dibujado.
    Restricciones:
        pygame debe estar inicializado antes de invocar esta funcion.
    """
    base_w, base_h = 540, 390
    surf = pygame.Surface((base_w, base_h))
    surf.fill((20, 24, 33))

    # Factores de proyeccion desde las dimensiones del mundo (3600x2600) hacia la miniatura (540x390)
    sx = base_w / float(WORLD_WIDTH)
    sy = base_h / float(WORLD_HEIGHT)

    for gx in range(0, WORLD_WIDTH, 300):
        x = int(gx * sx)
        pygame.draw.line(surf, (30, 35, 48), (x, 0), (x, base_h), 1)
    for gy in range(0, WORLD_HEIGHT, 300):
        y = int(gy * sy)
        pygame.draw.line(surf, (30, 35, 48), (0, y), (base_w, y), 1)

    for muro in obtener_muros_arena(tipo_mapa):
        r = pygame.Rect(
            int(muro.x * sx),
            int(muro.y * sy),
            max(2, int(muro.width * sx)),
            max(2, int(muro.height * sy)),
        )
        pygame.draw.rect(surf, (68, 76, 96), r)
        pygame.draw.rect(surf, (100, 112, 138), r, 1)

    for idx, (spx, spy) in SPAWN_POINTS.items():
        cx, cy = int(spx * sx), int(spy * sy)
        pygame.draw.circle(surf, (42, 157, 143), (cx, cy), 8)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 8, 1)

    rx, ry = int(REACTOR_CENTER[0] * sx), int(REACTOR_CENTER[1] * sy)
    pygame.draw.circle(surf, (0, 180, 216), (rx, ry), 24, 2)
    pygame.draw.circle(surf, (0, 235, 255), (rx, ry), 13)

    return surf


def iniciar_lobby_pygame(controller, screen: pygame.Surface | None = None) -> None:
    """
    Descripcion:
        Ejecuta el bucle principal a 60 FPS del Lobby Caminable en Pygame, permitiendo
        desplazar el avatar con mando/teclado hacia las 3 zonas fisicas (Salida, Mesa de
        Comando y Despegue), configurar colores/mapa/parametros con exclusion mutua y
        validar el minimo de 2 jugadores antes de pasar a la Arena.
    Entradas:
        controller (AppController): Instancia del controlador maestro con la sesion y red.
        screen (pygame.Surface | None): Superficie de ventana Pygame reutilizada o None para crearla.
    Salidas:
        None: Transfiere el flujo hacia iniciar_arena_pygame, mostrar_hub o cerrar_aplicacion.
    Restricciones:
        Bloquea el inicio de partida en la Zona de Despegue si hay menos de 2 jugadores
        conectados cuando controller.modo_estricto es True. Exige soltar y volver a presionar
        el boton de accion (Command.ACTION) al entrar al Lobby para evitar disparos accidentales.
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

    pygame.display.set_caption("Battle Arena Challenge - Lobby de Espera")
    clock = pygame.time.Clock()

    input_manager = create_default_input_manager(allow_keyboard_fallback=True)
    # Inicializar comandos_previos con los botones ya presionados al entrar al Lobby
    # y bloquear ACTION hasta que el usuario suelte fisicamente el boton y vuelva a tocarlo.
    comandos_previos: set[Command] = set(input_manager.poll())
    esperando_soltar_accion: bool = Command.ACTION in comandos_previos

    lista_colores = list(COLORES_AVATAR.items())
    orden_pestanas = ["colores", "mapas", "musica"]

    jugadores = [
        {
            "id": 1,
            "nombre": str(controller.usuario_actual),
            "color_nombre": controller.obtener_nombre_color(controller.avatar_color),
            "color": controller.avatar_color,
            "es_local": True,
            "rel_x": 0.50,
            "rel_y": 0.78,
            "pos_x": None,
            "pos_y": None,
            "rect": pygame.Rect(0, 0, 48, 48),
            "puntos": 0,
            "extrayendo": False,
            "direccion": "down",
        }
    ]

    if getattr(controller, "jugadores_sala", None) and len(controller.jugadores_sala) > 1:
        jugadores = controller.jugadores_sala
        jugadores[0]["nombre"] = str(controller.usuario_actual)
        jugadores[0]["color"] = controller.avatar_color
        jugadores[0]["color_nombre"] = controller.obtener_nombre_color(controller.avatar_color)
        # Al volver de una partida al Lobby, ubicar siempre al jugador local en la zona libre
        # inferior central (fuera de la Zona de Despegue) para no reiniciar otra partida por accidente
        jugadores[0]["rel_x"] = 0.50
        jugadores[0]["rel_y"] = 0.78
        jugadores[0]["pos_x"] = None
        jugadores[0]["pos_y"] = None

    minimapa_base = _generar_superficie_minimapa(controller.mapa_seleccionado)

    # Estado del modal y alertas notorias
    modal_abierto = False
    pestana_modal = "colores"
    fila_foco = 1
    indice_foco = 0
    mapa_ampliado = False
    mensaje_modal = ""
    alerta_rechazo_lobby = ""
    alerta_rechazo_expira = 0.0

    velocidad_base = 5.0
    corriendo = True
    accion_salida = None  # "menu" | "arena" | "cerrar"
    tamano_ventana_previo = screen.get_size()

    while corriendo:
        ahora = time.time()
        w, h = screen.get_size()
        sx = w / 1280.0
        sy = h / 720.0
        ventana_redimensionada = (w, h) != tamano_ventana_previo
        tamano_ventana_previo = (w, h)

        zona_caminable = pygame.Rect(
            int(50 * sx),
            int(92 * sy),
            int(800 * sx),
            int(585 * sy),
        )
        panel_derecho = pygame.Rect(
            int(875 * sx),
            int(92 * sy),
            int(365 * sx),
            int(585 * sy),
        )

        colisiones_lobby = obtener_colisiones_lobby(zona_caminable)
        muros_lobby = colisiones_lobby["muros"]
        mesa_rect = colisiones_lobby["mesa"]
        zona_interaccion = colisiones_lobby["zona_interaccion"]
        zona_despegue = colisiones_lobby["zona_despegue"]
        zona_salida = colisiones_lobby["zona_salida"]

        # Sincronizar jugadores conectados desde el servidor de red si existen
        if getattr(controller, "estado_partida_red", None):
            with controller.estado_red_lock:
                remotos = controller.estado_partida_red.get("jugadores", [])
                for idx_r, datos_r in enumerate(remotos):
                    if idx_r == 0:
                        continue
                    while len(jugadores) <= idx_r and len(jugadores) < 4:
                        usados = {j["color"].upper() for j in jugadores}
                        c_nom, c_hex = "Azul", "#1D3557"
                        for nc, hc in lista_colores:
                            if hc.upper() not in usados:
                                c_nom, c_hex = nc, hc
                                break
                        pos_def = [(0.50, 0.20), (0.72, 0.22), (0.28, 0.22)]
                        rx_d, ry_d = pos_def[(len(jugadores) - 1) % len(pos_def)]
                        jugadores.append({
                            "id": datos_r.get("id", len(jugadores) + 1),
                            "nombre": datos_r.get("nombre", f"Piloto_{len(jugadores) + 1}"),
                            "color_nombre": c_nom,
                            "color": c_hex,
                            "es_local": False,
                            "rel_x": rx_d,
                            "rel_y": ry_d,
                            "pos_x": None,
                            "pos_y": None,
                            "rect": pygame.Rect(0, 0, 48, 48),
                            "puntos": datos_r.get("puntaje", 0),
                            "extrayendo": False,
                        })

        # Resolucion automatica de duplicados de color al unirse (CA-10.3)
        if hasattr(controller, "resolver_conflicto_color"):
            color_resuelto = controller.resolver_conflicto_color(jugadores)
            if color_resuelto:
                alerta_rechazo_lobby = (
                    f"COLOR REASIGNADO: Tu color original estaba en uso. "
                    f"Se te asigno: {color_resuelto}."
                )
                alerta_rechazo_expira = ahora + 4.5

        hitbox_size = max(34, int(48 * min(sx, sy)))
        for jug in jugadores:
            if jug.get("pos_x") is None or jug.get("pos_y") is None or ventana_redimensionada:
                px = zona_caminable.x + int(round(jug["rel_x"] * (zona_caminable.width - hitbox_size)))
                py = zona_caminable.y + int(round(jug["rel_y"] * (zona_caminable.height - hitbox_size)))
                jug["pos_x"] = px
                jug["pos_y"] = py
            jug["rect"] = pygame.Rect(int(jug["pos_x"]), int(jug["pos_y"]), hitbox_size, hitbox_size)

        jugador_local = jugadores[0]
        cerca_de_mesa = jugador_local["rect"].colliderect(zona_interaccion)
        en_zona_despegue = jugador_local["rect"].colliderect(zona_despegue)
        en_zona_salida = jugador_local["rect"].colliderect(zona_salida)
        puede_iniciar = (len(jugadores) >= 2) if controller.modo_estricto else True

        minimapa_rect = pygame.Rect(
            panel_derecho.x + int(22 * sx),
            panel_derecho.y + int(38 * sy),
            panel_derecho.width - int(44 * sx),
            int(195 * sy),
        )
        btn_ampliar_rect = pygame.Rect(
            minimapa_rect.x,
            minimapa_rect.bottom + int(6 * sy),
            minimapa_rect.width,
            int(28 * sy),
        )

        # =====================================================================
        # LECTURA DE COMANDOS DEL MANDO / TECLADO (CON BLOQUEO HASTA SOLTAR BOTON)
        # =====================================================================
        comandos_actuales = input_manager.poll()
        if esperando_soltar_accion:
            if Command.ACTION not in comandos_actuales:
                esperando_soltar_accion = False
            comandos_nuevos = (comandos_actuales - comandos_previos) - {Command.ACTION}
        else:
            comandos_nuevos = comandos_actuales - comandos_previos
            if Command.ACTION in comandos_nuevos:
                esperando_soltar_accion = True
        comandos_previos = set(comandos_actuales)

        colores_ocupados_otros = {
            j["color"]: j["nombre"] for j in jugadores if not j["es_local"]
        }

        if modal_abierto:
            if Command.UP in comandos_nuevos:
                fila_foco = max(0, fila_foco - 1)
                if fila_foco == 0:
                    indice_foco = orden_pestanas.index(pestana_modal)
                elif fila_foco == 1:
                    indice_foco = 0
            elif Command.DOWN in comandos_nuevos:
                fila_foco = min(2, fila_foco + 1)
                if fila_foco == 1:
                    indice_foco = 0

            elif Command.LEFT in comandos_nuevos:
                if fila_foco == 0:
                    idx_tab = (orden_pestanas.index(pestana_modal) - 1) % len(orden_pestanas)
                    pestana_modal = orden_pestanas[idx_tab]
                    indice_foco = idx_tab
                    mensaje_modal = ""
                elif fila_foco == 1:
                    if pestana_modal == "colores":
                        indice_foco = (indice_foco - 1) % len(lista_colores)
                    elif pestana_modal == "mapas":
                        indice_foco = (indice_foco - 1) % NUM_OPCIONES_MAPAS
                    elif pestana_modal == "musica":
                        controller.volumen_musica = max(0, controller.volumen_musica - 10)
                        controller.actualizar_volumen_audio()
                        mensaje_modal = f"Volumen ajustado a {controller.volumen_musica}%"

            elif Command.RIGHT in comandos_nuevos:
                if fila_foco == 0:
                    idx_tab = (orden_pestanas.index(pestana_modal) + 1) % len(orden_pestanas)
                    pestana_modal = orden_pestanas[idx_tab]
                    indice_foco = idx_tab
                    mensaje_modal = ""
                elif fila_foco == 1:
                    if pestana_modal == "colores":
                        indice_foco = (indice_foco + 1) % len(lista_colores)
                    elif pestana_modal == "mapas":
                        indice_foco = (indice_foco + 1) % NUM_OPCIONES_MAPAS
                    elif pestana_modal == "musica":
                        controller.volumen_musica = min(100, controller.volumen_musica + 10)
                        controller.actualizar_volumen_audio()
                        mensaje_modal = f"Volumen ajustado a {controller.volumen_musica}%"

            elif Command.ACTION in comandos_nuevos:
                if fila_foco == 0:
                    fila_foco = 1
                    indice_foco = 0
                elif fila_foco == 1:
                    if pestana_modal == "colores":
                        nom_c, hex_c = lista_colores[indice_foco % len(lista_colores)]
                        ocupado_por = colores_ocupados_otros.get(hex_c)
                        if ocupado_por:
                            mensaje_modal = f"RECHAZADO: El color {nom_c} ya esta ocupado por {ocupado_por}."
                        else:
                            controller.avatar_color = hex_c
                            jugador_local["color"] = hex_c
                            jugador_local["color_nombre"] = nom_c
                            controller.guardar_config_local()
                            mensaje_modal = f"Color seleccionado: {nom_c}."
                    elif pestana_modal == "mapas":
                        op_idx = indice_foco % NUM_OPCIONES_MAPAS
                        if not controller.es_creador:
                            mensaje_modal = "ACCESO BLOQUEADO: Solo el creador puede cambiar mapa y parametros."
                        elif op_idx < 3 and not controller.configuracion_editable():
                            mensaje_modal = "BLOQUEADO: la partida ya inicio, la configuracion no se puede cambiar."
                        elif op_idx < 3:
                            nombre_mapa = TIPOS_MAPA[op_idx]
                            controller.mapa_seleccionado = nombre_mapa
                            minimapa_base = _generar_superficie_minimapa(nombre_mapa)
                            mensaje_modal = f"Mapa cambiado a: {nombre_mapa}"
                        else:
                            mensaje_modal = aplicar_opcion_configuracion(controller, op_idx)
                    elif pestana_modal == "musica":
                        controller.volumen_musica = 0 if controller.volumen_musica > 0 else 50
                        controller.actualizar_volumen_audio()
                        mensaje_modal = f"Volumen: {controller.volumen_musica}%"
                elif fila_foco == 2:
                    modal_abierto = False
                    mensaje_modal = ""

        else:
            if Command.ACTION in comandos_nuevos:
                if mapa_ampliado:
                    mapa_ampliado = False
                elif cerca_de_mesa:
                    modal_abierto = True
                    fila_foco = 1
                    indice_foco = 0
                    mensaje_modal = ""
                elif en_zona_despegue:
                    if puede_iniciar:
                        controller.jugadores_sala = jugadores
                        accion_salida = "arena"
                        corriendo = False
                    else:
                        alerta_rechazo_lobby = (
                            f"RECHAZO DE INICIO: Se requieren minimo 2 jugadores conectados "
                            f"para iniciar la partida (Actual: {len(jugadores)}/4)."
                        )
                        alerta_rechazo_expira = ahora + 4.0
                elif en_zona_salida:
                    accion_salida = "menu"
                    corriendo = False

        # =====================================================================
        # DIBUJO DE PANTALLA DEL LOBBY
        # =====================================================================
        screen.fill((18, 20, 27))

        dibujar_hud_lobby(screen, controller, jugadores)

        # Zona Caminable de la Nave
        pygame.draw.rect(screen, (26, 30, 40), zona_caminable, border_radius=8)

        paso_grid = max(40, int(65 * min(sx, sy)))
        for gx in range(zona_caminable.left + paso_grid, zona_caminable.right, paso_grid):
            pygame.draw.line(screen, (33, 38, 50), (gx, zona_caminable.top), (gx, zona_caminable.bottom), 1)
        for gy in range(zona_caminable.top + paso_grid, zona_caminable.bottom, paso_grid):
            pygame.draw.line(screen, (33, 38, 50), (zona_caminable.left, gy), (zona_caminable.right, gy), 1)

        for borde in colisiones_lobby["bordes"]:
            pygame.draw.rect(screen, (58, 66, 86), borde)
            pygame.draw.rect(screen, (88, 98, 124), borde, 1)

        font_bold = pygame.font.SysFont("Segoe UI", max(12, int(15 * sy)), bold=True)
        font_reg = pygame.font.SysFont("Segoe UI", max(11, int(13 * sy)))
        font_small = pygame.font.SysFont("Segoe UI", max(10, int(12 * sy)))

        # 1. Izquierda: Zona Caminable de Salida mediante Sprite
        sp_salida = obtener_sprite_entorno("sign_salida", (zona_salida.width, zona_salida.height))
        if sp_salida:
            screen.blit(sp_salida, zona_salida)
        else:
            color_sal = (184, 46, 56) if en_zona_salida else (68, 34, 42)
            pygame.draw.rect(screen, color_sal, zona_salida, border_radius=8)
            pygame.draw.rect(screen, (230, 95, 105), zona_salida, 2, border_radius=8)
        if en_zona_salida:
            pygame.draw.rect(screen, (255, 255, 255), zona_salida, 2, border_radius=8)

        # 2. Derecha: Zona Caminable de Despegue mediante Sprite
        sp_despegue = obtener_sprite_entorno("sign_despegue", (zona_despegue.width, zona_despegue.height))
        if sp_despegue:
            screen.blit(sp_despegue, zona_despegue)
        else:
            color_pad = (42, 157, 143) if en_zona_despegue else (34, 58, 62)
            pygame.draw.rect(screen, color_pad, zona_despegue, border_radius=8)
        if en_zona_despegue:
            borde_act = (90, 255, 200) if puede_iniciar else (255, 80, 80)
            pygame.draw.rect(screen, borde_act, zona_despegue, 2, border_radius=8)

        # 3. Centro: Mesa de Comando mediante Sprite
        sp_mesa = obtener_sprite_entorno("mesa_comando", (mesa_rect.width, mesa_rect.height))
        if sp_mesa:
            screen.blit(sp_mesa, mesa_rect)
        else:
            pygame.draw.rect(screen, (45, 55, 78), mesa_rect, border_radius=8)
            pygame.draw.rect(screen, (100, 140, 200), mesa_rect, 2, border_radius=8)

        # Cartel holografico sobre la mesa
        sp_sign_mesa = obtener_sprite_entorno("sign_mesa_comando", (int(170 * sx), int(42 * sy)))
        if sp_sign_mesa:
            screen.blit(sp_sign_mesa, (mesa_rect.centerx - sp_sign_mesa.get_width() // 2, mesa_rect.top - sp_sign_mesa.get_height() - 6))

        if cerca_de_mesa:
            pygame.draw.rect(screen, (57, 255, 20), mesa_rect, 2, border_radius=8)

        lbl_mesa1 = font_bold.render("MESA DE", True, (255, 255, 255))
        lbl_mesa2 = font_bold.render("COMANDO", True, (160, 200, 255))
        screen.blit(lbl_mesa1, (mesa_rect.centerx - lbl_mesa1.get_width() // 2, mesa_rect.centery - lbl_mesa1.get_height()))
        screen.blit(lbl_mesa2, (mesa_rect.centerx - lbl_mesa2.get_width() // 2, mesa_rect.centery + 2))

        if (cerca_de_mesa or en_zona_despegue or en_zona_salida) and not modal_abierto:
            if cerca_de_mesa:
                txt_aviso = "Presiona [Boton Accion / Espacio] para Configurar Colores, Mapa y Parametros"
            elif en_zona_despegue:
                if puede_iniciar:
                    txt_aviso = "Presiona [Boton Accion / Espacio] para Iniciar la Partida"
                else:
                    txt_aviso = "Faltan jugadores (Minimo 2). Presiona F2 para simular conexion de otro jugador."
            else:
                txt_aviso = "Presiona [Boton Accion / Espacio] para Volver al Menu Principal"
            aviso_surf = font_bold.render(txt_aviso, True, (233, 196, 106))
            aviso_bg = pygame.Rect(
                zona_caminable.centerx - aviso_surf.get_width() // 2 - 12,
                zona_caminable.bottom - int(48 * sy),
                aviso_surf.get_width() + 24,
                aviso_surf.get_height() + 10,
            )
            pygame.draw.rect(screen, (20, 24, 34), aviso_bg, border_radius=6)
            pygame.draw.rect(screen, (233, 196, 106), aviso_bg, 1, border_radius=6)
            screen.blit(aviso_surf, (aviso_bg.x + 12, aviso_bg.y + 5))

        # Dibujar Jugadores en la Sala Caminable con Sprites Hazmat
        for jug in jugadores:
            j_rect = jug["rect"]
            c_hex = jug.get("color", "#E63946")
            d_jug = jug.get("direccion", "down")

            sp_jug = obtener_sprite_personaje(
                color_hex=c_hex,
                direccion=d_jug,
                extrayendo=False,
                size=(j_rect.width, j_rect.height),
            )

            if sp_jug:
                screen.blit(sp_jug, j_rect)
            else:
                pygame.draw.rect(screen, hex_to_rgb(c_hex), j_rect, border_radius=6)

            lbl_nom = font_small.render(jug["nombre"], True, (255, 255, 255))
            screen.blit(lbl_nom, (j_rect.centerx - lbl_nom.get_width() // 2, j_rect.top - lbl_nom.get_height() - 4))

        # Cartel Notorio de Rechazo si intenta iniciar partida con menos de 2 jugadores
        if ahora < alerta_rechazo_expira and alerta_rechazo_lobby:
            surf_rej = font_bold.render(alerta_rechazo_lobby, True, (255, 220, 220))
            rej_bg = pygame.Rect(
                zona_caminable.centerx - surf_rej.get_width() // 2 - 18,
                zona_caminable.top + int(22 * sy),
                surf_rej.get_width() + 36,
                surf_rej.get_height() + 18,
            )
            pygame.draw.rect(screen, (95, 18, 26), rej_bg, border_radius=8)
            pygame.draw.rect(screen, (255, 80, 95), rej_bg, 3, border_radius=8)
            screen.blit(surf_rej, (rej_bg.x + 18, rej_bg.y + 9))

        # =====================================================================
        # PANEL LATERAL DERECHO (MINIMAPA Y JUGADORES ADAPTADOS AL ESPACIO)
        # =====================================================================
        pygame.draw.rect(screen, (26, 30, 40), panel_derecho, border_radius=8)
        pygame.draw.rect(screen, (58, 66, 86), panel_derecho, 2, border_radius=8)

        lbl_prev = font_bold.render(f"MAPA: {controller.mapa_seleccionado.upper()}", True, (255, 255, 255))
        screen.blit(lbl_prev, (panel_derecho.x + int(22 * sx), panel_derecho.y + int(10 * sy)))

        mini_scaled = pygame.transform.smoothscale(minimapa_base, (minimapa_rect.width, minimapa_rect.height))
        screen.blit(mini_scaled, minimapa_rect)
        pygame.draw.rect(screen, (90, 105, 135), minimapa_rect, 2)

        pygame.draw.rect(screen, (43, 45, 66), btn_ampliar_rect, border_radius=5)
        lbl_amp = font_small.render(
            f"Ver Mapa | Tiempo: {controller.tiempo_partida_min}m | Meta: {controller.puntos_meta}pts",
            True,
            (200, 215, 240),
        )
        screen.blit(
            lbl_amp,
            (btn_ampliar_rect.centerx - lbl_amp.get_width() // 2, btn_ampliar_rect.centery - lbl_amp.get_height() // 2),
        )

        # Seccion de Jugadores adaptada para completar todo el espacio restante del panel
        lbl_slots = font_bold.render("JUGADORES EN SALA (Min 2 / Max 4):", True, (200, 210, 225))
        titulo_slots_y = btn_ampliar_rect.bottom + int(14 * sy)
        screen.blit(lbl_slots, (minimapa_rect.x, titulo_slots_y))

        slot_start_y = titulo_slots_y + lbl_slots.get_height() + int(10 * sy)
        margen_inf = int(18 * sy)
        espacio_disponible_h = max(140, (panel_derecho.bottom - margen_inf) - slot_start_y)
        sep_slots = max(8, int(10 * sy))
        slot_h = (espacio_disponible_h - (3 * sep_slots)) // 4

        for i in range(4):
            sy_pos = slot_start_y + i * (slot_h + sep_slots)
            s_rect = pygame.Rect(minimapa_rect.x, sy_pos, minimapa_rect.width, slot_h)
            pygame.draw.rect(screen, (20, 23, 31), s_rect, border_radius=7)
            if i < len(jugadores):
                j_slot = jugadores[i]
                pygame.draw.rect(screen, hex_to_rgb(j_slot["color"]), s_rect, 2, border_radius=7)
                box_sz = max(20, int(slot_h * 0.48))
                c_box = pygame.Rect(
                    s_rect.x + int(12 * sx),
                    s_rect.centery - box_sz // 2,
                    box_sz,
                    box_sz,
                )
                pygame.draw.rect(screen, hex_to_rgb(j_slot["color"]), c_box, border_radius=4)
                pygame.draw.rect(screen, (255, 255, 255), c_box, 1, border_radius=4)

                etiqueta = f"{i + 1}. {j_slot['nombre']}"
                sub_etiqueta = f"Color: {j_slot['color_nombre']} | CONECTADO"
                surf_s = font_bold.render(etiqueta, True, (255, 255, 255))
                surf_sub = font_small.render(sub_etiqueta, True, (165, 175, 195))
                screen.blit(surf_s, (c_box.right + int(12 * sx), s_rect.y + int(slot_h * 0.16)))
                screen.blit(surf_sub, (c_box.right + int(12 * sx), s_rect.y + int(slot_h * 0.54)))
            else:
                pygame.draw.rect(screen, (45, 50, 65), s_rect, 1, border_radius=7)
                surf_vacio = font_reg.render(f"Ranura {i + 1}: Esperando jugador... (F2 simula)", True, (110, 120, 140))
                screen.blit(surf_vacio, (s_rect.x + int(12 * sx), s_rect.centery - surf_vacio.get_height() // 2))

        # =====================================================================
        # VENTANA MODAL SUPERPUESTA (NAVEGABLE CON MANDO Y RATON)
        # =====================================================================
        rects_modal = {}
        if modal_abierto:
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 175))
            screen.blit(overlay, (0, 0))

            modal_w = int(720 * sx)
            modal_h = int(510 * sy)
            modal_rect = pygame.Rect((w - modal_w) // 2, (h - modal_h) // 2, modal_w, modal_h)
            pygame.draw.rect(screen, (26, 30, 42), modal_rect, border_radius=12)
            pygame.draw.rect(screen, (74, 144, 226), modal_rect, 2, border_radius=12)

            tab_w = (modal_w - int(60 * sx)) // 3
            tab_h = max(34, int(40 * sy))
            tab_y = modal_rect.y + int(18 * sy)

            tabs_info = [
                ("colores", "1. COLORES Y AVATAR"),
                ("mapas", "2. MAPA Y PARAMETROS"),
                ("musica", "3. MUSICA Y AUDIO"),
            ]
            for idx, (t_id, t_label) in enumerate(tabs_info):
                tx = modal_rect.x + int(20 * sx) + idx * (tab_w + int(10 * sx))
                t_rect = pygame.Rect(tx, tab_y, tab_w, tab_h)
                activo = pestana_modal == t_id
                pygame.draw.rect(
                    screen,
                    (31, 83, 141) if activo else (43, 45, 66),
                    t_rect,
                    border_radius=6,
                )
                if fila_foco == 0 and activo:
                    pygame.draw.rect(screen, (233, 196, 106), t_rect, 3, border_radius=6)

                lbl_t = font_bold.render(t_label, True, (255, 255, 255))
                screen.blit(lbl_t, (t_rect.centerx - lbl_t.get_width() // 2, t_rect.centery - lbl_t.get_height() // 2))
                rects_modal[f"tab_{t_id}"] = t_rect

            content_y = tab_y + tab_h + int(18 * sy)

            if pestana_modal == "colores":
                lbl_inst = font_reg.render(
                    "Mando: Izquierda/Derecha para elegir color y Boton Accion para confirmar:",
                    True,
                    (210, 215, 225),
                )
                screen.blit(lbl_inst, (modal_rect.x + int(28 * sx), content_y))

                btn_c_w = int(118 * sx)
                btn_c_h = int(88 * sy)
                start_cx = modal_rect.x + int(28 * sx)
                cy_box = content_y + int(32 * sy)

                for idx, (nombre_c, hex_c) in enumerate(lista_colores):
                    cx_box = start_cx + idx * (btn_c_w + int(14 * sx))
                    c_rect = pygame.Rect(cx_box, cy_box, btn_c_w, btn_c_h)
                    ocupado_por = colores_ocupados_otros.get(hex_c)
                    es_mio = controller.avatar_color.upper() == hex_c.upper()
                    foco_mando = (fila_foco == 1 and (indice_foco % len(lista_colores)) == idx)

                    pygame.draw.rect(screen, hex_to_rgb(hex_c), c_rect, border_radius=8)
                    if es_mio:
                        pygame.draw.rect(screen, (255, 255, 255), c_rect, 4, border_radius=8)
                        est_txt = "ACTIVO"
                    elif ocupado_por:
                        sombra = pygame.Surface((c_rect.width, c_rect.height), pygame.SRCALPHA)
                        sombra.fill((0, 0, 0, 155))
                        screen.blit(sombra, c_rect.topleft)
                        pygame.draw.rect(screen, (230, 57, 70), c_rect, 2, border_radius=8)
                        est_txt = "OCUPADO"
                    else:
                        pygame.draw.rect(screen, (40, 45, 60), c_rect, 2, border_radius=8)
                        est_txt = "LIBRE"

                    if foco_mando:
                        pygame.draw.rect(screen, (233, 196, 106), c_rect.inflate(8, 8), 3, border_radius=10)

                    s_nom = font_bold.render(nombre_c, True, (255, 255, 255))
                    s_est = font_small.render(est_txt, True, (255, 255, 255))
                    screen.blit(s_nom, (c_rect.centerx - s_nom.get_width() // 2, c_rect.y + int(16 * sy)))
                    screen.blit(s_est, (c_rect.centerx - s_est.get_width() // 2, c_rect.bottom - int(26 * sy)))

                    rects_modal[f"color_{nombre_c}"] = (c_rect, nombre_c, hex_c, ocupado_por, idx)

            elif pestana_modal == "mapas":
                if controller.es_creador:
                    lbl_m_info = font_bold.render(
                        "Anfitrion: Configura Mapa, Duracion, Meta, Modo y Congelamiento (Mando o Raton):",
                        True,
                        (42, 157, 143),
                    )
                else:
                    lbl_m_info = font_bold.render(
                        "[CANDADO] SOLO EL CREADOR DE LA PARTIDA PUEDE MODIFICAR MAPA Y PARAMETROS",
                        True,
                        (233, 196, 106),
                    )
                screen.blit(lbl_m_info, (modal_rect.x + int(28 * sx), content_y))

                for idx, nombre_mapa in enumerate(TIPOS_MAPA):
                    m_rect = pygame.Rect(
                        modal_rect.x + int(28 * sx),
                        content_y + int(32 * sy) + idx * int(48 * sy),
                        modal_w - int(56 * sx),
                        int(40 * sy),
                    )
                    seleccionado = controller.mapa_seleccionado == nombre_mapa
                    foco_mando = (fila_foco == 1 and (indice_foco % NUM_OPCIONES_MAPAS) == idx)

                    bg_m = ((42, 157, 143) if seleccionado else (43, 45, 66)) if controller.es_creador else (38, 40, 50)
                    pygame.draw.rect(screen, bg_m, m_rect, border_radius=7)
                    pygame.draw.rect(screen, (255, 255, 255) if seleccionado else (80, 90, 110), m_rect, 2, border_radius=7)
                    if foco_mando:
                        pygame.draw.rect(screen, (233, 196, 106), m_rect.inflate(6, 6), 3, border_radius=9)

                    prefijo = "[MAPA ACTIVO] " if seleccionado else "Mapa: "
                    sufijo = "" if controller.es_creador else "   [BLOQUEADO - CANDADO]"
                    lbl_mp = font_bold.render(f"{prefijo}{nombre_mapa}{sufijo}", True, (255, 255, 255))
                    screen.blit(lbl_mp, (m_rect.x + int(16 * sx), m_rect.centery - lbl_mp.get_height() // 2))
                    rects_modal[f"mapa_{idx}"] = (m_rect, nombre_mapa)

                # Selectores de Parametros de Partida (US-08): 2 filas x 2 botones
                param_y = content_y + int(32 * sy) + 3 * int(48 * sy) + int(2 * sy)
                param_w = (modal_w - int(72 * sx)) // 2
                alto_p = int(40 * sy)
                editable = controller.es_creador and controller.configuracion_editable()
                etiqueta_modo = "Tiempo" if controller.modo_fin == "tiempo" else "Puntos"
                params = [
                    ("btn_tiempo", 0, 0, f"Duracion: {controller.tiempo_partida_min} Minutos"),
                    ("btn_puntos", 1, 0, f"Meta Ganador: {controller.puntos_meta} Puntos"),
                    ("btn_modo", 0, 1, f"Termina por: {etiqueta_modo}"),
                    ("btn_congela", 1, 1, f"Congelamiento: {controller.tiempo_congelado_seg} s"),
                ]
                for p_idx, (clave, col, fila, p_txt) in enumerate(params):
                    p_rect = pygame.Rect(
                        modal_rect.x + int(28 * sx) + col * (param_w + int(16 * sx)),
                        param_y + fila * (alto_p + int(6 * sy)),
                        param_w,
                        alto_p,
                    )
                    foco_p = (fila_foco == 1 and (indice_foco % NUM_OPCIONES_MAPAS) == (3 + p_idx))
                    pygame.draw.rect(screen, (31, 83, 141) if editable else (38, 40, 50), p_rect, border_radius=7)
                    pygame.draw.rect(screen, (120, 160, 220), p_rect, 1, border_radius=7)
                    if foco_p:
                        pygame.draw.rect(screen, (233, 196, 106), p_rect.inflate(6, 6), 3, border_radius=9)
                    s_pt = font_bold.render(p_txt, True, (255, 255, 255) if editable else (150, 155, 170))
                    screen.blit(s_pt, (p_rect.centerx - s_pt.get_width() // 2, p_rect.centery - s_pt.get_height() // 2))
                    rects_modal[clave] = p_rect

            elif pestana_modal == "musica":
                lbl_au = font_bold.render(
                    f"Volumen de Musica Continua: {controller.volumen_musica}% (Mando: Izq/Der ajusta, Accion silencia)",
                    True,
                    (255, 255, 255),
                )
                screen.blit(lbl_au, (modal_rect.x + int(28 * sx), content_y + int(10 * sy)))

                barra_vol = pygame.Rect(
                    modal_rect.x + int(28 * sx),
                    content_y + int(55 * sy),
                    modal_w - int(56 * sx),
                    int(28 * sy),
                )
                pygame.draw.rect(screen, (18, 20, 28), barra_vol, border_radius=6)
                ancho_lleno = int((controller.volumen_musica / 100.0) * barra_vol.width)
                if ancho_lleno > 0:
                    pygame.draw.rect(
                        screen,
                        (42, 157, 143),
                        pygame.Rect(barra_vol.x, barra_vol.y, ancho_lleno, barra_vol.height),
                        border_radius=6,
                    )
                borde_barra = (233, 196, 106) if fila_foco == 1 else (90, 105, 130)
                pygame.draw.rect(screen, borde_barra, barra_vol, 2, border_radius=6)
                rects_modal["barra_vol"] = barra_vol

                btn_menos = pygame.Rect(barra_vol.x, barra_vol.bottom + int(22 * sy), int(130 * sx), int(40 * sy))
                btn_mas = pygame.Rect(btn_menos.right + int(16 * sx), btn_menos.y, int(130 * sx), int(40 * sy))
                btn_mute = pygame.Rect(btn_mas.right + int(16 * sx), btn_menos.y, int(170 * sx), int(40 * sy))

                for b_r, b_t in [(btn_menos, "- 10% Volumen"), (btn_mas, "+ 10% Volumen"), (btn_mute, "Silenciar (0%)")]:
                    pygame.draw.rect(screen, (43, 45, 66), b_r, border_radius=6)
                    s_bt = font_reg.render(b_t, True, (255, 255, 255))
                    screen.blit(s_bt, (b_r.centerx - s_bt.get_width() // 2, b_r.centery - s_bt.get_height() // 2))

                rects_modal["vol_menos"] = btn_menos
                rects_modal["vol_mas"] = btn_mas
                rects_modal["vol_mute"] = btn_mute

            lbl_guia_m = font_small.render(
                "Navegacion Mando: Arriba/Abajo cambia entre Pestañas, Opciones y LISTO | Accion selecciona",
                True,
                (160, 175, 195),
            )
            screen.blit(lbl_guia_m, (modal_rect.x + int(28 * sx), modal_rect.bottom - int(90 * sy)))

            if mensaje_modal:
                s_msg = font_reg.render(mensaje_modal, True, (233, 196, 106))
                screen.blit(s_msg, (modal_rect.x + int(28 * sx), modal_rect.bottom - int(116 * sy)))

            btn_listo = pygame.Rect(
                modal_rect.centerx - int(110 * sx),
                modal_rect.bottom - int(54 * sy),
                int(220 * sx),
                int(42 * sy),
            )
            pygame.draw.rect(screen, (42, 157, 143), btn_listo, border_radius=8)
            if fila_foco == 2:
                pygame.draw.rect(screen, (233, 196, 106), btn_listo.inflate(8, 8), 3, border_radius=10)
            lbl_listo = font_bold.render("LISTO", True, (255, 255, 255))
            screen.blit(
                lbl_listo,
                (btn_listo.centerx - lbl_listo.get_width() // 2, btn_listo.centery - lbl_listo.get_height() // 2),
            )
            rects_modal["btn_listo"] = btn_listo

        # =====================================================================
        # MODAL DE VISTA AMPLIADA DEL MAPA
        # =====================================================================
        btn_cerrar_amp = None
        if mapa_ampliado and not modal_abierto:
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 185))
            screen.blit(overlay, (0, 0))

            amp_w = int(840 * sx)
            amp_h = int(580 * sy)
            amp_rect = pygame.Rect((w - amp_w) // 2, (h - amp_h) // 2, amp_w, amp_h)
            pygame.draw.rect(screen, (24, 28, 38), amp_rect, border_radius=10)
            pygame.draw.rect(screen, (90, 120, 170), amp_rect, 2, border_radius=10)

            map_inner = pygame.Rect(
                amp_rect.x + int(20 * sx),
                amp_rect.y + int(20 * sy),
                amp_w - int(40 * sx),
                amp_h - int(85 * sy),
            )
            big_map = pygame.transform.smoothscale(minimapa_base, (map_inner.width, map_inner.height))
            screen.blit(big_map, map_inner)

            btn_cerrar_amp = pygame.Rect(
                amp_rect.centerx - int(100 * sx),
                amp_rect.bottom - int(52 * sy),
                int(200 * sx),
                int(38 * sy),
            )
            pygame.draw.rect(screen, (42, 157, 143), btn_cerrar_amp, border_radius=6)
            lbl_ca = font_bold.render("LISTO (CERRAR MAPA)", True, (255, 255, 255))
            screen.blit(
                lbl_ca,
                (btn_cerrar_amp.centerx - lbl_ca.get_width() // 2, btn_cerrar_amp.centery - lbl_ca.get_height() // 2),
            )

        # =====================================================================
        # GESTION DE EVENTOS DE VENTANA, TECLAS DE PRUEBA (F2/F3) Y RATON
        # =====================================================================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                accion_salida = "cerrar"
                corriendo = False

            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(800, event.w), max(540, event.h)), pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if modal_abierto:
                        modal_abierto = False
                        mensaje_modal = ""
                    elif mapa_ampliado:
                        mapa_ampliado = False
                elif event.key == pygame.K_e and not mapa_ampliado:
                    if modal_abierto:
                        modal_abierto = False
                        mensaje_modal = ""
                    elif cerca_de_mesa:
                        modal_abierto = True
                        fila_foco = 1
                        indice_foco = 0
                        mensaje_modal = ""
                elif event.key == pygame.K_F2:
                    # Tecla rapida de desarrollo para simular la llegada de un 2do a 4to jugador
                    if len(jugadores) < 4:
                        usados = {j["color"].upper() for j in jugadores}
                        color_disp_nom, color_disp_hex = "Azul", "#1D3557"
                        for nom_c, hex_c in lista_colores:
                            if hex_c.upper() not in usados:
                                color_disp_nom, color_disp_hex = nom_c, hex_c
                                break
                        nuevo_id = len(jugadores) + 1
                        pos_prueba = [(0.50, 0.20), (0.72, 0.22), (0.28, 0.22)]
                        rx, ry = pos_prueba[(nuevo_id - 2) % len(pos_prueba)]
                        jugadores.append({
                            "id": nuevo_id,
                            "nombre": f"Piloto_{nuevo_id}",
                            "color_nombre": color_disp_nom,
                            "color": color_disp_hex,
                            "es_local": False,
                            "rel_x": rx,
                            "rel_y": ry,
                            "rect": pygame.Rect(0, 0, hitbox_size, hitbox_size),
                            "puntos": 0,
                            "extrayendo": False,
                        })
                        alerta_rechazo_expira = 0.0
                elif event.key == pygame.K_F3:
                    if len(jugadores) > 1:
                        jugadores.pop()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

                if mapa_ampliado:
                    if btn_cerrar_amp and btn_cerrar_amp.collidepoint(pos):
                        mapa_ampliado = False
                    continue

                if modal_abierto:
                    if rects_modal.get("btn_listo") and rects_modal["btn_listo"].collidepoint(pos):
                        modal_abierto = False
                        mensaje_modal = ""
                        continue

                    for idx_t, t_id in enumerate(orden_pestanas):
                        t_r = rects_modal.get(f"tab_{t_id}")
                        if t_r and t_r.collidepoint(pos):
                            pestana_modal = t_id
                            fila_foco = 1
                            indice_foco = 0
                            mensaje_modal = ""

                    if pestana_modal == "colores":
                        for nombre_c, _ in lista_colores:
                            info_c = rects_modal.get(f"color_{nombre_c}")
                            if info_c:
                                c_rect, nom_c, hex_c, ocupado_por, idx_c = info_c
                                if c_rect.collidepoint(pos):
                                    fila_foco = 1
                                    indice_foco = idx_c
                                    if ocupado_por:
                                        mensaje_modal = f"RECHAZADO: El color {nom_c} ya esta ocupado por {ocupado_por}."
                                    else:
                                        controller.avatar_color = hex_c
                                        jugador_local["color"] = hex_c
                                        jugador_local["color_nombre"] = nom_c
                                        controller.guardar_config_local()
                                        mensaje_modal = f"Color actualizado a {nom_c}."

                    elif pestana_modal == "mapas":
                        for idx in range(len(TIPOS_MAPA)):
                            info_m = rects_modal.get(f"mapa_{idx}")
                            if info_m:
                                m_rect, nombre_mapa = info_m
                                if m_rect.collidepoint(pos):
                                    fila_foco = 1
                                    indice_foco = idx
                                    if controller.es_creador and not controller.configuracion_editable():
                                        mensaje_modal = "BLOQUEADO: la partida ya inicio, la configuracion no se puede cambiar."
                                    elif controller.es_creador:
                                        controller.mapa_seleccionado = nombre_mapa
                                        minimapa_base = _generar_superficie_minimapa(nombre_mapa)
                                        mensaje_modal = f"Mapa cambiado a: {nombre_mapa}"
                                    else:
                                        mensaje_modal = "Acceso bloqueado: Solo el creador puede cambiar el mapa."

                        for clave_btn, op_btn in (("btn_tiempo", 3), ("btn_puntos", 4), ("btn_modo", 5), ("btn_congela", 6)):
                            r_btn = rects_modal.get(clave_btn)
                            if r_btn and r_btn.collidepoint(pos):
                                fila_foco = 1
                                indice_foco = op_btn
                                mensaje_modal = aplicar_opcion_configuracion(controller, op_btn)

                    elif pestana_modal == "musica":
                        if rects_modal.get("barra_vol") and rects_modal["barra_vol"].collidepoint(pos):
                            b_v = rects_modal["barra_vol"]
                            porcentaje = int(((pos[0] - b_v.x) / float(b_v.width)) * 100)
                            controller.volumen_musica = max(0, min(100, porcentaje))
                            controller.actualizar_volumen_audio()
                        elif rects_modal.get("vol_menos") and rects_modal["vol_menos"].collidepoint(pos):
                            controller.volumen_musica = max(0, controller.volumen_musica - 10)
                            controller.actualizar_volumen_audio()
                        elif rects_modal.get("vol_mas") and rects_modal["vol_mas"].collidepoint(pos):
                            controller.volumen_musica = min(100, controller.volumen_musica + 10)
                            controller.actualizar_volumen_audio()
                        elif rects_modal.get("vol_mute") and rects_modal["vol_mute"].collidepoint(pos):
                            controller.volumen_musica = 0
                            controller.actualizar_volumen_audio()

                    continue

                if mesa_rect.collidepoint(pos):
                    modal_abierto = True
                    fila_foco = 1
                    indice_foco = 0
                    mensaje_modal = ""
                elif zona_despegue.collidepoint(pos):
                    if puede_iniciar:
                        controller.jugadores_sala = jugadores
                        accion_salida = "arena"
                        corriendo = False
                    else:
                        alerta_rechazo_lobby = (
                            f"RECHAZO DE INICIO: Se requieren minimo 2 jugadores conectados "
                            f"para iniciar la partida (Actual: {len(jugadores)}/4)."
                        )
                        alerta_rechazo_expira = ahora + 4.0
                elif zona_salida.collidepoint(pos):
                    accion_salida = "menu"
                    corriendo = False
                elif btn_ampliar_rect.collidepoint(pos) or minimapa_rect.collidepoint(pos):
                    mapa_ampliado = True

        # Movimiento del jugador local en la sala caminable
        if not modal_abierto and not mapa_ampliado:
            dx_unit, dy_unit = direction_from(comandos_actuales)
            if dx_unit != 0 or dy_unit != 0:
                if abs(dx_unit) >= abs(dy_unit):
                    jugador_local["direccion"] = "right" if dx_unit > 0 else "left"
                else:
                    jugador_local["direccion"] = "down" if dy_unit > 0 else "up" 
                vel_x = dx_unit * velocidad_base * sx
                vel_y = dy_unit * velocidad_base * sy
                nuevo_rect = mover_con_colisiones(
                    jugador_local["rect"],
                    vel_x,
                    vel_y,
                    muros_lobby,
                    zona_caminable,
                )
                jugador_local["rect"] = nuevo_rect
                jugador_local["pos_x"] = nuevo_rect.x
                jugador_local["pos_y"] = nuevo_rect.y
                ancho_util = max(1, zona_caminable.width - hitbox_size)
                alto_util = max(1, zona_caminable.height - hitbox_size)
                jugador_local["rel_x"] = (nuevo_rect.x - zona_caminable.x) / float(ancho_util)
                jugador_local["rel_y"] = (nuevo_rect.y - zona_caminable.y) / float(alto_util)

        pygame.display.flip()
        clock.tick(60)

    controller.jugadores_sala = jugadores
    if accion_salida == "arena":
        from Cliente.Interfaz.arena_view import iniciar_arena_pygame
        iniciar_arena_pygame(controller, screen=screen)
    elif accion_salida == "menu":
        pygame.display.quit()
        controller.mostrar_hub()
    else:
        controller.cerrar_aplicacion()
