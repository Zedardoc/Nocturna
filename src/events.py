"""
NOCTURNA: El Despertar del Eclipse
P11 - Eventos ambientales

Este módulo administra Eclipse, Luna de sangre, Lluvia corrupta e Incendio.
No importa directamente P2-P5: las funciones del mapa se inyectan al crear
ControlEventos mediante marcar_efecto_fn y consultar_efectos_fn.

Ejemplo de conexión:
    from events import ControlEventos
    eventos = ControlEventos(
        marcar_efecto_fn=marcar_efecto,
        consultar_efectos_fn=consultar_efectos,
        tamano_mapa=TAMANO_MAPA
    )

Llama eventos.avanzar_ciclo(...) exactamente una vez por ciclo.
"""

# ======================================================================
# P11 - EVENTOS AMBIENTALES: ECLIPSE, LUNA DE SANGRE, LLUVIA CORRUPTA, INCENDIO
# NOCTURNA: El Despertar del Eclipse  |  UIS  |  Corte: 16 nov 2026
#
# Este módulo NO programa Guayagod (P4). Decide inicio, duración, fin y zona
# de los 4 eventos normales y AVISA / LLAMA a los demás módulos.
#
# USA del Colab compartido (celdas que deben estar ejecutadas ANTES):
#   - P2: TAMANO_MAPA, dentro_del_mapa, obtener_casilla, marcar_efecto,
#         consultar_efectos  (y la clase Poblacion / Criatura para Luna de sangre)
#   - P4: ControlRecursos.retirar_recursos_por_incendio(fila, columna)
#   - P5: ControlAldeas.aplicar_dano_en_casilla(fila, columna, dano, ciclo, registro)
#   - P3: RegistroMundo.registrar_evento_ambiental(ciclo, tipo_evento, descripcion)
#   - P6 (opcional): aplica el daño ambiental a criaturas leyendo las marcas del mapa.
#
# LO QUE ENTREGA A OTROS:
#   - P4  -> eventos.evento_activo()  devuelve "Eclipse", "Luna de sangre",
#            "Lluvia corrupta", "Incendio" o None (mismos textos que usa P4).
#   - P6  -> eventos.bloquea_dano_solar(), eventos.bonos_luna_sangre(criatura),
#            eventos.dano_ambiental_criatura(criatura, efectos_de_la_casilla)
#   - P12 -> eventos.datos_para_dibujar()
#   - P1  -> eventos.avanzar_ciclo(...)  UNA vez por ciclo.
#
# ORDEN RECOMENDADO PARA P1 EN CADA CICLO:
#   1) reloj de P6   2) eventos.avanzar_ciclo(ciclo, mapa, poblacion, recursos,
#   aldeas, registro)   3) ... AFD / acciones / daños ...
#   4) avanzar_efectos(mapa) de P2 AL FINAL del ciclo (descuenta duración de marcas).
# ======================================================================

import random

from config import (
    CICLOS_POR_DIA_MUNDO,
    PERIODOS,
    CONFIG_EVENTOS,
    BONOS_LUNA_SANGRE,
    CONTAMINACION_SALUD,
    EXCLUSION_ENTRE_EVENTOS,
    ORDEN_ORDEN_PRIORIDAD,
    TAMANO_MAPA,
)

class ControlEventos:
    """Controla los 4 eventos ambientales normales de una partida."""

    def __init__(self, semilla=None, generador=None,
                 marcar_efecto_fn=None, consultar_efectos_fn=None,
                 tamano_mapa=TAMANO_MAPA):
        # generador: cualquier objeto con .random() y .randint(a, b) (útil en pruebas).
        self.rng = generador if generador is not None else random.Random(semilla)
        self.activos = {}            # {tipo: dict del evento}
        self.historial = []          # lista de dict: inicios y fines
        self._bonos_luna = {}        # {id_criatura: {...}} bono aplicado actualmente
        self._termino_este_ciclo = set()   # tipos que acaban de terminar (no repetir en el mismo ciclo)

        # Dependencias de P2 inyectadas para mantener este módulo desacoplado.
        self.marcar_efecto = marcar_efecto_fn
        self.consultar_efectos = consultar_efectos_fn
        self.tamano_mapa = tamano_mapa

    # ------------------------------------------------------------------
    # Utilidades de tiempo
    # ------------------------------------------------------------------
    @staticmethod
    def periodo_del_ciclo(ciclo):
        """Devuelve 'dia', 'atardecer' o 'noche' (ciclo 0 = primer ciclo del día)."""
        return PERIODOS[(ciclo % CICLOS_POR_DIA_MUNDO) // 4]

    # ------------------------------------------------------------------
    # Consultas (para P4, P6, P12)
    # ------------------------------------------------------------------
    def esta_activo(self, tipo):
        return tipo in self.activos

    def tipos_activos(self):
        return [t for t in ORDEN_ORDEN_PRIORIDAD if t in self.activos]

    def evento_activo(self):
        """Nombre oficial del evento activo ('Eclipse', 'Luna de sangre',
        'Lluvia corrupta', 'Incendio') o None. P4 lo usa para Guayagod."""
        tipos = self.tipos_activos()
        if not tipos:
            return None
        return CONFIG_EVENTOS[tipos[0]]["nombre"]

    def obtener_evento_activo(self):
        """Copia del diccionario del evento activo (o None)."""
        tipos = self.tipos_activos()
        if not tipos:
            return None
        return self._copiar(self.activos[tipos[0]])

    def listar_eventos_activos(self):
        return [self._copiar(self.activos[t]) for t in self.tipos_activos()]

    def eclipse_activo(self):
        return "eclipse" in self.activos

    def bloquea_dano_solar(self):
        """True si durante este ciclo el Eclipse impide el daño solar (P6)."""
        return self.eclipse_activo()

    def luna_sangre_activa(self):
        return "luna_sangre" in self.activos

    def casillas_afectadas(self, tipo=None):
        """Casillas (fila, columna) de la zona de lluvia/incendio activos."""
        casillas = []
        for t in self.tipos_activos():
            if tipo is not None and t != tipo:
                continue
            casillas.extend(self.activos[t].get("zona", []))
        return casillas

    def datos_para_dibujar(self):
        """Resumen simple para P12."""
        return {"evento": self.evento_activo(),
                "eventos": self.listar_eventos_activos(),
                "zona": self.casillas_afectadas()}

    @staticmethod
    def _copiar(evento):
        copia = dict(evento)
        copia["zona"] = list(evento.get("zona", []))
        return copia

    # ------------------------------------------------------------------
    # Zona 3 x 3
    # ------------------------------------------------------------------
    def _generar_zona(self, lado, centro=None):
        """Zona cuadrada completamente dentro del mapa. centro=(fila, columna)
        opcional; si se omite se sortea. Devuelve lista de tuplas."""
        n = self.tamano_mapa
        if centro is None:
            f0 = self.rng.randint(0, n - lado)
            c0 = self.rng.randint(0, n - lado)
        else:
            f0 = min(max(centro[0] - lado // 2, 0), n - lado)
            c0 = min(max(centro[1] - lado // 2, 0), n - lado)
        return [(f0 + i, c0 + j) for i in range(lado) for j in range(lado)]

    # ------------------------------------------------------------------
    # Inicio / fin de eventos
    # ------------------------------------------------------------------
    def iniciar_evento(self, tipo, ciclo, mapa=None, recursos=None, aldeas=None,
                       registro=None, centro=None):
        """Inicia un evento. Devuelve el dict del evento o None si no se pudo
        (tipo inválido, ya activo, o hay otro evento activo con exclusión)."""
        if tipo not in CONFIG_EVENTOS:
            raise ValueError("ERROR INTERNO: evento desconocido: " + str(tipo))
        if tipo in self.activos:
            return None
        if EXCLUSION_ENTRE_EVENTOS and self.activos:
            return None

        cfg = CONFIG_EVENTOS[tipo]
        evento = {
            "tipo": tipo,
            "nombre": cfg["nombre"],
            "inicio": ciclo,
            "fin": ciclo + cfg["duracion"],   # ciclo (exclusivo) en que ya no está activo
            "duracion": cfg["duracion"],
            "zona": [],
            "ultimo_tick": None,
        }

        if tipo in ("lluvia_corrupta", "incendio"):
            evento["zona"] = self._generar_zona(cfg["lado_zona"], centro)

        # Marcas en el mapa de P2 (solo una vez, al empezar)
        if mapa is not None:
            if self.marcar_efecto is None:
                raise RuntimeError("Falta conectar marcar_efecto de P2.")
            if tipo == "lluvia_corrupta":
                dur = cfg["duracion"] + cfg["ciclos_contaminacion_extra"]
                for f, c in evento["zona"]:
                    self.marcar_efecto(mapa, f, c, "contaminacion", dur)
            elif tipo == "incendio":
                for f, c in evento["zona"]:
                    self.marcar_efecto(mapa, f, c, "fuego", cfg["duracion"])
                    self.marcar_efecto(mapa, f, c, "quemado",
                                  cfg["duracion"] + cfg["ciclos_quemado_extra"])

        self.activos[tipo] = evento
        self._anotar(evento, "inicio", ciclo, registro)
        return self._copiar(evento)

    def finalizar_evento(self, tipo, ciclo, registro=None, poblacion=None):
        """Termina un evento activo. Las marcas del mapa (contaminación,
        quemado) siguen su propia duración y las descuenta P2."""
        if tipo not in self.activos:
            return False
        evento = self.activos.pop(tipo)
        self._termino_este_ciclo.add(tipo)
        self._anotar(evento, "fin", ciclo, registro)
        if tipo == "luna_sangre" and poblacion is not None:
            self.sincronizar_luna_sangre(poblacion)
        return True

    def forzar_evento(self, tipo, ciclo, mapa=None, recursos=None, aldeas=None,
                      registro=None, poblacion=None, centro=None):
        """Activación MANUAL (pruebas / botón de P12). Termina cualquier evento
        activo (si hay exclusión) y arranca el pedido. Aplica de inmediato sus
        efectos del ciclo actual."""
        if EXCLUSION_ENTRE_EVENTOS:
            for t in list(self.activos):
                self.finalizar_evento(t, ciclo, registro, poblacion)
        evento = self.iniciar_evento(tipo, ciclo, mapa, recursos, aldeas, registro, centro)
        if evento is not None:
            self._aplicar_efectos_ciclo(self.activos[tipo], ciclo, mapa, recursos,
                                        aldeas, registro)
            if poblacion is not None:
                self.sincronizar_luna_sangre(poblacion)
        return evento

    def _anotar(self, evento, accion, ciclo, registro):
        nombre = evento["nombre"]
        zona_txt = ""
        if evento["zona"]:
            zona_txt = " Zona 3x3 desde " + str(evento["zona"][0]) + "."
        if accion == "inicio":
            desc = f"Comienza {nombre} (dura {evento['duracion']} ciclos).{zona_txt}"
        else:
            desc = f"Termina {nombre}."
        self.historial.append({"ciclo": ciclo, "tipo": evento["tipo"], "nombre": nombre,
                               "accion": accion, "zona": list(evento["zona"])})
        if registro is not None:
            registro.registrar_evento_ambiental(ciclo, nombre, desc)

    # ------------------------------------------------------------------
    # Sorteo automático
    # ------------------------------------------------------------------
    def _sortear_evento(self, ciclo):
        """Decide si empieza un evento nuevo en este ciclo. Devuelve tipo o None."""
        if EXCLUSION_ENTRE_EVENTOS and self.activos:
            return None
        en_dia = ciclo % CICLOS_POR_DIA_MUNDO

        # Eventos ligados al inicio de un período (consumen un sorteo cada uno)
        for tipo in ("eclipse", "luna_sangre"):
            cfg = CONFIG_EVENTOS[tipo]
            if tipo in self.activos or tipo in self._termino_este_ciclo:
                continue
            if en_dia == cfg["ciclo_en_dia"] and self.rng.random() < cfg["probabilidad"]:
                return tipo
        # Eventos por ciclo elegible
        for tipo in ("lluvia_corrupta", "incendio"):
            if tipo in self.activos or tipo in self._termino_este_ciclo:
                continue
            if self.rng.random() < CONFIG_EVENTOS[tipo]["probabilidad"]:
                return tipo
        return None

    # ------------------------------------------------------------------
    # Efectos por ciclo
    # ------------------------------------------------------------------
    def _aplicar_efectos_ciclo(self, evento, ciclo, mapa, recursos, aldeas, registro):
        """Efectos que se repiten cada ciclo mientras el evento está activo.
        Solo actúa una vez por evento y por ciclo."""
        if evento["ultimo_tick"] == ciclo:
            return
        evento["ultimo_tick"] = ciclo
        if evento["tipo"] != "incendio":
            return
        cfg = CONFIG_EVENTOS["incendio"]
        for f, c in evento["zona"]:
            # P4: destruye los recursos presentes
            if recursos is not None:
                recursos.retirar_recursos_por_incendio(f, c)
            # P5: resistencia de construcciones -12 por ciclo
            if aldeas is not None:
                aldeas.aplicar_dano_en_casilla(f, c, cfg["dano_edificios"],
                                               ciclo=ciclo, registro=registro)

    def avanzar_ciclo(self, ciclo, mapa=None, poblacion=None, recursos=None,
                      aldeas=None, registro=None, aplicar_dano_criaturas=False,
                      al_morir=None):
        """LLAMAR UNA VEZ POR CICLO (P1). Termina eventos vencidos, sortea
        nuevos, aplica los efectos del ciclo y devuelve la lista de cambios:
        [{'accion': 'inicio'|'fin', 'tipo':..., 'nombre':..., 'ciclo':...}]

        aplicar_dano_criaturas=True solo si P6 NO aplica el daño ambiental
        (evita duplicarlo). al_morir(criatura, causa) opcional."""
        if type(ciclo) is not int or ciclo < 0:
            raise ValueError("ERROR INTERNO: ciclo debe ser entero >= 0")
        self._termino_este_ciclo = set()
        cambios = []

        # 1) terminar eventos vencidos
        for tipo in list(self.activos):
            if ciclo >= self.activos[tipo]["fin"]:
                nombre = self.activos[tipo]["nombre"]
                self.finalizar_evento(tipo, ciclo, registro, poblacion)
                cambios.append({"accion": "fin", "tipo": tipo, "nombre": nombre, "ciclo": ciclo})

        # 2) sorteo de un evento nuevo
        nuevo = self._sortear_evento(ciclo)
        if nuevo is not None:
            ev = self.iniciar_evento(nuevo, ciclo, mapa, recursos, aldeas, registro)
            if ev is not None:
                cambios.append({"accion": "inicio", "tipo": nuevo,
                                "nombre": ev["nombre"], "ciclo": ciclo})

        # 3) efectos del ciclo para todos los eventos activos
        for tipo in list(self.activos):
            self._aplicar_efectos_ciclo(self.activos[tipo], ciclo, mapa, recursos,
                                        aldeas, registro)

        # 4) Luna de sangre: sincronizar bonos de los lobos
        if poblacion is not None:
            self.sincronizar_luna_sangre(poblacion)

        # 5) (opcional) daño/curación ambiental directo a criaturas
        if aplicar_dano_criaturas and poblacion is not None and mapa is not None:
            self.aplicar_dano_ambiental_poblacion(poblacion, mapa, al_morir)

        return cambios

    # ------------------------------------------------------------------
    # LUNA DE SANGRE: +5 ataque / +2 defensa a lobos en forma bestia
    # ------------------------------------------------------------------
    def bonos_luna_sangre(self, criatura):
        """(bono_ataque, bono_defensa) que corresponden AHORA a la criatura."""
        if (self.luna_sangre_activa() and criatura.vivo
                and criatura.linaje == "hombre_lobo" and criatura.forma == "bestia"):
            return BONOS_LUNA_SANGRE["ataque"], BONOS_LUNA_SANGRE["defensa"]
        return 0, 0

    def sincronizar_luna_sangre(self, poblacion):
        """Idempotente. Aplica el bono a lobos bestia mientras dure la Luna de
        sangre y lo retira si termina el evento, el lobo muere o vuelve a forma
        humana. No toca los bonos permanentes de evolución (P10).
        Llamar DESPUÉS de la transformación de P6."""
        aplicados = 0
        retirados = 0
        for c in poblacion.criaturas:
            if c.linaje != "hombre_lobo":
                continue
            previo = self._bonos_luna.pop(c.id, None)
            if previo is not None:
                # Solo restamos si el valor sigue siendo el que dejamos
                # (cambiar_forma/evolucionar recalculan y ya lo borraron).
                if c.ataque == previo["ataque_final"]:
                    c.ataque -= previo["da"]
                if c.defensa == previo["defensa_final"]:
                    c.defensa -= previo["dd"]
                retirados += 1
            da, dd = self.bonos_luna_sangre(c)
            if da or dd:
                c.ataque += da
                c.defensa += dd
                self._bonos_luna[c.id] = {"da": da, "dd": dd,
                                          "ataque_final": c.ataque,
                                          "defensa_final": c.defensa}
                aplicados += 1
        return {"aplicados": aplicados, "retirados": retirados}

    # ------------------------------------------------------------------
    # DAÑO / CURACIÓN AMBIENTAL (consulta para P6; aplicación opcional)
    # ------------------------------------------------------------------
    @staticmethod
    def dano_ambiental_criatura(criatura, efectos):
        """Cambio de salud por ciclo (negativo = daño) según las marcas de la
        casilla. efectos = diccionario de la casilla, p. ej. {'fuego': 2}.
        Fuego: -12 vampiro/lobo, -18 zombi. Contaminación: +5 zombi, -5 otros."""
        cambio = 0
        if "fuego" in efectos:
            cambio -= CONFIG_EVENTOS["incendio"]["dano_criaturas"][criatura.linaje]
        if "contaminacion" in efectos:
            cambio += CONTAMINACION_SALUD[criatura.linaje]
        return cambio

    def aplicar_dano_ambiental_poblacion(self, poblacion, mapa, al_morir=None):
        """Aplica el cambio de salud anterior a todas las criaturas vivas.
        USAR SOLO si P6 no lo hace. Devuelve {id: cambio}."""
        if self.consultar_efectos is None:
            raise RuntimeError("Falta conectar consultar_efectos de P2.")

        resultado = {}
        for c in poblacion.obtener_vivas():
            if c.posicion is None:
                continue
            f, col = c.posicion
            efectos = self.consultar_efectos(mapa, f, col)
            cambio = self.dano_ambiental_criatura(c, efectos)
            if cambio == 0:
                continue
            c.modificar_salud(cambio)
            resultado[c.id] = cambio
            if not c.vivo and al_morir is not None:
                causa = "incendio" if "fuego" in efectos else "contaminacion"
                al_morir(c, causa)
        return resultado