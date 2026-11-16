"""
Pantalla de Victoria (US-17).

CA-17.1  Muestra al ganador (avatar y nombre).
CA-17.2  Mensaje de felicitacion.
CA-17.3  Tabla de posiciones ordenada por puntaje.
CA-17.4  Se puede volver al lobby con el quinto boton del mando, teclado o clic.
Ademas: musica festiva sintetizada (sin archivos externos) y confeti animado.

Las funciones puras (ranking, sintesis de audio) no necesitan ventana y se prueban
sin hardware; solo `mostrar_pantalla_victoria` abre el bucle grafico.
"""
from __future__ import annotations

import array
import math
import random

import pygame

from Cliente.Inputs.gamepad_manager import Command, create_default_input_manager
from Cliente.Interfaz.Components.hud import hex_to_rgb

# Fanfarria: (frecuencia Hz, duracion s). 0 Hz = silencio.
_NOTAS_FANFARRIA = [
    (523.25, 0.14), (523.25, 0.14), (523.25, 0.14), (523.25, 0.40),
    (415.30, 0.40), (466.16, 0.40), (523.25, 0.14), (466.16, 0.10), (523.25, 0.70),
    (0, 0.12),
    (659.25, 0.18), (783.99, 0.18), (1046.50, 0.18), (783.99, 0.18), (1046.50, 0.90),
]


def calcular_ranking(jugadores: list[dict]) -> list[dict]:
    """
    Descripcion:
        Ordena a los jugadores de mayor a menor puntaje y asigna el puesto. Los empatados
        comparten puesto (1, 1, 3...). El orden entre empatados respeta el original.
    Entradas:
        jugadores: lista de dicts con clave 'puntos'.
    Salidas:
        Lista nueva de dicts (copias) con la clave extra 'puesto'. No modifica la entrada.
    """
    ordenados = sorted(jugadores, key=lambda j: j.get("puntos", 0), reverse=True)
    ranking: list[dict] = []
    for i, jug in enumerate(ordenados):
        copia = dict(jug)
        if i > 0 and copia.get("puntos", 0) == ranking[-1].get("puntos", 0):
            copia["puesto"] = ranking[-1]["puesto"]
        else:
            copia["puesto"] = i + 1
        ranking.append(copia)
    return ranking


def mensaje_felicitacion(ganador: dict) -> str:
    """Texto de felicitacion para el ganador (CA-17.2)."""
    nombre = str(ganador.get("nombre", "Piloto")).upper()
    return f"FELICIDADES {nombre}, CAMPEON DE LA ARENA!"


def formatear_duracion(segundos: float | None) -> str:
    """Formatea una duracion en segundos como MM:SS (US-26)."""
    if segundos is None:
        return "--:--"
    total = max(0, int(segundos))
    mins, segs = divmod(total, 60)
    return f"{mins:02d}:{segs:02d}"


def evaluar_record_personal(jugadores: list[dict], mejor_anterior: int = 0) -> tuple[bool, int]:
    """
    Determina si el jugador local supero su mejor puntuacion historica registrada.
    Retorna (es_nuevo_record, mejor_puntaje_actualizado).
    """
    mejor_prev = max(0, int(mejor_anterior or 0))
    locales = [j for j in jugadores if j.get("es_local")]
    if not locales:
        return False, mejor_prev
    pts_local = max(0, int(locales[0].get("puntos", 0) or 0))
    if pts_local > mejor_prev:
        return True, pts_local
    return False, mejor_prev


def construir_podio(ranking: list[dict]) -> list[dict]:
    """
    Construye la disposicion visual del podio dinamico (US-26):
      - 1 jugador: [1ro]
      - 2 jugadores: [2do (izq), 1ro (der)]
      - 3+ jugadores: [2do (izq), 1ro (centro), 3ro (der)]
    """
    if not ranking:
        return []

    estilo_1 = {
        "lugar": 1,
        "etiqueta": "#1",
        "altura_ratio": 1.0,
        "color_borde": (233, 196, 106),
        "color_relleno": (64, 54, 24),
    }
    estilo_2 = {
        "lugar": 2,
        "etiqueta": "#2",
        "altura_ratio": 0.72,
        "color_borde": (192, 204, 220),
        "color_relleno": (44, 50, 64),
    }
    estilo_3 = {
        "lugar": 3,
        "etiqueta": "#3",
        "altura_ratio": 0.54,
        "color_borde": (205, 127, 50),
        "color_relleno": (54, 38, 28),
    }

    if len(ranking) == 1:
        return [{**estilo_1, "jugador": ranking[0]}]
    if len(ranking) == 2:
        return [
            {**estilo_2, "jugador": ranking[1]},
            {**estilo_1, "jugador": ranking[0]},
        ]
    return [
        {**estilo_2, "jugador": ranking[1]},
        {**estilo_1, "jugador": ranking[0]},
        {**estilo_3, "jugador": ranking[2]},
    ]


def sintetizar_fanfarria(frecuencia_muestreo: int = 44100, canales: int = 2) -> bytes:
    """
    Descripcion:
        Genera una fanfarria corta (PCM 16 bits con signo, little endian) mezclando una
        onda cuadrada suave con una senoidal una octava arriba y una envolvente.
    Salidas:
        bytes listos para pygame.mixer.Sound(buffer=...). Nunca vacio.
    """
    if frecuencia_muestreo <= 0 or canales not in (1, 2):
        raise ValueError("Formato de audio no valido.")
    muestras = array.array("h")
    amplitud = 9000
    for frecuencia, duracion in _NOTAS_FANFARRIA:
        n = int(frecuencia_muestreo * duracion)
        for i in range(n):
            if frecuencia == 0:
                valor = 0.0
            else:
                t = i / frecuencia_muestreo
                onda = math.sin(2 * math.pi * frecuencia * t)
                cuadrada = 1.0 if onda >= 0 else -1.0
                brillo = math.sin(2 * math.pi * frecuencia * 2 * t)
                base = 0.35 * cuadrada + 0.45 * onda + 0.2 * brillo
                ataque = min(1.0, i / (0.01 * frecuencia_muestreo))
                relajo = min(1.0, (n - i) / (0.05 * frecuencia_muestreo))
                valor = base * ataque * relajo
            entero = int(valor * amplitud)
            for _ in range(canales):
                muestras.append(entero)
    return muestras.tobytes()


def _crear_sonido_victoria():
    """Sound de pygame con la fanfarria, o None si no hay audio disponible (modo silencioso)."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        frecuencia, _formato, canales = pygame.mixer.get_init()
        return pygame.mixer.Sound(buffer=sintetizar_fanfarria(frecuencia, min(2, canales)))
    except Exception as e:
        print(f"[AUDIO] Musica de victoria no disponible: {e}")
        return None


def _crear_confeti(ancho: int, alto: int, cantidad: int = 140, rng: random.Random | None = None) -> list[dict]:
    rng = rng or random.Random()
    colores = [(230, 57, 70), (233, 196, 106), (42, 157, 143), (74, 144, 226), (244, 162, 97), (255, 255, 255)]
    return [
        {
            "x": rng.uniform(0, ancho),
            "y": rng.uniform(-alto, 0),
            "vy": rng.uniform(80, 220),
            "vx": rng.uniform(-40, 40),
            "w": rng.randint(5, 10),
            "h": rng.randint(8, 14),
            "color": rng.choice(colores),
        }
        for _ in range(cantidad)
    ]


def _mover_confeti(particulas: list[dict], dt: float, ancho: int, alto: int) -> None:
    for p in particulas:
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        if p["y"] > alto:
            p["y"] = -p["h"]
            p["x"] = random.uniform(0, ancho)


def _cargar_sprites_personajes() -> dict:
    """Carga la cache de sprites de personajes de forma segura para el podio."""
    try:
        from Cliente.Interfaz.Components.sprite_loader import inicializar_sprites
        return inicializar_sprites().get("personajes", {})
    except Exception:
        return {}


def mostrar_pantalla_victoria(
    controller,
    ganador: dict,
    jugadores: list[dict],
    screen: pygame.Surface,
    avatar_img_surface: pygame.Surface | None = None,
    input_manager=None,
    duracion_seg: float | None = None,
    mapa_nombre: str | None = None,
    modo_fin: str | None = None,
    nuevo_record_servidor: bool = False,
) -> str:
    """
    Descripcion:
        Bucle de la pantalla de ceremonia de victoria (US-17 / US-26). Pausa la musica
        ambiental, reproduce la fanfarria, muestra el podio dinamico, estadisticas
        de la partida, insignia de record y botones limpios de salida.
    Entradas:
        controller: AppController (volumen y record personal).
        ganador: dict del jugador ganador.
        jugadores: todos los jugadores de la partida.
        screen: superficie de la ventana actual.
        input_manager: opcional (el de la arena).
        duracion_seg: duracion real de la partida en segundos.
        mapa_nombre: nombre del escenario jugado.
        modo_fin: modalidad de fin ('tiempo' o 'puntos').
    Salidas:
        "lobby" si pidio volver al lobby, "hub" al menu principal, "cerrar" si cerro la ventana.
    """
    reloj = pygame.time.Clock()
    manager = input_manager or create_default_input_manager()
    ranking = calcular_ranking(jugadores)
    podio = construir_podio(ranking)
    felicitacion = mensaje_felicitacion(ganador)
    sprites_chars = _cargar_sprites_personajes()

    mejor_prev = int(getattr(controller, "mejor_puntaje", 0) or 0)
    es_record_local, nuevo_mejor = evaluar_record_personal(jugadores, mejor_prev)
    if es_record_local:
        try:
            controller.mejor_puntaje = nuevo_mejor
            if hasattr(controller, "guardar_config_local"):
                controller.guardar_config_local()
        except Exception:
            pass
    es_nuevo_record = es_record_local or bool(nuevo_record_servidor) or bool((ganador or {}).get("nuevo_record"))

    mapa_txt = str(mapa_nombre or getattr(controller, "mapa_seleccionado", "Estacion Estandar"))
    modo_raw = modo_fin if modo_fin is not None else getattr(controller, "modo_fin", None)
    modo_txt = "Por Puntos" if modo_raw == "puntos" else "Por Tiempo"
    duracion_txt = formatear_duracion(duracion_seg)

    sonido = _crear_sonido_victoria()
    musica_pausada = False
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.pause()
            musica_pausada = True
        if sonido is not None:
            sonido.set_volume(max(0.0, min(1.0, getattr(controller, "volumen_musica", 50) / 100.0)))
            sonido.play()
    except Exception:
        pass

    w, h = screen.get_size()
    confeti = _crear_confeti(w, h)
    esperando_soltar = Command.ACTION in manager.poll()  # evita salir por un boton que venia presionado
    previos: set = set()
    t_total = 0.0
    opcion_idx = 0  # 0: VOLVER AL LOBBY, 1: MENU PRINCIPAL
    resultado = "lobby"
    corriendo = True
    btn_lobby_rect = None
    btn_hub_rect = None

    while corriendo:
        dt = min(reloj.tick(60) / 1000.0, 0.05)
        t_total += dt
        w, h = screen.get_size()
        sx, sy = w / 1280.0, h / 720.0

        actuales = set(manager.poll())
        if esperando_soltar and Command.ACTION not in actuales:
            esperando_soltar = False
        nuevos = actuales - previos
        previos = actuales
        if Command.LEFT in nuevos:
            opcion_idx = 0
        elif Command.RIGHT in nuevos:
            opcion_idx = 1
        if Command.ACTION in nuevos and not esperando_soltar:
            resultado = "lobby" if opcion_idx == 0 else "hub"
            corriendo = False

        screen.fill((12, 15, 24))
        _mover_confeti(confeti, dt, w, h)

        mw, mh = min(w - 30, int(920 * sx)), min(h - 30, int(650 * sy))
        modal = pygame.Rect(w // 2 - mw // 2, h // 2 - mh // 2, mw, mh)
        pygame.draw.rect(screen, (20, 25, 36), modal, border_radius=14)
        pygame.draw.rect(screen, (233, 196, 106), modal, 3, border_radius=14)

        f_tit = pygame.font.SysFont("Segoe UI", max(18, int(28 * sy)), bold=True)
        f_sub = pygame.font.SysFont("Segoe UI", max(13, int(18 * sy)), bold=True)
        f_row = pygame.font.SysFont("Segoe UI", max(11, int(15 * sy)), bold=True)
        f_sm = pygame.font.SysFont("Segoe UI", max(10, int(13 * sy)))

        t = f_tit.render("CEREMONIA DE VICTORIA", True, (233, 196, 106))
        screen.blit(t, (modal.centerx - t.get_width() // 2, modal.y + int(14 * sy)))

        fel = f_sub.render(felicitacion, True, (110, 235, 160))
        screen.blit(fel, (modal.centerx - fel.get_width() // 2, modal.y + int(48 * sy)))

        # Badge de Nuevo Record Personal (US-26)
        if es_nuevo_record:
            pulso = 1.0 + 0.08 * math.sin(t_total * 6)
            badge_w = int(260 * sx * pulso)
            badge_h = int(24 * sy)
            badge_rect = pygame.Rect(modal.centerx - badge_w // 2, modal.y + int(76 * sy), badge_w, badge_h)
            pygame.draw.rect(screen, (180, 120, 20), badge_rect, border_radius=12)
            pygame.draw.rect(screen, (255, 225, 110), badge_rect, 2, border_radius=12)
            b_txt = f_sm.render("NUEVO RECORD PERSONAL!", True, (255, 255, 255))
            screen.blit(b_txt, (badge_rect.centerx - b_txt.get_width() // 2, badge_rect.centery - b_txt.get_height() // 2))

        # Podio Dinamico (US-26)
        podio_base_y = modal.y + int(272 * sy)
        max_pedestal_h = int(96 * sy)
        col_w = int(156 * sx)
        gap_p = int(20 * sx)
        total_podio_w = len(podio) * col_w + max(0, len(podio) - 1) * gap_p
        start_px = modal.centerx - total_podio_w // 2

        for idx_p, slot in enumerate(podio):
            jug = slot["jugador"]
            px = start_px + idx_p * (col_w + gap_p)
            ph = max(int(44 * sy), int(max_pedestal_h * slot["altura_ratio"]))
            pedestal = pygame.Rect(px, podio_base_y - ph, col_w, ph)

            pygame.draw.rect(screen, slot["color_relleno"], pedestal, border_top_left_radius=8, border_top_right_radius=8)
            pygame.draw.rect(screen, slot["color_borde"], pedestal, 3, border_top_left_radius=8, border_top_right_radius=8)

            # Avatar sobre el pedestal (pulso suave para el 1er lugar)
            lado = int((56 + (5 * math.sin(t_total * 4) if slot["lugar"] == 1 else 0)) * sy)
            av = pygame.Rect(pedestal.centerx - lado // 2, pedestal.top - lado - int(8 * sy), lado, lado)
            color_hex = str(jug.get("color", "#E63946")).upper()
            spr = sprites_chars.get(color_hex, {}).get("down")

            if jug.get("es_local") and avatar_img_surface is not None:
                screen.blit(pygame.transform.smoothscale(avatar_img_surface, (lado, lado)), av)
            elif spr is not None:
                screen.blit(pygame.transform.smoothscale(spr, (lado, lado)), av)
            else:
                pygame.draw.rect(screen, hex_to_rgb(color_hex), av, border_radius=8)
                pygame.draw.rect(screen, (255, 255, 255), av, 2, border_radius=8)

            # Etiqueta del puesto, nombre y puntaje dentro del pedestal
            lbl_puesto = f_sub.render(slot["etiqueta"], True, slot["color_borde"])
            screen.blit(lbl_puesto, (pedestal.centerx - lbl_puesto.get_width() // 2, pedestal.top + int(6 * sy)))

            nom_corto = str(jug.get("nombre", "?"))[:13]
            lbl_nom = f_sm.render(nom_corto, True, (255, 255, 255))
            screen.blit(lbl_nom, (pedestal.centerx - lbl_nom.get_width() // 2, pedestal.top + int(28 * sy)))

            lbl_pts = f_sm.render(f"{jug.get('puntos', 0)} pts", True, (220, 230, 245))
            if pedestal.height >= int(64 * sy):
                screen.blit(lbl_pts, (pedestal.centerx - lbl_pts.get_width() // 2, pedestal.bottom - lbl_pts.get_height() - int(6 * sy)))

        # Panel Resumen de Estadisticas (US-26)
        stats_rect = pygame.Rect(modal.x + int(36 * sx), podio_base_y + int(12 * sy), modal.width - int(72 * sx), int(38 * sy))
        pygame.draw.rect(screen, (28, 34, 48), stats_rect, border_radius=8)
        pygame.draw.rect(screen, (55, 68, 92), stats_rect, 1, border_radius=8)
        resumen = f"Duracion: {duracion_txt}   |   Mapa: {mapa_txt}   |   Modo: {modo_txt}   |   Record Local: {max(mejor_prev, nuevo_mejor)} pts"
        lbl_stats = f_sm.render(resumen, True, (195, 210, 230))
        screen.blit(lbl_stats, (stats_rect.centerx - lbl_stats.get_width() // 2, stats_rect.centery - lbl_stats.get_height() // 2))

        # Tabla de posiciones completa (CA-17.3)
        y0 = stats_rect.bottom + int(12 * sy)
        alto_fila = int(34 * sy)
        for i, jug in enumerate(ranking[:4]):
            fila = pygame.Rect(modal.x + int(36 * sx), y0 + i * (alto_fila + int(6 * sy)),
                               modal.width - int(72 * sx), alto_fila)
            primero = jug["puesto"] == 1
            pygame.draw.rect(screen, (36, 52, 46) if primero else (30, 35, 48), fila, border_radius=8)
            pygame.draw.rect(screen, (42, 157, 143) if primero else (65, 75, 95), fila, 2 if primero else 1, border_radius=8)
            muestra = pygame.Rect(fila.x + int(12 * sx), fila.centery - int(9 * sy), int(18 * sx), int(18 * sy))
            pygame.draw.rect(screen, hex_to_rgb(jug.get("color", "#FFFFFF")), muestra, border_radius=4)
            color_nom = f" ({jug.get('color_nombre')})" if jug.get("color_nombre") else ""
            txt = f_row.render(f"#{jug['puesto']}   {jug.get('nombre', '?')}{color_nom}", True, (255, 255, 255))
            screen.blit(txt, (muestra.right + int(12 * sx), fila.centery - txt.get_height() // 2))
            pj = f_row.render(f"{jug.get('puntos', 0)} PTS", True, (233, 196, 106) if primero else (195, 205, 225))
            screen.blit(pj, (fila.right - pj.get_width() - int(16 * sx), fila.centery - pj.get_height() // 2))

        # Botones de Salida Limpios (US-26)
        bw, bh = int(310 * sx), int(42 * sy)
        gap_b = int(20 * sx)
        btn_y = modal.bottom - bh - int(16 * sy)
        btn_lobby_rect = pygame.Rect(modal.centerx - bw - gap_b // 2, btn_y, bw, bh)
        btn_hub_rect = pygame.Rect(modal.centerx + gap_b // 2, btn_y, bw, bh)

        pygame.draw.rect(screen, (42, 157, 143), btn_lobby_rect, border_radius=8)
        pygame.draw.rect(
            screen,
            (233, 196, 106) if opcion_idx == 0 else (255, 255, 255),
            btn_lobby_rect,
            3 if opcion_idx == 0 else 1,
            border_radius=8,
        )
        eti_l = f_row.render("VOLVER AL LOBBY  [Accion / Enter]", True, (255, 255, 255))
        screen.blit(eti_l, (btn_lobby_rect.centerx - eti_l.get_width() // 2, btn_lobby_rect.centery - eti_l.get_height() // 2))

        pygame.draw.rect(screen, (52, 62, 84), btn_hub_rect, border_radius=8)
        pygame.draw.rect(
            screen,
            (233, 196, 106) if opcion_idx == 1 else (180, 190, 210),
            btn_hub_rect,
            3 if opcion_idx == 1 else 1,
            border_radius=8,
        )
        eti_h = f_row.render("MENU PRINCIPAL  [Esc]", True, (255, 255, 255))
        screen.blit(eti_h, (btn_hub_rect.centerx - eti_h.get_width() // 2, btn_hub_rect.centery - eti_h.get_height() // 2))

        for p in confeti:  # el confeti cae por delante del recuadro
            pygame.draw.rect(screen, p["color"], (int(p["x"]), int(p["y"]), p["w"], p["h"]))

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                resultado, corriendo = "cerrar", False
            elif evento.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(800, evento.w), max(540, evento.h)), pygame.RESIZABLE)
            elif evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_LEFT, pygame.K_a):
                    opcion_idx = 0
                elif evento.key in (pygame.K_RIGHT, pygame.K_d):
                    opcion_idx = 1
                elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    resultado = "lobby" if opcion_idx == 0 else "hub"
                    corriendo = False
                elif evento.key == pygame.K_ESCAPE:
                    resultado = "hub"
                    corriendo = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if btn_lobby_rect.collidepoint(evento.pos):
                    resultado, corriendo = "lobby", False
                elif btn_hub_rect.collidepoint(evento.pos):
                    resultado, corriendo = "hub", False

        pygame.display.flip()

    try:
        if sonido is not None:
            sonido.stop()
        if musica_pausada and pygame.mixer.get_init():
            pygame.mixer.music.unpause()
    except Exception:
        pass
    return resultado
