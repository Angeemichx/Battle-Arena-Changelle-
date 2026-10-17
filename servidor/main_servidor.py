import os
from pathlib import Path

from servidor.adapters.json_repository import JsonRepository
from servidor.use_cases.auth_service import AuthService
from servidor.infraestructure.socket_server import ServidorJuego


BASE = Path(__file__).resolve().parent


def main():
    #variables
    ruta = os.getenv("DATA_FILE", str(BASE / "infraestructure" / "data" / "usuarios.json"))
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5555"))

    #Crear adaptadores y casos de uso
    repo = JsonRepository(ruta)
    auth = AuthService(repo)

    # traduce la acción del mensaje 
    def manejar(msg: dict, sesion: dict) -> dict:
        accion = msg.get("action")

        if accion == "register":
            return auth.registrar(msg.get("email", ""), msg.get("username", ""), msg.get("password", ""))

        # Aquí se van sumando: verify, login, me, forgot, reset

        return {"ok": False, "msg": "Acción desconocida"}

    # 5. Arrancar
    print(f"Datos en: {ruta}", flush=True)
    ServidorJuego(host, port, manejar).run()


if __name__ == "__main__":
    servidor = ServidorJuego(limite_puntos=50)
    try:
        servidor.iniciar()
    except KeyboardInterrupt:
        print("\n[SERVIDOR] detenido por el usuario")