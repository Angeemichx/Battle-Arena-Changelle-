import os
from pathlib import Path

from dotenv import load_dotenv

from Servidor.adapters.json_repository import JsonRepository
from Servidor.use_cases.auth_service import AuthService
from Servidor.infraestructure.socket_server import ServidorJuego
from Servidor.adapters.smtp_mailer import SmtpMailer
from Servidor.adapters.consola_mailer import ConsolaMailer

BASE = Path(__file__).resolve().parent


def main():
    load_dotenv(BASE.parent / ".env")

    # Variables
    ruta = os.getenv("DATA_FILE", str(BASE / "infraestructure" / "data" / "usuarios.json"))
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5555"))

    # Crear adaptadores y casos de uso
    repo = JsonRepository(ruta)

    if os.getenv("SMTP_USER") and os.getenv("SMTP_PASS"):
        mailer = SmtpMailer(
            os.getenv("SMTP_HOST", "smtp.gmail.com"),
            int(os.getenv("SMTP_PORT", "465")),
            os.getenv("SMTP_USER"),
            os.getenv("SMTP_PASS"),
        )
        print("Mailer en uso: SmtpMailer", flush=True)
    else:
        mailer = ConsolaMailer()
        print("Sin credenciales SMTP: usando ConsolaMailer", flush=True)

    auth = AuthService(repo, mailer)

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

        if accion == "me":
            if "email" not in sesion:
                return {"ok": False, "msg": "Debes iniciar sesión"}
            return auth.perfil(sesion["email"])

        if accion == "forgot":
            return auth.olvide_password(msg.get("email", ""))

        if accion == "reset":
            return auth.restablecer_password(
                msg.get("email", ""), msg.get("code", ""), msg.get("new_password", "")
            )

        return {"ok": False, "msg": "Acción desconocida"}

    # Arrancar
    print(f"Datos en: {ruta}", flush=True)
    ServidorJuego(host, port, manejar).run()


if __name__ == "__main__":
    main()