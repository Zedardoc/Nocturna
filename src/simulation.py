"""
NOCTURNA - Motor principal de simulación (P1).

Coordina los módulos del proyecto. No redefine valores de config.py.
Los objetos mapa, poblacion, recursos y aldeas llegan desde main.py.

Orden de un ciclo (ver ejecutar_ciclo):
  1. Eventos ambientales (P11) y Guayagod (P4).
  2. Por cada criatura viva:
       hambre (P6) -> forma del lobo (P6) -> veneno (P9) -> AFD (P7)
       -> acción (P8) -> XP (P10) -> energía (P6) -> daño ambiental (P6)
       -> XP de supervivencia / contadores (P10).
  3. Evoluciones (P10).
  4. Mantenimiento: cadáveres, regeneración de fuentes, habitantes muertos.
  5. Registro (P3) y descuento de marcas del mapa (P2).
"""

import random

from config import ESTADOS_AFD

from movement import (EjecutorAcciones, buscar_enemigo, puede_alimentarse_aqui,
    buscar_refugio, buscar_construccion_enemiga, amenaza_superior_cercana,
    hay_recurso_cercano, _en_acceso_refugio)
from combat import ControlCombate
from events import ControlEventos
from experience import ControlExperiencia
from time_manager import (
    RelojSimulacion,
    actualizar_hambre_y_saciedad,
    aplicar_costo_energia_accion,
    aplicar_recuperacion_energia,
    actualizar_forma,
    aplicar_dano_ambiental,
    vampiro_necesita_buscar_refugio,
)
from world import avanzar_efectos, liberar_casilla, marcar_efecto, consultar_efectos

# P7: AFD y prioridades de comportamiento
# El AFD asigna una única acción por ciclo de acuerdo con las condiciones
# de supervivencia, la proximidad de enemigos y el estado de las construcciones.
# La ejecución del movimiento y de las acciones corresponde a P8.

UMBRAL_HAMBRE = 40      # saciedad <= 40: la criatura tiene hambre (regla de saciedad)
UMBRAL_ENERGIA = 20     # energia <= 20: la criatura prioriza descansar (regla de energia)

# Tabla de transiciones: cada entrada lleva al estado que le corresponde.
# Estados usados: los mismos nombres de ESTADOS_AFD.
TRANSICIONES = {
    "veneno": "BUSCAR_CURA",
    "peligro_solar": "BUSCAR_REFUGIO",
    "refugio_diurno": "DESCANSAR",
    "retorno_preventivo": "BUSCAR_REFUGIO",
    "hambre": "BUSCAR_ALIMENTO",
    "hambre_en_fuente": "ALIMENTARSE",
    "energia_baja": "DESCANSAR",
    "enemigo_adyacente": "ATACAR",
    "enemigo_visible": "PERSEGUIR",
    "amenaza_superior": "HUIR",
    "construccion_adyacente": "ATACAR",
    "construccion_visible": "PERSEGUIR",
    "falta_aldea": "CONSTRUIR",
    "mejorar_aldea": "CONSTRUIR",
    "recurso_disponible": "RECOLECTAR",
    "nada": "EXPLORAR",
}

def elegir_entrada(situacion):
    """Selecciona una sola transición según peligro y posibilidades reales.

    Los riesgos ambientales y el veneno se atienden antes que los combates.
    Una amenaza cercana que supera a la criatura activa HUIR; si existe
    ventaja y energía suficiente, el AFD permite ATACAR o PERSEGUIR.
    """
    if not situacion.get("vivo", True):
        return "muerto"
    if situacion.get("peligro_solar"):
        return "peligro_solar"
    if situacion.get("veneno"):
        return "veneno"
    if situacion.get("en_refugio_de_dia"):
        # Un vampiro no abandona un refugio seguro durante el día.
        if situacion.get("enemigo_adyacente") and situacion.get("energia_para_atacar", True):
            return "enemigo_adyacente"
        if situacion.get("hambre") and situacion.get("en_fuente"):
            return "hambre_en_fuente"
        return "refugio_diurno"
    if situacion.get("retorno_preventivo"):
        return "retorno_preventivo"
    if situacion.get("amenaza_superior"):
        return "amenaza_superior"
    if situacion.get("enemigo_adyacente") and situacion.get("energia_para_atacar", True):
        return "enemigo_adyacente"
    if situacion.get("hambre"):
        return "hambre_en_fuente" if situacion.get("en_fuente") else "hambre"
    if situacion.get("energia_baja"):
        return "energia_baja"
    if situacion.get("enemigo_visible"):
        return "enemigo_visible"
    if situacion.get("falta_aldea"):
        return "falta_aldea"
    if situacion.get("mejorar_aldea"):
        return "mejorar_aldea"
    if situacion.get("recurso_disponible"):
        return "recurso_disponible"
    if situacion.get("construccion_adyacente") and situacion.get("energia_para_atacar", True):
        return "construccion_adyacente"
    if situacion.get("construccion_visible"):
        return "construccion_visible"
    return "nada"

def decidir(criatura, situacion):
    # Calcula el nuevo estado del AFD y lo guarda en criatura.estado_afd.
    # Una criatura muerta siempre queda en MUERTO.
    # Devuelve el estado elegido.
    situacion = dict(situacion, vivo=criatura.vivo)
    entrada = elegir_entrada(situacion)
    if entrada == "muerto" or criatura.estado_afd == "MUERTO":
        estado = "MUERTO"
    else:
        estado = TRANSICIONES[entrada]
    criatura.estado_afd = estado
    return estado

def _esta_en_refugio_de_dia(criatura, aldeas, ciclo=None, eventos=None):
    # True si un vampiro ya esta resguardado y sigue siendo de dia sin eclipse,
    # evitando que abandone el refugio mientras exista peligro solar.
    if criatura.linaje != "vampiro" or aldeas is None or ciclo is None:
        return False
    en_refugio = (aldeas.esta_en_refugio(criatura)
                  or aldeas.criatura_en_casilla_refugio(criatura))
    if not en_refugio:
        return False
    if eventos is not None and hasattr(eventos, "periodo_del_ciclo"):
        es_dia = eventos.periodo_del_ciclo(ciclo) == "dia"
    else:
        es_dia = (ciclo % 12) < 4
    hay_eclipse = False
    if eventos is not None and hasattr(eventos, "bloquea_dano_solar"):
        hay_eclipse = bool(eventos.bloquea_dano_solar())
    return es_dia and not hay_eclipse

def leer_situacion(criatura, mapa, poblacion, aldeas,
                   veneno=False, peligro_solar=False, en_fuente=False,
                   recursos=None, ciclo=None, eventos=None):
    """Agrupa las señales del mapa, la supervivencia y las construcciones.

    Una acción de construcción solo se habilita cuando existen los recursos y
    las condiciones necesarias. Si faltan, la recolección mantiene prioridad
    y evita intentos repetitivos de construcción sin resultados.
    """
    enemigo = buscar_enemigo(mapa, criatura, poblacion) if mapa is not None and poblacion is not None else None
    edificio = buscar_construccion_enemiga(mapa, criatura, aldeas)
    riesgo = (amenaza_superior_cercana(criatura, poblacion)
              if poblacion is not None else False)
    # Durante el atardecer y la noche, el vampiro estima los pasos necesarios
    # para volver a su refugio antes del próximo período diurno.
    regreso_preventivo = False
    if (criatura.linaje == "vampiro" and ciclo is not None
            and aldeas is not None and mapa is not None
            and criatura.posicion is not None and criatura.vivo
            and not aldeas.esta_en_refugio(criatura)
            and not (eventos is not None and eventos.bloquea_dano_solar())):
        fase = ciclo % 12
        if 4 <= fase <= 11:
            ruta_refugio = buscar_refugio(mapa, criatura, aldeas)
            if ruta_refugio is not None:
                pasos_hasta_refugio = len(ruta_refugio)
                ciclos_hasta_dia = 12 - fase
                regreso_preventivo = (pasos_hasta_refugio + 1 >= ciclos_hasta_dia)
    recurso_disp = False
    construccion_posible = False
    mejora_posible = False
    if recursos is not None and mapa is not None and criatura.posicion is not None:
        alimentacion = recursos.consultar_reserva(criatura.linaje, "alimento")
        materiales = recursos.consultar_reserva(criatura.linaje, "materiales")
        if alimentacion < 18 or materiales < 22:
            recurso_disp = (hay_recurso_cercano(mapa, criatura, recursos)
                            or alimentacion < 8 or materiales < 6)
        if aldeas is not None and poblacion is not None:
            if not aldeas.existe_aldea(criatura.linaje):
                if aldeas.existe_refugio_provisional(criatura.linaje):
                    ref = aldeas.consultar_refugio_provisional(criatura.linaje)
                    construccion_posible = (
                        ciclo is not None
                        and ref.get("ciclo_creacion") is not None
                        and ciclo - ref["ciclo_creacion"] >= 3
                        and len(poblacion.obtener_vivas(criatura.linaje)) >= 2
                        and materiales >= 5 and alimentacion >= 5
                    )
                else:
                    # El refugio provisional se permite solo tras destruir la aldea.
                    construccion_posible = (
                        criatura.linaje in aldeas.aldeas and materiales >= 5
                    )
            else:
                mejora_posible = aldeas.puede_mejorar_aldea(
                    criatura.linaje, poblacion, recursos
                )[0]
    return {
        "hambre": criatura.saciedad <= UMBRAL_HAMBRE,
        "energia_baja": criatura.energia <= UMBRAL_ENERGIA,
        "veneno": veneno,
        "peligro_solar": peligro_solar,
        "en_refugio_de_dia": _esta_en_refugio_de_dia(criatura, aldeas, ciclo, eventos),
        "retorno_preventivo": regreso_preventivo,
        "en_fuente": en_fuente,
        "enemigo_adyacente": enemigo is not None and enemigo["ruta"] == [],
        "enemigo_visible": enemigo is not None and enemigo["ruta"] != [],
        "amenaza_superior": riesgo,
        "energia_para_atacar": criatura.energia >= 5,
        "construccion_adyacente": edificio is not None and edificio["ruta"] == [],
        "construccion_visible": edificio is not None and edificio["ruta"] != [],
        "falta_aldea": construccion_posible,
        "mejorar_aldea": mejora_posible,
        "recurso_disponible": recurso_disp,
    }

# P7 - INTEGRACIÓN DEL ESTADO DE ENVENENAMIENTO CON P9
# La comprobación de veneno alimenta las transiciones del AFD.
# El peligro solar, la huida y la recolección se consultan desde P7 y P8.

def leer_situacion_parte3(criatura, mapa, poblacion, aldeas, combate,
                          peligro_solar=False, en_fuente=False,
                          recursos=None, ciclo=None, eventos=None):
    veneno = combate.esta_envenenado(criatura)
    return leer_situacion(criatura, mapa, poblacion, aldeas,
                          veneno=veneno, peligro_solar=peligro_solar,
                          en_fuente=en_fuente, recursos=recursos,
                          ciclo=ciclo, eventos=eventos)



ESTADOS_DE_MOVIMIENTO = {"EXPLORAR", "BUSCAR_ALIMENTO", "BUSCAR_REFUGIO", "BUSCAR_CURA",
 "PERSEGUIR", "HUIR", "RECOLECTAR"}

class Simulacion:
    """
    Coordina una partida completa.

    Parámetros:
        mapa, poblacion, recursos, aldeas: creados en main.py.
        registro: RegistroMundo opcional.
        semilla: semilla para eventos y veneno (reproducible).
        reloj, eventos, combate, experiencia, ejecutor: opcionales (pruebas).
        intervalo_regeneracion: cada cuántos ciclos regeneran las fuentes
            (0 = nunca). Las reglas del Colab no fijan el valor; se deja
            configurable.
    """

    def __init__(
        self,
        mapa,
        poblacion,
        recursos,
        aldeas,
        registro=None,
        semilla=None,
        reloj=None,
        eventos=None,
        combate=None,
        experiencia=None,
        ejecutor=None,
        intervalo_regeneracion=1,
    ):
        self.mapa = mapa
        self.poblacion = poblacion
        self.recursos = recursos
        self.aldeas = aldeas
        self.registro = registro
        self.intervalo_regeneracion = intervalo_regeneracion

        self._rng = random.Random(semilla)
        if hasattr(self.recursos, "rng"):
            self.recursos.rng = random.Random(semilla)

        self.reloj = reloj if reloj is not None else RelojSimulacion()

        # ControlEventos no importa world.py: se le inyectan las funciones de P2.
        self.eventos = eventos if eventos is not None else ControlEventos(
            semilla=semilla,
            marcar_efecto_fn=marcar_efecto,
            consultar_efectos_fn=consultar_efectos,
        )

        # ControlCombate necesita la función que libera la casilla al morir.
        self.combate = combate if combate is not None else ControlCombate(
            liberar_casilla,
            generador_aleatorio=self._rng.random,
        )

        self.experiencia = experiencia if experiencia is not None else ControlExperiencia()
        self.ejecutor = ejecutor if ejecutor is not None else EjecutorAcciones()

        self.historial_ciclos = []

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    def _registrar_muerte_si_corresponde(self, criatura, ciclo, causa):
        """combate.registrar_muerte es idempotente: solo actúa la primera vez."""
        if not criatura.vivo or criatura.salud <= 0:
            return self.combate.registrar_muerte(
                self.mapa, criatura, self.recursos, ciclo, causa, self.registro
            )
        return False

    def _leer_situacion(self, criatura, ciclo):
        """Agrupa señales del entorno, riesgos y recursos para el AFD (P7)."""
        return leer_situacion(
            criatura, self.mapa, self.poblacion, self.aldeas,
            veneno=self.combate.esta_envenenado(criatura),
            peligro_solar=vampiro_necesita_buscar_refugio(
                criatura, ciclo, self.aldeas, self.eventos),
            en_fuente=puede_alimentarse_aqui(criatura, self.recursos),
            recursos=self.recursos, ciclo=ciclo, eventos=self.eventos,
        )

    def _decidir_estado(self, criatura, ciclo):
        """Aplica P7 y conserva la acción decidida en el objeto Criatura."""
        estado = decidir(criatura, self._leer_situacion(criatura, ciclo))
        if estado not in ESTADOS_AFD:
            raise ValueError("Estado AFD no reconocido: " + str(estado))
        return estado

    def _sincronizar_luna(self):
        """Actualiza primero los bonos de zona (P10) y después Luna de sangre (P11)."""
        for criatura in self.poblacion.obtener_vivas():
            self.experiencia.actualizar_bonos_zona(criatura, self.mapa)
        self.eventos.sincronizar_luna_sangre(self.poblacion)

    def _procesar_una_criatura(self, criatura, ciclo):
        """Procesa el veneno, la decisión AFD y la acción de P8 de una criatura."""
        # El cambio de forma se aplica antes de evaluar los enfrentamientos.
        actualizar_forma(criatura, ciclo, evento_activo=self.eventos.evento_activo())
        self._sincronizar_luna()

        veneno = None
        if self.combate.esta_envenenado(criatura):
            veneno = self.combate.procesar_veneno(
                self.mapa, criatura, self.recursos, ciclo, self.registro)
        if not criatura.vivo:
            return {"id": criatura.id, "estado": "MUERTO", "ok": False, "veneno": veneno}

        estado = self._decidir_estado(criatura, ciclo)
        resultado = self.ejecutor.ejecutar_accion(
            criatura, ciclo, self.mapa, self.poblacion,
            recursos=self.recursos, aldeas=self.aldeas,
            combate=self.combate, registro=self.registro,
        )

        if resultado.get("ok"):
            if estado == "DESCANSAR":
                aplicar_recuperacion_energia(criatura, self.aldeas)
            elif estado in ("ALIMENTARSE", "RECOLECTAR", "CONSTRUIR"):
                # P8 ya cobra 2 por movimiento y P9 ya cobra 5 por ataque.
                aplicar_costo_energia_accion(criatura, ciclo, accion=estado)

        # El alojamiento no se pierde por actuar sin desplazarse. Solo se
        # retira cuando la criatura sale físicamente del perímetro protegido.
        if criatura.vivo and self.aldeas.esta_en_refugio(criatura):
            if not _en_acceso_refugio(self.mapa, criatura, self.aldeas):
                self.aldeas.desalojar_criatura(criatura)

        self.experiencia.procesar_resultado_accion(criatura, ciclo, resultado)
        if estado == "ATACAR":
            externo = resultado.get("externo") or {}
            if externo.get("tipo_objetivo") != "construccion":
                objetivo = self.poblacion.buscar_por_id(externo.get("objetivo_id"))
                self.experiencia.procesar_resultado_ataque(
                    criatura, ciclo, externo, objetivo=objetivo)

        self._registrar_muerte_si_corresponde(criatura, ciclo, "combate/accion")
        return {
            "id": criatura.id,
            "estado": estado,
            "ok": resultado.get("ok", False),
            "detalle": resultado.get("detalle"),
            "resultado": resultado,
            "veneno": veneno,
        }

    def _causa_muerte(self, id_criatura):
        """Busca en el registro la causa de muerte de una criatura (si hay registro)."""
        if self.registro is None:
            return ""
        marca = f"(ID: {id_criatura})"
        for ev in reversed(self.registro.eventos_cronologicos):
            if ev.get("tipo") == "muerte" and marca in ev.get("descripcion", ""):
                desc = ev["descripcion"]
                return desc.split("Causa:")[-1].strip(" .") if "Causa:" in desc else ""
        return ""

    # ------------------------------------------------------------------
    # Ciclo de simulación
    # ------------------------------------------------------------------

    def ejecutar_ciclo(self):
        """Ejecuta un ciclo preservando la interfaz pública y las reglas de integración."""
        ciclo = self.reloj.ciclo
        periodo = self.reloj.periodo
        vivas_antes = {c.id: c for c in self.poblacion.obtener_vivas()}

        # Los cadáveres previos envejecen antes de crear nuevos cadáveres.
        self.recursos.avanzar_cadáveres()
        cambios_eventos = self.eventos.avanzar_ciclo(
            ciclo, mapa=self.mapa, poblacion=self.poblacion,
            recursos=self.recursos, aldeas=self.aldeas,
            registro=self.registro, aplicar_dano_criaturas=False,
        )
        guayagod_activo = self.recursos.evaluar_aparicion_guayagod(
            ciclo, self.eventos.evento_activo(), self.poblacion, self.registro)
        if guayagod_activo:
            # Guayagod selecciona UN SOLO objetivo: criatura O construcción.
            objetivos = [("criatura", c) for c in self.poblacion.obtener_vivas()
                         if c.linaje != self.recursos.linaje_protegido_actual]
            objetivos += [("construccion", a) for a in self.aldeas.listar_construcciones()
                          if a["existe"] and a["linaje"] != self.recursos.linaje_protegido_actual]
            if objetivos:
                tipo, objetivo = self._rng.choice(objetivos)
                if tipo == "criatura":
                    self.recursos.ejecutar_ataque_guayagod(objetivo, ciclo, self.registro)
                    self._registrar_muerte_si_corresponde(objetivo, ciclo, "ataque de Guayagod")
                else:
                    self.recursos.ejecutar_ataque_guayagod_construccion(
                        objetivo, self.aldeas, ciclo, self.registro)

        self._sincronizar_luna()
        resultados_criaturas = []
        for criatura in list(self.poblacion.obtener_vivas()):
            if not criatura.vivo:
                continue
            hambre = actualizar_hambre_y_saciedad(criatura, ciclo)
            self._registrar_muerte_si_corresponde(criatura, ciclo, "inanición")
            accion = (self._procesar_una_criatura(criatura, ciclo)
                      if criatura.vivo else {"id": criatura.id, "estado": "MUERTO", "ok": False})
            ambiente = None
            if criatura.vivo:
                ambiente = aplicar_dano_ambiental(
                    criatura, self.mapa, ciclo, aldeas=self.aldeas,
                    info_p11=self.eventos, xp=self.experiencia)
                self._registrar_muerte_si_corresponde(criatura, ciclo, "daño ambiental")
            if criatura.vivo:
                if ambiente and ambiente["dano_sol"] != 0:
                    self.experiencia.registrar_exposicion_solar(criatura, ciclo)
                self.experiencia.procesar_ciclo(criatura, ciclo, mapa=self.mapa)
                self._sincronizar_luna()
            resultados_criaturas.append({
                "id": criatura.id, "hambre": hambre, "accion": accion,
                "ambiente": ambiente, "vivo": criatura.vivo,
            })

        evoluciones = self.experiencia.evolucionar_poblacion(
            self.poblacion, ciclo, registro=self.registro, mapa=self.mapa)
        if evoluciones:
            self._sincronizar_luna()
        self.aldeas.limpiar_habitantes_muertos(self.poblacion)

        # Se permite nacer cada ocho ciclos si quedan supervivientes y
        # se cumplen la capacidad, reservas y espacio físico definidos en P5.
        nacimientos = []
        for linaje in ("vampiro", "hombre_lobo", "zombi"):
            if self.poblacion.obtener_vivas(linaje):
                nueva, _ = self.aldeas.generar_individuo(
                    self.mapa, linaje, self.poblacion, self.recursos,
                    ciclo, registro=self.registro)
                if nueva is not None:
                    nacimientos.append(nueva.id)

        if self.intervalo_regeneracion and ciclo % self.intervalo_regeneracion == 0:
            self.recursos.regenerar_fuentes()
        if self.registro is not None:
            self.registro.registrar_ciclo(
                ciclo, self.poblacion,
                eventos_activos=[e["nombre"] for e in self.eventos.listar_eventos_activos()],
                eventos_ciclo=[],
            )
        avanzar_efectos(self.mapa)
        vivas_despues = self.poblacion.obtener_vivas()
        muertas = [
            {"id": i, "linaje": c.linaje, "causa": self._causa_muerte(i)}
            for i, c in vivas_antes.items() if not c.vivo
        ]
        resumen = {
            "ciclo": ciclo, "periodo": periodo, "eventos": cambios_eventos,
            "guayagod": guayagod_activo, "criaturas": resultados_criaturas,
            "evoluciones": evoluciones, "nacimientos": nacimientos,
            "muertes": muertas, "vivos": len(vivas_despues),
            "muertos": len(self.poblacion.criaturas) - len(vivas_despues),
            "extincion": len(vivas_despues) == 0,
        }
        self.historial_ciclos.append(resumen)
        self.reloj.avanzar()
        return resumen

    def ejecutar(self, cantidad_ciclos):
        """Ejecuta varios ciclos y devuelve la lista de sus resúmenes."""
        if type(cantidad_ciclos) is not int or cantidad_ciclos < 1:
            raise ValueError("cantidad_ciclos debe ser un entero >= 1")
        return [self.ejecutar_ciclo() for _ in range(cantidad_ciclos)]

    # ------------------------------------------------------------------
    # Salida para la interfaz / terminal
    # ------------------------------------------------------------------

    @staticmethod
    def resumen_a_logs(resumen):
        """Convierte el resumen de un ciclo en líneas de texto legibles (bitácora)."""
        c = resumen["ciclo"]
        logs = [f"── Ciclo {c} · {resumen['periodo'].upper()} · vivos {resumen['vivos']} ──"]

        for ev in resumen["eventos"]:
            verbo = "COMIENZA" if ev["accion"] == "inicio" else "TERMINA"
            logs.append(f"  ☾ {verbo}: {ev['nombre']}")
        if resumen.get("guayagod"):
            logs.append("  🐉 Guayagod está activo")

        for dato in resumen["criaturas"]:
            acc = dato.get("accion", {})
            estado = acc.get("estado")
            if estado in ("ATACAR", "ALIMENTARSE", "CONSTRUIR", "BUSCAR_CURA") and acc.get("detalle"):
                logs.append(f"  #{dato['id']} {estado}: {acc['detalle']}")
            if dato.get("hambre") and dato["hambre"].get("dano_saciedad_cero"):
                logs.append(f"  #{dato['id']} sufre hambre ({dato['hambre']['dano_saciedad_cero']} HP)")

        for evo in resumen["evoluciones"]:
            logs.append(f"  ✦ #{evo['id']} evolucionó a {evo['nombre']} (etapa {evo['etapa']}, {evo['tipo']})")
        for m in resumen["muertes"]:
            causa = f" — {m['causa']}" if m["causa"] else ""
            logs.append(f"  ☠ #{m['id']} ({m['linaje']}) murió{causa}")
        if resumen.get("extincion"):
            logs.append("  ⚠ No quedan criaturas vivas. Fin de la simulación.")
        return logs

    def estado_actual(self):
        """Datos generales para la interfaz gráfica (P12)."""
        return {
            "tiempo": {"ciclo": self.reloj.ciclo, "periodo": self.reloj.periodo},
            "eventos": self.eventos.datos_para_dibujar(),
            "poblacion": [c.resumen() for c in self.poblacion.obtener_vivas()],
            "aldeas": self.aldeas.listar_aldeas(),
        }