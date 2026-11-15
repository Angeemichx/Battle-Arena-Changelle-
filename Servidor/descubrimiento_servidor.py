
import socket
import json

PUERTO_DESCUBRIMIENTO = 5556
PUERTO_SERVIDOR = 5555
MENSAJE_DESCUBRIMIENTO = "BATTLE_ARENA_DISCOVER_V1"


def obtener_ip_radmin(cliente_ip: str) -> str | None:
    """
    Determina qué IP local utilizaría Windows para comunicarse
    con el cliente a través de Radmin VPN.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # UDP connect no establece una conexión TCP ni envía datos.
        sock.connect((cliente_ip, PUERTO_DESCUBRIMIENTO))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def iniciar_descubrimiento():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("0.0.0.0", PUERTO_DESCUBRIMIENTO))

    print(
        f"[DESCUBRIMIENTO] Escuchando UDP en el puerto {PUERTO_DESCUBRIMIENTO}",
        flush=True
    )

    while True:
        try:
            datos, direccion = servidor.recvfrom(1024)
            print(f"[DEBUG 1] Paquete recibido de {direccion}", flush=True)

            mensaje = datos.decode("utf-8", errors="ignore").strip()
            print(f"[DEBUG 2] Mensaje recibido: {repr(mensaje)}", flush=True)

            if mensaje != MENSAJE_DESCUBRIMIENTO:
                print(f"[DEBUG] Mensaje esperado: {repr(MENSAJE_DESCUBRIMIENTO)}", flush=True)
                print(f"[DEBUG] ¿Coinciden?: {mensaje == MENSAJE_DESCUBRIMIENTO}", flush=True)
                print("[DEBUG 3] Mensaje no reconocido", flush=True)
                continue

            cliente_ip = direccion[0]
            print(f"[DEBUG 4] IP del cliente: {cliente_ip}", flush=True)

            if not cliente_ip.startswith("26."):
                print("[DEBUG 5] IP fuera del rango Radmin", flush=True)
                continue

            print("[DEBUG 6] Obteniendo IP Radmin del servidor...", flush=True)

            ip_servidor = obtener_ip_radmin(cliente_ip)

            print(f"[DEBUG 7] IP detectada: {ip_servidor}", flush=True)

            if not ip_servidor or not ip_servidor.startswith("26."):
                print("[DEBUG 8] No se pudo determinar la IP Radmin", flush=True)
                continue

            respuesta = {
                "servicio": MENSAJE_DESCUBRIMIENTO,
                "ip": ip_servidor,
                "puerto": PUERTO_SERVIDOR
            }

            servidor.sendto(
                json.dumps(respuesta).encode("utf-8"),
                direccion
            )

            print(
                f"[DESCUBRIMIENTO] Cliente {cliente_ip} -> "
                f"{ip_servidor}:{PUERTO_SERVIDOR}",
                flush=True
            )

        except OSError as error:
            print(f"[DESCUBRIMIENTO] Error: {error}", flush=True)
        except Exception as error:
            print(f"[DEBUG] Error inesperado: {type(error).__name__}: {error}", flush=True)

if __name__ == "__main__":
    iniciar_descubrimiento()
