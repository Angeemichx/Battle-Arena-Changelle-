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


def test_el_servidor_respeta_el_puntaje_del_cliente(servidor):
    _, a, b = dos(servidor)
    for _ in range(60):  # un segundo de movimiento a 60 mensajes/s
        a.enviar({"tipo": "movimiento", "x": 10, "y": 10, "puntaje": 10})
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["puntaje"] == 10)
    time.sleep(0.2)
    assert b.jugador(a.id)["puntaje"] == 10  # no se infla con cada mensaje


def test_sin_puntaje_se_mantiene_el_comportamiento_anterior(servidor):
    _, a, b = dos(servidor)
    for _ in range(3):
        a.enviar({"tipo": "movimiento", "x": 10, "y": 10})
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["puntaje"] == 3)


def test_puntaje_por_accion_en_el_reactor(servidor):
    _, a, b = dos(servidor)
    a.enviar({"tipo": "accion", "mensaje": "[EXTRAYENDO]", "puntaje": 80})
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["puntaje"] == 80)


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
    a.enviar({"tipo": "movimiento", "x": 100, "y": 100, "puntaje": 1})
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["x"] == 100)
    a.enviar({"tipo": "movimiento", "x": x, "y": y, "puntaje": 2})
    assert esperar(lambda: b.jugador(a.id)["puntaje"] == 2)
    assert (b.jugador(a.id)["x"], b.jugador(a.id)["y"]) == (100, 100)


@pytest.mark.parametrize("puntaje", [-1, "mucho", None, True, 10**9, 2.5])
def test_puntaje_invalido_no_se_acepta_como_valor(servidor, puntaje):
    _, a, b = dos(servidor)
    a.enviar({"tipo": "movimiento", "x": 1, "y": 1, "puntaje": puntaje})
    assert esperar(lambda: b.jugador(a.id) and b.jugador(a.id)["x"] == 1)
    assert b.jugador(a.id)["puntaje"] in (1,)  # cayo al comportamiento anterior: suma 1


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
