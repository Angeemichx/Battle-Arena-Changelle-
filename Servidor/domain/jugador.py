#Se crea la clase jugador para representar a cada jugador que se encuentra dentro de la partida

class Jugador:
    def __init__(self, id_jugador: int, nombre:str, x: int=0, y: int = 0, color: str | None = None):
        self.id_jugador = id_jugador 
        self.nombre = nombre 
        self.x = x
        self.y = y
        self.puntaje = 0 
        self.color = color  # color hexadecimal del avatar (opcional, lo informa el cliente)
        self.sala_x = None  # posicion relativa (0..1) dentro del lobby, solo mientras se espera
        self.sala_y = None

    #Movimiento del jugador sumando dy y dx, ademas restricciones de limites de la arena 

    def mover(self, dx:int, dy:int, limite: int=800):
        nueva_x = self.x + dx
        nueva_y = self.y + dy

        #Para que no se salga de la arena:

        if 0<= nueva_x <= limite:
            self.x = nueva_x

        if 0<= nueva_y <= limite:
            self.y = nueva_y

    #convertir el jugador en un diccionario para poder enviarlo como JSON
    def to_dict(self):
        datos = {"id": self.id_jugador,
                "nombre": self.nombre,
                "x": self.x,
                "y": self.y,
                "puntaje": self.puntaje,
                "color": self.color}
        if self.sala_x is not None and self.sala_y is not None:
            datos["sala_x"] = self.sala_x
            datos["sala_y"] = self.sala_y
        return datos

