#P9
# P9 - COMBATE, DEPREDACION, MUERTES, VENENO Y CURACION
import random
from config import (
    COSTO_ATAQUE, ALCANCE_ATAQUE, PROBABILIDAD_VENENO,
    DANO_VENENO, PLAZO_CURACION, SALUD_AL_CURAR,
)
# random es una libreria de Python para obtener resultados al azar.
# Solo se usa para decidir si ocurre el envenenamiento con 60 % de riesgo.


def distancia_combate(posicion1, posicion2):
    # Esta funcion RECIBE dos TUPLAS (fila, columna) y DEVUELVE un numero.
    # Ejemplo: posicion1 = (2, 5) y posicion2 = (3, 5).
    # [0] obtiene la FILA y [1] obtiene la COLUMNA de cada tupla.
    # Se suman ambas diferencias para calcular la distancia
    # Ejemplo: (2, 5) y (3, 5) -> abs(2-3) + abs(5-5) = 1 + 0 = 1.
    # Ejemplo diagonal: (2, 5) y (3, 6) -> 1 + 1 = 2; NO permite atacar.
    return abs(posicion1[0] - posicion2[0]) + abs(posicion1[1] - posicion2[1])


def calcular_dano(atacante, objetivo):
    # RECIBE dos OBJETOS Criatura. No recibe sus IDs porque necesitamos
    # consultar sus atributos: atacante.ataque y objetivo.defensa.
    # La formula NO usa atributos iniciales: esos numeros pueden cambiar
    # si el lobo se transforma o si una criatura evoluciona.
    #
    # objetivo.defensa // 2 es DIVISION ENTERA: 9 // 2 devuelve 4.
    # Por ejemplo, un vampiro con ataque 15 golpea a un lobo con defensa 4:
    # 15 - (4 // 2) = 15 - 2 = 13 puntos de daño.
    # max(2, resultado) escoge el mayor de los dos numeros.
    # Si resultado fuera -1, devolveria 2 porque el daño MINIMO es 2.
    #
    # Esta funcion SOLO CALCULA y devuelve el numero; no cambia salud.
    return max(2, atacante.ataque - (objetivo.defensa // 2))


class ControlCombate:
    # Cada OBJETO ControlCombate guarda la informacion de combates y veneno
    # de una partida, igual que cada objeto Criatura guarda sus atributos.
    # No es necesario crear un controlador nuevo por cada ataque.

    def __init__(self, liberar_casilla_funcion, generador_aleatorio=None):
        # __init__ se ejecuta al crear ControlCombate(...).
        # liberar_casilla_funcion RECIBE una FUNCION existente de P2.
        # Ejemplo: combate = ControlCombate(liberar_casilla)
        # Notar que aqui NO escribimos liberar_casilla(): con parentesis
        # la ejecutariamos, pero necesitamos GUARDARLA para usarla despues.
        self.liberar_casilla_funcion = liberar_casilla_funcion
        # Al morir alguien la llamaremos con (mapa, criatura) para quitar
        # su ID de la casilla, conservando su cadaver mediante P4.

        self.ultimo_ciclo_ataque = {}
        # DICCIONARIO VACIO que relaciona el ID con el ultimo ciclo atacado.
        # Ejemplo: {7: 20, 9: 18} quiere decir que ID 7 ataco en ciclo 20
        # y que ID 9 ataco por ultima vez en el ciclo 18.
        # Asi no dejamos atacar dos veces a la misma criatura en un ciclo.

        self.numero_ataques = 0
        # CONTADOR: aumenta 1 cada vez que se ejecuta un ataque valido.
        # No aumenta cuando se intenta atacar pero la funcion lo rechaza.

        self.envenenados = {}
        # DICCIONARIO DE DICCIONARIOS, parecido a ATRIBUTOS_INICIALES de P2.
        # Primera clave: ID de criatura. Valor: otro diccionario con dos datos.
        # Ejemplo: {7: {"ciclo_inicio": 12, "ciclos_procesados": 0}}
        # Esto dice que la criatura 7 se enveneno en el ciclo 12 y aun no
        # ha recibido ninguno de los daños que corresponden a ese veneno.
        # El diccionario NO cuenta automaticamente: el metodo
        # procesar_veneno() se encarga de aumentar ciclos_procesados.

        self.muertes_registradas = set()
        # SET: conjunto VACIO que guarda IDs sin repetirlos.
        # Ejemplo: {3, 7} significa que esas muertes ya fueron registradas.
        # No son los muertos del mundo, sino los que ESTE controlador
        # ya notifico para evitar crear dos cadaveres de un mismo individuo.

        if generador_aleatorio is None:
            # None indica que NO nos entregaron otra funcion de azar.
            # random.random es una FUNCION que genera decimales entre 0 y 1.
            self.generador_aleatorio = random.random
        else:
            # Si nos pasan otra funcion, la guardamos sin ejecutarla.
            # Por ejemplo, lambda: 0.20 devuelve siempre 0.20 en una prueba.
            self.generador_aleatorio = generador_aleatorio

    def _validar_ciclo(self, ciclo):
        # Revisa que el ciclo recibido sea un numero entero 0, 1, 2...
        # En Python, True se comporta como 1 en algunas operaciones;
        # por eso type(ciclo) is not int evita aceptarlo como ciclo.
        # "or" significa O: basta con que UNA condicion sea cierta.
        if type(ciclo) is not int or ciclo < 0:
            raise ValueError("ERROR INTERNO P9: ciclo debe ser un entero >= 0")
            # raise detiene la operacion y muestra un error para que
            # quien programo el motor corrija el valor enviado.

    def esta_envenenado(self, criatura):
        # Devuelve True SOLO si la criatura esta viva Y si su ID aparece
        # como CLAVE dentro del diccionario self.envenenados.
        # Ejemplo: si envenenados = {7: {...}} y criatura.id = 7,
        # "7 in self.envenenados" es True.
        # "and" exige que las DOS condiciones se cumplan.
        return criatura.vivo and criatura.id in self.envenenados

    def puede_atacar(self, atacante, objetivo, ciclo):
        # SOLO CONSULTA SI ES POSIBLE UN ATAQUE; no aplica ningun daño.
        # Devuelve una TUPLA con (booleano, texto de explicacion).
        # Ejemplo: (False, "energia insuficiente para atacar").
        self._validar_ciclo(ciclo)

        if not atacante.vivo or not objetivo.vivo:
            # "not" invierte True/False. Si cualquiera esta muerto,
            # no tiene sentido ejecutar el golpe.
            return False, "atacante u objetivo muerto"

        if atacante.id == objetivo.id:
            # Comparamos IDs, pues una criatura no puede atacarse a si misma.
            return False, "no puede atacarse a si mismo"

        if atacante.linaje == objetivo.linaje:
            # La simulacion usa combates entre linajes diferentes.
            return False, "el ataque entre criaturas del mismo linaje no esta previsto"

        if atacante.posicion is None or objetivo.posicion is None:
            # None significa que alguna criatura NO tiene coordenadas.
            return False, "alguna criatura no tiene posicion en el mapa"

        if distancia_combate(atacante.posicion, objetivo.posicion) != ALCANCE_ATAQUE:
            # != significa DIFERENTE. Si distancia es 2, no puede atacar;
            # si vale 1, esta en una casilla vecina y puede seguir revisando.
            return False, "el objetivo no esta en una casilla adyacente"

        if atacante.energia < COSTO_ATAQUE:
            # Con energia 4 no alcanza a pagar 5; con 5 si alcanza.
            return False, "energia insuficiente para atacar"

        if self.ultimo_ciclo_ataque.get(atacante.id) == ciclo:
            # get(ID) CONSULTA el diccionario y devuelve el ciclo guardado.
            # Si ese ID no existe, get devuelve None (sin lanzar error).
            # Si guardamos {7: 20} y ciclo = 20, ya ataco ese turno.
            return False, "ya ataco durante este ciclo"

        return True, "puede atacar"
        # Si llegamos aqui, ninguna condicion anterior rechazo el golpe.

    def registrar_muerte(self, mapa, criatura, recursos, ciclo, causa, registro=None):
        # Registra las consecuencias de UNA muerte, sin volver a matar.
        # RECIBE: mapa de P2, objeto Criatura, objeto recursos de P4,
        # numero de ciclo, texto con la causa y registro opcional de P3.
        # DEVUELVE True si registro por primera vez o False si no procedia.
        self._validar_ciclo(ciclo)

        if criatura.vivo and criatura.salud > 0:
            # Si sigue viva y con salud positiva, no debe crear un cadaver.
            return False

        if criatura.id in self.muertes_registradas:
            # "in" verifica si el ID ya estaba dentro del SET.
            # Impide duplicar un mismo cadaver/evento cuando se llame otra vez.
            return False

        if criatura.vivo:
            # Puede haber quedado con vida True pero salud 0 por una
            # modificacion externa. Marcamos de manera coherente su muerte.
            criatura.marcar_muerta()
            # Esta funcion de P2 pone salud=0, vivo=False, estado="MUERTO".

        if recursos is not None:
            # Primero dejamos el CADAVER en la posicion que tiene ahora.
            # Si pusieramos criatura.posicion = None antes, P4 ya no sabria
            # en que casilla murio el individuo.
            ya_existe_cadaver = any(
                c["id_criatura"] == criatura.id for c in recursos.cadáveres
            )
            # recursos.cadáveres es una LISTA de diccionarios de P4.
            # En cada vuelta del for se llama c a un diccionario de cadaver.
            # c["id_criatura"] lee el identificador guardado en el cadaver.
            # La comparacion es True si coincide con la criatura que murio.
            # any(...) devuelve True si AL MENOS UNO coincide, False si ninguno.
            # Ejemplo: si ya habia un cadaver ID 7, no agregamos otro ID 7.
            if not ya_existe_cadaver:
                recursos.registrar_cadáver(criatura)
                # P4 agrega a su lista un diccionario con el ID, el linaje,
                # la posicion y los 4 ciclos de vigencia del cadaver.

        if registro is not None:
            # RegistroMundo es opcional. Solo registramos si fue entregado.
            registro.registrar_muerte(ciclo, criatura.id, criatura.linaje, causa)
            # El texto causa permite distinguir combate, veneno, etc.

        if criatura.posicion is not None:
            self.liberar_casilla_funcion(mapa, criatura)
            # Esta es la FUNCION de P2 que guardamos en __init__.
            # Busca su casilla y cambia "ocupante_id" a None cuando coincide.
            criatura.posicion = None
            # Despues quitamos las coordenadas del OBJETO muerto.
            # El cadaver sigue en el mapa LOGICAMENTE porque P4 conserva
            # su posicion dentro de recursos.cadáveres.

        self.envenenados.pop(criatura.id, None)
        # pop(clave, valor_por_defecto) borra la clave del diccionario si existe.
        # Si no existe, devuelve None en vez de provocar un error.
        self.muertes_registradas.add(criatura.id)
        # add() agrega el ID al SET; no permite guardarlo dos veces.
        return True

    def atacar(self, mapa, atacante, objetivo, ciclo, recursos, registro=None):
        # Ejecuta UN golpe entre criaturas. A diferencia de puede_atacar(),
        # esta funcion SI cambia salud, energia y registra los resultados.
        permitido, motivo = self.puede_atacar(atacante, objetivo, ciclo)
        # La funcion devuelve una TUPLA (True/False, texto).
        # Python separa el primer dato en permitido y el segundo en motivo.

        if not permitido:
            # Si permitido es False, salimos inmediatamente sin gastar energia.
            return {"ok": False, "motivo": motivo, "atacante_id": atacante.id,
                    "objetivo_id": objetivo.id, "dano": 0, "objetivo_murio": False}
            # Este DICCIONARIO sirve para que quien ejecuto el ataque sepa
            # que fallo y por que. "dano": 0 deja claro que no golpeo.

        dano = calcular_dano(atacante, objetivo)
        # Guarda el NUMERO que devuelve la formula del combate.
        # Ejemplo: si retorna 13, dano = 13.
        atacante.modificar_energia(-COSTO_ATAQUE)
        # Enviamos -5 a P2. Si tenia 80 de energia, pasa a 75.
        objetivo.modificar_salud(-dano)
        # Enviamos -13 para descontar 13 de salud, NO para sumarlos.
        # Si llega a 0, P2 deja la criatura marcada como muerta.
        self.ultimo_ciclo_ataque[atacante.id] = ciclo
        # Guarda un par en el diccionario: clave ID -> valor ciclo actual.
        # Ejemplo: ultimo_ciclo_ataque[7] = 20 registra que ID 7 golpeo hoy.
        self.numero_ataques += 1
        # += 1 significa: numero_ataques = numero_ataques + 1.

        if registro is not None:
            registro.registrar_combate(
                ciclo, atacante.id, objetivo.id,
                f"Criatura {atacante.id} ataco a {objetivo.id} e hizo {dano} de daño"
            )
            # La f antes del texto crea una f-string: sustituye {dano}
            # por el valor real, ej. "... hizo 13 de daño".

        murio = not objetivo.vivo
        # Si objetivo.vivo es False, "not" lo convierte en True.
        # Por ejemplo, murio=True indica que el golpe fue mortal.
        if murio:
            self.registrar_muerte(mapa, objetivo, recursos, ciclo, "combate", registro)
            # Esta funcion de P9 controla el cadaver, el registro de muerte
            # y que la casilla quede libre una sola vez.

        return {"ok": True, "motivo": "ataque realizado", "atacante_id": atacante.id,
                "objetivo_id": objetivo.id, "dano": dano, "objetivo_murio": murio,
                "energia_restante": atacante.energia, "salud_objetivo": objetivo.salud}
        # Devuelve un DICCIONARIO con el RESULTADO, no una nueva criatura.
        # Ejemplo: resultado["dano"] vale 13 y resultado["ok"] vale True.
        # Para XP, otra seccion puede leer objetivo_murio y dano.

    def depredar(self, mapa, cazador, presa, ciclo, recursos, registro=None):
        # DEPREDAR es intentar cazar otra criatura.
        # cazador y presa son OBJETOS Criatura, aunque tengan esos nombres.
        # No existe otro calculo de daño para cazar: usamos atacar().
        # Por eso "return self.atacar(...)" devuelve EL MISMO diccionario
        # que hubiera devuelto un ataque normal.
        #
        # IMPORTANTE: matar NO alimenta automaticamente. El cadaver queda
        # registrado en P4 y consumirlo seria una accion posterior.
        return self.atacar(mapa, cazador, presa, ciclo, recursos, registro)

    def consumir_cadaver(self, criatura, recursos, ciclo, registro=None):
        # Intenta que UNA criatura consuma un cadaver en su misma casilla.
        # P4 ya programa el alimento y suma 40 puntos de saciedad;
        # P9 solamente decide si ese consumo causa ENVENENAMIENTO.
        self._validar_ciclo(ciclo)

        if not criatura.vivo or criatura.posicion is None:
            return {"ok": False, "motivo": "criatura muerta o sin posicion",
                    "envenenado": False}

        consumido, tipo = recursos.consumir_cadáver(criatura.posicion, criatura)
        # P4 devuelve una TUPLA como (True, "normal") o (False, "sin_cadáver").
        # Python la separa: consumido guarda True/False y tipo el texto.
        # La funcion de P4 elimina el cadaver usado para que no se coma dos veces.
        if not consumido:
            return {"ok": False, "motivo": tipo, "envenenado": False}

        envenenado_ahora = False
        # Esta variable diferencia "se enveneno POR ESTE consumo" de
        # "ya estaba envenenado desde antes". Inicialmente no hubo cambio.
        if tipo == "envenenamiento_potencial" and not self.esta_envenenado(criatura):
            # Este texto se usa cuando un vampiro o lobo come CADAVER ZOMBI.
            # Si ya estaba envenenado, no creamos otro veneno encima.
            if self.generador_aleatorio() < PROBABILIDAD_VENENO:
                # La FUNCION de azar devuelve un decimal entre 0 y 1.
                # Si sale 0.20: 0.20 < 0.60, hay veneno.
                # Si sale 0.81: 0.81 < 0.60 es False, no hay veneno.
                self.envenenados[criatura.id] = {
                    "ciclo_inicio": ciclo,
                    "ciclos_procesados": 0
                }
                # Se crea una entrada en el DICCIONARIO usando la clave ID.
                # Ejemplo: {7: {"ciclo_inicio": 10, "ciclos_procesados": 0}}
                # Todavia NO descontamos salud en el ciclo del consumo.
                envenenado_ahora = True
                if registro is not None:
                    registro.registrar_acontecimiento(
                        ciclo, "envenenamiento",
                        f"Criatura {criatura.id} se enveneno al consumir cadaver zombi",
                        id_unico=f"veneno_{criatura.id}_{ciclo}"
                    )
                    # id_unico es un texto como "veneno_7_10" que permite
                    # a P3 evitar guardar dos veces este mismo acontecimiento.

        return {"ok": True, "motivo": "cadaver consumido", "tipo": tipo,
                "envenenado": self.esta_envenenado(criatura),
                "envenenado_ahora": envenenado_ahora}
        # "envenenado" informa si AHORA sigue con veneno, aunque ya lo tuviera.
        # "envenenado_ahora" solo sera True si se lo acabamos de registrar.

    def procesar_veneno(self, mapa, criatura, recursos, ciclo, registro=None):
        # Procesa el efecto de veneno de UNA criatura en el ciclo recibido.
        # Es diferente de consumir_cadaver: aquel puede iniciar el veneno;
        # este resta salud a medida que avanzan los ciclos.
        #
        # EJEMPLO: el vampiro comio cadaver zombi en el ciclo 10.
        # - Ciclo 10: todavia no pierde salud por veneno.
        # - Ciclo 11: pierde 8 salud, ciclos_procesados = 1.
        # - Ciclo 12: pierde otros 8, ciclos_procesados = 2.
        # - Ciclo 13: pierde otros 8, ciclos_procesados = 3.
        # - Ciclo 14: pierde otros 8 y, si no tomo antidoto, muere.
        self._validar_ciclo(ciclo)
        if not self.esta_envenenado(criatura):
            return {"envenenado": False, "dano": 0, "murio": False}
            # Si no aparece en el diccionario, no hay daño que aplicar.

        datos = self.envenenados[criatura.id]
        # datos es el DICCIONARIO INTERNO del ID de esta criatura.
        # Ejemplo: {"ciclo_inicio": 10, "ciclos_procesados": 2}.

        ciclos_desde_consumo = max(0, ciclo - datos["ciclo_inicio"])
        # Restamos al ciclo actual el ciclo de inicio.
        # Ejemplo: 13 - 10 = 3. max(0, ...) evita resultados negativos.
        # Este numero indica cuantos ciclos PASARON desde que comio.

        ciclos_que_corresponden = min(PLAZO_CURACION, ciclos_desde_consumo)
        # min(4, 3) devuelve 3. min(4, 8) devuelve 4.
        # Por tanto, no puede reclamar mas de cuatro ciclos de veneno.

        ciclos_pendientes = ciclos_que_corresponden - datos["ciclos_procesados"]
        # Si ya procesamos 2 ciclos, pero por la fecha deberian ir 3:
        # ciclos_pendientes = 3 - 2 = 1. Solo falta descontar UN ciclo.
        # Si lo llamamos otra vez en el mismo ciclo: 3 - 3 = 0.
        # Por eso no descontamos 8 de salud dos veces accidentalmente.

        dano_total = 0
        # Acumulador: guardara cuanto daño se desconto EN ESTA LLAMADA.
        # Si hay dos ciclos pendientes, sumara 8 + 8 = 16.
        for _ in range(max(0, ciclos_pendientes)):
            # range(n) hace que el for se repita n veces.
            # La variable _ significa que no necesitamos el numero de vuelta.
            # max(0, ...) evita un rango negativo.
            criatura.modificar_salud(-DANO_VENENO)
            # Pasamos -8 al metodo de P2: pierde ocho puntos de salud.
            dano_total += DANO_VENENO
            # Sumamos +8 al registro del DAÑO aplicado; no a la salud.
            datos["ciclos_procesados"] += 1
            # Aumentamos 1 en el diccionario para recordar este ciclo.

            if not criatura.vivo:
                # Si con el daño llego a salud 0, muere ANTES del plazo.
                self.registrar_muerte(mapa, criatura, recursos, ciclo,
                                     "daño por veneno", registro)
                return {"envenenado": False, "dano": dano_total, "murio": True}

            if datos["ciclos_procesados"] >= PLAZO_CURACION:
                # >= significa MAYOR O IGUAL. Si ya llego a cuatro ciclos
                # sin cura, muere INCLUSO SI TODAVIA TENIA SALUD POSITIVA.
                criatura.marcar_muerta()
                self.registrar_muerte(mapa, criatura, recursos, ciclo,
                                     "veneno sin cura durante 4 ciclos", registro)
                return {"envenenado": False, "dano": dano_total, "murio": True}

        return {"envenenado": True, "dano": dano_total, "murio": False,
                "ciclos_procesados": datos["ciclos_procesados"]}
        # Si el for termino sin muerte, devuelve el daño que aplico ahora.
        # Ejemplo segundo llamado en ciclo 12: dano=0, ciclos_procesados=2.

    def procesar_veneno_poblacion(self, mapa, poblacion, recursos, ciclo, registro=None):
        # A diferencia del metodo anterior, este revisa VARIAS criaturas.
        # Recibe un objeto Poblacion de P2 con su lista de individuos.
        # Devuelve una LISTA de diccionarios con resultados de envenenados.
        resultados = []
        # Inicialmente no hay resultados para este ciclo.
        for criatura in poblacion.obtener_vivas():
            # obtener_vivas() devuelve una LISTA de objetos Criatura vivos.
            # En cada repeticion, la variable criatura toma UN objeto.
            if self.esta_envenenado(criatura):
                # No tiene sentido llamar procesar_veneno a los no envenenados.
                resultado = self.procesar_veneno(
                    mapa, criatura, recursos, ciclo, registro
                )
                # resultado es un DICCIONARIO como {"dano": 8, "murio": False,...}.
                resultado["id"] = criatura.id
                # Agregamos una clave "id" para identificar a quien pertenece.
                resultados.append(resultado)
                # append agrega este diccionario AL FINAL de la lista.
        return resultados
        # Si no habia envenenados, devuelve una lista vacia [].

    def curar(self, criatura, recursos, ciclo, registro=None):
        # Cura UNA criatura envenenada cuando se encuentra en la MISMA
        # posicion de un antidoto de P4. No basta con estar al lado.
        # Ejemplo: criatura.posicion=(3, 7), antidoto en (3, 7): coincide.
        # Si antidoto en (3, 8), todavia no puede consumirlo.
        self._validar_ciclo(ciclo)
        if not criatura.vivo or criatura.posicion is None:
            return {"ok": False, "motivo": "criatura muerta o sin posicion"}

        if not self.esta_envenenado(criatura):
            return {"ok": False, "motivo": "la criatura no esta envenenada"}

        inicio = self.envenenados[criatura.id]["ciclo_inicio"]
        # Buscamos DOS claves: primero el ID de criatura y despues
        # "ciclo_inicio" dentro del diccionario de ese individuo.
        # Ejemplo: envenenados[7]["ciclo_inicio"] devuelve 10.
        if ciclo - inicio > PLAZO_CURACION:
            # Si estamos en ciclo 15 y el inicio fue 10:
            # 15 - 10 = 5; 5 > 4 significa que vencio el plazo.
            return {"ok": False, "motivo": "ya paso el plazo de curacion"}

        if not recursos.consumir_antidoto(criatura.posicion):
            # P4 busca en su LISTA de antidotos si existe uno con
            # la misma tupla de posicion y con cantidad mayor que cero.
            # Si lo encuentra, descuenta UNA unidad y devuelve True.
            # "not" hace que entremos aqui solo si devolvio False.
            return {"ok": False, "motivo": "no hay antidoto disponible en esta casilla"}

        self.envenenados.pop(criatura.id)
        # pop(ID) elimina del DICCIONARIO el registro de veneno de esa criatura.
        # Ejemplo: si habia {7: {...}, 9: {...}}, queda solo el ID 9.
        criatura.modificar_salud(SALUD_AL_CURAR)
        # Le sumamos +10 salud usando P2, que NO deja superar salud_maxima.

        if registro is not None:
            registro.registrar_acontecimiento(
                ciclo, "curacion", f"Criatura {criatura.id} consumio un antidoto",
                id_unico=f"cura_{criatura.id}_{ciclo}"
            )
            # Se guarda que hubo curacion con un ID unico de acontecimiento.

        return {"ok": True, "motivo": "curada con antidoto", "salud": criatura.salud}
        # Quien llama puede consultar resultado["ok"] o resultado["salud"].

    def atacar_construccion(self, atacante, fila, columna, aldeas, ciclo,
                            dano_estructura=None, registro=None):
        # Ataca una construccion ENEMIGA. Una construccion no es Criatura:
        # su resistencia la guarda ControlAldeas (P5), no tiene salud de P2.
        #
        # El PDF da 15 de daño para ataques de GUAYAGOD, pero NO define
        # el daño de un golpe ordinario de criatura contra un edificio.
        # Por eso dano_estructura tiene None por defecto: sin un valor
        # aprobado, la funcion devuelve ok=False en lugar de inventar un dato.
        self._validar_ciclo(ciclo)
        if not atacante.vivo or atacante.posicion is None:
            return {"ok": False, "motivo": "atacante muerto o sin posicion"}

        if distancia_combate(atacante.posicion, (fila, columna)) != ALCANCE_ATAQUE:
            # Armamos la TUPLA (fila, columna) del edificio y calculamos
            # la distancia. Si no es exactamente 1, no puede alcanzarlo.
            return {"ok": False, "motivo": "construccion fuera de alcance"}

        if atacante.energia < COSTO_ATAQUE:
            return {"ok": False, "motivo": "energia insuficiente"}

        if self.ultimo_ciclo_ataque.get(atacante.id) == ciclo:
            # Consultamos el mismo DICCIONARIO que usan ataques a criaturas.
            # Esto impide golpear a una criatura y al edificio en ese ciclo.
            return {"ok": False, "motivo": "ya ataco en este ciclo"}

        estructura = aldeas.obtener_construccion_en_casilla(fila, columna)
        # P5 devuelve un DICCIONARIO si hay aldea/refugio activo en esa casilla.
        # Por ejemplo, estructura["linaje"] podria ser "zombi".
        # Si no existe, devuelve None.
        if estructura is None:
            return {"ok": False, "motivo": "no existe construccion activa"}

        if estructura["linaje"] == atacante.linaje:
            # Si los linajes coinciden, seria una construccion propia.
            return {"ok": False, "motivo": "no puede atacar construccion propia"}

        if type(dano_estructura) is not int or dano_estructura <= 0:
            # Si nadie definio el daño, None NO pasa esta comprobacion.
            # Tampoco se admiten textos, decimales ni daño cero o negativo.
            return {"ok": False, "motivo": "falta definir dano ordinario a edificios en reglas"}

        resultado = aldeas.aplicar_dano_en_casilla(
            fila, columna, dano_estructura, ciclo=ciclo, registro=registro
        )
        # Esta FUNCION de P5 descuenta resistencia y devuelve un DICCIONARIO.
        # "ciclo=ciclo" significa que el parametro ciclo de P5 recibe
        # el valor de la variable local ciclo; igual para registro.
        # Ejemplo de resultado: {"ok": True, "mensaje": "...",
        # "destruida": False, "resistencia_restante": 90}.
        if not resultado["ok"]:
            # Consultamos la clave "ok" del diccionario que devolvio P5.
            return {"ok": False, "motivo": resultado["mensaje"]}

        atacante.modificar_energia(-COSTO_ATAQUE)
        # Descontamos la energia SOLO si el ataque se realizo de verdad.
        self.ultimo_ciclo_ataque[atacante.id] = ciclo
        self.numero_ataques += 1
        return {"ok": True, "motivo": resultado["mensaje"],
                "dano": dano_estructura, "destruida": resultado["destruida"],
                "resistencia_restante": resultado["resistencia_restante"]}
        # Devolvemos los datos de P5 para saber si el edificio quedo
        # destruido y cuanta resistencia le resta.

    def resumen(self):
        # Reune el ESTADO GENERAL de P9 dentro de un diccionario nuevo.
        # No devuelve objetos Criatura, solo datos faciles de consultar.
        # Por ejemplo, si numero_ataques es 4, "ataques_realizados": 4.
        copiaEnvenenados = {}
        # Este DICCIONARIO VACIO recibira las copias de todos los venenos.
        for identificador, datos in self.envenenados.items():
            # items() entrega pares (clave, valor) del diccionario.
            # Ejemplo: si la entrada es 7: {"ciclo_inicio": 10,...},
            # identificador vale 7 y datos es el diccionario interior.
            copiaEnvenenados[identificador] = datos.copy()
            # copy() crea OTRO diccionario para esa criatura.
            # Asi quien consulte el resumen no cambia el original por error.

        return {
            "envenenados": copiaEnvenenados,
            # Diccionario con registros de veneno, copiados por ID.
            "muertes_registradas": len(self.muertes_registradas),
            # len() cuenta cuantos IDs hay en el SET de muertes.
            "ataques_realizados": self.numero_ataques
            # Cuenta ataques que SI ocurrieron (no los intentos fallidos).
        }