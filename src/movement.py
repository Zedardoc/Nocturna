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
    # A quien persigue cada linaje (regla 3).
    # 0 = principal, 1 = secundario, None = no lo persigue.
    if presa.linaje == cazador.linaje:
        return None
    if cazador.linaje in ("vampiro", "zombi"):
        presa_humana = presa.linaje == "hombre_lobo" and presa.forma == "humana"
        return 0 if presa_humana else 1
    if cazador.linaje == "hombre_lobo":
        if cazador.forma != "bestia":
            return None
        return 0 if presa.linaje == "vampiro" else 1
    return None


def buscar_enemigo(mapa, criatura, poblacion):
    # Ruta a una casilla adyacente al objetivo mas cercano (alcance 1).
    # Primero objetivos principales y luego secundarios.
    # Devuelve {"ruta", "objetivo_id", "prioridad"} o None.
    # ruta [] significa que ya esta junto al objetivo.
    if criatura.posicion is None:
        return None
    visibles = enemigos_visibles(criatura, poblacion)
    for nivel in (0, 1):   # si ya hay un objetivo adyacente, no hace falta moverse
        for otra in visibles:
            if prioridad_objetivo(criatura, otra) == nivel and distancia(criatura.posicion, otra.posicion) == 1:
                return {"ruta": [], "objetivo_id": otra.id, "prioridad": nivel}
    for nivel in (0, 1):
        adyacentes = {}   # casilla adyacente y id del objetivo
        for otra in visibles:
            if prioridad_objetivo(criatura, otra) != nivel:
                continue
            for vecino in obtener_vecinos(mapa, otra.posicion[0], otra.posicion[1]):
                if es_transitable(mapa, vecino[0], vecino[1]):
                    adyacentes.setdefault(vecino, otra.id)
        if not adyacentes:
            continue
        ruta = buscar_ruta(mapa, criatura.posicion, set(adyacentes.keys()))
        if ruta is None:
            continue
        destino = ruta[-1] if ruta else criatura.posicion
        return {"ruta": ruta, "objetivo_id": adyacentes[destino], "prioridad": nivel}
    return None


def buscar_refugio(mapa, criatura, aldeas, permitir_destino_ocupado=False):
    # Ruta a la aldea de su linaje o, si fue destruida, a su refugio provisional (P5).
    if criatura.posicion is None:
        return None
    destino = aldeas.obtener_refugio_disponible_linaje(criatura.linaje)
    if destino is None or not destino["existe"]:
        return None
    return buscar_ruta(mapa, criatura.posicion, {destino["casilla"]}, permitir_destino_ocupado)


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
        # Paso a la vecina libre menos visitada, sin azar.
        visitas = self.visitas.setdefault(criatura.id, {})
        visitas[criatura.posicion] = visitas.get(criatura.posicion, 0) + 1
        total = {"movio": False, "pasos": 0, "posicion": criatura.posicion,
                 "llego": False, "motivo": "sin casillas libres"}
        for _ in range(MOVIMIENTO_POR_ACCION):
            candidatas = [v for v in obtener_vecinos(mapa, criatura.posicion[0], criatura.posicion[1])
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
            if not aldeas.criatura_en_casilla_refugio(criatura):
                ruta = buscar_refugio(mapa, criatura, aldeas)
                if ruta is None:
                    return self._resultado(criatura, estado, False, "sin ruta a la aldea o al refugio")
                mov = intentar_mover(mapa, criatura, ruta)
            if aldeas.criatura_en_casilla_refugio(criatura):
                ok, mensaje = aldeas.alojar_criatura(criatura)
                return self._resultado(criatura, estado, ok, mensaje, mov)
            return self._resultado(criatura, estado, True, "avanza hacia el refugio", mov)

        if estado == "DESCANSAR":
            # La energia que recupera la calcula P6; aqui solo se verifica el refugio.
            if aldeas is not None and aldeas.criatura_en_casilla_refugio(criatura):
                if aldeas.esta_en_refugio(criatura):
                    return self._resultado(criatura, estado, True, "descansa en refugio")
                ok, mensaje = aldeas.alojar_criatura(criatura)
                return self._resultado(criatura, estado, ok, mensaje)
            return self._resultado(criatura, estado, True, "descansa en el lugar (sin refugio)")

        if estado == "PERSEGUIR":
            hallado = buscar_enemigo(mapa, criatura, poblacion)
            if hallado is None:
                return self._resultado(criatura, estado, False, "sin enemigo alcanzable")
            if not hallado["ruta"]:
                return self._resultado(criatura, estado, True,
                                       "ya esta junto al enemigo " + str(hallado["objetivo_id"]))
            mov = intentar_mover(mapa, criatura, hallado["ruta"])
            return self._resultado(criatura, estado, True,
                                   "avanza hacia el enemigo " + str(hallado["objetivo_id"]), mov)

        if estado == "HUIR":
            mov = self._huir(mapa, criatura, poblacion)
            if mov is None:
                return self._resultado(criatura, estado, True, "no hay enemigos visibles")
            return self._resultado(criatura, estado, True, "huye", mov)

        if estado == "ATACAR":
            if combate is None or recursos is None:
                return self._resultado(criatura, estado, False, "falta combate (P9) o recursos (P4)")
            hallado = buscar_enemigo(mapa, criatura, poblacion)
            if hallado is None or hallado["ruta"]:
                return self._resultado(criatura, estado, False, "no hay objetivo adyacente")
            objetivo = poblacion.buscar_por_id(hallado["objetivo_id"])
            r = combate.atacar(mapa, criatura, objetivo, ciclo, recursos, registro)
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
                    ok, mensaje = aldeas.reconstruir_aldea(mapa, linaje, recursos,
                                                           ciclo=ciclo, registro=registro)
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