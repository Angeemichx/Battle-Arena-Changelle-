"""Persistencia de la última configuración usada (CA-08.1)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from Cliente.Config.configuracion import (
    ConfiguracionInvalida, ConfiguracionPartida, ErrorPersistencia,
)

RUTA_POR_DEFECTO = Path(__file__).resolve().parent.parent / "Recursos" / "ultima_configuracion.json"


class JsonConfiguracionRepository:
    def __init__(self, ruta: Path | str = RUTA_POR_DEFECTO):
        self._ruta = Path(ruta)

    def cargar(self) -> ConfiguracionPartida:
        """Última configuración guardada; si no hay o está dañada, la de por defecto."""
        try:
            with open(self._ruta, "r", encoding="utf-8") as f:
                return ConfiguracionPartida.desde_dict(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError, ConfiguracionInvalida, UnicodeDecodeError):
            return ConfiguracionPartida()
        except OSError as e:
            raise ErrorPersistencia(f"No se pudo leer la configuración: {e}") from e

    def guardar(self, config: ConfiguracionPartida) -> None:
        tmp = self._ruta.with_suffix(".tmp")
        try:
            self._ruta.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(config.a_dict(), f, indent=2)
            os.replace(tmp, self._ruta)  # escritura atómica: nunca queda un archivo a medias
        except OSError as e:
            raise ErrorPersistencia(f"No se pudo guardar la configuración: {e}") from e
