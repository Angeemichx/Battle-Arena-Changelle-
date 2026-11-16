"""Movimiento entre jugadores contra el servidor real (sockets en localhost)."""
import json
import socket
import threading
import time

import pytest

from Servidor.infraestructure.socket_server import ServidorJuego


def _puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Cliente:
    def __init__(self, puerto, nombre=None):
        self.sock = socket.create_connection(("127.0.0.1", puerto), timeout=2)
        self.sock.settimeout(None)
        self.id, self.estado, self.lineas_invalidas = None, {}, 0
        self.rechazos = []
        threading.Thread(target=self._leer, daemon=True).start()
        if nombre:
            self.enviar({"tipo": "identificar", "nombre": nombre})

    def enviar(self, mensaje):
        self.sock.sendall((json.dumps(mensaje) + "\n").encode())

    def _leer(self):
        buf = ""
        try:
            while True:
                datos = self.sock.recv(4096)
                if not datos:
                    return
                buf += datos.decode()
                while "\n" in buf:
                    linea, buf = buf.split("\n", 1)
                    try:
                        m = json.loads(linea)
                    except ValueError:
                        self.lineas_invalidas += 1
                        continue
                    if m.get("tipo") == "bienvenida":
                        self.id = m["id_jugador"]
                    elif m.get("tipo") == "estado":
                        self.estado = m
                    elif m.get("tipo") == "rechazo":
                        self.rechazos.append(m["mensaje"])
        except OSError:
            pass

    def jugador(self, id_):
        return next((j for j in self.estado.get("jugadores", []) if j["id"] == id_), None)


def esperar(cond, tiempo=2.0):
    fin = time.time() + tiempo
    while time.time() < fin:
        if cond():
            return True
        time.sleep(0.02)
    return False


@pytest.fixture
def servidor():
    puerto = _puerto_libre()
    srv = ServidorJuego("127.0.0.1", puerto, lambda m, s: {"ok": True})
    threading.Thread(target=srv.run, daemon=True).start()
    esperar(lambda: _acepta(puerto))
    clientes = []
    yield srv, puerto, clientes
    for c in clientes:
        c.sock.close()
    srv.socket_servidor.close()


def _acepta(puerto):
    try:
        socket.create_connection(("127.0.0.1", puerto), timeout=0.2).close()
        return True
    except OSError:
        return False


def dos(servidor):
    srv, puerto, clientes = servidor
    a, b = Cliente(puerto, "Ana"), Cliente(puerto, "Beto")
    clientes += [a, b]
    assert esperar(lambda: a.id and b.id and len(b.estado.get("jugadores", [])) == 2)
    return srv, a, b


# ---------- positivas ----------
def test_ambos_jugadores_reciben_la_posicion_del_otro(servidor):
    _, a, b = dos(servidor)
    a.enviar({"tipo": "movimiento", "x": 500, "y": 200})
    b.enviar({"tipo": "movimiento", "x": 1500, "y": 900})
    assert esperar(lambda: a.jugador(b.id) and a.jugador(b.id)["x"] == 1500 and a.jugador(a.id)["x"] == 500)
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["x"] == 500 and b.jugador(b.id)["y"] == 900)


def test_el_servidor_ignora_el_puntaje_que_informa_el_cliente(servidor):
    """CA-19.4 / CA-21.8: el puntaje lo decide el servidor, no el cliente."""
    _, a, b = dos(servidor)
    for _ in range(60):
        a.enviar({"tipo": "movimiento", "x": 10, "y": 10, "puntaje": 9999})
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["x"] == 10)
    time.sleep(0.2)
    assert b.jugador(a.id)["puntaje"] == 0


def test_moverse_no_suma_puntos(servidor):
    _, a, b = dos(servidor)
    for _ in range(3):
        a.enviar({"tipo": "movimiento", "x": 10, "y": 10})
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["x"] == 10)
    assert b.jugador(a.id)["puntaje"] == 0  # moverse no da puntos


def _iniciar_partida(srv, a, **extra):
    a.enviar({"tipo": "configurar_partida", "minutos": 5, **extra})
    assert esperar(lambda: a.estado.get("activa"))


def _al_reactor(a, b):
    a.enviar({"tipo": "movimiento", "x": 1800 - 24, "y": 1300 - 24})
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["x"] == 1776)


def test_extraer_en_el_reactor_se_paga_por_tiempo(servidor):
    """US-18: +40 pts/s medidos por el servidor, sin importar cuantos mensajes lleguen."""
    srv, a, b = dos(servidor)
    _iniciar_partida(srv, a, puntos=500, modo="puntos")
    _al_reactor(a, b)
    fin = time.time() + 1.0
    while time.time() < fin:
        a.enviar({"tipo": "accion", "mensaje": "[EXTRAYENDO]"})
        time.sleep(0.016)
    time.sleep(0.2)
    pts = b.jugador(a.id)["puntaje"]
    assert 25 <= pts <= 50


def test_mensajes_de_extraccion_duplicados_no_inflan_el_puntaje(servidor):
    srv, a, b = dos(servidor)
    _iniciar_partida(srv, a, puntos=500, modo="puntos")
    _al_reactor(a, b)
    for _ in range(200):                      # 200 copias casi simultaneas
        a.enviar({"tipo": "accion", "mensaje": "[EXTRAYENDO]"})
    time.sleep(0.4)
    assert b.jugador(a.id)["puntaje"] <= 16   # a lo sumo lo que avanzo el reloj (~0.4 s x 40)


def test_extraer_lejos_del_reactor_se_rechaza_con_motivo(servidor):
    srv, a, b = dos(servidor)
    _iniciar_partida(srv, a)
    a.enviar({"tipo": "movimiento", "x": 10, "y": 10})
    a.enviar({"tipo": "accion", "mensaje": "[EXTRAYENDO]"})
    assert esperar(lambda: a.rechazos)
    assert "reactor" in a.rechazos[0].lower()
    assert b.jugador(a.id)["puntaje"] == 0 and not b.rechazos


def test_extraer_sin_partida_activa_se_rechaza(servidor):
    _, a, b = dos(servidor)
    _al_reactor(a, b)
    a.enviar({"tipo": "accion", "mensaje": "[EXTRAYENDO]"})
    assert esperar(lambda: a.rechazos and "activa" in a.rechazos[0])
    assert b.jugador(a.id)["puntaje"] == 0


def test_el_estado_incluye_guardianes_reactor_y_evento(servidor):
    srv, a, b = dos(servidor)
    _iniciar_partida(srv, a)
    assert esperar(lambda: len(b.estado.get("guardianes", [])) == 4)
    assert b.estado["estado_reactor"] == "disponible"
    assert "evento_especial" in b.estado


def test_los_guardianes_se_mueven_y_todos_ven_lo_mismo(servidor):
    srv, a, b = dos(servidor)
    _iniciar_partida(srv, a)
    assert esperar(lambda: a.estado.get("guardianes") and b.estado.get("guardianes"))
    antes = [(g["x"], g["y"]) for g in b.estado["guardianes"]]
    time.sleep(0.7)
    assert [(g["x"], g["y"]) for g in b.estado["guardianes"]] != antes


def test_jugador_congelado_no_se_mueve_ni_extrae(servidor):
    """US-21 / CA-21.8: el congelamiento lo aplica el servidor y el cliente no puede ignorarlo."""
    srv, a, b = dos(servidor)
    _iniciar_partida(srv, a, puntos=500, modo="puntos")
    _al_reactor(a, b)
    with srv.lock:
        srv.partida.dinamicas.congelar(a.id, 30)
    assert esperar(lambda: b.jugador(a.id)["congelado"])
    a.enviar({"tipo": "movimiento", "x": 3000, "y": 2000})
    time.sleep(0.3)
    assert b.jugador(a.id)["x"] == 1776                 # no se movio
    a.enviar({"tipo": "accion", "mensaje": "[EXTRAYENDO]"})
    assert esperar(lambda: a.rechazos and "congelado" in a.rechazos[0].lower())


def test_configurar_partida_aplica_meta_y_modo(servidor):
    srv, a, b = dos(servidor)
    _iniciar_partida(srv, a, puntos=300, modo="puntos", congelamiento=7)
    assert esperar(lambda: b.estado.get("puntos_meta") == 300 and b.estado.get("modo") == "puntos")
    assert srv.partida.dinamicas.congelamiento == 7


def test_al_llegar_a_la_meta_el_servidor_cierra_y_avisa(servidor):
    srv, a, b = dos(servidor)
    _iniciar_partida(srv, a, puntos=20, modo="puntos")
    _al_reactor(a, b)
    fin = time.time() + 3
    while time.time() < fin and not b.estado.get("partida_finalizada"):
        a.enviar({"tipo": "accion", "mensaje": "[EXTRAYENDO]"})
        time.sleep(0.016)
    assert esperar(lambda: a.estado.get("partida_finalizada") and b.estado.get("partida_finalizada"))
    assert a.estado["ganador_id"] == a.id == b.estado["ganador_id"]
    puntos = b.jugador(a.id)["puntaje"]
    a.enviar({"tipo": "accion", "mensaje": "[EXTRAYENDO]"})
    time.sleep(0.2)
    assert b.jugador(a.id)["puntaje"] == puntos         # CA-25.3: nada cambia tras el final


def test_el_color_se_comparte(servidor):
    _, a, b = dos(servidor)
    a.enviar({"tipo": "movimiento", "x": 5, "y": 5, "puntaje": 0, "color": "#2A9D8F"})
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["color"] == "#2A9D8F")


def test_el_servidor_usa_tcp_nodelay(servidor):
    srv, a, b = dos(servidor)
    for s in list(srv.clientes.values()):
        assert s.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY) != 0


def test_mensajes_simultaneos_llegan_enteros(servidor):
    _, a, b = dos(servidor)
    hilos = [threading.Thread(target=lambda c=c: [c.enviar({"tipo": "movimiento", "x": i, "y": i, "puntaje": i}) for i in range(150)]) for c in (a, b)]
    [h.start() for h in hilos]; [h.join() for h in hilos]
    time.sleep(0.5)
    assert a.lineas_invalidas == 0 and b.lineas_invalidas == 0


# ---------- negativas ----------
@pytest.mark.parametrize("x,y", [("abc", 5), (None, None), (True, 5), (10**9, 5), (5, -10**9), (1.5, 2)])
def test_coordenadas_invalidas_no_mueven_ni_rompen_al_jugador(servidor, x, y):
    _, a, b = dos(servidor)
    a.enviar({"tipo": "movimiento", "x": 100, "y": 100, "color": "#111111"})
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["x"] == 100)
    a.enviar({"tipo": "movimiento", "x": x, "y": y, "color": "#222222"})
    assert esperar(lambda: b.jugador(a.id)["color"] == "#222222")  # el mensaje si se proceso
    assert (b.jugador(a.id)["x"], b.jugador(a.id)["y"]) == (100, 100)


@pytest.mark.parametrize("puntaje", [-1, "mucho", None, True, 10**9, 2.5])
def test_puntaje_invalido_no_se_acepta_como_valor(servidor, puntaje):
    _, a, b = dos(servidor)
    a.enviar({"tipo": "movimiento", "x": 1, "y": 1, "puntaje": puntaje})
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["x"] == 1)
    assert b.jugador(a.id)["puntaje"] == 0  # un puntaje invalido se ignora y moverse no suma


@pytest.mark.parametrize("color", ["rojo", "#12", "#GGGGGG", 5, "<script>"])
def test_color_invalido_se_ignora(servidor, color):
    _, a, b = dos(servidor)
    a.enviar({"tipo": "movimiento", "x": 1, "y": 1, "puntaje": 0, "color": color})
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["x"] == 1)
    assert b.jugador(a.id)["color"] is None


def test_cliente_no_identificado_no_aparece_ni_rompe(servidor):
    srv, puerto, clientes = servidor
    c = Cliente(puerto)  # sin identificar
    clientes.append(c)
    assert esperar(lambda: c.id)
    c.enviar({"tipo": "movimiento", "x": 5, "y": 5, "puntaje": 5})
    time.sleep(0.2)
    assert c.id not in srv.partida.jugadores


def test_al_detenerse_ambos_clientes_quedan_con_la_posicion_final(servidor):
    """Regresion: con dos jugadores moviendose a la vez, un estado viejo podia llegar despues de uno
    nuevo y el avatar del rival quedaba clavado unos pixeles atras."""
    _, a, b = dos(servidor)

    def mover(c, base):
        for i in range(200):
            c.enviar({"tipo": "movimiento", "x": base + i, "y": base, "puntaje": i})

    hilos = [threading.Thread(target=mover, args=(c, base)) for c, base in ((a, 100), (b, 1000))]
    [h.start() for h in hilos]; [h.join() for h in hilos]
    assert esperar(lambda: a.jugador(b.id) and a.jugador(b.id)["x"] == 1199 and a.jugador(a.id)["x"] == 299)
    time.sleep(0.3)
    for c in (a, b):
        assert (c.jugador(a.id)["x"], c.jugador(b.id)["x"]) == (299, 1199)
