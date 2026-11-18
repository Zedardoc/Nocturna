import copy
import random
from config import COMPATIBILIDAD_ALIMENTO, RESERVAS_COMPARTIDAS


class ControlRecursos:
    """Administra la localización de fuentes de recursos, reservas compartidas, cadáveres, antídotos y Guayagod."""

    def __init__(self):
        # Almacena las fuentes de recursos situadas en casillas específicas del mapa
        # Estructura: {(fila, columna): {"tipo": str, "cantidad": int, "capacidad_maxima": int}}
        self.fuentes_mapa = {}

        # Copia propia de las reservas: cada partida empieza con los valores de config.py
        self.reservas = copy.deepcopy(RESERVAS_COMPARTIDAS)

        self.cadáveres = []
        self.antídotos = []
        self.guayagod_activo = False
        self.duracion_guayagod = 0
        self.ciclos_desde_ultima_aparicion = 20
        self.linaje_protegido_actual = None

    @property
    def antidotos(self):
        """Alias sin tilde: movement.py (P8) consulta recursos.antidotos."""
        return self.antídotos

    # --- Fuentes de Recursos y Consultas Básicas ---

    def registrar_fuente_recurso(self, fila, columna, tipo_recurso, cantidad_inicial=10):
        """Registra una fuente de recursos en una casilla (sangre, carne, biomasa o materiales)."""
        tipos_validos = {"sangre", "carne", "biomasa", "materiales"}
        if tipo_recurso not in tipos_validos:
            raise ValueError(f"ERROR INTERNO: Tipo de recurso no válido: {tipo_recurso}")

        self.fuentes_mapa[(fila, columna)] = {
            "tipo": tipo_recurso,
            "cantidad": cantidad_inicial,
            "capacidad_maxima": cantidad_inicial,
        }

    def es_alimento_compatible(self, linaje, tipo_recurso):
        """Verifica si el alimento es compatible con el linaje indicado."""
        if linaje not in COMPATIBILIDAD_ALIMENTO:
            return False
        return COMPATIBILIDAD_ALIMENTO[linaje] == tipo_recurso

    def consultar_fuente(self, fila, columna):
        """Devuelve la información de la fuente en la posición especificada o None si no hay."""
        return self.fuentes_mapa.get((fila, columna), None)

    # --- Reservas Compartidas y Regeneración ---

    def consultar_reserva(self, linaje, tipo_recurso):
        """Devuelve el número actual de unidades en la reserva compartida del linaje."""
        if linaje not in self.reservas:
            raise ValueError(f"ERROR INTERNO: Linaje no reconocido: {linaje}")
        if tipo_recurso not in ["alimento", "materiales"]:
            raise ValueError(f"ERROR INTERNO: Recurso no reconocido: {tipo_recurso}")

        return self.reservas[linaje][tipo_recurso]

    def modificar_reserva(self, linaje, tipo_recurso, cambio):
        """Suma o descuenta unidades de la reserva compartida garantizando que nunca sea negativa."""
        actual = self.consultar_reserva(linaje, tipo_recurso)
        nuevo_saldo = max(0, actual + cambio)
        self.reservas[linaje][tipo_recurso] = nuevo_saldo
        return nuevo_saldo

    def recolectar_de_fuente(self, fila, columna, linaje, cantidad=1):
        """Una criatura recolecta unidades de una fuente del mapa hacia la reserva compartida."""
        fuente = self.consultar_fuente(fila, columna)
        if fuente is None or fuente["cantidad"] <= 0:
            return 0

        unidades_extraídas = min(fuente["cantidad"], cantidad)
        fuente["cantidad"] -= unidades_extraídas

        if self.es_alimento_compatible(linaje, fuente["tipo"]):
            self.modificar_reserva(linaje, "alimento", unidades_extraídas)
        elif fuente["tipo"] == "materiales":
            self.modificar_reserva(linaje, "materiales", unidades_extraídas)

        return unidades_extraídas

    def consumir_de_reserva(self, linaje, tipo_recurso, cantidad=1):
        """Intenta consumir recursos de la reserva compartida. Retorna True si es posible."""
        disponible = self.consultar_reserva(linaje, tipo_recurso)
        if disponible >= cantidad:
            self.modificar_reserva(linaje, tipo_recurso, -cantidad)
            return True
        return False

    def regenerar_fuentes(self, unidades=1):
        """Regenera periódicamente las existencias de las fuentes sin exceder su capacidad máxima."""
        for pos, datos in self.fuentes_mapa.items():
            if datos["cantidad"] < datos["capacidad_maxima"]:
                datos["cantidad"] = min(datos["capacidad_maxima"], datos["cantidad"] + unidades)

    # --- Cadáveres, Antídotos y Retirada por Incendio ---

    def registrar_cadáver(self, criatura):
        """Registra el cadáver de una criatura abatida (permanecen 4 ciclos)."""
        if criatura.posicion is None:
            return False

        cadáver = {
            "id_criatura": criatura.id,
            "linaje": criatura.linaje,
            "posicion": criatura.posicion,
            "duracion_restante": 4,
        }
        self.cadáveres.append(cadáver)
        return True

    def avanzar_cadáveres(self):
        """Descuenta un ciclo de vida a los cadáveres y elimina los expirados."""
        cadáveres_vigentes = []
        for c in self.cadáveres:
            c["duracion_restante"] -= 1
            if c["duracion_restante"] > 0:
                cadáveres_vigentes.append(c)
        self.cadáveres = cadáveres_vigentes

    def consumir_cadáver(self, posicion, criatura_consumidora):
        """Permite consumir un cadáver compatible. Los zombis otorgan saciedad pero exponen a veneno."""
        for c in self.cadáveres:
            if c["posicion"] == posicion:
                if c["linaje"] == "zombi" and criatura_consumidora.linaje in ["vampiro", "hombre_lobo"]:
                    criatura_consumidora.modificar_saciedad(40)
                    self.cadáveres.remove(c)
                    return True, "envenenamiento_potencial"
                elif criatura_consumidora.linaje == c["linaje"]:
                    criatura_consumidora.modificar_saciedad(40)
                    self.cadáveres.remove(c)
                    return True, "normal"
        return False, "sin_cadáver"

    def agregar_antidoto(self, fila, columna, cantidad=1):
        """Coloca antídotos en el entorno."""
        self.antídotos.append({"posicion": (fila, columna), "cantidad": cantidad})

    def consumir_antidoto(self, posicion):
        """Consume una unidad de antídoto en la posición indicada."""
        for a in self.antídotos:
            if a["posicion"] == posicion and a["cantidad"] > 0:
                a["cantidad"] -= 1
                return True
        return False

    def retirar_recursos_por_incendio(self, fila, columna):
        """Retira alimentos o materiales y antídotos de casillas afectadas por incendio."""
        if (fila, columna) in self.fuentes_mapa:
            del self.fuentes_mapa[(fila, columna)]
        self.antídotos = [a for a in self.antídotos if a["posicion"] != (fila, columna)]
        return True

    # --- Guayagod (El Dragón) ---

    def evaluar_aparicion_guayagod(self, numero_ciclo, evento_activo, poblacion_obj, registro=None):
        """Controla la aparición de Guayagod (2% probabilidad, duración 3 ciclos, mínimo 20 ciclos entre apariciones)."""
        self.ciclos_desde_ultima_aparicion += 1

        if self.guayagod_activo:
            self.duracion_guayagod -= 1
            if self.duracion_guayagod <= 0:
                self.guayagod_activo = False
                self.linaje_protegido_actual = None
            return self.guayagod_activo

        if self.ciclos_desde_ultima_aparicion >= 20:
            if random.random() < 0.02:
                self.guayagod_activo = True
                self.duracion_guayagod = 3
                self.ciclos_desde_ultima_aparicion = 0
                self.determinar_linaje_protegido(evento_activo, poblacion_obj, registro, numero_ciclo)

        return self.guayagod_activo

    def determinar_linaje_protegido(self, evento_activo, poblacion_obj, registro=None, numero_ciclo=0):
        """Determina qué linaje recibe la protección de Guayagod según el evento o su poder."""
        if evento_activo == "Eclipse":
            self.linaje_protegido_actual = "vampiro"
        elif evento_activo == "Luna de sangre":
            self.linaje_protegido_actual = "hombre_lobo"
        elif evento_activo == "Lluvia corrupta":
            self.linaje_protegido_actual = "zombi"
        else:
            linajes = ["vampiro", "hombre_lobo", "zombi"]
            poderes = {}

            for linaje in linajes:
                vivas = poblacion_obj.obtener_vivas(linaje)
                if not vivas:
                    poderes[linaje] = 0
                    continue

                suma_poder = sum(c.salud + (2 * c.ataque) + (2 * c.defensa) for c in vivas)
                poderes[linaje] = suma_poder / len(vivas)

            max_poder = -1
            linaje_elegido = None
            empates = []

            for linaje, poder in poderes.items():
                if poder > max_poder:
                    max_poder = poder
                    linaje_elegido = linaje
                    empates = [linaje]
                elif poder == max_poder and poder > 0:
                    empates.append(linaje)

            self.linaje_protegido_actual = random.choice(empates) if len(empates) > 1 else linaje_elegido

            if self.linaje_protegido_actual and registro is not None:
                desc_texto = f"Guayagod reconoció la fortaleza del linaje de {self.linaje_protegido_actual} y decidió protegerlo"
                registro.registrar_ataque_guayagod(numero_ciclo, self.linaje_protegido_actual, desc_texto)

        if self.linaje_protegido_actual:
            self.modificar_reserva(self.linaje_protegido_actual, "alimento", -3)

    def ejecutar_ataque_guayagod(self, criatura_objetivo, ciclo=0, registro=None):
        """Guayagod ataca a criaturas no protegidas restando 20 de salud."""
        if not self.guayagod_activo or criatura_objetivo.linaje == self.linaje_protegido_actual:
            return False

        criatura_objetivo.modificar_salud(-20)
        if registro is not None:
            registro.registrar_ataque_guayagod(
                ciclo, self.linaje_protegido_actual,
                f"Guayagod atacó a criatura {criatura_objetivo.id} ({criatura_objetivo.linaje}) haciendo 20 de daño."
            )
        return True

    def ejecutar_ataque_guayagod_construccion(self, construccion_objetivo, aldeas_obj, ciclo=0, registro=None):
        """Guayagod ataca construcciones no protegidas haciendo 15 de daño."""
        if not self.guayagod_activo:
            return False

        linaje_construccion = construccion_objetivo.get("linaje")
        if linaje_construccion == self.linaje_protegido_actual:
            return False

        tipo_construccion = construccion_objetivo.get("tipo", "aldea")
        resultado = aldeas_obj.aplicar_dano_edificio(
            linaje_construccion, 15, tipo=tipo_construccion, ciclo=ciclo, registro=registro
        )

        if resultado.get("ok") and registro is not None:
            registro.registrar_ataque_guayagod(
                ciclo, self.linaje_protegido_actual,
                f"Guayagod atacó la construcción de {linaje_construccion} haciendo 15 de daño."
            )

        return resultado.get("ok", False)