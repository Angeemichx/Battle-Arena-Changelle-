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
            if self.port == 465:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=15) as s:
                    s.login(self.user, self.password)
                    s.send_message(msg)
            else:  
                with smtplib.SMTP(self.host, self.port, timeout=15) as s:
                    s.starttls()
                    s.login(self.user, self.password)
                    s.send_message(msg)
            print(f"[MAIL] Enviado a {destino}", flush=True)
            return True
        except Exception as e:
            print(f"[MAIL] Error enviando a {destino}: {e}", flush=True)
            return False

class MailerConRespaldo:
    def __init__(self, mailers):
        self.mailers = mailers

    def enviar(self, destino: str, asunto: str, cuerpo: str):
        threading.Thread(
            target=self._intentar, args=(destino, asunto, cuerpo), daemon=True
        ).start()

    def _intentar(self, destino, asunto, cuerpo):
        for m in self.mailers:
            if m._enviar(destino, asunto, cuerpo):
                return
        print(f"[MAIL] Ningún proveedor pudo enviar a {destino}", flush=True)