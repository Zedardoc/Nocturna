# ======================================================================
# VILLAGES.PY - Control de Aldeas, Refugio, Mejoras y Nacimientos
# Proyecto: NOCTURNA — El Despertar del Eclipse
# ======================================================================

from config import (
    ATRIBUTOS_INICIALES,
    NIVEL_INICIAL,
    NIVEL_MAXIMO,
    RESISTENCIA_POR_NIVEL,
    CAPACIDAD_POR_NIVEL,
    COSTO_MEJORA_POR_NIVEL,
    COSTO_RECONSTRUCCION,
    REQUISITOS_NACIMIENTO,
    PROVISIONAL_CONFIG,
    ALDEA_ACEPTA_OTROS_LINAJES,
)
from world import dentro_del_mapa, casilla_disponible, obtener_vecinos, ubicar_criatura


class ControlAldeas:
    def __init__(self):
        self.aldeas = {}
        self.refugios_provisionales = {}
        self.ultimo_ciclo_nacimiento = {}

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    def _validar_linaje(self, linaje):
        if linaje not in ATRIBUTOS_INICIALES:
            raise ValueError("ERROR INTERNO: linaje no reconocido: " + str(linaje))

    def _validar_entero_positivo_o_none(self, nombre, valor):
        if valor is not None and (type(valor) is not int or valor <= 0):
            raise ValueError("ERROR INTERNO: " + nombre + " debe ser un entero positivo o None")

    def _validar_entero_no_negativo_o_none(self, nombre, valor):
        if valor is not None and (type(valor) is not int or valor < 0):
            raise ValueError("ERROR INTERNO: " + nombre + " debe ser un entero >= 0 o None")

    def _copiar(self, estructura):
        copia = dict(estructura)
        copia["habitantes"] = set(estructura["habitantes"])
        return copia

    def _casilla_ocupada_por_construccion(self, fila, columna):
        for aldea in self.aldeas.values():
            if aldea["existe"] and aldea["casilla"] == (fila, columna):
                return True
        for ref in self.refugios_provisionales.values():
            if ref["existe"] and ref["casilla"] == (fila, columna):
                return True
        return False

    # ------------------------------------------------------------------
    # 1. Creación de aldeas iniciales (Entrega 1)
    # ------------------------------------------------------------------

    def crear_aldea_inicial(self, mapa, linaje, fila, columna,
                            resistencia=None, capacidad=None):
        self._validar_linaje(linaje)
        if linaje in self.aldeas:
            raise ValueError("ERROR INTERNO: ya existe una aldea principal de " + str(linaje))
        if not dentro_del_mapa(mapa, fila, columna):
            raise ValueError("ERROR INTERNO: la casilla de la aldea esta fuera del mapa")
        if self._casilla_ocupada_por_construccion(fila, columna):
            raise ValueError("ERROR INTERNO: ya hay otra construccion en esa casilla")

        if resistencia is None:
            resistencia = RESISTENCIA_POR_NIVEL.get(NIVEL_INICIAL)
        if capacidad is None:
            capacidad = CAPACIDAD_POR_NIVEL.get(NIVEL_INICIAL)

        self._validar_entero_positivo_o_none("resistencia", resistencia)
        self._validar_entero_positivo_o_none("capacidad", capacidad)

        self.aldeas[linaje] = {
            "tipo": "aldea",
            "linaje": linaje,
            "casilla": (fila, columna),
            "nivel": NIVEL_INICIAL,
            "resistencia": resistencia,
            "resistencia_maxima": resistencia,
            "capacidad": capacidad,
            "existe": True,
            "habitantes": set(),
        }
        return self.consultar_aldea(linaje)

    def crear_aldeas_iniciales(self, mapa, posiciones,
                               resistencia=None, capacidad=None):
        if set(posiciones.keys()) != set(ATRIBUTOS_INICIALES.keys()):
            raise ValueError("ERROR INTERNO: se necesita una posicion por cada linaje")

        usadas = set()
        for linaje, posicion in posiciones.items():
            if linaje in self.aldeas:
                raise ValueError("ERROR INTERNO: ya existe una aldea principal de " + linaje)
            if type(posicion) is not tuple or len(posicion) != 2:
                raise ValueError("ERROR INTERNO: la posicion debe ser una tupla (fila, columna)")
            if not dentro_del_mapa(mapa, posicion[0], posicion[1]):
                raise ValueError("ERROR INTERNO: la casilla de " + linaje + " esta fuera del mapa")
            if self._casilla_ocupada_por_construccion(posicion[0], posicion[1]):
                raise ValueError("ERROR INTERNO: casilla ya ocupada por otra construccion")
            if posicion in usadas:
                raise ValueError("ERROR INTERNO: dos aldeas no pueden compartir casilla")
            usadas.add(posicion)

        creadas = {}
        for linaje, posicion in posiciones.items():
            creadas[linaje] = self.crear_aldea_inicial(
                mapa, linaje, posicion[0], posicion[1],
                resistencia=resistencia, capacidad=capacidad
            )
        return creadas

    # ------------------------------------------------------------------
    # 2. Consultas de aldeas y refugios provisionales
    # ------------------------------------------------------------------

    def consultar_aldea(self, linaje):
        if linaje not in self.aldeas:
            return None
        return self._copiar(self.aldeas[linaje])

    def existe_aldea(self, linaje):
        return linaje in self.aldeas and self.aldeas[linaje]["existe"]

    def consultar_refugio_provisional(self, linaje):
        if linaje not in self.refugios_provisionales:
            return None
        return self._copiar(self.refugios_provisionales[linaje])

    def existe_refugio_provisional(self, linaje):
        return (linaje in self.refugios_provisionales
                and self.refugios_provisionales[linaje]["existe"])

    def listar_aldeas(self):
        return [self._copiar(aldea) for aldea in self.aldeas.values()]

    def listar_refugios_provisionales(self):
        return [self._copiar(ref) for ref in self.refugios_provisionales.values()]

    def listar_construcciones(self):
        return self.listar_aldeas() + self.listar_refugios_provisionales()

    def obtener_aldea_en_casilla(self, fila, columna):
        for aldea in self.aldeas.values():
            if aldea["existe"] and aldea["casilla"] == (fila, columna):
                return self._copiar(aldea)
        return None

    def obtener_construccion_en_casilla(self, fila, columna):
        aldea = self.obtener_aldea_en_casilla(fila, columna)
        if aldea is not None:
            return aldea
        for ref in self.refugios_provisionales.values():
            if ref["existe"] and ref["casilla"] == (fila, columna):
                return self._copiar(ref)
        return None

    def obtener_refugio_disponible_linaje(self, linaje):
        if self.existe_aldea(linaje):
            return self._copiar(self.aldeas[linaje])
        if self.existe_refugio_provisional(linaje):
            return self._copiar(self.refugios_provisionales[linaje])
        return None

    def criatura_en_casilla_aldea(self, criatura):
        if not criatura.vivo or criatura.posicion is None:
            return False
        if not self.existe_aldea(criatura.linaje):
            return False
        return self.aldeas[criatura.linaje]["casilla"] == criatura.posicion

    def criatura_en_casilla_refugio(self, criatura):
        if not criatura.vivo or criatura.posicion is None:
            return False
        destino = self.obtener_refugio_disponible_linaje(criatura.linaje)
        if destino is None:
            return False
        return destino["casilla"] == criatura.posicion

    # ------------------------------------------------------------------
    # 3. Espacio y alojamiento (aldea principal o refugio provisional)
    # ------------------------------------------------------------------

    def _estructura_activa_para_alojar(self, linaje):
        if self.existe_aldea(linaje):
            return self.aldeas[linaje]
        if self.existe_refugio_provisional(linaje):
            return self.refugios_provisionales[linaje]
        return None

    def consultar_espacio(self, linaje):
        estructura = self._estructura_activa_para_alojar(linaje)
        if estructura is None:
            return {"existe": False, "tipo": None, "capacidad": None,
                    "ocupados": 0, "libres": None}
        ocupados = len(estructura["habitantes"])
        capacidad = estructura["capacidad"]
        libres = None if capacidad is None else max(0, capacidad - ocupados)
        return {
            "existe": True,
            "tipo": estructura["tipo"],
            "capacidad": capacidad,
            "ocupados": ocupados,
            "libres": libres,
        }

    def hay_espacio(self, linaje):
        datos = self.consultar_espacio(linaje)
        if not datos["existe"]:
            return False
        if datos["libres"] is None:
            return None
        return datos["libres"] > 0

    def alojar_criatura(self, criatura, linaje_aldea=None):
        if linaje_aldea is None:
            linaje_aldea = criatura.linaje
        if not criatura.vivo:
            return False, "La criatura esta muerta"
        if linaje_aldea != criatura.linaje and not ALDEA_ACEPTA_OTROS_LINAJES:
            return False, "La construccion solo aloja a su propio linaje"
        estructura = self._estructura_activa_para_alojar(linaje_aldea)
        if estructura is None:
            return False, "No existe aldea ni refugio activo de " + str(linaje_aldea)
        if self.refugio_de(criatura) is not None:
            return False, "La criatura ya esta alojada"
        if self.hay_espacio(linaje_aldea) is False:
            return False, "El refugio esta lleno"

        estructura["habitantes"].add(criatura.id)
        return True, "Criatura alojada en " + estructura["tipo"]

    def desalojar_criatura(self, criatura):
        desalojada = False
        for aldea in self.aldeas.values():
            if criatura.id in aldea["habitantes"]:
                aldea["habitantes"].discard(criatura.id)
                desalojada = True
        for ref in self.refugios_provisionales.values():
            if criatura.id in ref["habitantes"]:
                ref["habitantes"].discard(criatura.id)
                desalojada = True
        return desalojada

    def refugio_de(self, criatura):
        if not criatura.vivo:
            return None
        for linaje, aldea in self.aldeas.items():
            if aldea["existe"] and criatura.id in aldea["habitantes"]:
                return linaje
        for linaje, ref in self.refugios_provisionales.items():
            if ref["existe"] and criatura.id in ref["habitantes"]:
                return linaje
        return None

    def esta_en_refugio(self, criatura):
        return self.refugio_de(criatura) is not None

    def limpiar_habitantes_muertos(self, poblacion):
        retirados = []
        for coleccion in (self.aldeas.values(), self.refugios_provisionales.values()):
            for estructura in coleccion:
                for id_criatura in list(estructura["habitantes"]):
                    criatura = poblacion.buscar_por_id(id_criatura)
                    if criatura is None or not criatura.vivo:
                        estructura["habitantes"].discard(id_criatura)
                        retirados.append(id_criatura)
        return retirados

    # ------------------------------------------------------------------
    # 4. Niveles y mejoras de aldeas (Entrega 2)
    # ------------------------------------------------------------------

    def puede_mejorar_aldea(self, linaje, poblacion, recursos,
                            costo_materiales=None, etapa_minima=None):
        """Comprueba el nivel, la población viva y las reservas requeridas.

        Las mejoras no requieren una etapa evolutiva individual. La condición
        establecida en el reglamento se calcula sobre el número de supervivientes.
        """
        if not self.existe_aldea(linaje):
            return False, "No existe una aldea activa de " + str(linaje)
        aldea = self.aldeas[linaje]
        if aldea["nivel"] >= NIVEL_MAXIMO:
            return False, "La aldea ya alcanzo el nivel maximo"
        nivel = aldea["nivel"] + 1
        regla = COSTO_MEJORA_POR_NIVEL[nivel]
        materiales = regla["materiales"] if costo_materiales is None else costo_materiales
        self._validar_entero_no_negativo_o_none("costo_materiales", materiales)
        if poblacion is None:
            return False, "Falta la poblacion para comprobar supervivientes"
        vivas = poblacion.obtener_vivas(linaje)
        if len(vivas) < regla["minimo_vivos"]:
            return False, f"Se requieren {regla['minimo_vivos']} individuos vivos"
        if etapa_minima is not None and not any(c.etapa >= etapa_minima for c in vivas):
            return False, f"Se requiere una criatura en etapa {etapa_minima}"
        if recursos is None:
            return False, "Falta el modulo de recursos (P4)"
        if recursos.consultar_reserva(linaje, "alimento") < regla["alimento"]:
            return False, f"Alimento insuficiente para mejorar a nivel {nivel}"
        if recursos.consultar_reserva(linaje, "materiales") < materiales:
            return False, f"Materiales insuficientes para mejorar a nivel {nivel}"
        return True, f"Cumple los requisitos para mejorar a nivel {nivel}"

    def mejorar_aldea(self, linaje, poblacion, recursos,
                      costo_materiales=None, etapa_minima=None,
                      nueva_resistencia=None, nueva_capacidad=None,
                      ciclo=None, registro=None):
        """Descuenta alimento y materiales antes de aumentar el nivel de aldea."""
        ok, mensaje = self.puede_mejorar_aldea(linaje, poblacion, recursos,
                                              costo_materiales, etapa_minima)
        if not ok:
            return False, mensaje
        aldea = self.aldeas[linaje]
        nivel = aldea["nivel"] + 1
        regla = COSTO_MEJORA_POR_NIVEL[nivel]
        materiales = regla["materiales"] if costo_materiales is None else costo_materiales
        alimento = regla["alimento"]
        if nueva_resistencia is None:
            nueva_resistencia = RESISTENCIA_POR_NIVEL[nivel]
        if nueva_capacidad is None:
            nueva_capacidad = CAPACIDAD_POR_NIVEL[nivel]
        self._validar_entero_positivo_o_none("nueva_resistencia", nueva_resistencia)
        self._validar_entero_positivo_o_none("nueva_capacidad", nueva_capacidad)
        if not recursos.consumir_de_reserva(linaje, "alimento", alimento):
            return False, "No se pudo descontar el alimento"
        if not recursos.consumir_de_reserva(linaje, "materiales", materiales):
            recursos.modificar_reserva(linaje, "alimento", alimento)
            return False, "No se pudo descontar los materiales"
        aldea.update(nivel=nivel, resistencia=nueva_resistencia,
                     resistencia_maxima=nueva_resistencia, capacidad=nueva_capacidad)
        if registro is not None and ciclo is not None:
            registro.registrar_aldea(ciclo, linaje, "mejora",
                                    f"Aldea de {linaje} mejorada a nivel {nivel}")
        return True, f"Aldea de {linaje} mejorada a nivel {nivel}"

    # ------------------------------------------------------------------
    # 5. Daño y destrucción de edificios (Entrega 2)
    # ------------------------------------------------------------------

    def aplicar_dano_edificio(self, linaje, dano, tipo="aldea",
                              ciclo=None, registro=None):
        if type(dano) is not int or dano < 0:
            raise ValueError("ERROR INTERNO: el dano al edificio debe ser entero >= 0")
        if tipo not in ("aldea", "refugio_provisional"):
            raise ValueError("ERROR INTERNO: tipo de construccion no reconocido: " + str(tipo))

        coleccion = self.aldeas if tipo == "aldea" else self.refugios_provisionales
        if linaje not in coleccion or not coleccion[linaje]["existe"]:
            return {"ok": False, "destruida": False, "resistencia_restante": None,
                    "mensaje": f"No existe {tipo} activo de {linaje}"}

        estructura = coleccion[linaje]
        if estructura["resistencia"] is None:
            return {"ok": False, "destruida": False, "resistencia_restante": None,
                    "mensaje": "La resistencia de la construccion no esta configurada"}

        estructura["resistencia"] = max(0, estructura["resistencia"] - dano)
        destruida = (estructura["resistencia"] == 0)

        if destruida:
            estructura["existe"] = False
            estructura["habitantes"].clear()
            if registro is not None and ciclo is not None:
                registro.registrar_aldea(
                    ciclo, linaje, "destruccion",
                    f"{tipo} de {linaje} destruido por dano ({dano})"
                )
            return {"ok": True, "destruida": True, "resistencia_restante": 0,
                    "mensaje": f"{tipo} de {linaje} destruido"}

        return {"ok": True, "destruida": False,
                "resistencia_restante": estructura["resistencia"],
                "mensaje": f"Dano aplicado ({dano}); resistencia restante: {estructura['resistencia']}"}

    def aplicar_dano_en_casilla(self, fila, columna, dano, ciclo=None, registro=None):
        construccion = self.obtener_construccion_en_casilla(fila, columna)
        if construccion is None:
            return {"ok": False, "destruida": False, "resistencia_restante": None,
                    "mensaje": "No hay construccion activa en esa casilla"}
        return self.aplicar_dano_edificio(
            construccion["linaje"], dano, tipo=construccion["tipo"],
            ciclo=ciclo, registro=registro
        )

    # ------------------------------------------------------------------
    # 6. Refugio provisional y reconstrucción de aldea (Entrega 3)
    # ------------------------------------------------------------------

    def construir_refugio_provisional(self, mapa, linaje, fila, columna, recursos,
                                      costo_materiales=None, resistencia=None,
                                      capacidad=None, ciclo=None, registro=None):
        self._validar_linaje(linaje)
        if linaje not in self.aldeas:
            return False, "Se requiere una aldea principal destruida previamente"
        if self.existe_aldea(linaje):
            return False, "La aldea principal sigue en pie; no se requiere refugio provisional"
        if self.existe_refugio_provisional(linaje):
            return False, "Ya existe un refugio provisional activo para " + linaje
        if not dentro_del_mapa(mapa, fila, columna):
            raise ValueError("ERROR INTERNO: la casilla del refugio esta fuera del mapa")
        if self._casilla_ocupada_por_construccion(fila, columna):
            return False, "Ya hay otra construccion activa en esa casilla"

        if costo_materiales is None:
            costo_materiales = PROVISIONAL_CONFIG.get("costo_materiales")
        if resistencia is None:
            resistencia = PROVISIONAL_CONFIG.get("resistencia")
        if capacidad is None:
            capacidad = PROVISIONAL_CONFIG.get("capacidad")

        if costo_materiales is None:
            return False, "El costo del refugio provisional no esta configurado"
        self._validar_entero_no_negativo_o_none("costo_materiales", costo_materiales)
        self._validar_entero_positivo_o_none("resistencia", resistencia)
        self._validar_entero_positivo_o_none("capacidad", capacidad)

        if recursos is None:
            return False, "Falta el modulo de recursos (P4)"
        if not recursos.consumir_de_reserva(linaje, "materiales", costo_materiales):
            return False, "Materiales insuficientes para refugio provisional"

        self.refugios_provisionales[linaje] = {
            "tipo": "refugio_provisional",
            "linaje": linaje,
            "casilla": (fila, columna),
            "nivel": 1,
            "resistencia": resistencia,
            "resistencia_maxima": resistencia,
            "capacidad": capacidad,
            "existe": True,
            "habitantes": set(),
            "ciclo_creacion": ciclo,
        }

        if registro is not None and ciclo is not None:
            registro.registrar_aldea(
                ciclo, linaje, "refugio_provisional",
                f"Refugio provisional de {linaje} construido en {(fila, columna)}"
            )
        return True, "Refugio provisional construido"

    def reconstruir_aldea(self, mapa, linaje, recursos, fila=None, columna=None,
                          costo_materiales=None, resistencia=None, capacidad=None,
                          ciclo=None, registro=None, poblacion=None):
        """Convierte el refugio activo en aldea I en su posición actual.

        Requiere dos supervivientes, cinco unidades de alimento, cinco de
        materiales y tres ciclos completos desde la construcción del refugio.
        La validación evita reconstrucciones de linajes extinguidos.
        """
        self._validar_linaje(linaje)
        if self.existe_aldea(linaje):
            return False, "La aldea principal sigue activa"
        if not self.existe_refugio_provisional(linaje):
            return False, "No existe refugio provisional activo"
        if poblacion is None:
            return False, "Falta la poblacion para comprobar los supervivientes"
        if len(poblacion.obtener_vivas(linaje)) < COSTO_RECONSTRUCCION["minimo_vivos"]:
            return False, "Se requieren dos individuos vivos para reconstruir"
        ref = self.refugios_provisionales[linaje]
        if ciclo is None or ref.get("ciclo_creacion") is None:
            return False, "Se requiere el ciclo de construccion del refugio"
        if ciclo - ref["ciclo_creacion"] < COSTO_RECONSTRUCCION["ciclos_en_refugio"]:
            return False, "El refugio debe permanecer activo durante tres ciclos"
        destino = ref["casilla"]
        if fila is not None and columna is not None and (fila, columna) != destino:
            return False, "La aldea debe reemplazar al refugio en su misma casilla"
        if not dentro_del_mapa(mapa, *destino):
            return False, "La casilla del refugio esta fuera del mapa"
        if recursos is None:
            return False, "Falta el modulo de recursos (P4)"
        materiales = (COSTO_RECONSTRUCCION["materiales"] if costo_materiales is None
                      else costo_materiales)
        alimento = COSTO_RECONSTRUCCION["alimento"]
        self._validar_entero_no_negativo_o_none("costo_materiales", materiales)
        if recursos.consultar_reserva(linaje, "alimento") < alimento:
            return False, "Alimento insuficiente para reconstruir"
        if recursos.consultar_reserva(linaje, "materiales") < materiales:
            return False, "Materiales insuficientes para reconstruir"
        if not recursos.consumir_de_reserva(linaje, "alimento", alimento):
            return False, "No se pudo descontar alimento"
        if not recursos.consumir_de_reserva(linaje, "materiales", materiales):
            recursos.modificar_reserva(linaje, "alimento", alimento)
            return False, "No se pudo descontar materiales"
        resistencia = RESISTENCIA_POR_NIVEL[1] if resistencia is None else resistencia
        capacidad = CAPACIDAD_POR_NIVEL[1] if capacidad is None else capacidad
        self._validar_entero_positivo_o_none("resistencia", resistencia)
        self._validar_entero_positivo_o_none("capacidad", capacidad)
        habitantes = set(ref["habitantes"])
        if len(habitantes) > capacidad:
            return False, "La nueva aldea no puede alojar a todos los habitantes"
        ref["habitantes"].clear()
        ref["existe"] = False
        aldea = self.aldeas[linaje]
        aldea.update(casilla=destino, nivel=1, resistencia=resistencia,
                     resistencia_maxima=resistencia, capacidad=capacidad,
                     existe=True, habitantes=habitantes)
        if registro is not None:
            registro.registrar_aldea(ciclo, linaje, "reconstruccion",
                                    f"Aldea de {linaje} reconstruida en nivel I en {destino}")
        return True, "Aldea reconstruida en nivel I"

    # ------------------------------------------------------------------
    # 7. Nacimientos (Entrega 4)
    # ------------------------------------------------------------------

    def _buscar_casilla_libre_nacimiento(self, mapa, casilla_aldea):
        """Localiza una casilla desocupada dentro del área de alojamiento.

        El radio se determina a partir de la capacidad de la aldea activa.
        Se utiliza distancia Manhattan para mantener la misma geometría
        del acceso a refugios y se elige la casilla disponible más próxima.
        La ocupación individual de cada casilla continúa siendo exclusiva.
        """
        f, c = casilla_aldea
        capacidad = 1
        for aldea in self.aldeas.values():
            if aldea["existe"] and aldea["casilla"] == casilla_aldea:
                capacidad = aldea["capacidad"] or 1
                break

        radio = 0
        while 1 + 2 * radio * (radio + 1) < capacidad:
            radio += 1

        candidatas = []
        for fila in range(max(0, f - radio), min(len(mapa), f + radio + 1)):
            for columna in range(max(0, c - radio), min(len(mapa[fila]), c + radio + 1)):
                distancia = abs(fila - f) + abs(columna - c)
                if distancia <= radio and casilla_disponible(mapa, fila, columna):
                    candidatas.append((distancia, fila, columna))

        if not candidatas:
            return None
        _, fila, columna = min(candidatas)
        return (fila, columna)

    def puede_generar_individuo(self, mapa, linaje, poblacion, recursos, ciclo,
                                intervalo_ciclos=None, minimo_vivos=None,
                                costo_alimento=None, costo_materiales=None):
        self._validar_linaje(linaje)
        if type(ciclo) is not int or ciclo < 0:
            raise ValueError("ERROR INTERNO: ciclo debe ser entero >= 0")

        if not self.existe_aldea(linaje):
            return False, "No existe aldea principal activa de " + linaje

        if intervalo_ciclos is None:
            intervalo_ciclos = REQUISITOS_NACIMIENTO.get("intervalo_ciclos")
        if minimo_vivos is None:
            minimo_vivos = REQUISITOS_NACIMIENTO.get("minimo_vivos")
        if costo_alimento is None:
            costo_alimento = REQUISITOS_NACIMIENTO.get("costo_alimento")
        if costo_materiales is None:
            costo_materiales = REQUISITOS_NACIMIENTO.get("costo_materiales")

        if None in (intervalo_ciclos, minimo_vivos, costo_alimento, costo_materiales):
            return False, "Los parametros de nacimiento no estan configurados"

        self._validar_entero_positivo_o_none("intervalo_ciclos", intervalo_ciclos)
        self._validar_entero_positivo_o_none("minimo_vivos", minimo_vivos)
        self._validar_entero_no_negativo_o_none("costo_alimento", costo_alimento)
        self._validar_entero_no_negativo_o_none("costo_materiales", costo_materiales)

        ultimo = self.ultimo_ciclo_nacimiento.get(linaje)
        if ultimo is not None and (ciclo - ultimo) < intervalo_ciclos:
            return False, f"Intervalo no cumplido ({ciclo - ultimo}/{intervalo_ciclos} ciclos)"

        vivas = poblacion.obtener_vivas(linaje)
        if len(vivas) >= REQUISITOS_NACIMIENTO["maximo_poblacion"]:
            return False, "Se alcanzo la poblacion maxima del linaje"
        if len(vivas) < minimo_vivos:
            return False, f"Poblacion viva insuficiente ({len(vivas)}/{minimo_vivos})"

        if self.hay_espacio(linaje) is False:
            return False, "La aldea no tiene espacio libre para nuevos individuos"

        if recursos is None:
            return False, "Falta el modulo de recursos (P4)"
        if recursos.consultar_reserva(linaje, "alimento") < costo_alimento:
            return False, "Alimento insuficiente en reserva compartida"
        if recursos.consultar_reserva(linaje, "materiales") < costo_materiales:
            return False, "Materiales insuficientes en reserva compartida"

        casilla_spawn = self._buscar_casilla_libre_nacimiento(
            mapa, self.aldeas[linaje]["casilla"]
        )
        if casilla_spawn is None:
            return False, "No hay casilla libre en la aldea ni en sus vecinos"

        return True, f"Nacimiento autorizado en casilla {casilla_spawn}"

    def generar_individuo(self, mapa, linaje, poblacion, recursos, ciclo,
                          intervalo_ciclos=None, minimo_vivos=None,
                          costo_alimento=None, costo_materiales=None,
                          registro=None):
        ok, msg = self.puede_generar_individuo(
            mapa, linaje, poblacion, recursos, ciclo,
            intervalo_ciclos=intervalo_ciclos, minimo_vivos=minimo_vivos,
            costo_alimento=costo_alimento, costo_materiales=costo_materiales
        )
        if not ok:
            return None, msg

        if costo_alimento is None:
            costo_alimento = REQUISITOS_NACIMIENTO.get("costo_alimento")
        if costo_materiales is None:
            costo_materiales = REQUISITOS_NACIMIENTO.get("costo_materiales")

        casilla_spawn = self._buscar_casilla_libre_nacimiento(
            mapa, self.aldeas[linaje]["casilla"]
        )
        if casilla_spawn is None:
            return None, "No hay casilla libre disponible"

        if costo_alimento > 0 and not recursos.consumir_de_reserva(linaje, "alimento", costo_alimento):
            return None, "Fallo al descontar alimento"
        if costo_materiales > 0 and not recursos.consumir_de_reserva(linaje, "materiales", costo_materiales):
            if costo_alimento > 0:
                recursos.modificar_reserva(linaje, "alimento", costo_alimento)
            return None, "Fallo al descontar materiales"

        nueva = poblacion.crear_criatura(linaje)
        ubicar_criatura(mapa, nueva, casilla_spawn[0], casilla_spawn[1])
        self.ultimo_ciclo_nacimiento[linaje] = ciclo

        if registro is not None:
            registro.registrar_nacimiento(ciclo, nueva.id, linaje)

        return nueva, f"Nacio {linaje} ID {nueva.id} en {casilla_spawn}"

    # ------------------------------------------------------------------
    # 8. Verificación global de consistencia
    # ------------------------------------------------------------------

    def verificar_consistencia(self):
        casillas_vistas = set()
        ids_vistos = set()
        for linaje, aldea in self.aldeas.items():
            if linaje not in ATRIBUTOS_INICIALES or aldea["linaje"] != linaje:
                return False, "Aldea con linaje inconsistente: " + str(linaje)
            if aldea["existe"]:
                if aldea["casilla"] in casillas_vistas:
                    return False, "Dos construcciones comparten la casilla " + str(aldea["casilla"])
                casillas_vistas.add(aldea["casilla"])
            for id_criatura in aldea["habitantes"]:
                if id_criatura in ids_vistos:
                    return False, "Criatura alojada en dos construcciones: ID " + str(id_criatura)
                ids_vistos.add(id_criatura)
            if aldea["capacidad"] is not None and len(aldea["habitantes"]) > aldea["capacidad"]:
                return False, "Aldea de " + linaje + " sobrepasa su capacidad"

        for linaje, ref in self.refugios_provisionales.items():
            if linaje not in ATRIBUTOS_INICIALES or ref["linaje"] != linaje:
                return False, "Refugio provisional con linaje inconsistente: " + str(linaje)
            if ref["existe"]:
                if self.existe_aldea(linaje):
                    return False, "Coexisten aldea activa y refugio provisional para " + linaje
                if ref["casilla"] in casillas_vistas:
                    return False, "Refugio comparte casilla ocupada: " + str(ref["casilla"])
                casillas_vistas.add(ref["casilla"])
            for id_criatura in ref["habitantes"]:
                if id_criatura in ids_vistos:
                    return False, "Criatura alojada en dos construcciones: ID " + str(id_criatura)
                ids_vistos.add(id_criatura)
            if ref["capacidad"] is not None and len(ref["habitantes"]) > ref["capacidad"]:
                return False, "Refugio provisional de " + linaje + " sobrepasa su capacidad"

        return True, "Construcciones consistentes"
