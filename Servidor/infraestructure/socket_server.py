import socket
import threading
import json
import time
from Servidor.domain.jugador import Jugador
from Servidor.domain.partida import Partida


#Servidor TCP para aceptar clientes y sincronizar su estado

class ServidorJuego:
    def __init__(self, host, port, manejar):
        self.host = host
        self.port = port
        self.manejar = manejar
        self.socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clientes={}
        self.lock = threading.Lock()
        self.partida = Partida(id_partida="partida_1", limite_puntos=50)
        self.siguiente_id = 1 

    #Arrancar Servidor y quedarse escuchando conexiones

    def run(self):
        self.socket_servidor.bind((self.host, self.port))
        self.socket_servidor.listen(2)
        print(f"[SERVIDOR] Escuchando en {self.host}:{self.port}")

        #Agregar hilo para revisar el tiempo en cada segundo que transcurre
        hilo_tiempo = threading.Thread(target=self._reloj_partida)
        hilo_tiempo.daemon = True
        hilo_tiempo.start()

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
            #Asignar id para registrar al jugador

            with self.lock:
                if len(self.clientes) >= 2:
                    mensaje_error = {"tipo": "error", "mensaje": "Partida llena"}
                    datos = (json.dumps(mensaje_error)+"\n").encode("utf-8")
                    try:
                        socket_cliente.sendall(datos)
                    except Exception:
                        pass
                    return 
                
                id_jugador = self.siguiente_id
                self.siguiente_id += 1
                self.clientes[id_jugador] = socket_cliente

                jugador = Jugador(id_jugador=id_jugador, nombre=f"Jugador{id_jugador}")
                self.partida.agregar_jugador(jugador)
                aceptado = True

            #Confirmar la conexión con el cliente 
            
            self._enviar_a(socket_cliente, {"tipo": "bienvenida","id_jugador": id_jugador,})

            #Avisar a todos los clientes el nuevo estado

            self._broadcast(self.partida.estado_actual())

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

                try:
                    socket_cliente.close()

                except Exception:
                    pass
                print(f"[SERVIDOR] Cliente {id_jugador} desconectado")
                self._broadcast(self.partida.estado_actual())

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
            self.partida.iniciar_cronometro(minutos)
            print (f"[SERVIDOR] Partida configurada para {minutos} minutos.")
            self._broadcast(self.partida.estado_actual())

        elif tipo == "movimiento":
            dx = mensaje.get("dx", 0)
            dy = mensaje.get("dy", 0)
            with self.lock:
                self.partida.mover_jugador(id_jugador, dx, dy)
                estado = self.partida.estado_actual()
            self._broadcast(estado)

        #Acción que se debe modificar a una acción física más adelante

        elif tipo == "accion":
            self._broadcast({
                "tipo": "accion",
                "jugador": id_jugador,
                "mensaje": mensaje.get("mensaje", "¡Acción!"),})

	#Manejo de la autentificación

        elif accion:
            with self.lock:
                respuesta = self.manejar(mensaje, {})
            self._enviar_a(self.clientes.get(id_jugador), respuesta)

    #Enviar mensaje a todos los clientes que estén conectados 

    def _broadcast(self, mensaje: dict):
        datos = (json.dumps(mensaje) + "\n").encode("utf-8")
        with self.lock:
            for socket_cliente in list(self.clientes.values()):
                try:
                    socket_cliente.sendall(datos)
                except Exception:
                    pass  

    #Enviar mensajes a clientes específicos 
    def _enviar_a(self, socket_cliente, mensaje: dict):
        datos = (json.dumps(mensaje) + "\n").encode("utf-8")
        try:
            socket_cliente.sendall(datos)
        except Exception:
            pass

    def _reloj_partida(self):
        while True:
            time.sleep(1) # Espera 1 segundo
            if self.partida.activa:
                self.partida.verificar_tiempo()
                # Llamar al broadcast
                self._broadcast(self.partida.estado_actual())