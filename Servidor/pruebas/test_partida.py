import pytest
import time
from Servidor.domain.partida import Partida
from Servidor.domain.jugador import Jugador

def test_mover_jugador_suma_punto():
    partida = Partida(id_partida="test_1")
    jugador = Jugador(id_jugador=1, nombre="Test")
    partida.agregar_jugador(jugador)
    partida.iniciar_cronometro(5)
    
    partida.mover_jugador(1, 1, 0)
    assert jugador.puntaje == 1

def test_detectar_empate():
    partida = Partida(id_partida="test_2")
    j1 = Jugador(id_jugador=1, nombre="A")
    j2 = Jugador(id_jugador=2, nombre="B")
    partida.agregar_jugador(j1)
    partida.agregar_jugador(j2)
    partida.iniciar_cronometro(0.01) 
    time.sleep(1)  # Esperamos a que el tiempo se agote     
    
    partida.verificar_tiempo()
    assert partida.en_tiempo_extra == True