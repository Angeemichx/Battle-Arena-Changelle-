import socket
import threading
import json
import sys

HOST = "127.0.0.1"
PUERTO = 5555

#hilo que imprime:
def escuchar(sock, nombre):
    buffer = ""
    try:
        while True:
            datos = sock.recv(4096)
            if not datos:
                print(f"[{nombre}] Servidor cerró la conexión")
                break
            buffer += datos.decode("utf-8")
            while "\n" in buffer:
                linea, buffer = buffer.split("\n", 1)
                if linea.strip():
                    try:
                        msg = json.loads(linea)
                        print(f"[{nombre}] << {msg}")
                    except json.JSONDecodeError:
                        print(f"[{nombre}] << (no JSON): {linea}")
    except ConnectionResetError:
        print(f"[{nombre}] Conexión reseteada por el servidor")
    except Exception as e:
        print(f"[{nombre}] Error escuchando: {e}")


def main():
    nombre = sys.argv[1] if len(sys.argv) > 1 else "Anonimo"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PUERTO))
    except ConnectionRefusedError:
        print(f"[{nombre}] No se pudo conectar. ¿Está el servidor corriendo?")
        return

    print(f"[{nombre}] Conectado al servidor")

    hilo = threading.Thread(target=escuchar, args=(sock, nombre), daemon=True)
    hilo.start()

    # Menú de acciones
    try:
        while True:
            print(f"\n[{nombre}] Acciones:")
            print("  w = arriba    s = abajo")
            print("  a = izquierda d = derecha")
            print("  e = accion    q = salir")
            print("  i = iniciar partida (1 minuto)")
<<<<<<< HEAD

            print("  r = registrar   v = verificar   l = login")

=======
            print("  r = registrar   v = verificar   l = login")
            print("  m = perfil   f = olvidé contraseña   x = restablecer")
>>>>>>> Int4_auth_json
            tecla = input(f"[{nombre}] Tecla: ").strip().lower()

            if tecla == "q":
                break

            movimientos = {
                "w": (0, -1),
                "s": (0, 1),
                "a": (-1, 0),
                "d": (1, 0),}
            if tecla in ("r", "v", "l", "m", "f", "x"):
                if tecla == "m":
                    msg = {"action": "me"}
                else:
                    email = input("  Correo: ").strip()
                    if tecla == "r":
                        usuario = input("  Usuario: ").strip()
                        clave = input("  Contraseña: ").strip()
                        msg = {"action": "register", "email": email,
                            "username": usuario, "password": clave}
                    elif tecla == "v":
                        codigo = input("  Código: ").strip()
                        msg = {"action": "verify", "email": email, "code": codigo}
                    elif tecla == "l":
                        clave = input("  Contraseña: ").strip()
                        msg = {"action": "login", "email": email, "password": clave}
                    elif tecla == "f":
                        msg = {"action": "forgot", "email": email}
                    else:  # "x"
                        codigo = input("  Código: ").strip()
                        nueva = input("  Nueva contraseña: ").strip()
                        msg = {"action": "reset", "email": email,
                            "code": codigo, "new_password": nueva}

<<<<<<< HEAD
            if tecla in ("r", "v", "l"):
                email = input("  Correo: ").strip()
                if tecla == "r":
                    usuario = input("  Usuario: ").strip()
                    clave = input("  Contraseña: ").strip()
                    msg = {"action": "register", "email": email,
                           "username": usuario, "password": clave}
                elif tecla == "v":
                    codigo = input("  Código: ").strip()
                    msg = {"action": "verify", "email": email, "code": codigo}
                else:
                    clave = input("  Contraseña: ").strip()
                    msg = {"action": "login", "email": email, "password": clave}

            elif tecla in movimientos:


            if tecla in movimientos:

=======

            elif tecla in movimientos:
>>>>>>> Int4_auth_json
                dx, dy = movimientos[tecla]
                msg = {"tipo": "movimiento", "dx": dx, "dy": dy}
            elif tecla == "e":
                msg = {"tipo": "accion", "mensaje": f"{nombre} hizo accion!"}
            elif tecla == "i":
                msg = {"tipo": "configurar_partida", "minutos": 0.1}
                print(f"[{nombre}] Iniciando partida de 1 minuto...")
            else:
                print(f"[{nombre}] Tecla no reconocida")
                continue

            try:
                sock.sendall((json.dumps(msg) + "\n").encode("utf-8"))
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                print(f"[{nombre}] El servidor cerró la conexión")
                break

    except KeyboardInterrupt:
        pass
    finally:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        sock.close()
        print(f"\n[{nombre}] Desconectado")


if __name__ == "__main__":
    main()