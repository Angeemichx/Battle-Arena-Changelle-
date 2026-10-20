import re
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE))

from Servidor.adapters.json_repository import JsonRepository
from Servidor.use_cases.auth_service import AuthService


class MailerFalso:
    def __init__(self): self.ultimo = ""
    def enviar(self, destino, asunto, cuerpo): self.ultimo = cuerpo
    def codigo(self): return re.search(r"\d{6}", self.ultimo).group()


def nuevo_auth():
    ruta = Path(tempfile.mkdtemp()) / "usuarios.json"
    mailer = MailerFalso()
    return AuthService(JsonRepository(str(ruta)), mailer), mailer


def test_registro_y_duplicado():
    auth, _ = nuevo_auth()
    assert auth.registrar("a@correo.com", "ana", "clave1234")["ok"]
    assert not auth.registrar("a@correo.com", "otra", "clave1234")["ok"]


def test_validaciones():
    auth, _ = nuevo_auth()
    assert not auth.registrar("mal-correo", "x", "clave1234")["ok"]
    assert not auth.registrar("b@correo.com", "bob", "corta")["ok"]


def test_registro_no_devuelve_codigo():
    auth, _ = nuevo_auth()
    assert "codigo" not in auth.registrar("a@correo.com", "ana", "clave1234")


def test_login_bloquea_no_verificados():
    auth, _ = nuevo_auth()
    auth.registrar("a@correo.com", "ana", "clave1234")
    assert not auth.login("a@correo.com", "clave1234")["ok"]


def test_verificar_y_login():
    auth, mailer = nuevo_auth()
    auth.registrar("c@correo.com", "carla", "clave1234")
    assert not auth.verificar("c@correo.com", "000000")["ok"]
    assert auth.verificar("c@correo.com", mailer.codigo())["ok"]
    assert auth.login("c@correo.com", "clave1234")["ok"]
    assert not auth.login("c@correo.com", "incorrecta1")["ok"]


def test_perfil_y_recuperacion():
    auth, mailer = nuevo_auth()
    auth.registrar("c@correo.com", "carla", "clave1234")
    auth.verificar("c@correo.com", mailer.codigo())
    assert auth.perfil("c@correo.com")["verified"]
    auth.olvide_password("c@correo.com")
    cod = mailer.codigo()
    assert not auth.restablecer_password("c@correo.com", "000000", "nueva1234")["ok"]
    assert auth.restablecer_password("c@correo.com", cod, "nueva1234")["ok"]
    assert not auth.login("c@correo.com", "clave1234")["ok"]
    assert auth.login("c@correo.com", "nueva1234")["ok"]