##ESTO ES SOLO DE PRUEBA, SE BORRA LUEGO DE CONFIRMAR QUE FUNCIONE

class ConsolaMailer:
    def enviar(self, destino: str, asunto: str, cuerpo: str):
        print(f"[MAIL SIMULADO] Para: {destino}\n{asunto}\n{cuerpo}\n", flush=True)