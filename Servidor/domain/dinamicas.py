"""
Dinamicas de la partida (US-18, US-21, US-22): extraccion de energia, guardianes con
congelamiento y eventos especiales.

Todo el modulo es logica pura (sin sockets ni pygame): el servidor es la autoridad y los
clientes solo dibujan lo que reciben en el estado. Asi cumple CA-21.8 (el cliente no puede
cambiar las reglas) y se puede probar sin red.

REGLAS DEL JUEGO (documentadas para CA-18.4, CA-19.1, CA-21.2, CA-22.10)
------------------------------------------------------------------------
Extraccion (US-18 / US-19)
  * El reactor extrae solo si la partida esta activa, el jugador esta dentro del radio de
    extraccion (210 px al centro del reactor), no esta congelado y el reactor no esta
    sobrecargado.
  * La energia se paga por TIEMPO real medido por el servidor: 40 puntos por segundo
    (x2 durante el evento "Doble extraccion"). Mensajes repetidos o retransmitidos no
    suman nada extra porque no avanza el tiempo (CA-18.8, CA-19.4).
  * Moverse nunca da puntos.

Guardianes (US-21)
  * 4 guardianes base, uno en cada esquina de la arena.
  * Comportamiento: persiguen al avatar NO congelado mas cercano (200 px/s, mas lento que
    un jugador, que va a ~420 px/s). Si no hay a quien perseguir, vuelven a su puesto.
  * Contacto (<= 44 px): el jugador queda congelado `congelamiento` segundos (5 por
    defecto). Durante un evento especial, el contacto con alguien que ya esta congelado SUMA
    tiempo al que ya tenia (CA-21.10), con un maximo de 4 veces la duracion para que nadie
    quede inmovilizado para siempre. Fuera de eventos no se vuelve a congelar a un congelado.
  * Tras congelar, el guardian se "recarga" 3 s: se aleja a su puesto y no congela de nuevo.
  * Un jugador congelado no puede moverse ni extraer; al terminar el tiempo se libera solo.
  * Los guardianes nunca cambian el puntaje (CA-21.9).

Eventos especiales (US-22)
  * Se programan al iniciar la partida, uno a la vez (sin traslapes), repartidos entre el
    10 % y el 95 % de la duracion, en orden aleatorio:
      - Energia adicional (x3): aparece un icono en un lugar aleatorio; el primero que lo
        toque gana 80 puntos. Dura hasta 15 s.
      - Refuerzo de guardianes (x1): aparecen 5 guardianes extra hasta 30 s.
      - Sobrecarga del reactor (x2): el reactor se desactiva hasta 12 s.
      - Doble extraccion (x1, creativo): la extraccion paga el doble hasta 15 s.
      - Tormenta electrica (x1, creativo): los guardianes se mueven 1.6 veces mas rapido
        hasta 15 s.
  * Si la partida es muy corta, la duracion de cada evento se reduce para que quepan todos.
  * Al terminar un evento (o la partida) se restauran las condiciones anteriores.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Callable

ANCHO_ARENA = 3600
ALTO_ARENA = 2600
CENTRO_REACTOR = (1800, 1300)
RADIO_EXTRACCION = 210
MITAD_JUGADOR = 24          # los clientes envian la esquina del rect de 48 px

PUNTOS_POR_SEGUNDO = 40
MAX_BRECHA_EXTRACCION = 0.5  # una pausa mayor reinicia la "sesion" de extraccion

VELOCIDAD_GUARDIAN = 200.0
RADIO_CONTACTO = 44.0
RECARGA_GUARDIAN = 3.0
CONGELAMIENTO_DEFECTO = 5.0
MAX_ACUMULADO_CONGELAMIENTO = 4  # veces la duracion base

PUNTOS_ENERGIA_ADICIONAL = 80
RADIO_RECOGER_ENERGIA = 60.0
MULTIPLICADOR_TORMENTA = 1.6

BASES_GUARDIANES = [(400, 400), (3200, 400), (400, 2200), (3200, 2200)]
BASES_EXTRA = [(900, 500), (2700, 500), (900, 2100), (2700, 2100), (1800, 1900)]

REACTOR_DISPONIBLE = "disponible"
REACTOR_SOBRECARGADO = "sobrecargado"

# tipo -> (nombre visible, cuantas veces, duracion maxima en segundos)
EVENTOS = {
    "energia_adicional": ("Energia adicional", 3, 15.0),
    "guardianes_extra": ("Refuerzo de guardianes", 1, 30.0),
    "sobrecarga_reactor": ("Sobrecarga del reactor", 2, 12.0),
    "doble_extraccion": ("Doble extraccion", 1, 15.0),
    "tormenta_electrica": ("Tormenta electrica", 1, 15.0),
}

MOTIVO_INACTIVA = "La partida no esta activa"
MOTIVO_LEJOS = "Acercate al reactor para extraer"
MOTIVO_CONGELADO = "Estas congelado"
MOTIVO_SOBRECARGA = "Reactor en sobrecarga, espera"


@dataclass
class Guardian:
    id: int
    x: float
    y: float
    base: tuple
    extra: bool = False
    recarga: float = 0.0

    def to_dict(self) -> dict:
        return {"id": self.id, "x": int(round(self.x)), "y": int(round(self.y)), "extra": self.extra}


@dataclass
class EventoProgramado:
    tipo: str
    inicio: float
    duracion: float


@dataclass
class ResultadoExtraccion:
    ok: bool
    puntos: int = 0
    motivo: str | None = None   # texto para mostrar al jugador si no fue valida


def crear_cronograma(duracion_total: float, rng: random.Random) -> list[EventoProgramado]:
    """Reparte todos los eventos sin traslaparse entre el 10 % y el 95 % de la partida."""
    tipos = [t for t, (_, veces, _) in EVENTOS.items() for _ in range(veces)]
    rng.shuffle(tipos)
    if duracion_total <= 0:
        return []
    desde, hasta = duracion_total * 0.10, duracion_total * 0.95
    ranura = (hasta - desde) / len(tipos)
    cronograma = []
    for i, tipo in enumerate(tipos):
        dur = min(EVENTOS[tipo][2], ranura * 0.7)
        margen = ranura - dur
        inicio = desde + i * ranura + rng.uniform(0, margen * 0.6)
        cronograma.append(EventoProgramado(tipo, inicio, dur))
    return cronograma


class DinamicasPartida:
    """Estado y reglas de guardianes, eventos, congelamiento y extraccion de una partida."""

    def __init__(self, reloj: Callable[[], float] = time.monotonic, rng: random.Random | None = None):
        self.reloj = reloj
        self.rng = rng or random.Random()
        self.congelamiento = CONGELAMIENTO_DEFECTO
        self.reiniciar(0)

    # ------------------------------------------------------------------ ciclo de vida
    def reiniciar(self, duracion_total: float, congelamiento: float | None = None) -> None:
        """Deja todo como al inicio de una partida nueva de `duracion_total` segundos."""
        if congelamiento is not None:
            self.congelamiento = max(1.0, min(60.0, float(congelamiento)))
        self.inicio = self.reloj()
        self.ultimo_tick = self.inicio
        self.duracion_total = float(duracion_total)
        self.cronograma = crear_cronograma(self.duracion_total, self.rng)
        self._siguiente_evento = 0
        self.evento: dict | None = None      # evento activo (publico)
        self._fin_evento = 0.0
        self.reactor = REACTOR_DISPONIBLE
        self.congelados: dict[int, float] = {}      # id -> segundos restantes
        self._extrayendo: dict[int, tuple[float, float]] = {}  # id -> (ultimo instante, resto fraccionario)
        self._rechazos: dict[int, tuple[str, float]] = {}
        self._id_guardian = 0
        self.guardianes: list[Guardian] = []
        for base in BASES_GUARDIANES:
            self.guardianes.append(self._nuevo_guardian(base, extra=False))
        self.bonus_pendientes: list[tuple[int, int]] = []  # (id_jugador, puntos) por recoger energia

    def _nuevo_guardian(self, base, extra: bool) -> Guardian:
        self._id_guardian += 1
        return Guardian(self._id_guardian, float(base[0]), float(base[1]), base, extra)

    @property
    def transcurrido(self) -> float:
        return self.reloj() - self.inicio

    # ------------------------------------------------------------------ jugadores
    @staticmethod
    def centro(jugador) -> tuple[float, float]:
        return jugador.x + MITAD_JUGADOR, jugador.y + MITAD_JUGADOR

    def esta_congelado(self, id_jugador: int) -> bool:
        return self.congelados.get(id_jugador, 0.0) > 0.0

    def congelar(self, id_jugador: int, segundos: float | None = None) -> float:
        """Congela (o suma tiempo si ya estaba congelado, CA-21.10). Devuelve lo que le queda."""
        base = self.congelamiento if segundos is None else segundos
        actual = self.congelados.get(id_jugador, 0.0)
        nuevo = min(actual + base, base * MAX_ACUMULADO_CONGELAMIENTO)
        self.congelados[id_jugador] = nuevo
        return nuevo

    # ------------------------------------------------------------------ extraccion
    def _rechazo(self, id_jugador: int, motivo: str) -> ResultadoExtraccion:
        """Evita repetir el mismo aviso a cada fotograma del cliente (maximo 1 cada 1.5 s)."""
        ahora = self.reloj()
        previo = self._rechazos.get(id_jugador)
        if previo and previo[0] == motivo and ahora - previo[1] < 1.5:
            return ResultadoExtraccion(False, 0, None)
        self._rechazos[id_jugador] = (motivo, ahora)
        return ResultadoExtraccion(False, 0, motivo)

    def extraer(self, jugador, partida_activa: bool) -> ResultadoExtraccion:
        """Procesa un mensaje de extraccion de `jugador` y devuelve los puntos validos."""
        idj = jugador.id_jugador
        if not partida_activa:
            self._extrayendo.pop(idj, None)
            return self._rechazo(idj, MOTIVO_INACTIVA)
        if self.esta_congelado(idj):
            self._extrayendo.pop(idj, None)
            return self._rechazo(idj, MOTIVO_CONGELADO)
        if self.reactor != REACTOR_DISPONIBLE:
            self._extrayendo.pop(idj, None)
            return self._rechazo(idj, MOTIVO_SOBRECARGA)
        cx, cy = self.centro(jugador)
        if math.hypot(cx - CENTRO_REACTOR[0], cy - CENTRO_REACTOR[1]) > RADIO_EXTRACCION:
            self._extrayendo.pop(idj, None)
            return self._rechazo(idj, MOTIVO_LEJOS)

        ahora = self.reloj()
        ultimo, resto = self._extrayendo.get(idj, (ahora, 0.0))
        dt = ahora - ultimo
        if dt > MAX_BRECHA_EXTRACCION or dt < 0:
            dt, resto = 0.0, 0.0  # nueva sesion de extraccion: no regala puntos
        mult = 2 if self.evento and self.evento["tipo"] == "doble_extraccion" else 1
        bruto = resto + PUNTOS_POR_SEGUNDO * mult * dt
        puntos = int(bruto)
        self._extrayendo[idj] = (ahora, bruto - puntos)
        if puntos:
            jugador.puntaje += puntos
        return ResultadoExtraccion(True, puntos, None)

    # ------------------------------------------------------------------ avance del tiempo
    def tick(self, jugadores: dict, partida_activa: bool) -> None:
        """Avanza guardianes, congelamientos y eventos hasta el instante actual."""
        ahora = self.reloj()
        dt = max(0.0, min(ahora - self.ultimo_tick, 0.5))
        self.ultimo_tick = ahora

        if not partida_activa:
            self._terminar_evento()
            return

        # Congelamientos: se liberan solos (CA-21.6) y se limpian los jugadores que se fueron
        for idj in list(self.congelados):
            if idj not in jugadores:
                del self.congelados[idj]
                continue
            self.congelados[idj] -= dt
            if self.congelados[idj] <= 0:
                del self.congelados[idj]

        self._avanzar_eventos(jugadores)
        self._mover_guardianes(jugadores, dt)
        self._recoger_energia(jugadores)

    # ------------------------------------------------------------------ guardianes
    def _mover_guardianes(self, jugadores: dict, dt: float) -> None:
        velocidad = VELOCIDAD_GUARDIAN
        if self.evento and self.evento["tipo"] == "tormenta_electrica":
            velocidad *= MULTIPLICADOR_TORMENTA
        for g in self.guardianes:
            g.recarga = max(0.0, g.recarga - dt)
            objetivo = None if g.recarga > 0 else self._objetivo(g, jugadores)
            if objetivo is None:
                destino = g.base   # sin objetivo, o recargando tras congelar: vuelve a su puesto
            else:
                destino = self.centro(objetivo)
            dx, dy = destino[0] - g.x, destino[1] - g.y
            dist = math.hypot(dx, dy)
            paso = velocidad * dt
            if dist > 1e-6:
                f = min(1.0, paso / dist)
                g.x += dx * f
                g.y += dy * f
            g.x = min(max(g.x, 0.0), float(ANCHO_ARENA))
            g.y = min(max(g.y, 0.0), float(ALTO_ARENA))
            self._contacto(g, jugadores)

    def _objetivo(self, g: Guardian, jugadores: dict):
        """Avatar mas cercano que no este congelado (CA-21.11)."""
        mejor, mejor_d = None, None
        for idj, j in jugadores.items():
            if self.esta_congelado(idj):
                continue
            cx, cy = self.centro(j)
            d = math.hypot(cx - g.x, cy - g.y)
            if mejor_d is None or d < mejor_d:
                mejor, mejor_d = j, d
        return mejor

    def _contacto(self, g: Guardian, jugadores: dict) -> None:
        if g.recarga > 0:
            return
        for idj, j in jugadores.items():
            if self.esta_congelado(idj) and not self.evento:
                continue  # fuera de eventos un congelado no se vuelve a congelar encima
            cx, cy = self.centro(j)
            if math.hypot(cx - g.x, cy - g.y) <= RADIO_CONTACTO:
                self.congelar(idj)
                g.recarga = RECARGA_GUARDIAN
                self._extrayendo.pop(idj, None)
                return

    # ------------------------------------------------------------------ eventos
    def _avanzar_eventos(self, jugadores: dict) -> None:
        t = self.transcurrido
        if self.evento and t >= self._fin_evento:
            self._terminar_evento()
        if self.evento is None and self._siguiente_evento < len(self.cronograma):
            prog = self.cronograma[self._siguiente_evento]
            if t >= prog.inicio:
                self._siguiente_evento += 1       # cada evento se aplica una sola vez (CA-22.9)
                if t < prog.inicio + prog.duracion:
                    self._iniciar_evento(prog, t)

    def _iniciar_evento(self, prog: EventoProgramado, t: float) -> None:
        nombre = EVENTOS[prog.tipo][0]
        self._fin_evento = prog.inicio + prog.duracion
        self.evento = {"tipo": prog.tipo, "nombre": nombre, "activo": True}
        if prog.tipo == "energia_adicional":
            self.evento["x"] = self.rng.randint(450, ANCHO_ARENA - 450)
            self.evento["y"] = self.rng.randint(450, ALTO_ARENA - 450)
            # no aparece encima del reactor
            while math.hypot(self.evento["x"] - CENTRO_REACTOR[0], self.evento["y"] - CENTRO_REACTOR[1]) < 300:
                self.evento["x"] = self.rng.randint(450, ANCHO_ARENA - 450)
                self.evento["y"] = self.rng.randint(450, ALTO_ARENA - 450)
            self.evento["puntos"] = PUNTOS_ENERGIA_ADICIONAL
        elif prog.tipo == "guardianes_extra":
            for base in BASES_EXTRA:
                self.guardianes.append(self._nuevo_guardian(base, extra=True))
        elif prog.tipo == "sobrecarga_reactor":
            self.reactor = REACTOR_SOBRECARGADO
            self._extrayendo.clear()

    def _terminar_evento(self) -> None:
        if self.evento is None:
            return
        if self.evento["tipo"] == "guardianes_extra":
            self.guardianes = [g for g in self.guardianes if not g.extra]
        if self.evento["tipo"] == "sobrecarga_reactor":
            self.reactor = REACTOR_DISPONIBLE
        self.evento = None

    def _recoger_energia(self, jugadores: dict) -> None:
        ev = self.evento
        if not ev or ev["tipo"] != "energia_adicional":
            return
        for idj, j in jugadores.items():
            if self.esta_congelado(idj):
                continue
            cx, cy = self.centro(j)
            if math.hypot(cx - ev["x"], cy - ev["y"]) <= RADIO_RECOGER_ENERGIA:
                j.puntaje += ev["puntos"]           # el primero en llegar se lo lleva
                self.bonus_pendientes.append((idj, ev["puntos"]))
                self.evento = None                  # desaparece el icono
                return

    # ------------------------------------------------------------------ estado publico
    def estado_publico(self) -> dict:
        """Campos que se agregan al estado de la partida que reciben los clientes."""
        evento = None
        if self.evento:
            evento = dict(self.evento)
            evento["restante"] = max(0, int(round(self._fin_evento - self.transcurrido)))
        return {
            "guardianes": [g.to_dict() for g in self.guardianes],
            "estado_reactor": self.reactor,
            "evento_especial": evento,
            "congelados": {str(i): round(s, 1) for i, s in self.congelados.items()},
        }
