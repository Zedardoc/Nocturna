from config import ATRIBUTOS_INICIALES, ESTADISTICAS_LOBO, NOMBRES_ETAPA_I, ESTADOS_AFD


class Criatura:
    """Cada objeto creado de esta clase tendrá su propia salud, su propio ID y sus datos."""

    def __init__(self, identificador, linaje):
        if linaje not in ATRIBUTOS_INICIALES:  # Validación del linaje
            raise ValueError("ERROR INTERNO: linaje no reconocido: " + str(linaje))
        if type(identificador) is not int or identificador < 1:  # Validación del identificador
            raise ValueError("ERROR INTERNO: el ID debe ser un entero mayor que cero")

        datos = ATRIBUTOS_INICIALES[linaje]

        self.id = identificador
        self.linaje = linaje

        if linaje == "hombre_lobo":
            self.forma = "humana"
        else:
            self.forma = None

        self.posicion = None

        self.salud_maxima = datos["salud_maxima"]
        self.salud = self.salud_maxima
        self.energia_maxima = datos["energia_maxima"]
        self.energia = self.energia_maxima
        self.saciedad = datos["saciedad"]
        self.deteccion = datos["deteccion"]

        self.bono_ataque = 0  # Aumento permanente por evolución
        self.bono_defensa = 0

        self.actualizar_ataque_defensa()  # Para calcular valores iniciales de ataque/defensa

        self.xp = 0  # Puntos de experiencia
        self.etapa = 1  # Primera etapa evolutiva
        self.nombre_evolucion = NOMBRES_ETAPA_I[linaje]
        self.estado_afd = "EXPLORAR"  # Estado predeterminado
        self.vivo = True

    def actualizar_ataque_defensa(self):
        """Busca el ataque base y defensa base y los combina con los bonos de evolución."""
        if self.linaje == "hombre_lobo":
            datosCombate = ESTADISTICAS_LOBO[self.forma]
        else:
            datosCombate = ATRIBUTOS_INICIALES[self.linaje]

        self.ataque = datosCombate["ataque"] + self.bono_ataque
        self.defensa = datosCombate["defensa"] + self.bono_defensa

        return self.ataque, self.defensa

    def cambiar_forma(self, nueva_forma):
        """Cambia la forma de un hombre lobo."""
        if self.linaje != "hombre_lobo":
            raise ValueError("ERROR INTERNO: solo los hombres lobo cambian de forma")
        if nueva_forma not in ESTADISTICAS_LOBO:
            raise ValueError("ERROR INTERNO: la forma debe ser humana o bestia")
        if not self.vivo:
            return self.forma

        self.forma = nueva_forma
        self.actualizar_ataque_defensa()
        return self.forma

    def modificar_salud(self, cambio):
        """Modifica la salud actual respetando los límites de 0 y salud_maxima."""
        if not self.vivo:
            return self.salud
        self.salud = max(0, min(self.salud_maxima, self.salud + cambio))
        if self.salud == 0:
            self.marcar_muerta()
        return self.salud

    def modificar_energia(self, cambio):
        """Modifica la energía actual respetando los límites."""
        if not self.vivo:
            return self.energia
        self.energia = max(0, min(self.energia_maxima, self.energia + cambio))
        return self.energia

    def modificar_saciedad(self, cambio):
        """Modifica la saciedad actual respetando los límites de 0 a 100."""
        if not self.vivo:
            return self.saciedad
        self.saciedad = max(0, min(100, self.saciedad + cambio))
        return self.saciedad

    def marcar_muerta(self):
        """Marca al individuo como fallecido."""
        self.salud = 0
        self.vivo = False
        self.estado_afd = "MUERTO"

    def resumen(self):
        """Devuelve un diccionario con el estado actual de la criatura."""
        return {
            "id": self.id,
            "linaje": self.linaje,
            "forma": self.forma,
            "posicion": self.posicion,
            "salud": self.salud,
            "salud_maxima": self.salud_maxima,
            "energia": self.energia,
            "energia_maxima": self.energia_maxima,
            "saciedad": self.saciedad,
            "ataque": self.ataque,
            "defensa": self.defensa,
            "deteccion": self.deteccion,
            "bono_ataque": self.bono_ataque,
            "bono_defensa": self.bono_defensa,
            "xp": self.xp,
            "etapa": self.etapa,
            "nombre_evolucion": self.nombre_evolucion,
            "estado_afd": self.estado_afd,
            "vivo": self.vivo,
        }


class Poblacion:
    """Administra el conjunto de individuos de una partida y la asignación de IDs únicos."""

    def __init__(self):
        self.criaturas = []
        self.siguiente_id = 1

    def crear_criatura(self, linaje):
        """Crea un individuo de etapa I, lo agrega a la lista y devuelve el objeto."""
        criatura = Criatura(self.siguiente_id, linaje)
        self.criaturas.append(criatura)
        self.siguiente_id += 1
        return criatura

    def buscar_por_id(self, identificador):
        """Busca y devuelve el objeto Criatura por su ID, o None si no existe."""
        for criatura in self.criaturas:
            if criatura.id == identificador:
                return criatura
        return None

    def obtener_vivas(self, linaje=None):
        """Devuelve una lista con las criaturas vivas, opcionalmente filtradas por linaje."""
        vivas = []
        for criatura in self.criaturas:
            if criatura.vivo:
                if linaje is None or criatura.linaje == linaje:
                    vivas.append(criatura)
        return vivas