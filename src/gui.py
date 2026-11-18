# =====================================================================
# NOCTURNA: El Despertar del Eclipse - Módulo: gui.py (P12)
# Interfaz gráfica con Tkinter. Solo LEE el estado de la Simulacion y
# llama a sim.ejecutar_ciclo(); no contiene reglas del juego.
# =====================================================================

import tkinter as tk
from tkinter import ttk, scrolledtext

from config import TAMANO_MAPA

COLORES_TERRENO = {
    "camino": "#2b2d31",
    "bosque": "#1e3a29",
    "pantano": "#26362c",
    "cementerio": "#383642",
    "ruinas": "#47433e",
    "castillo": "#3d2c3e",
    "sin definir": "#1e1f22",
}

COLORES_LINAJE = {
    "vampiro": "#e63946",      # Rojo carmesí
    "hombre_lobo": "#f4a261",  # Ámbar / Naranja
    "zombi": "#52b788",        # Verde necrótico
}

SIMBOLOS_LINAJE = {"vampiro": "V", "hombre_lobo": "L", "zombi": "Z"}

COLORES_RECURSO = {
    "sangre": "#ff6b81",
    "carne": "#ffb347",
    "biomasa": "#7bed9f",
    "materiales": "#38bdf8",
}

EVENTOS_FORZABLES = ["eclipse", "luna_sangre", "lluvia_corrupta", "incendio"]


def _fmt(valor):
    """Muestra 'n/d' cuando un dato oficial sigue pendiente (None) en config.py."""
    return "n/d" if valor is None else str(valor)


class InterfazNocturnaGUI:
    def __init__(self, root, simulador, fabrica=None):
        """
        root: ventana tk.Tk().
        simulador: instancia de Simulacion.
        fabrica: función sin argumentos que crea una Simulacion nueva
                 (habilita el botón Reiniciar).
        """
        self.root = root
        self.sim = simulador
        self.fabrica = fabrica
        self.root.title("NOCTURNA — El Despertar del Eclipse")
        self.root.geometry("1220x780")
        self.root.configure(bg="#141518")

        self.auto_play = False
        self._after_id = None
        self.velocidad_ms = 500
        self.tam_celda = 32
        self.n = TAMANO_MAPA

        self._construir_estilos()
        self._construir_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.actualizar_vista()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------

    def _construir_estilos(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#141518")
        style.configure("Panel.TFrame", background="#1e2025", relief="flat")
        style.configure("TLabel", background="#1e2025", foreground="#e2e8f0", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#1e2025", foreground="#f8fafc", font=("Segoe UI", 12, "bold"))
        style.configure("Title.TLabel", background="#141518", foreground="#f43f5e", font=("Segoe UI", 15, "bold"))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)

    def _construir_layout(self):
        top_bar = ttk.Frame(self.root)
        top_bar.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(10, 5))

        ttk.Label(top_bar, text="NOCTURNA: El Despertar del Eclipse", style="Title.TLabel").pack(side=tk.LEFT)

        self.lbl_tiempo = ttk.Label(
            top_bar, text="Ciclo: 0 | Período: DÍA",
            font=("Segoe UI", 12, "bold"), background="#141518", foreground="#38bdf8"
        )
        self.lbl_tiempo.pack(side=tk.RIGHT, padx=10)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # --- Izquierda: mapa ---
        left_frame = ttk.Frame(main_frame, style="Panel.TFrame", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        lado = self.tam_celda * self.n
        self.canvas = tk.Canvas(
            left_frame, width=lado, height=lado,
            bg="#111215", highlightthickness=1, highlightbackground="#334155"
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click_mapa)

        ttk.Label(
            left_frame,
            text="[V] Vampiro  [L/B] Lobo humano/bestia  [Z] Zombi  [A] Aldea  [R] Refugio  "
                 "[x] Cadáver  [+] Antídoto  [•] Recurso  | borde rojo: fuego · morado: contaminación",
            font=("Segoe UI", 8), foreground="#94a3b8", wraplength=lado
        ).pack(anchor=tk.W, pady=(8, 0))

        # --- Derecha ---
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(15, 0))

        # Controles
        ctrl_frame = ttk.Frame(right_frame, style="Panel.TFrame", padding=10)
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(ctrl_frame, text="Controles de Simulación", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 8))

        fila1 = ttk.Frame(ctrl_frame, style="Panel.TFrame")
        fila1.pack(fill=tk.X)
        self.btn_paso = ttk.Button(fila1, text="▶ Avanzar 1 Ciclo", command=self.paso_manual)
        self.btn_paso.pack(side=tk.LEFT, padx=(0, 6))
        self.btn_auto = ttk.Button(fila1, text="⏩ Auto-Play", command=self.toggle_auto)
        self.btn_auto.pack(side=tk.LEFT, padx=6)
        if self.fabrica is not None:
            ttk.Button(fila1, text="↺ Reiniciar", command=self.reiniciar).pack(side=tk.LEFT, padx=6)

        ttk.Label(fila1, text="Velocidad:", padding=(12, 0, 4, 0)).pack(side=tk.LEFT)
        self.escala_vel = ttk.Scale(fila1, from_=50, to=1500, orient=tk.HORIZONTAL, length=110,
                                    command=self._cambiar_velocidad)
        self.escala_vel.set(1550 - self.velocidad_ms)  # a la derecha = más rápido
        self.escala_vel.pack(side=tk.LEFT)

        fila2 = ttk.Frame(ctrl_frame, style="Panel.TFrame")
        fila2.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(fila2, text="Forzar evento:").pack(side=tk.LEFT)
        self.combo_evento = ttk.Combobox(fila2, values=EVENTOS_FORZABLES, state="readonly", width=15)
        self.combo_evento.current(0)
        self.combo_evento.pack(side=tk.LEFT, padx=4)
        ttk.Button(fila2, text="Activar", command=self.forzar_evento_gui).pack(side=tk.LEFT, padx=4)

        # Ecosistema
        stats_frame = ttk.Frame(right_frame, style="Panel.TFrame", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(stats_frame, text="Estado del Ecosistema y Reservas", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 6))

        self.lbl_evento = ttk.Label(
            stats_frame, text="Evento Activo: Ninguno | Guayagod: Inactivo",
            foreground="#fbbf24", font=("Segoe UI", 10, "bold")
        )
        self.lbl_evento.pack(anchor=tk.W, pady=(0, 6))

        self.txt_stats = tk.Text(
            stats_frame, height=5, bg="#141518", fg="#e2e8f0",
            font=("Consolas", 10), relief="flat", padx=8, pady=6
        )
        self.txt_stats.pack(fill=tk.X)
        self.txt_stats.config(state=tk.DISABLED)

        # Inspector
        insp_frame = ttk.Frame(right_frame, style="Panel.TFrame", padding=10)
        insp_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(insp_frame, text="Inspector de Casilla (clic en el mapa)", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))
        self.lbl_inspector = ttk.Label(
            insp_frame,
            text="Selecciona una casilla para ver terreno, recursos o atributos de la criatura.",
            foreground="#94a3b8", wraplength=500, justify=tk.LEFT
        )
        self.lbl_inspector.pack(anchor=tk.W)

        # Bitácora
        log_frame = ttk.Frame(right_frame, style="Panel.TFrame", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(log_frame, text="Bitácora del Mundo", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 6))
        self.txt_logs = scrolledtext.ScrolledText(
            log_frame, bg="#141518", fg="#cbd5e1",
            font=("Consolas", 9), relief="flat", padx=8, pady=6
        )
        self.txt_logs.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------

    def dibujar_mapa(self):
        self.canvas.delete("all")
        t = self.tam_celda
        recursos = self.sim.recursos

        # Posiciones de cadáveres y antídotos, calculadas una sola vez por dibujo
        cadaveres = {c["posicion"] for c in recursos.cadáveres}
        antidotos = {a["posicion"] for a in recursos.antídotos if a["cantidad"] > 0}

        for f in range(self.n):
            for c in range(self.n):
                casilla = self.sim.mapa[f][c]
                x1, y1 = c * t, f * t
                x2, y2 = x1 + t, y1 + t

                color = COLORES_TERRENO.get(casilla["terreno"], "#1e1f22")
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#262930")

                # Efectos ambientales
                efectos = casilla.get("efectos", {})
                if "fuego" in efectos:
                    self.canvas.create_rectangle(x1 + 2, y1 + 2, x2 - 2, y2 - 2, outline="#ef4444", width=2)
                elif "contaminacion" in efectos:
                    self.canvas.create_rectangle(x1 + 2, y1 + 2, x2 - 2, y2 - 2, outline="#a855f7", width=2)
                elif "quemado" in efectos:
                    self.canvas.create_rectangle(x1 + 2, y1 + 2, x2 - 2, y2 - 2, outline="#57534e", width=1)

                # Construcciones: aldea (A) o refugio provisional (R)
                construccion = self.sim.aldeas.obtener_construccion_en_casilla(f, c)
                if construccion:
                    col = COLORES_LINAJE.get(construccion["linaje"], "#ffffff")
                    letra = "A" if construccion["tipo"] == "aldea" else "R"
                    self.canvas.create_rectangle(x1 + 3, y1 + 3, x2 - 3, y2 - 3, outline=col, width=2)
                    self.canvas.create_text(x1 + 9, y1 + 8, text=letra, fill=col, font=("Segoe UI", 7, "bold"))

                # Fuentes de recursos (color según tipo)
                fuente = recursos.consultar_fuente(f, c)
                if fuente and fuente["cantidad"] > 0:
                    col = COLORES_RECURSO.get(fuente["tipo"], "#38bdf8")
                    self.canvas.create_oval(x2 - 11, y2 - 11, x2 - 4, y2 - 4, fill=col, outline="")

                if (f, c) in cadaveres:
                    self.canvas.create_text(x1 + 9, y2 - 9, text="x", fill="#cbd5e1", font=("Segoe UI", 9, "bold"))
                if (f, c) in antidotos:
                    self.canvas.create_text(x2 - 9, y1 + 9, text="+", fill="#4ade80", font=("Segoe UI", 10, "bold"))

                # Criatura
                occ_id = casilla.get("ocupante_id")
                if occ_id is not None:
                    cr = self.sim.poblacion.buscar_por_id(occ_id)
                    if cr and cr.vivo:
                        col_c = COLORES_LINAJE.get(cr.linaje, "#ffffff")
                        simb = SIMBOLOS_LINAJE.get(cr.linaje, "?")
                        if cr.linaje == "hombre_lobo" and cr.forma == "bestia":
                            simb = "B"
                        self.canvas.create_oval(x1 + 5, y1 + 5, x2 - 5, y2 - 5,
                                                fill=col_c, outline="#0f172a", width=1.5)
                        self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=simb,
                                                fill="#0f172a", font=("Segoe UI", 10, "bold"))

    def actualizar_estadisticas(self):
        reloj = self.sim.reloj
        self.lbl_tiempo.config(text=f"Ciclo: {reloj.ciclo}  |  Período: {reloj.periodo.upper()}")

        ev = self.sim.eventos.evento_activo() or "Ninguno"
        rec = self.sim.recursos
        if rec.guayagod_activo:
            guayagod = f"ACTIVO (protege: {rec.linaje_protegido_actual})"
        else:
            guayagod = "Inactivo"
        self.lbl_evento.config(text=f"Evento activo: {ev}   |   Guayagod: {guayagod}")

        lineas = [f"{'LINAJE':<13} | {'VIVOS':<5} | {'ALIM.':<5} | {'MAT.':<5} | ALDEA (NIVEL / RESISTENCIA)",
                  "-" * 66]
        for linaje in ("vampiro", "hombre_lobo", "zombi"):
            vivos = len(self.sim.poblacion.obtener_vivas(linaje))
            alim = rec.consultar_reserva(linaje, "alimento")
            mat = rec.consultar_reserva(linaje, "materiales")
            aldea = self.sim.aldeas.consultar_aldea(linaje)
            if aldea and aldea["existe"]:
                info = f"Nvl {aldea['nivel']} ({_fmt(aldea['resistencia'])}/{_fmt(aldea['resistencia_maxima'])})"
            elif self.sim.aldeas.existe_refugio_provisional(linaje):
                info = "Refugio provisional"
            else:
                info = "Destruida"
            lineas.append(f"{linaje.upper():<13} | {vivos:<5} | {alim:<5} | {mat:<5} | {info}")

        self.txt_stats.config(state=tk.NORMAL)
        self.txt_stats.delete("1.0", tk.END)
        self.txt_stats.insert(tk.END, "\n".join(lineas))
        self.txt_stats.config(state=tk.DISABLED)

    def actualizar_vista(self):
        self.dibujar_mapa()
        self.actualizar_estadisticas()

    def agregar_logs(self, mensajes):
        if not mensajes:
            return
        for msg in mensajes:
            self.txt_logs.insert(tk.END, msg + "\n")
        self.txt_logs.see(tk.END)

    # ------------------------------------------------------------------
    # Controles
    # ------------------------------------------------------------------

    def paso_manual(self):
        resumen = self.sim.ejecutar_ciclo()          # devuelve un dict, no una lista de textos
        self.agregar_logs(self.sim.resumen_a_logs(resumen))
        self.actualizar_vista()
        if resumen.get("extincion") and self.auto_play:
            self.toggle_auto()
        return resumen

    def toggle_auto(self):
        self.auto_play = not self.auto_play
        self.btn_auto.config(text="⏸ Pausar" if self.auto_play else "⏩ Auto-Play")
        if self.auto_play:
            self._bucle_auto()
        elif self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    def _bucle_auto(self):
        if not self.auto_play:
            return
        self.paso_manual()
        if self.auto_play:  # paso_manual puede haberlo pausado por extinción
            self._after_id = self.root.after(self.velocidad_ms, self._bucle_auto)

    def _cambiar_velocidad(self, valor):
        self.velocidad_ms = max(50, int(1550 - float(valor)))

    def reiniciar(self):
        if self.fabrica is None:
            return
        if self.auto_play:
            self.toggle_auto()
        self.sim = self.fabrica()
        self.txt_logs.delete("1.0", tk.END)
        self.lbl_inspector.config(text="Simulación reiniciada.", foreground="#94a3b8")
        self.actualizar_vista()

    def forzar_evento_gui(self):
        tipo = self.combo_evento.get()
        ev = self.sim.eventos.forzar_evento(
            tipo, self.sim.reloj.ciclo, mapa=self.sim.mapa,
            recursos=self.sim.recursos, aldeas=self.sim.aldeas,
            registro=self.sim.registro, poblacion=self.sim.poblacion
        )
        if ev:
            self.agregar_logs([f"[Manual] Evento forzado: {ev['nombre']} en el ciclo {self.sim.reloj.ciclo}"])
            self.actualizar_vista()

    def _cerrar(self):
        self.auto_play = False
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
        self.root.destroy()

    # ------------------------------------------------------------------
    # Inspector
    # ------------------------------------------------------------------

    def _on_click_mapa(self, event):
        c = event.x // self.tam_celda
        f = event.y // self.tam_celda
        if not (0 <= f < self.n and 0 <= c < self.n):
            return

        casilla = self.sim.mapa[f][c]
        rec = self.sim.recursos
        info = [f"Casilla ({f}, {c}) — terreno: {casilla['terreno']}"]

        if casilla["efectos"]:
            info.append("Efectos: " + ", ".join(f"{k} ({v})" for k, v in casilla["efectos"].items()))

        cons = self.sim.aldeas.obtener_construccion_en_casilla(f, c)
        if cons:
            esp = self.sim.aldeas.consultar_espacio(cons["linaje"])
            info.append(
                f"{cons['tipo'].replace('_', ' ').title()} de {cons['linaje']} "
                f"(nivel {cons['nivel']}, resistencia {_fmt(cons['resistencia'])}, "
                f"alojados {esp['ocupados']}/{_fmt(esp['capacidad'])})"
            )

        fuente = rec.consultar_fuente(f, c)
        if fuente:
            info.append(f"Recurso: {fuente['tipo']} ({fuente['cantidad']}/{fuente['capacidad_maxima']})")

        for cad in rec.cadáveres:
            if cad["posicion"] == (f, c):
                info.append(f"Cadáver de {cad['linaje']} (ID {cad['id_criatura']}), "
                            f"{cad['duracion_restante']} ciclos restantes")
        for a in rec.antídotos:
            if a["posicion"] == (f, c) and a["cantidad"] > 0:
                info.append(f"Antídoto x{a['cantidad']}")

        occ_id = casilla.get("ocupante_id")
        if occ_id is not None:
            cr = self.sim.poblacion.buscar_por_id(occ_id)
            if cr:
                forma = f" ({cr.forma})" if cr.forma else ""
                veneno = " · ENVENENADA" if self.sim.combate.esta_envenenado(cr) else ""
                info.append(
                    f"Criatura #{cr.id} [{cr.linaje.upper()}{forma} — {cr.nombre_evolucion}, etapa {cr.etapa}]\n"
                    f"HP {cr.salud}/{cr.salud_maxima} · EN {cr.energia}/{cr.energia_maxima} · "
                    f"SAC {cr.saciedad} · ATQ {cr.ataque} · DEF {cr.defensa} · XP {cr.xp} · "
                    f"AFD {cr.estado_afd}{veneno}"
                )

        self.lbl_inspector.config(text="\n".join(info), foreground="#e2e8f0")


def iniciar_gui(simulacion, fabrica=None):
    """Punto de entrada que usa main.py: abre la ventana y entra al bucle de Tkinter."""
    root = tk.Tk()
    InterfazNocturnaGUI(root, simulacion, fabrica=fabrica)
    root.mainloop()