import os
from pathlib import Path

from Servidor.adapters.json_repository import JsonRepository
from Servidor.use_cases.auth_service import AuthService
from Servidor.infraestructure.socket_server import ServidorJuego

BASE = Path(__file__).resolve().parent


def main():
    # Variables
    ruta = os.getenv("DATA_FILE", str(BASE / "infraestructure" / "data" / "usuarios.json"))
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5555"))

    # Crear adaptadores y casos de uso
    repo = JsonRepository(ruta)
    auth = AuthService(repo)

    # Traduce la acción del mensaje
    def manejar(msg: dict, sesion: dict) -> dict:
        accion = msg.get("action")

        if accion == "register":
            return auth.registrar(msg.get("email", ""), msg.get("username", ""), msg.get("password", ""))

        if accion == "verify":
            return auth.verificar(msg.get("email", ""), msg.get("code", ""))

        if accion == "login":
                resp = auth.login(msg.get("email", ""), msg.get("password", ""))
                if resp["ok"]:
                    sesion["email"] = resp["email"]
                return resp
    
        # Aquí se van sumando: verify, login, me, forgot, reset
        return {"ok": False, "msg": "Acción desconocida"}

    # Arrancar
    print(f"Datos en: {ruta}", flush=True)
    ServidorJuego(host, port, manejar).run()


if __name__ == "__main__":
    main()
