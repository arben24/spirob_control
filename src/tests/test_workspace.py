"""Geometrie des Arbeitsraums."""

from __future__ import annotations

import math

import pytest

from spirob_control import workspace


def test_schale_ist_am_scheitel_am_weitesten():
  assert workspace.shell_radius(0.0) == pytest.approx(workspace.SHELL_RADIUS)
  assert workspace.shell_radius(1.0) < workspace.SHELL_RADIUS


def test_polar_und_karthesisch_sind_umkehrbar():
  for angle in (-1.2, 0.0, 0.9):
    x, z = workspace.polar_to_xz(angle, 0.3)
    back_angle, back_radius = workspace.xz_to_polar(x, z)
    assert back_angle == pytest.approx(angle)
    assert back_radius == pytest.approx(0.3)


def test_punkte_auf_der_schale_gelten_als_gueltig():
  for angle in (-1.5, -0.5, 0.0, 0.5, 1.5):
    x, z = workspace.shell_point(angle)
    assert workspace.describe(x, z).ok
    assert workspace.warnings_for(x, z) == []


def test_zu_weit_aussen_wird_gemeldet():
  warnings = workspace.warnings_for(0.0, 0.9)
  assert warnings and "Zielradius" in warnings[0]


def test_ausserhalb_des_winkelbereichs_wird_gemeldet():
  x, z = workspace.polar_to_xz(2.5, 0.3)
  assert any("Zielwinkel" in w for w in workspace.warnings_for(x, z))


def test_einrasten_landet_auf_der_schale():
  x, z = workspace.snap_to_shell(0.6, 0.05)
  assert workspace.describe(x, z).deviation == pytest.approx(0.0, abs=1e-9)
  assert abs(math.atan2(x, z)) <= workspace.ANGLE_LIMIT + 1e-9
