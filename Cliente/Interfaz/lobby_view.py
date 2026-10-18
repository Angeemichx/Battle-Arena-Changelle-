"""
Vista del Lobby Caminable en Pygame (US-09 y US-06).
- Se adapta dinamicamente a las dimensiones de la pantalla del computador.
- Soporta navegacion completa tanto con Raton como con Mando (Gamepad / Teclado):
  * Al acercarse a la Mesa Central y presionar el boton de Accion del mando (Command.ACTION / Espacio / E),
    abre la ventana modal superpuesta.
  * Dentro de la ventana modal, permite desplazarse con el mando (Arriba, Abajo, Izquierda, Derecha)
    entre Pestañas, Colores, Mapas, Volumen y el boton LISTO, seleccionando con Command.ACTION.
  * Tambien incluye una Plataforma de Despegue caminable para iniciar la partida con Command.ACTION.
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
    SPAWN_POINTS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    mover_con_colisiones,
    obtener_colisiones_lobby,
    obtener_muros_arena,
)
from Cliente.Interfaz.components.hud import dibujar_hud_lobby, hex_to_rgb
from Cliente.Interfaz.components.ui_helpers import COLORES_AVATAR

TIPOS_MAPA = [
    "Estacion Estandar",
    "Reactor Inestable",
    "Laberinto Cerrado",
]


def _generar_superficie_minimapa(tipo_mapa: str) -> pygame.Surface:
    """
    Genera una superficie proporcional del mapa de 3600x2600 px
    para luego escalarla con pygame.transform.smoothscale en el Lobby.
    """
    base_w, base_h = 540, 390
    surf = pygame.Surface((base_w, base_h))
    surf.fill((20, 24, 33))

    sx = base_w / float(WORLD_WIDTH)
    sy = base_h / float(WORLD_HEIGHT)

    # Cuadricula sutil de piso
    for gx in range(0, WORLD_WIDTH, 300):
        x = int(gx * sx)
        pygame.draw.line(surf, (30, 35, 48), (x, 0), (x, base_h), 1)
    for gy in range(0, WORLD_HEIGHT, 300):
        y = int(gy * sy)
        pygame.draw.line(surf, (30, 35, 48), (0, y), (base_w, y), 1)

    # Muros del mapa seleccionado
    for muro in obtener_muros_arena(tipo_mapa):
        r = pygame.Rect(
            int(muro.x * sx),
            int(muro.y * sy),
            max(2, int(muro.width * sx)),
            max(2, int(muro.height * sy)),
        )
        pygame.draw.rect(surf, (68, 76, 96), r)
        pygame.draw.rect(surf, (100, 112, 138), r, 1)

    # 4 Spawns
    for idx, (spx, spy) in SPAWN_POINTS.items():
        cx, cy = int(spx * sx), int(spy * sy)
        pygame.draw.circle(surf, (42, 157, 143), (cx, cy), 8)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 8, 1)

    # Reactor Central
    rx, ry = int(REACTOR_CENTER[0] * sx), int(REACTOR_CENTER[1] * sy)
    pygame.draw.circle(surf, (0, 180, 216), (rx, ry), 24, 2)
    pygame.draw.circle(surf, (0, 235, 255), (rx, ry), 13)

    return surf


def _cargar_imagen_avatar_disco(ruta: str | None) -> pygame.Surface | None:
    if not ruta or not os.path.exists(ruta):
        return None
    try:
        return pygame.image.load(ruta).convert_alpha()
    except Exception:
        return None


def _seleccionar_archivo_imagen() -> str | None:
    """Abre filedialog para elegir imagen de avatar desde disco (CA-06.3)."""
    try:
        from tkinter import Tk, filedialog
        tk_root = Tk()
        tk_root.withdraw()
        tk_root.attributes("-topmost", True)
        ruta = filedialog.askopenfilename(
            title="Seleccionar Imagen de Avatar",
            filetypes=[("Imagenes", "*.png;*.jpg;*.jpeg;*.bmp")],
        )
        tk_root.destroy()
        return ruta if ruta else None
    except Exception as e:
        print(f"[AVATAR] Error al abrir selector de archivo: {e}")
        return None


def iniciar_lobby_pygame(controller, screen: pygame.Surface | None = None):
    """
    Ejecuta el bucle del Lobby Caminable en Pygame adaptandose a la pantalla
    y permitiendo interaccion tanto con raton como con mando (Command.ACTION y direcciones).
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

    # Reutilizar InputManager del Integrante 2 (mando Xbox/PS5 + teclado WASD/Flechas/Espacio)
    input_manager = create_default_input_manager(allow_keyboard_fallback=True)
    comandos_previos: set[Command] = set()

    lista_colores = list(COLORES_AVATAR.items())  # [("Rojo", "#E63946"), ...]
    orden_pestanas = ["colores", "mapas", "musica"]

    # Inicializar jugadores en la sala (jugador 0 es el jugador local)
    jugadores = [
        {
            "id": 1,
            "nombre": str(controller.usuario_actual),
            "color_nombre": controller.obtener_nombre_color(controller.avatar_color),
            "color": controller.avatar_color,
            "es_local": True,
            "rel_x": 0.22,
            "rel_y": 0.50,
            "rect": pygame.Rect(0, 0, 48, 48),
            "puntos": 0,
            "extrayendo": False,
        }
    ]

    if getattr(controller, "jugadores_sala", None) and len(controller.jugadores_sala) > 1:
        jugadores = controller.jugadores_sala
        jugadores[0]["nombre"] = str(controller.usuario_actual)
        jugadores[0]["color"] = controller.avatar_color
        jugadores[0]["color_nombre"] = controller.obtener_nombre_color(controller.avatar_color)

    avatar_img_surface = _cargar_imagen_avatar_disco(controller.avatar_imagen)
    minimapa_base = _generar_superficie_minimapa(controller.mapa_seleccionado)

    # Estado del modal de la Mesa Interactiva y navegacion con Mando
    modal_abierto = False
    pestana_modal = "colores"  # "colores" | "mapas" | "musica"
    # Foco del mando en el modal:
    # fila_foco = 0 (Pestañas superiores), 1 (Opciones centrales), 2 (Boton LISTO)
    fila_foco = 1
    indice_foco = 0
    mapa_ampliado = False
    mensaje_modal = ""

    velocidad_base = 5.0
    corriendo = True
    accion_salida = None  # "menu" | "arena" | "cerrar"

    while corriendo:
        w, h = screen.get_size()
        sx = w / 1280.0
        sy = h / 720.0

        # Zonas adaptadas a la resolucion actual de la ventana
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

        hitbox_size = max(34, int(48 * min(sx, sy)))
        for jug in jugadores:
            px = zona_caminable.x + int(jug["rel_x"] * (zona_caminable.width - hitbox_size))
            py = zona_caminable.y + int(jug["rel_y"] * (zona_caminable.height - hitbox_size))
            jug["rect"] = pygame.Rect(px, py, hitbox_size, hitbox_size)

        jugador_local = jugadores[0]
        cerca_de_mesa = jugador_local["rect"].colliderect(zona_interaccion)
        en_zona_despegue = jugador_local["rect"].colliderect(zona_despegue)

        # Rectangulos interactivos del panel lateral derecho
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

        btn_add_bot = pygame.Rect(
            panel_derecho.x + int(22 * sx),
            panel_derecho.y + int(455 * sy),
            int(152 * sx),
            int(32 * sy),
        )
        btn_rem_bot = pygame.Rect(
            btn_add_bot.right + int(12 * sx),
            panel_derecho.y + int(455 * sy),
            int(152 * sx),
            int(32 * sy),
        )

        btn_iniciar_rect = pygame.Rect(
            panel_derecho.x + int(22 * sx),
            panel_derecho.bottom - int(72 * sy),
            panel_derecho.width - int(44 * sx),
            int(54 * sy),
        )

        # =====================================================================
        # LECTURA DE COMANDOS DEL MANDO / TECLADO (DETECCION DE PULSACION UNICA)
        # =====================================================================
        comandos_actuales = input_manager.poll()
        comandos_nuevos = comandos_actuales - comandos_previos
        comandos_previos = set(comandos_actuales)

        colores_ocupados_otros = {
            j["color"]: j["nombre"] for j in jugadores if not j["es_local"]
        }

        # Si el modal esta abierto, manejar navegacion por Mando (Cruceta/Stick + Boton Accion)
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
                        indice_foco = (indice_foco - 1) % len(TIPOS_MAPA)
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
                        indice_foco = (indice_foco + 1) % len(TIPOS_MAPA)
                    elif pestana_modal == "musica":
                        controller.volumen_musica = min(100, controller.volumen_musica + 10)
                        controller.actualizar_volumen_audio()
                        mensaje_modal = f"Volumen ajustado a {controller.volumen_musica}%"

            elif Command.ACTION in comandos_nuevos:
                if fila_foco == 0:
                    # Pasar directamente a las opciones de la pestaña
                    fila_foco = 1
                    indice_foco = 0
                elif fila_foco == 1:
                    if pestana_modal == "colores":
                        nom_c, hex_c = lista_colores[indice_foco % len(lista_colores)]
                        ocupado_por = colores_ocupados_otros.get(hex_c)
                        if ocupado_por:
                            mensaje_modal = f"El color {nom_c} ya esta ocupado por {ocupado_por}."
                        else:
                            controller.avatar_color = hex_c
                            jugador_local["color"] = hex_c
                            jugador_local["color_nombre"] = nom_c
                            controller.guardar_config_local()
                            mensaje_modal = f"Color seleccionado con mando: {nom_c}."
                    elif pestana_modal == "mapas":
                        nombre_mapa = TIPOS_MAPA[indice_foco % len(TIPOS_MAPA)]
                        if controller.es_creador:
                            controller.mapa_seleccionado = nombre_mapa
                            minimapa_base = _generar_superficie_minimapa(nombre_mapa)
                            mensaje_modal = f"Mapa cambiado a: {nombre_mapa}"
                        else:
                            mensaje_modal = "Candado activo: Solo el creador puede cambiar el mapa."
                    elif pestana_modal == "musica":
                        controller.volumen_musica = 0 if controller.volumen_musica > 0 else 50
                        controller.actualizar_volumen_audio()
                        mensaje_modal = f"Volumen: {controller.volumen_musica}%"
                elif fila_foco == 2:
                    # Boton LISTO presionado con el mando
                    modal_abierto = False
                    mensaje_modal = ""

        else:
            # Si NO esta abierto el modal, el boton de Accion del mando (Command.ACTION)
            # permite abrir la Mesa de Comando o Iniciar la Partida en la Zona de Despegue
            if Command.ACTION in comandos_nuevos:
                if mapa_ampliado:
                    mapa_ampliado = False
                elif cerca_de_mesa:
                    modal_abierto = True
                    fila_foco = 1
                    indice_foco = 0
                    mensaje_modal = ""
                elif en_zona_despegue:
                    controller.jugadores_sala = jugadores
                    accion_salida = "arena"
                    corriendo = False

        # =====================================================================
        # DIBUJO DE PANTALLA DEL LOBBY
        # =====================================================================
        screen.fill((18, 20, 27))

        rects_hud = dibujar_hud_lobby(screen, controller, jugadores, avatar_img_surface)

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

        # Plataforma de Despegue (para iniciar partida caminando hacia ella y pulsando Accion)
        color_pad = (42, 157, 143) if en_zona_despegue else (34, 58, 62)
        pygame.draw.rect(screen, color_pad, zona_despegue, border_radius=8)
        pygame.draw.rect(screen, (90, 210, 190), zona_despegue, 2, border_radius=8)
        lbl_pad1 = font_small.render("ZONA DESPEGUE", True, (255, 255, 255))
        lbl_pad2 = font_small.render("[Accion / Espacio]", True, (200, 240, 230))
        screen.blit(lbl_pad1, (zona_despegue.centerx - lbl_pad1.get_width() // 2, zona_despegue.centery - lbl_pad1.get_height()))
        screen.blit(lbl_pad2, (zona_despegue.centerx - lbl_pad2.get_width() // 2, zona_despegue.centery + 2))

        # Zona de interaccion y Mesa Central de Comando
        color_zona = (42, 157, 143) if cerca_de_mesa else (50, 60, 80)
        pygame.draw.rect(screen, color_zona, zona_interaccion, 2, border_radius=10)
        pygame.draw.rect(screen, (45, 55, 78), mesa_rect, border_radius=8)
        pygame.draw.rect(screen, (100, 140, 200), mesa_rect, 2, border_radius=8)

        lbl_mesa1 = font_bold.render("MESA DE", True, (255, 255, 255))
        lbl_mesa2 = font_bold.render("COMANDO", True, (160, 200, 255))
        screen.blit(lbl_mesa1, (mesa_rect.centerx - lbl_mesa1.get_width() // 2, mesa_rect.centery - lbl_mesa1.get_height()))
        screen.blit(lbl_mesa2, (mesa_rect.centerx - lbl_mesa2.get_width() // 2, mesa_rect.centery + 2))

        if (cerca_de_mesa or en_zona_despegue) and not modal_abierto:
            if cerca_de_mesa:
                txt_aviso = "Presiona [Boton Accion del Mando / Espacio / E] para Configurar"
            else:
                txt_aviso = "Presiona [Boton Accion del Mando / Espacio] para Iniciar Partida"
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

        # Dibujar Jugadores en la Sala Caminable
        for jug in jugadores:
            j_rect = jug["rect"]
            if jug["es_local"] and avatar_img_surface is not None:
                img_scaled = pygame.transform.smoothscale(avatar_img_surface, (j_rect.width, j_rect.height))
                screen.blit(img_scaled, j_rect)
            else:
                pygame.draw.rect(screen, hex_to_rgb(jug["color"]), j_rect, border_radius=6)

            grosor_borde_j = 3 if jug["es_local"] else 1
            color_borde_j = (255, 255, 255) if jug["es_local"] else (30, 30, 30)
            pygame.draw.rect(screen, color_borde_j, j_rect, grosor_borde_j, border_radius=6)

            lbl_nom = font_small.render(jug["nombre"], True, (255, 255, 255))
            screen.blit(lbl_nom, (j_rect.centerx - lbl_nom.get_width() // 2, j_rect.top - lbl_nom.get_height() - 4))

        # Panel Lateral Derecho
        pygame.draw.rect(screen, (26, 30, 40), panel_derecho, border_radius=8)
        pygame.draw.rect(screen, (58, 66, 86), panel_derecho, 2, border_radius=8)

        lbl_prev = font_bold.render(f"MAPA (3600x2600): {controller.mapa_seleccionado.upper()}", True, (255, 255, 255))
        screen.blit(lbl_prev, (panel_derecho.x + int(22 * sx), panel_derecho.y + int(10 * sy)))

        mini_scaled = pygame.transform.smoothscale(minimapa_base, (minimapa_rect.width, minimapa_rect.height))
        screen.blit(mini_scaled, minimapa_rect)
        pygame.draw.rect(screen, (90, 105, 135), minimapa_rect, 2)

        pygame.draw.rect(screen, (43, 45, 66), btn_ampliar_rect, border_radius=5)
        lbl_amp = font_small.render("Ver / Ampliar Mapa", True, (200, 215, 240))
        screen.blit(
            lbl_amp,
            (btn_ampliar_rect.centerx - lbl_amp.get_width() // 2, btn_ampliar_rect.centery - lbl_amp.get_height() // 2),
        )

        lbl_slots = font_bold.render("JUGADORES EN SALA (2 A 4):", True, (200, 210, 225))
        screen.blit(lbl_slots, (minimapa_rect.x, btn_ampliar_rect.bottom + int(12 * sy)))

        slot_start_y = btn_ampliar_rect.bottom + int(36 * sy)
        slot_h = max(26, int(34 * sy))
        for i in range(4):
            s_rect = pygame.Rect(minimapa_rect.x, slot_start_y + i * (slot_h + int(5 * sy)), minimapa_rect.width, slot_h)
            pygame.draw.rect(screen, (20, 23, 31), s_rect, border_radius=5)
            if i < len(jugadores):
                j_slot = jugadores[i]
                pygame.draw.rect(screen, hex_to_rgb(j_slot["color"]), s_rect, 1, border_radius=5)
                c_box = pygame.Rect(s_rect.x + int(8 * sx), s_rect.centery - int(8 * sy), int(16 * sx), int(16 * sy))
                pygame.draw.rect(screen, hex_to_rgb(j_slot["color"]), c_box, border_radius=3)
                etiqueta = f"{i + 1}. {j_slot['nombre']} ({j_slot['color_nombre']})"
                surf_s = font_small.render(etiqueta, True, (255, 255, 255))
                screen.blit(surf_s, (c_box.right + int(8 * sx), s_rect.centery - surf_s.get_height() // 2))
            else:
                pygame.draw.rect(screen, (45, 50, 65), s_rect, 1, border_radius=5)
                surf_vacio = font_small.render(f"{i + 1}. Esperando conexion...", True, (110, 120, 140))
                screen.blit(surf_vacio, (s_rect.x + int(10 * sx), s_rect.centery - surf_vacio.get_height() // 2))

        pygame.draw.rect(screen, (43, 55, 75), btn_add_bot, border_radius=5)
        lbl_add = font_small.render("+ Simular Jugador", True, (220, 230, 245))
        screen.blit(lbl_add, (btn_add_bot.centerx - lbl_add.get_width() // 2, btn_add_bot.centery - lbl_add.get_height() // 2))

        pygame.draw.rect(screen, (55, 43, 55), btn_rem_bot, border_radius=5)
        lbl_rem = font_small.render("- Quitar Jugador", True, (220, 200, 210))
        screen.blit(lbl_rem, (btn_rem_bot.centerx - lbl_rem.get_width() // 2, btn_rem_bot.centery - lbl_rem.get_height() // 2))

        puede_iniciar = True if not controller.modo_estricto else (len(jugadores) >= 2)
        color_btn_ini = (42, 157, 143) if puede_iniciar else (60, 65, 78)
        texto_btn_ini = "INICIAR PARTIDA" if puede_iniciar else "ESPERANDO JUGADORES (MIN 2)"
        pygame.draw.rect(screen, color_btn_ini, btn_iniciar_rect, border_radius=8)
        lbl_ini = font_bold.render(texto_btn_ini, True, (255, 255, 255))
        screen.blit(
            lbl_ini,
            (btn_iniciar_rect.centerx - lbl_ini.get_width() // 2, btn_iniciar_rect.centery - lbl_ini.get_height() // 2),
        )

        # =====================================================================
        # VENTANA MODAL SUPERPUESTA (NAVEGABLE CON MANDO Y RATON)
        # =====================================================================
        rects_modal = {}
        if modal_abierto:
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 175))
            screen.blit(overlay, (0, 0))

            modal_w = int(700 * sx)
            modal_h = int(490 * sy)
            modal_rect = pygame.Rect((w - modal_w) // 2, (h - modal_h) // 2, modal_w, modal_h)
            pygame.draw.rect(screen, (26, 30, 42), modal_rect, border_radius=12)
            pygame.draw.rect(screen, (74, 144, 226), modal_rect, 2, border_radius=12)

            # Pestañas superiores (Fila 0 de navegacion con mando)
            tab_w = (modal_w - int(60 * sx)) // 3
            tab_h = max(34, int(40 * sy))
            tab_y = modal_rect.y + int(18 * sy)

            tabs_info = [
                ("colores", "1. COLORES Y AVATAR"),
                ("mapas", "2. TIPOS DE MAPA"),
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
                # Si el foco del mando esta en la fila de pestañas, resaltar con borde amarillo
                if fila_foco == 0 and activo:
                    pygame.draw.rect(screen, (233, 196, 106), t_rect, 3, border_radius=6)

                lbl_t = font_bold.render(t_label, True, (255, 255, 255))
                screen.blit(lbl_t, (t_rect.centerx - lbl_t.get_width() // 2, t_rect.centery - lbl_t.get_height() // 2))
                rects_modal[f"tab_{t_id}"] = t_rect

            content_y = tab_y + tab_h + int(20 * sy)

            # CONTENIDO PESTANA 1: COLORES Y AVATAR
            if pestana_modal == "colores":
                lbl_inst = font_reg.render(
                    "Mando: Izquierda/Derecha para elegir color y Boton Accion para confirmar:",
                    True,
                    (210, 215, 225),
                )
                screen.blit(lbl_inst, (modal_rect.x + int(28 * sx), content_y))

                btn_c_w = int(116 * sx)
                btn_c_h = int(88 * sy)
                start_cx = modal_rect.x + int(28 * sx)
                cy_box = content_y + int(34 * sy)

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

                    # Resaltar cursor del mando
                    if foco_mando:
                        pygame.draw.rect(screen, (233, 196, 106), c_rect.inflate(8, 8), 3, border_radius=10)

                    s_nom = font_bold.render(nombre_c, True, (255, 255, 255))
                    s_est = font_small.render(est_txt, True, (255, 255, 255))
                    screen.blit(s_nom, (c_rect.centerx - s_nom.get_width() // 2, c_rect.y + int(16 * sy)))
                    screen.blit(s_est, (c_rect.centerx - s_est.get_width() // 2, c_rect.bottom - int(26 * sy)))

                    rects_modal[f"color_{nombre_c}"] = (c_rect, nombre_c, hex_c, ocupado_por, idx)

                btn_disco = pygame.Rect(
                    modal_rect.x + int(28 * sx),
                    cy_box + btn_c_h + int(28 * sy),
                    int(280 * sx),
                    int(42 * sy),
                )
                pygame.draw.rect(screen, (31, 83, 141), btn_disco, border_radius=6)
                lbl_d = font_bold.render("Cargar Imagen desde Disco", True, (255, 255, 255))
                screen.blit(lbl_d, (btn_disco.centerx - lbl_d.get_width() // 2, btn_disco.centery - lbl_d.get_height() // 2))
                rects_modal["btn_disco"] = btn_disco

                if controller.avatar_imagen:
                    btn_limpiar_img = pygame.Rect(
                        btn_disco.right + int(16 * sx),
                        btn_disco.y,
                        int(220 * sx),
                        int(42 * sy),
                    )
                    pygame.draw.rect(screen, (70, 50, 60), btn_limpiar_img, border_radius=6)
                    lbl_li = font_small.render("Usar Solo Hitbox de Color", True, (255, 255, 255))
                    screen.blit(
                        lbl_li,
                        (btn_limpiar_img.centerx - lbl_li.get_width() // 2, btn_limpiar_img.centery - lbl_li.get_height() // 2),
                    )
                    rects_modal["btn_limpiar_img"] = btn_limpiar_img

            # CONTENIDO PESTANA 2: TIPOS DE MAPA (CANDADO PARA INVITADOS)
            elif pestana_modal == "mapas":
                if controller.es_creador:
                    lbl_m_info = font_bold.render(
                        "Anfitrion: Usa Mando (Izquierda/Derecha + Accion) o Raton para elegir mapa:",
                        True,
                        (42, 157, 143),
                    )
                else:
                    lbl_m_info = font_bold.render(
                        "[CANDADO] SOLO EL CREADOR DE LA PARTIDA PUEDE MODIFICAR EL MAPA",
                        True,
                        (233, 196, 106),
                    )
                screen.blit(lbl_m_info, (modal_rect.x + int(28 * sx), content_y))

                for idx, nombre_mapa in enumerate(TIPOS_MAPA):
                    m_rect = pygame.Rect(
                        modal_rect.x + int(28 * sx),
                        content_y + int(38 * sy) + idx * int(60 * sy),
                        modal_w - int(56 * sx),
                        int(48 * sy),
                    )
                    seleccionado = controller.mapa_seleccionado == nombre_mapa
                    foco_mando = (fila_foco == 1 and (indice_foco % len(TIPOS_MAPA)) == idx)

                    if controller.es_creador:
                        bg_m = (42, 157, 143) if seleccionado else (43, 45, 66)
                    else:
                        bg_m = (38, 40, 50)
                    pygame.draw.rect(screen, bg_m, m_rect, border_radius=8)
                    pygame.draw.rect(
                        screen,
                        (255, 255, 255) if seleccionado else (80, 90, 110),
                        m_rect,
                        2,
                        border_radius=8,
                    )
                    if foco_mando:
                        pygame.draw.rect(screen, (233, 196, 106), m_rect.inflate(6, 6), 3, border_radius=10)

                    prefijo = "[SELECCIONADO] " if seleccionado else ""
                    sufijo = "" if controller.es_creador else "   [BLOQUEADO - CANDADO]"
                    lbl_mp = font_bold.render(f"{prefijo}{nombre_mapa}{sufijo}", True, (255, 255, 255))
                    screen.blit(lbl_mp, (m_rect.x + int(18 * sx), m_rect.centery - lbl_mp.get_height() // 2))
                    rects_modal[f"mapa_{idx}"] = (m_rect, nombre_mapa)

            # CONTENIDO PESTANA 3: MUSICA Y AUDIO
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

            # Guía de navegacion con mando en el modal
            lbl_guia_m = font_small.render(
                "Navegacion Mando: Arriba/Abajo cambia entre Pestañas, Opciones y LISTO | Accion selecciona",
                True,
                (160, 175, 195),
            )
            screen.blit(lbl_guia_m, (modal_rect.x + int(28 * sx), modal_rect.bottom - int(92 * sy)))

            if mensaje_modal:
                s_msg = font_reg.render(mensaje_modal, True, (233, 196, 106))
                screen.blit(s_msg, (modal_rect.x + int(28 * sx), modal_rect.bottom - int(118 * sy)))

            # Boton LISTO (Fila 2 de navegacion con mando)
            btn_listo = pygame.Rect(
                modal_rect.centerx - int(110 * sx),
                modal_rect.bottom - int(56 * sy),
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
        # GESTION DE EVENTOS DE VENTANA Y RATON
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
                                        mensaje_modal = f"El color {nom_c} ya esta ocupado por {ocupado_por}."
                                    else:
                                        controller.avatar_color = hex_c
                                        jugador_local["color"] = hex_c
                                        jugador_local["color_nombre"] = nom_c
                                        controller.guardar_config_local()
                                        mensaje_modal = f"Color actualizado a {nom_c}."

                        if rects_modal.get("btn_disco") and rects_modal["btn_disco"].collidepoint(pos):
                            nueva_ruta = _seleccionar_archivo_imagen()
                            if nueva_ruta:
                                img_cargada = _cargar_imagen_avatar_disco(nueva_ruta)
                                if img_cargada is not None:
                                    controller.avatar_imagen = nueva_ruta
                                    avatar_img_surface = img_cargada
                                    controller.guardar_config_local()
                                    mensaje_modal = "Imagen de avatar cargada correctamente."

                        if rects_modal.get("btn_limpiar_img") and rects_modal["btn_limpiar_img"].collidepoint(pos):
                            controller.avatar_imagen = None
                            avatar_img_surface = None
                            controller.guardar_config_local()
                            mensaje_modal = "Usando hitbox de color solido."

                    elif pestana_modal == "mapas":
                        for idx in range(len(TIPOS_MAPA)):
                            info_m = rects_modal.get(f"mapa_{idx}")
                            if info_m:
                                m_rect, nombre_mapa = info_m
                                if m_rect.collidepoint(pos):
                                    fila_foco = 1
                                    indice_foco = idx
                                    if controller.es_creador:
                                        controller.mapa_seleccionado = nombre_mapa
                                        minimapa_base = _generar_superficie_minimapa(nombre_mapa)
                                        mensaje_modal = f"Mapa cambiado a: {nombre_mapa}"
                                    else:
                                        mensaje_modal = "Acceso bloqueado: Solo el creador de la sala puede cambiar el mapa."

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

                # Clics normales en el Lobby cuando el modal no esta abierto
                if rects_hud["btn_menu"].collidepoint(pos):
                    accion_salida = "menu"
                    corriendo = False

                elif rects_hud["btn_mesa"].collidepoint(pos) or mesa_rect.collidepoint(pos):
                    modal_abierto = True
                    fila_foco = 1
                    indice_foco = 0
                    mensaje_modal = ""

                elif btn_ampliar_rect.collidepoint(pos) or minimapa_rect.collidepoint(pos):
                    mapa_ampliado = True

                elif btn_add_bot.collidepoint(pos):
                    if len(jugadores) < 4:
                        usados = {j["color"].upper() for j in jugadores}
                        color_disp_nom, color_disp_hex = "Azul", "#1D3557"
                        for nom_c, hex_c in lista_colores:
                            if hex_c.upper() not in usados:
                                color_disp_nom, color_disp_hex = nom_c, hex_c
                                break
                        nuevo_id = len(jugadores) + 1
                        posiciones_prueba = [(0.75, 0.22), (0.22, 0.78), (0.75, 0.78)]
                        rx, ry = posiciones_prueba[(nuevo_id - 2) % len(posiciones_prueba)]
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

                elif btn_rem_bot.collidepoint(pos):
                    if len(jugadores) > 1:
                        jugadores.pop()

                elif btn_iniciar_rect.collidepoint(pos) and puede_iniciar:
                    controller.jugadores_sala = jugadores
                    accion_salida = "arena"
                    corriendo = False

        # Movimiento del jugador local en la sala caminable (solo si no hay modal abierto)
        if not modal_abierto and not mapa_ampliado:
            dx_unit, dy_unit = direction_from(comandos_actuales)
            if dx_unit != 0 or dy_unit != 0:
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
