"""Modelo de la configuración de partida (US-08).

CA-08.3  forma de terminar: por tiempo o por puntos.
CA-08.4  minutos de duración, o puntos objetivo.
CA-08.5  segundos de congelamiento con el arma paralizadora.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

MODO_TIEMPO = "tiempo"
MODO_PUNTOS = "puntos"
MODOS = (MODO_TIEMPO, MODO_PUNTOS)

MIN_MINUTOS, MAX_MINUTOS = 1, 60
MIN_PUNTOS, MAX_PUNTOS = 1, 1000
MIN_CONGELAMIENTO, MAX_CONGELAMIENTO = 1, 60


class ConfiguracionInvalida(ValueError):
    """Un valor de la configuración no cumple las reglas."""


class ErrorPersistencia(Exception):
    """No se pudo leer o escribir la configuración en disco."""


def _entero_en_rango(valor, nombre: str, minimo: int, maximo: int) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ConfiguracionInvalida(f"{nombre} debe ser un número entero.")
    if not minimo <= valor <= maximo:
        raise ConfiguracionInvalida(f"{nombre} debe estar entre {minimo} y {maximo}.")
    return valor


@dataclass(frozen=True)
class ConfiguracionPartida:
    modo_fin: str = MODO_TIEMPO
    minutos: int = 3
    puntos_objetivo: int = 500
    segundos_congelamiento: int = 5

    def __post_init__(self) -> None:
        if self.modo_fin not in MODOS:
            raise ConfiguracionInvalida("Elige cómo termina la partida: por tiempo o por puntos.")
        _entero_en_rango(self.minutos, "La duración (minutos)", MIN_MINUTOS, MAX_MINUTOS)
        _entero_en_rango(self.puntos_objetivo, "Los puntos para ganar", MIN_PUNTOS, MAX_PUNTOS)
        _entero_en_rango(
            self.segundos_congelamiento, "El congelamiento (segundos)",
            MIN_CONGELAMIENTO, MAX_CONGELAMIENTO,
        )

    @classmethod
    def desde_dict(cls, datos: dict) -> "ConfiguracionPartida":
        if not isinstance(datos, dict):
            raise ConfiguracionInvalida("Formato de configuración no válido.")
        base = cls()
        return cls(
            modo_fin=datos.get("modo_fin", base.modo_fin),
            minutos=datos.get("minutos", base.minutos),
            puntos_objetivo=datos.get("puntos_objetivo", base.puntos_objetivo),
            segundos_congelamiento=datos.get("segundos_congelamiento", base.segundos_congelamiento),
        )

    def a_dict(self) -> dict:
        return asdict(self)

    def a_mensaje(self) -> dict:
        """Mensaje PROPUESTO para el servidor (falta acordarlo con el Integrante 3)."""
        return {"tipo": "configuracion", **self.a_dict()}
