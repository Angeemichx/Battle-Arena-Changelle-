import os
from pathlib import Path

from dotenv import load_dotenv

from Servidor.adapters.json_repository import JsonRepository
from Servidor.use_cases.auth_service import AuthService
from Servidor.infraestructure.socket_server import ServidorJuego
from Servidor.adapters.smtp_mailer import MailerConRespaldo, SmtpMailer
from Servidor.adapters.json_historial import JsonHistorial
from Servidor.use_cases.estadisticas import Estadisticas
from Servidor.adapters.github_oauth import GithubOAuth
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
    ruta_hist = os.getenv("HISTORIAL_FILE", str(BASE / "infraestructure" / "data" / "historial.json"))
    Stats = Estadisticas(JsonHistorial(ruta_hist))

    if not mailers:
        raise SystemExit("Falta configurar SMTP_USER y SMTP_PASS en el .env")
    mailer = mailers[0] if len(mailers) == 1 else MailerConRespaldo(mailers)
    print(f"Remitentes configurados: {len(mailers)}", flush=True)

    auth = AuthService(repo, mailer)
    gh_id = os.getenv("GITHUB_CLIENT_ID")
    github = GithubOAuth(gh_id) if gh_id else None

    # Traduce la acción del mensaje
    def manejar(msg: dict, sesion: dict) -> dict:
        accion = msg.get("action")

        if accion == "request_code":
            return auth.solicitar_codigo_registro(msg.get("email", ""),msg.get("username", ""))

        if accion == "register_confirm":
            return auth.registrar_con_codigo(msg.get("email", ""),msg.get("username", ""),msg.get("password", ""),msg.get("code", ""))
    
        if accion == "register":
            return auth.registrar(msg.get("email", ""), msg.get("username", ""), msg.get("password", ""))

        if accion == "verify":
            return auth.verificar(msg.get("email", ""), msg.get("code", ""))

        if accion == "login":
            identificador = msg.get("identificador") or msg.get("email", "")
            resp = auth.login(identificador, msg.get("password", ""))

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
                msg.get("email", ""), msg.get("code", ""), msg.get("new_password", ""))
        
        if accion == "ranking":
            return {"ok": True, "ranking": Estadisticas.ranking()}

        if accion == "historial":
            return {"ok": True, "historial": Estadisticas.historial(msg.get("username", ""))}
        
        if accion == "oauth_start":
            if not github:
                return {"ok": False, "msg": "Login con GitHub no está configurado en el servidor."}
            try:
                d = github.iniciar()
            except Exception:
                return {"ok": False, "msg": "No se pudo contactar a GitHub."}
            return {"ok": True, "user_code": d["user_code"], "verification_uri": d["verification_uri"],
                    "device_code": d["device_code"], "interval": d.get("interval", 5)}

        if accion == "oauth_poll":
            if not github:
                return {"ok": False, "msg": "Login con GitHub no está configurado."}
            try:
                r = github.consultar(msg.get("device_code", ""))
                if "access_token" in r:
                    p = github.perfil(r["access_token"])
                    resp = auth.login_oauth("github", p["id"], p["email"], p["login"])
                    if resp["ok"]:
                        sesion["email"] = resp["email"]
                    return resp
            except Exception:
                return {"ok": False, "msg": "Error consultando a GitHub."}
            if r.get("error") in ("authorization_pending", "slow_down"):
                return {"ok": False, "pendiente": True, "msg": "Esperando autorización..."}
            return {"ok": False, "msg": "Autorización rechazada o expirada."}
        
        # Aquí se van sumando: verify, login, me, forgot, reset
        return {"ok": False, "msg": "Acción desconocida"}
     
    # Arrancar
    print(f"Datos en: {ruta}", flush=True)
    ServidorJuego(host, port, manejar, fin_partida=lambda js: Estadisticas.registrar_partida(js, 0)).run()


if __name__ == "__main__":
    main()