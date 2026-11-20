# =====================================================================
# NOCTURNA: El Despertar del Eclipse - Módulo: gui.py (P12)
# Interfaz gráfica con PYGAME + sprites. Solo LEE el estado de la
# Simulacion y llama a sim.ejecutar_ciclo(); no contiene reglas del juego.
#
# Las imágenes se buscan (sin distinguir mayúsculas/acentos/espacios) en:
#   $NOCTURNA_ASSETS, y en las carpetas assets/ imagenes/ img/ images/
#   sprites/ recursos/ junto a este archivo (o del directorio actual),
#   o directamente junto a gui.py.
# Si falta alguna imagen se dibuja un marcador de reemplazo: nunca falla.
#
# Atajos: ESPACIO = avanzar ciclo · A = auto-play · R = reiniciar
#         ↑/↓ = velocidad · rueda del ratón sobre la bitácora = scroll
# =====================================================================

import math
import os
import random
import re
import unicodedata

import pygame

from config import TAMANO_MAPA

# ---------------------------------------------------------------------
# Archivos de imagen (nombres exactos entregados)
# ---------------------------------------------------------------------

QUITAR_FONDO_SPRITES = True   # intenta volver transparente un fondo liso de color claro

ARCH = {
    "terreno_base": "01_terreno_base.png",
    "bosque": "Baldosa de Bosque Pixelado Floral.png",
    "bosque_contaminado": "03_bosque_contaminado (1).png",
    "refugio": "refugio provisional.png",
    "guayagod": "Dragón Guayagod con magia pixelada.png",
    "incendio": "incendio.png",
    "lluvia_corrupta": "lluvia_corrupta.png",
    "eclipse": "eclipse.png",
    "luna_sangre": "luna_de_sangre.png",
    "sangre": "01_sangre_frasco.png",
    "carne": "02_carne.png",
    "biomasa": "03_biomasa.png",
    "materiales": "04_materiales_construccion.png",
    "antidoto": "05_antidoto.png",
}

ARCH_ALDEA = {   # {n} = nivel 1..3
    "vampiro": "aldea vampiro tipo {n}.png",
    "hombre_lobo": "aldea lobo tipo {n}.png",
    "zombi": "aldea zombie tipo {n}.png",
}

ARCH_CRIATURA = {
    "nocturno": "06_nocturno_etapa_1.png",
    "sanguinario": "07_sanguinario_etapa_2.png",
    "senor_carmesi": "08_senor_carmesi_etapa_3.png",
    "vampiro_solar": "09_vampiro_solar_etapa_3_alternativa.png",
    "lobo_humano": "10_hombre_lobo_forma_humana.png",
    "licantropo": "11_licantropo_forma_bestia.png",
    "alfa_lunar": "12_alfa_lunar_forma_bestia.png",
    "bestia_salvaje": "13_bestia_salvaje_forma_bestia.png",
    "errante": "14_errante_zombie_etapa_1.png",
    "devorador": "15_devorador_zombie_etapa_2.png",
    "coloso": "16_coloso_putrido_etapa_3.png",
    "portador_plaga": "17_portador_plaga_etapa_3_alternativa.png",
}

# terreno -> (imagen base, tinte multiplicativo). Solo hay arte para
# "camino/base" y "bosque": el resto reutiliza la baldosa base teñida.
TERRENOS = {
    "camino": ("terreno_base", None),
    "bosque": ("bosque", None),
    "pantano": ("terreno_base", (105, 170, 135)),
    "cementerio": ("terreno_base", (150, 140, 180)),
    "ruinas": ("terreno_base", (195, 175, 145)),
    "castillo": ("terreno_base", (175, 120, 175)),
    "sin definir": ("terreno_base", (70, 70, 80)),
}

COLORES_TERRENO = {
    "camino": "#2b2d31", "bosque": "#1e3a29", "pantano": "#26362c",
    "cementerio": "#383642", "ruinas": "#47433e", "castillo": "#3d2c3e",
    "sin definir": "#1e1f22",
}

COLORES_LINAJE = {
    "vampiro": (230, 57, 70),
    "hombre_lobo": (244, 162, 97),
    "zombi": (82, 183, 136),
}
SIMBOLOS_LINAJE = {"vampiro": "V", "hombre_lobo": "L", "zombi": "Z"}
NOMBRES_LINAJE = {"vampiro": "VAMPIRO", "hombre_lobo": "HOMBRE LOBO", "zombi": "ZOMBI"}
RECURSO_ALIMENTO = {"vampiro": "sangre", "hombre_lobo": "carne", "zombi": "biomasa"}

EVENTOS_FORZABLES = ["eclipse", "luna_sangre", "lluvia_corrupta", "incendio"]
ICONO_EVENTO = {"eclipse": "eclipse", "luna_sangre": "luna_sangre",
                "lluvia_corrupta": "lluvia_corrupta", "incendio": "incendio"}

# Paleta de la interfaz
C_FONDO_A, C_FONDO_B = (13, 14, 20), (27, 16, 30)
C_PANEL = (27, 29, 38)
C_PANEL2 = (36, 38, 50)
C_BORDE = (56, 60, 80)
C_ACENTO = (225, 50, 85)
C_TXT = (226, 232, 240)
C_MUTED = (148, 163, 184)
C_AMBAR = (251, 191, 36)
C_AZUL = (56, 189, 248)
C_VERDE = (74, 222, 128)
C_ROJO = (239, 68, 68)
C_MORADO = (168, 85, 247)

VEL_MIN, VEL_MAX = 50, 1500


def _fmt(valor):
    """Muestra 'n/d' cuando un dato oficial sigue pendiente (None) en config.py."""
    return "n/d" if valor is None else str(valor)


def _norm(texto):
    texto = os.path.splitext(texto)[0]
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", texto.lower())


def _sin_acentos(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(ch for ch in texto if not unicodedata.combining(ch)).lower()


# ---------------------------------------------------------------------
# Carga de imágenes
# ---------------------------------------------------------------------

class Assets:
    EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

    def __init__(self):
        base = os.path.dirname(os.path.abspath(__file__))
        cwd = os.getcwd()
        dirs = []
        env = os.environ.get("NOCTURNA_ASSETS")
        if env:
            dirs.append((env, True))
        for sub in ("assets", "imagenes", "imágenes", "img", "images", "sprites", "recursos"):
            for raiz in (base, cwd):
                dirs.append((os.path.join(raiz, sub), True))
        dirs += [(base, False), (cwd, False)]

        self.index = {}
        vistos = set()
        for d, recursivo in dirs:
            d = os.path.abspath(d)
            if d in vistos or not os.path.isdir(d):
                continue
            vistos.add(d)
            if recursivo:
                recorrido = os.walk(d)
            else:
                recorrido = [(d, [], os.listdir(d))]
            for raiz, _, archivos in recorrido:
                for a in archivos:
                    if a.lower().endswith(self.EXT):
                        self.index.setdefault(_norm(a), os.path.join(raiz, a))

        self._orig = {}
        self._esc = {}
        self.faltantes = []

    def _ruta(self, nombre):
        n = _norm(nombre)
        if n in self.index:
            return self.index[n]
        for k, ruta in self.index.items():       # tolera sufijos tipo " (1)"
            if len(k) >= 8 and (k.startswith(n) or n.startswith(k)):
                return ruta
        return None

    def get(self, nombre, sprite=True):
        clave = (nombre, sprite)
        if clave in self._orig:
            return self._orig[clave]
        img = None
        ruta = self._ruta(nombre)
        if ruta:
            try:
                img = pygame.image.load(ruta).convert_alpha()
                if sprite and QUITAR_FONDO_SPRITES:
                    img = self._quitar_fondo(img)
            except Exception:
                img = None
        if img is None and nombre not in self.faltantes:
            self.faltantes.append(nombre)
        self._orig[clave] = img
        return img

    @staticmethod
    def _quitar_fondo(img):
        """Si las 4 esquinas son opacas, claras y casi iguales, se vuelven transparentes."""
        w, h = img.get_size()
        esquinas = [img.get_at(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
        if any(c.a < 250 for c in esquinas):
            return img
        r0 = esquinas[0]
        if any(max(abs(c.r - r0.r), abs(c.g - r0.g), abs(c.b - r0.b)) > 14 for c in esquinas):
            return img
        if (r0.r + r0.g + r0.b) / 3 < 60:         # fondos oscuros: se respetan (contornos negros)
            return img
        try:
            mascara = pygame.mask.from_threshold(img, (r0.r, r0.g, r0.b, 255), (22, 22, 22, 255))
            mascara.to_surface(img, setcolor=(0, 0, 0, 0), unsetcolor=None)
        except Exception:
            pass
        return img

    @staticmethod
    def _escalar(img, nw, nh):
        ow, oh = img.get_size()
        if ow > nw * 2 or oh > nh * 2:
            return pygame.transform.smoothscale(img, (nw, nh))
        return pygame.transform.scale(img, (nw, nh))    # pixel art: sin suavizar

    def ajustado(self, nombre, w, h, sprite=True):
        """Escala conservando proporción dentro de (w, h)."""
        k = ("fit", nombre, w, h, sprite)
        if k not in self._esc:
            img = self.get(nombre, sprite)
            if img is None:
                self._esc[k] = None
            else:
                ow, oh = img.get_size()
                f = min(w / ow, h / oh)
                self._esc[k] = self._escalar(img, max(1, int(ow * f)), max(1, int(oh * f)))
        return self._esc[k]

    def exacto(self, nombre, w, h, sprite=False):
        k = ("ex", nombre, w, h, sprite)
        if k not in self._esc:
            img = self.get(nombre, sprite)
            self._esc[k] = None if img is None else self._escalar(img, w, h)
        return self._esc[k]


# ---------------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------------

class InterfazNocturnaGUI:
    def __init__(self, simulador, fabrica=None):
        """
        simulador: instancia de Simulacion.
        fabrica: función sin argumentos que crea una Simulacion nueva
                 (habilita el botón Reiniciar).
        """
        pygame.init()
        pygame.display.set_caption("NOCTURNA — El Despertar del Eclipse")
        logo = pygame.image.load("./img/logo.png")
        pygame.display.set_icon(logo)
        info = pygame.display.Info()
        w = max(1100, min(1380, info.current_w - 40))
        h = max(760, min(860, info.current_h - 90))
        self.pantalla = pygame.display.set_mode((w, h), pygame.RESIZABLE)

        self.sim = simulador
        self.fabrica = fabrica
        self.n = TAMANO_MAPA
        self.assets = Assets()

        self.auto_play = False
        self.velocidad_ms = 500
        self._acum = 0
        self.t = 0.0
        self.extincion = False
        self.corriendo = True

        self._cache = {}
        self._fuentes = {}
        self._zonas = []
        self._mouse = (0, 0)
        self._tip = None
        self._arrastrando_vel = False
        self.evento_sel = 0
        self.seleccion = None
        self.insp = None
        self.logs = []
        self.log_scroll = 0
        self._log_lineas = []
        self._log_dirty = True
        self.lluvia = []

        self._layout()
        self.actualizar_vista()

    # ------------------------------------------------------------------
    # Utilidades de dibujo
    # ------------------------------------------------------------------

    def _fuente(self, size, bold=False):
        k = (size, bold)
        if k not in self._fuentes:
            self._fuentes[k] = pygame.font.SysFont(
                "segoeui,calibri,dejavusans,liberationsans,arial", size, bold=bold)
        return self._fuentes[k]

    def _recortar(self, txt, fnt, ancho):
        if fnt.size(txt)[0] <= ancho:
            return txt
        while len(txt) > 1 and fnt.size(txt + "…")[0] > ancho:
            txt = txt[:-1]
        return txt + "…"

    def _t(self, surf, txt, size, color, pos, bold=False, anchor="topleft", clip_w=None):
        fnt = self._fuente(size, bold)
        if clip_w is not None:
            txt = self._recortar(txt, fnt, clip_w)
        img = fnt.render(txt, True, color)
        r = img.get_rect(**{anchor: pos})
        surf.blit(img, r)
        return r

    def _ajustar(self, texto, fnt, ancho):
        lineas = []
        for parrafo in str(texto).split("\n"):
            actual = ""
            for palabra in parrafo.split(" "):
                prueba = palabra if not actual else actual + " " + palabra
                if fnt.size(prueba)[0] <= ancho or not actual:
                    actual = prueba
                else:
                    lineas.append(actual)
                    actual = palabra
            lineas.append(actual)
        return lineas

    def _panel(self, surf, rect, titulo=None):
        pygame.draw.rect(surf, C_PANEL, rect, border_radius=12)
        pygame.draw.rect(surf, C_BORDE, rect, 1, border_radius=12)
        if titulo:
            pygame.draw.rect(surf, C_ACENTO, (rect.x + 12, rect.y + 11, 3, 17), border_radius=2)
            self._t(surf, titulo, 15, C_TXT, (rect.x + 22, rect.y + 8), bold=True)

    def _barra(self, surf, rect, frac, color):
        pygame.draw.rect(surf, (18, 19, 26), rect, border_radius=rect.h // 2)
        frac = max(0.0, min(1.0, frac))
        if frac > 0:
            r = pygame.Rect(rect.x, rect.y, max(rect.h, int(rect.w * frac)), rect.h)
            pygame.draw.rect(surf, color, r, border_radius=rect.h // 2)

    def _solido(self, color, tam):
        k = ("solido", color, tam)
        if k not in self._cache:
            s = pygame.Surface(tam, pygame.SRCALPHA)
            s.fill(color)
            self._cache[k] = s
        return self._cache[k]

    def _sombra(self, s):
        k = ("sombra", s)
        if k not in self._cache:
            sf = pygame.Surface((s, max(2, s // 3)), pygame.SRCALPHA)
            pygame.draw.ellipse(sf, (0, 0, 0, 95), sf.get_rect())
            self._cache[k] = sf
        return self._cache[k]

    def _boton(self, surf, rect, texto, icono=None, accion=None, activo=False,
               color=None, tip=None):
        hover = rect.collidepoint(self._mouse)
        base = (150, 38, 72) if activo else (color or (50, 54, 72))
        fondo = tuple(min(255, v + 24) for v in base) if hover else base
        pygame.draw.rect(surf, fondo, rect, border_radius=9)
        pygame.draw.rect(surf, (255, 255, 255) if hover else C_BORDE, rect, 1, border_radius=9)
        fnt = self._fuente(14, True)
        ancho_txt = fnt.size(texto)[0] if texto else 0
        ic = 18
        total = ancho_txt + (ic + 8 if icono and texto else (ic if icono else 0))
        x = rect.centerx - total // 2
        if icono:
            self._icono(surf, icono, pygame.Rect(x, rect.centery - ic // 2, ic, ic), C_TXT)
            x += ic + 8
        if texto:
            self._t(surf, texto, 14, C_TXT, (x, rect.centery), bold=True, anchor="midleft")
        if accion:
            self._zonas.append((rect, accion))
        if tip and hover:
            self._tip = [tip]

    def _icono(self, surf, tipo, r, col):
        cx, cy = r.center
        k = min(r.w, r.h) / 2
        if tipo == "play":
            pygame.draw.polygon(surf, col, [(cx - k * .5, cy - k * .75), (cx - k * .5, cy + k * .75),
                                            (cx + k * .8, cy)])
        elif tipo == "ffwd":
            for dx in (-k * .55, k * .15):
                pygame.draw.polygon(surf, col, [(cx + dx - k * .35, cy - k * .7), (cx + dx - k * .35, cy + k * .7),
                                                (cx + dx + k * .6, cy)])
        elif tipo == "pause":
            pygame.draw.rect(surf, col, (cx - k * .6, cy - k * .7, k * .45, k * 1.4))
            pygame.draw.rect(surf, col, (cx + k * .15, cy - k * .7, k * .45, k * 1.4))
        elif tipo == "reset":
            pygame.draw.arc(surf, col, pygame.Rect(cx - k * .7, cy - k * .7, k * 1.4, k * 1.4),
                            math.radians(50), math.radians(330), 3)
            ax, ay = cx + k * .7 * math.cos(math.radians(50)), cy - k * .7 * math.sin(math.radians(50))
            pygame.draw.polygon(surf, col, [(ax - k * .1, ay - k * .6), (ax + k * .55, ay + k * .1),
                                            (ax - k * .5, ay + k * .15)])
        elif tipo == "bolt":
            pygame.draw.polygon(surf, col, [(cx + k * .2, cy - k * .9), (cx - k * .6, cy + k * .1),
                                            (cx - k * .05, cy + k * .1), (cx - k * .25, cy + k * .9),
                                            (cx + k * .6, cy - k * .15), (cx + k * .05, cy - k * .15)])

    def _calavera(self, s):
        k = ("calavera", s)
        if k not in self._cache:
            sf = pygame.Surface((s, s), pygame.SRCALPHA)
            c = s // 2
            pygame.draw.circle(sf, (226, 226, 236), (c, int(s * .42)), int(s * .34))
            pygame.draw.rect(sf, (226, 226, 236), (int(s * .3), int(s * .55), int(s * .4), int(s * .3)),
                             border_radius=3)
            for dx in (-.14, .14):
                pygame.draw.circle(sf, (30, 30, 40), (int(c + s * dx), int(s * .42)), max(2, int(s * .09)))
            pygame.draw.rect(sf, (30, 30, 40), (int(s * .46), int(s * .7), max(1, int(s * .08)), int(s * .12)))
            self._cache[k] = sf
        return self._cache[k]

    def _placeholder(self, texto, color, s):
        k = ("ph", texto, color, s)
        if k not in self._cache:
            sf = pygame.Surface((s, s), pygame.SRCALPHA)
            pygame.draw.circle(sf, color, (s // 2, s // 2), int(s * .42))
            pygame.draw.circle(sf, (15, 23, 42), (s // 2, s // 2), int(s * .42), 2)
            img = self._fuente(max(8, int(s * .42)), True).render(texto, True, (15, 23, 42))
            sf.blit(img, img.get_rect(center=(s // 2, s // 2)))
            self._cache[k] = sf
        return self._cache[k]

    def _gris(self, surf):
        k = ("gris", id(surf))
        if k not in self._cache:
            g = surf.copy()
            g.set_alpha(80)
            self._cache[k] = g
        return self._cache[k]

    # ------------------------------------------------------------------
    # Sprites del dominio
    # ------------------------------------------------------------------

    def _clave_criatura(self, linaje, forma, nombre, etapa):
        nom = _sin_acentos(nombre or "")
        try:
            etapa = int(etapa)
        except (TypeError, ValueError):
            etapa = 1
        if linaje == "vampiro":
            if "solar" in nom:
                return "vampiro_solar"
            if "carmes" in nom:
                return "senor_carmesi"
            if "sanguinar" in nom:
                return "sanguinario"
            if "nocturn" in nom:
                return "nocturno"
            return {1: "nocturno", 2: "sanguinario"}.get(etapa, "senor_carmesi")
        if linaje == "hombre_lobo":
            if forma != "bestia":
                return "lobo_humano"
            if "alfa" in nom:
                return "alfa_lunar"
            if "salvaje" in nom:
                return "bestia_salvaje"
            if "licantrop" in nom:
                return "licantropo"
            return {1: "licantropo", 2: "alfa_lunar"}.get(etapa, "bestia_salvaje")
        if linaje == "zombi":
            if "plaga" in nom or "portador" in nom:
                return "portador_plaga"
            if "coloso" in nom:
                return "coloso"
            if "devorador" in nom:
                return "devorador"
            if "errante" in nom:
                return "errante"
            return {1: "errante", 2: "devorador"}.get(etapa, "coloso")
        return "nocturno"

    def _spr_criatura(self, cr, s):
        clave = self._clave_criatura(cr.linaje, getattr(cr, "forma", None),
                                     getattr(cr, "nombre_evolucion", ""), getattr(cr, "etapa", 1))
        return self._spr_clave(clave, cr.linaje, s)

    def _spr_clave(self, clave, linaje, s):
        img = self.assets.ajustado(ARCH_CRIATURA[clave], s, s)
        if img is None:
            return self._placeholder(SIMBOLOS_LINAJE.get(linaje, "?"),
                                     COLORES_LINAJE.get(linaje, (255, 255, 255)), s)
        return img

    def _spr_construccion(self, cons, s):
        linaje = cons["linaje"]
        if cons["tipo"] == "aldea":
            try:
                nivel = max(1, min(3, int(cons["nivel"])))
            except (TypeError, ValueError, KeyError):
                nivel = 1
            nombre = ARCH_ALDEA.get(linaje, ARCH_ALDEA["vampiro"]).format(n=nivel)
            letra = "A"
        else:
            nombre, letra = ARCH["refugio"], "R"
        img = self.assets.ajustado(nombre, s, s)
        return img or self._placeholder(letra, COLORES_LINAJE.get(linaje, (255, 255, 255)), s)

    def _spr_recurso(self, tipo, s):
        img = self.assets.ajustado(ARCH.get(tipo, ""), s, s) if tipo in ARCH else None
        if img is None:
            col = {"sangre": (255, 107, 129), "carne": (255, 179, 71), "biomasa": (123, 237, 159),
                   "materiales": (56, 189, 248), "antidoto": (74, 222, 128)}.get(tipo, (200, 200, 200))
            return self._placeholder(tipo[:1].upper() if tipo else "?", col, s)
        return img

    def _tile(self, terreno, s, var):
        k = ("tile", terreno, s, var)
        if k in self._cache:
            return self._cache[k]
        arch, tinte = TERRENOS.get(terreno, TERRENOS["sin definir"])
        img = self.assets.exacto(ARCH[arch], s, s)
        if img is None:
            img = pygame.Surface((s, s))
            img.fill(pygame.Color(COLORES_TERRENO.get(terreno, "#1e1f22")))
        else:
            img = img.copy()
        if var & 1 or var & 2:
            img = pygame.transform.flip(img, bool(var & 1), bool(var & 2))
        if tinte:
            img.fill(tinte, special_flags=pygame.BLEND_RGB_MULT)
        self._decorar(img, terreno, s, var)
        self._cache[k] = img
        return img

    def _decorar(self, img, terreno, s, var):
        rnd = random.Random(f"{terreno}{var}")
        if terreno == "pantano":
            for _ in range(2):
                x, y = rnd.randint(2, max(3, s - s // 3)), rnd.randint(2, max(3, s - s // 4))
                pygame.draw.ellipse(img, (58, 120, 105), (x, y, max(3, s // 4), max(2, s // 8)))
                pygame.draw.ellipse(img, (120, 190, 165), (x + 2, y + 1, max(1, s // 10), max(1, s // 16)))
        elif terreno == "cementerio":
            x, y = rnd.randint(2, max(3, s - s // 3)), rnd.randint(2, max(3, s - s // 2))
            w, h = max(4, s // 5), max(6, s // 3)
            pygame.draw.rect(img, (118, 118, 136), (x, y, w, h), border_top_left_radius=w // 2,
                             border_top_right_radius=w // 2)
            pygame.draw.line(img, (55, 55, 70), (x + w // 2, y + 2), (x + w // 2, y + h // 2), 1)
            pygame.draw.line(img, (55, 55, 70), (x + w // 4, y + h // 4), (x + w * 3 // 4, y + h // 4), 1)
        elif terreno == "ruinas":
            for _ in range(2):
                x, y = rnd.randint(2, max(3, s - s // 3)), rnd.randint(2, max(3, s - s // 3))
                pygame.draw.rect(img, (112, 102, 92), (x, y, max(3, s // 5), max(3, s // 6)), border_radius=2)
        elif terreno == "castillo":
            ladrillo = max(4, s // 4)
            for i, y in enumerate(range(0, s, ladrillo)):
                pygame.draw.line(img, (42, 28, 46), (0, y), (s, y), 1)
                for x in range(-(ladrillo if i % 2 else 0), s, ladrillo * 2):
                    pygame.draw.line(img, (42, 28, 46), (x, y), (x, y + ladrillo), 1)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _layout(self):
        self.pantalla = pygame.display.get_surface()
        
        W, H = self.pantalla.get_size()
        pad, top, leyenda = 12, 56, 58
        self.top_h = top

        disp_w = W - 460 - 3 * pad - 16
        disp_h = H - top - 2 * pad - 16 - leyenda
        self.cell = max(14, min(disp_w, disp_h) // self.n)
        side = self.cell * self.n
        self.side = side
        self.map_rect = pygame.Rect(pad + 8, top + pad + 8, side, side)
        self.map_panel = pygame.Rect(pad, top + pad, side + 16, side + 16 + leyenda)
        self.r_leyenda = pygame.Rect(self.map_rect.x, self.map_rect.bottom + 6, side, leyenda - 6)

        x = self.map_panel.right + pad
        w = max(300, W - x - pad)
        y = top + pad
        self.r_ctrl = pygame.Rect(x, y, w, 160); y += 170
        self.r_stats = pygame.Rect(x, y, w, 244); y += 254
        self.r_insp = pygame.Rect(x, y, w, 150); y += 160
        self.r_log = pygame.Rect(x, y, w, max(90, H - y - pad))
        self._log_dirty = True

        # fondo degradado
        fondo = pygame.Surface((W, H))
        for i in range(H):
            t = i / max(1, H - 1)
            col = tuple(int(C_FONDO_A[j] + (C_FONDO_B[j] - C_FONDO_A[j]) * t) for j in range(3))
            pygame.draw.line(fondo, col, (0, i), (W, i))
        self._fondo = fondo

        # capas del mapa
        self._ov = pygame.Surface((side, side), pygame.SRCALPHA)
        grid = pygame.Surface((side, side), pygame.SRCALPHA)
        for i in range(self.n + 1):
            pygame.draw.line(grid, (0, 0, 0, 55), (i * self.cell, 0), (i * self.cell, side))
            pygame.draw.line(grid, (0, 0, 0, 55), (0, i * self.cell), (side, i * self.cell))
        self._grid = grid

        peq = 48
        vin = pygame.Surface((peq, peq), pygame.SRCALPHA)
        for yy in range(peq):
            for xx in range(peq):
                d = math.hypot(xx - peq / 2 + .5, yy - peq / 2 + .5) / (peq / 2)
                vin.set_at((xx, yy), (0, 0, 0, int(max(0.0, min(1.0, (d - .45) / .75)) * 190)))
        self._vineta = pygame.transform.smoothscale(vin, (side, side))

        rnd = random.Random(7)
        self.lluvia = [[rnd.uniform(0, side), rnd.uniform(0, side), rnd.uniform(.7, 1.3)] for _ in range(90)]

    # ------------------------------------------------------------------
    # Estado (instantánea de la simulación)
    # ------------------------------------------------------------------

    def actualizar_vista(self):
        sim = self.sim
        rec = sim.recursos
        cad = {c["posicion"] for c in rec.cadáveres}
        ant = {a["posicion"] for a in rec.antídotos if a["cantidad"] > 0}

        celdas = []
        for f in range(self.n):
            fila = []
            for c in range(self.n):
                cas = sim.mapa[f][c]
                fuente = rec.consultar_fuente(f, c)
                if fuente and fuente["cantidad"] <= 0:
                    fuente = None
                cr, veneno = None, False
                oid = cas.get("ocupante_id")
                if oid is not None:
                    x = sim.poblacion.buscar_por_id(oid)
                    if x and x.vivo:
                        cr = x
                        try:
                            veneno = bool(sim.combate.esta_envenenado(x))
                        except Exception:
                            veneno = False
                fila.append({
                    "terreno": cas["terreno"],
                    "efectos": set((cas.get("efectos") or {}).keys()),
                    "cons": sim.aldeas.obtener_construccion_en_casilla(f, c),
                    "fuente": fuente,
                    "cr": cr, "veneno": veneno,
                    "cadaver": (f, c) in cad,
                    "antidoto": (f, c) in ant,
                })
            celdas.append(fila)
        self.celdas = celdas

        reloj = sim.reloj
        self.ciclo = reloj.ciclo
        self.periodo = str(reloj.periodo)
        per = _sin_acentos(self.periodo)
        self.es_noche = "noche" in per or "noct" in per

        ev = sim.eventos.evento_activo()
        self.evento_txt = str(ev) if ev else None
        e = _sin_acentos(self.evento_txt or "")
        self.ev_eclipse = "eclipse" in e
        self.ev_luna = "luna" in e
        self.ev_lluvia = "lluvia" in e
        self.ev_incendio = "incendio" in e
        self.ev_clave = ("eclipse" if self.ev_eclipse else "luna_sangre" if self.ev_luna else
                         "lluvia_corrupta" if self.ev_lluvia else "incendio" if self.ev_incendio else None)

        self.guayagod = bool(rec.guayagod_activo)
        self.protegido = getattr(rec, "linaje_protegido_actual", None)

        self.res_linajes = {}
        for linaje in ("vampiro", "hombre_lobo", "zombi"):
            vivas = sim.poblacion.obtener_vivas(linaje)
            aldea = sim.aldeas.consultar_aldea(linaje)
            d = {
                "vivos": len(vivas),
                "rep": max(vivas, key=lambda x: getattr(x, "etapa", 1)) if vivas else None,
                "alim": rec.consultar_reserva(linaje, "alimento"),
                "mat": rec.consultar_reserva(linaje, "materiales"),
                "aldea": None, "estado": "Destruida", "res": None, "res_max": None,
            }
            if aldea and aldea["existe"]:
                d["aldea"] = ("aldea", aldea["nivel"])
                d["estado"] = f"Nvl {aldea['nivel']}"
                d["res"], d["res_max"] = aldea["resistencia"], aldea["resistencia_maxima"]
            elif sim.aldeas.existe_refugio_provisional(linaje):
                d["aldea"] = ("refugio", 1)
                d["estado"] = "Refugio provisional"
            self.res_linajes[linaje] = d

        if self.seleccion:
            self._inspeccionar(*self.seleccion)

    # ------------------------------------------------------------------
    # Dibujo principal
    # ------------------------------------------------------------------

    def _dibujar(self):
        pant = self.pantalla
        self._zonas = []
        self._tip = None
        pant.blit(self._fondo, (0, 0))

        self._dibujar_topbar(pant)
        self._panel(pant, self.map_panel)
        self._dibujar_mapa(pant)
        self._dibujar_leyenda(pant)
        self._dibujar_controles(pant)
        self._dibujar_stats(pant)
        self._dibujar_inspector(pant)
        self._dibujar_log(pant)
        self._dibujar_tip(pant)

    def _dibujar_topbar(self, pant):
        W = pant.get_width()
        pygame.draw.rect(pant, (20, 21, 29), (0, 0, W, self.top_h))
        pygame.draw.line(pant, C_ACENTO, (0, self.top_h - 1), (W, self.top_h - 1), 2)
        self._t(pant, "NOCTURNA", 28, C_ACENTO, (18, 6), bold=True)
        self._t(pant, "El Despertar del Eclipse", 14, C_MUTED, (172, 24))

        x = W - 18
        r = self._t(pant, f"Período: {self.periodo.upper()}", 17, C_AZUL if not self.es_noche else (180, 160, 255),
                    (x, 14), bold=True, anchor="topright")
        r2 = self._t(pant, f"Ciclo {self.ciclo}", 17, C_TXT, (r.left - 24, 14), bold=True, anchor="topright")
        ic = pygame.Rect(0, 0, 30, 30)
        ic.midright = (r2.left - 16, self.top_h // 2)
        cx, cy = ic.center
        if self.es_noche:
            pygame.draw.circle(pant, (225, 225, 245), (cx, cy), 11)
            pygame.draw.circle(pant, (20, 21, 29), (cx + 6, cy - 4), 9)
        else:
            pygame.draw.circle(pant, (253, 224, 71), (cx, cy), 9)
            for a in range(0, 360, 45):
                rad = math.radians(a)
                pygame.draw.line(pant, (253, 224, 71), (cx + 12 * math.cos(rad), cy + 12 * math.sin(rad)),
                                 (cx + 16 * math.cos(rad), cy + 16 * math.sin(rad)), 2)

    # --- mapa ----------------------------------------------------------

    def _dibujar_mapa(self, pant):
        s, n = self.cell, self.n
        ox, oy = self.map_rect.topleft
        pant.set_clip(self.map_rect)

        # 1) terreno y efectos
        for f in range(n):
            for c in range(n):
                d = self.celdas[f][c]
                x, y = ox + c * s, oy + f * s
                pant.blit(self._tile(d["terreno"], s, (f * 7 + c * 13) % 4), (x, y))
                ef = d["efectos"]
                if "contaminacion" in ef:
                    k = ("contam", s)
                    if k not in self._cache:
                        img = self.assets.exacto(ARCH["bosque_contaminado"], s, s)
                        if img is not None:
                            img = img.copy()
                            img.set_alpha(185)
                        else:
                            img = self._solido((140, 60, 200, 95), (s, s))
                        self._cache[k] = img
                    pant.blit(self._cache[k], (x, y))
                if "quemado" in ef:
                    pant.blit(self._solido((18, 12, 10, 150), (s, s)), (x, y))
        pant.blit(self._grid, self.map_rect.topleft)

        # 2) objetos del suelo
        for f in range(n):
            for c in range(n):
                d = self.celdas[f][c]
                x, y = ox + c * s, oy + f * s
                libre = d["cons"] is None and d["cr"] is None
                if d["cadaver"]:
                    tam = int(s * (.6 if libre else .38))
                    pant.blit(self._calavera(tam), (x + 2, y + s - tam - 2))
                fu = d["fuente"]
                if fu:
                    tam = int(s * (.82 if libre else .46))
                    img = self._spr_recurso(fu["tipo"], tam)
                    pos = img.get_rect(center=(x + s // 2, y + s // 2)) if libre else \
                        img.get_rect(bottomright=(x + s - 2, y + s - 2))
                    pant.blit(self._sombra(tam), (pos.x, pos.bottom - tam // 6))
                    pant.blit(img, pos)
                    cap = fu.get("capacidad_maxima") or 0
                    if libre and cap:
                        self._barra(pant, pygame.Rect(x + s // 5, y + s - 6, s * 3 // 5, 3),
                                    fu["cantidad"] / cap, (250, 220, 120))
                if d["antidoto"]:
                    tam = int(s * (.6 if d["fuente"] is None and libre else .4))
                    img = self._spr_recurso("antidoto", tam)
                    pant.blit(img, img.get_rect(topright=(x + s - 2, y + 2)))

        # 3) construcciones y criaturas, fila a fila (solapan bien)
        for f in range(n):
            for c in range(n):
                d = self.celdas[f][c]
                x, y = ox + c * s, oy + f * s
                if d["cons"]:
                    self._dibujar_construccion(pant, d["cons"], x, y, s)
            for c in range(n):
                d = self.celdas[f][c]
                if d["cr"]:
                    self._dibujar_criatura(pant, d["cr"], d["veneno"], ox + c * s, oy + f * s, s)

        # 4) fuego animado
        for f in range(n):
            for c in range(n):
                if "fuego" in self.celdas[f][c]["efectos"]:
                    self._dibujar_fuego(pant, ox + c * s, oy + f * s, s, f * 31 + c * 17)

        # 5) clima / ambiente
        self._dibujar_clima(pant)

        # 6) dragón Guayagod
        if self.guayagod:
            self._dibujar_dragon(pant)

        # 7) selección / hover
        mc = self._celda_en(self._mouse)
        if mc:
            r = pygame.Rect(ox + mc[1] * s, oy + mc[0] * s, s, s)
            pant.blit(self._solido((255, 255, 255, 38), (s, s)), r)
            self._tip_celda(*mc)
        if self.seleccion:
            f, c = self.seleccion
            r = pygame.Rect(ox + c * s, oy + f * s, s, s)
            p = 2 + int(1.5 * (1 + math.sin(self.t * 5)))
            pygame.draw.rect(pant, C_AMBAR, r.inflate(-2, -2), p, border_radius=5)

        pant.set_clip(None)
        pygame.draw.rect(pant, C_BORDE, self.map_rect.inflate(2, 2), 1)
        self._dibujar_banner(pant)

    def _dibujar_construccion(self, pant, cons, x, y, s):
        col = COLORES_LINAJE.get(cons["linaje"], (255, 255, 255))
        es_aldea = cons["tipo"] == "aldea"
        pygame.draw.rect(pant, col, (x + 2, y + 2, s - 4, s - 4), 2, border_radius=6)
        pant.blit(self._solido(col + (45,), (s - 6, s - 6)), (x + 3, y + 3))
        big = int(s * (1.5 if es_aldea else 1.1))
        img = self._spr_construccion(cons, big)
        pant.blit(self._sombra(int(s * .9)), (x + s // 2 - int(s * .45), y + s - s // 6))
        pant.blit(img, img.get_rect(midbottom=(x + s // 2, y + s - 1)))

    def _dibujar_criatura(self, pant, cr, veneno, x, y, s):
        col = COLORES_LINAJE.get(cr.linaje, (255, 255, 255))
        bob = math.sin(self.t * 3 + cr.id * 1.7) * s * .04
        tam = int(s * .98)
        img = self._spr_criatura(cr, tam)
        pant.blit(self._sombra(int(s * .7)), (x + s // 2 - int(s * .35), y + s - s // 5))
        pygame.draw.ellipse(pant, col, (x + s // 2 - int(s * .33), y + s - s // 5, int(s * .66), s // 5 + 1), 2)
        pant.blit(img, img.get_rect(midbottom=(x + s // 2, y + s - 3 + bob)))
        # barra de vida
        try:
            frac = cr.salud / cr.salud_maxima
        except (ZeroDivisionError, AttributeError, TypeError):
            frac = 1
        color = C_VERDE if frac > .6 else C_AMBAR if frac > .3 else C_ROJO
        self._barra(pant, pygame.Rect(x + s // 6, y + 2, s * 2 // 3, max(3, s // 10)), frac, color)
        if veneno:
            pygame.draw.circle(pant, (120, 255, 90), (x + 6, y + s // 2), max(3, s // 9))
            pygame.draw.circle(pant, (10, 60, 10), (x + 6, y + s // 2), max(3, s // 9), 1)

    def _dibujar_fuego(self, pant, x, y, s, semilla):
        flick = .78 + .22 * math.sin(self.t * 9 + semilla)
        img = self.assets.ajustado(ARCH["incendio"], int(s * 1.1), int(s * 1.1))
        pant.blit(self._solido((255, 90, 20, int(60 * flick)), (s, s)), (x, y))
        if img is not None:
            img.set_alpha(int(255 * flick))
            pant.blit(img, img.get_rect(midbottom=(x + s // 2, y + s)))
        else:
            h = int(s * .7 * flick)
            pygame.draw.polygon(pant, (255, 140, 30), [(x + s * .2, y + s - 2), (x + s // 2, y + s - h),
                                                       (x + s * .8, y + s - 2)])
        pygame.draw.rect(pant, C_ROJO, (x + 2, y + 2, s - 4, s - 4), 2, border_radius=4)

    def _dibujar_clima(self, pant):
        mr, side = self.map_rect, self.side
        if self.es_noche:
            pant.blit(self._solido((12, 18, 62, 80), (side, side)), mr.topleft)
        if self.ev_eclipse:
            pant.blit(self._solido((18, 0, 34, 120), (side, side)), mr.topleft)
            pant.blit(self._vineta, mr.topleft)
        elif self.ev_luna:
            pulso = int(70 + 25 * math.sin(self.t * 1.6))
            pant.blit(self._solido((160, 12, 25, pulso), (side, side)), mr.topleft)
            pant.blit(self._vineta, mr.topleft)
        if self.ev_incendio:
            pant.blit(self._solido((255, 110, 20, 22), (side, side)), mr.topleft)
        if self.ev_lluvia:
            pant.blit(self._solido((70, 30, 105, 55), (side, side)), mr.topleft)
            ov = self._ov
            ov.fill((0, 0, 0, 0))
            for p in self.lluvia:
                pygame.draw.line(ov, (185, 130, 245, 150), (p[0], p[1]), (p[0] - 5, p[1] + 14 * p[2]), 1)
            pant.blit(ov, mr.topleft)

    def _dibujar_dragon(self, pant):
        mr = self.map_rect
        tam = int(self.cell * 3.4)
        x = mr.centerx + math.cos(self.t * .45) * self.side * .30
        y = mr.centery + math.sin(self.t * .7) * self.side * .26
        img = self.assets.ajustado(ARCH["guayagod"], tam, tam)
        if img is None:
            img = self._placeholder("G", (120, 255, 150), tam)
        glow = pygame.Surface((tam, tam), pygame.SRCALPHA)
        pygame.draw.circle(glow, (120, 255, 170, 40), (tam // 2, tam // 2), tam // 2)
        pant.blit(glow, glow.get_rect(center=(x, y)))
        pant.blit(self._sombra(tam // 2), (x - tam // 4, y + tam // 2 + 6))
        img.set_alpha(235)
        pant.blit(img, img.get_rect(center=(x, y + math.sin(self.t * 3) * 4)))

    def _dibujar_banner(self, pant):
        items = []
        if self.ev_clave:
            items.append((ICONO_EVENTO[self.ev_clave], f"Evento: {self.evento_txt.replace('_', ' ').title()}", C_AMBAR))
        if self.guayagod:
            items.append(("guayagod", "Guayagod protege: " + str(self.protegido).replace("_", " "), (120, 255, 170)))
        y = self.map_rect.y + 8
        for clave, txt, col in items:
            fnt = self._fuente(14, True)
            w = fnt.size(txt)[0] + 56
            r = pygame.Rect(0, 0, w, 36)
            r.midtop = (self.map_rect.centerx, y)
            pant.blit(self._solido((10, 10, 16, 200), r.size), r)
            pygame.draw.rect(pant, col, r, 1, border_radius=8)
            ic = self.assets.ajustado(ARCH[clave], 28, 28)
            if ic:
                pant.blit(ic, ic.get_rect(center=(r.x + 20, r.centery)))
            self._t(pant, txt, 14, col, (r.x + 40, r.centery), bold=True, anchor="midleft")
            y += 42
        if self.extincion:
            r = pygame.Rect(0, 0, self.side * .7, 70)
            r.center = self.map_rect.center
            pant.blit(self._solido((10, 0, 4, 215), r.size), r)
            pygame.draw.rect(pant, C_ROJO, r, 2, border_radius=10)
            self._t(pant, "EXTINCIÓN", 34, C_ROJO, r.center, bold=True, anchor="center")

    def _dibujar_leyenda(self, pant):
        items = [("sangre", "Sangre"), ("carne", "Carne"), ("biomasa", "Biomasa"), ("materiales", "Materiales"),
                 ("antidoto", "Antídoto"), ("calavera", "Cadáver"), ("incendio", "Fuego"),
                 ("bosque_contaminado", "Contaminación")]
        r = self.r_leyenda
        cw = r.w / 4
        for i, (clave, txt) in enumerate(items):
            x = r.x + (i % 4) * cw
            y = r.y + (i // 4) * 24 + 2
            if clave == "calavera":
                img = self._calavera(20)
            elif clave in ("incendio", "bosque_contaminado"):
                img = self.assets.ajustado(ARCH[clave], 22, 22, sprite=clave == "incendio") \
                    or self._placeholder("?", (150, 60, 200), 20)
            else:
                img = self._spr_recurso(clave, 22)
            pant.blit(img, img.get_rect(midleft=(x + 4, y + 11)))
            self._t(pant, txt, 12, C_MUTED, (x + 32, y + 11), anchor="midleft")

    # --- paneles derechos ---------------------------------------------

    def _dibujar_controles(self, pant):
        r = self.r_ctrl
        self._panel(pant, r, "Controles de simulación")
        x0, w = r.x + 12, r.w - 24

        n_btn = 3 if self.fabrica else 2
        bw = (w - 8 * (n_btn - 1)) // n_btn
        y = r.y + 38
        self._boton(pant, pygame.Rect(x0, y, bw, 36), "Avanzar ciclo", "play", self.paso_manual,
                    tip="Ejecuta un ciclo (Espacio)")
        self._boton(pant, pygame.Rect(x0 + bw + 8, y, bw, 36),
                    "Pausar" if self.auto_play else "Auto-play",
                    "pause" if self.auto_play else "ffwd", self.toggle_auto, activo=self.auto_play,
                    tip="Alterna el avance automático (A)")
        if self.fabrica:
            self._boton(pant, pygame.Rect(x0 + 2 * (bw + 8), y, bw, 36), "Reiniciar", "reset",
                        self.reiniciar, tip="Crea una partida nueva (R)")

        # deslizador de velocidad
        y = r.y + 86
        self._t(pant, "Velocidad", 14, C_MUTED, (x0, y + 2))
        tr = pygame.Rect(x0 + 84, y + 8, w - 84 - 80, 6)
        self._slider = tr
        pygame.draw.rect(pant, (18, 19, 26), tr, border_radius=3)
        frac = (VEL_MAX - self.velocidad_ms) / (VEL_MAX - VEL_MIN)
        pygame.draw.rect(pant, C_ACENTO, (tr.x, tr.y, int(tr.w * frac), tr.h), border_radius=3)
        pygame.draw.circle(pant, C_TXT, (tr.x + int(tr.w * frac), tr.centery), 9)
        pygame.draw.circle(pant, C_ACENTO, (tr.x + int(tr.w * frac), tr.centery), 9, 2)
        self._t(pant, f"{self.velocidad_ms} ms", 13, C_TXT, (r.right - 14, y + 11), anchor="midright")

        # forzar evento
        y = r.y + 112
        self._t(pant, "Forzar evento", 14, C_MUTED, (x0, y + 22), anchor="midleft")
        bx = x0 + 112
        for i, ev in enumerate(EVENTOS_FORZABLES):
            br = pygame.Rect(bx + i * 46, y + 2, 42, 42)
            self._boton(pant, br, "", None, lambda i=i: setattr(self, "evento_sel", i),
                        activo=(i == self.evento_sel), tip=ev.replace("_", " ").title())
            ic = self.assets.ajustado(ARCH[ICONO_EVENTO[ev]], 32, 32)
            if ic:
                pant.blit(ic, ic.get_rect(center=br.center))
            else:
                self._t(pant, ev[0].upper(), 16, C_TXT, br.center, bold=True, anchor="center")
        ar = pygame.Rect(bx + 4 * 46 + 6, y + 4, max(80, r.right - 12 - (bx + 4 * 46 + 6)), 38)
        self._boton(pant, ar, "Activar", "bolt", self.forzar_evento_gui, color=(120, 40, 60),
                    tip="Fuerza el evento seleccionado")

    def _dibujar_stats(self, pant):
        r = self.r_stats
        self._panel(pant, r, "Ecosistema y reservas")
        x0, w = r.x + 12, r.w - 24

        # chips: evento / Guayagod
        cw = (w - 8) // 2
        y = r.y + 34
        chips = [
            (self.ev_clave and ICONO_EVENTO[self.ev_clave],
             "Evento: " + (self.evento_txt.replace("_", " ").title() if self.evento_txt else "Ninguno"),
             C_AMBAR if self.evento_txt else C_MUTED),
            ("guayagod", "Guayagod: " + (f"ACTIVO ({str(self.protegido).replace('_', ' ')})"
                                         if self.guayagod else "Inactivo"),
             (120, 255, 170) if self.guayagod else C_MUTED),
        ]
        for i, (clave, txt, col) in enumerate(chips):
            cr = pygame.Rect(x0 + i * (cw + 8), y, cw, 34)
            pygame.draw.rect(pant, C_PANEL2, cr, border_radius=8)
            pygame.draw.rect(pant, col if col != C_MUTED else C_BORDE, cr, 1, border_radius=8)
            ic = self.assets.ajustado(ARCH[clave], 26, 26) if clave else None
            if ic:
                if clave == "guayagod" and not self.guayagod:
                    ic = self._gris(ic)
                pant.blit(ic, ic.get_rect(center=(cr.x + 20, cr.centery)))
            self._t(pant, txt, 12, col, (cr.x + 38, cr.centery), bold=True, anchor="midleft", clip_w=cr.w - 44)

        # tarjetas por linaje
        y = r.y + 76
        for linaje in ("vampiro", "hombre_lobo", "zombi"):
            d = self.res_linajes[linaje]
            col = COLORES_LINAJE[linaje]
            cr = pygame.Rect(x0, y, w, 48)
            pygame.draw.rect(pant, C_PANEL2, cr, border_radius=9)
            pygame.draw.rect(pant, col, (cr.x, cr.y + 4, 4, cr.h - 8), border_radius=2)

            if d["rep"] is not None:
                por = self._spr_criatura(d["rep"], 42)
            else:
                base = {"vampiro": "nocturno", "hombre_lobo": "lobo_humano", "zombi": "errante"}[linaje]
                por = self._gris(self._spr_clave(base, linaje, 42))
            pant.blit(por, por.get_rect(center=(cr.x + 30, cr.centery)))

            self._t(pant, NOMBRES_LINAJE[linaje], 13, col, (cr.x + 56, cr.y + 7), bold=True, clip_w=96)
            self._t(pant, f"Vivos: {d['vivos']}", 12, C_TXT if d["vivos"] else C_ROJO, (cr.x + 56, cr.y + 26))

            for j, (clave, val) in enumerate(((RECURSO_ALIMENTO[linaje], d["alim"]), ("materiales", d["mat"]))):
                ix = cr.x + 156 + j * 64
                pant.blit(self._spr_recurso(clave, 24), (ix, cr.centery - 12))
                self._t(pant, str(val), 14, C_TXT, (ix + 28, cr.centery), bold=True, anchor="midleft")

            ax = cr.x + 290
            if d["aldea"]:
                tipo, nivel = d["aldea"]
                cons = {"linaje": linaje, "tipo": tipo, "nivel": nivel}
                sp = self._spr_construccion(cons, 40)
                pant.blit(sp, sp.get_rect(center=(ax + 18, cr.centery)))
            else:
                cx, cy = ax + 18, cr.centery
                pygame.draw.line(pant, C_ROJO, (cx - 9, cy - 9), (cx + 9, cy + 9), 3)
                pygame.draw.line(pant, C_ROJO, (cx - 9, cy + 9), (cx + 9, cy - 9), 3)
            tx = ax + 42
            ancho = max(40, cr.right - tx - 8)
            self._t(pant, d["estado"], 12, C_TXT if d["aldea"] else C_ROJO, (tx, cr.y + 6), bold=True, clip_w=ancho)
            if isinstance(d["res"], (int, float)) and isinstance(d["res_max"], (int, float)) and d["res_max"]:
                self._barra(pant, pygame.Rect(tx, cr.y + 26, ancho, 6), d["res"] / d["res_max"], C_AZUL)
                self._t(pant, f"{_fmt(d['res'])}/{_fmt(d['res_max'])}", 11, C_MUTED, (tx, cr.y + 33))
            elif d["aldea"] and d["aldea"][0] == "aldea":
                self._t(pant, f"Res. {_fmt(d['res'])}/{_fmt(d['res_max'])}", 11, C_MUTED, (tx, cr.y + 27))
            y += 52

    def _dibujar_inspector(self, pant):
        r = self.r_insp
        self._panel(pant, r, "Inspector de casilla (clic en el mapa)")
        inner = pygame.Rect(r.x + 12, r.y + 34, r.w - 24, r.h - 44)
        if not self.insp:
            fnt = self._fuente(13)
            for i, l in enumerate(self._ajustar(
                    "Selecciona una casilla para ver terreno, recursos o atributos de la criatura.",
                    fnt, inner.w)):
                self._t(pant, l, 13, C_MUTED, (inner.x, inner.y + i * 18))
            return
        caja = pygame.Rect(inner.x, inner.y, 76, 76)
        pygame.draw.rect(pant, (18, 19, 26), caja, border_radius=10)
        pygame.draw.rect(pant, C_BORDE, caja, 1, border_radius=10)
        img = self._spr_insp(self.insp["sprite"], 68)
        if img:
            pant.blit(img, img.get_rect(center=caja.center))
        by = caja.bottom + 6
        if self.insp["hp"]:
            self._barra(pant, pygame.Rect(caja.x, by, caja.w, 6), self.insp["hp"][0] / max(1, self.insp["hp"][1]), C_VERDE)
            self._barra(pant, pygame.Rect(caja.x, by + 9, caja.w, 6), self.insp["en"][0] / max(1, self.insp["en"][1]), C_AZUL)

        tx = caja.right + 14
        fnt = self._fuente(13)
        pant.set_clip(pygame.Rect(tx, inner.y, inner.right - tx, inner.h + 6))
        y = inner.y
        for texto, col in self.insp["lineas"]:
            for l in self._ajustar(texto, fnt, inner.right - tx):
                self._t(pant, l, 13, col, (tx, y))
                y += 17
        pant.set_clip(None)

    def _dibujar_log(self, pant):
        r = self.r_log
        self._panel(pant, r, "Bitácora del mundo")
        area = pygame.Rect(r.x + 10, r.y + 34, r.w - 26, r.h - 42)
        pygame.draw.rect(pant, (18, 19, 26), area.inflate(8, 6), border_radius=8)
        fnt = self._fuente(12)
        lh = 15
        if self._log_dirty:
            self._log_lineas = []
            for txt, col in self.logs:
                for i, l in enumerate(self._ajustar(txt, fnt, area.w)):
                    self._log_lineas.append(((" " if i else "") + l, col))
            self._log_dirty = False
        vis = max(1, area.h // lh)
        total = len(self._log_lineas)
        self.log_scroll = max(0, min(self.log_scroll, max(0, total - vis)))
        fin = total - self.log_scroll
        ini = max(0, fin - vis)
        pant.set_clip(area.inflate(0, 4))
        for i, (l, col) in enumerate(self._log_lineas[ini:fin]):
            self._t(pant, l, 12, col, (area.x, area.y + i * lh))
        pant.set_clip(None)
        if total > vis:
            sb = pygame.Rect(r.right - 12, area.y, 4, area.h)
            pygame.draw.rect(pant, (40, 42, 56), sb, border_radius=2)
            h = max(14, int(sb.h * vis / total))
            top = int((sb.h - h) * (ini / max(1, total - vis)))
            pygame.draw.rect(pant, C_MUTED, (sb.x, sb.y + top, 4, h), border_radius=2)
        self._rect_log_area = area

    def _dibujar_tip(self, pant):
        if not self._tip:
            return
        fnt = self._fuente(13)
        w = max(fnt.size(l)[0] for l in self._tip) + 16
        h = len(self._tip) * 17 + 10
        x, y = self._mouse[0] + 16, self._mouse[1] + 16
        W, H = pant.get_size()
        x, y = min(x, W - w - 4), min(y, H - h - 4)
        r = pygame.Rect(x, y, w, h)
        pant.blit(self._solido((8, 8, 14, 235), r.size), r)
        pygame.draw.rect(pant, C_BORDE, r, 1, border_radius=6)
        for i, l in enumerate(self._tip):
            self._t(pant, l, 13, C_TXT, (x + 8, y + 5 + i * 17))

    # ------------------------------------------------------------------
    # Inspector y tooltip
    # ------------------------------------------------------------------

    def _celda_en(self, pos):
        if not self.map_rect.collidepoint(pos):
            return None
        c = (pos[0] - self.map_rect.x) // self.cell
        f = (pos[1] - self.map_rect.y) // self.cell
        if 0 <= f < self.n and 0 <= c < self.n:
            return (f, c)
        return None

    def _tip_celda(self, f, c):
        d = self.celdas[f][c]
        l = [f"({f}, {c}) · {d['terreno']}"]
        if d["cr"]:
            cr = d["cr"]
            l.append(f"{cr.linaje.replace('_', ' ').title()} #{cr.id} · HP {cr.salud}/{cr.salud_maxima}")
        if d["cons"]:
            l.append(f"{d['cons']['tipo'].replace('_', ' ').title()} de {d['cons']['linaje']}")
        if d["fuente"]:
            l.append(f"{d['fuente']['tipo']} ×{d['fuente']['cantidad']}")
        if d["efectos"]:
            l.append("Efectos: " + ", ".join(sorted(d["efectos"])))
        self._tip = l

    def _spr_insp(self, sprite, s):
        tipo, arg = sprite
        if tipo == "criatura":
            return self._spr_criatura(arg, s)
        if tipo == "cons":
            return self._spr_construccion(arg, s)
        if tipo == "recurso":
            return self._spr_recurso(arg, s)
        if tipo == "cadaver":
            return self._calavera(s)
        return self._tile(arg, s, 0)

    def _inspeccionar(self, f, c):
        sim, rec = self.sim, self.sim.recursos
        cas = sim.mapa[f][c]
        L = [(f"Casilla ({f}, {c}) — terreno: {cas['terreno']}", C_TXT)]
        sprite, hp, en = ("terreno", cas["terreno"]), None, None

        if cas["efectos"]:
            L.append(("Efectos: " + ", ".join(f"{k} ({v})" for k, v in cas["efectos"].items()), C_MORADO))

        cons = sim.aldeas.obtener_construccion_en_casilla(f, c)
        fuente = rec.consultar_fuente(f, c)
        cads = [cad for cad in rec.cadáveres if cad["posicion"] == (f, c)]
        ants = [a for a in rec.antídotos if a["posicion"] == (f, c) and a["cantidad"] > 0]

        if cads:
            sprite = ("cadaver", None)
        if ants:
            sprite = ("recurso", "antidoto")
        if fuente:
            sprite = ("recurso", fuente["tipo"])
        if cons:
            sprite = ("cons", cons)
            esp = sim.aldeas.consultar_espacio(cons["linaje"])
            L.append((f"{cons['tipo'].replace('_', ' ').title()} de {cons['linaje']} "
                      f"(nivel {cons['nivel']}, resistencia {_fmt(cons['resistencia'])}, "
                      f"alojados {esp['ocupados']}/{_fmt(esp['capacidad'])})",
                      COLORES_LINAJE.get(cons["linaje"], C_TXT)))
        if fuente:
            L.append((f"Recurso: {fuente['tipo']} ({fuente['cantidad']}/{fuente['capacidad_maxima']})", C_AMBAR))
        for cad in cads:
            L.append((f"Cadáver de {cad['linaje']} (ID {cad['id_criatura']}), "
                      f"{cad['duracion_restante']} ciclos restantes", C_MUTED))
        for a in ants:
            L.append((f"Antídoto x{a['cantidad']}", C_VERDE))

        oid = cas.get("ocupante_id")
        if oid is not None:
            cr = sim.poblacion.buscar_por_id(oid)
            if cr:
                forma = f" ({cr.forma})" if cr.forma else ""
                veneno = " · ENVENENADA" if sim.combate.esta_envenenado(cr) else ""
                col = COLORES_LINAJE.get(cr.linaje, C_TXT)
                L.append((f"Criatura #{cr.id} [{cr.linaje.upper()}{forma} — {cr.nombre_evolucion}, etapa {cr.etapa}]", col))
                L.append((f"HP {cr.salud}/{cr.salud_maxima} · EN {cr.energia}/{cr.energia_maxima} · "
                          f"SAC {cr.saciedad} · ATQ {cr.ataque} · DEF {cr.defensa} · XP {cr.xp} · "
                          f"AFD {cr.estado_afd}{veneno}", C_TXT))
                if cr.vivo:
                    sprite = ("criatura", cr)
                    hp, en = (cr.salud, cr.salud_maxima), (cr.energia, cr.energia_maxima)
        self.insp = {"lineas": L, "sprite": sprite, "hp": hp, "en": en}

    # ------------------------------------------------------------------
    # Controles
    # ------------------------------------------------------------------

    @staticmethod
    def _color_log(msg):
        m = _sin_acentos(msg)
        if any(k in m for k in ("extin", "muere", "muerte", "destru", "[error")):
            return (248, 113, 113)
        if any(k in m for k in ("evento", "eclipse", "luna", "lluvia", "incendio", "guayagod", "[manual")):
            return C_AMBAR
        if any(k in m for k in ("evolu", "nace", "naci", "construy", "mejor")):
            return (134, 239, 172)
        return (203, 213, 225)

    def agregar_logs(self, mensajes):
        if not mensajes:
            return
        for msg in mensajes:
            self.logs.append((str(msg), self._color_log(str(msg))))
        self.logs = self.logs[-600:]
        self._log_dirty = True
        self.log_scroll = 0

    def paso_manual(self):
        try:
            resumen = self.sim.ejecutar_ciclo()           # devuelve un dict, no una lista de textos
            self.agregar_logs(self.sim.resumen_a_logs(resumen))
        except Exception as exc:                          # no cerrar la ventana por un fallo de la simulación
            self.auto_play = False
            self.agregar_logs([f"[Error] {type(exc).__name__}: {exc}"])
            return None
        if resumen.get("extincion"):
            self.extincion = True
            self.auto_play = False
        self.actualizar_vista()
        return resumen

    def toggle_auto(self):
        if self.extincion:
            return
        self.auto_play = not self.auto_play
        self._acum = 0

    def reiniciar(self):
        if self.fabrica is None:
            return
        self.auto_play = False
        self.extincion = False
        self.sim = self.fabrica()
        self.logs, self._log_lineas, self._log_dirty = [], [], True
        self.seleccion, self.insp = None, None
        self.agregar_logs(["Simulación reiniciada."])
        self.actualizar_vista()

    def forzar_evento_gui(self):
        tipo = EVENTOS_FORZABLES[self.evento_sel]
        ev = self.sim.eventos.forzar_evento(
            tipo, self.sim.reloj.ciclo, mapa=self.sim.mapa,
            recursos=self.sim.recursos, aldeas=self.sim.aldeas,
            registro=self.sim.registro, poblacion=self.sim.poblacion
        )
        if ev:
            self.agregar_logs([f"[Manual] Evento forzado: {ev['nombre']} en el ciclo {self.sim.reloj.ciclo}"])
            self.actualizar_vista()

    def _set_velocidad_desde_x(self, x):
        tr = self._slider
        frac = max(0.0, min(1.0, (x - tr.x) / tr.w))
        self.velocidad_ms = int(VEL_MAX - frac * (VEL_MAX - VEL_MIN))

    # ------------------------------------------------------------------
    # Bucle principal
    # ------------------------------------------------------------------

    def _evento(self, ev):
        if ev.type == pygame.QUIT:
            self.corriendo = False
        elif ev.type == pygame.VIDEORESIZE:
            self._layout()
        elif ev.type == pygame.MOUSEMOTION:
            self._mouse = ev.pos
            if self._arrastrando_vel:
                self._set_velocidad_desde_x(ev.pos[0])
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self._arrastrando_vel = False
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self._mouse = ev.pos
            for rect, fn in reversed(self._zonas):
                if rect.collidepoint(ev.pos):
                    fn()
                    return
            if getattr(self, "_slider", None) and self._slider.inflate(16, 24).collidepoint(ev.pos):
                self._arrastrando_vel = True
                self._set_velocidad_desde_x(ev.pos[0])
                return
            cel = self._celda_en(ev.pos)
            if cel:
                self.seleccion = cel
                self._inspeccionar(*cel)
        elif ev.type == pygame.MOUSEWHEEL:
            if self.r_log.collidepoint(self._mouse):
                self.log_scroll = max(0, self.log_scroll + ev.y * 3)
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.corriendo = False
            elif ev.key == pygame.K_SPACE:
                self.paso_manual()
            elif ev.key == pygame.K_a:
                self.toggle_auto()
            elif ev.key == pygame.K_r:
                self.reiniciar()
            elif ev.key == pygame.K_UP:
                self.velocidad_ms = max(VEL_MIN, self.velocidad_ms - 50)
            elif ev.key == pygame.K_DOWN:
                self.velocidad_ms = min(VEL_MAX, self.velocidad_ms + 50)

    def _actualizar(self, dt):
        self.t += dt / 1000.0
        if self.auto_play and not self.extincion:
            self._acum += dt
            if self._acum >= self.velocidad_ms:
                self._acum = 0
                self.paso_manual()
        if self.ev_lluvia:
            for p in self.lluvia:
                p[1] += 420 * p[2] * dt / 1000.0
                p[0] -= 150 * p[2] * dt / 1000.0
                if p[1] > self.side or p[0] < 0:
                    p[0] = random.uniform(0, self.side + 40)
                    p[1] = -15

    def run(self):
        reloj = pygame.time.Clock()
        self._mouse = pygame.mouse.get_pos()
        avisado = False
        while self.corriendo:
            dt = reloj.tick(60)
            for ev in pygame.event.get():
                self._evento(ev)
            self._actualizar(dt)
            self._dibujar()
            pygame.display.flip()
            if not avisado and self.t > 1.0:      # las imágenes se cargan al usarse: avisar tras el 1er segundo
                avisado = True
                if self.assets.faltantes:
                    print("[gui] Imágenes no encontradas (se usan marcadores):")
                    for n in self.assets.faltantes:
                        print("   -", n)
        pygame.quit()


def iniciar_gui(simulacion, fabrica=None):
    """Punto de entrada que usa main.py: abre la ventana y entra al bucle de Pygame."""
    InterfazNocturnaGUI(simulacion, fabrica=fabrica).run()
