import smtplib
import threading
from email.mime.text import MIMEText

class SmtpMailer:
    def __init__(self, host: str, port: int, user: str, password: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
    # En un hilo aparte para no congelar el servidor mientras gmail responde
    def enviar(self, destino: str, asunto: str, cuerpo: str):
        threading.Thread(target=self._enviar, args=(destino, asunto, cuerpo), daemon=True).start()

    def _enviar(self, destino, asunto, cuerpo):
        msg = MIMEText(cuerpo, "plain", "utf-8")
        msg["From"] = self.user
        msg["To"] = destino
        msg["Subject"] = asunto
        try:
            with smtplib.SMTP_SSL(self.host, self.port) as s:
                s.login(self.user, self.password)
                s.send_message(msg)
            print(f"[MAIL SIMULADO] Para: {destino}\n{asunto}\n{cuerpo}\n", flush=True)
        except Exception as e:
            print(f"[MAIL] Error enviando a {destino}: {e}", flush=True)