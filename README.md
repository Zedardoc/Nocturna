# NOCTURNA: El Despertar del Eclipse

Simulador de ecosistema sobrenatural en Python. Tres linajes (vampiros, hombres lobo y zombis) viven en un mundo de 20 × 20 casillas. Cada criatura decide qué hacer mediante un **Autómata Finito Determinista (AFD)**: se alimenta, combate, huye del sol, busca refugio, evoluciona y construye aldeas, mientras el mundo cambia con el ciclo día / atardecer / noche, eventos ambientales y la aparición del dragón Guayagod.

## Integrantes

Juliana Jaramillo Ciprián · Juan Camilo Calderón Ayala · Freyman Vera Almeyda · Juan Esteban Monsalve Hernández · Federico Prieto Landaburu · Kevin Daniel Gómez Pabón · Samuel Hazzad Oñate Silva · Adriana Lucía Sepúlveda Parra · Alejandro Rodríguez Luna · Óscar Leonardo Delgado Gélvez · Juan Sebastián Carreño Gélvez · Julián David Vargas Gómez

## Requisitos

- Python 3.8 o superior
- `tkinter` (solo para la interfaz gráfica; viene con Python en Windows y macOS, en Linux: `sudo apt install python3-tk`)
- No se necesitan librerías externas.

## Cómo ejecutarlo

```bash
python main.py                            # interfaz gráfica con el escenario de demostración
python main.py --semilla 7                # eventos aleatorios reproducibles
python main.py --terminal --ciclos 24     # sin ventana, imprime la bitácora en consola
python main.py --vacio                    # mundo vacío (sin criaturas, aldeas ni recursos)
```

| Opción | Descripción |
|---|---|
| `--terminal` | Ejecuta en consola en lugar de abrir la interfaz. |
| `--ciclos N` | Cantidad de ciclos en modo terminal (por defecto 12, un día). |
| `--semilla N` | Semilla para reproducir eventos y veneno. |
| `--vacio` | No carga el escenario de demostración. |

### Interfaz gráfica

- **Avanzar 1 Ciclo / Auto-Play:** controlan el avance; hay control de velocidad y botón **Reiniciar**.
- **Forzar evento:** activa Eclipse, Luna de sangre, Lluvia corrupta o Incendio a mano.
- **Mapa:** `V` vampiro, `L` lobo humano, `B` lobo bestia, `Z` zombi, `A` aldea, `R` refugio provisional, `x` cadáver, `+` antídoto, punto de color = fuente de recurso. Borde rojo = fuego, borde morado = contaminación.
- **Inspector:** haz clic en una casilla para ver terreno, efectos, construcción, recursos y atributos de la criatura (salud, energía, saciedad, ataque, defensa, XP, estado del AFD).
- **Bitácora:** muestra eventos, ataques, alimentación, evoluciones y muertes de cada ciclo.

## Estructura del proyecto

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Punto de entrada. Arma la partida y el escenario de demostración. |
| `simulation.py` | Motor principal: coordina todos los módulos y ejecuta cada ciclo. |
| `gui.py` | Interfaz gráfica (Tkinter). Solo lee el estado; no contiene reglas. |
| `config.py` | Todas las constantes y tablas de reglas del juego. |
| `models.py` | Clases `Criatura` y `Poblacion`. |
| `world.py` | Mapa 20×20: terrenos, ocupación de casillas y efectos temporales. |
| `registry.py` | Registro del mundo: historial, estadísticas y verificación de datos. |
| `villages.py` | Aldeas, refugios provisionales, alojamiento, mejoras y daño a edificios. |
| `resources.py` | Fuentes de recursos, reservas por linaje, cadáveres, antídotos y Guayagod. |
| `movement.py` | Rutas (BFS), movimiento y ejecución de la acción de cada estado del AFD. |
| `combat.py` | Ataques, muertes, veneno y curación. |
| `time_manager.py` | Reloj, hambre, energía, forma del lobo y daño ambiental. |
| `events.py` | Eventos ambientales: Eclipse, Luna de sangre, Lluvia corrupta, Incendio. |
| `experience.py` | XP, etapas y evoluciones (normal y alternativa). |

## Cómo funciona un ciclo

Cada llamada a `Simulacion.ejecutar_ciclo()` hace, en orden:

1. **Eventos ambientales** (sorteo, inicio y fin) y evaluación de **Guayagod**.
2. **Por cada criatura viva:**
   hambre y saciedad → cambio de forma del lobo → veneno → decisión del AFD → acción (movimiento, ataque, alimentación, etc.) → XP → costo de energía → daño ambiental → XP de supervivencia y contadores.
3. **Evoluciones** de las criaturas que cumplan requisitos.
4. **Mantenimiento:** cadáveres, regeneración de fuentes y limpieza de habitantes muertos de las aldeas.
5. **Registro** del ciclo y descuento de la duración de los efectos del mapa.

### Prioridades del AFD

`muerte > veneno > peligro solar > hambre > energía baja > enemigo adyacente > enemigo visible > falta de aldea > explorar`

| Situación | Estado |
|---|---|
| Envenenada | `BUSCAR_CURA` |
| Vampiro de día fuera de refugio | `BUSCAR_REFUGIO` |
| Hambre (saciedad ≤ 40) | `ALIMENTARSE` si puede comer ahí, si no `BUSCAR_ALIMENTO` |
| Energía ≤ 20 | `DESCANSAR` |
| Enemigo adyacente | `ATACAR` |
| Enemigo a la vista | `PERSEGUIR` |
| Sin aldea | `CONSTRUIR` |
| Nada urgente | `EXPLORAR` |

## Posiciones de las criaturas

- **Posición inicial:** `main.py`, función `crear_escenario_demo()`, diccionario `posiciones_criaturas` (tuplas `(fila, columna)`).
- **Dónde se guarda:** `criatura.posicion` y `mapa[fila][columna]["ocupante_id"]`, ambos actualizados por `ubicar_criatura` en `world.py`.
- **Qué la cambia durante la simulación:** `intentar_mover` en `movement.py`.

## Crear tu propio escenario

```python
from main import crear_simulacion

sim = crear_simulacion(
    zonas=[(0, 0, 19, 19, "camino"), (2, 2, 6, 6, "bosque")],
    posiciones_aldeas={"vampiro": (16, 3), "hombre_lobo": (3, 16), "zombi": (3, 3)},
    posiciones_criaturas={"vampiro": [(15, 4)], "hombre_lobo": [(4, 15)], "zombi": [(4, 4)]},
    fuentes_recursos=[((14, 6), "sangre", 10), ((5, 14), "carne", 10), ((5, 5), "biomasa", 10)],
    antidotos=[((8, 5), 1)],
    semilla=1,
)
resumenes = sim.ejecutar(24)
```

Terrenos válidos: `camino`, `bosque`, `pantano`, `cementerio`, `ruinas`, `castillo`. Recursos válidos: `sangre`, `carne`, `biomasa`, `materiales`.

## Pendientes y decisiones abiertas

- **Tablas de aldeas sin definir** en `config.py` (`RESISTENCIA_POR_NIVEL`, `CAPACIDAD_POR_NIVEL`, `COSTO_MEJORA_POR_NIVEL`, `COSTO_RECONSTRUCCION`, `PROVISIONAL_CONFIG`, `REQUISITOS_NACIMIENTO`). Mientras estén vacías, las aldeas no reciben daño, no se pueden mejorar ni reconstruir, y no hay nacimientos.
- **Daño solar del vampiro:** `DANO_SOL_POR_LINAJE` usa 23, pero `DANO_SOLAR_BASE` indica 8 (regla 3.1). La adaptación de Vampiro Solar (`obtener_dano_solar`) todavía no está conectada.
- **Guayagod** aparece y protege a un linaje, pero aún no ataca a criaturas ni construcciones.
- **Regeneración de fuentes:** frecuencia configurable con `intervalo_regeneracion` en `Simulacion` (por defecto, cada ciclo).
- El escenario de demostración es solo una distribución de ejemplo; el balance entre linajes no está ajustado.
