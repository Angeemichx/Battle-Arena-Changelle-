
import socket
import json

PUERTO_DESCUBRIMIENTO = 5556
PUERTO_SERVIDOR = 5555
MENSAJE_DESCUBRIMIENTO = "BATTLE_ARENA_DISCOVERy "


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
        f"[DESCUBRIMIENTO] Escuchando UDP en el puerto "
        f"{PUERTO_DESCUBRIMIENTO}",
        flush=True
    )

    while True:
        try:
            datos, direccion = servidor.recvfrom(1024)
            mensaje = datos.decode("utf-8", errors="ignore").strip()

            if mensaje != MENSAJE_DESCUBRIMIENTO:
                continue

            cliente_ip = direccion[0]

            # Solo atender solicitudes procedentes de Radmin.
            if not cliente_ip.startswith("26."):
                continue

            ip_servidor = obtener_ip_radmin(cliente_ip)

            if not ip_servidor or not ip_servidor.startswith("26."):
                print(
                    f"[DESCUBRIMIENTO] No se pudo determinar "
                    f"la IP Radmin para {cliente_ip}",
                    flush=True
                )
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


if __name__ == "__main__":
    iniciar_descubrimiento()
