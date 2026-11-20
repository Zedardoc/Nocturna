"""
NOCTURNA - P6: tiempo, necesidades y daño ambiental.
(Extraído de las celdas P6 del Colab; las tablas viven en config.py.)
"""
from config import (
    DURACION_CICLO,
    DESGASTE_SACIEDAD,
    DANO_SACIEDAD_CERO,
    COSTO_ENERGIA_POR_PERIODO,
    ACCIONES_MOVIMIENTO_P8,
    RECUPERACION_ENERGIA_DESCANSO,
    DANO_SOL_POR_LINAJE,
    DANO_FUEGO_POR_LINAJE,
    DANO_CONTAMINACION_POR_LINAJE,
)
from world import consultar_efectos
from events import ControlEventos
#=====================
# Calculo del ciclo
#=====================



def obtener_periodo(ciclo):
    """Devuelve 'dia', 'atardecer' o 'noche' para un ciclo entero >= 0 usando %."""
    if type(ciclo) is not int or ciclo < 0:
        raise ValueError("ERROR INTERNO: el ciclo debe ser un entero mayor o igual que 0")

    fase = ciclo % DURACION_CICLO

    if fase < 4:
        return "dia"
    elif fase < 8:
        return "atardecer"
    else:
        return "noche"


def resumen_tiempo(ciclo):
    """Devuelve información útil del reloj para un ciclo dado."""
    periodo = obtener_periodo(ciclo)
    return {
        "ciclo": ciclo,
        "ciclo_completado": ciclo // DURACION_CICLO,
        "fase_en_ciclo": ciclo % DURACION_CICLO,
        "periodo": periodo,
    }


class RelojSimulacion:
    """Mantiene el avance regular del tiempo ciclo a ciclo."""

    def __init__(self, ciclo_inicial=0):
        if type(ciclo_inicial) is not int or ciclo_inicial < 0:
            raise ValueError("ERROR INTERNO: ciclo_inicial debe ser un entero >= 0")
        self.ciclo = ciclo_inicial

    @property
    def periodo(self):
        return obtener_periodo(self.ciclo)

    def avanzar(self, pasos=1):
        if type(pasos) is not int or pasos < 1:
            raise ValueError("ERROR INTERNO: pasos debe ser un entero >= 1")
        self.ciclo += pasos
        return resumen_tiempo(self.ciclo)

#=====================================
# Calculo y consecuencias de saciedad
#=====================================




def calcular_cambio_saciedad(linaje, periodo):
    """Devuelve el cambio de saciedad (negativo o 0) para un linaje y período."""
    if linaje not in DESGASTE_SACIEDAD:
        raise ValueError(f"ERROR INTERNO: linaje no reconocido en saciedad: {linaje}")
    if periodo not in DESGASTE_SACIEDAD[linaje]:
        raise ValueError(f"ERROR INTERNO: período no reconocido: {periodo}")
    return DESGASTE_SACIEDAD[linaje][periodo]


def aplicar_consecuencia_saciedad_cero(criatura, periodo):
    """
    Aplica el daño por saciedad == 0 según linaje y período, respetando
    los límites de salud (0 a salud_maxima) definidos por P2.
    Devuelve el cambio real de salud (negativo o 0).
    """
    if not criatura.vivo or criatura.saciedad > 0:
        return 0

    if criatura.linaje not in DANO_SACIEDAD_CERO:
        raise ValueError(f"ERROR INTERNO: linaje no reconocido en saciedad cero: {criatura.linaje}")
    if periodo not in DANO_SACIEDAD_CERO[criatura.linaje]:
        raise ValueError(f"ERROR INTERNO: período no reconocido: {periodo}")

    dano = DANO_SACIEDAD_CERO[criatura.linaje][periodo]
    salud_antes = criatura.salud
    criatura.modificar_salud(dano)
    return criatura.salud - salud_antes


def actualizar_hambre_y_saciedad(criatura, ciclo):
    """
    Actualiza la saciedad de una criatura según el ciclo/período y aplica
    consecuencias si su saciedad queda en 0.
    """
    periodo = obtener_periodo(ciclo)

    if not criatura.vivo:
        return {
            "id": criatura.id,
            "periodo": periodo,
            "cambio_saciedad": 0,
            "saciedad": criatura.saciedad,
            "dano_saciedad_cero": 0,
            "vivo": criatura.vivo,
        }

    delta_saciedad = calcular_cambio_saciedad(criatura.linaje, periodo)
    saciedad_antes = criatura.saciedad
    criatura.modificar_saciedad(delta_saciedad)
    cambio_real_saciedad = criatura.saciedad - saciedad_antes

    dano_cero = 0
    if criatura.saciedad == 0:
        dano_cero = aplicar_consecuencia_saciedad_cero(criatura, periodo)

    return {
        "id": criatura.id,
        "periodo": periodo,
        "cambio_saciedad": cambio_real_saciedad,
        "saciedad": criatura.saciedad,
        "dano_saciedad_cero": dano_cero,
        "vivo": criatura.vivo,
    }

#========================================================
# Calculo de costo por accion y recuperacion de energia
#========================================================


# Acciones que corresponden al movimiento gestionado por P8 (no aplican el cobro extra de esta tabla)



def calcular_costo_energia_accion(linaje, periodo, accion=None):
    """
    Devuelve el costo de energía (negativo o 0) por acción para un linaje y período.
    Si accion está en ACCIONES_MOVIMIENTO_P8, devuelve 0 porque P8 ya cobra el movimiento.
    """
    if accion in ACCIONES_MOVIMIENTO_P8:
        return 0
    if linaje not in COSTO_ENERGIA_POR_PERIODO:
        raise ValueError(f"ERROR INTERNO: linaje no reconocido en energía: {linaje}")
    if periodo not in COSTO_ENERGIA_POR_PERIODO[linaje]:
        raise ValueError(f"ERROR INTERNO: período no reconocido en energía: {periodo}")
    return COSTO_ENERGIA_POR_PERIODO[linaje][periodo]


def aplicar_costo_energia_accion(criatura, ciclo, accion=None):
    """
    Aplica el desgaste de energía por acción (distinta a movimiento de P8) según el
    linaje y el período del ciclo actual, respetando los límites [0, energia_maxima] de P2.
    """
    periodo = obtener_periodo(ciclo)
    if not criatura.vivo:
        return {
            "id": criatura.id,
            "accion": accion,
            "periodo": periodo,
            "cambio_energia": 0,
            "energia": criatura.energia,
            "vivo": criatura.vivo,
        }

    costo = calcular_costo_energia_accion(criatura.linaje, periodo, accion=accion)
    energia_antes = criatura.energia
    criatura.modificar_energia(costo)

    return {
        "id": criatura.id,
        "accion": accion,
        "periodo": periodo,
        "cambio_energia": criatura.energia - energia_antes,
        "energia": criatura.energia,
        "vivo": criatura.vivo,
    }


def obtener_condicion_descanso(criatura, aldeas=None):
    """
    Determina la condición de descanso usando las consultas de P5 (ControlAldeas):
    - 'en_refugio': criatura viva y alojada en refugio (esta_en_refugio)
    - 'en_aldea': criatura viva en la casilla de su aldea (criatura_en_casilla_aldea)
    - 'fuera_de_aldea': en cualquier otro caso o si aldeas es None
    """
    if not criatura.vivo or aldeas is None:
        return "fuera_de_aldea"

    if hasattr(aldeas, "esta_en_refugio") and aldeas.esta_en_refugio(criatura):
        return "en_refugio"

    if hasattr(aldeas, "criatura_en_casilla_aldea") and aldeas.criatura_en_casilla_aldea(criatura):
        return "en_aldea"

    return "fuera_de_aldea"


def aplicar_recuperacion_energia(criatura, aldeas=None):
    """
    Aplica la recuperación reglamentaria de +15 al descansar, respetando [0, energia_maxima] de P2.
    """
    if not criatura.vivo:
        return {
            "id": criatura.id,
            "condicion_descanso": "muerta",
            "cambio_energia": 0,
            "energia": criatura.energia,
            "vivo": criatura.vivo,
        }

    condicion = obtener_condicion_descanso(criatura, aldeas)
    recuperacion = RECUPERACION_ENERGIA_DESCANSO[condicion]

    energia_antes = criatura.energia
    criatura.modificar_energia(recuperacion)

    return {
        "id": criatura.id,
        "condicion_descanso": condicion,
        "cambio_energia": criatura.energia - energia_antes,
        "energia": criatura.energia,
        "vivo": criatura.vivo,
    }

#========================
# Actualizar hombre lobo
#========================

FORMAS_LOBO = ("humana", "bestia")


def determinar_forma_lobo(periodo, evento_activo=None):
    """
    Determina la forma esperada ('humana' o 'bestia') según el período
    y el evento ambiental activo (sin sortear eventos).
    Durante el día y el atardecer mantiene la forma humana; durante la noche es bestia.
    """
    if periodo == "noche":
        return "bestia"
    if periodo in ("dia", "atardecer"):
        return "humana"
    raise ValueError("ERROR INTERNO: periodo no reconocido")


def actualizar_forma(criatura, ciclo, evento_activo=None):
    """
    Actualiza la forma ('humana' / 'bestia') de una criatura hombre_lobo
    usando el método cambiar_forma de P2, sin sustituir el objeto original.
    """
    periodo = obtener_periodo(ciclo)
    forma_anterior = criatura.forma

    if not criatura.vivo or criatura.linaje != "hombre_lobo":
        return {
            "id": criatura.id,
            "linaje": criatura.linaje,
            "periodo": periodo,
            "evento_activo": evento_activo,
            "forma_anterior": forma_anterior,
            "forma_actual": criatura.forma,
            "cambio": False,
        }

    forma_objetivo = determinar_forma_lobo(periodo, evento_activo)
    cambio = False

    if forma_objetivo is not None and criatura.forma != forma_objetivo:
        criatura.cambiar_forma(forma_objetivo)
        cambio = True

    return {
        "id": criatura.id,
        "linaje": criatura.linaje,
        "periodo": periodo,
        "evento_activo": evento_activo,
        "forma_anterior": forma_anterior,
        "forma_actual": criatura.forma,
        "cambio": cambio,
        "ataque": criatura.ataque,
        "defensa": criatura.defensa,
    }

#==============================
# Calculo de daños ambientales
#==============================





def calcular_dano_sol(criatura, periodo, en_refugio=False, info_p11=None, xp=None):
    """
    Calcula el daño por exposición solar (solo aplica en período 'dia',
    si no está en refugio, y sujeto a la información de Eclipse de P11).
    """
    if periodo != "dia" or en_refugio:
        return 0

    # La condición de Eclipse se consulta a P11; P6 no realiza sorteos.
    if info_p11 is not None:
        if (hasattr(info_p11, "bloquea_dano_solar") and info_p11.bloquea_dano_solar()) or (
            hasattr(info_p11, "eclipse_activo") and info_p11.eclipse_activo()
        ) or info_p11 == "Eclipse":
            return 0

    if xp is not None and criatura.linaje == "vampiro" and "dano_solar_reducido" in xp.adaptaciones.get(criatura.id, []):
        return -xp.obtener_dano_solar(criatura)

    return DANO_SOL_POR_LINAJE.get(criatura.linaje, 0)


def calcular_dano_fuego(criatura):
    """Calcula el daño por efecto 'fuego' en la casilla actual."""
    dano_cfg = DANO_FUEGO_POR_LINAJE.get(criatura.linaje, 0)
    if isinstance(dano_cfg, dict):
        return dano_cfg.get(criatura.forma, 0)
    return dano_cfg


def calcular_dano_contaminacion(criatura):
    """Devuelve el cambio de salud por contaminación (+5 para zombis)."""
    return DANO_CONTAMINACION_POR_LINAJE.get(criatura.linaje, 0)


def aplicar_dano_ambiental(criatura, mapa, ciclo, aldeas=None, info_p11=None, xp=None):
    """
    Consulta el mapa de P2 para sol, fuego o contaminación y aplica las
    consecuencias aprobadas respetando los límites de P2.
    Durante Eclipse se deja preparado para usar información de P11 (sin sortear).
    """
    periodo = obtener_periodo(ciclo)

    if not criatura.vivo or criatura.posicion is None:
        return {
            "id": criatura.id,
            "ciclo": ciclo,
            "periodo": periodo,
            "posicion": criatura.posicion,
            "efectos_casilla": {},
            "dano_sol": 0,
            "dano_fuego": 0,
            "dano_contaminacion": 0,
            "dano_total": 0,
            "salud": criatura.salud,
            "vivo": criatura.vivo,
        }

    fila, columna = criatura.posicion
    efectos_casilla = consultar_efectos(mapa, fila, columna)

    en_refugio = False
    if aldeas is not None:
        if hasattr(aldeas, "esta_en_refugio") and aldeas.esta_en_refugio(criatura):
            en_refugio = True
        elif hasattr(aldeas, "criatura_en_casilla_refugio") and aldeas.criatura_en_casilla_refugio(criatura):
            en_refugio = True

    dano_sol = calcular_dano_sol(criatura, periodo, en_refugio=en_refugio, info_p11=info_p11, xp=xp)
    dano_fuego = calcular_dano_fuego(criatura) if "fuego" in efectos_casilla else 0
    dano_cont = calcular_dano_contaminacion(criatura) if "contaminacion" in efectos_casilla else 0

    dano_total = dano_sol + dano_fuego + dano_cont
    salud_antes = criatura.salud

    if dano_total != 0:
        criatura.modificar_salud(dano_total)

    return {
        "id": criatura.id,
        "ciclo": ciclo,
        "periodo": periodo,
        "posicion": criatura.posicion,
        "efectos_casilla": efectos_casilla,
        "dano_sol": dano_sol,
        "dano_fuego": dano_fuego,
        "dano_contaminacion": dano_cont,
        "dano_total": criatura.salud - salud_antes,
        "salud": criatura.salud,
        "vivo": criatura.vivo,
    }

#====================================================
# Verificacion de si vampiro necesita buscar refugio
#====================================================

def _es_de_dia(ciclo, eventos=None):
    """Determina si el ciclo corresponde a 'dia', usando P11 si está disponible."""
    if eventos is not None and hasattr(eventos, "periodo_del_ciclo"):
        return eventos.periodo_del_ciclo(ciclo) == "dia"
    if "ControlEventos" in globals():
        return ControlEventos.periodo_del_ciclo(ciclo) == "dia"
    return (ciclo % 7) < 3


def _hay_eclipse_activo(eventos=None):
    """Consulta directamente el sistema de P11 (ControlEventos) sin sortear eventos."""
    if eventos is None:
        return False
    if hasattr(eventos, "bloquea_dano_solar"):
        return bool(eventos.bloquea_dano_solar())
    if hasattr(eventos, "eclipse_activo"):
        return bool(eventos.eclipse_activo())
    if isinstance(eventos, dict):
        return (
            eventos.get("evento_activo") == "Eclipse"
            or eventos.get("tipo") == "Eclipse"
            or bool(eventos.get("eclipse_activo", False))
        )
    if isinstance(eventos, str):
        return eventos == "Eclipse"
    return getattr(eventos, "evento_activo", None) == "Eclipse"


def vampiro_necesita_buscar_refugio(criatura, ciclo, aldeas, eventos):
    """
    Devuelve True únicamente si se cumplen simultáneamente:
    1. La criatura está viva y su linaje es 'vampiro'.
    2. Es de día ('dia').
    3. Está fuera de su aldea y de refugio (según P5).
    4. No hay un eclipse activo (según P11).
    En cualquier otro caso devuelve False.
    """
    if not criatura.vivo or criatura.linaje != "vampiro":
        return False

    if not _es_de_dia(ciclo, eventos):
        return False

    if _hay_eclipse_activo(eventos):
        return False

    if aldeas is not None:
        en_refugio = hasattr(aldeas, "esta_en_refugio") and bool(aldeas.esta_en_refugio(criatura))
        en_aldea = hasattr(aldeas, "criatura_en_casilla_aldea") and bool(aldeas.criatura_en_casilla_aldea(criatura))
        if en_refugio or en_aldea:
            return False

    return True