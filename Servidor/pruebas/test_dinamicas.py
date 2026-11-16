"""Pruebas de las dinamicas de partida: extraccion (US-18), guardianes (US-21) y eventos (US-22)."""
import math
import random

import pytest

from Servidor.domain import dinamicas as d
from Servidor.domain.jugador import Jugador
from Servidor.domain.partida import Partida


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def avanzar(self, s):
        self.t += s


def crear(duracion=300, semilla=1, congelamiento=None):
    reloj = Reloj()
    din = d.DinamicasPartida(reloj=reloj, rng=random.Random(semilla))
    din.reiniciar(duracion, congelamiento)
    return din, reloj


def jugador(id_=1, x=0, y=0):
    return Jugador(id_jugador=id_, nombre=f"J{id_}", x=x, y=y)


def en_reactor(id_=1):
    # el cliente envia la esquina del rect de 48 px: el centro queda sobre el reactor
    return jugador(id_, d.CENTRO_REACTOR[0] - 24, d.CENTRO_REACTOR[1] - 24)


def sin_guardianes(din):
    din.guardianes.clear()


def extraer_durante(din, reloj, j, segundos, paso=1 / 60):
    din.extraer(j, True)
    for _ in range(int(segundos / paso)):
        reloj.avanzar(paso)
        din.extraer(j, True)


# ----------------------------------------------------------------- US-18 / US-19 extraccion
def test_extraer_en_el_reactor_paga_40_por_segundo():
    din, reloj = crear()
    j = en_reactor()
    extraer_durante(din, reloj, j, 3.0)
    assert 118 <= j.puntaje <= 120


def test_mensajes_repetidos_en_el_mismo_instante_no_suman():
    din, reloj = crear()
    j = en_reactor()
    din.extraer(j, True)
    reloj.avanzar(0.4)
    for _ in range(50):          # retransmisiones del mismo evento fisico
        din.extraer(j, True)
    assert j.puntaje in (15, 16)  # 0.4 s x 40 pts/s, sin importar cuantas copias lleguen


def test_enviar_mas_rapido_no_da_mas_puntos():
    din, reloj = crear()
    lento, rapido = en_reactor(1), en_reactor(2)
    din.extraer(lento, True), din.extraer(rapido, True)
    for _ in range(100):
        reloj.avanzar(0.01)
        din.extraer(rapido, True)
        din.extraer(rapido, True)   # el doble de mensajes
    din.extraer(lento, True)
    assert abs(rapido.puntaje - 40) <= 1


def test_una_pausa_larga_no_regala_puntos():
    din, reloj = crear()
    j = en_reactor()
    din.extraer(j, True)
    reloj.avanzar(10.0)
    din.extraer(j, True)
    assert j.puntaje == 0


@pytest.mark.parametrize("x,y", [(0, 0), (d.CENTRO_REACTOR[0] + 300, d.CENTRO_REACTOR[1])])
def test_fuera_de_zona_se_rechaza_con_motivo(x, y):
    din, _ = crear()
    j = jugador(1, x, y)
    r = din.extraer(j, True)
    assert not r.ok and r.motivo == d.MOTIVO_LEJOS and j.puntaje == 0


def test_partida_inactiva_se_rechaza():
    din, _ = crear()
    j = en_reactor()
    r = din.extraer(j, False)
    assert not r.ok and r.motivo == d.MOTIVO_INACTIVA and j.puntaje == 0


def test_el_motivo_no_se_repite_a_cada_mensaje():
    din, reloj = crear()
    j = jugador(1, 0, 0)
    assert din.extraer(j, True).motivo == d.MOTIVO_LEJOS
    for _ in range(20):
        reloj.avanzar(0.016)
        assert din.extraer(j, True).motivo is None
    reloj.avanzar(2.0)
    assert din.extraer(j, True).motivo == d.MOTIVO_LEJOS


def test_borde_del_radio_de_extraccion():
    din, _ = crear()
    dentro = jugador(1, d.CENTRO_REACTOR[0] - 24 + d.RADIO_EXTRACCION, d.CENTRO_REACTOR[1] - 24)
    fuera = jugador(2, d.CENTRO_REACTOR[0] - 24 + d.RADIO_EXTRACCION + 2, d.CENTRO_REACTOR[1] - 24)
    assert din.extraer(dentro, True).ok
    assert not din.extraer(fuera, True).ok


# ----------------------------------------------------------------- US-21 guardianes
def test_hay_cuatro_guardianes_en_los_extremos():
    din, _ = crear()
    assert len(din.guardianes) == 4
    for g in din.guardianes:
        assert g.x in (400, 3200) and g.y in (400, 2200)


def test_el_guardian_persigue_al_jugador_mas_cercano():
    din, reloj = crear()
    cerca, lejos = jugador(1, 700, 400), jugador(2, 3000, 2000)
    jugadores = {1: cerca, 2: lejos}
    g = din.guardianes[0]  # esquina (400, 400)
    antes = math.hypot(g.x - 724, g.y - 424)
    for _ in range(10):
        reloj.avanzar(0.1)
        din.tick(jugadores, True)
    assert math.hypot(g.x - 724, g.y - 424) < antes


def test_velocidad_del_guardian_es_razonable():
    din, reloj = crear()
    j = {1: jugador(1, 1800, 1300)}
    g = din.guardianes[0]
    x0, y0 = g.x, g.y
    reloj.avanzar(0.4)
    din.tick(j, True)
    recorrido = math.hypot(g.x - x0, g.y - y0)
    assert recorrido == pytest.approx(d.VELOCIDAD_GUARDIAN * 0.4, rel=0.01)
    assert d.VELOCIDAD_GUARDIAN < 420  # mas lento que un jugador (7 px por fotograma a 60 fps)


def test_el_contacto_congela_y_luego_se_libera_solo():
    din, reloj = crear(congelamiento=5)
    g = din.guardianes[0]
    g.x, g.y = 500.0, 500.0
    j = jugador(1, 500 - 24, 500 - 24)
    jugadores = {1: j}
    din.tick(jugadores, True)
    assert din.esta_congelado(1)
    assert din.congelados[1] == pytest.approx(5, abs=0.5)
    liberado = False
    for _ in range(80):
        reloj.avanzar(0.1)
        din.tick(jugadores, True)
        if not din.esta_congelado(1):
            liberado = True
            break
    assert liberado


def test_congelado_no_puede_extraer():
    din, _ = crear()
    j = en_reactor()
    din.congelar(1)
    r = din.extraer(j, True)
    assert not r.ok and r.motivo == d.MOTIVO_CONGELADO and j.puntaje == 0


def test_el_guardian_no_persigue_a_un_congelado_y_busca_a_otro():
    din, reloj = crear()
    g = din.guardianes[0]
    congelado, libre = jugador(1, 500, 500), jugador(2, 3000, 400)
    din.congelar(1, 60)
    jugadores = {1: congelado, 2: libre}
    for _ in range(5):
        reloj.avanzar(0.1)
        din.tick(jugadores, True)
    assert g.x > 400  # se va hacia el jugador libre (a la derecha), no hacia el congelado


def test_si_todos_estan_congelados_vuelve_a_su_puesto():
    din, reloj = crear()
    g = din.guardianes[0]
    g.x, g.y = 1000.0, 1000.0
    din.congelar(1, 60)
    jugadores = {1: jugador(1, 2000, 2000)}
    for _ in range(30):
        reloj.avanzar(0.1)
        din.tick(jugadores, True)
    assert math.hypot(g.x - 400, g.y - 400) < math.hypot(1000 - 400, 1000 - 400)


def test_contacto_con_congelado_suma_tiempo_con_tope():
    din, _ = crear(congelamiento=5)
    din.congelar(1)
    assert din.congelar(1) == pytest.approx(10)
    for _ in range(10):
        din.congelar(1)
    assert din.congelados[1] == pytest.approx(5 * d.MAX_ACUMULADO_CONGELAMIENTO)


def test_el_guardian_se_recarga_tras_congelar():
    din, reloj = crear(congelamiento=1)
    g = din.guardianes[0]
    g.x, g.y = 500.0, 500.0
    j = jugador(1, 500 - 24, 500 - 24)
    jugadores = {1: j}
    din.tick(jugadores, True)
    assert g.recarga > 0
    reloj.avanzar(0.1)
    din.tick(jugadores, True)
    assert math.hypot(g.x - 500, g.y - 500) > 0           # se aleja a su puesto
    assert din.congelados[1] < 1.0                         # no sumo otro congelamiento


def test_los_guardianes_no_cambian_el_puntaje():
    din, reloj = crear()
    g = din.guardianes[0]
    j = jugador(1, int(g.x) - 24, int(g.y) - 24)
    j.puntaje = 100
    din.tick({1: j}, True)
    assert j.puntaje == 100


def test_jugador_que_se_va_se_limpia():
    din, reloj = crear()
    din.congelar(7)
    reloj.avanzar(0.1)
    din.tick({}, True)
    assert 7 not in din.congelados


# ----------------------------------------------------------------- US-22 eventos
def test_cronograma_cumple_los_minimos_del_enunciado():
    for semilla in range(20):
        c = d.crear_cronograma(300, random.Random(semilla))
        tipos = [e.tipo for e in c]
        assert tipos.count("energia_adicional") >= 3
        assert tipos.count("sobrecarga_reactor") >= 2
        assert tipos.count("guardianes_extra") >= 1
        creativos = [t for t in tipos if t in ("doble_extraccion", "tormenta_electrica")]
        assert len(set(creativos)) >= 2


@pytest.mark.parametrize("duracion", [60, 180, 300, 900])
def test_eventos_sin_traslape_y_dentro_de_la_partida(duracion):
    for semilla in range(20):
        c = d.crear_cronograma(duracion, random.Random(semilla))
        c.sort(key=lambda e: e.inicio)
        for a, b in zip(c, c[1:]):
            assert a.inicio + a.duracion <= b.inicio + 1e-9
        assert c[0].inicio >= 0 and c[-1].inicio + c[-1].duracion <= duracion
        assert all(e.duracion > 0 for e in c)


def correr_hasta(din, reloj, jugadores, condicion, limite=400, paso=0.25):
    for _ in range(int(limite / paso)):
        reloj.avanzar(paso)
        din.tick(jugadores, True)
        if condicion():
            return True
    return False


def evento_de_tipo(din, reloj, jugadores, tipo, limite=400):
    return correr_hasta(din, reloj, jugadores, lambda: din.evento and din.evento["tipo"] == tipo, limite)


def test_sobrecarga_desactiva_el_reactor_y_luego_lo_restaura():
    din, reloj = crear()
    sin_guardianes(din)
    j = en_reactor()
    jugadores = {1: j}
    assert evento_de_tipo(din, reloj, jugadores, "sobrecarga_reactor")
    assert din.estado_publico()["estado_reactor"] == d.REACTOR_SOBRECARGADO
    r = din.extraer(j, True)
    assert not r.ok and r.motivo == d.MOTIVO_SOBRECARGA
    assert correr_hasta(din, reloj, jugadores, lambda: din.reactor == d.REACTOR_DISPONIBLE)
    assert din.evento is None


def test_sobrecarga_ocurre_al_menos_dos_veces():
    din, reloj = crear()
    sin_guardianes(din)
    jugadores = {1: jugador(1, 1800, 1300)}
    veces, antes = 0, False
    for _ in range(int(300 / 0.25)):
        reloj.avanzar(0.25)
        din.tick(jugadores, True)
        ahora = din.reactor == d.REACTOR_SOBRECARGADO
        veces += ahora and not antes
        antes = ahora
    assert veces >= 2


def test_energia_adicional_la_gana_el_primero_que_la_toca():
    din, reloj = crear()
    sin_guardianes(din)
    a, b = jugador(1, 3000, 2300), jugador(2, 3000, 100)
    jugadores = {1: a, 2: b}
    assert evento_de_tipo(din, reloj, jugadores, "energia_adicional")
    ev = din.evento
    a.x, a.y = ev["x"] - 24, ev["y"] - 24      # a llega primero
    din.tick(jugadores, True)
    assert a.puntaje == d.PUNTOS_ENERGIA_ADICIONAL
    assert din.evento is None                   # el icono desaparece
    b.x, b.y = ev["x"] - 24, ev["y"] - 24
    din.tick(jugadores, True)
    assert b.puntaje == 0                       # nadie mas lo cobra


def test_energia_adicional_aparece_tres_veces_y_en_sitios_validos():
    din, reloj = crear()
    sin_guardianes(din)
    jugadores = {1: jugador(1, 0, 0)}
    vistos = []
    for _ in range(int(300 / 0.25)):
        reloj.avanzar(0.25)
        din.tick(jugadores, True)
        ev = din.evento
        if ev and ev["tipo"] == "energia_adicional" and ev not in vistos and not any(v is ev for v in vistos):
            vistos.append(ev)
    assert len(vistos) >= 3
    for ev in vistos:
        assert 0 < ev["x"] < d.ANCHO_ARENA and 0 < ev["y"] < d.ALTO_ARENA
        assert math.hypot(ev["x"] - d.CENTRO_REACTOR[0], ev["y"] - d.CENTRO_REACTOR[1]) >= 300


def test_refuerzo_agrega_cinco_guardianes_y_luego_se_van():
    din, reloj = crear()
    jugadores = {1: jugador(1, 1800, 1300)}
    assert evento_de_tipo(din, reloj, jugadores, "guardianes_extra")
    assert len(din.guardianes) == 9
    assert sum(g.extra for g in din.guardianes) == 5
    assert correr_hasta(din, reloj, jugadores, lambda: din.evento is None)
    assert len(din.guardianes) == 4 and not any(g.extra for g in din.guardianes)


def test_doble_extraccion_duplica_los_puntos():
    din, reloj = crear()
    sin_guardianes(din)
    j = en_reactor()
    jugadores = {1: j}
    assert evento_de_tipo(din, reloj, jugadores, "doble_extraccion")
    j.x, j.y = d.CENTRO_REACTOR[0] - 24, d.CENTRO_REACTOR[1] - 24
    din.congelados.clear()
    j.puntaje = 0
    din.extraer(j, True)
    for _ in range(60):
        reloj.avanzar(1 / 60)
        din.extraer(j, True)
    assert 78 <= j.puntaje <= 80


def test_tormenta_acelera_a_los_guardianes():
    din, reloj = crear()
    jugadores = {1: jugador(1, 1800, 1300)}
    assert evento_de_tipo(din, reloj, jugadores, "tormenta_electrica")
    din.congelados.clear()
    jugadores[1].x, jugadores[1].y = 3000, 2000
    g = din.guardianes[0]
    g.x, g.y, g.recarga = 400.0, 400.0, 0.0
    reloj.avanzar(0.4)
    din.tick(jugadores, True)
    recorrido = math.hypot(g.x - 400, g.y - 400)
    assert recorrido == pytest.approx(d.VELOCIDAD_GUARDIAN * d.MULTIPLICADOR_TORMENTA * 0.4, rel=0.05)


def test_cada_evento_se_activa_una_sola_vez():
    din, reloj = crear()
    sin_guardianes(din)
    jugadores = {1: jugador(1, 0, 0)}
    inicios = 0
    antes = None
    for _ in range(int(300 / 0.25)):
        reloj.avanzar(0.25)
        din.tick(jugadores, True)
        actual = None if din.evento is None else id(din.evento)
        if actual is not None and actual != antes:
            inicios += 1
        antes = actual
    assert inicios <= len(din.cronograma)


def test_sin_partida_activa_no_hay_eventos_ni_efectos():
    din, reloj = crear()
    jugadores = {1: jugador(1, 1800, 1300)}
    assert evento_de_tipo(din, reloj, jugadores, "sobrecarga_reactor")
    din.tick(jugadores, False)
    assert din.evento is None and din.reactor == d.REACTOR_DISPONIBLE
    pos = [(g.x, g.y) for g in din.guardianes]
    reloj.avanzar(5)
    din.tick(jugadores, False)
    assert pos == [(g.x, g.y) for g in din.guardianes]


def test_estado_publico_tiene_el_formato_que_dibuja_el_cliente():
    din, reloj = crear()
    pub = din.estado_publico()
    assert set(pub) >= {"guardianes", "estado_reactor", "evento_especial"}
    assert all({"id", "x", "y"} <= set(g) for g in pub["guardianes"])
    assert pub["evento_especial"] is None
    assert evento_de_tipo(din, reloj, {1: jugador(1, 0, 0)}, "doble_extraccion")
    ev = din.estado_publico()["evento_especial"]
    assert ev["activo"] and ev["nombre"] == "Doble extraccion" and ev["restante"] >= 0


# ----------------------------------------------------------------- integracion con Partida
def partida_con_jugadores(modo=None, puntos=500):
    p = Partida("t", limite_puntos=50)
    a, b = jugador(1, 0, 0), jugador(2, 100, 100)
    p.agregar_jugador(a)
    p.agregar_jugador(b)
    reloj = Reloj()
    p.dinamicas = d.DinamicasPartida(reloj=reloj, rng=random.Random(3))
    p.iniciar_cronometro(5, puntos=puntos, modo=modo)
    return p, a, b, reloj


def test_partida_usa_la_meta_configurada_y_reinicia_puntajes():
    p, a, _, _ = partida_con_jugadores(puntos=500)
    a.puntaje = 300
    p.iniciar_cronometro(5, puntos=500)
    assert a.puntaje == 0 and p.limite_puntos == 500


def test_extraer_hasta_la_meta_finaliza_y_bloquea_nuevas_acciones():
    p, a, b, reloj = partida_con_jugadores(modo="puntos", puntos=100)
    a.x, a.y = d.CENTRO_REACTOR[0] - 24, d.CENTRO_REACTOR[1] - 24
    p.extraer(1)
    for _ in range(400):
        reloj.avanzar(1 / 60)
        p.extraer(1)
        if not p.activa:
            break
    assert not p.activa and p.ganador == 1
    estado = p.estado_actual()
    assert estado["partida_finalizada"] and estado["ganador_id"] == 1
    puntos = a.puntaje
    reloj.avanzar(1)
    r = p.extraer(1)
    assert not r.ok and a.puntaje == puntos           # CA-25.3


def test_modo_tiempo_ignora_la_meta_de_puntos():
    p, a, _, _ = partida_con_jugadores(modo="tiempo", puntos=100)
    a.puntaje = 500
    p._verificar_ganador()
    assert p.activa


def test_modo_puntos_no_termina_por_tiempo():
    p, _, _, _ = partida_con_jugadores(modo="puntos", puntos=100)
    p.tiempo_inicio -= 10_000
    p.verificar_tiempo()
    assert p.activa


def test_estado_incluye_congelamiento_por_jugador():
    p, a, _, _ = partida_con_jugadores()
    p.dinamicas.congelar(1)
    est = {j["id"]: j for j in p.estado_actual()["jugadores"]}
    assert est[1]["congelado"] and est[1]["congelado_restante"] > 0
    assert not est[2]["congelado"]


def test_energia_adicional_puede_dar_la_victoria():
    p, a, b, reloj = partida_con_jugadores(modo="puntos", puntos=d.PUNTOS_ENERGIA_ADICIONAL)
    jugadores = p.jugadores
    for _ in range(2000):
        reloj.avanzar(0.25)
        p.tick()
        ev = p.dinamicas.evento
        if ev and ev["tipo"] == "energia_adicional":
            a.x, a.y = ev["x"] - 24, ev["y"] - 24
            p.tick()
            break
    assert not p.activa and p.ganador == 1
