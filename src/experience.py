"""
NOCTURNA: El Despertar del Eclipse
P10 - Experiencia, etapas y evoluciones.

La configuración se importa desde config.py.
La consulta de casillas se importa desde world.py.
"""

from config import (
    XP_ETAPA_II,
    XP_ETAPA_III,
    XP_POR_ACCION,
    REQUISITOS_ETAPA,
    MEJORA_POR_EVOLUCION,
    EVOLUCION_CURA_SALUD_ACTUAL,
    DANO_SOLAR_BASE,
    CICLOS_SUPERVIVENCIA_TRAS_FUEGO,
    CONDICIONES_ALTERNATIVAS,
    ADAPTACIONES,
    EVOLUCIONES,
    CLAVES_BONOS_ZONA,
)

from world import obtener_casilla


def datos_pendientes_p10():
    # Revisa que las tablas esten completas y coherentes. Devuelve la lista de problemas
    # (lista vacia = todo definido). Sirve para el Word y como prueba rapida.
    problemas = []
    for linaje, formas in EVOLUCIONES.items():
        for clave, datos in formas.items():
            if not datos.get("nombre") or "pendiente" in datos["nombre"].lower():
                problemas.append(f"{linaje}/{clave}: falta el nombre oficial")
            for nombre in datos.get("adaptaciones", []):
                if nombre not in ADAPTACIONES:
                    problemas.append(f"{linaje}/{clave}: adaptacion '{nombre}' no esta en ADAPTACIONES")
    for nombre, datos in ADAPTACIONES.items():
        for clave in datos.get("bonos_zona", {}):
            if clave not in CLAVES_BONOS_ZONA:
                problemas.append(f"adaptacion '{nombre}': bono no reconocido '{clave}'")
    return problemas


class ControlExperiencia:
    # Lleva la XP, los contadores y las evoluciones de cada criatura.
    # Todo se guarda por id de criatura para no tocar la clase Criatura.

    def __init__(self):
        self.acciones_contadas = set()    # acciones que ya dieron XP (id, tipo, ciclo, id_accion)
        self.eventos_contados = set()     # eventos de contadores que ya se contaron
        self.alimentaciones = {}          # {id: veces que comio}
        self.contadores = {}              # {id: {nombre del contador: valor}}
        self.casillas_contaminadas = {}   # {id: set de casillas (fila, columna)}
        self.fuego_pendiente = {}         # {id: set de ciclos con dano por fuego que aun no cumplen los dos ciclos}
        self.bonos_zona_activos = {}      # {id: bonos temporales de zona aplicados ahora mismo}
        self.evoluciones_aplicadas = set()  # (id, etapa) que ya se aplicaron
        self.tipo_evolucion = {}          # {id: "normal" o "alternativa"}
        self.forma_final = {}             # {id: nombre de la forma final} para P12
        self.adaptaciones = {}            # {id: lista de adaptaciones}

    def _validar_ciclo(self, ciclo):
        if type(ciclo) is not int or ciclo < 0:
            raise ValueError("ERROR INTERNO: el ciclo debe ser un entero mayor o igual que cero")

    # XP

    def sumar_xp(self, criatura, tipo, ciclo, id_accion=None):
        # Suma la XP de una accion y devuelve cuanto sumo (0 si ya estaba contada o esta muerta).
        # id_accion sirve para separar dos hechos iguales en el mismo ciclo (dos enemigos, por ejemplo).
        if tipo not in XP_POR_ACCION:
            raise ValueError("ERROR INTERNO: tipo de XP no reconocido: " + str(tipo))
        self._validar_ciclo(ciclo)
        if not criatura.vivo:
            return 0
        clave = (criatura.id, tipo, ciclo, id_accion)
        if clave in self.acciones_contadas:
            return 0
        self.acciones_contadas.add(clave)
        criatura.xp += XP_POR_ACCION[tipo]
        return XP_POR_ACCION[tipo]

    def registrar_supervivencia(self, criatura, ciclo):
        # +1 XP por sobrevivir un ciclo (no se duplica si se llama dos veces en el mismo ciclo)
        return self.sumar_xp(criatura, "supervivencia", ciclo)

    def registrar_alimentacion(self, criatura, ciclo, id_accion=None):
        # +1 XP y ademas cuenta una alimentacion
        self._validar_ciclo(ciclo)
        clave = (criatura.id, "alimentacion", ciclo, id_accion)
        if not criatura.vivo or clave in self.acciones_contadas:
            return 0
        self.alimentaciones[criatura.id] = self.alimentaciones.get(criatura.id, 0) + 1
        return self.sumar_xp(criatura, "alimentacion", ciclo, id_accion)

    def registrar_ataque_exitoso(self, criatura, ciclo, id_objetivo):
        # +2 XP por un ataque exitoso
        return self.sumar_xp(criatura, "ataque_exitoso", ciclo, id_objetivo)

    def registrar_victoria(self, criatura, ciclo, id_enemigo, linaje_enemigo=None):
        # +4 XP por eliminar un enemigo. Si es un hombre lobo que elimina un zombi, tambien cuenta
        # para "zombis_eliminados" (condicion de Bestia Salvaje). Hay que pasar linaje_enemigo.
        xp = self.sumar_xp(criatura, "victoria", ciclo, id_enemigo)
        if criatura.linaje == "hombre_lobo" and linaje_enemigo == "zombi":
            self._sumar_contador_unico(criatura, "zombis_eliminados", ciclo, id_enemigo)
        return xp

    def registrar_mejora(self, criatura, ciclo, id_mejora):
        # Las reglas no dan XP por mejoras: devuelve 0 (XP_POR_ACCION["mejora"] = 0)
        return self.sumar_xp(criatura, "mejora", ciclo, id_mejora)

    def procesar_resultado_accion(self, criatura, ciclo, resultado):
        # Recibe el diccionario que devuelve ejecutar_accion de P8.
        # Si se alimento bien, cuenta la alimentacion.
        if resultado.get("ok") and resultado.get("estado") == "ALIMENTARSE":
            return self.registrar_alimentacion(criatura, ciclo)
        return 0

    def procesar_resultado_ataque(self, atacante, ciclo, resultado, objetivo=None):
        # Recibe el diccionario que devuelve ControlCombate.atacar (P9).
        # Ataque con dano -> +2 XP. Si ademas el objetivo murio -> +4 XP (y cuenta zombi eliminado
        # si objetivo es un zombi). Devuelve la XP total sumada.
        if not resultado.get("ok") or resultado.get("dano", 0) <= 0:
            return 0
        id_objetivo = resultado.get("objetivo_id")
        total = self.registrar_ataque_exitoso(atacante, ciclo, id_objetivo)
        if resultado.get("objetivo_murio"):
            linaje = objetivo.linaje if objetivo is not None else None
            total += self.registrar_victoria(atacante, ciclo, id_objetivo, linaje)
        return total

    # Contadores de la evolucion alternativa

    def _sumar_contador_unico(self, criatura, nombre, ciclo, extra=None):
        # Suma 1 al contador, pero solo una vez por evento. Antes de la etapa II no cuenta.
        self._validar_ciclo(ciclo)
        if not criatura.vivo or criatura.etapa < 2:
            return False
        clave = (criatura.id, nombre, ciclo, extra)
        if clave in self.eventos_contados:
            return False
        self.eventos_contados.add(clave)
        contadores = self.contadores.setdefault(criatura.id, {})
        contadores[nombre] = contadores.get(nombre, 0) + 1
        return True

    def registrar_exposicion_solar(self, criatura, ciclo):
        # Vampiro: un ciclo diurno fuera de refugio SOBREVIVIDO. P6 debe llamarla solo en periodo
        # de dia, fuera de refugio propio y sin eclipse (con eclipse no hay dano solar), y despues
        # de aplicar el dano (si la criatura murio, no cuenta).
        if criatura.linaje != "vampiro":
            return False
        return self._sumar_contador_unico(criatura, "ciclos_exposicion_solar", ciclo)

    def registrar_bosque_contaminado(self, criatura, ciclo, mapa):
        # Lobo: un ciclo en una casilla de bosque con contaminacion
        if criatura.linaje != "hombre_lobo" or criatura.posicion is None:
            return False
        casilla = obtener_casilla(mapa, criatura.posicion[0], criatura.posicion[1])
        if casilla["terreno"] != "bosque" or "contaminacion" not in casilla["efectos"]:
            return False
        return self._sumar_contador_unico(criatura, "ciclos_bosque_contaminado", ciclo)

    def registrar_visita_contaminada(self, criatura, ciclo, mapa):
        # Zombi: visita a una casilla contaminada. Se usa un set para contar solo casillas distintas.
        self._validar_ciclo(ciclo)
        if criatura.linaje != "zombi" or criatura.posicion is None:
            return False
        if not criatura.vivo or criatura.etapa < 2:
            return False
        casilla = obtener_casilla(mapa, criatura.posicion[0], criatura.posicion[1])
        if "contaminacion" not in casilla["efectos"]:
            return False
        visitadas = self.casillas_contaminadas.setdefault(criatura.id, set())
        if criatura.posicion in visitadas:
            return False
        visitadas.add(criatura.posicion)
        contadores = self.contadores.setdefault(criatura.id, {})
        contadores["casillas_contaminadas_distintas"] = len(visitadas)
        return True

    def registrar_dano_fuego(self, criatura, ciclo, mapa):
        # Zombi: el ciclo en que recibe dano por incendio (esta en una casilla con fuego) NO cuenta
        # todavia: queda pendiente y solo cuenta si sigue vivo CICLOS_SUPERVIVENCIA_TRAS_FUEGO ciclos
        # despues. Devuelve True si se anoto el ciclo como pendiente.
        self._validar_ciclo(ciclo)
        if criatura.linaje != "zombi" or criatura.posicion is None:
            return False
        if not criatura.vivo or criatura.etapa < 2:
            return False
        casilla = obtener_casilla(mapa, criatura.posicion[0], criatura.posicion[1])
        if "fuego" not in casilla["efectos"]:
            return False
        pendientes = self.fuego_pendiente.setdefault(criatura.id, set())
        if ciclo in pendientes or (criatura.id, "incendios_sobrevividos", ciclo, "tras_fuego") in self.eventos_contados:
            return False
        pendientes.add(ciclo)
        return True

    def madurar_danos_fuego(self, criatura, ciclo_actual):
        # Revisa los ciclos de fuego pendientes del zombi. Si ya pasaron los ciclos exigidos y la
        # criatura sigue viva, cuenta ese ciclo en "incendios_sobrevividos". Si murio, los descarta.
        # Devuelve cuantos se contaron ahora. Se puede llamar todos los ciclos sin duplicar.
        self._validar_ciclo(ciclo_actual)
        pendientes = self.fuego_pendiente.get(criatura.id)
        if not pendientes:
            return 0
        if not criatura.vivo:
            pendientes.clear()
            return 0
        contadas = 0
        for ciclo_fuego in sorted(pendientes):
            if ciclo_actual >= ciclo_fuego + CICLOS_SUPERVIVENCIA_TRAS_FUEGO:
                pendientes.discard(ciclo_fuego)
                if self._sumar_contador_unico(criatura, "incendios_sobrevividos", ciclo_fuego, "tras_fuego"):
                    contadas += 1
        return contadas

    def consultar_contadores(self, criatura):
        # Devuelve una copia con los contadores del linaje (0 si todavia no hay)
        guardados = self.contadores.get(criatura.id, {})
        copia = {}
        for nombre in CONDICIONES_ALTERNATIVAS[criatura.linaje]:
            copia[nombre] = guardados.get(nombre, 0)
        return copia

    # Efectos de las formas alternativas

    def obtener_dano_solar(self, criatura):
        # Dano solar por ciclo de un vampiro: 8, o 2 si es Vampiro Solar. Lo usa P6.
        if "dano_solar_reducido" in self.adaptaciones.get(criatura.id, []):
            return ADAPTACIONES["dano_solar_reducido"]["dano_solar"]
        return DANO_SOLAR_BASE

    def _en_zona(self, criatura, mapa, zona):
        if criatura.posicion is None:
            return False
        casilla = obtener_casilla(mapa, criatura.posicion[0], criatura.posicion[1])
        contaminada = "contaminacion" in casilla["efectos"]
        if zona == "contaminada":
            return contaminada
        if zona == "bosque_contaminado":
            return contaminada and casilla["terreno"] == "bosque"
        raise ValueError("ERROR INTERNO: zona no reconocida: " + str(zona))

    def actualizar_bonos_zona(self, criatura, mapa):
        # Aplica o retira los bonos de zona de Bestia Salvaje y Portador de la Plaga segun la casilla
        # donde esta AHORA. Es idempotente (llamarla dos veces no suma dos veces).
        # Nota: recalcula ataque/defensa; si P11 aplica Luna de sangre, llamar
        # sincronizar_luna_sangre DESPUES de esta funcion (igual que despues de evolucionar).
        deseado = {clave: 0 for clave in CLAVES_BONOS_ZONA}
        if criatura.vivo:
            for nombre in self.adaptaciones.get(criatura.id, []):
                datos = ADAPTACIONES[nombre]
                if "zona" in datos and self._en_zona(criatura, mapa, datos["zona"]):
                    for clave, valor in datos["bonos_zona"].items():
                        deseado[clave] += valor
        actual = self.bonos_zona_activos.get(criatura.id, {clave: 0 for clave in CLAVES_BONOS_ZONA})
        if criatura.vivo:
            d_salud = deseado["salud_maxima"] - actual["salud_maxima"]
            d_ataque = deseado["ataque"] - actual["ataque"]
            d_defensa = deseado["defensa"] - actual["defensa"]
            if d_salud:
                criatura.salud_maxima += d_salud
                criatura.modificar_salud(0)  # si el maximo baja, la salud actual no puede quedar por encima
            if d_ataque or d_defensa:
                criatura.bono_ataque += d_ataque
                criatura.bono_defensa += d_defensa
                criatura.actualizar_ataque_defensa()
        if any(deseado.values()):
            self.bonos_zona_activos[criatura.id] = deseado
        else:
            self.bonos_zona_activos.pop(criatura.id, None)
        return dict(deseado)

    def procesar_ciclo(self, criatura, ciclo, mapa=None):
        # Atajo para P1: UNA llamada por criatura y ciclo, despues del movimiento y los danos.
        #  - +1 XP por sobrevivir el ciclo
        #  - madura los ciclos de fuego pendientes del zombi
        #  - con mapa: registra visitas/bosque contaminado/fuego y actualiza los bonos de zona
        # El sol del vampiro lo avisa P6 con registrar_exposicion_solar; la alimentacion y los
        # combates llegan por procesar_resultado_accion y procesar_resultado_ataque.
        self._validar_ciclo(ciclo)
        if criatura.vivo:
            self.registrar_supervivencia(criatura, ciclo)
        self.madurar_danos_fuego(criatura, ciclo)
        if mapa is not None and criatura.vivo:
            if criatura.linaje == "zombi":
                self.registrar_visita_contaminada(criatura, ciclo, mapa)
                self.registrar_dano_fuego(criatura, ciclo, mapa)
            elif criatura.linaje == "hombre_lobo":
                self.registrar_bosque_contaminado(criatura, ciclo, mapa)
        if mapa is not None:
            self.actualizar_bonos_zona(criatura, mapa)

    # Requisitos
    def _faltantes_etapa(self, criatura, etapa_destino):
        # Devuelve {requisito: cuanto falta}. Si queda vacio, cumple todo.
        requisitos = REQUISITOS_ETAPA[etapa_destino]
        faltantes = {}
        if criatura.xp < requisitos["xp"]:
            faltantes["xp"] = requisitos["xp"] - criatura.xp
        alimentaciones = self.alimentaciones.get(criatura.id, 0)
        if alimentaciones < requisitos["alimentaciones"]:
            faltantes["alimentaciones"] = requisitos["alimentaciones"] - alimentaciones
        return faltantes

    def _faltantes_alternativa(self, criatura):
        # Igual que el anterior pero con los contadores de la alternativa
        contadores = self.consultar_contadores(criatura)
        faltantes = {}
        for nombre, minimo in CONDICIONES_ALTERNATIVAS[criatura.linaje].items():
            if contadores[nombre] < minimo:
                faltantes[nombre] = minimo - contadores[nombre]
        return faltantes

    def evaluar_evolucion(self, criatura):
        # Solo revisa, no cambia nada. Devuelve un diccionario con:
        # puede, tipo, etapa_destino, faltantes, faltantes_alternativa y motivo
        r = {"puede": False, "tipo": None, "etapa_destino": None,
             "faltantes": {}, "faltantes_alternativa": {}, "motivo": ""}
        if not criatura.vivo:
            r["motivo"] = "la criatura esta muerta"
            return r
        if criatura.etapa >= 3:
            r["motivo"] = "ya esta en la etapa final"
            return r
        destino = criatura.etapa + 1
        r["etapa_destino"] = destino
        if (criatura.id, destino) in self.evoluciones_aplicadas:
            r["motivo"] = "esa evolucion ya se aplico"
            return r

        r["faltantes"] = self._faltantes_etapa(criatura, destino)
        if destino == 3:
            r["faltantes_alternativa"] = self._faltantes_alternativa(criatura)
        if r["faltantes"]:
            r["motivo"] = "faltan requisitos de la etapa " + str(destino)
            return r

        r["puede"] = True
        if destino == 3 and not r["faltantes_alternativa"]:
            r["tipo"] = "alternativa"  # regla de seleccion final: si cumple lo alternativo, gana la alternativa
        else:
            r["tipo"] = "normal"
        r["motivo"] = "cumple los requisitos"
        return r

    # Evolucion

    def evolucionar(self, criatura, ciclo, registro=None, mapa=None):
        # Si cumple, sube una etapa y aplica los cambios. Devuelve un diccionario con
        # ok, tipo, etapa, nombre, cambios y motivo.
        # registro es el RegistroMundo de P3 (opcional). mapa (opcional) sirve para aplicar de una vez
        # los bonos de zona de la forma alternativa.
        self._validar_ciclo(ciclo)
        self.madurar_danos_fuego(criatura, ciclo)  # por si el ciclo de fuego ya cumple los dos ciclos
        ev = self.evaluar_evolucion(criatura)
        if not ev["puede"]:
            return {"ok": False, "tipo": None, "etapa": criatura.etapa,
                    "nombre": criatura.nombre_evolucion, "cambios": None, "motivo": ev["motivo"]}

        destino = ev["etapa_destino"]
        tipo = ev["tipo"]
        if destino == 2:
            clave_forma = "II"
        elif tipo == "normal":
            clave_forma = "III_normal"
        else:
            clave_forma = "III_alternativa"
        datos = EVOLUCIONES[criatura.linaje][clave_forma]

        # Se validan las adaptaciones ANTES de cambiar nada, para no dejar la criatura a medias
        for nombre in datos["adaptaciones"]:
            if nombre not in ADAPTACIONES:
                raise ValueError("ERROR INTERNO: adaptacion no definida en ADAPTACIONES: " + str(nombre))

        self.evoluciones_aplicadas.add((criatura.id, destino))  # se marca antes para que no se repita

        mejora = MEJORA_POR_EVOLUCION
        criatura.etapa = destino
        criatura.nombre_evolucion = datos["nombre"]
        criatura.salud_maxima += mejora["salud_maxima"]
        if EVOLUCION_CURA_SALUD_ACTUAL:
            criatura.modificar_salud(mejora["salud_maxima"])
        criatura.bono_ataque += mejora["ataque"]
        criatura.bono_defensa += mejora["defensa"]
        criatura.actualizar_ataque_defensa()  # recalcula sin perder la forma del lobo
        lista = self.adaptaciones.setdefault(criatura.id, [])
        for nombre in datos["adaptaciones"]:
            if nombre not in lista:
                lista.append(nombre)
        self.tipo_evolucion[criatura.id] = tipo
        if destino == 3:
            self.forma_final[criatura.id] = datos["nombre"]
        if mapa is not None:
            self.actualizar_bonos_zona(criatura, mapa)

        if registro is not None:
            registro.registrar_evolucion(ciclo, criatura.id, destino, datos["nombre"])

        cambios = {"salud_maxima": mejora["salud_maxima"], "ataque": mejora["ataque"],
                   "defensa": mejora["defensa"], "adaptaciones": list(datos["adaptaciones"])}
        return {"ok": True, "tipo": tipo, "etapa": destino,
                "nombre": datos["nombre"], "cambios": cambios, "motivo": "evoluciono"}

    def evolucionar_poblacion(self, poblacion, ciclo, registro=None, mapa=None):
        # Revisa a todas las criaturas vivas y devuelve la lista de las que evolucionaron
        evolucionaron = []
        for criatura in poblacion.obtener_vivas():
            resultado = self.evolucionar(criatura, ciclo, registro, mapa)
            if resultado["ok"]:
                resultado["id"] = criatura.id
                evolucionaron.append(resultado)
        return evolucionaron

    # Consultas

    def obtener_forma_final(self, criatura):
        # Nombre de la forma final (para P12), o None si todavia no llega a la etapa III
        return self.forma_final.get(criatura.id)

    def resumen_experiencia(self, criatura):
        return {
            "id": criatura.id,
            "linaje": criatura.linaje,
            "xp": criatura.xp,
            "etapa": criatura.etapa,
            "nombre_evolucion": criatura.nombre_evolucion,
            "alimentaciones": self.alimentaciones.get(criatura.id, 0),
            "contadores": self.consultar_contadores(criatura),
            "fuego_pendiente": sorted(self.fuego_pendiente.get(criatura.id, set())),
            "bonos_zona": dict(self.bonos_zona_activos.get(criatura.id, {})),
            "tipo_evolucion": self.tipo_evolucion.get(criatura.id),
            "forma_final": self.forma_final.get(criatura.id),
            "adaptaciones": list(self.adaptaciones.get(criatura.id, [])),
        }