"""Busqueda del servidor: variable de entorno, memoria de la sesion y fallo del broadcast."""
import pytest

import Cliente.descubrimiento as d


@pytest.fixture(autouse=True)
def limpio(monkeypatch):
    d.olvidar_servidor()
    monkeypatch.delenv("SERVER_HOST", raising=False)
    monkeypatch.delenv("SERVER_PORT", raising=False)
    yield
    d.olvidar_servidor()


def falso_broadcast(monkeypatch, resultado):
    llamadas = []

    def buscar(timeout):
        llamadas.append(timeout)
        if isinstance(resultado, Exception):
            raise resultado
        return resultado

    monkeypatch.setattr(d, "_buscar_por_broadcast", buscar)
    return llamadas


def test_variable_de_entorno_tiene_prioridad_y_no_hace_broadcast(monkeypatch):
    monkeypatch.setenv("SERVER_HOST", "192.168.1.50")
    monkeypatch.setenv("SERVER_PORT", "6000")
    llamadas = falso_broadcast(monkeypatch, ("26.1.2.3", 5555))
    assert d.obtener_servidor() == ("192.168.1.50", 6000)
    assert llamadas == []


def test_puerto_invalido_en_entorno_usa_5555(monkeypatch):
    monkeypatch.setenv("SERVER_HOST", "10.0.0.5")
    monkeypatch.setenv("SERVER_PORT", "abc")
    assert d.obtener_servidor() == ("10.0.0.5", 5555)


def test_host_vacio_en_entorno_se_ignora(monkeypatch):
    monkeypatch.setenv("SERVER_HOST", "   ")
    falso_broadcast(monkeypatch, ("26.1.2.3", 5555))
    assert d.obtener_servidor() == ("26.1.2.3", 5555)


def test_el_servidor_encontrado_se_recuerda(monkeypatch):
    llamadas = falso_broadcast(monkeypatch, ("26.1.2.3", 5555))
    assert d.obtener_servidor() == ("26.1.2.3", 5555)
    assert d.obtener_servidor() == ("26.1.2.3", 5555)
    assert len(llamadas) == 1  # el segundo no repitio el broadcast


def test_olvidar_servidor_obliga_a_buscar_de_nuevo(monkeypatch):
    llamadas = falso_broadcast(monkeypatch, ("26.1.2.3", 5555))
    d.obtener_servidor()
    d.olvidar_servidor()
    d.obtener_servidor()
    assert len(llamadas) == 2


def test_si_no_se_encuentra_se_informa_y_no_se_recuerda_el_fallo(monkeypatch):
    falso_broadcast(monkeypatch, ConnectionError("No se encontró el servidor"))
    with pytest.raises(ConnectionError):
        d.obtener_servidor()
    llamadas = falso_broadcast(monkeypatch, ("26.9.9.9", 5555))
    assert d.obtener_servidor() == ("26.9.9.9", 5555) and len(llamadas) == 1


def test_broadcast_real_sin_servidor_agota_el_tiempo(monkeypatch):
    """Sin ningun servidor respondiendo, falla con ConnectionError en vez de colgarse."""
    class SocketFalso:
        def setsockopt(self, *a): pass
        def settimeout(self, t): pass
        def sendto(self, *a): pass
        def recvfrom(self, n): raise d.socket.timeout()
        def close(self): pass
    monkeypatch.setattr(d.socket, "socket", lambda *a, **k: SocketFalso())
    with pytest.raises(ConnectionError):
        d._buscar_por_broadcast(0.1)


def test_broadcast_ignora_respuestas_invalidas(monkeypatch):
    respuestas = [
        (b"no es json", ("1.1.1.1", 1)),
        (b'{"servicio": "OTRO", "ip": "26.1.1.1", "puerto": 5555}', ("1.1.1.1", 1)),
        (b'{"servicio": "BATTLE_ARENA_DISCOVER_V1", "ip": "192.168.0.9", "puerto": 5555}', ("1.1.1.1", 1)),
        (b'{"servicio": "BATTLE_ARENA_DISCOVER_V1", "ip": "26.4.5.6", "puerto": "5555"}', ("1.1.1.1", 1)),
        (b'{"servicio": "BATTLE_ARENA_DISCOVER_V1", "ip": "26.4.5.6", "puerto": 5555}', ("1.1.1.1", 1)),
    ]

    class SocketFalso:
        def setsockopt(self, *a): pass
        def settimeout(self, t): pass
        def sendto(self, *a): pass
        def recvfrom(self, n): return respuestas.pop(0)
        def close(self): pass
    monkeypatch.setattr(d.socket, "socket", lambda *a, **k: SocketFalso())
    assert d._buscar_por_broadcast(1.0) == ("26.4.5.6", 5555)
