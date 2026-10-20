import re
import secrets
import bcrypt
from datetime import datetime, timedelta, timezone

from Servidor.domain.cuenta import Cuenta

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class AuthService:
<<<<<<< HEAD
    def __init__(self, repo):

        self.repo = repo       
=======
    def __init__(self, repo, mailer):
        self.repo = repo
        self.mailer = mailer
>>>>>>> Int4_auth_json


    def registrar(self, email: str, username: str, password: str) -> dict:
        email = email.strip().lower()
        username = username.strip()

        if not EMAIL_RE.match(email):
            return {"ok": False, "msg": "Correo inválido"}
        if not self._password_valida(password):
            return {"ok": False, "msg": "Contraseña: mínimo 8 caracteres con letras y números"}
        if not username:
            return {"ok": False, "msg": "Usuario requerido"}

<<<<<<< HEAD

        # evita que dos registros iguales se crucen
        with self.repo.lock:
            if self.repo.get_by_email(email) or self.repo.username_exists(username):

=======
        with self.repo.lock:
            if self.repo._email(email) or self.repo.user_exists(username):
>>>>>>> Int4_auth_json
                return {"ok": False, "msg": "Correo o usuario ya registrado"}

            codigo = f"{secrets.randbelow(10**6):06d}"
            cuenta = Cuenta(
                email=email,
                username=username,
                password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
                verify_code=codigo,
                verify_expires=(_ahora() + timedelta(minutes=15)).isoformat(),
                created_at=_ahora().isoformat(),
            )
            self.repo.save(cuenta)

        self.mailer.enviar(
            email,
            "Verifica tu cuenta",
            f"Tu código de verificación es: {codigo}\nExpira en 15 minutos.",
        )
        return {"ok": True, "msg": "Cuenta creada. Revisa tu correo."}

    def verificar(self, email: str, codigo: str) -> dict:
        email = email.strip().lower()
        with self.repo.lock:
            c = self.repo._email(email)
            if (not c or c.verify_code != codigo or not c.verify_expires
                    or datetime.fromisoformat(c.verify_expires) < _ahora()):
                return {"ok": False, "msg": "Código inválido o expirado"}
            c.verified, c.verify_code, c.verify_expires = True, None, None
            self.repo.save(c)
        return {"ok": True, "msg": "Correo verificado"}

    def login(self, email: str, password: str) -> dict:
        email = email.strip().lower()
        c = self.repo._email(email)
        if not c or not bcrypt.checkpw(password.encode(), c.password_hash.encode()):
            return {"ok": False, "msg": "Credenciales incorrectas"}
        if not c.verified:
            return {"ok": False, "msg": "Debes verificar tu correo primero"}
        return {"ok": True, "msg": "Bienvenido", "email": email}
    
    def perfil(self, email: str) -> dict:
        c = self.repo._email(email)
        if not c:
            return {"ok": False, "msg": "Cuenta no encontrada"}
        return {
            "ok": True,
            "username": c.username,
            "email": c.email,
            "verified": c.verified,
            "created_at": c.created_at,
        }
    def olvide_password(self, email: str) -> dict:
        email = email.strip().lower()
        with self.repo.lock:
            c = self.repo._email(email)
            if c:
                codigo = f"{secrets.randbelow(10**6):06d}"
                c.reset_code = codigo
                c.reset_expires = (_ahora() + timedelta(minutes=30)).isoformat()
                self.repo.save(c)
                self.mailer.enviar(
                    email,
                    "Recuperar contraseña",
                    f"Tu código para restablecer la contraseña es: {codigo}\nExpira en 30 minutos.",
                )
        return {"ok": True, "msg": "Si el correo existe, recibirás un código."}
    def restablecer_password(self, email: str, codigo: str, nueva: str) -> dict:
        email = email.strip().lower()
        if not self._password_valida(nueva):
            return {"ok": False, "msg": "Contraseña: mínimo 8 caracteres con letras y números"}
        with self.repo.lock:
            c = self.repo._email(email)
            if (not c or not c.reset_code or c.reset_code != codigo or not c.reset_expires
                    or datetime.fromisoformat(c.reset_expires) < _ahora()):
                return {"ok": False, "msg": "Código inválido o expirado"}
            c.password_hash = bcrypt.hashpw(nueva.encode(), bcrypt.gensalt()).decode()
            c.reset_code, c.reset_expires = None, None
            self.repo.save(c)
        return {"ok": True, "msg": "Contraseña actualizada"}


    def verificar(self, email: str, codigo: str) -> dict:
        email = email.strip().lower()
        with self.repo.lock:
            c = self.repo._email(email)
            if (not c or c.verify_code != codigo or not c.verify_expires
                    or datetime.fromisoformat(c.verify_expires) < datetime.utcnow()):
                return {"ok": False, "msg": "Código inválido o expirado"}
            c.verified, c.verify_code, c.verify_expires = True, None, None
            self.repo.save(c)
        return {"ok": True, "msg": "Correo verificado"}

    def login(self, email: str, password: str) -> dict:
        email = email.strip().lower()
        c = self.repo._email(email)
        if not c or not bcrypt.checkpw(password.encode(), c.password_hash.encode()):
            return {"ok": False, "msg": "Credenciales incorrectas"}
        if not c.verified:
            return {"ok": False, "msg": "Debes verificar tu correo primero"}
        return {"ok": True, "msg": "Bienvenido", "email": email}


    @staticmethod
    def _password_valida(p: str) -> bool:
        return len(p) >= 8 and any(c.isdigit() for c in p) and any(c.isalpha() for c in p)