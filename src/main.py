"""
NOCTURNA - Punto de entrada de la aplicación.

Ensambla los módulos del proyecto sin duplicar reglas ni valores de config.py.
El Colab no fija una distribución inicial única, así que el escenario de
partida se recibe como datos (crear_simulacion) o se usa el escenario de
demostración (crear_escenario_demo).

Ejecución:
    python main.py                       # abre la interfaz gráfica con el escenario demo
    python main.py --terminal --ciclos 24
    python main.py --semilla 7           # eventos reproducibles
    python main.py --vacio               # mundo sin criaturas (para armarlo a mano)
"""

from __future__ import annotations

import argparse
from typing import Mapping

from config import ATRIBUTOS_INICIALES

from models import Poblacion
from world import crear_mapa, asignar_terreno, asignar_zona_rectangular, ubicar_criatura
from registry import RegistroMundo
from resources import ControlRecursos
from villages import ControlAldeas
from simulation import Simulacion


LINAJES_VALIDOS = tuple(ATRIBUTOS_INICIALES.keys())


# ----------------------------------------------------------------------
# Validaciones y construcción de piezas
# ----------------------------------------------------------------------

def _validar_posicion(posicion, nombre):
    if (
        not isinstance(posicion, (tuple, list))
        or len(posicion) != 2
        or type(posicion[0]) is not int
        or type(posicion[1]) is not int
    ):
        raise ValueError(
            f"{nombre}: cada posicion debe ser una tupla/lista (fila, columna) "
            "con coordenadas enteras."
        )
    return tuple(posicion)


def _crear_criaturas_iniciales(mapa, poblacion, posiciones_criaturas):
    if posiciones_criaturas is None:
        return

    if not isinstance(posiciones_criaturas, Mapping):
        raise TypeError("posiciones_criaturas debe ser un diccionario por linaje.")

    desconocidos = set(posiciones_criaturas) - set(LINAJES_VALIDOS)
    if desconocidos:
        raise ValueError(f"Linajes no reconocidos: {sorted(desconocidos)}")

    usadas = set()
    for linaje, posiciones in posiciones_criaturas.items():
        # Se acepta una sola posición suelta: (fila, columna)
        if isinstance(posiciones, (tuple, list)) and len(posiciones) == 2 and all(
            type(v) is int for v in posiciones
        ):
            posiciones = [posiciones]

        for posicion in posiciones:
            fila, columna = _validar_posicion(posicion, f"criaturas[{linaje}]")
            if (fila, columna) in usadas:
                raise ValueError(f"La casilla {(fila, columna)} fue asignada mas de una vez.")
            usadas.add((fila, columna))

            criatura = poblacion.crear_criatura(linaje)
            # ubicar_criatura NO lanza error: devuelve False si la casilla es
            # invalida u ocupada. Hay que revisarlo, o la criatura queda sin posicion.
            if not ubicar_criatura(mapa, criatura, fila, columna):
                poblacion.criaturas.remove(criatura)
                poblacion.siguiente_id -= 1
                raise ValueError(
                    f"No se pudo ubicar a {linaje} en {(fila, columna)}: "
                    "casilla fuera del mapa u ocupada."
                )


def _crear_aldeas_iniciales(mapa, aldeas, posiciones_aldeas):
    """
    Solo se crean si se dan las tres posiciones. Resistencia y capacidad quedan
    en None mientras config.py no tenga las tablas oficiales aprobadas.
    """
    if posiciones_aldeas is None:
        return {}

    if set(posiciones_aldeas) != set(LINAJES_VALIDOS):
        raise ValueError(
            "posiciones_aldeas debe contener exactamente una posicion para "
            f"cada linaje: {', '.join(LINAJES_VALIDOS)}."
        )

    posiciones = {
        linaje: _validar_posicion(pos, f"aldeas[{linaje}]")
        for linaje, pos in posiciones_aldeas.items()
    }
    return aldeas.crear_aldeas_iniciales(mapa, posiciones)


def crear_simulacion(
    *,
    posiciones_criaturas=None,
    posiciones_aldeas=None,
    terrenos=None,
    zonas=None,
    fuentes_recursos=None,
    antidotos=None,
    semilla=None,
):
    """
    Construye y conecta todos los componentes de una partida.

      posiciones_criaturas: {"vampiro": [(f, c), ...], "hombre_lobo": [...], "zombi": [...]}
      posiciones_aldeas:    {"vampiro": (f, c), "hombre_lobo": (f, c), "zombi": (f, c)}
      terrenos:             {(f, c): "bosque", ...}
      zonas:                [(f1, c1, f2, c2, "bosque"), ...]  (rectangulos, se aplican antes que terrenos)
      fuentes_recursos:     [((f, c), "sangre", cantidad), ...]
      antidotos:            [((f, c), cantidad), ...]
      semilla:              reproduce eventos y veneno.
    """
    mapa = crear_mapa()
    poblacion = Poblacion()
    registro = RegistroMundo()
    recursos = ControlRecursos()
    aldeas = ControlAldeas()

    for f1, c1, f2, c2, terreno in (zonas or []):
        asignar_zona_rectangular(mapa, f1, c1, f2, c2, terreno)

    for posicion, terreno in (terrenos or {}).items():
        fila, columna = _validar_posicion(posicion, "terrenos")
        asignar_terreno(mapa, fila, columna, terreno)

    _crear_criaturas_iniciales(mapa, poblacion, posiciones_criaturas)
    _crear_aldeas_iniciales(mapa, aldeas, posiciones_aldeas)

    for fuente in (fuentes_recursos or []):
        if not isinstance(fuente, (tuple, list)) or len(fuente) not in (2, 3):
            raise ValueError(
                "Cada fuente debe ser ((fila, columna), tipo) o "
                "((fila, columna), tipo, cantidad)."
            )
        pos = _validar_posicion(fuente[0], "fuentes_recursos")
        cantidad = fuente[2] if len(fuente) == 3 else 10  # 10 = valor por defecto de P4
        recursos.registrar_fuente_recurso(pos[0], pos[1], fuente[1], cantidad_inicial=cantidad)

    for pos, cantidad in (antidotos or []):
        fila, columna = _validar_posicion(pos, "antidotos")
        recursos.agregar_antidoto(fila, columna, cantidad)

    return Simulacion(
        mapa=mapa,
        poblacion=poblacion,
        recursos=recursos,
        aldeas=aldeas,
        registro=registro,
        semilla=semilla,
    )


# ----------------------------------------------------------------------
# Escenario de demostración
# ----------------------------------------------------------------------

def crear_escenario_demo(semilla=None):
    """
    Escenario de ejemplo para probar la simulación y la interfaz.
    Es solo una distribución de partida (el Colab no define una): se puede
    cambiar libremente. Vampiros abajo-izquierda, lobos arriba-derecha,
    zombis arriba-izquierda; los recursos del centro son disputados.
    """
    return crear_simulacion(
        semilla=semilla,
        zonas=[
            (0, 0, 19, 19, "camino"),
            (1, 12, 7, 18, "bosque"),         # territorio de los lobos
            (1, 1, 6, 6, "pantano"),          # territorio de los zombis
            (13, 1, 18, 7, "cementerio"),     # territorio de los vampiros
            (8, 8, 11, 11, "ruinas"),         # centro
            (15, 13, 18, 17, "castillo"),
        ],
        posiciones_aldeas={
            "vampiro": (16, 3),
            "hombre_lobo": (3, 16),
            "zombi": (3, 3),
        },
        posiciones_criaturas={
            "vampiro": [(15, 4), (17, 4), (16, 5)],
            "hombre_lobo": [(4, 15), (2, 15), (4, 17)],
            "zombi": [(4, 4), (2, 4), (4, 2)],
        },
        fuentes_recursos=[
            # propios de cada linaje
            ((14, 6), "sangre", 10), ((17, 7), "sangre", 10),
            ((5, 14), "carne", 10), ((2, 17), "carne", 10),
            ((5, 5), "biomasa", 10), ((2, 6), "biomasa", 10),
            # materiales para construir / mejorar
            ((15, 2), "materiales", 10), ((3, 14), "materiales", 10), ((5, 2), "materiales", 10),
            # centro: disputado
            ((9, 9), "sangre", 10), ((10, 10), "carne", 10), ((9, 10), "biomasa", 10),
        ],
        antidotos=[((8, 5), 1), ((11, 14), 1), ((12, 4), 1)],
    )


# ----------------------------------------------------------------------
# Modos de ejecución
# ----------------------------------------------------------------------

def ejecutar_terminal(simulacion, cantidad_ciclos):
    """Ejecuta la simulación e imprime la bitácora de cada ciclo."""
    if type(cantidad_ciclos) is not int or cantidad_ciclos < 1:
        raise ValueError("La cantidad de ciclos debe ser un entero mayor o igual que 1.")

    for _ in range(cantidad_ciclos):
        resumen = simulacion.ejecutar_ciclo()
        print("\n".join(simulacion.resumen_a_logs(resumen)))
        if resumen["extincion"]:
            break
    return simulacion


def iniciar_interfaz(simulacion, fabrica=None):
    """Abre la interfaz gráfica (gui.iniciar_gui). fabrica() crea una partida nueva (botón Reiniciar)."""
    try:
        import bettergui
    except ImportError as exc:
        raise RuntimeError(
            "No se pudo abrir la interfaz (¿falta tkinter?). Usa --terminal."
        ) from exc
    return bettergui.iniciar_gui(simulacion, fabrica=fabrica)


def main():
    parser = argparse.ArgumentParser(description="NOCTURNA: El Despertar del Eclipse")
    parser.add_argument("--ciclos", type=int, default=12,
                        help="Ciclos a ejecutar en modo terminal (default: 12 = un dia).")
    parser.add_argument("--terminal", action="store_true",
                        help="Ejecuta en terminal en lugar de abrir la interfaz grafica.")
    parser.add_argument("--semilla", type=int, default=None,
                        help="Semilla para reproducir eventos aleatorios.")
    parser.add_argument("--vacio", action="store_true",
                        help="Mundo vacio (sin criaturas, aldeas ni recursos).")
    args = parser.parse_args()

    if args.vacio:
        def fabrica():
            return crear_simulacion(semilla=args.semilla)
    else:
        def fabrica():
            return crear_escenario_demo(semilla=args.semilla)
    simulacion = fabrica()

    if args.terminal:
        ejecutar_terminal(simulacion, args.ciclos)
    else:
        iniciar_interfaz(simulacion, fabrica)


if __name__ == "__main__":
    main()