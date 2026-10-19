from Servidor.domain.jugador import Jugador
import time

#Creacion de la clase para definir los metodos de las partidas como jugadores y estado

class Partida:
    def __init__(self, id_partida: str, limite_puntos: int=50):
        self.id_partida= id_partida
        self.limite_puntos = limite_puntos
        self.jugadores = {}
        self.activa = False
        self.ganador = None  
        self.tiempo_limite_segundos = 0
        self.tiempo_inicio = 0
        self.en_tiempo_extra = False

    #Agregar un jugador solo si hay espacio (pueden haber maximo 2 en partida)
    def agregar_jugador (self, jugador:Jugador):

        if len(self.jugadores) >=2:
                    return False 
        
        self.jugadores[jugador.id_jugador] = jugador
        return True

    def iniciar_cronometro(self, minutos):
        self.tiempo_limite_segundos = minutos * 60
        self.tiempo_inicio = time.time()
        self.activa = True
        print (f"[PARTIDA] Iniciada. Tiempo: {minutos} minutos.")

    def mover_jugador (self, id_jugador:int, dx:int, dy:int):
          if not self.activa:
                return
          
          if id_jugador in self.jugadores:
                self.jugadores[id_jugador].mover(dx, dy)
                self.jugadores [id_jugador].sumar_punto()
                self._verificar_ganador()

    #Al alcanzar el limite de puntos el jugador gana 
    def _verificar_ganador (self):
        for jugador in self.jugadores.values():
              if jugador.puntaje >= self.limite_puntos:
                    self._declarar_ganador()
                    break

    def verificar_tiempo(self):
        if not self.activa:
            return
            
        tiempo_transcurrido = time.time() - self.tiempo_inicio
        if tiempo_transcurrido >= self.tiempo_limite_segundos:
            puntajes = [j.puntaje for j in self.jugadores.values()]
            print(f"[PARTIDA] Tiempo terminado. Puntajes: {puntajes}")

            #Cada vez que haya empate se agrega tiempo extra de 2 minutos hasta que haya un ganador            
            if len(puntajes) >= 2 and puntajes[0] == puntajes[1]:
                # Hay empate en tiempo normal
                print("[PARTIDA] ¡Empate! Iniciando tiempo extra de 2 minutos.")
                self.en_tiempo_extra = True
                self.tiempo_limite_segundos = 120 # 2 minutos
                self.tiempo_inicio = time.time()  # Reiniciamos el reloj
                self.activa = True                # Aseguramos que siga activa
            else:
                # No hay empate, hay un ganador claro
                self._declarar_ganador()

    def _declarar_ganador(self):
        self.activa = False
        if not self.jugadores:
            return
            
        # Ordenar por puntaje si hay empate, tomará al primero de la lista *Cambiar para sprint 3
        jugadores_ordenados = sorted(self.jugadores.values(), key=lambda j: j.puntaje, reverse=True)
        self.ganador = jugadores_ordenados[0].id_jugador
        print(f"[PARTIDA] Fin del juego. Ganador: Jugador {self.ganador}")

    #devolver el estado de la partida como un diccionario para enviarlo por red para los demas clientes
    def estado_actual(self):
          tiempo_restante = 0
          if self.activa:
                tiempo_transcurrido = time.time() - self.tiempo_inicio
                tiempo_restante = max(0, int(self.tiempo_limite_segundos - tiempo_transcurrido))

          return {"tipo":"estado", 
                  "jugadores":[j.to_dict() for j in self.jugadores.values()], 
                  "activa":self.activa,
                  "ganador":self.ganador, 
                  "tiempo_restante": tiempo_restante, 
                  "tiempo_extra": self.en_tiempo_extra}
    
