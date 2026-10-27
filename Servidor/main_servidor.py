import os
from pathlib import Path

from dotenv import load_dotenv

from Servidor.adapters.json_repository import JsonRepository
from Servidor.use_cases.auth_service import AuthService
from Servidor.infraestructure.socket_server import ServidorJuego
from Servidor.adapters.smtp_mailer import MailerConRespaldo, SmtpMailer

BASE = Path(__file__).resolve().parent

def crear_mailers():
    mailers = []
    for prefijo, host_def, port_def in (
        ("SMTP", "smtp.gmail.com", "587"),        
        ("SMTP2", "smtp-mail.outlook.com", "587")   
    ):
        user = os.getenv(f"{prefijo}_USER")
        pwd = os.getenv(f"{prefijo}_PASS")
        if user and pwd:
            mailers.append(SmtpMailer(
                os.getenv(f"{prefijo}_HOST", host_def),
                int(os.getenv(f"{prefijo}_PORT", port_def)),
                user,
                pwd,
            ))
    return mailers

def main():
    load_dotenv(BASE.parent / ".env")

    # Variables
    ruta = os.getenv("DATA_FILE", str(BASE / "infraestructure" / "data" / "usuarios.json"))
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5555"))
    repo = JsonRepository(ruta)
    mailers = crear_mailers()

    if not mailers:
        raise SystemExit("Falta configurar SMTP_USER y SMTP_PASS en el .env")
    mailer = mailers[0] if len(mailers) == 1 else MailerConRespaldo(mailers)
    print(f"Remitentes configurados: {len(mailers)}", flush=True)

    auth = AuthService(repo, mailer)

    # Traduce la acción del mensaje
    def manejar(msg: dict, sesion: dict) -> dict:
        accion = msg.get("action")

        if accion == "register":
            return auth.registrar(msg.get("email", ""), msg.get("username", ""), msg.get("password", ""))

        if accion == "verify":
            return auth.verificar(msg.get("email", ""), msg.get("code", ""))

        if accion == "login":
<<<<<<< HEAD
            resp = auth.login(msg.get("email", ""), msg.get("password", ""))
            if resp["ok"]:
                sesion["email"] = resp["email"]
            return resp

=======
                resp = auth.login(msg.get("email", ""), msg.get("password", ""))
                if resp["ok"]:
                    sesion["email"] = resp["email"]
                return resp
>>>>>>> f6d3519 (Resolucion de conflictos dentro del servidor)
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
<<<<<<< HEAD
        
        if accion == "request_code":
            return auth.solicitar_codigo_registro(msg.get("email", ""), msg.get("username", ""))

        if accion == "register_confirm":
            return auth.registrar_con_codigo(
                msg.get("email", ""), msg.get("username", ""),
                msg.get("password", ""), msg.get("code", ""),
            )

=======
        # Aquí se van sumando: verify, login, me, forgot, reset
>>>>>>> f6d3519 (Resolucion de conflictos dentro del servidor)
        return {"ok": False, "msg": "Acción desconocida"}

    # Arrancar
    print(f"Datos en: {ruta}", flush=True)
    ServidorJuego(host, port, manejar).run()


if __name__ == "__main__":
    main()