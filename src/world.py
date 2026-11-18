from config import TAMANO_MAPA, TERRENOS, EFECTOS


def crear_mapa():
    """
    Crea el mapa de NOCTURNA de 20 filas y 20 columnas.
    El mapa es una lista de listas donde cada casilla es un diccionario.
    """
    mapa = []

    for numeroFila in range(TAMANO_MAPA):
        fila = []
        for numeroColumna in range(TAMANO_MAPA):
            casilla = {
                "terreno": "sin definir",
                "ocupante_id": None,
                "efectos": {},
            }
            fila.append(casilla)
        mapa.append(fila)

    return mapa


def dentro_del_mapa(mapa, fila, columna):
    """Comprueba si las coordenadas existen dentro de la matriz del mapa."""
    if type(fila) is not int or type(columna) is not int:
        return False
    if fila < 0 or fila >= len(mapa):
        return False
    if columna < 0 or columna >= len(mapa[fila]):
        return False
    return True


def obtener_casilla(mapa, fila, columna):
    """Recibe el mapa y coordenadas; devuelve el diccionario de esa casilla."""
    if not dentro_del_mapa(mapa, fila, columna):
        raise ValueError("ERROR INTERNO: casilla fuera del mapa")
    return mapa[fila][columna]


def asignar_terreno(mapa, fila, columna, terreno):
    """Cambia solo la clave 'terreno' de la casilla seleccionada."""
    if terreno not in TERRENOS:
        raise ValueError("ERROR INTERNO: terreno no reconocido: " + str(terreno))
    casilla = obtener_casilla(mapa, fila, columna)
    casilla["terreno"] = terreno
    return casilla


def asignar_zona_rectangular(mapa, fila_inicio, columna_inicio, fila_fin, columna_fin, terreno):
    """Cambia el terreno de una zona rectangular completa."""
    if fila_inicio > fila_fin or columna_inicio > columna_fin:
        raise ValueError("ERROR INTERNO: inicio de zona posterior al final")
    if not dentro_del_mapa(mapa, fila_inicio, columna_inicio):
        raise ValueError("ERROR INTERNO: inicio de zona fuera del mapa")
    if not dentro_del_mapa(mapa, fila_fin, columna_fin):
        raise ValueError("ERROR INTERNO: final de zona fuera del mapa")
    if terreno not in TERRENOS:
        raise ValueError("ERROR INTERNO: terreno no reconocido: " + str(terreno))

    for fila in range(fila_inicio, fila_fin + 1):
        for columna in range(columna_inicio, columna_fin + 1):
            asignar_terreno(mapa, fila, columna, terreno)


def casilla_disponible(mapa, fila, columna):
    """Comprueba si una posición del mapa existe y si está desocupada."""
    if not dentro_del_mapa(mapa, fila, columna):
        return False
    casilla = obtener_casilla(mapa, fila, columna)
    return casilla["ocupante_id"] is None


def obtener_vecinos(mapa, fila, columna, solo_disponibles=False):
    """
    Obtiene las posiciones vecinas (arriba, abajo, izquierda, derecha).
    Devuelve una lista de tuplas (fila, columna).
    """
    obtener_casilla(mapa, fila, columna)

    posiblesVecinos = [
        (fila - 1, columna),  # Arriba
        (fila + 1, columna),  # Abajo
        (fila, columna - 1),  # Izquierda
        (fila, columna + 1),  # Derecha
    ]

    vecinos = []
    for filaVecina, columnaVecina in posiblesVecinos:
        if solo_disponibles:
            permitir = casilla_disponible(mapa, filaVecina, columnaVecina)
        else:
            permitir = dentro_del_mapa(mapa, filaVecina, columnaVecina)

        if permitir:
            vecinos.append((filaVecina, columnaVecina))

    return vecinos


def ubicar_criatura(mapa, criatura, fila, columna):
    """Coloca una criatura en la casilla sincronizando el mapa y el objeto."""
    if not criatura.vivo:
        return False

    if criatura.posicion == (fila, columna):
        if not dentro_del_mapa(mapa, fila, columna):
            return False
        return obtener_casilla(mapa, fila, columna)["ocupante_id"] == criatura.id

    if not casilla_disponible(mapa, fila, columna):
        return False

    posicionAnterior = criatura.posicion
    if posicionAnterior is not None:
        filaAnterior, columnaAnterior = posicionAnterior
        if not dentro_del_mapa(mapa, filaAnterior, columnaAnterior):
            return False
        casillaAnterior = obtener_casilla(mapa, filaAnterior, columnaAnterior)
        if casillaAnterior["ocupante_id"] != criatura.id:
            return False
        casillaAnterior["ocupante_id"] = None

    casillaNueva = obtener_casilla(mapa, fila, columna)
    casillaNueva["ocupante_id"] = criatura.id
    criatura.posicion = (fila, columna)
    return True


def liberar_casilla(mapa, criatura):
    """Quita la ocupación cuando una criatura muere o deja un lugar."""
    if criatura.posicion is None:
        return False
    fila, columna = criatura.posicion
    if not dentro_del_mapa(mapa, fila, columna):
        return False
    casilla = obtener_casilla(mapa, fila, columna)
    if casilla["ocupante_id"] != criatura.id:
        return False
    casilla["ocupante_id"] = None
    return True


def marcar_efecto(mapa, fila, columna, efecto, duracion):
    """Agrega una marca temporal de efecto ambiental a una casilla."""
    if efecto not in EFECTOS:
        raise ValueError("ERROR INTERNO: efecto desconocido: " + str(efecto))
    if type(duracion) is not int or duracion <= 0:
        raise ValueError("ERROR INTERNO: la duración debe ser entero positivo")

    casilla = obtener_casilla(mapa, fila, columna)
    casilla["efectos"][efecto] = duracion
    return casilla["efectos"][efecto]


def consultar_efectos(mapa, fila, columna):
    """Retorna una copia del diccionario de efectos de la casilla."""
    casilla = obtener_casilla(mapa, fila, columna)
    return casilla["efectos"].copy()


def quitar_efecto(mapa, fila, columna, efecto):
    """Borra una marca ambiental de una casilla."""
    casilla = obtener_casilla(mapa, fila, columna)
    if efecto in casilla["efectos"]:
        del casilla["efectos"][efecto]
        return True
    return False


def avanzar_efectos(mapa):
    """Descuenta una unidad de tiempo a todas las marcas ambientales del mapa."""
    for fila in mapa:
        for casilla in fila:
            efectosActivos = list(casilla["efectos"].keys())
            for nombreEfecto in efectosActivos:
                casilla["efectos"][nombreEfecto] -= 1
                if casilla["efectos"][nombreEfecto] <= 0:
                    del casilla["efectos"][nombreEfecto]