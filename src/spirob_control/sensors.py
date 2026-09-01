"""Sensorplatine: 14 Beschleunigungssensoren -> 13 Gelenkwinkel.

Die zweite USB-Quelle neben dem Motor-Controller. Auf jedem Segment des Arms
sitzt ein Beschleunigungssensor; im Ruhezustand misst er die Richtung der
Schwerkraft und damit die Neigung seines Segments. Die Differenz zweier
benachbarter Neigungen ist der Gelenkwinkel dazwischen.

Damit liefert die Platine drei Dinge, die es sonst nirgends gibt:

* ``joint_pos`` / ``joint_vel`` - die 13 Gelenkwinkel und ihre
  Geschwindigkeiten, also die Beobachtung für Policies des Sensor-Levels
  ``joints``,
* ``segment_pitch`` - die Neigungen als Cosinus/Sinus, die Beobachtung für
  ``imu``,
* über die Vorwärtskinematik (:mod:`kinematics`) die **gemessene** Form des
  Arms - das Einzige, was die Anzeige vom echten Roboter zeigen kann.

Rechenweg
---------
Alle Gelenke drehen um dieselbe Achse. Dadurch bleibt die Komponente des
Schwerkraftvektors entlang dieser Achse unverändert, und die ganze Drehung
findet in der Ebene senkrecht dazu statt. Der Richtungswinkel des gemessenen
Vektors in dieser Ebene ist die Neigung des Segments, die Differenz benachbarter
Segmente der Gelenkwinkel:

    phi_i = atan2(a_z, a_y)        (Drehachse x)
    q_i   = phi_i - phi_(i+1)

Das ist keine Näherung: Weil das Problem in 13 unabhängige Ein-Parameter-
Probleme zerfällt, trifft diese geschlossene Ablesung das Least-Squares-Minimum
exakt - nachgewiesen im Ursprungsprojekt gegen den iterativen Löser
(6,7e-06 Grad Abweichung, dabei rund 400-mal schneller). Deshalb kommt dieses
Modul mit NumPy aus und braucht kein SciPy.

Protokoll
---------
Binärstrom der Platinen-Firmware, 1 MBaud::

    Kopf (12 B): 0xAA 0x55 | frame_id(u32) | t_esp_us(u32) | mode(u8) | n(u8)
    je Sensor:   sensor_id(u8) + 3 float32 (ACC) bzw. 6 float32 (ACC+MAG)

Nach dem Öffnen schickt die GUI ``a`` und stellt die Platine damit auf reine
Beschleunigungsdaten - die höchste Bildrate, und mehr wird hier nicht gebraucht.

Zwei Dinge kann die Software nicht selbst prüfen, weil sie vom Einbau abhängen:
die **Reihenfolge** der Sensoren (Voreinstellung: Platine und Simulation zählen
beide von der Basis zur Spitze) und das **Vorzeichen** der Winkel. Für Letzteres
gibt es in der Oberfläche einen Schalter; steht der Arm im Schema
spiegelverkehrt, ist er gemeint.
"""

from __future__ import annotations

import struct
import time

import numpy as np

from . import kinematics
from .hardware import SERIAL_AVAILABLE, _FilteredDiff, serial

BAUD_RATE = 1_000_000
"""Muss zu ``SERIAL_BAUD`` in der Firmware der Sensorplatine passen."""

FRAME_HEADER = b"\xaa\x55"
FRAME_META = struct.Struct("<IIBB")  # frame_id, t_esp_us, mode, num_sensors
MODE_BOTH, MODE_HALL, MODE_ACC = 0, 1, 2
MODE_COMMAND_ACC = b"a"
MAX_SENSORS_PER_FRAME = 16

SENSOR_IDS = (0, 1, 2, 3, 4, 5, 6, 7, 32, 33, 34, 35, 36, 37)
"""Sensorkennungen in physischer Reihenfolge, Basis -> Spitze."""

NUM_SEGMENTS = len(SENSOR_IDS)
NUM_JOINTS = NUM_SEGMENTS - 1

JOINT_LIMIT_RAD = np.radians(30.0)
"""Mechanische Grenze je Gelenk; darüber hinaus gemessene Werte sind Rauschen."""

ACC_EMA_ALPHA = 0.25
"""Glättung der Rohbeschleunigungen, wie im Referenzskript der Platine."""

FRAME_TIMEOUT_S = 1.0
"""Ohne neues Frame in dieser Zeit gelten die Sensordaten als veraltet."""


class BinaryFrameParser:
  """Zerlegt den Binärstrom der Platine in Frames.

  Robust gegen alles, was auf einer seriellen Leitung passiert: verlorene
  Bytes, Klartextzeilen der Firmware zwischendrin, Kopfbytes, die zufällig
  mitten in Fließkommazahlen auftauchen. Gegen Letzteres hilft die Prüfung, ob
  direkt hinter dem Frame der nächste Kopf steht - sonst war es ein Fehltreffer.
  """

  def __init__(self, buffer_size: int = 16384) -> None:
    self.buffer = bytearray()
    self.buffer_size = buffer_size

  def add_data(self, data: bytes) -> None:
    self.buffer.extend(data)
    if len(self.buffer) > self.buffer_size:
      del self.buffer[: len(self.buffer) - self.buffer_size]

  def extract_frames(self) -> list[dict]:
    """Alle vollständigen Frames aus dem Puffer holen."""
    frames: list[dict] = []
    while True:
      start = self.buffer.find(FRAME_HEADER)
      if start == -1:
        # Kein Kopf in Sicht: nur vollständige Textzeilen verwerfen, damit ein
        # angefangener Kopf am Pufferende erhalten bleibt.
        last_newline = self.buffer.rfind(b"\n")
        if last_newline != -1:
          del self.buffer[: last_newline + 1]
        break
      if start > 0:
        del self.buffer[:start]
      if len(self.buffer) < 2 + FRAME_META.size:
        break

      _frame_id, _t_us, mode, num_sensors = FRAME_META.unpack_from(self.buffer, 2)
      if num_sensors == 0 or num_sensors > MAX_SENSORS_PER_FRAME or mode > MODE_ACC:
        del self.buffer[:2]  # Fehltreffer
        continue

      num_floats = 6 if mode == MODE_BOTH else 3
      packet_size = 1 + num_floats * 4
      frame_size = 2 + FRAME_META.size + num_sensors * packet_size
      if len(self.buffer) < frame_size + 2:
        break  # Frame oder der folgende Kopf noch nicht vollständig da
      if self.buffer[frame_size : frame_size + 2] != FRAME_HEADER:
        del self.buffer[:2]  # kein echter Frame
        continue

      raw = bytes(self.buffer[:frame_size])
      del self.buffer[:frame_size]

      sensors: dict[int, tuple[float, float, float]] = {}
      offset = 2 + FRAME_META.size
      for _ in range(num_sensors):
        sensor_id = raw[offset]
        values = struct.unpack_from(f"<{num_floats}f", raw, offset + 1)
        # Nur die Beschleunigung wird gebraucht; im HALL-Modus gibt es keine.
        sensors[sensor_id] = (0.0, 0.0, 0.0) if mode == MODE_HALL else values[:3]
        offset += packet_size
      frames.append({"mode": mode, "sensors": sensors})
    return frames


def solve_joint_angles(acc_by_segment: np.ndarray) -> np.ndarray:
  """Gelenkwinkel [rad] aus den normierten Beschleunigungen, Basis -> Spitze.

  ``acc_by_segment`` hat die Form ``(NUM_SEGMENTS, 3)`` und ist bereits sortiert
  und auf Länge 1 normiert.
  """
  acc = np.asarray(acc_by_segment, dtype=float)
  pitch = np.arctan2(acc[:, 2], acc[:, 1])  # Drehachse x -> Ebene (y, z)
  angles = pitch[:-1] - pitch[1:]
  # Auf (-pi, pi] normieren, sonst springt ein Winkel nahe 180 Grad um 360.
  angles = (angles + np.pi) % (2.0 * np.pi) - np.pi
  return np.clip(angles, -JOINT_LIMIT_RAD, JOINT_LIMIT_RAD)


def order_and_normalize(acc_by_id: dict[int, np.ndarray]) -> np.ndarray | None:
  """Rohwerte in physische Reihenfolge bringen und normieren.

  Gibt ``None`` zurück, solange nicht jeder Sensor mindestens einmal gesehen
  wurde - lieber keine Winkel als Winkel mit Löchern darin.
  """
  if any(sensor_id not in acc_by_id for sensor_id in SENSOR_IDS):
    return None
  ordered = np.array([acc_by_id[sensor_id] for sensor_id in SENSOR_IDS], dtype=float)
  lengths = np.linalg.norm(ordered, axis=1, keepdims=True)
  lengths[lengths == 0.0] = 1.0
  return ordered / lengths


class JointSensorLink:
  """Verbindung zur Sensorplatine. Nicht blockierend, wirft nicht."""

  name = "sensors"
  provides = ("joint_pos", "joint_vel", "segment_pitch")

  def __init__(self, sign: float = 1.0, vel_alpha: float = 0.15) -> None:
    self._serial = None
    self.port: str | None = None
    self.sign = sign
    self.last_error: str | None = None
    self.frames = 0
    self._parser = BinaryFrameParser()
    self._smooth_acc: dict[int, np.ndarray] = {}
    self._angles = np.zeros(NUM_JOINTS)
    self._diff = _FilteredDiff(NUM_JOINTS, vel_alpha)
    self._last_frame_ts: float | None = None
    self._last_poll_ts: float | None = None

  # -- Verbindung ------------------------------------------------------------

  @property
  def connected(self) -> bool:
    return self._serial is not None and getattr(self._serial, "is_open", False)

  @property
  def has_data(self) -> bool:
    """True, solange zuletzt gültige Winkel angekommen sind."""
    if not self.connected or self._last_frame_ts is None:
      return False
    return (time.monotonic() - self._last_frame_ts) < FRAME_TIMEOUT_S

  def connect(self, port: str, baudrate: int = BAUD_RATE) -> bool:
    if not SERIAL_AVAILABLE:
      self.last_error = "pyserial ist nicht installiert (pip install pyserial)."
      return False
    self.disconnect()
    try:
      self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=0.0, write_timeout=0.2)
      time.sleep(0.1)
      self._serial.reset_input_buffer()
      self._serial.write(MODE_COMMAND_ACC)  # nur Beschleunigung, höchste Rate
      self.port = port
      self.last_error = None
      self.frames = 0
      self._parser = BinaryFrameParser()
      self._smooth_acc.clear()
      self._diff.reset()
      self._last_frame_ts = None
      self._last_poll_ts = None
      return True
    except Exception as exc:
      self.last_error = f"{port}: {exc}"
      self._serial = None
      self.port = None
      return False

  def disconnect(self) -> None:
    if self._serial is not None:
      try:
        self._serial.close()
      except Exception:
        pass
    self._serial = None
    self.port = None
    self._last_frame_ts = None

  def _fail(self, exc: Exception) -> None:
    self.last_error = str(exc)
    self.disconnect()

  # -- Regelkreis ------------------------------------------------------------

  def poll(self) -> None:
    """Alles Gepufferte lesen und die Winkel aus dem neuesten Frame bestimmen.

    Die Platine sendet deutlich schneller, als geregelt wird; wie beim
    Motor-Controller zählt nur der jüngste vollständige Frame.
    """
    if not self.connected:
      return
    try:
      waiting = self._serial.in_waiting
      if waiting:
        self._parser.add_data(self._serial.read(waiting))
    except Exception as exc:
      self._fail(exc)
      return

    frames = self._parser.extract_frames()
    if not frames:
      return
    self.frames += len(frames)

    for sensor_id, values in frames[-1]["sensors"].items():
      raw = np.asarray(values, dtype=float)
      previous = self._smooth_acc.get(sensor_id)
      self._smooth_acc[sensor_id] = (
        raw if previous is None else ACC_EMA_ALPHA * raw + (1.0 - ACC_EMA_ALPHA) * previous
      )

    ordered = order_and_normalize(self._smooth_acc)
    if ordered is None:
      return  # noch nicht jeder Sensor gesehen

    now = time.monotonic()
    dt = 0.02 if self._last_poll_ts is None else max(now - self._last_poll_ts, 1e-3)
    self._last_poll_ts = now
    self._angles = self.sign * solve_joint_angles(ordered)
    self._diff.update(self._angles, dt)
    self._last_frame_ts = now

  def signals(self) -> dict[str, np.ndarray]:
    return {
      "joint_pos": self._angles.copy(),
      "joint_vel": self._diff.vel.copy(),
      "segment_pitch": kinematics.segment_pitch_cos_sin(self._angles),
    }

  @property
  def joint_angles(self) -> np.ndarray:
    """Die 13 gemessenen Gelenkwinkel [rad], Basis -> Spitze."""
    return self._angles.copy()

  def angles_deg(self) -> np.ndarray:
    return np.degrees(self._angles)
