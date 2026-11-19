import re
import socket
import threading
import json
import time
from Servidor.domain.jugador import Jugador
from Servidor.domain.partida import Partida


def _numero_o_none(valor):
    """Numero valido (no bool) o None."""
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return valor
    return None


def _es_coordenada(valor) -> bool:
    """Coordenada valida: entero (no bool) dentro del mundo de juego."""
    return isinstance(valor, int) and not isinstance(valor, bool) and -10000 <= valor <= 10000


#Servidor TCP para aceptar clientes y sincronizar su estado

class ServidorJuego:
    def __init__(self, host, port, manejar, fin_partida=None):
        self.host = host
        self.port = port
        self.manejar = manejar
        self.socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clientes={}
        self.sesiones = {}
        self.lock = threading.Lock()
        # Serializa los envios: dos hilos escribiendo en el mismo socket pueden mezclar mensajes
        self._envio_lock = threading.Lock()
        self.partida = Partida(id_partida="partida_1", limite_puntos=50)
        self.siguiente_id = 1 
        self.fin_partida = fin_partida
        self._era_activa = False

    #Arrancar Servidor y quedarse escuchando conexiones

    def run(self):
        self.socket_servidor.bind((self.host, self.port))
        self.socket_servidor.listen(10)
        print(f"[SERVIDOR] Escuchando en {self.host}:{self.port}")

        #Agregar hilo para revisar el tiempo en cada segundo que transcurre
        hilo_tiempo = threading.Thread(target=self._reloj_partida)
        hilo_tiempo.daemon = True
        hilo_tiempo.start()

        #Hilo de dinamicas: mueve guardianes y eventos varias veces por segundo
        hilo_dinamicas = threading.Thread(target=self._bucle_dinamicas)
        hilo_dinamicas.daemon = True
        hilo_dinamicas.start()

        while True:
            socket_cliente, direccion = self.socket_servidor.accept()
            print(f"[SERVIDOR] Nueva conexión desde {direccion}")

            hilo = threading.Thread(target=self._manejar_cliente, args=(socket_cliente,))
            hilo.daemon = True
            hilo.start()

    #Atender a los clientes en su hilo

    def _manejar_cliente(self, socket_cliente):
        id_jugador = None
        buffer = ""
        aceptado = False
        try:
            # Sin retardo de Nagle: los mensajes de movimiento son pequenos y frecuentes
            socket_cliente.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass

        try:
            #Asignar id para registrar al jugador
            with self.lock:
                id_jugador = self.siguiente_id
                self.siguiente_id += 1
                self.clientes[id_jugador] = socket_cliente
                aceptado = True

            #Confirmar la conexión con el cliente 
            
            self._enviar_a(socket_cliente, {"tipo": "bienvenida","id_jugador": id_jugador,})

            #Avisar a todos los clientes el nuevo estado

            self._broadcast_estado()

            #Escuchar mensajes de este cliente

            while True:
                datos = socket_cliente.recv(4096)
                if not datos:
                    break

                buffer += datos.decode("utf-8")

                #Separar mensajes por saltos de línea 
                while "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    if linea.strip():
                        print(f"[SERVIDOR] socket_server, mensaje recibido de {id_jugador}: {linea}")
                        self._procesar_mensaje(id_jugador, linea)

        except ConnectionResetError:
            print(f"[SERVIDOR] Cliente {id_jugador} desconectado abruptamente")
        except Exception as e:
            print(f"[SERVIDOR] Error con cliente {id_jugador}: {e}")
        finally:
            if aceptado:
                with self.lock:
                    if id_jugador in self.clientes:
                        del self.clientes[id_jugador]
                    if id_jugador in self.partida.jugadores:
                        del self.partida.jugadores[id_jugador]
                    self.sesiones.pop(id_jugador, None)

                try:
                    socket_cliente.close()

                except Exception:
                    pass
                print(f"[SERVIDOR] Cliente {id_jugador} desconectado")
                self._broadcast_estado()

            else: 
                try:
                    socket_cliente.close()

                except Exception:
                    pass

    #Procesar mensaje JSON que se reciba de un cliente

    def _procesar_mensaje(self, id_jugador, linea):
        try:
            mensaje = json.loads(linea)
        except json.JSONDecodeError:
            print(f"[SERVIDOR] Mensaje inválido de {id_jugador}: {linea}")
            return

        tipo = mensaje.get("tipo")
        accion = mensaje.get("action")

        if tipo == "configurar_partida":
            minutos = mensaje.get("minutos", 5)
            if not isinstance(minutos, (int, float)) or isinstance(minutos, bool) or not 0 < minutos <= 120:
                minutos = 5
            with self.lock:
                self.partida.iniciar_cronometro(
                    minutos,
                    puntos=mensaje.get("puntos"),
                    modo=mensaje.get("modo"),
                    congelamiento=_numero_o_none(mensaje.get("congelamiento")),
                )
            print (f"[SERVIDOR] Partida configurada para {minutos} minutos.")
            self._broadcast_estado()

        elif tipo == "movimiento":
            x = mensaje.get("x", 0)
            y = mensaje.get("y", 0)
            with self.lock:
                if id_jugador in self.partida.jugadores:
                    jugador = self.partida.jugadores[id_jugador]
                    # Un jugador congelado no puede moverse: el servidor ignora su posicion (CA-21.8)
                    congelado = self.partida.dinamicas.esta_congelado(id_jugador)
                    if _es_coordenada(x) and _es_coordenada(y) and not congelado:
                        jugador.x = x
                        jugador.y = y
                    self._aplicar_datos_cliente(jugador, mensaje)
            self._broadcast_estado()

        #US-18: el servidor valida la extraccion (zona, estado, partida activa) y la paga por tiempo
        elif tipo == "accion":
            with self.lock:
                resultado = self.partida.extraer(id_jugador)
                finalizo = self.partida.finalizada
            if resultado is None:
                return
            if resultado.ok:
                #avisar a los demas para que vean la extraccion (particulas) sin recargar
                self._broadcast({
                    "tipo": "accion", "jugador": id_jugador, "mensaje": "[EXTRAYENDO]"})
                if resultado.puntos or finalizo:
                    self._broadcast_estado()
            elif resultado.motivo:
                #solo se le avisa a quien intento extraer, y explicando el motivo (CA-18.5)
                self._enviar_a(self.clientes.get(id_jugador), {
                    "tipo": "rechazo", "jugador": id_jugador, "mensaje": resultado.motivo})
           
        elif tipo == "identificar":
            nombre = str(mensaje.get("nombre", "")).strip()[:20]
            lleno = False
            with self.lock:
                if id_jugador not in self.partida.jugadores:
                    if len(self.partida.jugadores) >= 4:
                        lleno = True
                    else:
                        self.partida.agregar_jugador(
                            Jugador(id_jugador=id_jugador, nombre=nombre or f"Jugador{id_jugador}")
                        )
                elif nombre:
                    self.partida.jugadores[id_jugador].nombre = nombre
            if lleno:
                self._enviar_a(self.clientes.get(id_jugador), {"tipo": "error", "mensaje": "Partida llena"})
            else:
                self._broadcast_estado()


        # Manejo de peticiones de cuentas (registro, verificacion, login, etc.)
        elif accion:
            sesion = self.sesiones.setdefault(id_jugador, {})
            with self.lock:
                respuesta = self.manejar(mensaje, sesion)
            self._enviar_a(self.clientes.get(id_jugador), respuesta)

        # Manejo de peticiones de cuentas (registro, verificacion, login, etc.)
        elif accion:
            sesion = self.sesiones.setdefault(id_jugador, {})
            with self.lock:
                respuesta = self.manejar(mensaje, sesion)
            self._enviar_a(self.clientes.get(id_jugador), respuesta)

    #Enviar mensaje a todos los clientes que estén conectados 

    def _aplicar_datos_cliente(self, jugador, mensaje: dict):
        """Color informado por el cliente. Moverse no suma puntos: sin puntaje valido se conserva el actual."""
        color = mensaje.get("color")
        if isinstance(color, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            jugador.color = color

    def _broadcast_estado(self):
        """
        Difunde el estado actual. La foto del estado y su envio ocurren en el mismo bloque:
        si se tomara la foto fuera de el, un estado viejo podia llegar DESPUES de uno nuevo
        (dos jugadores moviendose a la vez) y los clientes se quedaban con la posicion vieja.
        """
        with self._envio_lock:
            with self.lock:
                datos = (json.dumps(self.partida.estado_actual()) + "\n").encode("utf-8")
                destinos = list(self.clientes.values())
            for socket_cliente in destinos:
                try:
                    socket_cliente.sendall(datos)
                except Exception:
                    pass

    def _broadcast(self, mensaje: dict):
        datos = (json.dumps(mensaje) + "\n").encode("utf-8")
        with self.lock:
            destinos = list(self.clientes.values())
        with self._envio_lock:
            for socket_cliente in destinos:
                try:
                    socket_cliente.sendall(datos)
                except Exception:
                    pass  

    #Enviar mensajes a clientes específicos 
    def _enviar_a(self, socket_cliente, mensaje: dict):
        datos = (json.dumps(mensaje) + "\n").encode("utf-8")
        try:
            with self._envio_lock:
                socket_cliente.sendall(datos)
        except Exception:
            pass

    def _bucle_dinamicas(self):
        """Avanza guardianes y eventos (~15 veces por segundo) y difunde el estado mientras hay partida."""
        while True:
            time.sleep(1 / 15)
            try:
                with self.lock:
                    activa = self.partida.activa
                    if activa:
                        self.partida.tick()
                if activa:
                    self._broadcast_estado()
            except Exception as e:
                print(f"[SERVIDOR] Error en dinamicas: {e}", flush=True)

    def _reloj_partida(self):
        while True:
            time.sleep(1) # Espera 1 segundo
            if self.partida.activa:
                self._era_activa = True
                self.partida.verificar_tiempo()

                if not self.partida.activa and self._era_activa:
                    self._era_activa = False

                    #US-25 Mensaje de fin de partida a los clientes
                    with self.lock:
                        estado_final = self.partida.estado_actual()
                    print(f"[SERVIDOR] Mensaje de fin de partida enviado a los usuarios")#para prueba 4
                    self._broadcast({"tipo": "fin_partida", "ganador": self.partida.ganador, "estado_final": estado_final})
                    print("[SERVIDOR] ¡Partida finalizada!")

                    #función de cierre para guardar estadísticas de la partida
                    self._cerrar_partida()

                # Llamar al broadcast
                self._broadcast_estado()
                
    def _cerrar_partida(self):
        callback = getattr(self, "fin_partida", None)
        if not callback:
            return  # las estadisticas las registra partida.on_fin (ver main_servidor)
        with self.lock:
            #Calcular la duración restando el tiempo de inicio al actual
            duracion_seg = int(time.time() - self.partida.tiempo_inicio) if self.partida.tiempo_inicio > 0 else 0
            jugadores = [{"nombre": j.nombre, "puntos": int(j.puntaje)}
                         for j in self.partida.jugadores.values()]
        try:
            callback(jugadores, duracion_seg)
        except Exception as e:
            print(f"[STATS] Error guardando partida: {e}", flush=True)