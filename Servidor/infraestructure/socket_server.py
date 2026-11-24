import re
import secrets
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


def _es_fraccion(valor) -> bool:
    """Posicion relativa dentro del lobby: numero (no bool) entre 0 y 1."""
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and 0.0 <= valor <= 1.0


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
        self.salas = {"DEFAULT": self.partida}
        self.sala_por_cliente = {}
        self._era_activa_salas = {"DEFAULT": False}
        self.siguiente_id = 1 
        self.fin_partida = fin_partida
        self._era_activa = False

    def _generar_codigo_sala(self) -> str:
        for _ in range(20):
            codigo = secrets.token_hex(2).upper()
            if codigo not in self.salas and codigo != "DEFAULT":
                return codigo
        return f"S{int(time.time()) % 10000}"

    def _sala_de(self, id_jugador: int):
        codigo = self.sala_por_cliente.get(id_jugador, "DEFAULT")
        return codigo, self.salas.get(codigo, self.partida)

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
                termino_por_abandono = False
                codigo_sala = "DEFAULT"
                estado_final = None
                with self.lock:
                    codigo_sala, partida_sala = self._sala_de(id_jugador)
                    if id_jugador in self.clientes:
                        del self.clientes[id_jugador]
                    era_activa = partida_sala.activa
                    if id_jugador in partida_sala.jugadores:
                        partida_sala.registrar_desconexion(id_jugador)
                    self.sesiones.pop(id_jugador, None)
                    self.sala_por_cliente.pop(id_jugador, None)
                    if era_activa and not partida_sala.activa:
                        self._era_activa_salas[codigo_sala] = False
                        if codigo_sala == "DEFAULT":
                            self._era_activa = False
                        termino_por_abandono = True
                        estado_final = partida_sala.estado_actual()
                        estado_final["sala"] = codigo_sala

                try:
                    socket_cliente.close()

                except Exception:
                    pass
                print(f"[SERVIDOR] Cliente {id_jugador} desconectado")
                if termino_por_abandono:
                    self._broadcast({"tipo": "fin_partida", "ganador": partida_sala.ganador, "estado_final": estado_final}, codigo_sala=codigo_sala)
                    self._cerrar_partida(codigo_sala)
                self._broadcast_estado(codigo_sala)

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
                codigo_sala, partida_sala = self._sala_de(id_jugador)
                if partida_sala.activa:
                    self._enviar_a(self.clientes.get(id_jugador), {
                        "tipo": "error", "mensaje": "La partida ya esta en curso"})
                    return
                partida_sala.iniciar_cronometro(
                    minutos,
                    puntos=mensaje.get("puntos"),
                    modo=mensaje.get("modo"),
                    congelamiento=_numero_o_none(mensaje.get("congelamiento")),
                    mapa=mensaje.get("mapa"),
                )
            print (f"[SERVIDOR] Partida configurada para {minutos} minutos.")
            self._broadcast_estado(codigo_sala)

        elif tipo == "movimiento":
            x = mensaje.get("x")
            y = mensaje.get("y")
            with self.lock:
                codigo_sala, partida_sala = self._sala_de(id_jugador)
                if id_jugador in partida_sala.jugadores:
                    jugador = partida_sala.jugadores[id_jugador]
                    # Un jugador congelado no puede moverse: el servidor ignora su posicion (CA-21.8)
                    congelado = partida_sala.dinamicas.esta_congelado(id_jugador)
                    if _es_coordenada(x) and _es_coordenada(y) and not congelado:
                        jugador.x = x
                        jugador.y = y
                    # Posicion dentro del lobby (0..1): la envian los clientes mientras esperan para
                    # que todos vean moverse a los demas antes de iniciar la partida
                    sala_x, sala_y = mensaje.get("sala_x"), mensaje.get("sala_y")
                    if _es_fraccion(sala_x) and _es_fraccion(sala_y):
                        jugador.sala_x = float(sala_x)
                        jugador.sala_y = float(sala_y)
                    self._aplicar_datos_cliente(jugador, mensaje)
            self._broadcast_estado(codigo_sala)

        #US-18: el servidor valida la extraccion (zona, estado, partida activa) y la paga por tiempo
        elif tipo == "accion":
            with self.lock:
                codigo_sala, partida_sala = self._sala_de(id_jugador)
                resultado = partida_sala.extraer(id_jugador)
                finalizo = partida_sala.finalizada
            if resultado is None:
                return
            if resultado.ok:
                #avisar a los demas para que vean la extraccion (particulas) sin recargar
                self._broadcast({
                    "tipo": "accion", "jugador": id_jugador, "mensaje": "[EXTRAYENDO]"}, codigo_sala=codigo_sala)
                if resultado.puntos or finalizo:
                    self._broadcast_estado(codigo_sala)
            elif resultado.motivo:
                #solo se le avisa a quien intento extraer, y explicando el motivo (CA-18.5)
                self._enviar_a(self.clientes.get(id_jugador), {
                    "tipo": "rechazo", "jugador": id_jugador, "mensaje": resultado.motivo})
           
        elif tipo == "identificar":
            nombre = str(mensaje.get("nombre", "")).strip()[:20]
            color = mensaje.get("color", "#E63946")
            crear_sala = bool(mensaje.get("crear_sala"))
            codigo_req = str(mensaje.get("sala", "")).strip().upper()[:8]
            error_ingreso = None
            codigo_sala = "DEFAULT"
            with self.lock:
                if crear_sala: #verificar a cual sala se van a unir o si se va a crear una
                    codigo_sala = codigo_req if (codigo_req and codigo_req not in self.salas and codigo_req != "DEFAULT") else self._generar_codigo_sala()
                    nueva = Partida(id_partida=codigo_sala, limite_puntos=self.partida.limite_puntos)
                    nueva.on_fin = self.partida.on_fin
                    self.salas[codigo_sala] = nueva
                    self._era_activa_salas[codigo_sala] = False
                    self.sala_por_cliente[id_jugador] = codigo_sala
                    partida_sala = nueva
                elif codigo_req:
                    if codigo_req not in self.salas:
                        error_ingreso = "Sala no encontrada"
                        partida_sala = None
                    else:
                        codigo_sala = codigo_req
                        self.sala_por_cliente[id_jugador] = codigo_sala
                        partida_sala = self.salas[codigo_sala]
                else:
                    codigo_sala = self.sala_por_cliente.get(id_jugador, "DEFAULT")
                    self.sala_por_cliente[id_jugador] = codigo_sala
                    partida_sala = self.salas.get(codigo_sala, self.partida)

                #agragar jugador a la sala correspondiente o actualizar su nombre si ya estaba conectado
                if partida_sala is not None:
                    if id_jugador not in partida_sala.jugadores:
                        if partida_sala.activa:
                            error_ingreso = "La partida ya esta en curso"
                        elif len(partida_sala.jugadores) >= 4:
                            error_ingreso = "Partida llena"
                        elif partida_sala.nombre_en_uso(nombre, excluir_id=id_jugador):
                            error_ingreso = "Usuario ya conectado en la sala"
                        else:
                            # 1. Crear jugador con su color
                            nuevo_jugador = Jugador(id_jugador=id_jugador, nombre=nombre or f"Jugador{id_jugador}")
                            nuevo_jugador.color = color
                            partida_sala.agregar_jugador(nuevo_jugador)
                    elif nombre:
                        if partida_sala.nombre_en_uso(nombre, excluir_id=id_jugador):
                            error_ingreso = "Usuario ya conectado en la sala"
                        else:
                            # 2. Actualizar jugador existente con su nuevo nombre y color
                            partida_sala.jugadores[id_jugador].nombre = nombre
                            partida_sala.jugadores[id_jugador].color = color
            if error_ingreso:
                self._enviar_a(self.clientes.get(id_jugador), {"tipo": "error", "mensaje": error_ingreso})
            else:
                self._broadcast_estado(codigo_sala)

    #Enviar mensaje a todos los clientes que estén conectados 

    def _aplicar_datos_cliente(self, jugador, mensaje: dict):
        """Color informado por el cliente. Moverse no suma puntos: sin puntaje valido se conserva el actual."""
        color = mensaje.get("color")
        if isinstance(color, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            jugador.color = color

    def _destinos_sala(self, codigo_sala: str) -> list:
        return [
            sock for idj, sock in self.clientes.items()
            if self.sala_por_cliente.get(idj, "DEFAULT") == codigo_sala
        ]

    def _broadcast_estado(self, codigo_sala: str = "DEFAULT"):
        """
        Difunde el estado actual de la sala indicada.
        """
        with self._envio_lock:
            with self.lock:
                partida_sala = self.salas.get(codigo_sala, self.partida)
                estado = partida_sala.estado_actual()
                estado["sala"] = codigo_sala
                datos = (json.dumps(estado) + "\n").encode("utf-8")
                destinos = self._destinos_sala(codigo_sala)
            for socket_cliente in destinos:
                try:
                    socket_cliente.sendall(datos)
                except Exception:
                    pass

    def _broadcast(self, mensaje: dict, codigo_sala: str = "DEFAULT"):
        datos = (json.dumps(mensaje) + "\n").encode("utf-8")
        with self.lock:
            destinos = self._destinos_sala(codigo_sala)
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
                salas_activas = []
                with self.lock:
                    for codigo, partida_sala in list(self.salas.items()):
                        if partida_sala.activa:
                            partida_sala.tick()
                            salas_activas.append(codigo)
                for codigo in salas_activas:
                    self._broadcast_estado(codigo)
            except Exception as e:
                print(f"[SERVIDOR] Error en dinamicas: {e}", flush=True)

    def _reloj_partida(self):
        while True:
            time.sleep(1) # Espera 1 segundo
            with self.lock:
                salas_snapshot = list(self.salas.items())
            for codigo, partida_sala in salas_snapshot:
                if partida_sala.activa:
                    self._era_activa_salas[codigo] = True
                    if codigo == "DEFAULT":
                        self._era_activa = True
                    partida_sala.verificar_tiempo()
                    self._broadcast_estado(codigo)

                if not partida_sala.activa and self._era_activa_salas.get(codigo, False):
                    self._era_activa_salas[codigo] = False
                    if codigo == "DEFAULT":
                        self._era_activa = False

                    with self.lock:
                        estado_final = partida_sala.estado_actual()
                        estado_final["sala"] = codigo
                    print(f"[SERVIDOR] Mensaje de fin de partida enviado a los usuarios ({codigo})")
                    self._broadcast({"tipo": "fin_partida", "ganador": partida_sala.ganador, "estado_final": estado_final}, codigo_sala=codigo)
                    print("[SERVIDOR] ¡Partida finalizada!")

                    self._cerrar_partida(codigo)
                    self._broadcast_estado(codigo)
                
    def _cerrar_partida(self, codigo_sala: str = "DEFAULT"):
        callback = getattr(self, "fin_partida", None)
        if not callback:
            return  # las estadisticas las registra partida.on_fin (ver main_servidor)
        with self.lock:
            partida_sala = self.salas.get(codigo_sala, self.partida)
            duracion_seg = int(time.time() - partida_sala.tiempo_inicio) if partida_sala.tiempo_inicio > 0 else 0
            jugadores = [{"nombre": j.nombre, "puntos": int(j.puntaje)}
                         for j in partida_sala.jugadores.values()]
        try:
            callback(jugadores, duracion_seg)
        except Exception as e:
            print(f"[STATS] Error guardando partida: {e}", flush=True)