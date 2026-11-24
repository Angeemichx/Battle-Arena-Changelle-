"""Pruebas de ranking, historial y sitio movil (US-27, US-28, US-30)."""
import json

import pytest

from Servidor.adapters.json_historial import JsonHistorial
from Servidor.use_cases.estadisticas import Estadisticas


@pytest.fixture
def stats(tmp_path):
    return Estadisticas(JsonHistorial(str(tmp_path / "historial.json")))


def test_el_ranking_ordena_por_victorias_y_luego_por_puntos(stats):
    stats.registrar_partida([{"nombre": "Ana", "puntos": 300}, {"nombre": "Luis", "puntos": 100}], 120)
    stats.registrar_partida([{"nombre": "Ana", "puntos": 50}, {"nombre": "Luis", "puntos": 400}], 90)
    stats.registrar_partida([{"nombre": "Ana", "puntos": 500}, {"nombre": "Luis", "puntos": 10}], 60)
    r = stats.ranking()
    assert [j["nombre"] for j in r] == ["Ana", "Luis"]
    assert r[0] == {"nombre": "Ana", "partidas": 3, "victorias": 2, "puntos": 850}
    assert r[1]["victorias"] == 1


def test_el_desempate_del_ranking_es_por_puntos(stats):
    stats.registrar_partida([{"nombre": "Ana", "puntos": 100}, {"nombre": "Luis", "puntos": 50}], 60)
    stats.registrar_partida([{"nombre": "Luis", "puntos": 500}, {"nombre": "Ana", "puntos": 10}], 60)
    assert [j["nombre"] for j in stats.ranking()] == ["Luis", "Ana"]


def test_un_empate_no_da_victoria_a_nadie(stats):
    stats.registrar_partida([{"nombre": "Ana", "puntos": 200}, {"nombre": "Luis", "puntos": 200}], 60)
    assert all(j["victorias"] == 0 for j in stats.ranking())
    assert stats.historial("Ana")[0]["resultado"] == "empate"


def test_el_ranking_respeta_el_limite(stats):
    for i in range(12):
        stats.registrar_partida([{"nombre": f"J{i}", "puntos": i}], 30)
    assert len(stats.ranking(limite=10)) == 10


def test_el_historial_de_un_usuario(stats):
    stats.registrar_partida([{"nombre": "Ana", "puntos": 300}, {"nombre": "Luis", "puntos": 100}], 120)
    stats.registrar_partida([{"nombre": "Ana", "puntos": 20}, {"nombre": "Luis", "puntos": 90}], 45)
    h = stats.historial("ana")                      # no distingue mayusculas
    assert [p["resultado"] for p in h] == ["derrota", "victoria"]   # la mas reciente primero
    assert h[1]["puntos"] == 300 and h[1]["rivales"] == ["Luis"] and h[1]["duracion"] == 120
    assert stats.historial("nadie") == []


def test_cada_partida_se_guarda_una_sola_vez_y_persiste(tmp_path):
    ruta = str(tmp_path / "historial.json")
    Estadisticas(JsonHistorial(ruta)).registrar_partida([{"nombre": "Ana", "puntos": 1}], 10)
    otra = Estadisticas(JsonHistorial(ruta))        # "reinicio" del servidor: relee el archivo
    assert len(otra.repo.todas()) == 1
    assert otra.repo.todas()[0]["ganador"] == "Ana"


def test_sin_jugadores_no_se_guarda_nada(stats):
    stats.registrar_partida([], 10)
    assert stats.repo.todas() == []


def test_sitio_movil_muestra_ranking_y_puntos(tmp_path, monkeypatch):
    ruta = tmp_path / "historial.json"
    est = Estadisticas(JsonHistorial(str(ruta)))
    est.registrar_partida([{"nombre": "Ana", "puntos": 300}, {"nombre": "Luis", "puntos": 100}], 120)
    pytest.importorskip("flask")
    import app_movil
    monkeypatch.setattr(app_movil, "RUTA_HISTORIAL", str(ruta))
    cliente = app_movil.app.test_client()
    html = cliente.get("/").get_data(as_text=True)
    assert "width=device-width" in html                       # adaptable a movil (CA-30.2)
    assert "Ana" in html and "300" in html                    # ranking y puntos visibles (CA-30.4)
    assert "Ana" in cliente.get("/?usuario=Ana").get_data(as_text=True)
    assert "No hay partidas" in cliente.get("/?usuario=Zoe").get_data(as_text=True)


def test_sitio_movil_sin_archivo_no_falla(tmp_path, monkeypatch):
    pytest.importorskip("flask")
    import app_movil
    monkeypatch.setattr(app_movil, "RUTA_HISTORIAL", str(tmp_path / "no_existe.json"))
    r = app_movil.app.test_client().get("/")
    assert r.status_code == 200 and "Aun no hay partidas" in r.get_data(as_text=True)


def test_sitio_movil_con_archivo_danado_no_falla(tmp_path, monkeypatch):
    pytest.importorskip("flask")
    import app_movil
    malo = tmp_path / "historial.json"
    malo.write_text("{ esto no es json", encoding="utf-8")
    monkeypatch.setattr(app_movil, "RUTA_HISTORIAL", str(malo))
    assert app_movil.app.test_client().get("/").status_code == 200
