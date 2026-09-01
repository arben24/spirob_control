"""Ausführung der trainierten Policies -- ohne PyTorch, nur mit NumPy.

Eine Policy ist hier ein exportiertes ``.npz`` aus ``tools/export_policy.py``:
die Gewichte des Actor-MLP plus ein Manifest, das beschreibt, wie der
Beobachtungsvektor aufgebaut sein muss. Der Vorwärtspass ist eine Kette aus
``Linear`` + ``ELU`` mit ``Linear`` am Ende; die deterministische Aktion ist
exakt die Netzausgabe (die Policies sind ohne Beobachtungsnormalisierung und
mit skalarer Standardabweichung trainiert). Damit braucht die GUI zur
Laufzeit weder PyTorch noch mjlab noch eine GPU.

Der eigentlich heikle Teil ist nicht das Netz, sondern der *Beobachtungsvektor*:
Reihenfolge der Terme, Dimension je Term und die Historie über fünf Zeitschritte
müssen exakt dem Training entsprechen. Weicht auch nur die Reihenfolge ab,
rechnet das Netz weiter und der Arm bewegt sich einfach falsch. Deshalb kommt
das Layout aus dem Manifest (beim Export gegen die Netzdimension geprüft) und
wird hier bei jedem Term noch einmal gegen die tatsächlich gelieferte Länge
geprüft.

Aufbau des Vektors (Beispiel Sensor-Level "tendon", 45 Werte)::

    [target(t-4) ... target(t)] [last_action(t-4) ... last_action(t)]
    [tendon_len(t-4) ... tendon_len(t)] [tendon_vel(t-4) ... tendon_vel(t)]

also je Term die komplette Historie von alt nach neu, Terme in
Manifest-Reihenfolge -- genau das, was mjlabs ``CircularBuffer`` mit
``flatten_history_dim`` erzeugt.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ASSET_DIR = Path(__file__).resolve().parent / "assets" / "policies"

# Terme, die die GUI selbst füllt; alles andere muss von der aktiven
# Datenquelle (Simulation oder Hardware) als Signal kommen.
_TARGET_TERM = "target"
_LAST_ACTION_TERM = "last_action"


@dataclass(frozen=True)
class TermSpec:
  name: str
  dim: int


@dataclass(frozen=True)
class PolicyInfo:
  """Was die GUI über eine Policy wissen muss, ohne sie zu laden."""

  path: Path
  name: str
  task: str
  sensor_level: str
  description: str
  input_dim: int
  action_dim: int
  history_length: int
  required_signals: tuple[str, ...]
  iteration: int

  @property
  def label(self) -> str:
    return f"{self.name}  [{self.sensor_level}]"


def _elu(x: np.ndarray) -> np.ndarray:
  """ELU wie in PyTorch: x für x > 0, sonst exp(x) - 1 (alpha = 1)."""
  return np.where(x > 0.0, x, np.expm1(np.minimum(x, 0.0)))


def available_policies(directory: Path | None = None) -> list[PolicyInfo]:
  """Alle mitgelieferten Policies, alphabetisch nach Sensor-Level sortiert."""
  directory = directory or ASSET_DIR
  infos: list[PolicyInfo] = []
  for path in sorted(directory.glob("*.npz")):
    try:
      infos.append(read_info(path))
    except Exception as exc:  # eine kaputte Datei darf die GUI nicht blockieren
      print(f"[WARN] Policy {path.name} konnte nicht gelesen werden: {exc}")
  order = {"force": 0, "tendon": 1, "imu": 2, "joints": 3}
  infos.sort(key=lambda i: (order.get(i.sensor_level, 99), i.name))
  return infos


def _manifest(path: Path) -> dict:
  with np.load(path, allow_pickle=False) as data:
    return json.loads(str(data["manifest"]))


def read_info(path: Path) -> PolicyInfo:
  manifest = _manifest(path)
  return PolicyInfo(
    path=path,
    name=manifest.get("name", path.stem),
    task=manifest.get("task", "?"),
    sensor_level=manifest.get("sensor_level", "?"),
    description=manifest.get("description", ""),
    input_dim=int(manifest["input_dim"]),
    action_dim=int(manifest["action_dim"]),
    history_length=int(manifest["history_length"]),
    required_signals=tuple(manifest.get("required_signals", ())),
    iteration=int(manifest.get("iteration", -1)),
  )


class Policy:
  """Geladenes Netz samt Beobachtungs-Historie.

  Nicht threadsicher und bewusst zustandsbehaftet: die Historie gehört zu
  genau einem laufenden Regelkreis. Beim Moduswechsel oder nach einem Reset
  ``reset()`` aufrufen, sonst sieht das Netz einen Sprung in der Vergangenheit.
  """

  def __init__(self, path: Path) -> None:
    self.info = read_info(path)
    manifest = _manifest(path)
    self.terms = tuple(TermSpec(t["name"], int(t["dim"])) for t in manifest["terms"])
    self.history_length = int(manifest["history_length"])
    self.action_clip = float(manifest.get("action_clip", 0.0))

    with np.load(path, allow_pickle=False) as data:
      num_layers = int(data["num_layers"])
      self.layers = [
        (np.ascontiguousarray(data[f"W{i}"], dtype=np.float64),
         np.ascontiguousarray(data[f"b{i}"], dtype=np.float64))
        for i in range(num_layers)
      ]

    self.input_dim = int(self.layers[0][0].shape[1])
    self.action_dim = int(self.layers[-1][0].shape[0])
    expected = sum(t.dim for t in self.terms) * self.history_length
    if expected != self.input_dim:
      raise ValueError(
        f"{path.name}: Layout ergibt {expected} Eingänge, das Netz erwartet "
        f"{self.input_dim}. Die Datei ist inkonsistent."
      )

    self._history: dict[str, deque] = {}
    self._last_action = np.zeros(self.action_dim)
    self.reset()

  # -- Regelkreis ------------------------------------------------------------

  def reset(self) -> None:
    """Historie leeren und letzte Aktion auf null setzen."""
    self._history = {t.name: deque(maxlen=self.history_length) for t in self.terms}
    self._last_action = np.zeros(self.action_dim)

  @property
  def required_signals(self) -> tuple[str, ...]:
    return self.info.required_signals

  def observation(self, target_xz: tuple[float, float], signals: dict[str, np.ndarray]) -> np.ndarray:
    """Beobachtungsvektor aus Ziel, letzter Aktion und Sensorsignalen bauen.

    Beim ersten Aufruf wird jeder Term über die ganze Historie kopiert, damit
    das Netz nicht mit künstlichen Nullen in der Vergangenheit startet -- das
    macht mjlabs ``CircularBuffer`` beim ersten Push genauso.
    """
    for term in self.terms:
      if term.name == _TARGET_TERM:
        # Der SpiRob biegt sich in der x-z-Ebene; y ist im Training immer 0.
        value = np.array([target_xz[0], 0.0, target_xz[1]])
      elif term.name == _LAST_ACTION_TERM:
        value = self._last_action
      else:
        if term.name not in signals:
          raise KeyError(
            f"Die Policy braucht das Signal {term.name!r}, die aktive Datenquelle "
            "liefert es nicht."
          )
        value = np.asarray(signals[term.name], dtype=np.float64).reshape(-1)
      if value.size != term.dim:
        raise ValueError(
          f"Signal {term.name!r} hat {value.size} Werte, die Policy erwartet "
          f"{term.dim}. Modell und Policy passen nicht zusammen."
        )
      buffer = self._history[term.name]
      if not buffer:
        buffer.extend([value] * self.history_length)
      else:
        buffer.append(value)

    return np.concatenate([np.concatenate(list(self._history[t.name])) for t in self.terms])

  def forward(self, obs: np.ndarray) -> np.ndarray:
    """Roher Vorwärtspass: Linear + ELU, letzte Schicht ohne Aktivierung."""
    x = obs
    for i, (weight, bias) in enumerate(self.layers):
      x = weight @ x + bias
      if i < len(self.layers) - 1:
        x = _elu(x)
    return x

  def act(self, target_xz: tuple[float, float], signals: dict[str, np.ndarray]) -> np.ndarray:
    """Ein Regelschritt: Beobachtung bauen, Netz auswerten, Aktion begrenzen.

    Die Begrenzung auf ±``action_clip`` ist keine Kosmetik: im Training hat der
    RSL-RL-Wrapper die Aktion vor der Umgebung genauso beschnitten, und der
    beschnittene Wert ist es auch, der als ``last_action`` zurückgekoppelt wird.
    """
    obs = self.observation(target_xz, signals)
    action = self.forward(obs)
    if self.action_clip > 0.0:
      action = np.clip(action, -self.action_clip, self.action_clip)
    self._last_action = action
    return action
