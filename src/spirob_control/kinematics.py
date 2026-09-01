"""Vorwärtskinematik: von den Gelenkwinkeln zur Form des Arms.

Der SpiRob kann seine eigene Spitze nicht messen. Die Sensorplatine misst aber
die Neigung jedes Segments, daraus folgen die 13 Gelenkwinkel - und weil die
Kette starre Glieder mit bekannten Längen hat, folgt daraus die Form des ganzen
Arms samt Spitze. Genau das rechnet dieses Modul.

Damit wird aus der Sensorplatine mehr als eine Beobachtungsquelle für die
Policy: Die Schema-Ansicht kann zeigen, wo der Arm *wirklich* steht, und die
Telemetrie kann den kommandierten Zielpunkt gegen die *gemessene* Spitze
halten statt gegen die simulierte.

Zwei Größen, die leicht zu verwechseln sind:

* **Gelenkwinkel** ``q[i]`` - die Verdrehung eines Gelenks gegenüber dem
  vorherigen Segment.
* **Segmentneigung** - die absolute Neigung eines Segments gegenüber der
  Senkrechten, also die Summe aller Gelenkwinkel davor. Das ist die Größe, die
  die Beschleunigungssensoren physikalisch messen; die Platine gibt ihre
  Differenzen als Gelenkwinkel aus, und hier werden sie wieder aufsummiert.
  Der Schwerkraftbezug hebt sich in diesem Hin und Zurück auf.

Die Gliedlängen stammen aus demselben MuJoCo-Modell, auf dem die Policies
trainiert wurden (siehe :meth:`Simulation.link_lengths`) - eine kopierte
Konstante wäre eine Konstante, die still veraltet.
"""

from __future__ import annotations

import numpy as np


def segment_pitch(joint_angles) -> np.ndarray:
  """Absolute Neigung jedes Segments, Basis -> Spitze. Länge ``len(q) + 1``.

  Das Basissegment sitzt fest am Fuß, seine Neigung ist damit definitionsgemäß
  null; jedes weitere Segment addiert einen Gelenkwinkel.
  """
  q = np.asarray(joint_angles, dtype=float)
  return np.concatenate([[0.0], np.cumsum(q)])


def segment_pitch_cos_sin(joint_angles) -> np.ndarray:
  """Die Beobachtung ``segment_pitch`` des Trainings, aus Winkeln rekonstruiert.

  Reihenfolge wie im Training: erst alle Cosinus von der Basis zur Spitze, dann
  alle Sinus.
  """
  pitch = segment_pitch(joint_angles)
  return np.concatenate([np.cos(pitch), np.sin(pitch)])


def chain_xz(joint_angles, link_lengths) -> np.ndarray:
  """Stützpunkte der Kette in der x-z-Ebene, Form ``(len(link_lengths) + 1, 2)``.

  Ebene Kette, alle Gelenke drehen um y: eine Drehung um ``theta`` schickt die
  lokale z-Achse eines Segments nach ``(sin theta, cos theta)``. Der erste Punkt
  ist der Fußpunkt, der letzte die Spitze (TCP).
  """
  q = np.asarray(joint_angles, dtype=float)
  lengths = np.asarray(link_lengths, dtype=float)
  if q.size != lengths.size - 1:
    raise ValueError(
      f"{lengths.size} Gliedlängen brauchen {lengths.size - 1} Gelenkwinkel, "
      f"bekommen habe ich {q.size}."
    )
  theta = segment_pitch(q)
  points = np.zeros((lengths.size + 1, 2))
  points[1:, 0] = np.cumsum(lengths * np.sin(theta))
  points[1:, 1] = np.cumsum(lengths * np.cos(theta))
  return points


def tcp_xz(joint_angles, link_lengths) -> tuple[float, float]:
  """Position der Spitze (x, z) [m] im Basis-Koordinatensystem."""
  tip = chain_xz(joint_angles, link_lengths)[-1]
  return float(tip[0]), float(tip[1])
