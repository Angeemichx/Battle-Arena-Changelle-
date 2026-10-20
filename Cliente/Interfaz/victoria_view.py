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


def mostrar_pantalla_victoria(
    controller,
    ganador: dict,
    jugadores: list[dict],
    screen: pygame.Surface,
    avatar_img_surface: pygame.Surface | None = None,
    input_manager=None,
) -> str:
    """
    Descripcion:
        Bucle de la pantalla de victoria. Pausa la musica ambiental, reproduce la fanfarria
        y, al salir, reanuda la ambiental.
    Entradas:
        controller: AppController (solo se usa para el volumen).
        ganador: dict del jugador ganador. jugadores: todos los jugadores de la partida.
        screen: superficie de la ventana actual. input_manager: opcional (el de la arena).
    Salidas:
        "lobby" si el usuario pidio volver, "cerrar" si cerro la ventana.
    """
    reloj = pygame.time.Clock()
    manager = input_manager or create_default_input_manager()
    ranking = calcular_ranking(jugadores)
    felicitacion = mensaje_felicitacion(ganador)

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
    resultado = "lobby"
    corriendo = True
    btn_rect = None

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
        if Command.ACTION in nuevos and not esperando_soltar:
            corriendo = False

        screen.fill((12, 15, 24))
        _mover_confeti(confeti, dt, w, h)

        mw, mh = min(w - 40, int(760 * sx)), min(h - 40, int(540 * sy))
        modal = pygame.Rect(w // 2 - mw // 2, h // 2 - mh // 2, mw, mh)
        pygame.draw.rect(screen, (22, 27, 38), modal, border_radius=14)
        pygame.draw.rect(screen, (233, 196, 106), modal, 3, border_radius=14)

        f_tit = pygame.font.SysFont("Segoe UI", max(20, int(30 * sy)), bold=True)
        f_sub = pygame.font.SysFont("Segoe UI", max(14, int(20 * sy)), bold=True)
        f_row = pygame.font.SysFont("Segoe UI", max(12, int(16 * sy)), bold=True)

        t = f_tit.render("PANTALLA DE VICTORIA", True, (233, 196, 106))
        screen.blit(t, (modal.centerx - t.get_width() // 2, modal.y + int(18 * sy)))

        # Avatar del ganador con un pulso suave
        lado = int((72 + 6 * math.sin(t_total * 4)) * sy)
        av = pygame.Rect(modal.centerx - lado // 2, modal.y + int(66 * sy), lado, lado)
        if ganador.get("es_local") and avatar_img_surface is not None:
            screen.blit(pygame.transform.smoothscale(avatar_img_surface, (lado, lado)), av)
        else:
            pygame.draw.rect(screen, hex_to_rgb(ganador.get("color", "#E63946")), av, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), av, 3, border_radius=10)

        fel = f_sub.render(felicitacion, True, (110, 235, 160))
        screen.blit(fel, (modal.centerx - fel.get_width() // 2, av.bottom + int(12 * sy)))
        pts = f_row.render(f"{ganador.get('puntos', 0)} puntos", True, (233, 196, 106))
        screen.blit(pts, (modal.centerx - pts.get_width() // 2, av.bottom + int(14 * sy) + fel.get_height()))

        # Tabla de posiciones (CA-17.3)
        y0 = av.bottom + int(70 * sy)
        alto_fila = int(42 * sy)
        for i, jug in enumerate(ranking):
            fila = pygame.Rect(modal.x + int(40 * sx), y0 + i * (alto_fila + int(6 * sy)),
                               modal.width - int(80 * sx), alto_fila)
            primero = jug["puesto"] == 1
            pygame.draw.rect(screen, (36, 52, 46) if primero else (30, 35, 48), fila, border_radius=8)
            pygame.draw.rect(screen, (42, 157, 143) if primero else (65, 75, 95), fila, 2 if primero else 1, border_radius=8)
            muestra = pygame.Rect(fila.x + int(12 * sx), fila.centery - int(11 * sy), int(22 * sx), int(22 * sy))
            pygame.draw.rect(screen, hex_to_rgb(jug.get("color", "#FFFFFF")), muestra, border_radius=4)
            txt = f_row.render(f"#{jug['puesto']}   {jug.get('nombre', '?')} ({jug.get('color_nombre', '')})",
                               True, (255, 255, 255))
            screen.blit(txt, (muestra.right + int(12 * sx), fila.centery - txt.get_height() // 2))
            pj = f_row.render(f"{jug.get('puntos', 0)} PTS", True, (233, 196, 106) if primero else (195, 205, 225))
            screen.blit(pj, (fila.right - pj.get_width() - int(16 * sx), fila.centery - pj.get_height() // 2))

        bw, bh = int(480 * sx), int(44 * sy)
        btn_rect = pygame.Rect(modal.centerx - bw // 2, modal.bottom - bh - int(16 * sy), bw, bh)
        pygame.draw.rect(screen, (42, 157, 143), btn_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), btn_rect, 2, border_radius=8)
        eti = f_row.render("VOLVER AL LOBBY  [5to Boton Mando / Espacio / Enter]", True, (255, 255, 255))
        screen.blit(eti, (btn_rect.centerx - eti.get_width() // 2, btn_rect.centery - eti.get_height() // 2))

        for p in confeti:  # el confeti cae por delante del recuadro
            pygame.draw.rect(screen, p["color"], (int(p["x"]), int(p["y"]), p["w"], p["h"]))

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                resultado, corriendo = "cerrar", False
            elif evento.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(800, evento.w), max(540, evento.h)), pygame.RESIZABLE)
            elif evento.type == pygame.KEYDOWN and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                corriendo = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and btn_rect.collidepoint(evento.pos):
                corriendo = False

        pygame.display.flip()

    try:
        if sonido is not None:
            sonido.stop()
        if musica_pausada and pygame.mixer.get_init():
            pygame.mixer.music.unpause()
    except Exception:
        pass
    return resultado
