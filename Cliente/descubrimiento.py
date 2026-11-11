
import json
import os
import socket

IP_BROADCAST_RADMIN = "26.255.255.255"
PUERTO_DESCUBRIMIENTO = 5556

MENSAJE_DESCUBRIMIENTO = "BATTLE_ARENA_DISCOVER_V1"


_cache: tuple[str, int] | None = None


def olvidar_servidor() -> None:
    """Descarta el servidor recordado (por ejemplo, si dejo de responder)."""
    global _cache
    _cache = None


def obtener_servidor(timeout: float = 3.0) -> tuple[str, int]:
    """
    Devuelve (IP, puerto TCP) del servidor, en este orden:
      1. Las variables de entorno SERVER_HOST / SERVER_PORT, si existen (pruebas locales o en LAN).
      2. El servidor ya encontrado antes en esta sesion (evita repetir el broadcast en cada peticion).
      3. Busqueda automatica por broadcast UDP en la red Radmin VPN.
    """
    global _cache
    manual = os.getenv("SERVER_HOST", "").strip()
    if manual:
        try:
            return manual, int(os.getenv("SERVER_PORT", "5555"))
        except ValueError:
            return manual, 5555
    if _cache is not None:
        return _cache
    _cache = _buscar_por_broadcast(timeout)
    return _cache


def _buscar_por_broadcast(timeout: float) -> tuple[str, int]:
    """Busca el servidor por broadcast UDP en la red Radmin VPN."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        mensaje = MENSAJE_DESCUBRIMIENTO.encode("utf-8")

        sock.sendto(
            mensaje,
            (IP_BROADCAST_RADMIN, PUERTO_DESCUBRIMIENTO)
        )

        while True:
            datos, direccion = sock.recvfrom(1024)

            try:
                respuesta = json.loads(datos.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            if respuesta.get("servicio") != MENSAJE_DESCUBRIMIENTO:
                continue

            ip = respuesta.get("ip")
            puerto = respuesta.get("puerto")

            if not isinstance(ip, str) or not ip.startswith("26."):
                continue

            if not isinstance(puerto, int):
                continue

            return ip, puerto

    except socket.timeout:
        raise ConnectionError(
            "No se encontró el servidor en la red Radmin VPN."
        )

    finally:
        sock.close()
