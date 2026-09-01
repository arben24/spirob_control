"""Der Regelkreis: verbindet Bedienung, Simulation, Policy und Hardware.

Absichtlich frei von GUI-Code. Die Oberfläche setzt Sollwerte
(:class:`ControlState`) und ruft 50-mal je Sekunde :meth:`Controller.tick`
auf; alles Fachliche passiert hier. Das hält die GUI dumm und macht den
Regelkreis ohne Fenster testbar (siehe ``tests/``).

Ein Takt läuft immer in derselben Reihenfolge ab:

1. Hardware-Telemetrie abholen (nicht blockierend),
2. Sollkräfte bestimmen -- je nach Modus aus den Schiebereglern oder aus der
   Policy,
3. Kräfte auf das Sicherheitslimit begrenzen,
4. Simulation einen Regelschritt weiterrechnen,
5. Kräfte an die Hardware schicken (falls aktiv),
6. Telemetrie für die Anzeige einsammeln.

Die Simulation läuft **immer** mit, auch im Hardwarebetrieb: sie ist die
Anzeige und der Vergleichsmaßstab. Ob die Policy dabei die Sensordaten der
Simulation oder die der echten Seilencoder sieht, entscheidet
``ControlState.observation_source``.

Kraftkonvention: nach außen (GUI, Hardware, dieses Modul) sind Seilkräfte
Beträge in Newton, ``0 .. 150``. Nur die Simulation rechnet intern mit
negativen (ziehenden) Stellgrößen.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from . import workspace
from .hardware import HardwareLink
from .policy import Policy
from .simulation import FORCE_LIMIT_N, NUM_TENDONS, Simulation

MODE_MANUAL = "manual"
MODE_POLICY = "policy"

SOURCE_SIM = "sim"
SOURCE_HARDWARE = "hardware"


def action_to_forces(action) -> np.ndarray:
  """Policy-Aktion in Seilkräfte [N, Betrag] umrechnen.

  Bildet ``TendonEffortActionCfg(scale=75, offset=-75, clip=(-150, 0))`` aus
  dem Training nach und dreht das Vorzeichen um: die Simulation erwartet eine
  ziehende, also negative Stellgröße ``clip(a*75 - 75, -150, 0)``, die Firmware
  dagegen den Betrag der Zugkraft. Das ist genau deren Negation.
  """
  return np.clip(75.0 - 75.0 * np.asarray(action, dtype=float), 0.0, FORCE_LIMIT_N)


@dataclass
class ControlState:
  """Alles, was die Oberfläche verstellen kann."""

  mode: str = MODE_MANUAL
  manual_forces: list[float] = field(default_factory=lambda: [0.0, 0.0])
  target_xz: tuple[float, float] = (0.0, workspace.SHELL_RADIUS)
  observation_source: str = SOURCE_SIM
  send_to_hardware: bool = False
  force_limit_n: float = FORCE_LIMIT_N
  emergency_stop: bool = False


@dataclass
class Telemetry:
  """Momentaufnahme für die Anzeige. Wird je Takt neu gefüllt."""

  forces_n: np.ndarray = field(default_factory=lambda: np.zeros(NUM_TENDONS))
  action: np.ndarray | None = None
  tcp_xz: tuple[float, float] = (0.0, 0.0)
  target_xz: tuple[float, float] = (0.0, 0.0)
  error_m: float = 0.0
  chain_xz: np.ndarray | None = None
  hardware_force_n: np.ndarray | None = None
  hardware_rope_mm: np.ndarray | None = None
  rate_hz: float = 0.0
  tick_ms: float = 0.0
  ticks: int = 0
  message: str | None = None


class Controller:
  """Hält Simulation, Hardware und Policy zusammen und rechnet den Takt."""

  def __init__(self, simulation: Simulation | None = None, hardware: HardwareLink | None = None) -> None:
    self.sim = simulation or Simulation()
    self.hardware = hardware or HardwareLink()
    self.state = ControlState()
    self.telemetry = Telemetry()
    self.policy: Policy | None = None
    self.message: str | None = None

    self._periods = deque(maxlen=100)
    self._last_tick: float | None = None
    self._ticks = 0

  # -- Policy ----------------------------------------------------------------

  def load_policy(self, path) -> None:
    """Policy laden und ihre Historie zurücksetzen."""
    self.policy = Policy(path)
    self.policy.reset()

  def unload_policy(self) -> None:
    self.policy = None

  def policy_ready(self) -> tuple[bool, str]:
    """Kann die aktuelle Policy mit der gewählten Datenquelle laufen?

    Gibt (ja/nein, Begründung) zurück. Die Simulation liefert jedes Signal;
    an der Hardware hängt derzeit nur der Motor-Controller, also fehlen dort
    Gelenkwinkel und Segmentneigungen.
    """
    if self.policy is None:
      return False, "Keine Policy geladen."
    if self.state.observation_source == SOURCE_SIM:
      return True, ""
    if not self.hardware.connected:
      return False, "Hardware-Rückmeldung gewählt, aber keine Verbindung."
    missing = [s for s in self.policy.required_signals if s not in self.hardware.provides]
    if missing:
      return False, (
        f"Diese Policy braucht {', '.join(missing)}. Der Motor-Controller liefert das "
        "nicht - dafür wäre die Beschleunigungssensor-Platine nötig. Sensor-Level "
        "'force' oder 'tendon' wählen oder Rückmeldung aus der Simulation nehmen."
      )
    return True, ""

  # -- Bedienung -------------------------------------------------------------

  def reset_simulation(self) -> None:
    """Arm zurück in die Ruhelage und Policy-Historie leeren."""
    self.sim.reset()
    if self.policy is not None:
      self.policy.reset()
    self.state.manual_forces = [0.0, 0.0]

  def set_mode(self, mode: str) -> None:
    if mode == self.state.mode:
      return
    self.state.mode = mode
    if mode == MODE_POLICY and self.policy is not None:
      # Ohne Reset sähe die Policy als "Vergangenheit" den Handbetrieb.
      self.policy.reset()
    if mode == MODE_MANUAL:
      self.state.manual_forces = [0.0, 0.0]

  def trigger_emergency_stop(self) -> None:
    self.state.emergency_stop = True
    self.state.manual_forces = [0.0, 0.0]
    self.hardware.stop()
    self.message = "Not-Aus ausgelöst: Kräfte auf 0 N, Kraftregelung gestoppt."

  def release_emergency_stop(self) -> None:
    self.state.emergency_stop = False
    self.hardware.start()
    if self.policy is not None:
      self.policy.reset()
    self.message = "Not-Aus aufgehoben."

  # -- Regeltakt -------------------------------------------------------------

  def tick(self) -> Telemetry:
    """Einen Regelschritt rechnen (20 ms Modellzeit) und Telemetrie liefern."""
    begin = time.perf_counter()
    if self._last_tick is not None:
      self._periods.append(begin - self._last_tick)
    self._last_tick = begin
    self._ticks += 1

    self.hardware.poll()

    action: np.ndarray | None = None
    if self.state.emergency_stop:
      forces = np.zeros(NUM_TENDONS)
    elif self.state.mode == MODE_POLICY and self.policy is not None:
      ok, reason = self.policy_ready()
      if not ok:
        # Nicht heimlich weiterfahren: zurück in den Handbetrieb, Kräfte auf 0.
        self.state.mode = MODE_MANUAL
        self.state.manual_forces = [0.0, 0.0]
        self.message = reason
        forces = np.zeros(NUM_TENDONS)
      else:
        signals = (
          self.hardware.signals()
          if self.state.observation_source == SOURCE_HARDWARE
          else self.sim.signals()
        )
        try:
          action = self.policy.act(self.state.target_xz, signals)
          forces = action_to_forces(action)
        except Exception as exc:
          self.state.mode = MODE_MANUAL
          self.state.manual_forces = [0.0, 0.0]
          self.message = f"Policy gestoppt: {exc}"
          action = None
          forces = np.zeros(NUM_TENDONS)
    else:
      forces = np.array(self.state.manual_forces, dtype=float)

    forces = np.clip(forces, 0.0, self.state.force_limit_n)

    self.sim.apply_forces(forces)
    self.sim.step()

    if self.state.send_to_hardware and not self.state.emergency_stop:
      self.hardware.send_forces(forces)

    tcp = self.sim.tcp_xz()
    target = self.state.target_xz
    mean_period = float(np.mean(self._periods)) if self._periods else 0.0
    self.telemetry = Telemetry(
      forces_n=forces,
      action=action,
      tcp_xz=tcp,
      target_xz=target,
      error_m=float(np.hypot(tcp[0] - target[0], tcp[1] - target[1])),
      chain_xz=self.sim.chain_xz(),
      hardware_force_n=np.array(self.hardware.status.force_n) if self.hardware.connected else None,
      hardware_rope_mm=np.array(self.hardware.status.rope_len_mm) if self.hardware.connected else None,
      rate_hz=(1.0 / mean_period) if mean_period > 0 else 0.0,
      tick_ms=(time.perf_counter() - begin) * 1000.0,
      ticks=self._ticks,
      message=self.message,
    )
    return self.telemetry

  def shutdown(self) -> None:
    """Beim Beenden: Motoren stromlos, Port zu. Darf nie werfen."""
    try:
      self.hardware.stop()
    finally:
      self.hardware.disconnect()
