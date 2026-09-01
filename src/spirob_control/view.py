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
import tkinter as tk
from tkinter import ttk

import numpy as np

from . import theme, workspace

try:
  from PIL import Image, ImageTk  # deutlich schneller als der PPM-Umweg

  PIL_AVAILABLE = True
except Exception:  # pragma: no cover - Pillow ist optional
  PIL_AVAILABLE = False

MAX_RENDER_WIDTH = 1280
MAX_RENDER_HEIGHT = 960


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

  def _draw_3d(self, telemetry, width: int, height: int) -> bool:
    try:
      import mujoco

      size = (min(width, MAX_RENDER_WIDTH), min(height, MAX_RENDER_HEIGHT))
      if self._renderer is None or self._render_size != size:
        if self._renderer is not None:
          self._renderer.close()
        # Der Offscreen-Puffer ist im Modell auf 640x480 vorbelegt; für ein
        # scharfes Bild im großen Fenster wird er vor dem Anlegen erhöht.
        self.sim.model.vis.global_.offwidth = max(self.sim.model.vis.global_.offwidth, size[0])
        self.sim.model.vis.global_.offheight = max(self.sim.model.vis.global_.offheight, size[1])
        self._renderer = mujoco.Renderer(self.sim.model, size[1], size[0])
        self._render_size = size

      camera = self._ensure_camera()
      self._renderer.update_scene(self.sim.data, camera)
      self._add_target_marker(telemetry)
      frame = self._renderer.render()
      self._photo = _to_photo_image(frame)
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

  def _draw_hud(self, telemetry, width: int, height: int) -> None:
    """Knappe Einblendung im 3D-Bild: was gerade gilt."""
    lines = [
      f"Ziel   x {telemetry.target_xz[0]:+.3f} m   z {telemetry.target_xz[1]:+.3f} m",
      f"Spitze x {telemetry.tcp_xz[0]:+.3f} m   z {telemetry.tcp_xz[1]:+.3f} m",
      f"Abstand {telemetry.error_m * 1000:.0f} mm",
    ]
    self.canvas.create_text(
      14, height - 14, anchor="sw", justify="left", text="\n".join(lines),
      fill=theme.TEXT, font=("TkFixedFont", 9),
    )
    self.canvas.create_text(
      width - 14, 14, anchor="ne", text="Ziehen: drehen   Rad: zoomen",
      fill=theme.MUTED, font=("TkFixedFont", 8),
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
                       fill=theme.MUTED, font=("TkFixedFont", 8))

    # Die Kette selbst.
    chain = telemetry.chain_xz
    if chain is not None and len(chain) > 1:
      points = [coord for point in chain for coord in to_px(point)]
      canvas.create_line(points, fill="#2f7d5c", width=9, capstyle="round", joinstyle="round")
      canvas.create_line(points, fill=theme.OK, width=4, capstyle="round", joinstyle="round")
      for point in chain[1:-1]:
        px, py = to_px(point)
        canvas.create_oval(px - 2.5, py - 2.5, px + 2.5, py + 2.5,
                           fill=theme.BG, outline=theme.OK)

    # Ziel (Kreuz) und Spitze (Punkt), dazu der Abstand zwischen beiden.
    tx, ty = to_px(telemetry.target_xz)
    canvas.create_oval(tx - 9, ty - 9, tx + 9, ty + 9, outline=theme.WARN, width=2)
    canvas.create_line(tx - 13, ty, tx + 13, ty, fill=theme.WARN, width=1)
    canvas.create_line(tx, ty - 13, tx, ty + 13, fill=theme.WARN, width=1)

    cx, cy = to_px(telemetry.tcp_xz)
    canvas.create_line(tx, ty, cx, cy, fill=theme.MUTED, dash=(3, 3))
    canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=theme.ACCENT, outline="")

    canvas.create_text(
      14, 14, anchor="nw", justify="left", fill=theme.MUTED, font=("TkFixedFont", 9),
      text=(
        f"Ziel   x {telemetry.target_xz[0]:+.3f}  z {telemetry.target_xz[1]:+.3f} m\n"
        f"Spitze x {telemetry.tcp_xz[0]:+.3f}  z {telemetry.tcp_xz[1]:+.3f} m\n"
        f"Abstand {telemetry.error_m * 1000:.0f} mm"
      ),
    )

    if self.on_pick is not None:
      canvas.create_text(width - 14, height - 14, anchor="se", text="Klick setzt das Ziel",
                         fill=theme.MUTED, font=("TkFixedFont", 8))

    # Kraftbalken je Seil, damit man die Stellgröße auch im Schema sieht.
    self._draw_force_bars(telemetry, width, height)

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
                         fill=theme.MUTED, font=("TkFixedFont", 8))
    canvas.create_text(width - 14, top - 6, text="Seilkraft [N]", anchor="se",
                       fill=theme.MUTED, font=("TkFixedFont", 8))

  # -- Aufräumen -------------------------------------------------------------

  def close(self) -> None:
    if self._renderer is not None:
      try:
        self._renderer.close()
      except Exception:
        pass
      self._renderer = None


def _to_photo_image(frame: np.ndarray):
  """RGB-Array in ein Tk-Bild wandeln.

  Mit Pillow ist das ein direkter Weg. Ohne Pillow wird das Bild als PPM
  aufbereitet und base64-kodiert an Tk übergeben -- langsamer, aber es kommt
  ohne zusätzliche Abhängigkeit aus, und die GUI läuft damit auch auf einem
  frisch aufgesetzten Rechner sofort.
  """
  if PIL_AVAILABLE:
    return ImageTk.PhotoImage(Image.fromarray(frame))
  height, width = frame.shape[:2]
  ppm = b"P6 %d %d 255 " % (width, height) + frame.tobytes()
  return tk.PhotoImage(data=base64.b64encode(ppm))
