"""Die Ansicht des Roboters: 3D-Bild aus MuJoCo oder 2D-Schema.

Zwei Darstellungen derselben Sache, umschaltbar:

* **3D** -- ein offscreen gerendertes Bild des MuJoCo-Modells, in die
  Zeichenfläche gelegt. Mit der Maus drehbar (ziehen) und zoombar (Rad).
* **Schema** -- die Kette als Polygonzug in der x-z-Ebene, dazu der trainierte
  Arbeitsraum, das Ziel und die Spitze. Reine Tk-Zeichenbefehle.

Das Schema ist nicht nur Beiwerk: es braucht kein OpenGL und ist damit die
Rückfallebene, wenn das 3D-Rendering auf einem Rechner nicht startet (ältere
Fernwartungssitzungen, fehlende Grafiktreiber). Schlägt der Renderer fehl,
schaltet die Ansicht selbsttätig um und sagt, warum.
"""

from __future__ import annotations

import base64
import math
import time
import tkinter as tk
from tkinter import ttk

import numpy as np

from . import theme, workspace

try:
  from PIL import Image, ImageTk  # deutlich schneller als der PPM-Umweg

  PIL_AVAILABLE = True
except Exception:  # pragma: no cover - Pillow ist optional
  PIL_AVAILABLE = False

MAX_RENDER_WIDTH = 3840
MAX_RENDER_HEIGHT = 2400
"""Obergrenze der Renderauflösung.

Groß genug, dass auch ein 4K-Vollbild in Originalauflösung gerendert wird - das
ist der schnellste Fall, weil dann gar nicht skaliert werden muss. Erst
darüber (etwa auf einem virtuellen Bildschirm über mehrere Monitore) rendert
die Ansicht seitenverhältnisgetreu kleiner und skaliert das Bild auf die
Zeichenfläche hoch, statt es klein in der Mitte stehen zu lassen. Dass dabei
der Regeltakt nicht leidet, sorgt die Bildrate in ``app.py``: sie richtet sich
danach, wie lange ein Bild tatsächlich dauert.
"""

FALLBACK_RENDER_SIZE = (1280, 800)
"""Zweiter Versuch, falls die Grafikkarte den gewünschten Puffer verweigert."""

RESIZE_DEBOUNCE_S = 0.2
"""Mindestabstand zwischen zwei Neuanlagen des Renderers.

Beim Ziehen am Fensterrand ändert sich die Größe viele Male je Sekunde. Für
jede davon einen neuen OpenGL-Kontext anzulegen wäre teuer; in der Zwischenzeit
wird das zuletzt gerenderte Format hochskaliert angezeigt.
"""


class RobotView(ttk.Frame):
  """Zeichenfläche mit umschaltbarer 3D-/Schema-Darstellung."""

  def __init__(self, master: tk.Misc, simulation, on_message=None) -> None:
    super().__init__(master, style="Card.TFrame")
    self.sim = simulation
    self.on_message = on_message or (lambda text: None)
    self.on_pick = None
    """Rückruf ``f(x, z)`` für einen Klick ins Schema, in Weltkoordinaten [m]."""
    self.mode = "3d"

    self.canvas = tk.Canvas(self, background=theme.BG, highlightthickness=0, bd=0)
    self.canvas.pack(fill="both", expand=True)

    self._renderer = None
    self._render_size = (0, 0)
    self._photo = None
    self._camera = None
    self._drag_origin: tuple[int, int] | None = None
    self._render_failed = False
    self._last_resize = 0.0
    self._transform: tuple[float, float, float] | None = None  # (x0, y0, Maßstab)

    self.canvas.bind("<ButtonPress-1>", self._on_press)
    self.canvas.bind("<B1-Motion>", self._on_drag)
    self.canvas.bind("<ButtonRelease-1>", lambda _e: setattr(self, "_drag_origin", None))
    self.canvas.bind("<MouseWheel>", self._on_wheel)  # Windows / macOS
    self.canvas.bind("<Button-4>", lambda e: self._zoom(0.9))  # X11
    self.canvas.bind("<Button-5>", lambda e: self._zoom(1.1))

  # -- Umschalten ------------------------------------------------------------

  def set_mode(self, mode: str) -> None:
    self.mode = mode
    self.canvas.delete("all")
    if mode == "3d":
      self._render_failed = False

  # -- Kamera ----------------------------------------------------------------

  def _ensure_camera(self):
    import mujoco

    if self._camera is None:
      camera = mujoco.MjvCamera()
      mujoco.mjv_defaultFreeCamera(self.sim.model, camera)
      # Blick von der Seite auf die Biegeebene: der SpiRob bewegt sich in x-z.
      camera.azimuth = 90.0
      camera.elevation = -6.0
      camera.distance = 0.82
      camera.lookat[:] = [0.0, 0.0, 0.22]
      self._camera = camera
    return self._camera

  def _on_press(self, event) -> None:
    self._drag_origin = (event.x, event.y)
    # Im Schema dreht sich nichts - dort setzt ein Klick stattdessen das Ziel.
    if self.mode != "3d" and self.on_pick is not None and self._transform is not None:
      origin_x, origin_y, scale = self._transform
      self.on_pick((event.x - origin_x) / scale, (origin_y - event.y) / scale)

  def _on_drag(self, event) -> None:
    if self.mode != "3d" or self._drag_origin is None:
      return
    camera = self._ensure_camera()
    dx = event.x - self._drag_origin[0]
    dy = event.y - self._drag_origin[1]
    self._drag_origin = (event.x, event.y)
    camera.azimuth = (camera.azimuth - dx * 0.4) % 360.0
    camera.elevation = float(np.clip(camera.elevation - dy * 0.4, -89.0, 89.0))

  def _on_wheel(self, event) -> None:
    self._zoom(0.9 if event.delta > 0 else 1.1)

  def _zoom(self, factor: float) -> None:
    if self.mode != "3d":
      return
    camera = self._ensure_camera()
    camera.distance = float(np.clip(camera.distance * factor, 0.25, 4.0))

  def reset_camera(self) -> None:
    self._camera = None

  # -- Zeichnen --------------------------------------------------------------

  def draw(self, telemetry) -> None:
    width = self.canvas.winfo_width()
    height = self.canvas.winfo_height()
    if width < 40 or height < 40:  # Fenster noch nicht ausgelegt
      return
    if self.mode == "3d" and not self._render_failed:
      if self._draw_3d(telemetry, width, height):
        return
    self._draw_schematic(telemetry, width, height)

  # -- 3D --------------------------------------------------------------------

  @staticmethod
  def _render_size_for(width: int, height: int) -> tuple[int, int]:
    """Renderformat für eine Zeichenfläche dieser Größe.

    Normalfall: genau die Größe der Zeichenfläche, also ein Bild ohne
    Skalierung und im richtigen Seitenverhältnis. Erst jenseits der Obergrenze
    wird proportional verkleinert - das Seitenverhältnis bleibt dabei erhalten,
    sonst wäre das hochskalierte Bild verzerrt.
    """
    scale = min(1.0, MAX_RENDER_WIDTH / width, MAX_RENDER_HEIGHT / height)
    return (max(64, int(width * scale)), max(64, int(height * scale)))

  def _build_renderer(self, size: tuple[int, int]):
    """Renderer für dieses Format anlegen; bei Ablehnung kleiner erneut versuchen."""
    import mujoco

    if self._renderer is not None:
      self._renderer.close()
      self._renderer = None
    for candidate in (size, FALLBACK_RENDER_SIZE):
      # Der Offscreen-Puffer ist im Modell auf 640x480 vorbelegt und muss vor
      # dem Anlegen des Renderers groß genug sein.
      self.sim.model.vis.global_.offwidth = max(self.sim.model.vis.global_.offwidth, candidate[0])
      self.sim.model.vis.global_.offheight = max(self.sim.model.vis.global_.offheight, candidate[1])
      try:
        self._renderer = mujoco.Renderer(self.sim.model, candidate[1], candidate[0])
        self._render_size = candidate
        self._last_resize = time.monotonic()
        return
      except Exception:
        if candidate is FALLBACK_RENDER_SIZE:
          raise  # auch das kleinere Format geht nicht -> Schema-Ansicht

  def _draw_3d(self, telemetry, width: int, height: int) -> bool:
    try:
      wanted = self._render_size_for(width, height)
      if self._renderer is None:
        self._build_renderer(wanted)
      elif wanted != self._render_size and time.monotonic() - self._last_resize >= RESIZE_DEBOUNCE_S:
        # Beim Ziehen am Fensterrand nicht für jede Zwischengröße einen neuen
        # OpenGL-Kontext anlegen; bis dahin wird hochskaliert angezeigt.
        self._build_renderer(wanted)

      camera = self._ensure_camera()
      self._renderer.update_scene(self.sim.data, camera)
      self._add_target_marker(telemetry)
      self._add_measured_chain(telemetry)
      frame = self._renderer.render()
      # Auf die Zeichenfläche bringen: normalerweise passt das Bild exakt, nur
      # während einer Größenänderung oder oberhalb der Obergrenze wird skaliert.
      self._photo = _to_photo_image(frame, (width, height))
      self.canvas.delete("all")
      self.canvas.create_image(width // 2, height // 2, image=self._photo, anchor="center")
      self._draw_hud(telemetry, width, height)
      return True
    except Exception as exc:
      self._render_failed = True
      self._renderer = None
      self.on_message(
        f"3D-Ansicht nicht verfügbar ({exc}). Es wird das Schema gezeichnet."
      )
      return False

  def _add_target_marker(self, telemetry) -> None:
    """Das kommandierte Ziel als Kugel in die gerenderte Szene legen."""
    import mujoco

    scene = self._renderer.scene
    if scene.ngeom >= scene.maxgeom:
      return
    geom = scene.geoms[scene.ngeom]
    mujoco.mjv_initGeom(
      geom,
      type=mujoco.mjtGeom.mjGEOM_SPHERE,
      size=np.array([0.012, 0.0, 0.0]),
      pos=np.array([telemetry.target_xz[0], 0.0, telemetry.target_xz[1]]),
      mat=np.eye(3).flatten(),
      rgba=np.array([1.0, 0.72, 0.33, 0.85], dtype=np.float32),
    )
    scene.ngeom += 1

  def _add_measured_chain(self, telemetry) -> None:
    """Die gemessene Armform als Kapselzug über das Simulationsmodell legen.

    Hängt die Sensorplatine, zeigt die 3D-Ansicht nur das Modell. Mit ihr sieht
    man beides übereinander: das Modell in seinen eigenen Farben und die
    Messung als durchgehenden Strang - der Unterschied zwischen beiden ist
    genau der Sim-to-Real-Abstand.
    """
    import mujoco

    chain = telemetry.measured_chain_xz
    if chain is None:
      return
    scene = self._renderer.scene
    color = np.array([0.25, 0.85, 0.6, 0.95], dtype=np.float32)
    for start, end in zip(chain[:-1], chain[1:]):
      if scene.ngeom >= scene.maxgeom:
        return
      geom = scene.geoms[scene.ngeom]
      mujoco.mjv_initGeom(
        geom,
        type=mujoco.mjtGeom.mjGEOM_CAPSULE,
        size=np.zeros(3),
        pos=np.zeros(3),
        mat=np.eye(3).flatten(),
        rgba=color,
      )
      # mjv_connector spannt die Kapsel zwischen zwei Punkten auf und übernimmt
      # dabei Länge und Ausrichtung - von Hand wäre das eine Rotationsmatrix.
      mujoco.mjv_connector(
        geom,
        mujoco.mjtGeom.mjGEOM_CAPSULE,
        0.006,
        np.array([start[0], 0.0, start[1]]),
        np.array([end[0], 0.0, end[1]]),
      )
      scene.ngeom += 1

  def _draw_hud(self, telemetry, width: int, height: int) -> None:
    """Knappe Einblendung im 3D-Bild: was gerade gilt."""
    lines = [
      f"Ziel      x {telemetry.target_xz[0]:+.3f} m   z {telemetry.target_xz[1]:+.3f} m",
      f"Sim       x {telemetry.tcp_xz[0]:+.3f} m   z {telemetry.tcp_xz[1]:+.3f} m"
      f"   Abstand {telemetry.error_m * 1000:4.0f} mm",
    ]
    if telemetry.measured_tcp_xz is not None:
      lines.append(
        f"Gemessen  x {telemetry.measured_tcp_xz[0]:+.3f} m   "
        f"z {telemetry.measured_tcp_xz[1]:+.3f} m"
        f"   Abstand {telemetry.measured_error_m * 1000:4.0f} mm"
      )
    self.canvas.create_text(
      14, height - 14, anchor="sw", justify="left", text="\n".join(lines),
      fill=theme.TEXT, font=theme.canvas_font(9),
    )
    self.canvas.create_text(
      width - 14, 14, anchor="ne", text="Ziehen: drehen   Rad: zoomen",
      fill=theme.MUTED, font=theme.canvas_font(8),
    )

  # -- Schema ----------------------------------------------------------------

  def _draw_schematic(self, telemetry, width: int, height: int) -> None:
    canvas = self.canvas
    canvas.delete("all")

    # Weltausschnitt: die volle Armlänge plus Rand, mittig und maßstabsgetreu.
    span = 0.52
    scale = min(width / (2 * span), height / (span + 0.12))
    origin_x = width / 2
    origin_y = height - 0.09 * height
    self._transform = (origin_x, origin_y, scale)

    def to_px(point) -> tuple[float, float]:
      return origin_x + point[0] * scale, origin_y - point[1] * scale

    # Arbeitsraum: das Band, in dem im Training die Ziele lagen.
    band = [coord for point in workspace.shell_band(61) for coord in to_px(point)]
    canvas.create_polygon(band, fill="#1b2530", outline="")
    shell = [coord for point in workspace.shell_outline(61) for coord in to_px(point)]
    canvas.create_line(shell, fill="#33465c", width=1, dash=(4, 4))

    # Boden und Fußpunkt.
    canvas.create_line(0, origin_y, width, origin_y, fill=theme.BORDER, width=1)
    canvas.create_rectangle(origin_x - 26, origin_y, origin_x + 26, origin_y + 10,
                            fill=theme.BORDER, outline="")

    # Maßstab: 100 mm.
    canvas.create_line(16, height - 18, 16 + 0.1 * scale, height - 18,
                       fill=theme.MUTED, width=2)
    canvas.create_text(16, height - 26, anchor="sw", text="100 mm",
                       fill=theme.MUTED, font=theme.canvas_font(8))

    # Die Kette. Mit Sensorplatine ist die gemessene Form die Hauptaussage und
    # die Simulation nur noch der blasse Vergleich dahinter - der Abstand
    # zwischen beiden Linien ist der Sim-to-Real-Unterschied, und den soll man
    # sehen können.
    measured = telemetry.measured_chain_xz
    if measured is not None:
      self._draw_chain(to_px, telemetry.chain_xz, ghost=True)
      self._draw_chain(to_px, measured, ghost=False)
      tip = telemetry.measured_tcp_xz
    else:
      self._draw_chain(to_px, telemetry.chain_xz, ghost=False)
      tip = telemetry.tcp_xz

    # Ziel (Kreuz) und Spitze (Punkt), dazu der Abstand zwischen beiden.
    tx, ty = to_px(telemetry.target_xz)
    canvas.create_oval(tx - 9, ty - 9, tx + 9, ty + 9, outline=theme.WARN, width=2)
    canvas.create_line(tx - 13, ty, tx + 13, ty, fill=theme.WARN, width=1)
    canvas.create_line(tx, ty - 13, tx, ty + 13, fill=theme.WARN, width=1)

    if tip is not None:
      cx, cy = to_px(tip)
      canvas.create_line(tx, ty, cx, cy, fill=theme.MUTED, dash=(3, 3))
      canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=theme.ACCENT, outline="")

    lines = [
      f"Ziel      x {telemetry.target_xz[0]:+.3f}  z {telemetry.target_xz[1]:+.3f} m",
      f"Simulation x {telemetry.tcp_xz[0]:+.3f}  z {telemetry.tcp_xz[1]:+.3f} m"
      f"   Abstand {telemetry.error_m * 1000:4.0f} mm",
    ]
    if telemetry.measured_tcp_xz is not None:
      lines.append(
        f"Gemessen  x {telemetry.measured_tcp_xz[0]:+.3f}  "
        f"z {telemetry.measured_tcp_xz[1]:+.3f} m"
        f"   Abstand {telemetry.measured_error_m * 1000:4.0f} mm"
      )
    canvas.create_text(
      14, 14, anchor="nw", justify="left", fill=theme.MUTED, font=theme.canvas_font(9),
      text="\n".join(lines),
    )

    if measured is not None:
      self._draw_legend(height)

    if self.on_pick is not None:
      canvas.create_text(width - 14, height - 14, anchor="se", text="Klick setzt das Ziel",
                         fill=theme.MUTED, font=theme.canvas_font(8))

    # Kraftbalken je Seil, damit man die Stellgröße auch im Schema sieht.
    self._draw_force_bars(telemetry, width, height)

  def _draw_chain(self, to_px, chain, ghost: bool) -> None:
    """Einen Kettenzug zeichnen: kräftig als Messung, blass als Vergleich."""
    if chain is None or len(chain) < 2:
      return
    points = [coord for point in chain for coord in to_px(point)]
    if ghost:
      self.canvas.create_line(points, fill="#61748a", width=2, dash=(5, 4),
                              capstyle="round", joinstyle="round")
      return
    self.canvas.create_line(points, fill="#2f7d5c", width=9, capstyle="round",
                            joinstyle="round")
    self.canvas.create_line(points, fill=theme.OK, width=4, capstyle="round",
                            joinstyle="round")
    for point in chain[1:-1]:
      px, py = to_px(point)
      self.canvas.create_oval(px - 2.5, py - 2.5, px + 2.5, py + 2.5,
                              fill=theme.BG, outline=theme.OK)

  def _draw_legend(self, height: int) -> None:
    """Sagt, welche Linie was ist - sobald zwei Armformen im Bild sind.

    Unten links, oberhalb des Maßstabs: dort ist die Zeichenfläche frei, und
    die Kraftbalken oben rechts bleiben unangetastet.
    """
    canvas = self.canvas
    for offset, color, dash, label, fill in (
      (70, theme.OK, None, "gemessen", theme.TEXT),
      (52, "#61748a", (5, 4), "Simulation", theme.MUTED),
    ):
      y = height - offset
      canvas.create_line(14, y, 36, y, fill=color, width=4 if dash is None else 2,
                         dash=dash, capstyle="round")
      canvas.create_text(42, y, anchor="w", text=label, fill=fill,
                         font=theme.canvas_font(8))

  def _draw_force_bars(self, telemetry, width: int, height: int) -> None:
    canvas = self.canvas
    bar_height = 90
    top = 20
    for i, force in enumerate(telemetry.forces_n):
      x = width - 46 + i * 22
      canvas.create_rectangle(x, top, x + 12, top + bar_height,
                              outline=theme.BORDER, fill=theme.BG)
      filled = bar_height * min(force / 150.0, 1.0)
      canvas.create_rectangle(x, top + bar_height - filled, x + 12, top + bar_height,
                              outline="", fill=theme.TENDON_COLORS[i])
      canvas.create_text(x + 6, top + bar_height + 12, text=f"{force:.0f}",
                         fill=theme.MUTED, font=theme.canvas_font(8))
    canvas.create_text(width - 14, top - 6, text="Seilkraft [N]", anchor="se",
                       fill=theme.MUTED, font=theme.canvas_font(8))

  # -- Aufräumen -------------------------------------------------------------

  def close(self) -> None:
    if self._renderer is not None:
      try:
        self._renderer.close()
      except Exception:
        pass
      self._renderer = None


def _to_photo_image(frame: np.ndarray, display_size: tuple[int, int] | None = None):
  """RGB-Array in ein Tk-Bild wandeln, bei Bedarf auf ``display_size`` gebracht.

  Mit Pillow ist das ein direkter Weg, und dort kann das Bild auch skaliert
  werden. Ohne Pillow wird es als PPM aufbereitet und base64-kodiert an Tk
  übergeben -- langsamer und ohne Skalierung, aber es kommt ohne zusätzliche
  Abhängigkeit aus, und die GUI läuft damit auch auf einem frisch aufgesetzten
  Rechner sofort.
  """
  height, width = frame.shape[:2]
  if PIL_AVAILABLE:
    image = Image.fromarray(frame)
    if display_size is not None and display_size != (width, height):
      image = image.resize(display_size, Image.BILINEAR)
    return ImageTk.PhotoImage(image)
  ppm = b"P6 %d %d 255 " % (width, height) + frame.tobytes()
  return tk.PhotoImage(data=base64.b64encode(ppm))
