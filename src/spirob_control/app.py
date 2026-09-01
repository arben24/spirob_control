"""Das Fenster: Bedienelemente, Ansicht und der Takt, der beides antreibt.

Aufbau der Oberfläche::

    +----------------------------------------------------------------+
    | SpiRob Control                              Simulation/Hardware |
    +---------------------------+------------------------------------+
    | Verbindung                |                                    |
    | Betriebsart (2 Register)  |   Ansicht (3D oder Schema)         |
    |   Handbetrieb: 2 Regler   |                                    |
    |   Policy:      2 Regler   +------------------------------------+
    | Sicherheit / Not-Aus      |   Telemetrie                       |
    +---------------------------+------------------------------------+
    | Statusleiste: Meldung, Regeltakt, Port                          |
    +----------------------------------------------------------------+

Alles läuft in **einem** Thread. Der Regelkreis hängt an Tks ``after()`` und
rechnet 50-mal je Sekunde einen Schritt; die Anzeige wird seltener
aufgefrischt (Bild 25-mal, Zahlen 10-mal je Sekunde). Ein Regelschritt kostet
etwa 0,15 ms und ein gerendertes Bild etwa 4 ms -- das passt bequem in die
20 ms je Takt, und ohne Threads gibt es keine Wettläufe zwischen Anzeige und
Regelung. Genau das ist hier mit "robust" gemeint.
"""

from __future__ import annotations

import math
import time
import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np

from . import hardware, policy as policy_module, settings, theme, workspace
from .controller import (
  MODE_MANUAL,
  MODE_POLICY,
  SOURCE_HARDWARE,
  SOURCE_SIM,
  Controller,
)
from .simulation import FORCE_LIMIT_N
from .view import RobotView

CONTROL_PERIOD_S = 0.02
"""Regeltakt: 50 Hz, wie im Training (Dezimation 5 bei 4 ms Zeitschritt)."""

RENDER_EVERY = 2   # Bild:  25 Hz
REFRESH_EVERY = 5  # Zahlen: 10 Hz


class SpirobApp(tk.Tk):
  def __init__(self) -> None:
    super().__init__()
    self.title("SpiRob Control")
    self.geometry("1320x900")
    self.minsize(1080, 700)
    self.configure(background=theme.BG)

    self.fonts = theme.setup(self)
    self.settings = settings.load()
    self.controller = Controller()

    self._policies = {info.label: info for info in policy_module.available_policies()}
    self._tick_count = 0
    self._next_tick = time.perf_counter()
    self._status_text = "Bereit. Die Simulation läuft; für die echte Hardware oben einen Port wählen."

    self._build()
    self._apply_settings()

    self.protocol("WM_DELETE_WINDOW", self._on_close)
    self.bind("<space>", lambda _e: self._toggle_emergency_stop())
    self.bind("<Escape>", lambda _e: self._emergency_stop())
    self.bind("<F5>", lambda _e: self._reset_simulation())

    self.after(0, self._loop)

  # ==========================================================================
  # Aufbau
  # ==========================================================================

  def _build(self) -> None:
    self.columnconfigure(0, weight=0, minsize=440)
    self.columnconfigure(1, weight=1)
    self.rowconfigure(1, weight=1)

    self._build_header()

    sidebar = self._scrollable_sidebar()
    self._build_connection(sidebar)
    self._build_modes(sidebar)
    self._build_safety(sidebar)

    right = ttk.Frame(self, padding=(7, 10, 14, 10))
    right.grid(row=1, column=1, sticky="nsew")
    right.columnconfigure(0, weight=1)
    right.rowconfigure(0, weight=1)
    self._build_view(right)
    self._build_telemetry(right)

    self._build_statusbar()

  def _scrollable_sidebar(self) -> ttk.Frame:
    """Seitenleiste, die bei kleinen Bildschirmen scrollt.

    Auf einem 1366x768-Notebook passt die Spalte sonst nicht vollständig ins
    Fenster, und ausgerechnet der Not-Aus säße unten außerhalb. Mit dem
    Rollbalken bleibt jedes Bedienelement erreichbar, egal wie klein das
    Fenster gezogen wird.
    """
    holder = ttk.Frame(self, padding=(14, 10, 4, 10))
    holder.grid(row=1, column=0, sticky="nsew")
    holder.columnconfigure(0, weight=1)
    holder.rowconfigure(0, weight=1)

    canvas = tk.Canvas(holder, background=theme.PANEL, highlightthickness=0, bd=0, width=404)
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    canvas.configure(yscrollcommand=scrollbar.set)

    inner = ttk.Frame(canvas)
    inner.columnconfigure(0, weight=1)
    window = canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))

    # Das Mausrad nur greifen, solange der Zeiger über der Seitenleiste steht -
    # sonst würde es auch das Zoomen in der 3D-Ansicht abfangen.
    def scroll(event) -> None:
      delta = 1 if getattr(event, "num", 0) == 5 else -1 if getattr(event, "num", 0) == 4 else (
        -1 if event.delta > 0 else 1)
      canvas.yview_scroll(delta, "units")

    canvas.bind("<Enter>", lambda _e: [self.bind_all(seq, scroll)
                                       for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>")])
    canvas.bind("<Leave>", lambda _e: [self.unbind_all(seq)
                                       for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>")])
    return inner

  def _build_header(self) -> None:
    header = ttk.Frame(self, style="Header.TFrame", padding=(16, 12))
    header.grid(row=0, column=0, columnspan=2, sticky="ew")
    header.columnconfigure(1, weight=1)

    ttk.Label(header, text="SpiRob Control", style="Title.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(
      header,
      text="Seilzug-Tentakel  ·  digitaler Zwilling und Hardware",
      style="Status.TLabel",
    ).grid(row=1, column=0, sticky="w")

    self.lbl_link = tk.Label(
      header, text="● nur Simulation", bg=theme.BG, fg=theme.MUTED, font=self.fonts["heading"]
    )
    self.lbl_link.grid(row=0, column=2, rowspan=2, sticky="e", padx=(0, 16))

    # Der Not-Aus gehört in die Kopfzeile und nicht in die Seitenleiste: er muss
    # sichtbar und klickbar sein, egal wohin die Seitenleiste gerade gescrollt
    # ist und wie klein das Fenster gezogen wurde.
    self.btn_stop = ttk.Button(header, text="NOT-AUS  (Leertaste)", style="Stop.TButton",
                               command=self._toggle_emergency_stop)
    self.btn_stop.grid(row=0, column=3, rowspan=2, sticky="e")

  # -- Verbindung ------------------------------------------------------------

  def _build_connection(self, parent: ttk.Frame) -> None:
    card = theme.card(parent, "Verbindung")
    card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    card.columnconfigure(0, weight=1)

    self.var_port = tk.StringVar()
    self.cmb_port = ttk.Combobox(card, textvariable=self.var_port, state="readonly", width=26)
    self.cmb_port.grid(row=1, column=0, sticky="ew", padx=(0, 6))
    ttk.Button(card, text="Suchen", width=8, command=self._refresh_ports).grid(row=1, column=1)

    self.btn_connect = ttk.Button(card, text="Verbinden", style="Accent.TButton",
                                  command=self._toggle_connection)
    self.btn_connect.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    self.var_send_hw = tk.BooleanVar(value=False)
    ttk.Checkbutton(card, text="Kräfte an die Hardware senden", variable=self.var_send_hw,
                    command=self._on_send_toggle).grid(row=3, column=0, columnspan=2,
                                                       sticky="w", pady=(8, 0))
    self.var_null = tk.BooleanVar(value=False)
    ttk.Checkbutton(card, text="Seillängen nullen (Arm gerade)",
                    variable=self.var_null).grid(row=4, column=0, columnspan=2, sticky="w")

    self.lbl_conn = ttk.Label(card, text="Nicht verbunden.", style="Muted.TLabel", wraplength=340)
    self.lbl_conn.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))

    self._refresh_ports()

  # -- Betriebsarten ---------------------------------------------------------

  def _build_modes(self, parent: ttk.Frame) -> None:
    self.notebook = ttk.Notebook(parent)
    self.notebook.grid(row=1, column=0, sticky="ew", pady=(0, 10))
    self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    self._build_manual_tab()
    self._build_policy_tab()

  def _build_manual_tab(self) -> None:
    tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=(12, 12))
    tab.columnconfigure(0, weight=1)
    self.notebook.add(tab, text="  Handbetrieb  ")

    ttk.Label(
      tab,
      text="Ein Seil allein biegt den Arm zu seiner Seite, beide zusammen krümmen ihn ein.",
      style="Muted.TLabel", justify="left", wraplength=340,
    ).grid(row=0, column=0, sticky="w", pady=(0, 10))

    self.var_f0 = tk.DoubleVar(value=0.0)
    self.var_f1 = tk.DoubleVar(value=0.0)
    self.lbl_f0 = self._force_slider(tab, 1, "Seil 0  (biegt nach +x)", self.var_f0, 0)
    self.lbl_f1 = self._force_slider(tab, 3, "Seil 1  (biegt nach −x)", self.var_f1, 1)

    buttons = ttk.Frame(tab, style="Card.TFrame")
    buttons.grid(row=5, column=0, sticky="ew", pady=(12, 0))
    ttk.Button(buttons, text="Beide auf 0 N", command=self._release_forces).pack(side="left")
    ttk.Button(buttons, text="Arm zurücksetzen", command=self._reset_simulation).pack(
      side="left", padx=(8, 0)
    )

  def _force_slider(self, parent, row: int, label: str, variable: tk.DoubleVar, index: int):
    head = ttk.Frame(parent, style="Card.TFrame")
    head.grid(row=row, column=0, sticky="ew")
    head.columnconfigure(0, weight=1)
    tk.Label(head, text=label, bg=theme.CARD, fg=theme.TENDON_COLORS[index],
             font=self.fonts["heading"]).grid(row=0, column=0, sticky="w")
    value = ttk.Label(head, text="0,0 N", style="Value.TLabel")
    value.grid(row=0, column=1, sticky="e")

    scale = self._slider(parent, variable, 0.0, FORCE_LIMIT_N, 0.5,
                         lambda _v, i=index: self._on_force_slider(i),
                         trough=theme.TENDON_TROUGHS[index])
    scale.grid(row=row + 1, column=0, sticky="ew", pady=(2, 8))
    return value

  def _build_policy_tab(self) -> None:
    tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=(12, 12))
    tab.columnconfigure(0, weight=1)
    self.notebook.add(tab, text="  Policy  ")

    ttk.Label(
      tab,
      text="Die Policy stellt die Seilkräfte; vorgegeben wird nur noch das Ziel.",
      style="Muted.TLabel", justify="left", wraplength=340,
    ).grid(row=0, column=0, sticky="w", pady=(0, 10))

    self.var_policy = tk.StringVar()
    self.cmb_policy = ttk.Combobox(tab, textvariable=self.var_policy, state="readonly",
                                   values=list(self._policies))
    self.cmb_policy.grid(row=1, column=0, sticky="ew")
    self.cmb_policy.bind("<<ComboboxSelected>>", lambda _e: self._load_policy())
    self.lbl_policy = ttk.Label(tab, text="", style="Muted.TLabel", wraplength=340, justify="left")
    self.lbl_policy.grid(row=2, column=0, sticky="w", pady=(6, 10))

    self.var_angle = tk.DoubleVar(value=0.0)
    self.var_radius = tk.DoubleVar(value=workspace.SHELL_RADIUS)
    self.lbl_angle = self._target_slider(
      tab, 3, "Winkel zur Senkrechten", self.var_angle,
      -workspace.ANGLE_LIMIT, workspace.ANGLE_LIMIT,
    )
    self.lbl_radius = self._target_slider(
      tab, 5, "Abstand vom Fußpunkt", self.var_radius,
      0.12, workspace.SHELL_RADIUS + workspace.SHELL_BAND + 0.02,
    )

    self.var_snap = tk.BooleanVar(value=True)
    ttk.Checkbutton(tab, text="Abstand auf den Arbeitsraum legen",
                    variable=self.var_snap, command=self._on_target_change).grid(
      row=7, column=0, sticky="w")

    self.lbl_target = ttk.Label(tab, text="", style="Muted.TLabel", wraplength=340, justify="left")
    self.lbl_target.grid(row=8, column=0, sticky="w", pady=(8, 0))

    ttk.Label(tab, text="Die Policy sieht die Sensordaten aus:", style="Card.TLabel").grid(
      row=9, column=0, sticky="w", pady=(10, 2))
    source = ttk.Frame(tab, style="Card.TFrame")
    source.grid(row=10, column=0, sticky="ew")
    self.var_source = tk.StringVar(value=SOURCE_SIM)
    ttk.Radiobutton(source, text="Simulation", value=SOURCE_SIM, variable=self.var_source,
                    command=self._on_source_change).pack(side="left")
    ttk.Radiobutton(source, text="Hardware", value=SOURCE_HARDWARE, variable=self.var_source,
                    command=self._on_source_change).pack(side="left", padx=(8, 0))

  def _target_slider(self, parent, row: int, label: str, variable: tk.DoubleVar,
                     low: float, high: float):
    head = ttk.Frame(parent, style="Card.TFrame")
    head.grid(row=row, column=0, sticky="ew")
    head.columnconfigure(0, weight=1)
    ttk.Label(head, text=label, style="Card.TLabel").grid(row=0, column=0, sticky="w")
    value = ttk.Label(head, text="", style="Value.TLabel")
    value.grid(row=0, column=1, sticky="e")
    step = 0.005 if label.startswith("Winkel") else 0.001
    scale = self._slider(parent, variable, low, high, step,
                         lambda _v: self._on_target_change())
    scale.grid(row=row + 1, column=0, sticky="ew", pady=(2, 8))
    if label.startswith("Abstand"):
      self.scale_radius = scale
    return value

  def _slider(self, parent, variable, low: float, high: float, step: float,
              command, trough: str = theme.BG) -> tk.Scale:
    """Ein Schieberegler.

    Bewusst der klassische ``tk.Scale`` und nicht ``ttk.Scale``: nur er lässt
    sich in Größe und Farbe vollständig vorgeben und sieht damit unter Windows
    und Linux gleich aus - und ein Regler, den man sicher trifft, ist hier das
    wichtigste Bedienelement.
    """
    return tk.Scale(
      parent, from_=low, to=high, resolution=step, orient="horizontal",
      variable=variable, command=command, showvalue=False,
      background=theme.CARD, troughcolor=trough, activebackground=theme.ACCENT,
      highlightthickness=0, borderwidth=1, relief="flat",
      sliderlength=30, width=16, sliderrelief="raised",
    )

  # -- Sicherheit ------------------------------------------------------------

  def _build_safety(self, parent: ttk.Frame) -> None:
    card = theme.card(parent, "Sicherheit")
    card.grid(row=2, column=0, sticky="ew")
    card.columnconfigure(0, weight=1)

    head = ttk.Frame(card, style="Card.TFrame")
    head.grid(row=1, column=0, sticky="ew")
    head.columnconfigure(0, weight=1)
    ttk.Label(head, text="Kraftgrenze", style="Card.TLabel").grid(row=0, column=0, sticky="w")
    self.lbl_limit = ttk.Label(head, text="150 N", style="Value.TLabel")
    self.lbl_limit.grid(row=0, column=1, sticky="e")

    self.var_limit = tk.DoubleVar(value=FORCE_LIMIT_N)
    ttk.Scale(card, from_=0.0, to=FORCE_LIMIT_N, orient="horizontal", variable=self.var_limit,
              command=lambda _v: self._on_limit_change()).grid(row=2, column=0, sticky="ew",
                                                               pady=(2, 6))
    ttk.Label(card, text="Obergrenze für jede Seilkraft - wirkt in beiden Betriebsarten "
                        "und auch auf das, was an die Hardware geht.",
              style="Muted.TLabel", wraplength=340, justify="left").grid(row=3, column=0, sticky="w")

  # -- Ansicht und Telemetrie ------------------------------------------------

  def _build_view(self, parent: ttk.Frame) -> None:
    frame = ttk.Frame(parent, style="Card.TFrame", padding=(10, 10))
    frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    bar = ttk.Frame(frame, style="Card.TFrame")
    bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    ttk.Label(bar, text="ANSICHT", style="Heading.TLabel").pack(side="left")
    self.var_view = tk.StringVar(value="3d")
    ttk.Radiobutton(bar, text="3D", value="3d", variable=self.var_view,
                    command=self._on_view_change).pack(side="left", padx=(12, 0))
    ttk.Radiobutton(bar, text="Schema", value="2d", variable=self.var_view,
                    command=self._on_view_change).pack(side="left", padx=(6, 0))
    ttk.Button(bar, text="Kamera zurücksetzen", command=self._reset_camera).pack(side="right")

    self.view = RobotView(frame, self.controller.sim, on_message=self._set_status)
    self.view.on_pick = self._on_view_pick
    self.view.grid(row=1, column=0, sticky="nsew")

  def _build_telemetry(self, parent: ttk.Frame) -> None:
    card = theme.card(parent, "Telemetrie")
    card.grid(row=1, column=0, sticky="ew")
    # Beschriftungen bekommen festen Platz, die Werte den Rest - sonst kürzt Tk
    # bei schmalem Fenster genau die Beschriftungen weg.
    card.columnconfigure(0, weight=0, minsize=150)
    card.columnconfigure(1, weight=1, minsize=110)
    card.columnconfigure(2, weight=0, minsize=150)
    card.columnconfigure(3, weight=1, minsize=110)

    self.tele: dict[str, ttk.Label] = {}
    rows = [
      ("Sollkraft Seil 0", "f0", "Sollkraft Seil 1", "f1"),
      ("Spitze x / z", "tcp", "Ziel x / z", "target"),
      ("Abstand zum Ziel", "err", "Policy-Aktion", "action"),
      ("Kraft ist (HW)", "hw_force", "Seillänge (HW)", "hw_rope"),
      ("Regeltakt", "rate", "Rechenzeit je Takt", "tick"),
    ]
    for row, (label_a, key_a, label_b, key_b) in enumerate(rows):
      self._telemetry_cell(card, row + 1, 0, label_a, key_a)
      self._telemetry_cell(card, row + 1, 2, label_b, key_b)

  def _telemetry_cell(self, parent, row: int, column: int, label: str, key: str) -> None:
    ttk.Label(parent, text=label, style="Muted.TLabel").grid(
      row=row, column=column, sticky="w", padx=(0, 8), pady=2)
    value = ttk.Label(parent, text="–", style="Value.TLabel")
    value.grid(row=row, column=column + 1, sticky="w", pady=2)
    self.tele[key] = value

  def _build_statusbar(self) -> None:
    bar = ttk.Frame(self, style="Header.TFrame", padding=(16, 6))
    bar.grid(row=2, column=0, columnspan=2, sticky="ew")
    bar.columnconfigure(0, weight=1)
    self.lbl_status = ttk.Label(bar, text=self._status_text, style="Status.TLabel")
    self.lbl_status.grid(row=0, column=0, sticky="w")
    self.lbl_rate = ttk.Label(bar, text="", style="Status.TLabel")
    self.lbl_rate.grid(row=0, column=1, sticky="e")

  # ==========================================================================
  # Ereignisse
  # ==========================================================================

  def _apply_settings(self) -> None:
    ports = [value for value in self.cmb_port["values"]]
    if self.settings["port"] and self.settings["port"] in ports:
      self.var_port.set(self.settings["port"])
    labels = list(self._policies)
    wanted = [label for label, info in self._policies.items()
              if info.path.name == self.settings["policy"]]
    if labels:
      self.var_policy.set(wanted[0] if wanted else labels[0])
      self._load_policy()
    self.var_limit.set(float(self.settings["force_limit_n"]))
    self._on_limit_change()
    self.var_view.set(self.settings["view_mode"])
    self._on_view_change()
    self._on_target_change()

  def _collect_settings(self) -> dict:
    info = self._policies.get(self.var_policy.get())
    return {
      "port": self.var_port.get(),
      "policy": info.path.name if info else "",
      "view_mode": self.var_view.get(),
      "force_limit_n": float(self.var_limit.get()),
      "send_to_hardware": bool(self.var_send_hw.get()),
    }

  # -- Verbindung ------------------------------------------------------------

  def _refresh_ports(self) -> None:
    ports = hardware.available_ports()
    self.cmb_port["values"] = [device for device, _ in ports]
    if ports and not self.var_port.get():
      self.var_port.set(hardware.guess_port() or ports[0][0])
    if not hardware.SERIAL_AVAILABLE:
      self.lbl_conn.configure(
        text="pyserial ist nicht installiert - Hardwarebetrieb nicht möglich. "
             "Die Simulation läuft trotzdem.")
    elif not ports:
      self.lbl_conn.configure(text="Kein serieller Port gefunden. Kabel prüfen, dann „Suchen“.")

  def _toggle_connection(self) -> None:
    link = self.controller.hardware
    if link.connected:
      self.var_send_hw.set(False)
      self.controller.state.send_to_hardware = False
      link.disconnect()
      self._set_status("Verbindung getrennt, Motoren gestoppt.")
    else:
      port = self.var_port.get()
      if not port:
        messagebox.showinfo("Kein Port", "Bitte zuerst einen seriellen Port auswählen.")
        return
      if link.connect(port, null_tendons=self.var_null.get()):
        self._set_status(f"Verbunden mit {port}. Kraftregelung läuft.")
      else:
        messagebox.showerror("Verbindung fehlgeschlagen", str(link.last_error))
        self._set_status(f"Verbindung fehlgeschlagen: {link.last_error}")
    self._update_connection_widgets()

  def _update_connection_widgets(self) -> None:
    link = self.controller.hardware
    if link.connected:
      self.btn_connect.configure(text="Trennen")
      self.lbl_conn.configure(text=f"Verbunden: {link.port} @ {hardware.BAUD_RATE} Baud, "
                                   f"{link.packets} Pakete empfangen.")
      sending = self.controller.state.send_to_hardware
      self.lbl_link.configure(
        text="● Hardware aktiv" if sending else "● Hardware verbunden",
        fg=theme.OK if sending else theme.WARN,
      )
    else:
      self.btn_connect.configure(text="Verbinden")
      self.lbl_link.configure(text="● nur Simulation", fg=theme.MUTED)
      if link.last_error:
        self.lbl_conn.configure(text=f"Nicht verbunden ({link.last_error}).")
      elif hardware.SERIAL_AVAILABLE:
        self.lbl_conn.configure(text="Nicht verbunden.")

  def _on_send_toggle(self) -> None:
    wanted = self.var_send_hw.get()
    if wanted and not self.controller.hardware.connected:
      self.var_send_hw.set(False)
      messagebox.showinfo("Keine Verbindung",
                          "Erst mit dem Motor-Controller verbinden, dann Kräfte senden.")
      return
    self.controller.state.send_to_hardware = wanted
    self._set_status("Kräfte gehen jetzt an die Hardware." if wanted
                     else "Kräfte gehen nur noch in die Simulation.")
    self._update_connection_widgets()

  # -- Betriebsart -----------------------------------------------------------

  def _on_tab_changed(self, _event=None) -> None:
    index = self.notebook.index(self.notebook.select())
    if index == 1:
      if self.controller.policy is None:
        self._set_status("Keine Policy geladen - im Ordner assets/policies liegt keine Datei.")
        self.notebook.select(0)
        return
      self.controller.set_mode(MODE_POLICY)
      self._set_status("Policy-Betrieb: die Regler geben nur noch das Ziel vor.")
    else:
      self.controller.set_mode(MODE_MANUAL)
      self.var_f0.set(0.0)
      self.var_f1.set(0.0)
      self._set_status("Handbetrieb: die Regler geben die Seilkräfte direkt vor.")
    self._update_force_labels()

  def _on_force_slider(self, _index: int) -> None:
    self.controller.state.manual_forces = [float(self.var_f0.get()), float(self.var_f1.get())]
    self._update_force_labels()

  def _release_forces(self) -> None:
    self.var_f0.set(0.0)
    self.var_f1.set(0.0)
    self._on_force_slider(0)

  def _update_force_labels(self) -> None:
    self.lbl_f0.configure(text=f"{self.var_f0.get():.1f} N".replace(".", ","))
    self.lbl_f1.configure(text=f"{self.var_f1.get():.1f} N".replace(".", ","))

  # -- Policy ----------------------------------------------------------------

  def _load_policy(self) -> None:
    info = self._policies.get(self.var_policy.get())
    if info is None:
      return
    try:
      self.controller.load_policy(info.path)
    except Exception as exc:
      messagebox.showerror("Policy", f"{info.path.name} konnte nicht geladen werden:\n{exc}")
      return
    needs = ", ".join(info.required_signals) or "keine Sensordaten"
    self.lbl_policy.configure(
      text=f"{info.description}\nBraucht: {needs}.")
    self.settings["policy"] = info.path.name

  def _on_target_change(self) -> None:
    angle = float(self.var_angle.get())
    if self.var_snap.get():
      radius = workspace.shell_radius(angle)
      self.var_radius.set(radius)
      self.scale_radius.configure(state="disabled", troughcolor=theme.PANEL)
    else:
      radius = float(self.var_radius.get())
      self.scale_radius.configure(state="normal", troughcolor=theme.BG)

    x, z = workspace.polar_to_xz(angle, radius)
    self.controller.state.target_xz = (x, z)

    self.lbl_angle.configure(text=f"{math.degrees(angle):+.0f}°".replace(".", ","))
    self.lbl_radius.configure(text=f"{radius * 1000:.0f} mm")
    warnings = workspace.warnings_for(x, z)
    self.lbl_target.configure(
      text=f"Ziel: x = {x * 1000:+.0f} mm, z = {z * 1000:+.0f} mm\n"
           + ("Im trainierten Arbeitsraum." if not warnings else warnings[0]),
      foreground=theme.MUTED if not warnings else theme.WARN,
    )

  def _on_source_change(self) -> None:
    self.controller.state.observation_source = self.var_source.get()
    ok, reason = self.controller.policy_ready()
    if not ok and self.var_source.get() == SOURCE_HARDWARE:
      self._set_status(reason)
    else:
      self._set_status("Die Policy sieht jetzt die Daten der "
                       + ("Hardware." if self.var_source.get() == SOURCE_HARDWARE
                          else "Simulation."))

  def _on_view_pick(self, x: float, z: float) -> None:
    """Klick ins Schema: Ziel dorthin legen (nur im Policy-Betrieb sinnvoll)."""
    if self.controller.state.mode != MODE_POLICY:
      return
    angle, radius = workspace.xz_to_polar(x, z)
    angle = max(-workspace.ANGLE_LIMIT, min(workspace.ANGLE_LIMIT, angle))
    self.var_angle.set(angle)
    if not self.var_snap.get():
      self.var_radius.set(min(max(radius, 0.12), workspace.SHELL_RADIUS + workspace.SHELL_BAND))
    self._on_target_change()

  # -- Sicherheit ------------------------------------------------------------

  def _on_limit_change(self) -> None:
    limit = float(self.var_limit.get())
    self.controller.state.force_limit_n = limit
    self.lbl_limit.configure(text=f"{limit:.0f} N")

  def _toggle_emergency_stop(self) -> None:
    if self.controller.state.emergency_stop:
      self.controller.release_emergency_stop()
      self.btn_stop.configure(text="NOT-AUS  (Leertaste)")
    else:
      self._emergency_stop()

  def _emergency_stop(self) -> None:
    self.controller.trigger_emergency_stop()
    self.var_f0.set(0.0)
    self.var_f1.set(0.0)
    self._update_force_labels()
    self.btn_stop.configure(text="Not-Aus aufheben")

  # -- Ansicht ---------------------------------------------------------------

  def _on_view_change(self) -> None:
    self.view.set_mode(self.var_view.get())

  def _reset_camera(self) -> None:
    self.view.reset_camera()

  def _reset_simulation(self) -> None:
    self.controller.reset_simulation()
    self.var_f0.set(0.0)
    self.var_f1.set(0.0)
    self._update_force_labels()
    self._set_status("Simulation zurückgesetzt: Arm gerade, Kräfte auf 0 N.")

  def _set_status(self, text: str) -> None:
    self._status_text = text
    if hasattr(self, "lbl_status"):
      self.lbl_status.configure(text=text)

  # ==========================================================================
  # Takt
  # ==========================================================================

  def _loop(self) -> None:
    telemetry = self.controller.tick()
    if self.controller.message:
      self._set_status(self.controller.message)
      self.controller.message = None
      # Ein erzwungener Moduswechsel (z. B. fehlende Sensordaten) muss sich
      # auch im Register widerspiegeln, sonst zeigt die GUI etwas anderes an,
      # als der Regelkreis tut.
      if self.controller.state.mode == MODE_MANUAL and self.notebook.index("current") == 1:
        self.notebook.select(0)

    self._tick_count += 1
    if self._tick_count % RENDER_EVERY == 0:
      self.view.draw(telemetry)
    if self._tick_count % REFRESH_EVERY == 0:
      self._refresh_labels(telemetry)

    # Auf dem ursprünglichen Zeitraster bleiben: nach einem zu langen Takt
    # werden verpasste Schlitze übersprungen, statt die Phase zu verschieben.
    self._next_tick += CONTROL_PERIOD_S
    now = time.perf_counter()
    if self._next_tick < now:
      self._next_tick = now + CONTROL_PERIOD_S
    self.after(max(1, int((self._next_tick - now) * 1000)), self._loop)

  def _refresh_labels(self, telemetry) -> None:
    self.tele["f0"].configure(text=f"{telemetry.forces_n[0]:6.1f} N")
    self.tele["f1"].configure(text=f"{telemetry.forces_n[1]:6.1f} N")
    self.tele["tcp"].configure(
      text=f"{telemetry.tcp_xz[0]:+.3f} / {telemetry.tcp_xz[1]:+.3f} m")
    self.tele["target"].configure(
      text=f"{telemetry.target_xz[0]:+.3f} / {telemetry.target_xz[1]:+.3f} m")
    self.tele["err"].configure(text=f"{telemetry.error_m * 1000:6.0f} mm")
    self.tele["action"].configure(
      text="–" if telemetry.action is None
      else f"{telemetry.action[0]:+.2f} / {telemetry.action[1]:+.2f}")
    if telemetry.hardware_force_n is not None:
      self.tele["hw_force"].configure(
        text=f"{telemetry.hardware_force_n[0]:5.1f} / {telemetry.hardware_force_n[1]:5.1f} N")
      self.tele["hw_rope"].configure(
        text=f"{telemetry.hardware_rope_mm[0]:6.1f} / {telemetry.hardware_rope_mm[1]:6.1f} mm")
    else:
      self.tele["hw_force"].configure(text="–")
      self.tele["hw_rope"].configure(text="–")
    self.tele["rate"].configure(text=f"{telemetry.rate_hz:5.1f} Hz")
    self.tele["tick"].configure(text=f"{telemetry.tick_ms:5.2f} ms")

    self.lbl_rate.configure(
      text=f"{telemetry.rate_hz:.1f} Hz · Takt {telemetry.ticks}"
           + (f" · {self.controller.hardware.port}" if self.controller.hardware.connected else ""))
    self._update_connection_widgets()

  # ==========================================================================

  def _on_close(self) -> None:
    settings.save(self._collect_settings())
    try:
      self.controller.shutdown()
      self.view.close()
    finally:
      self.destroy()


def main() -> None:
  app = SpirobApp()
  app.mainloop()
