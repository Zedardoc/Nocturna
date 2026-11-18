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
from world import dentro_del_mapa, casilla_disponible, obtener_vecinos


class ControlAldeas:

    def __init__(self):
        self.aldeas = {}
        self.refugios_provisionales = {}
        self.ultimo_ciclo_nacimiento = {}

    # --- Utilidades internas ---

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

    # --- 1. Creación de aldeas iniciales ---

    def crear_aldea_inicial(self, mapa, linaje, fila, columna, resistencia=None, capacidad=None):
        self._validar_linaje(linaje)
        if linaje in self.aldeas:
            raise ValueError("ERROR INTERNO: ya existe una aldea principal de " + str(linaje))
        if not dentro_del_mapa(mapa, fila, columna):
            raise ValueError("ERROR INTERNO: la casilla de la aldea está fuera del mapa")
        if self._casilla_ocupada_por_construccion(fila, columna):
            raise ValueError("ERROR INTERNO: ya hay otra construcción en esa casilla")

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

    def crear_aldeas_iniciales(self, mapa, posiciones, resistencia=None, capacidad=None):
        if set(posiciones.keys()) != set(ATRIBUTOS_INICIALES.keys()):
            raise ValueError("ERROR INTERNO: se necesita una posición por cada linaje")

        usadas = set()
        for linaje, posicion in posiciones.items():
            if linaje in self.aldeas:
                raise ValueError("ERROR INTERNO: ya existe una aldea principal de " + linaje)
            if type(posicion) is not tuple or len(posicion) != 2:
                raise ValueError("ERROR INTERNO: la posición debe ser una tupla (fila, columna)")
            if not dentro_del_mapa(mapa, posicion[0], posicion[1]):
                raise ValueError("ERROR INTERNO: la casilla de " + linaje + " está fuera del mapa")
            if self._casilla_ocupada_por_construccion(posicion[0], posicion[1]):
                raise ValueError("ERROR INTERNO: casilla ya ocupada por otra construcción")
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

    # --- 2. Consultas de aldeas y refugios provisionales ---

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

    # --- 3. Espacio y alojamiento ---

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
            return False, "La criatura está muerta"
        if linaje_aldea != criatura.linaje and not ALDEA_ACEPTA_OTROS_LINAJES:
            return False, "La construcción solo aloja a su propio linaje"
        estructura = self._estructura_activa_para_alojar(linaje_aldea)
        if estructura is None:
            return False, "No existe aldea ni refugio activo de " + str(linaje_aldea)
        if self.refugio_de(criatura) is not None:
            return False, "La criatura ya está alojada"
        if self.hay_espacio(linaje_aldea) is False:
            return False, "El refugio está lleno"

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

    # --- 4. Niveles y mejoras de aldeas ---

    def puede_mejorar_aldea(self, linaje, poblacion, recursos, costo_materiales=None, etapa_minima=None):
        if not self.existe_aldea(linaje):
            return False, "No existe una aldea activa de " + str(linaje)
        aldea = self.aldeas[linaje]
        if aldea["nivel"] >= NIVEL_MAXIMO:
            return False, "La aldea ya alcanzó el nivel máximo (" + str(NIVEL_MAXIMO) + ")"

        siguiente_nivel = aldea["nivel"] + 1
        regla_nivel = COSTO_MEJORA_POR_NIVEL.get(siguiente_nivel, {})

        if costo_materiales is None:
            costo_materiales = regla_nivel.get("materiales")
        if etapa_minima is None:
            etapa_minima = regla_nivel.get("etapa_minima", siguiente_nivel)

        if costo_materiales is None:
            return False, "Costo de mejora pendiente de aprobación oficial"
        self._validar_entero_no_negativo_o_none("costo_materiales", costo_materiales)
        if type(etapa_minima) is not int or etapa_minima < 1:
            raise ValueError("ERROR INTERNO: etapa_minima debe ser entero >= 1")

        vivas = poblacion.obtener_vivas(linaje)
        if not vivas:
            return False, "No hay criaturas vivas del linaje " + linaje
        if not any(c.etapa >= etapa_minima for c in vivas):
            return False, f"Se requiere al menos una criatura viva en etapa {etapa_minima}"

        if recursos is None:
            return False, "Falta el módulo de recursos"
        disponibles = recursos.consultar_reserva(linaje, "materiales")
        if disponibles < costo_materiales:
            return False, f"Materiales insuficientes ({disponibles}/{costo_materiales})"

        return True, "Cumple requisitos para mejorar a nivel " + str(siguiente_nivel)

    def mejorar_aldea(self, linaje, poblacion, recursos, costo_materiales=None, etapa_minima=None,
                      nueva_resistencia=None, nueva_capacidad=None, ciclo=None, registro=None):
        ok, msg = self.puede_mejorar_aldea(
            linaje, poblacion, recursos,
            costo_materiales=costo_materiales, etapa_minima=etapa_minima
        )
        if not ok:
            return False, msg

        aldea = self.aldeas[linaje]
        siguiente_nivel = aldea["nivel"] + 1
        regla_nivel = COSTO_MEJORA_POR_NIVEL.get(siguiente_nivel, {})
        if costo_materiales is None:
            costo_materiales = regla_nivel.get("materiales")

        if nueva_resistencia is None:
            nueva_resistencia = RESISTENCIA_POR_NIVEL.get(siguiente_nivel)
        if nueva_capacidad is None:
            nueva_capacidad = CAPACIDAD_POR_NIVEL.get(siguiente_nivel)

        self._validar_entero_positivo_o_none("nueva_resistencia", nueva_resistencia)
        self._validar_entero_positivo_o_none("nueva_capacidad", nueva_capacidad)

        if not recursos.consumir_de_reserva(linaje, "materiales", costo_materiales):
            return False, "No se pudo descontar materiales de la reserva"

        aldea["nivel"] = siguiente_nivel
        if nueva_resistencia is not None:
            aldea["resistencia_maxima"] = nueva_resistencia
            aldea["resistencia"] = nueva_resistencia
        if nueva_capacidad is not None:
            aldea["capacidad"] = nueva_capacidad

        if registro is not None and ciclo is not None:
            registro.registrar_aldea(
                ciclo, linaje, "mejora",
                f"Aldea de {linaje} mejorada a nivel {siguiente_nivel}"
            )

        return True, f"Aldea de {linaje} mejorada a nivel {siguiente_nivel}"

    # --- 5. Daño y destrucción de edificios ---

    def aplicar_dano_edificio(self, linaje, dano, tipo="aldea", ciclo=None, registro=None):
        if type(dano) is not int or dano < 0:
            raise ValueError("ERROR INTERNO: el daño al edificio debe ser entero >= 0")
        if tipo not in ("aldea", "refugio_provisional"):
            raise ValueError("ERROR INTERNO: tipo de construcción no reconocido: " + str(tipo))

        coleccion = self.aldeas if tipo == "aldea" else self.refugios_provisionales
        if linaje not in coleccion or not coleccion[linaje]["existe"]:
            return {"ok": False, "destruida": False, "resistencia_restante": None,
                    "mensaje": f"No existe {tipo} activo de {linaje}"}

        estructura = coleccion[linaje]
        if estructura["resistencia"] is None:
            return {"ok": False, "destruida": False, "resistencia_restante": None,
                    "mensaje": "Resistencia pendiente de aprobación; no se puede calcular daño"}

        estructura["resistencia"] = max(0, estructura["resistencia"] - dano)
        destruida = (estructura["resistencia"] == 0)

        if destruida:
            estructura["existe"] = False
            estructura["habitantes"].clear()
            if registro is not None and ciclo is not None:
                registro.registrar_aldea(
                    ciclo, linaje, "destrucción",
                    f"{tipo} de {linaje} destruido por daño ({dano})"
                )
            return {"ok": True, "destruida": True, "resistencia_restante": 0,
                    "mensaje": f"{tipo} de {linaje} destruido"}

        return {"ok": True, "destruida": False,
                "resistencia_restante": estructura["resistencia"],
                "mensaje": f"Daño aplicado ({dano}); resistencia restante: {estructura['resistencia']}"}

    def aplicar_dano_en_casilla(self, fila, columna, dano, ciclo=None, registro=None):
        construccion = self.obtener_construccion_en_casilla(fila, columna)
        if construccion is None:
            return {"ok": False, "destruida": False, "resistencia_restante": None,
                    "mensaje": "No hay construcción activa en esa casilla"}
        return self.aplicar_dano_edificio(
            construccion["linaje"], dano, tipo=construccion["tipo"],
            ciclo=ciclo, registro=registro
        )

    # --- 6. Refugio provisional y reconstrucción de aldea ---

    def construir_refugio_provisional(self, mapa, linaje, fila, columna, recursos,
                                      costo_materiales=None, resistencia=None,
                                      capacidad=None, ciclo=None, registro=None):
        self._validar_linaje(linaje)
        if self.existe_aldea(linaje):
            return False, "La aldea principal sigue en pie; no se requiere refugio provisional"
        if self.existe_refugio_provisional(linaje):
            return False, "Ya existe un refugio provisional activo para " + linaje
        if not dentro_del_mapa(mapa, fila, columna):
            raise ValueError("ERROR INTERNO: la casilla del refugio está fuera del mapa")
        if self._casilla_ocupada_por_construccion(fila, columna):
            return False, "Ya hay otra construcción activa en esa casilla"

        if costo_materiales is None:
            costo_materiales = PROVISIONAL_CONFIG.get("costo_materiales")
        if resistencia is None:
            resistencia = PROVISIONAL_CONFIG.get("resistencia")
        if capacidad is None:
            capacidad = PROVISIONAL_CONFIG.get("capacidad")

        if costo_materiales is None:
            return False, "Costo de refugio provisional pendiente de aprobación"
        self._validar_entero_no_negativo_o_none("costo_materiales", costo_materiales)
        self._validar_entero_positivo_o_none("resistencia", resistencia)
        self._validar_entero_positivo_o_none("capacidad", capacidad)

        if recursos is None:
            return False, "Falta el módulo de recursos"
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
        }

        if registro is not None and ciclo is not None:
            registro.registrar_aldea(
                ciclo, linaje, "refugio_provisional",
                f"Refugio provisional de {linaje} construido en {(fila, columna)}"
            )
        return True, "Refugio provisional construido"

    def reconstruir_aldea(self, mapa, linaje, recursos, fila=None, columna=None,
                          costo_materiales=None, resistencia=None, capacidad=None,
                          ciclo=None, registro=None):
        self._validar_linaje(linaje)
        if linaje not in self.aldeas:
            return False, "El linaje no tiene aldea previa registrada"
        if self.existe_aldea(linaje):
            return False, "La aldea principal ya existe y no está destruida"

        aldea = self.aldeas[linaje]
        if fila is None or columna is None:
            fila, columna = aldea["casilla"]
        if not dentro_del_mapa(mapa, fila, columna):
            raise ValueError("ERROR INTERNO: casilla de reconstrucción fuera del mapa")
        if self._casilla_ocupada_por_construccion(fila, columna):
            return False, "La casilla destino está ocupada por otra construcción"

        if costo_materiales is None:
            costo_materiales = COSTO_RECONSTRUCCION.get("materiales")
        if resistencia is None:
            resistencia = RESISTENCIA_POR_NIVEL