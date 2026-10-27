import json, os, threading
from dataclasses import asdict
from Servidor.domain.cuenta import Cuenta


class JsonRepository:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.RLock()
    #convierte a diccionario, si no existe manda {}
    def _load(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        with open(self.path, encoding="utf-8") as f:
            contenido = f.read().strip()
        if not contenido:
            return {}
        return json.loads(contenido)
    #Guarda el diccionario y crea la carpeta en caso de que no exista
    def _save(self, data: dict):
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)
    #Busca correo
    def _email(self, email: str) -> Cuenta | None:
        with self.lock:
            d = self._load().get(email)
        return Cuenta(email=email, **d) if d else None
    #Revisa si ya existe una cuenta con ese nombre
    def user_exists(self, username: str) -> bool:
        with self.lock:
            return any(u["username"].lower() == username.lower()
                       for u in self._load().values())
    
    def save(self, jugador: Cuenta):
        with self.lock:
            data = self._load()
            d = asdict(jugador)
            d.pop("email")           
            data[jugador.email] = d
            self._save(data) 