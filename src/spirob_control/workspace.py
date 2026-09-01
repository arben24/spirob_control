"""Geometrie des erreichbaren Arbeitsraums (Reach-Task).

Der SpiRob ist ein Tentakel mit fester Länge: er kann sich biegen, aber nicht
strecken. Erreichbare TCP-Positionen füllen deshalb keine Fläche, sondern
liegen auf einer dünnen, bogenförmigen *Schale*. Seitliches Biegen tauscht
Auslenkung gegen Radius:

    r(winkel) = SHELL_RADIUS - SHELL_CURVATURE * winkel**2   (± SHELL_BAND)

``winkel`` wird von der +z-Achse aus gemessen (positiv in Richtung +x) und ist
auf ±``ANGLE_LIMIT`` begrenzt. Alle Angaben in Metern bzw. Radiant im
Basis-Koordinatensystem des Roboters (x = seitlich, z = nach oben).

Genau aus dieser Verteilung wurden im Training die Ziele gezogen
(``TcpPositionCommandCfg`` in ``reach_env_cfg.py``). Ziele außerhalb sind nicht
verboten -- die Policy extrapoliert dann nur, was auf einem Seilzugroboter
meist als "beide Seile ziehen voll durch" endet. Die GUI zeigt das an, statt
es zu unterbinden.

Bewusst nur Standardbibliothek: dieses Modul wird auch von der Zeichenfläche
der GUI benutzt und darf nichts nachladen.
"""

from __future__ import annotations

import math
from typing import NamedTuple

ANGLE_LIMIT = 1.7
SHELL_RADIUS = 0.33
SHELL_CURVATURE = 0.045
SHELL_BAND = 0.08


class TargetInfo(NamedTuple):
  angle: float
  """Winkel zur +z-Achse [rad], positiv Richtung +x."""
  radius: float
  """Abstand vom Fußpunkt [m]."""
  shell_radius: float
  """Schalenradius bei diesem Winkel [m]."""
  deviation: float
  """Vorzeichenbehafteter Abstand zur Schale [m]; + ist außerhalb."""
  angle_ok: bool
  radius_ok: bool

  @property
  def ok(self) -> bool:
    """True, wenn das Ziel in der trainierten Verteilung liegt."""
    return self.angle_ok and self.radius_ok


def shell_radius(angle: float) -> float:
  return SHELL_RADIUS - SHELL_CURVATURE * angle**2


def shell_point(angle: float) -> tuple[float, float]:
  """Punkt (x, z) auf der Mittellinie der Schale beim gegebenen Winkel."""
  radius = shell_radius(angle)
  return radius * math.sin(angle), radius * math.cos(angle)


def polar_to_xz(angle: float, radius: float) -> tuple[float, float]:
  """Polarkoordinaten der Schale in eine Position in der x-z-Ebene."""
  return radius * math.sin(angle), radius * math.cos(angle)


def xz_to_polar(x: float, z: float) -> tuple[float, float]:
  """Umkehrung von :func:`polar_to_xz`: (winkel, radius)."""
  return math.atan2(x, z), math.hypot(x, z)


def describe(x: float, z: float) -> TargetInfo:
  angle, radius = xz_to_polar(x, z)
  r_shell = shell_radius(angle)
  deviation = radius - r_shell
  return TargetInfo(
    angle=angle,
    radius=radius,
    shell_radius=r_shell,
    deviation=deviation,
    angle_ok=abs(angle) <= ANGLE_LIMIT,
    radius_ok=abs(deviation) <= SHELL_BAND,
  )


def snap_to_shell(x: float, z: float) -> tuple[float, float]:
  """Nächster Punkt auf der Schalen-Mittellinie, auf den Winkelbereich begrenzt."""
  angle = max(-ANGLE_LIMIT, min(ANGLE_LIMIT, math.atan2(x, z)))
  return shell_point(angle)


def warnings_for(x: float, z: float) -> list[str]:
  """Lesbare Gründe, warum (x, z) außerhalb des trainierten Bereichs liegt.

  Leere Liste heißt: Ziel ist in Ordnung.
  """
  info = describe(x, z)
  messages: list[str] = []
  if not info.angle_ok:
    messages.append(
      f"Zielwinkel {info.angle:+.2f} rad liegt außerhalb des trainierten Bereichs "
      f"±{ANGLE_LIMIT:.2f} rad - die Policy extrapoliert."
    )
  if not info.radius_ok:
    messages.append(
      f"Zielradius {info.radius:.3f} m weicht {info.deviation:+.3f} m von der "
      f"Schale ab ({info.shell_radius:.3f} ±{SHELL_BAND:.2f} m bei Winkel "
      f"{info.angle:+.2f} rad) - der Tentakel ist nicht dehnbar, dieser Punkt "
      "ist vermutlich nicht haltbar."
    )
  return messages


def shell_outline(samples: int = 81) -> list[tuple[float, float]]:
  """Polygonzug der Schalen-Mittellinie für die Zeichenfläche der GUI."""
  step = 2.0 * ANGLE_LIMIT / (samples - 1)
  return [shell_point(-ANGLE_LIMIT + i * step) for i in range(samples)]


def shell_band(samples: int = 81) -> list[tuple[float, float]]:
  """Geschlossener Polygonzug um das ±``SHELL_BAND`` breite Band der Schale."""
  step = 2.0 * ANGLE_LIMIT / (samples - 1)
  inner: list[tuple[float, float]] = []
  outer: list[tuple[float, float]] = []
  for i in range(samples):
    angle = -ANGLE_LIMIT + i * step
    radius = shell_radius(angle)
    outer.append(polar_to_xz(angle, radius + SHELL_BAND))
    inner.append(polar_to_xz(angle, max(0.0, radius - SHELL_BAND)))
  return outer + inner[::-1]
