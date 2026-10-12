from infrastructure.socket_server import ServidorJuego

if __name__ == "__main__":
    servidor = ServidorJuego(limite_puntos=50)
    try:
        servidor.iniciar()
    except KeyboardInterrupt:
        print("\n[SERVIDOR] detenido por el usuario")