"""Verhalten des Regelkreises ohne Fenster und ohne Hardware."""

from __future__ import annotations

import numpy as np
import pytest

from spirob_control import policy as policy_module
from spirob_control.controller import (
  MODE_MANUAL,
  MODE_POLICY,
  SOURCE_HARDWARE,
  Controller,
)


def test_handbetrieb_stellt_die_reglerwerte():
  ctrl = Controller()
  ctrl.state.manual_forces = [40.0, 10.0]
  telemetry = ctrl.tick()
  assert telemetry.forces_n.tolist() == [40.0, 10.0]
  # Die Simulation bekommt dieselbe Kraft als ziehende (negative) Stellgröße.
  assert ctrl.sim.data.ctrl[:2].tolist() == [-40.0, -10.0]


def test_kraftgrenze_wirkt():
  ctrl = Controller()
  ctrl.state.manual_forces = [150.0, 150.0]
  ctrl.state.force_limit_n = 25.0
  assert ctrl.tick().forces_n.tolist() == [25.0, 25.0]


def test_not_aus_nimmt_die_kraft_weg():
  ctrl = Controller()
  ctrl.state.manual_forces = [80.0, 80.0]
  ctrl.tick()
  ctrl.trigger_emergency_stop()
  assert ctrl.tick().forces_n.tolist() == [0.0, 0.0]
  ctrl.release_emergency_stop()
  assert ctrl.state.emergency_stop is False


def test_policy_ohne_hardware_wird_abgelehnt():
  """Eine Policy, deren Sensordaten fehlen, darf nicht stillschweigend laufen."""
  ctrl = Controller()
  ctrl.load_policy(policy_module.ASSET_DIR / "reach_joints.npz")
  ctrl.set_mode(MODE_POLICY)
  ctrl.state.observation_source = SOURCE_HARDWARE  # nichts angeschlossen
  telemetry = ctrl.tick()
  assert ctrl.state.mode == MODE_MANUAL
  assert telemetry.forces_n.tolist() == [0.0, 0.0]
  assert "keine Verbindung" in (telemetry.message or "")


def test_reset_setzt_arm_und_historie_zurueck():
  ctrl = Controller()
  ctrl.state.manual_forces = [120.0, 0.0]
  for _ in range(100):
    ctrl.tick()
  assert abs(ctrl.sim.tcp_xz()[0]) > 0.05
  ctrl.reset_simulation()
  assert ctrl.sim.tcp_xz()[0] == pytest.approx(0.0, abs=1e-6)
  assert ctrl.state.manual_forces == [0.0, 0.0]


def test_telemetrie_bleibt_vollstaendig():
  ctrl = Controller()
  telemetry = ctrl.tick()
  assert telemetry.chain_xz is not None and telemetry.chain_xz.shape[1] == 2
  assert telemetry.hardware_force_n is None  # nichts verbunden
  assert np.isfinite(telemetry.error_m)
