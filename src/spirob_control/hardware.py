"""Serielle Verbindung zum Motor-Controller (ESP32) des SpiRob.

Protokoll (siehe ``COMMUNICATION_PROTOCOL.md`` im Trainings-Repo), 460800 Baud:

* **Host -> MCU**: ASCII-Zeilen, mit ``\\n`` abgeschlossen. Gebraucht werden
  ``start all`` (Kraftregelung an), ``f <motor> <newton>`` (Sollkraft),
  ``n all`` (Seillänge auf die aktuelle Lage nullen) und ``stop``.
* **MCU -> Host**: fortlaufend Binärpakete, ~600 Hz, unaufgefordert::

      0xAA 0x55 | uint32 zeitstempel_us | float kraft_0 | float kraft_1
                | float seil_0_mm | float seil_1_mm

  Dazu ein 3-Byte-Paket ``0xBB 0x66`` + Motorindex ("Schritt zu Ende"), das
  diese GUI nie auslöst, aber überliest, damit ein Streupaket den Parser nicht
  aus dem Tritt bringt.

Zwei Dinge sind hier wichtiger als Eleganz:

* **Nichts blockiert.** ``poll()`` liest nur, was schon im Puffer liegt. Der
  Regeltakt der GUI darf nicht an der seriellen Schnittstelle hängen bleiben.
* **Nichts wirft.** Ein abgezogenes USB-Kabel ist ein Betriebszustand, kein
  Programmfehler: die Verbindung geht in den Fehlerzustand, die GUI zeigt die
  Meldung an und läuft in der Simulation weiter.

Angeschlossen ist hier ausschließlich der Motor-Controller. Die
Beschleunigungssensor-Platine (13 Gelenkwinkel) ist eine zweite Quelle an einem
zweiten Port; sie wird von dieser GUI noch nicht gelesen -- deshalb sind auf
der Hardware nur Policies der Sensor-Level ``force`` und ``tendon`` nutzbar.
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field

import numpy as np

try:  # pyserial ist optional: ohne sie läuft die GUI im Simulationsbetrieb
  import serial
  from serial.tools import list_ports

  SERIAL_AVAILABLE = True
except Exception:  # pragma: no cover - hängt von der Installation ab
  serial = None  # type: ignore[assignment]
  list_ports = None  # type: ignore[assignment]
  SERIAL_AVAILABLE = False

BAUD_RATE = 460800
NUM_ACTUATORS = 2

HEADER = b"\xaa\x55"
STEP_END_HEADER = b"\xbb\x66"
STATUS_STRUCT = struct.Struct("<Iff ff")  # ts_us, kraft[2], seillaenge_mm[2]

SEND_INTERVAL_S = 0.02
"""Mindestabstand zwischen zwei ``f``-Kommandos je Motor (50 Hz)."""

FORCE_DEADBAND_N = 0.05
"""Kleinere Kraftänderungen werden nicht gesendet -- spart Bandbreite."""

VEL_FILTER_ALPHA = 0.15
"""Glättung der aus der Seillänge differenzierten Geschwindigkeit."""


@dataclass
class Status:
  """Letzte Rückmeldung des MCU."""

  timestamp_us: int = 0
  force_n: tuple[float, float] = (0.0, 0.0)
  rope_len_mm: tuple[float, float] = (0.0, 0.0)


def available_ports() -> list[tuple[str, str]]:
  """(Gerät, Beschreibung) aller seriellen Ports -- unter Windows ``COM3`` usw."""
  if not SERIAL_AVAILABLE:
    return []
  try:
    return [(p.device, p.description or p.device) for p in list_ports.comports()]
  except Exception:
    return []


def guess_port() -> str | None:
  """Plausibelster Port für den MCU, sonst None.

  Reine Bequemlichkeit für die Portauswahl: bevorzugt wird ein Eintrag, dessen
  Beschreibung nach USB-Seriell-Wandler klingt (CP210x, CH340, FTDI - die
  üblichen ESP32-Bretter).
  """
  ports = available_ports()
  if not ports:
    return None
  keywords = ("cp210", "ch340", "ch910", "ftdi", "silicon labs", "usb serial", "usb-serial")
  for device, description in ports:
    if any(k in description.lower() for k in keywords):
      return device
  return ports[0][0]


@dataclass
class _FilteredDiff:
  """Differenzierung mit Einpol-Glättung: wenig Verzögerung, wenig Rauschen."""

  size: int
  alpha: float = VEL_FILTER_ALPHA
  vel: np.ndarray = field(init=False)
  _prev: np.ndarray | None = field(default=None, init=False)

  def __post_init__(self) -> None:
    self.vel = np.zeros(self.size)

  def update(self, values: np.ndarray, dt: float) -> np.ndarray:
    if self._prev is not None and dt > 0.0:
      raw = (values - self._prev) / dt
      self.vel = self.alpha * raw + (1.0 - self.alpha) * self.vel
    self._prev = np.array(values, dtype=float)
    return self.vel

  def reset(self) -> None:
    self.vel = np.zeros(self.size)
    self._prev = None


class HardwareLink:
  """Verbindung zum Motor-Controller. Alle Methoden sind nicht-blockierend."""

  def __init__(self) -> None:
    self._serial = None
    self.port: str | None = None
    self.status = Status()
    self.last_error: str | None = None
    self.packets = 0
    self._tendon_len = np.zeros(NUM_ACTUATORS)
    self._diff = _FilteredDiff(NUM_ACTUATORS)
    self._prev_status: Status | None = None
    self._last_sent = [None, None]
    self._last_send_t = 0.0

  # -- Verbindung ------------------------------------------------------------

  @property
  def connected(self) -> bool:
    return self._serial is not None and getattr(self._serial, "is_open", False)

  def connect(self, port: str, baudrate: int = BAUD_RATE, null_tendons: bool = False) -> bool:
    """Port öffnen und Kraftregelung starten. Gibt den Erfolg zurück.

    ``null_tendons`` schickt ``n all`` und setzt damit den Nullpunkt der
    Seillängen auf die aktuelle Lage. Das ist nur richtig, wenn der Arm gerade
    tatsächlich gestreckt ist -- sonst passen die Seillängen nicht mehr zu dem,
    was die Policy im Training gesehen hat.
    """
    if not SERIAL_AVAILABLE:
      self.last_error = "pyserial ist nicht installiert (pip install pyserial)."
      return False
    self.disconnect()
    try:
      self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=0.0, write_timeout=0.2)
      time.sleep(0.1)
      self._serial.reset_input_buffer()
      self.port = port
      self.last_error = None
      self.packets = 0
      self._prev_status = None
      self._diff.reset()
      self._last_sent = [None, None]
      if null_tendons:
        self._write("n all")
        time.sleep(0.05)
      self._write("start all")
      return True
    except Exception as exc:
      self.last_error = f"{port}: {exc}"
      self._serial = None
      self.port = None
      return False

  def disconnect(self) -> None:
    """Motoren stoppen und Port schließen. Fehler werden bewusst geschluckt."""
    if self._serial is not None:
      try:
        self._write("stop")
      except Exception:
        pass
      try:
        self._serial.close()
      except Exception:
        pass
    self._serial = None
    self.port = None

  def _write(self, command: str) -> None:
    if self._serial is None:
      return
    self._serial.write((command + "\n").encode("ascii"))

  def _fail(self, exc: Exception) -> None:
    """Verbindung nach einem Fehler sauber aufgeben, ohne die GUI zu stören."""
    self.last_error = str(exc)
    try:
      if self._serial is not None:
        self._serial.close()
    except Exception:
      pass
    self._serial = None
    self.port = None

  # -- Regelkreis ------------------------------------------------------------

  def send_forces(self, forces_n, force: bool = False) -> None:
    """Sollkräfte [N, Betrag] senden -- gedrosselt und mit Totband.

    ``force=True`` umgeht beides; das braucht der Not-Aus, der auch dann
    ankommen muss, wenn er sich vom letzten Wert kaum unterscheidet.
    """
    if not self.connected:
      return
    now = time.monotonic()
    if not force and now - self._last_send_t < SEND_INTERVAL_S:
      return
    self._last_send_t = now
    try:
      for i in range(NUM_ACTUATORS):
        value = float(np.clip(forces_n[i], 0.0, 150.0))
        previous = self._last_sent[i]
        if force or previous is None or abs(value - previous) > FORCE_DEADBAND_N:
          self._write(f"f {i} {value:.2f}")
          self._last_sent[i] = value
    except Exception as exc:
      self._fail(exc)

  def stop(self) -> None:
    """Not-Aus: Kräfte auf null und Regelung aus."""
    if not self.connected:
      return
    try:
      self.send_forces([0.0, 0.0], force=True)
      self._write("stop")
    except Exception as exc:
      self._fail(exc)

  def start(self) -> None:
    """Kraftregelung nach einem Not-Aus wieder einschalten."""
    if not self.connected:
      return
    try:
      self._write("start all")
      self._last_sent = [None, None]
    except Exception as exc:
      self._fail(exc)

  def poll(self) -> None:
    """Alles Gepufferte lesen und den neuesten Status übernehmen.

    Der MCU sendet mit ~600 Hz, die GUI regelt mit 50 Hz. Für einen Regelschritt
    ist nur "wie sieht es jetzt aus" interessant -- der Puffer wird deshalb
    geleert und nur das letzte gültige Paket behalten. Das ist zugleich die
    einfachste und die verzögerungsärmste Variante.
    """
    if not self.connected:
      return
    latest: Status | None = None
    try:
      while self._serial.in_waiting >= 1:
        byte0 = self._serial.read(1)
        if not byte0:
          break
        if byte0 == HEADER[:1]:
          if self._serial.read(1) != HEADER[1:]:
            continue
          payload = self._serial.read(STATUS_STRUCT.size)
          if len(payload) != STATUS_STRUCT.size:
            break
          ts, f0, f1, r0, r1 = STATUS_STRUCT.unpack(payload)
          latest = Status(timestamp_us=ts, force_n=(f0, f1), rope_len_mm=(r0, r1))
          self.packets += 1
        elif byte0 == STEP_END_HEADER[:1]:
          if self._serial.read(1) != STEP_END_HEADER[1:]:
            continue
          self._serial.read(1)  # Motorindex, hier ohne Bedeutung
        # sonst: Streubyte (z. B. eine Klartextzeile der Firmware), überlesen
    except Exception as exc:
      self._fail(exc)
      return

    if latest is None:
      return  # kein neues Paket: letzter Stand bleibt gültig

    dt = 0.02
    if self._prev_status is not None and latest.timestamp_us > self._prev_status.timestamp_us:
      dt = max((latest.timestamp_us - self._prev_status.timestamp_us) * 1e-6, 1e-3)
    self._prev_status = self.status
    self.status = latest

    # Die Firmware zählt aufgewickelte Seillänge in mm ab dem Nullpunkt.
    # Negiert und in Meter ist das dieselbe Größe, die die Simulation als
    # tendon_len liefert (Seil kürzer als in Ruhelage -> negativer Wert).
    self._tendon_len = -np.array(latest.rope_len_mm) / 1000.0
    self._diff.update(self._tendon_len, dt)

  def signals(self) -> dict[str, np.ndarray]:
    """Signale, die der Motor-Controller für eine Policy liefern kann."""
    return {
      "tendon_len": self._tendon_len.copy(),
      "tendon_vel": self._diff.vel.copy(),
      "force": np.array(self.status.force_n),
    }

  @property
  def provides(self) -> tuple[str, ...]:
    return ("tendon_len", "tendon_vel", "force")
