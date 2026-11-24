from Servidor.domain.jugador import Jugador
from Servidor.domain.dinamicas import DinamicasPartida
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
        self.on_fin = None 
        self.duracion_total = 0
        self.modo = None  # "tiempo", "puntos" o None (cualquiera de las dos condiciones)
        self.mapa = None  # nombre del escenario elegido por el creador (US-23); None = el de cada cliente
        self.dinamicas = DinamicasPartida()  # guardianes, eventos, congelamiento y extraccion
        self.finalizada = False
        self._desconectados = []

    def nombre_en_uso(self, nombre: str, excluir_id: int | None = None) -> bool:
        """Indica si ya existe otro jugador conectado con el mismo nombre."""
        objetivo = str(nombre or "").strip().lower()
        if not objetivo:
            return False
        for idj, j in self.jugadores.items():
            if excluir_id is not None and idj == excluir_id:
                continue
            if str(j.nombre or "").strip().lower() == objetivo:
                return True
        return False

    #Agregar un jugador solo si hay espacio (pueden haber maximo 4 en partida)
    def agregar_jugador (self, jugador:Jugador):

        if len(self.jugadores) >=4:
                    return False 
        
        self.jugadores[jugador.id_jugador] = jugador
        return True

    def preconfigurar(self, minutos, puntos=None, modo=None, congelamiento=None, mapa=None):
        """Actualiza mapa y parametros desde el Lobby sin activar aun la partida."""
        if self.activa:
            return
        self.tiempo_limite_segundos = minutos * 60
        self.duracion_total = minutos * 60
        if isinstance(puntos, int) and not isinstance(puntos, bool) and puntos > 0:
            self.limite_puntos = puntos
        self.modo = modo if modo in ("tiempo", "puntos") else None
        # El mapa se guarda para que el servidor lo reenvie y todos jueguen en el mismo escenario (US-23)
        self.mapa = mapa.strip() if isinstance(mapa, str) and 0 < len(mapa.strip()) <= 40 else None
        self.finalizada = False

    def iniciar_cronometro(self, minutos, puntos=None, modo=None, congelamiento=None, mapa=None):
        """
        Arranca una partida nueva. `puntos` es la meta, `modo` la forma de terminar
        ("tiempo", "puntos" o None = lo que ocurra primero) y `congelamiento` los segundos
        que dura un congelamiento por guardian. Los puntajes empiezan en cero.
        """
        self.activa = False
        self.preconfigurar(minutos, puntos=puntos, modo=modo, congelamiento=congelamiento, mapa=mapa)
        self.tiempo_inicio = time.time()
        self.ganador = None
        self.en_tiempo_extra = False
        self._desconectados = []
        for j in self.jugadores.values():
            j.puntaje = 0
        self.dinamicas.reiniciar(self.duracion_total, congelamiento)
        self.activa = True
        print (f"[PARTIDA] Iniciada. Tiempo: {minutos} minutos.")

    def mover_jugador (self, id_jugador:int, dx:int, dy:int):
          if not self.activa:
                return
          
          if id_jugador in self.jugadores:
                self.jugadores[id_jugador].mover(dx, dy) #Sprint 3: el jugador puede moverse, pero no suma puntos

    #Procesar la extrancción de energía del reactor y suma los puntos corespondientes
    def extraer_energia(self, id_jugador: int, puntos_ganados: int):
        if not self.activa:
            return False
        
        if id_jugador in self.jugadores:
            self.jugadores[id_jugador].puntaje += puntos_ganados
            print(f"[PARTIDA] Jugador {id_jugador} extrajo energía. Puntos: {self.jugadores[id_jugador].puntaje}")
            self._verificar_ganador() # Verifica si llegó a los puntos necesarios y ganó
            return True
        return False
    
    def extraer(self, id_jugador: int):
        """US-18: valida y paga una extraccion segun las reglas de dinamicas.py."""
        jugador = self.jugadores.get(id_jugador)
        if jugador is None:
            return None
        resultado = self.dinamicas.extraer(jugador, self.activa)
        if resultado.puntos:
            self._verificar_ganador()
        return resultado

    def tick(self):
        """Avanza guardianes y eventos; los bonus de energia tambien pueden dar la victoria."""
        self.dinamicas.tick(self.jugadores, self.activa)
        if self.dinamicas.bonus_pendientes:
            self.dinamicas.bonus_pendientes.clear()
            self._verificar_ganador()

    #Al alcanzar el limite de puntos el jugador gana 
    def _verificar_ganador (self):
        if self.modo == "tiempo":
            return  # en este modo la meta de puntos no termina la partida
        for jugador in self.jugadores.values():
              if jugador.puntaje >= self.limite_puntos:
                    self._declarar_ganador()
                    break

    def verificar_tiempo(self):
        if not self.activa:
            return
            
        if self.modo == "puntos":
            return  # en este modo solo termina al alcanzar la meta
        tiempo_transcurrido = time.time() - self.tiempo_inicio
        if tiempo_transcurrido >= self.tiempo_limite_segundos:
            puntajes = [j.puntaje for j in self.jugadores.values()]
            print(f"[PARTIDA] Tiempo terminado. Puntajes: {puntajes}")

            #Cada vez que haya empate se agrega tiempo extra de 2 minutos hasta que haya un ganador            
            if len(puntajes) >= 2 and puntajes.count(max(puntajes)) >= 2:
                # Hay empate en tiempo normal
                print("[PARTIDA] ¡Empate! Iniciando tiempo extra de 2 minutos.")
                self.en_tiempo_extra = True
                self.tiempo_limite_segundos = 120 # 2 minutos
                self.tiempo_inicio = time.time()  # Reiniciamos el reloj
                self.activa = True                # Aseguramos que siga activa
            else:
                # No hay empate, hay un ganador claro
                self._declarar_ganador()

    def registrar_desconexion(self, id_jugador: int):
        """Remueve al jugador; si habia partida activa y quedan < 2, finaliza por abandono."""
        jugador = self.jugadores.pop(id_jugador, None)
        if jugador is not None and self.activa:
            self._desconectados.append({"nombre": jugador.nombre, "puntos": int(jugador.puntaje)})
            if len(self.jugadores) < 2:
                self.finalizar_por_abandono()

    def finalizar_por_abandono(self):
        """Finaliza la partida cuando quedan menos de 2 jugadores conectados."""
        if not self.activa:
            return
        if len(self.jugadores) == 1:
            self._declarar_ganador()
            return
        self.activa = False
        self.finalizada = True
        self.dinamicas.tick(self.jugadores, False)
        if self._desconectados and self.on_fin:
            try:
                self.on_fin(list(self._desconectados), int(time.time() - self.tiempo_inicio))
            except Exception as e:
                print(f"[STATS] Error guardando partida: {e}", flush=True)

    def _declarar_ganador(self):
        if not self.activa:
             return
        self.activa = False
        self.finalizada = True
        self.dinamicas.tick(self.jugadores, False)  # CA-22.8: ningun evento sigue tras el final
        if not self.jugadores:
            return
            
        # Ordenar por puntaje si hay empate, tomará al primero de la lista *Cambiar para sprint 3
        jugadores_ordenados = sorted(self.jugadores.values(), key=lambda j: j.puntaje, reverse=True)
        self.ganador = jugadores_ordenados[0].id_jugador
        print(f"[PARTIDA] Fin del juego. Ganador: Jugador {self.ganador}")
        if self.on_fin:
            try:
                registro = [{"nombre": j.nombre, "puntos": int(j.puntaje)} for j in jugadores_ordenados]
                registro.extend(self._desconectados)
                self.on_fin(registro, int(time.time() - self.tiempo_inicio))
            except Exception as e:
                print(f"[STATS] Error guardando partida: {e}", flush=True)

    #devolver el estado de la partida como un diccionario para enviarlo por red para los demas clientes
    def estado_actual(self):
          tiempo_restante = 0
          if self.activa:
                tiempo_transcurrido = time.time() - self.tiempo_inicio
                tiempo_restante = max(0, int(self.tiempo_limite_segundos - tiempo_transcurrido))

          jugadores = []
          for j in self.jugadores.values():
                datos = j.to_dict()
                restante = self.dinamicas.congelados.get(j.id_jugador, 0.0)
                datos["congelado"] = restante > 0
                datos["congelado_restante"] = round(max(0.0, restante), 1)
                jugadores.append(datos)

          estado = {"tipo":"estado", 
                  "jugadores": jugadores, 
                  "activa":self.activa,
                  "ganador":self.ganador, 
                  "ganador_id": self.ganador,
                  "partida_finalizada": self.finalizada,
                  "puntos_meta": self.limite_puntos,
                  "modo": self.modo,
                  "tiempo_restante": tiempo_restante, 
                  "tiempo_extra": self.en_tiempo_extra}
          if self.mapa:
                estado["mapa"] = self.mapa
          estado.update(self.dinamicas.estado_publico())
          return estado
    
