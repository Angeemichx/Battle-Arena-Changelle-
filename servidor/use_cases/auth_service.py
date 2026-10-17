import re
import secrets
import bcrypt
from datetime import datetime, timedelta

from servidor.domain.cuenta import Cuenta

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

        # evita que dos registros iguales se crucen
        with self.repo.lock:
            if self.repo.get_by_email(email) or self.repo.username_exists(username):
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

    @staticmethod
    def _password_valida(p: str) -> bool:
        return len(p) >= 8 and any(c.isdigit() for c in p) and any(c.isalpha() for c in p)