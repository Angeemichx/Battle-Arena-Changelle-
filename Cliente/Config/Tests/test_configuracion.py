"""Pruebas de US-08: modelo y persistencia (sin ventana)."""
import json

import pytest

from Cliente.Config.config_repository import JsonConfiguracionRepository
from Cliente.Config.configuracion import (
    MODO_PUNTOS, MODO_TIEMPO, ConfiguracionInvalida, ConfiguracionPartida, ErrorPersistencia,
)


# ---------- modelo: positivas ----------
def test_valores_por_defecto_son_validos():
    c = ConfiguracionPartida()
    assert (c.modo_fin, c.minutos, c.puntos_objetivo, c.segundos_congelamiento) == (MODO_TIEMPO, 3, 500, 5)


@pytest.mark.parametrize("modo", [MODO_TIEMPO, MODO_PUNTOS])
def test_acepta_los_dos_modos_de_fin(modo):
    assert ConfiguracionPartida(modo_fin=modo).modo_fin == modo


def test_ida_y_vuelta_dict():
    c = ConfiguracionPartida(MODO_PUNTOS, 10, 120, 8)
    assert ConfiguracionPartida.desde_dict(c.a_dict()) == c


def test_mensaje_para_el_servidor():
    m = ConfiguracionPartida().a_mensaje()
    assert m["tipo"] == "configuracion" and m["segundos_congelamiento"] == 5


# ---------- modelo: negativas ----------
@pytest.mark.parametrize("campo,valor", [
    ("minutos", 0), ("minutos", 61), ("puntos_objetivo", 0), ("puntos_objetivo", 1001),
    ("segundos_congelamiento", 0), ("segundos_congelamiento", 61),
    ("minutos", -3), ("minutos", "5"), ("minutos", 2.5), ("minutos", True),
])
def test_rechaza_valores_fuera_de_rango_o_tipo(campo, valor):
    with pytest.raises(ConfiguracionInvalida):
        ConfiguracionPartida(**{campo: valor})


def test_rechaza_modo_desconocido():
    with pytest.raises(ConfiguracionInvalida):
        ConfiguracionPartida(modo_fin="infinito")


def test_desde_dict_rechaza_basura():
    with pytest.raises(ConfiguracionInvalida):
        ConfiguracionPartida.desde_dict(["no", "es", "dict"])


# ---------- persistencia ----------
def test_sin_archivo_devuelve_valores_por_defecto(tmp_path):
    assert JsonConfiguracionRepository(tmp_path / "x.json").cargar() == ConfiguracionPartida()


def test_guarda_y_recupera_la_ultima_configuracion(tmp_path):
    repo = JsonConfiguracionRepository(tmp_path / "sub" / "c.json")
    c = ConfiguracionPartida(MODO_PUNTOS, 7, 99, 12)
    repo.guardar(c)
    assert JsonConfiguracionRepository(tmp_path / "sub" / "c.json").cargar() == c  # otra "sesión"


@pytest.mark.parametrize("contenido", ["{no es json", '{"minutos": 999}', "[]", ""])
def test_archivo_danado_no_rompe_y_vuelve_a_defaults(tmp_path, contenido):
    ruta = tmp_path / "c.json"
    ruta.write_text(contenido, encoding="utf-8")
    assert JsonConfiguracionRepository(ruta).cargar() == ConfiguracionPartida()


def test_error_de_escritura_se_reporta(tmp_path):
    bloqueo = tmp_path / "archivo"
    bloqueo.write_text("x")                      # un archivo donde debería haber carpeta
    with pytest.raises(ErrorPersistencia):
        JsonConfiguracionRepository(bloqueo / "c.json").guardar(ConfiguracionPartida())
