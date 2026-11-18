"""P3 - Registro del mundo: historial, estadísticas y consistencia."""

class RegistroMundo:
    """
    Actualizado, creo
    P3: Historial, estadísticas y verificación de datos (Versión Optimizada)
    Registra el estado del mundo ciclo a ciclo, eventos específicos, poblaciones y métricas detalladas.
    """
    def __init__(self):
        self.historial_ciclos = []           # Resumen estadístico completo de cada ciclo
        self.acontecimientos_unicos = set()    # IDs únicos para evitar duplicidad de eventos
        self.ids_nacimientos_registrados = set() # Control de IDs únicos de nacimientos
        self.eventos_cronologicos = []       # Historial cronológico plano de todos los eventos

    def registrar_ciclo(self, numero_ciclo, poblacion_obj, eventos_activos=None, eventos_ciclo=None):
        """
        Registra el estado detallado del mundo al finalizar un ciclo.
        - poblacion_obj: Instancia de la clase Poblacion.
        - eventos_activos: Lista o nombres de eventos ambientales activos en el ciclo.
        - eventos_ciclo: Lista de diccionarios con sucesos puntuales del ciclo.
        """
        if eventos_ciclo is None:
            eventos_ciclo = []

        # Conteo automático de individuos vivos por especie
        vivas_vampiros = poblacion_obj.obtener_vivas("vampiro")
        vivas_lobos = poblacion_obj.obtener_vivas("hombre_lobo")
        vivas_zombis = poblacion_obj.obtener_vivas("zombi")

        n_vamp = len(vivas_vampiros)
        n_lobos = len(vivas_lobos)
        n_zombis = len(vivas_zombis)
        total_vivos = n_vamp + n_lobos + n_zombis

        if total_vivos < 0:
            raise ValueError(f"ERROR: Población negativa detectada en el ciclo {numero_ciclo}")

        # Función auxiliar para calcular promedios reales de la simulación
        def calcular_promedios(criaturas):
            if not criaturas:
                return {"salud_prom": 0.0, "energia_prom": 0.0, "saciedad_prom": 0.0}
            s = sum(c.salud for c in criaturas)
            e = sum(c.energia for c in criaturas)
            sac = sum(c.saciedad for c in criaturas)
            n = len(criaturas)
            return {
                "salud_prom": round(s / n, 2),
                "energia_prom": round(e / n, 2),
                "saciedad_prom": round(sac / n, 2)
            }

        conteo_linajes = {
            "vampiro": {"vivos": n_vamp, **calcular_promedios(vivas_vampiros)},
            "hombre_lobo": {"vivos": n_lobos, **calcular_promedios(vivas_lobos)},
            "zombi": {"vivos": n_zombis, **calcular_promedios(vivas_zombis)},
            "total_vivos": total_vivos
        }

        resumen_ciclo = {
            "ciclo": numero_ciclo,
            "poblacion": conteo_linajes,
            "eventos": [],
            "eventos_ambientales": eventos_activos if eventos_activos else []
        }

        # Procesar eventos del ciclo previniendo duplicados exactos
        for evento in eventos_ciclo:
            evento_id = evento.get("id_unico")
            if evento_id is not None:
                if evento_id in self.acontecimientos_unicos:
                    continue
                self.acontecimientos_unicos.add(evento_id)

            resumen_ciclo["eventos"].append(evento)
            self.eventos_cronologicos.append({
                "ciclo": numero_ciclo,
                "tipo": evento.get("tipo", "general"),
                "descripcion": evento.get("descripcion", "Sin descripción"),
                "id_unico": evento_id
            })

        self.historial_ciclos.append(resumen_ciclo)
        return resumen_ciclo

    def registrar_nacimiento(self, numero_ciclo, id_criatura, linaje):
        """Registra el nacimiento de un individuo verificando que su ID no esté repetido."""
        if id_criatura in self.ids_nacimientos_registrados:
            return False, f"ID de nacimiento repetido detectado: {id_criatura}"

        self.ids_nacimientos_registrados.add(id_criatura)
        desc = f"Nació un nuevo {linaje} con ID {id_criatura} en etapa I."

        self.registrar_acontecimiento(
            numero_ciclo=numero_ciclo,
            tipo="nacimiento",
            descripcion=desc,
            id_unico=f"nac_{id_criatura}"
        )
        return True, "Nacimiento registrado correctamente"

    def registrar_muerte(self, numero_ciclo, id_criatura, linaje, causa):
        """Registra la muerte de una criatura y genera su rastro de cadáver."""
        desc = f"La criatura {linaje} (ID: {id_criatura}) ha muerto. Causa: {causa}."
        return self.registrar_acontecimiento(
            numero_ciclo=numero_ciclo,
            tipo="muerte",
            descripcion=desc,
            id_unico=f"muerte_{id_criatura}_{numero_ciclo}"
        )

    def registrar_combate(self, numero_ciclo, atacante_id, objetivo_id, descripcion):
        """Registra un enfrentamiento o ataque entre criaturas."""
        return self.registrar_acontecimiento(
            numero_ciclo=numero_ciclo,
            tipo="combate",
            descripcion=descripcion,
            id_unico=f"comb_{numero_ciclo}_{atacante_id}_{objetivo_id}"
        )

    def registrar_evolucion(self, numero_ciclo, id_criatura, nueva_etapa, nombre_evolucion):
        """Registra la evolución de una criatura a una nueva etapa o forma alternativa."""
        desc = f"La criatura ID {id_criatura} evolucionó a la etapa {nueva_etapa}: {nombre_evolucion}."
        return self.registrar_acontecimiento(
            numero_ciclo=numero_ciclo,
            tipo="evolucion",
            descripcion=desc,
            id_unico=f"evo_{id_criatura}_{nueva_etapa}"
        )

    def registrar_evento_ambiental(self, numero_ciclo, tipo_evento, descripcion):
        """Registra la aparición o efecto de un evento ambiental."""
        desc = f"Evento ambiental [{tipo_evento}]: {descripcion}"
        return self.registrar_acontecimiento(
            numero_ciclo=numero_ciclo,
            tipo="evento_ambiental",
            descripcion=desc,
            id_unico=f"amb_{numero_ciclo}_{tipo_evento}"
        )

    def registrar_ataque_guayagod(self, numero_ciclo, linaje_protegido, descripcion):
        """Registra la aparición, pactos o ataques del dragón Guayagod."""
        desc = f"Guayagod (Protegido: {linaje_protegido}): {descripcion}"
        return self.registrar_acontecimiento(
            numero_ciclo=numero_ciclo,
            tipo="guayagod",
            descripcion=desc,
            id_unico=f"guayagod_{numero_ciclo}"
        )

    def registrar_aldea(self, numero_ciclo, linaje, estado_accion, descripcion):
        """Registra destrucción, reconstrucción o mejora de aldeas y refugios."""
        desc = f"Aldea de [{linaje}] - {estado_accion}: {descripcion}"
        return self.registrar_acontecimiento(
            numero_ciclo=numero_ciclo,
            tipo="aldea",
            descripcion=desc,
            id_unico=f"aldea_{numero_ciclo}_{linaje}_{estado_accion}"
        )

    def registrar_acontecimiento(self, numero_ciclo, tipo, descripcion, id_unico=None):
        """Método general para registrar un evento puntual previniendo duplicados."""
        if id_unico is not None:
            if id_unico in self.acontecimientos_unicos:
                return False
            self.acontecimientos_unicos.add(id_unico)

        evento = {
            "ciclo": numero_ciclo,
            "tipo": tipo,
            "descripcion": descripcion,
            "id_unico": id_unico
        }
        self.eventos_cronologicos.append(evento)
        return True

    def obtener_estadisticas_ultimo_ciclo(self):
        """Devuelve el resumen estadístico del último ciclo registrado."""
        if not self.historial_ciclos:
            return None
        return self.historial_ciclos[-1]

    def obtener_evolucion_poblaciones(self):
        """Devuelve el historial completo de poblaciones por ciclo para gráficas."""
        evolucion = []
        for reg in self.historial_ciclos:
            pob_plana = {}
            for linaje, datos in reg["poblacion"].items():
                if linaje == "total_vivos":
                    pob_plana["total_vivos"] = datos
                else:
                    pob_plana[linaje] = datos["vivos"]
            evolucion.append({
                "ciclo": reg["ciclo"],
                **pob_plana
            })
        return evolucion

    def obtener_historial_cronologico(self, filtro_tipo=None):
        """Devuelve la lista cronológica de acontecimientos, opcionalmente filtrada."""
        if filtro_tipo is None:
            return self.eventos_cronologicos
        return [ev for ev in self.eventos_cronologicos if ev["tipo"] == filtro_tipo]

    def verificar_consistencia_datos(self, poblacion_obj):
        """
        Verifica la integridad de los datos de la población actual:
        1. Comprueba IDs duplicados.
        2. Verifica rangos válidos de salud, energía y saciedad.
        """
        ids_vistos = set()
        for criatura in poblacion_obj.criaturas:
            if criatura.id in ids_vistos:
                return False, f"ID duplicado detectado en población: {criatura.id}"
            ids_vistos.add(criatura.id)

            if criatura.salud < 0 or criatura.salud > criatura.salud_maxima:
                return False, f"Salud fuera de rango en criatura ID {criatura.id}: {criatura.salud}"

            if criatura.energia < 0 or criatura.energia > criatura.energia_maxima:
                return False, f"Energía fuera de rango en criatura ID {criatura.id}: {criatura.energia}"

            if criatura.saciedad < 0 or criatura.saciedad > 100:
                return False, f"Saciedad fuera de rango en criatura ID {criatura.id}: {criatura.saciedad}"

        return True, "Datos consistentes"