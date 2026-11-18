ATRIBUTOS_INICIALES = {
    "vampiro": {
        "salud_maxima": 90,
        "energia_maxima": 80,
        "saciedad": 70,
        "ataque": 15,
        "defensa": 6,
        "deteccion": 4,
    },
    "hombre_lobo": {
        "salud_maxima": 110,
        "energia_maxima": 80,
        "saciedad": 70,
        "deteccion": 3,
    },
    "zombi": {
        "salud_maxima": 125,
        "energia_maxima": 70,
        "saciedad": 70,
        "ataque": 12,
        "defensa": 9,
        "deteccion": 2,
    },
}

# ESTADISTICAS_LOBO es un diccionario de diccionarios, pero sus claves son las FORMAS
# que puede tener el hombre lobo. Cada forma apunta a su ataque y defensa.
# Ejemplo: ESTADISTICAS_LOBO["bestia"]["ataque"] devuelve 17.
ESTADISTICAS_LOBO = {
    "humana": {"ataque": 9, "defensa": 4},
    "bestia": {"ataque": 17, "defensa": 8},
}

# NOMBRES_ETAPA_I es un diccionario que relaciona cada linaje con el nombre de evolución etapa 1
NOMBRES_ETAPA_I = {
    "vampiro": "Nocturno",
    "hombre_lobo": "Cachorro Feral",
    "zombi": "Errante",
}

# ESTADOS_AFD es un conjunto Set
ESTADOS_AFD = {
    "EXPLORAR", "BUSCAR_ALIMENTO", "ALIMENTARSE", "DESCANSAR",
    "PERSEGUIR", "ATACAR", "HUIR", "BUSCAR_REFUGIO", "BUSCAR_CURA",
    "RECOLECTAR", "CONSTRUIR", "MUERTO",
}

TAMANO_MAPA = 20 #es la cantidad de filas y columnas del mundo (20 x 20).

TERRENOS = {"camino", "bosque", "pantano", "cementerio", "ruinas", "castillo"} # CONJUNTO (set): guarda los nombres de los terrenos usados en el plan.


EFECTOS = {"fuego", "contaminacion", "quemado"} # CONJUNTO de marcas ambientales que una casilla puede tener.

# Sangre -> Vampiros | Carne -> Hombres lobo | Biomasa -> Zombis
COMPATIBILIDAD_ALIMENTO = {
    "vampiro": "sangre",
    "hombre_lobo": "carne",
    "zombi": "biomasa"
}

# Sistema de reservas compartidas por linaje (Inicialmente con 20 alimentos y 10 materiales)
RESERVAS_COMPARTIDAS = {
    "vampiro": {"alimento": 20, "materiales": 10},
    "hombre_lobo": {"alimento": 20, "materiales": 10},
    "zombi": {"alimento": 20, "materiales": 10}
}

NIVEL_INICIAL = 1
NIVEL_MAXIMO = 3

ALDEA_ACEPTA_OTROS_LINAJES = False
# Tablas oficiales pendientes (no inventadas; se llenan tras aprobación escrita
# o se envían explícitamente por parámetro en las llamadas).
RESISTENCIA_POR_NIVEL = {}       # Ej: {1: <int>, 2: <int>, 3: <int>} — PENDIENTE
CAPACIDAD_POR_NIVEL = {}         # Ej: {1: <int>, 2: <int>, 3: <int>} — PENDIENTE
COSTO_MEJORA_POR_NIVEL = {}      # Ej: {2: {"materiales": <int>, "etapa_minima": 2}, ...} — PENDIENTE
COSTO_RECONSTRUCCION = {}        # Ej: {"materiales": <int>} — PENDIENTE
REQUISITOS_NACIMIENTO = {
    "intervalo_ciclos": None,    # int > 0 (PENDIENTE)
    "minimo_vivos": None,        # int >= 1 (PENDIENTE)
    "costo_alimento": None,      # int >= 0 (PENDIENTE)
    "costo_materiales": None,    # int >= 0 (PENDIENTE)
}
PROVISIONAL_CONFIG = {
    "resistencia": None,         # int > 0 (PENDIENTE)
    "capacidad": None,           # int > 0 (PENDIENTE)
    "costo_materiales": None,    # int >= 0 (PENDIENTE)
}

XP_ETAPA_II = 20    # Regla 9.1: etapa I -> II
XP_ETAPA_III = 50   # Regla 9.1: etapa II -> III

# Regla 9.1 (obtencion de experiencia). Las reglas NO dan XP por mejoras de aldea,
# por eso "mejora" vale 0
XP_POR_ACCION = {
    "supervivencia": 1,    # sobrevivir un ciclo
    "alimentacion": 1,     # alimentarse
    "ataque_exitoso": 2,   # ataque exitoso
    "victoria": 4,         # eliminar un enemigo
    "mejora": 0,
}

# Regla 9.1: para evolucionar solo se exige la XP. Las reglas no piden un minimo de
# alimentaciones, asi que el requisito es 0 (el contador sigue existiendo por si se aprueba uno).
REQUISITOS_ETAPA = {
    2: {"xp": XP_ETAPA_II, "alimentaciones": 0},
    3: {"xp": XP_ETAPA_III, "alimentaciones": 0},
}

# Regla 9.2: mejora de atributos POR CADA evolucion (se acumulan en cada etapa).
MEJORA_POR_EVOLUCION = {"salud_maxima": 15, "ataque": 2, "defensa": 1}

# Las reglas dicen "salud maxima +15" y que NO hay regeneracion automatica (6.2), asi que por defecto
# evolucionar sube solo el MAXIMO. Si el equipo decide curar tambien la salud actual, cambiar a True.
EVOLUCION_CURA_SALUD_ACTUAL = False

# Regla 3.1: dano solar normal del vampiro por ciclo diurno fuera de refugio (P6 lo aplica).
DANO_SOLAR_BASE = 8

# Regla 9.3 (Portador de la Plaga): despues del dano por incendio debe sobrevivir dos ciclos.
CICLOS_SUPERVIVENCIA_TRAS_FUEGO = 2

# Regla 9.3: condiciones de la evolucion alternativa (solo cuentan desde la etapa II).
#   Vampiro Solar: sobrevivir 3 ciclos diurnos fuera de un refugio.
#   Bestia Salvaje: 3 ciclos en un bosque contaminado y eliminar al menos un zombi.
#   Portador de la Plaga: visitar 3 casillas contaminadas distintas y recibir dano por
#   incendio sobreviviendo dos ciclos posteriores (al menos una vez).
CONDICIONES_ALTERNATIVAS = {
    "vampiro": {"ciclos_exposicion_solar": 3},
    "hombre_lobo": {"ciclos_bosque_contaminado": 3, "zombis_eliminados": 1},
    "zombi": {"casillas_contaminadas_distintas": 3, "incendios_sobrevividos": 1},
}

# Regla 9.3: efectos de las formas alternativas.
#   "dano_solar": nuevo dano solar por ciclo (lo consulta P6 con obtener_dano_solar).
#   "zona" + "bonos_zona": bonos que SOLO valen mientras la criatura esta en esa zona.
ADAPTACIONES = {
    "dano_solar_reducido": {
        "descripcion": "Vampiro Solar: su dano solar baja de 8 a 2 puntos por ciclo",
        "dano_solar": 2,
    },
    "bonos_bosque_contaminado": {
        "descripcion": "Bestia Salvaje: +3 ataque y +2 defensa mientras este en bosque contaminado",
        "zona": "bosque_contaminado",
        "bonos_zona": {"ataque": 3, "defensa": 2},
    },
    "bonos_zona_contaminada": {
        "descripcion": "Portador de la Plaga: +2 defensa y +5 salud maxima mientras este en zonas contaminadas",
        "zona": "contaminada",
        "bonos_zona": {"defensa": 2, "salud_maxima": 5},
    },
}

# Regla 9 (tabla de evoluciones): nombre de cada forma y adaptaciones propias.
# Las mejoras numericas son las de MEJORA_POR_EVOLUCION (iguales en todas las formas).
EVOLUCIONES = {
    "vampiro": {
        "II": {"nombre": "Sanguinario", "adaptaciones": []},
        "III_normal": {"nombre": "Señor Carmesí", "adaptaciones": []},
        "III_alternativa": {"nombre": "Vampiro Solar", "adaptaciones": ["dano_solar_reducido"]},
    },
    "hombre_lobo": {
        "II": {"nombre": "Licántropo", "adaptaciones": []},
        "III_normal": {"nombre": "Alfa Lunar", "adaptaciones": []},
        "III_alternativa": {"nombre": "Bestia Salvaje", "adaptaciones": ["bonos_bosque_contaminado"]},
    },
    "zombi": {
        "II": {"nombre": "Devorador", "adaptaciones": []},
        "III_normal": {"nombre": "Coloso Pútrido", "adaptaciones": []},
        "III_alternativa": {"nombre": "Portador de la Plaga", "adaptaciones": ["bonos_zona_contaminada"]},
    },
}

CLAVES_BONOS_ZONA = ("salud_maxima", "ataque", "defensa")

# --- EVENTOS AMBIENTALES Y TIEMPO (P11, P6) ---
CICLOS_POR_DIA_MUNDO = 12
PERIODOS = ["dia", "atardecer", "noche"]

CONFIG_EVENTOS = {
    "eclipse": {
        "nombre": "Eclipse",
        "probabilidad": 0.10,
        "duracion": 4,
        "ciclo_en_dia": 0,
    },
    "luna_sangre": {
        "nombre": "Luna de sangre",
        "probabilidad": 0.10,
        "duracion": 4,
        "ciclo_en_dia": 8,
    },
    "lluvia_corrupta": {
        "nombre": "Lluvia corrupta",
        "probabilidad": 0.05,
        "duracion": 4,
        "lado_zona": 3,
        "ciclos_contaminacion_extra": 6,
    },
    "incendio": {
        "nombre": "Incendio",
        "probabilidad": 0.03,
        "duracion": 3,
        "lado_zona": 3,
        "ciclos_quemado_extra": 4,
        "dano_edificios": 12,
        "dano_criaturas": {"vampiro": 12, "hombre_lobo": 12, "zombi": 18},
    },
}

BONOS_LUNA_SANGRE = {"ataque": 5, "defensa": 2}
CONTAMINACION_SALUD = {"zombi": 5, "vampiro": -5, "hombre_lobo": -5}
EXCLUSION_ENTRE_EVENTOS = True
ORDEN_ORDEN_PRIORIDAD = ["eclipse", "luna_sangre", "lluvia_corrupta", "incendio"]

DURACION_CICLO = 12
PERIODOS_VALIDOS = ("dia", "atardecer", "noche")

DESGASTE_SACIEDAD = {
    "hombre_lobo": {"dia": -3, "atardecer": -3, "noche": -6},
    "vampiro": {"dia": 0, "atardecer": -3, "noche": -3},
    "zombi": {"dia": -3, "atardecer": -3, "noche": -3},
}

DANO_SACIEDAD_CERO = {
    "hombre_lobo": {"dia": -10, "atardecer": -10, "noche": -6},
    "vampiro": {"dia": -5, "atardecer": -4, "noche": -4},
    "zombi": {"dia": -5, "atardecer": -5, "noche": -5},
}

COSTO_ENERGIA_POR_PERIODO = {
    "hombre_lobo": {"dia": -3, "atardecer": -3, "noche": -7},
    "vampiro": {"dia": -2, "atardecer": -6, "noche": -6},
    "zombi": {"dia": -5, "atardecer": -5, "noche": -5},
}

ACCIONES_MOVIMIENTO_P8 = {"MOVER"}

RECUPERACION_ENERGIA_DESCANSO = {
    "en_refugio": 8,
    "en_aldea": 5,
    "fuera_de_aldea": 2,
}

DANO_SOL_POR_LINAJE = {
    "hombre_lobo": 0,
    "vampiro": -23,
    "zombi": 0,
}

DANO_FUEGO_POR_LINAJE = {
    "hombre_lobo": {"humana": -10, "bestia": -5},
    "vampiro": -4,
    "zombi": -8,
}

DANO_CONTAMINACION_POR_LINAJE = {
    "hombre_lobo": -6,
    "vampiro": -7,
    "zombi": -4,
}

#Otros atributos
COSTO_ATAQUE = 5
# Un ataque consume 5 puntos de energia

ALCANCE_ATAQUE = 1
# La distancia entre atacante y objetivo debe ser exactamente 1 casilla.
# Esto permite arriba/abajo/izquierda/derecha, pero NO diagonal.

PROBABILIDAD_VENENO = 0.60
# Un vampiro o lobo que consuma un cadaver zombi tiene 60 % de riesgo.

DANO_VENENO = 8
# Durante cada ciclo de veneno se restan 8 puntos de salud.

PLAZO_CURACION = 4
# Si pasan 4 ciclos desde el consumo sin antidoto, la criatura muere.
# El consumo ocurre en un ciclo, y el primer daño se aplica al siguiente.

SALUD_AL_CURAR = 10
# Un antidoto recupera 10 puntos de salud, sin pasar la salud maxima.

COSTO_ENERGIA_PERIODO = {
    "hombre_lobo": {"dia": -3, "atardecer": -3, "noche": -7},
    "vampiro": {"dia": -2, "atardecer": -6, "noche": -6},
    "zombi": {"dia": -5, "atardecer": -5, "noche": -5},
}