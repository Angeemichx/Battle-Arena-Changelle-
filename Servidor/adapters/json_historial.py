import json, os, threading


class JsonHistorial:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.RLock()

    def _load(self) -> list:
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            txt = f.read().strip()
        return json.loads(txt) if txt else []

    def agregar(self, partida: dict):
        with self.lock:
            datos = self._load()
            datos.append(partida)
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)

    def todas(self) -> list:
        with self.lock:
            return self._load()