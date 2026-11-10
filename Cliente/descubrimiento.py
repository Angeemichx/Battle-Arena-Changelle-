
import socket
import json

IP_BROADCAST_RADMIN = "26.255.255.255"
PUERTO_DESCUBRIMIENTO = 5556

MENSAJE_DESCUBRIMIENTO = "BATTLE_ARENA_DISCOVER_V1"


def obtener_servidor(timeout: float = 3.0) -> tuple[str, int]:
    """
    Busca automáticamente el servidor mediante broadcast UDP
    en la red Radmin VPN.

    Devuelve:
        (IP del servidor, puerto TCP)
    """

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
