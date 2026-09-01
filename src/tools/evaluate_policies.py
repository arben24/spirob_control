"""Misst, wie genau die mitgelieferten Policies das Ziel in der Simulation halten.

Fährt jede Policy über den trainierten Arbeitsraum: je Zielwinkel ein Rollout
von 15 s, der Fehler wird über die letzten 3 s gemittelt (eingeschwungener
Zustand, nicht die Anfahrt). Zusätzlich wird die Rechenzeit eines Regelschritts
gemessen.

Das Ergebnis landet als CSV in ``extra/`` und ist die Zahlengrundlage für das
Kapitel „Messungen und Evaluation" der schriftlichen Arbeit. Alles läuft in der
Simulation - Messwerte am realen Aufbau ersetzt das nicht.

Aufruf::

    python tools/evaluate_policies.py
"""

from __future__ import annotations

import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spirob_control import policy as policy_module  # noqa: E402
from spirob_control import workspace  # noqa: E402
from spirob_control.controller import action_to_forces  # noqa: E402
from spirob_control.simulation import Simulation  # noqa: E402

ANGLES = [-1.5, -1.2, -0.9, -0.6, -0.3, 0.0, 0.3, 0.6, 0.9, 1.2, 1.5]
DURATION_S = 15.0
SETTLE_S = 3.0  # letzte Sekunden, über die gemittelt wird
OUTPUT = Path(__file__).resolve().parents[2] / "extra" / "policy_auswertung.csv"


def rollout(loaded: policy_module.Policy, angle: float) -> tuple[float, float]:
  """(mittlerer Fehler im eingeschwungenen Zustand [m], Rechenzeit je Takt [ms])."""
  sim = Simulation()
  loaded.reset()
  target = workspace.shell_point(angle)
  steps = int(DURATION_S / sim.control_period)
  settle_from = steps - int(SETTLE_S / sim.control_period)

  errors: list[float] = []
  durations: list[float] = []
  for step in range(steps):
    begin = time.perf_counter()
    action = loaded.act(target, sim.signals())
    sim.apply_forces(action_to_forces(action))
    sim.step()
    durations.append((time.perf_counter() - begin) * 1000.0)
    if step >= settle_from:
      x, z = sim.tcp_xz()
      errors.append(float(np.hypot(x - target[0], z - target[1])))
  return statistics.fmean(errors), statistics.fmean(durations)


def main() -> None:
  OUTPUT.parent.mkdir(parents=True, exist_ok=True)
  rows: list[dict] = []
  for info in policy_module.available_policies():
    loaded = policy_module.Policy(info.path)
    errors: list[float] = []
    times: list[float] = []
    for angle in ANGLES:
      error, tick_ms = rollout(loaded, angle)
      errors.append(error)
      times.append(tick_ms)
      rows.append({
        "policy": info.path.stem,
        "sensor_level": info.sensor_level,
        "winkel_rad": f"{angle:.2f}",
        "fehler_mm": f"{error * 1000:.1f}",
        "takt_ms": f"{tick_ms:.3f}",
      })
    print(
      f"{info.sensor_level:>7}: Fehler {statistics.fmean(errors) * 1000:6.1f} mm im Mittel, "
      f"{min(errors) * 1000:5.1f} .. {max(errors) * 1000:6.1f} mm | "
      f"Takt {statistics.fmean(times):.3f} ms"
    )

  with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
  print(f"\nGeschrieben: {OUTPUT}")


if __name__ == "__main__":
  main()
