"""
NOCTURNA: El Despertar del Eclipse
P8 - Rutas, movimiento y ejecución de acciones.

Este módulo contiene la lógica de navegación y ejecución de acciones.
La interfaz gráfica debe consumir sus resultados, sin implementar aquí
ningún elemento visual.
"""

from collections import deque

from world import (
    dentro_del_mapa,
    obtener_casilla,
    obtener_vecinos,
    casilla_disponible,
    ubicar_criatura,
)

# P8: rutas, movimiento y ejecucion de acciones

# Parametros del documento de reglas (se ajustan aqui, no en las funciones)
MOVIMIENTO_POR_ACCION = 1        # casillas por accion (regla 6.1)
COSTO_ENERGIA_MOVER = 2          # energia por casilla recorrida (regla 6.1)
SACIEDAD_POR_UNIDAD = 30         # saciedad por unidad de alimento (regla 5.3)
RADIO_DETECCION_ACTIVO = True    # limita busquedas a la deteccion (regla 2)
TERRENOS_BLOQUEADOS = set()      # PENDIENTE: las reglas no definen ninguno
EXPLORAR_SI_NO_HAY_RUTA = True   # sin recursos a la vista, explora


def distancia(a, b):
    # Distancia Manhattan entre dos posiciones (fila, columna).
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def es_transitable(mapa, fila, columna):
    # True si la casilla existe y su terreno no esta bloqueado.
    if not dentro_del_mapa(mapa, fila, columna):
        return False
    return obtener_casilla(mapa, fila, columna)["terreno"] not in TERRENOS_BLOQUEADOS


def _limitar_por_deteccion(criatura, posiciones):
    # Deja solo las posiciones dentro de la deteccion de la criatura.
    if not RADIO_DETECCION_ACTIVO:
        return set(posiciones)
    return {p for p in posiciones if distancia(criatura.posicion, p) <= criatura.deteccion}


def buscar_ruta(mapa, origen, destinos, permitir_destino_ocupado=False):
    # BFS: camino mas corto hasta el destino mas cercano.
    # Devuelve lista de pasos (sin el origen), [] si ya esta en un destino
    # o None si no hay camino.
    destinos = set(destinos)
    if not dentro_del_mapa(mapa, origen[0], origen[1]):
        raise ValueError("ERROR INTERNO: el origen esta fuera del mapa")
    if origen in destinos:
        return []

    padres = {origen: None}   # casilla visitada y de donde se llego
    cola = deque([origen])
    while cola:
        actual = cola.popleft()
        for vecino in obtener_vecinos(mapa, actual[0], actual[1]):
            if vecino in padres:
                continue
            if not es_transitable(mapa, vecino[0], vecino[1]):
                continue
            es_destino = vecino in destinos
            libre = casilla_disponible(mapa, vecino[0], vecino[1])
            if not libre and not (es_destino and permitir_destino_ocupado):
                continue
            padres[vecino] = actual
            if es_destino:
                # El primer destino encontrado es el mas cercano.
                ruta = [vecino]
                anterior = padres[vecino]
                while anterior != origen:
                    ruta.append(anterior)
                    anterior = padres[anterior]
                ruta.reverse()
                return ruta
            cola.append(vecino)
    return None


def _cadaver_compatible(criatura, cadaver):
    # Misma regla que consumir_cadaver de P4: zombi para vampiro y lobo, o del propio linaje.
    if cadaver["linaje"] == "zombi" and criatura.linaje in ("vampiro", "hombre_lobo"):
        return True
    return cadaver["linaje"] == criatura.linaje


def _cadaveres_compatibles(criatura, recursos):
    # Casillas con un cadaver que esta criatura puede consumir.
    return {c["posicion"] for c in getattr(recursos, "cadáveres", [])
            if _cadaver_compatible(criatura, c)}


def buscar_alimento(mapa, criatura, recursos):
    # Ruta a la fuente de alimento compatible o al cadaver compatible mas cercano, o None.
    if criatura.posicion is None:
        return None
    destinos = {pos for pos, datos in recursos.fuentes_mapa.items()
                if datos["cantidad"] > 0
                and recursos.es_alimento_compatible(criatura.linaje, datos["tipo"])}
    destinos |= _cadaveres_compatibles(criatura, recursos)
    destinos = _limitar_por_deteccion(criatura, destinos)
    if not destinos:
        return None
    return buscar_ruta(mapa, criatura.posicion, destinos)


def buscar_antidoto(mapa, criatura, recursos):
    # Ruta al antidoto disponible mas cercano dentro de la deteccion, o None.
    if criatura.posicion is None:
        return None
    destinos = {a["posicion"] for a in getattr(recursos, "antidotos", []) if a["cantidad"] > 0}
    destinos = _limitar_por_deteccion(criatura, destinos)
    if not destinos:
        return None
    return buscar_ruta(mapa, criatura.posicion, destinos)


def puede_alimentarse_aqui(criatura, recursos):
    # True si puede comer ya: hay reserva, fuente compatible o cadaver compatible en su casilla.
    # Sirve para el dato en_fuente de P7 (leer_situacion).
    if criatura.posicion is None:
        return False
    if recursos.consultar_reserva(criatura.linaje, "alimento") >= 1:
        return True
    fuente = recursos.consultar_fuente(criatura.posicion[0], criatura.posicion[1])
    if (fuente is not None and fuente["cantidad"] > 0
            and recursos.es_alimento_compatible(criatura.linaje, fuente["tipo"])):
        return True
    return criatura.posicion in _cadaveres_compatibles(criatura, recursos)


def buscar_materiales(mapa, criatura, recursos):
    # Ruta a la fuente de materiales mas cercana, o None.
    if criatura.posicion is None:
        return None
    destinos = {pos for pos, datos in recursos.fuentes_mapa.items()
                if datos["cantidad"] > 0 and datos["tipo"] == "materiales"}
    destinos = _limitar_por_deteccion(criatura, destinos)
    if not destinos:
        return None
    return buscar_ruta(mapa, criatura.posicion, destinos)


def buscar_recurso(mapa, criatura, recursos):
    # Ruta a la fuente mas cercana de materiales o de alimento compatible.
    if criatura.posicion is None:
        return None
    destinos = {pos for pos, datos in recursos.fuentes_mapa.items()
                if datos["cantidad"] > 0
                and (datos["tipo"] == "materiales"
                     or recursos.es_alimento_compatible(criatura.linaje, datos["tipo"]))}
    destinos = _limitar_por_deteccion(criatura, destinos)
    if not destinos:
        return None
    return buscar_ruta(mapa, criatura.posicion, destinos)


def enemigos_visibles(criatura, poblacion):
    # Criaturas vivas de otro linaje dentro de la deteccion.
    lista = []
    for otra in poblacion.obtener_vivas():
        if otra.linaje == criatura.linaje or otra.posicion is None:
            continue
        if RADIO_DETECCION_ACTIVO and distancia(criatura.posicion, otra.posicion) > criatura.deteccion:
            continue
        lista.append(otra)
    return lista


def prioridad_objetivo(cazador, presa):
    """Asigna preferencias de búsqueda entre linajes enemigos.

    El hombre lobo humano puede defenderse o aprovechar un combate
    favorable, pero no recibe la prioridad de caza de su forma bestial.
    La evaluación de riesgo determina después si persigue o evita al rival.
    """
    if presa.linaje == cazador.linaje:
        return None
    if cazador.linaje in ("vampiro", "zombi"):
        presa_humana = presa.linaje == "hombre_lobo" and presa.forma == "humana"
        return 0 if presa_humana else 1
    if cazador.linaje == "hombre_lobo":
        if cazador.forma == "bestia":
            return 0 if presa.linaje == "vampiro" else 1
        return 1
    return None


def buscar_enemigo(mapa, criatura, poblacion):
    """Selecciona enemigos que la criatura puede enfrentar con ventaja.

    La amenaza desfavorable permanece visible para la decisión de huida,
    pero no se convierte en un objetivo de persecución automática.
    Los lobos humanos pueden atacar en defensa propia cuando el cálculo
    de supervivencia resulta favorable.
    """
    if criatura.posicion is None:
        return None
    visibles = [enemigo for enemigo in enemigos_visibles(criatura, poblacion)
                if evaluar_ventaja_combate(criatura, enemigo)]
    for nivel in (0, 1):
        for otra in visibles:
            if (prioridad_objetivo(criatura, otra) == nivel
                    and distancia(criatura.posicion, otra.posicion) == 1):
                return {"ruta": [], "objetivo_id": otra.id, "prioridad": nivel}
    for nivel in (0, 1):
        adyacentes = {}
        for otra in visibles:
            if prioridad_objetivo(criatura, otra) != nivel:
                continue
            for vecino in obtener_vecinos(mapa, *otra.posicion):
                if (es_transitable(mapa, *vecino)
                        and (vecino == criatura.posicion
                             or casilla_disponible(mapa, *vecino))):
                    adyacentes.setdefault(vecino, otra.id)
        if not adyacentes:
            continue
        ruta = buscar_ruta(mapa, criatura.posicion, set(adyacentes))
        if ruta is None:
            continue
        destino = ruta[-1] if ruta else criatura.posicion
        return {"ruta": ruta, "objetivo_id": adyacentes[destino], "prioridad": nivel}
    return None


def buscar_refugio(mapa, criatura, aldeas, permitir_destino_ocupado=False):
    """Busca la casilla accesible más cercana del área de alojamiento.

    La capacidad declarada por P5 determina el número mínimo de casillas
    disponibles alrededor de cada construcción. Una ruta nunca termina en
    una casilla ocupada por otra criatura. Las plazas de P5 limitan el
    alojamiento independientemente de los puntos libres del perímetro.
    """
    if criatura.posicion is None or aldeas is None:
        return None
    construccion = aldeas.obtener_refugio_disponible_linaje(criatura.linaje)
    if construccion is None or not construccion["existe"]:
        return None
    centro = construccion["casilla"]
    radio = radio_acceso_construccion(construccion)
    destinos = set()
    for fila in range(max(0, centro[0] - radio), min(len(mapa), centro[0] + radio + 1)):
        for columna in range(max(0, centro[1] - radio), min(len(mapa[fila]), centro[1] + radio + 1)):
            pos = (fila, columna)
            if (distancia(pos, centro) <= radio
                    and es_transitable(mapa, fila, columna)
                    and (pos == criatura.posicion or casilla_disponible(mapa, fila, columna))):
                destinos.add(pos)
    if not destinos:
        return None
    return buscar_ruta(mapa, criatura.posicion, destinos, permitir_destino_ocupado=False)


def intentar_mover(mapa, criatura, ruta, pasos_max=None):
    # Avanza por la ruta hasta pasos_max casillas, cobrando energia por casilla.
    # Devuelve {"movio", "pasos", "posicion", "llego", "motivo"}.
    if pasos_max is None:
        pasos_max = MOVIMIENTO_POR_ACCION
    res = {"movio": False, "pasos": 0, "posicion": criatura.posicion,
           "llego": False, "motivo": ""}
    if not criatura.vivo:
        res["motivo"] = "la criatura esta muerta"
        return res
    if criatura.posicion is None:
        res["motivo"] = "la criatura no tiene posicion"
        return res
    if not ruta:
        res["llego"] = True
        res["motivo"] = "ya estaba en el destino"
        return res

    pasos = 0
    for siguiente in ruta[:pasos_max]:
        if COSTO_ENERGIA_MOVER is not None and criatura.energia < COSTO_ENERGIA_MOVER:
            res["motivo"] = "energia insuficiente"
            break
        if distancia(criatura.posicion, siguiente) != 1:
            res["motivo"] = "la ruta no es contigua a la posicion actual"
            break
        if not es_transitable(mapa, siguiente[0], siguiente[1]):
            res["motivo"] = "terreno bloqueado"
            break
        if not ubicar_criatura(mapa, criatura, siguiente[0], siguiente[1]):
            res["motivo"] = "casilla ocupada o invalida"
            break
        pasos += 1
        if COSTO_ENERGIA_MOVER is not None:
            criatura.modificar_energia(-COSTO_ENERGIA_MOVER)

    res["pasos"] = pasos
    res["movio"] = pasos > 0
    res["posicion"] = criatura.posicion
    res["llego"] = pasos == len(ruta)
    if pasos == pasos_max and not res["llego"]:
        res["motivo"] = "limite de casillas por accion"
    return res


class EjecutorAcciones:
    # Ejecuta la accion del estado AFD de cada criatura (una por ciclo).
    # ultimo_ciclo_accion: {id: ciclo en que actuo}
    # visitas: {id: {posicion: veces}} para explorar

    def __init__(self):
        self.ultimo_ciclo_accion = {}
        self.visitas = {}

    def puede_actuar(self, criatura, ciclo):
        # True si esta viva y no actuo en este ciclo.
        return criatura.vivo and self.ultimo_ciclo_accion.get(criatura.id) != ciclo

    def _resultado(self, criatura, estado, ok, detalle, movimiento=None, externo=None):
        # externo: respuesta del modulo de otro compañero (P9), por si P1 la necesita.
        return {"id": criatura.id, "estado": estado, "ok": ok, "detalle": detalle,
                "movimiento": movimiento, "posicion": criatura.posicion, "externo": externo}

    def _explorar(self, mapa, criatura):
        # Paso a la vecina libre menos visitada, sin azar (desempate rotado por ID para dispersar).
        visitas = self.visitas.setdefault(criatura.id, {})
        visitas[criatura.posicion] = visitas.get(criatura.posicion, 0) + 1
        total = {"movio": False, "pasos": 0, "posicion": criatura.posicion,
                 "llego": False, "motivo": "sin casillas libres"}
        for _ in range(MOVIMIENTO_POR_ACCION):
            vecinos = obtener_vecinos(mapa, criatura.posicion[0], criatura.posicion[1])
            if vecinos:
                desfase = getattr(criatura, "id", 0) % len(vecinos)
                vecinos = vecinos[desfase:] + vecinos[:desfase]
            candidatas = [v for v in vecinos
                          if es_transitable(mapa, v[0], v[1]) and casilla_disponible(mapa, v[0], v[1])]
            if not candidatas:
                break
            mejor = min(candidatas, key=lambda v: visitas.get(v, 0))
            paso = intentar_mover(mapa, criatura, [mejor], 1)
            if not paso["movio"]:
                total["motivo"] = paso["motivo"]
                break
            visitas[criatura.posicion] = visitas.get(criatura.posicion, 0) + 1
            total.update(movio=True, pasos=total["pasos"] + 1,
                         posicion=criatura.posicion, motivo="")
        return total

    def _huir(self, mapa, criatura, poblacion):
        # Se aleja del enemigo mas cercano; si ninguna casilla mejora, no se mueve.
        enemigos = enemigos_visibles(criatura, poblacion)
        if not enemigos:
            return None

        def dmin(pos):
            return min(distancia(pos, e.posicion) for e in enemigos)

        total = {"movio": False, "pasos": 0, "posicion": criatura.posicion,
                 "llego": False, "motivo": "ninguna casilla aleja de los enemigos"}
        for _ in range(MOVIMIENTO_POR_ACCION):
            candidatas = [v for v in obtener_vecinos(mapa, criatura.posicion[0], criatura.posicion[1])
                          if es_transitable(mapa, v[0], v[1]) and casilla_disponible(mapa, v[0], v[1])]
            if not candidatas:
                break
            mejor = max(candidatas, key=dmin)
            if dmin(mejor) <= dmin(criatura.posicion):
                break
            paso = intentar_mover(mapa, criatura, [mejor], 1)
            if not paso["movio"]:
                total["motivo"] = paso["motivo"]
                break
            total.update(movio=True, pasos=total["pasos"] + 1,
                         posicion=criatura.posicion, motivo="")
        return total

    def ejecutar_accion(self, criatura, ciclo, mapa, poblacion, recursos=None, aldeas=None,
                        combate=None, registro=None):
        # Ejecuta UNA accion segun criatura.estado_afd.
        # Devuelve {"id", "estado", "ok", "detalle", "movimiento", "posicion", "externo"}.
        # combate: ControlCombate de P9. registro: RegistroMundo de P3 (opcional).
        estado = criatura.estado_afd
        if not criatura.vivo:
            return self._resultado(criatura, estado, False, "la criatura esta muerta")
        if criatura.posicion is None:
            return self._resultado(criatura, estado, False, "la criatura no tiene posicion")
        if not self.puede_actuar(criatura, ciclo):
            return self._resultado(criatura, estado, False,
                                   "ya ejecuto su accion principal en este ciclo")
        self.ultimo_ciclo_accion[criatura.id] = ciclo   # se marca antes de actuar

        if estado == "EXPLORAR":
            # Una fuente compatible bajo la criatura permite recolectar sin
            # desplazamientos adicionales, incluso durante la exploración.
            if recursos is not None:
                f, c = criatura.posicion
                fuente = recursos.consultar_fuente(f, c)
                if (fuente is not None and fuente["cantidad"] > 0
                        and (fuente["tipo"] == "materiales"
                             or recursos.es_alimento_compatible(criatura.linaje, fuente["tipo"]))):
                    cantidad = recursos.recolectar_de_fuente(f, c, criatura.linaje, 1)
                    return self._resultado(criatura, estado, cantidad > 0,
                                           "exploracion: recurso recolectado")
            mov = self._explorar(mapa, criatura)
            return self._resultado(criatura, estado, True, "exploro", mov)

        if estado == "BUSCAR_ALIMENTO":
            if recursos is None:
                return self._resultado(criatura, estado, False, "falta el modulo de recursos (P4)")
            ruta = buscar_alimento(mapa, criatura, recursos)
            if ruta is None:
                if EXPLORAR_SI_NO_HAY_RUTA:
                    mov = self._explorar(mapa, criatura)
                    return self._resultado(criatura, estado, True, "sin ruta a alimento: exploro", mov)
                return self._resultado(criatura, estado, False, "sin ruta a alimento")
            mov = intentar_mover(mapa, criatura, ruta)
            return self._resultado(criatura, estado, True, "avanza hacia el alimento", mov)

        if estado == "ALIMENTARSE":
            # Consume 1 unidad de la reserva (regla 5.2) y sube la saciedad (regla 5.3).
            if recursos is None:
                return self._resultado(criatura, estado, False, "falta el modulo de recursos (P4)")
            linaje = criatura.linaje
            nota = ""
            if combate is not None and criatura.posicion in _cadaveres_compatibles(criatura, recursos):
                # Cadaver en su casilla: P4 da +40 de saciedad y P9 decide el veneno.
                r = combate.consumir_cadaver(criatura, recursos, ciclo, registro)
                if r["ok"]:
                    nota = " y se envenena" if r.get("envenenado_ahora") else ""
                    return self._resultado(criatura, estado, True, "come un cadaver" + nota, externo=r)
            if recursos.consultar_reserva(linaje, "alimento") < 1:
                # Reserva vacia: si esta sobre una fuente compatible, recolecta 1 antes.
                f, c = criatura.posicion
                fuente = recursos.consultar_fuente(f, c)
                if (fuente is not None and fuente["cantidad"] > 0
                        and recursos.es_alimento_compatible(linaje, fuente["tipo"])):
                    recursos.recolectar_de_fuente(f, c, linaje, 1)
                    nota = " (recolecto 1 unidad de la fuente)"
            if not recursos.consumir_de_reserva(linaje, "alimento", 1):
                return self._resultado(criatura, estado, False, "no hay alimento en la reserva ni en la casilla")
            if SACIEDAD_POR_UNIDAD is not None:
                criatura.modificar_saciedad(SACIEDAD_POR_UNIDAD)
            return self._resultado(criatura, estado, True, "se alimenta: 1 unidad de la reserva" + nota)

        if estado == "RECOLECTAR":
            # Suma a la reserva: materiales o alimento compatible.
            if recursos is None:
                return self._resultado(criatura, estado, False, "falta el modulo de recursos (P4)")
            f, c = criatura.posicion
            fuente = recursos.consultar_fuente(f, c)
            if (fuente is not None and fuente["cantidad"] > 0
                    and (fuente["tipo"] == "materiales"
                         or recursos.es_alimento_compatible(criatura.linaje, fuente["tipo"]))):
                extraidas = recursos.recolectar_de_fuente(f, c, criatura.linaje, 1)
                return self._resultado(criatura, estado, extraidas > 0,
                                       "unidades recolectadas: " + str(extraidas))
            ruta = buscar_recurso(mapa, criatura, recursos)
            if ruta is None:
                if EXPLORAR_SI_NO_HAY_RUTA:
                    mov = self._explorar(mapa, criatura)
                    return self._resultado(criatura, estado, True, "sin recursos a la vista: exploro", mov)
                return self._resultado(criatura, estado, False, "sin recursos a la vista")
            mov = intentar_mover(mapa, criatura, ruta)
            return self._resultado(criatura, estado, True, "avanza hacia un recurso", mov)

        if estado == "BUSCAR_REFUGIO":
            if aldeas is None:
                return self._resultado(criatura, estado, False, "falta el modulo de aldeas (P5)")
            if aldeas.esta_en_refugio(criatura):
                return self._resultado(criatura, estado, True, "ya esta en refugio")
            mov = None
            if not _en_acceso_refugio(mapa, criatura, aldeas):
                ruta = buscar_refugio(mapa, criatura, aldeas)
                if ruta is None:
                    return self._resultado(criatura, estado, False, "sin ruta a la aldea o al refugio")
                mov = intentar_mover(mapa, criatura, ruta)
            if _en_acceso_refugio(mapa, criatura, aldeas):
                ok, mensaje = aldeas.alojar_criatura(criatura)
                return self._resultado(criatura, estado, ok, mensaje, mov)
            return self._resultado(criatura, estado, True, "avanza hacia el refugio", mov)

        if estado == "DESCANSAR":
            # La energia que recupera la calcula P6; aqui solo se verifica el refugio.
            if aldeas is not None and _en_acceso_refugio(mapa, criatura, aldeas):
                if aldeas.esta_en_refugio(criatura):
                    return self._resultado(criatura, estado, True, "descansa en refugio")
                ok, mensaje = aldeas.alojar_criatura(criatura)
                return self._resultado(criatura, estado, ok, mensaje)
            return self._resultado(criatura, estado, True, "descansa en el lugar (sin refugio)")

        if estado == "PERSEGUIR":
            # Solo se persiguen criaturas con pronóstico favorable de combate.
            # Si no las hay, se permite aproximarse a una construcción enemiga.
            hallado = buscar_enemigo(mapa, criatura, poblacion)
            if hallado is not None:
                if not hallado["ruta"]:
                    return self._resultado(criatura, estado, True,
                                           "ya esta junto al enemigo " + str(hallado["objetivo_id"]))
                mov = intentar_mover(mapa, criatura, hallado["ruta"])
                return self._resultado(criatura, estado, mov["movio"],
                                       "avanza hacia el enemigo " + str(hallado["objetivo_id"]), mov)
            edificio = buscar_construccion_enemiga(mapa, criatura, aldeas)
            if edificio is None:
                return self._resultado(criatura, estado, False,
                                       "sin objetivo enemigo o construccion alcanzable")
            if not edificio["ruta"]:
                return self._resultado(criatura, estado, True,
                                       "ya esta junto a una construccion enemiga")
            mov = intentar_mover(mapa, criatura, edificio["ruta"])
            return self._resultado(criatura, estado, mov["movio"],
                                   "se aproxima a construccion enemiga", mov)

        if estado == "HUIR":
            mov = self._huir(mapa, criatura, poblacion)
            if mov is None:
                return self._resultado(criatura, estado, True, "no hay enemigos visibles")
            return self._resultado(criatura, estado, True, "huye", mov)

        if estado == "ATACAR":
            if combate is None or recursos is None:
                return self._resultado(criatura, estado, False, "falta combate (P9) o recursos (P4)")
            hallado = buscar_enemigo(mapa, criatura, poblacion)
            if hallado is not None and not hallado["ruta"]:
                objetivo = poblacion.buscar_por_id(hallado["objetivo_id"])
                r = combate.atacar(mapa, criatura, objetivo, ciclo, recursos, registro)
                return self._resultado(criatura, estado, r["ok"], r["motivo"], externo=r)
            # El ataque a construcciones reutiliza las validaciones de P9:
            # alcance 1, energía de ataque y un solo golpe por ciclo.
            edificio = buscar_construccion_enemiga(mapa, criatura, aldeas)
            if edificio is None or edificio["ruta"]:
                return self._resultado(criatura, estado, False, "no hay objetivo adyacente")
            fila, columna = edificio["casilla"]
            r = combate.atacar_construccion(
                criatura, fila, columna, aldeas, ciclo,
                dano_estructura=calcular_dano_construccion(criatura),
                registro=registro
            )
            if r["ok"] and registro is not None:
                registro.registrar_acontecimiento(
                    ciclo, "ataque_construccion",
                    f"Criatura {criatura.id} ataco {edificio['tipo']} de {edificio['linaje']} "
                    f"y produjo {r['dano']} de daño",
                    id_unico=f"ataque_edificio_{criatura.id}_{ciclo}"
                )
            # El resultado identifica al edificio para que P1 no aplique
            # XP de eliminación de criaturas a un objetivo estructural.
            r["tipo_objetivo"] = "construccion"
            r["objetivo_linaje"] = edificio["linaje"]
            r["objetivo_casilla"] = edificio["casilla"]
            return self._resultado(criatura, estado, r["ok"], r["motivo"], externo=r)

        if estado == "BUSCAR_CURA":
            if combate is None or recursos is None:
                return self._resultado(criatura, estado, False, "falta combate (P9) o recursos (P4)")
            en_antidoto = any(a["posicion"] == criatura.posicion and a["cantidad"] > 0
                              for a in getattr(recursos, "antidotos", []))
            if en_antidoto:
                r = combate.curar(criatura, recursos, ciclo, registro)
                return self._resultado(criatura, estado, r["ok"], r["motivo"], externo=r)
            ruta = buscar_antidoto(mapa, criatura, recursos)
            if ruta is None:
                if EXPLORAR_SI_NO_HAY_RUTA:
                    mov = self._explorar(mapa, criatura)
                    return self._resultado(criatura, estado, True, "sin antidoto a la vista: exploro", mov)
                return self._resultado(criatura, estado, False, "sin antidoto a la vista")
            mov = intentar_mover(mapa, criatura, ruta)
            return self._resultado(criatura, estado, True, "avanza hacia un antidoto", mov)

        if estado == "CONSTRUIR":
            # Sin aldea: reconstruye desde el refugio provisional o lo construye en su casilla.
            # Con aldea: intenta mejorarla. Costos y requisitos los valida P5.
            if aldeas is None or recursos is None:
                return self._resultado(criatura, estado, False, "falta aldeas (P5) o recursos (P4)")
            linaje = criatura.linaje
            if not aldeas.existe_aldea(linaje):
                if aldeas.existe_refugio_provisional(linaje):
                    refugio = aldeas.consultar_refugio_provisional(linaje)
                    if distancia(criatura.posicion, refugio["casilla"]) > 1:
                        # La transformación del refugio se ejecuta desde el sitio
                        # de construcción, no desde cualquier casilla del mapa.
                        ruta = buscar_refugio(mapa, criatura, aldeas)
                        if ruta is None:
                            return self._resultado(criatura, estado, False,
                                                   "No existe ruta hacia el refugio")
                        mov = intentar_mover(mapa, criatura, ruta)
                        return self._resultado(criatura, estado, mov["movio"],
                                               "Se aproxima al refugio para reconstruir", mov)
                    ok, mensaje = aldeas.reconstruir_aldea(mapa, linaje, recursos,
                                                           ciclo=ciclo, registro=registro,
                                                           poblacion=poblacion)
                else:
                    f, c = criatura.posicion
                    ok, mensaje = aldeas.construir_refugio_provisional(mapa, linaje, f, c, recursos,
                                                                       ciclo=ciclo, registro=registro)
            else:
                ok, mensaje = aldeas.mejorar_aldea(linaje, poblacion, recursos,
                                                   ciclo=ciclo, registro=registro)
            return self._resultado(criatura, estado, ok, mensaje)

        if estado == "MUERTO":
            return self._resultado(criatura, estado, False, "la criatura esta muerta")

        return self._resultado(criatura, estado, False, "estado AFD desconocido: " + str(estado))


# Funciones de navegación, defensa y acceso implementadas en el motor corregido.
FACTOR_DANO_ORDINARIO_CONSTRUCCION = 1

def hay_recurso_cercano(mapa, criatura, recursos):
    # True si esta sobre una fuente valida o ve alguna dentro de su deteccion (para P7).
    if mapa is None or recursos is None or criatura.posicion is None:
        return False
    f, c = criatura.posicion
    fuente = recursos.consultar_fuente(f, c)
    if (fuente is not None and fuente["cantidad"] > 0
            and (fuente["tipo"] == "materiales"
                 or recursos.es_alimento_compatible(criatura.linaje, fuente["tipo"]))):
        return True
    return buscar_recurso(mapa, criatura, recursos) is not None

def evaluar_ventaja_combate(criatura, enemigo):
    """Compara los turnos necesarios para ganar y para ser derrotado.

    Se utiliza la misma fórmula de daño de P9 con los atributos vigentes,
    incluidos bonos y transformaciones. El criterio conservador considera
    favorable el enfrentamiento solo cuando puede derrotarse al enemigo
    en menos golpes de los que este necesita para derrotar a la criatura.
    Este cálculo es una aproximación para elegir conducta, no un combate
    independiente ni una modificación de salud.
    """
    if (not criatura.vivo or not enemigo.vivo
            or criatura.linaje == enemigo.linaje):
        return False
    dano_propio = max(2, criatura.ataque - enemigo.defensa // 2)
    dano_enemigo = max(2, enemigo.ataque - criatura.defensa // 2)
    golpes_para_ganar = (enemigo.salud + dano_propio - 1) // dano_propio
    golpes_para_perder = (criatura.salud + dano_enemigo - 1) // dano_enemigo
    return golpes_para_ganar < golpes_para_perder

def amenaza_superior_cercana(criatura, poblacion, radio=2):
    """Detecta rivales cercanos capaces de derrotar a la criatura.

    La huida se considera una acción preventiva frente a una amenaza
    identificada, siempre que exista energía para desplazarse una casilla.
    """
    if criatura.posicion is None or criatura.energia < COSTO_ENERGIA_MOVER:
        return False
    return any(
        distancia(criatura.posicion, enemigo.posicion) <= radio
        and not evaluar_ventaja_combate(criatura, enemigo)
        for enemigo in enemigos_visibles(criatura, poblacion)
    )

def calcular_dano_construccion(criatura):
    """Calcula el daño ordinario configurado contra una construcción.

    Las aldeas no disponen de atributo defensa. Se aplica como valor
    inicial la fuerza de ataque vigente, con mínimo de dos puntos.
    """
    return max(2, int(criatura.ataque * FACTOR_DANO_ORDINARIO_CONSTRUCCION))

def buscar_construccion_enemiga(mapa, criatura, aldeas):
    """Localiza una aldea o refugio enemigo alcanzable en el radio de detección.

    La ruta termina en una casilla adyacente a la construcción, pues P9
    solo admite ataques a distancia Manhattan igual a uno. Las casillas
    ocupadas no se atraviesan y las construcciones propias se excluyen.
    """
    if (mapa is None or aldeas is None or criatura.posicion is None):
        return None
    candidatos = []
    for construccion in aldeas.listar_construcciones():
        if (not construccion["existe"]
                or construccion["linaje"] == criatura.linaje):
            continue
        centro = construccion["casilla"]
        if (RADIO_DETECCION_ACTIVO
                and distancia(criatura.posicion, centro) > criatura.deteccion):
            continue
        if distancia(criatura.posicion, centro) == 1:
            ruta = []
        else:
            vecinos = {
                pos for pos in obtener_vecinos(mapa, *centro)
                if es_transitable(mapa, *pos)
                and (pos == criatura.posicion or casilla_disponible(mapa, *pos))
            }
            ruta = buscar_ruta(mapa, criatura.posicion, vecinos) if vecinos else None
        if ruta is not None:
            candidatos.append((len(ruta), centro, construccion["linaje"],
                               construccion["tipo"], ruta))
    if not candidatos:
        return None
    _, centro, linaje, tipo, ruta = min(candidatos,
                                      key=lambda datos: (datos[0], datos[1]))
    return {"ruta": ruta, "casilla": centro, "linaje": linaje,
            "tipo": tipo}

def radio_acceso_construccion(construccion):
    """Calcula el perímetro lógico de alojamiento según la capacidad.

    El mapa mantiene un único ocupante por casilla. Las construcciones
    admiten varios residentes porque sus plazas se representan en un área
    de acceso, y no como ocupación simultánea de una sola casilla.
    """
    if construccion is None or not construccion.get("existe", False):
        return 0
    capacidad = construccion.get("capacidad") or 1
    radio = 0
    while 1 + 2 * radio * (radio + 1) < capacidad:
        radio += 1
    return radio

def _en_acceso_refugio(mapa, criatura, aldeas):
    """Comprueba que la criatura se encuentre dentro del perímetro de alojamiento.

    La ocupación real sigue registrada en P5 y respeta la capacidad del
    refugio o de la aldea. Este perímetro únicamente representa el acceso
    físico de las criaturas dentro de la cuadrícula del mapa.
    """
    if aldeas is None or not criatura.vivo or criatura.posicion is None:
        return False
    construccion = aldeas.obtener_refugio_disponible_linaje(criatura.linaje)
    if construccion is None or not construccion["existe"]:
        return False
    return distancia(criatura.posicion, construccion["casilla"]) <= radio_acceso_construccion(construccion)
