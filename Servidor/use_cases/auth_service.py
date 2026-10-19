import re
import secrets
import bcrypt
from datetime import datetime, timedelta

from Servidor.domain.cuenta import Cuenta

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthService:
    def __init__(self, repo):
        self.repo = repo

    def registrar(self, email: str, username: str, password: str) -> dict:
        email = email.strip().lower()
        username = username.strip()

        if not EMAIL_RE.match(email):
            return {"ok": False, "msg": "Correo inválido"}
        if not self._password_valida(password):
            return {"ok": False, "msg": "Contraseña: mínimo 8 caracteres con letras y números"}
        if not username:
            return {"ok": False, "msg": "Usuario requerido"}

        with self.repo.lock:
            if self.repo._email(email) or self.repo.user_exists(username):
                return {"ok": False, "msg": "Correo o usuario ya registrado"}

            codigo = f"{secrets.randbelow(10**6):06d}"
            cuenta = Cuenta(
                email=email,
                username=username,
                password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
                verify_code=codigo,
                verify_expires=(datetime.utcnow() + timedelta(minutes=15)).isoformat(),
                created_at=datetime.utcnow().isoformat(),
            )
            self.repo.save(cuenta)

        return {"ok": True, "msg": "Cuenta creada", "codigo": codigo}

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