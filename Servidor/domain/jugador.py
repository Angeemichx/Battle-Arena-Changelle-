#Se crea la clase jugador para representar a cada jugador que se encuentra dentro de la partida

class Jugador:
    def __init__(self, id_jugador: int, nombre:str, x: int=0, y: int = 0):
        self.id_jugador = id_jugador 
        self.nombre = nombre 
        self.x = x
        self.y = y
        self.puntaje = 0 

    #Movimiento del jugador sumando dy y dx, ademas restricciones de limites de la arena 

    def mover(self, dx:int, dy:int, limite: int=800):
        nueva_x = self.x + dx
        nueva_y = self.y + dy

        #Para que no se salga de la arena:

        if 0<= nueva_x <= limite:
            self.x = nueva_x

        if 0<= nueva_y <= limite:
            self.y = nueva_y

    def sumar_punto(self):
        #En este parametro se sumara un punto por cada moviento 
        self.puntaje +=1

    #convertir el jugador en un diccionario para poder enviarlo como JSON
    def to_dict(self):
        return {"id": self.id_jugador, 
                "nombre": self.nombre, 
                "x": self.x, 
                "y": self.y, 
                "puntaje": self.puntaje}

