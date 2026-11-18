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

from movement import EjecutorAcciones, buscar_enemigo, puede_alimentarse_aqui
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

# ----------------------------------------------------------------------
# P7 - AFD (tabla de transiciones tomada del Colab)
# ----------------------------------------------------------------------
UMBRAL_HAMBRE = 40
UMBRAL_ENERGIA = 20

TRANSICIONES = {
    "veneno": "BUSCAR_CURA",
    "peligro_solar": "BUSCAR_REFUGIO",
    "hambre": "BUSCAR_ALIMENTO",
    "hambre_en_fuente": "ALIMENTARSE",
    "energia_baja": "DESCANSAR",
    "enemigo_adyacente": "ATACAR",
    "enemigo_visible": "PERSEGUIR",
    "falta_aldea": "CONSTRUIR",
    "nada": "EXPLORAR",
}

# Estados cuya acción es desplazarse: P8 ya cobra energía por casilla,
# así que P6 no debe cobrar el costo por acción encima (accion="MOVER").
ESTADOS_DE_MOVIMIENTO = {
    "EXPLORAR", "BUSCAR_ALIMENTO", "BUSCAR_REFUGIO", "BUSCAR_CURA",
    "PERSEGUIR", "HUIR", "RECOLECTAR",
}


def elegir_entrada(situacion):
    """Orden: muerte > veneno > sol > hambre > energía > enemigo adyacente
    > enemigo visible > falta de aldea > nada."""
    if not situacion.get("vivo", True):
        return "muerto"
    if situacion.get("veneno"):
        return "veneno"
    if situacion.get("peligro_solar"):
        return "peligro_solar"
    if situacion.get("hambre"):
        return "hambre_en_fuente" if situacion.get("en_fuente") else "hambre"
    if situacion.get("energia_baja"):
        return "energia_baja"
    if situacion.get("enemigo_adyacente"):
        return "enemigo_adyacente"
    if situacion.get("enemigo_visible"):
        return "enemigo_visible"
    if situacion.get("falta_aldea"):
        return "falta_aldea"
    return "nada"


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
        """Arma el diccionario de situaciones de P7 con los datos de cada módulo."""
        enemigo = buscar_enemigo(self.mapa, criatura, self.poblacion)
        return {
            "veneno": self.combate.esta_envenenado(criatura),
            "peligro_solar": vampiro_necesita_buscar_refugio(
                criatura, ciclo, self.aldeas, self.eventos
            ),
            "hambre": criatura.saciedad <= UMBRAL_HAMBRE,
            "en_fuente": puede_alimentarse_aqui(criatura, self.recursos),
            "energia_baja": criatura.energia <= UMBRAL_ENERGIA,
            "enemigo_adyacente": enemigo is not None and enemigo["ruta"] == [],
            "enemigo_visible": enemigo is not None and enemigo["ruta"] != [],
            "falta_aldea": not self.aldeas.existe_aldea(criatura.linaje),
        }

    def _decidir_estado(self, criatura, ciclo):
        """Aplica el AFD de P7 y guarda el resultado en criatura.estado_afd."""
        if not criatura.vivo:
            criatura.estado_afd = "MUERTO"
            return "MUERTO"

        situacion = self._leer_situacion(criatura, ciclo)
        estado = TRANSICIONES[elegir_entrada(situacion)]

        if estado not in ESTADOS_AFD:
            raise ValueError(f"Estado AFD no reconocido: {estado}")

        criatura.estado_afd = estado
        return estado

    def _sincronizar_luna(self):
        """P11: reaplica el bono de Luna de sangre. Hay que llamarlo después de
        cualquier cosa que recalcule ataque/defensa (forma, evolución, zona)."""
        self.eventos.sincronizar_luna_sangre(self.poblacion)

    def _procesar_una_criatura(self, criatura, ciclo):
        """Veneno, decisión del AFD y acción principal de una criatura."""
        # P6: cambio de forma del lobo según el periodo / eclipse.
        actualizar_forma(criatura, ciclo, evento_activo=self.eventos.evento_activo())
        self._sincronizar_luna()

        # P9: el veneno se procesa antes de decidir.
        veneno = None
        if self.combate.esta_envenenado(criatura):
            veneno = self.combate.procesar_veneno(
                self.mapa, criatura, self.recursos, ciclo, self.registro
            )

        if not criatura.vivo:
            return {"id": criatura.id, "estado": "MUERTO", "ok": False, "veneno": veneno}

        estado = self._decidir_estado(criatura, ciclo)

        resultado = self.ejecutor.ejecutar_accion(
            criatura, ciclo, self.mapa, self.poblacion,
            recursos=self.recursos, aldeas=self.aldeas,
            combate=self.combate, registro=self.registro,
        )

        # P10: XP por alimentación y por ataques.
        self.experiencia.procesar_resultado_accion(criatura, ciclo, resultado)
        if estado == "ATACAR":
            externo = resultado.get("externo") or {}
            objetivo = self.poblacion.buscar_por_id(externo.get("objetivo_id"))
            self.experiencia.procesar_resultado_ataque(
                criatura, ciclo, externo, objetivo=objetivo
            )

        # P6: energía. Si se movió, P8 ya cobró por casilla -> accion="MOVER" (costo 0).
        if resultado.get("ok"):
            if estado == "DESCANSAR":
                aplicar_recuperacion_energia(criatura, self.aldeas)
            else:
                mov = resultado.get("movimiento") or {}
                accion = "MOVER" if (estado in ESTADOS_DE_MOVIMIENTO and mov.get("movio")) else estado
                aplicar_costo_energia_accion(criatura, ciclo, accion=accion)

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
        """Ejecuta exactamente un ciclo de mundo y devuelve un resumen (dict)."""
        ciclo = self.reloj.ciclo
        periodo = self.reloj.periodo
        vivas_antes = {c.id: c for c in self.poblacion.obtener_vivas()}

        # 1. Eventos ambientales y Guayagod.
        cambios_eventos = self.eventos.avanzar_ciclo(
            ciclo,
            mapa=self.mapa,
            poblacion=self.poblacion,
            recursos=self.recursos,
            aldeas=self.aldeas,
            registro=self.registro,
            aplicar_dano_criaturas=False,   # P6 aplica el daño ambiental
        )
        guayagod_activo = self.recursos.evaluar_aparicion_guayagod(
            ciclo, self.eventos.evento_activo(), self.poblacion, self.registro
        )

        # 2. Criaturas (copia de la lista: pueden morir durante el ciclo).
        resultados_criaturas = []
        for criatura in list(self.poblacion.obtener_vivas()):
            if not criatura.vivo:      # murió atacada antes de su turno
                continue

            hambre = actualizar_hambre_y_saciedad(criatura, ciclo)
            self._registrar_muerte_si_corresponde(criatura, ciclo, "inanición")

            if criatura.vivo:
                accion = self._procesar_una_criatura(criatura, ciclo)
            else:
                accion = {"id": criatura.id, "estado": "MUERTO", "ok": False}

            ambiente = None
            if criatura.vivo:
                ambiente = aplicar_dano_ambiental(
                    criatura, self.mapa, ciclo,
                    aldeas=self.aldeas, info_p11=self.eventos,
                )
                self._registrar_muerte_si_corresponde(criatura, ciclo, "daño ambiental")

            if criatura.vivo:
                # Solo cuenta como exposición solar si hubo daño solar real
                # (de día, fuera de refugio y sin eclipse) y sobrevivió.
                if ambiente and ambiente["dano_sol"] != 0:
                    self.experiencia.registrar_exposicion_solar(criatura, ciclo)
                # +1 XP de supervivencia, contadores y bonos de zona.
                self.experiencia.procesar_ciclo(criatura, ciclo, mapa=self.mapa)
                self._sincronizar_luna()

            resultados_criaturas.append({
                "id": criatura.id,
                "hambre": hambre,
                "accion": accion,
                "ambiente": ambiente,
                "vivo": criatura.vivo,
            })

        # 3. Evoluciones.
        evoluciones = self.experiencia.evolucionar_poblacion(
            self.poblacion, ciclo, registro=self.registro, mapa=self.mapa
        )
        if evoluciones:
            self._sincronizar_luna()

        # 4. Mantenimiento del mundo.
        self.recursos.avanzar_cadáveres()
        if self.intervalo_regeneracion and ciclo % self.intervalo_regeneracion == 0:
            self.recursos.regenerar_fuentes()
        self.aldeas.limpiar_habitantes_muertos(self.poblacion)

        # 5. Registro y marcas temporales del mapa.
        if self.registro is not None:
            self.registro.registrar_ciclo(
                ciclo,
                self.poblacion,
                eventos_activos=[e["nombre"] for e in self.eventos.listar_eventos_activos()],
                eventos_ciclo=[],  # P11 ya anota sus eventos con registrar_evento_ambiental
            )
        avanzar_efectos(self.mapa)

        vivas_despues = self.poblacion.obtener_vivas()
        muertas = [
            {"id": i, "linaje": c.linaje, "causa": self._causa_muerte(i)}
            for i, c in vivas_antes.items() if not c.vivo
        ]

        resumen = {
            "ciclo": ciclo,
            "periodo": periodo,
            "eventos": cambios_eventos,
            "guayagod": guayagod_activo,
            "criaturas": resultados_criaturas,
            "evoluciones": evoluciones,
            "muertes": muertas,
            "vivos": len(vivas_despues),
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