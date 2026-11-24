"""Pruebas de aislamiento entre salas al crear sala o unirse por codigo."""
import json
import socket
import threading
import time

from Servidor.infraestructure.socket_server import ServidorJuego


def _puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _conectar(puerto: int):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    s.connect(("127.0.0.1", puerto))
    return s


def _leer_hasta(sock: socket.socket, predicado, timeout: float = 2.0):
    limite = time.time() + timeout
    buf = ""
    while time.time() < limite:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk.decode("utf-8")
        while "\n" in buf:
            linea, buf = buf.split("\n", 1)
            if not linea.strip():
                continue
            msg = json.loads(linea)
            if predicado(msg):
                return msg
    return None


def test_salas_aisladas_y_codigo_inexistente():
    puerto = _puerto_libre()
    srv = ServidorJuego("127.0.0.1", puerto, lambda m, s: {"ok": True})
    hilo = threading.Thread(target=srv.run, daemon=True)
    hilo.start()
    time.sleep(0.1)

    c1 = _conectar(puerto)
    c2 = _conectar(puerto)
    c3 = _conectar(puerto)
    try:
        c1.sendall((json.dumps({"tipo": "identificar", "nombre": "HostA", "crear_sala": True}) + "\n").encode("utf-8"))
        estado_a = _leer_hasta(
            c1,
            lambda m: m.get("tipo") == "estado" and any(j.get("nombre") == "HostA" for j in m.get("jugadores", [])),
        )
        assert estado_a is not None
        codigo_a = estado_a.get("sala")
        assert codigo_a and codigo_a != "DEFAULT"

        # Un segundo anfitrion crea otra sala distinta y no se mezcla con HostA
        c2.sendall((json.dumps({"tipo": "identificar", "nombre": "HostB", "crear_sala": True}) + "\n").encode("utf-8"))
        estado_b = _leer_hasta(
            c2,
            lambda m: m.get("tipo") == "estado" and any(j.get("nombre") == "HostB" for j in m.get("jugadores", [])),
        )
        assert estado_b is not None
        assert estado_b.get("sala") != codigo_a
        assert all(j.get("nombre") != "HostA" for j in estado_b.get("jugadores", []))

        # Intentar unirse con un codigo inexistente devuelve error y no mete a ninguna sala
        c3.sendall((json.dumps({"tipo": "identificar", "nombre": "Invitado", "sala": "ZZZZ"}) + "\n").encode("utf-8"))
        err = _leer_hasta(c3, lambda m: m.get("tipo") == "error")
        assert err is not None
        assert "no encontrada" in err.get("mensaje", "").lower()
    finally:
        for c in (c1, c2, c3):
            try:
                c.close()
            except Exception:
                pass
        try:
            srv.socket_servidor.close()
        except Exception:
            pass
