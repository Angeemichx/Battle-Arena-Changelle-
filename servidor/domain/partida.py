from domain.jugador import Jugador 

#Creacion de la clase para definir los metodos de las partidas como jugadores y estado

class Partida:
    def __init__(self, id_partida: str, limite_puntos: int=50):
        self.id_partida= id_partida
        self.limite_puntos = limite_puntos
        self.jugadores = {}
        self.activa: True
        self.ganador: None 

    #Agregar un jugador solo si hay espacio (pueden haber maximo 2 en partida)
    def agregar_jugador (self, jugador:Jugador):

        if len(self.jugadores) >=2:
                    return False 
        
        self.jugadores[jugador.id_jugador] = jugador
        return True

    def mover_jugador (self, id_jugador:int, dx:int, dy:int):
          if id_jugador in self.jugadores:
                self.jugadores[id_jugador].mover(dx, dy)
                self.jugadores [id_jugador].sumar_punto()
                self._verificar_ganador()

    #Al alcanzar el limite de puntos el jugador gana 
    def _verificar_ganador (self):
        for jugador in self.jugadores.values():
              if jugador.puntaje >= self.limite_puntos:
                    self.activa = False 
                    self.ganador = jugador.id_jugador
                    break

    #devolver el estado de la partida como un diccionario para enviarlo por red para los demas clientes
    def estado_actual(self):
          return {"tipo":"estado", 
                  "jugadores":[j.to_dict() for j in self.jugadores.values()], 
                  "activa":self.activa,
                  "ganador":self.ganador}
    