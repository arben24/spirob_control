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


# ---------------------------------------------------------------------------
# Sensorplatine
# ---------------------------------------------------------------------------

def test_sensoren_liefern_die_gemessene_armform(sensor_link):
  from spirob_control import kinematics

  angles = np.full(13, 0.15)
  link, _master = sensor_link(angles)
  ctrl = Controller(sensors=link)
  ctrl.state.use_sensors = True
  telemetry = ctrl.tick()
  assert telemetry.measured_chain_xz is not None
  expected = kinematics.tcp_xz(angles, ctrl.sim.link_lengths)
  assert telemetry.measured_tcp_xz == pytest.approx(expected, abs=1e-6)
  # Der gemessene Arm ist gebogen, der simulierte steht noch gerade - die
  # beiden Spitzen dürfen also nicht zusammenfallen.
  assert telemetry.measured_tcp_xz != pytest.approx(telemetry.tcp_xz, abs=1e-3)


def test_ohne_haken_werden_sensordaten_ignoriert(sensor_link):
  """Die Platine darf angeschlossen sein, ohne benutzt zu werden."""
  link, _master = sensor_link(np.full(13, 0.1))
  ctrl = Controller(sensors=link)
  ctrl.state.use_sensors = False
  telemetry = ctrl.tick()
  assert telemetry.measured_chain_xz is None
  assert ctrl.sensors_active is False
  assert "joint_pos" not in ctrl.available_signals()


def test_policy_laeuft_mit_gemessenen_gelenkwinkeln(sensor_link):
  """Eine joints-Policy muss an der Hardware laufen, sobald die Platine hängt."""
  from spirob_control import policy as policy_module

  link, _master = sensor_link(np.full(13, 0.05))
  ctrl = Controller(sensors=link)
  ctrl.state.use_sensors = True
  ctrl.load_policy(policy_module.ASSET_DIR / "reach_joints.npz")
  ctrl.set_mode(MODE_POLICY)
  ctrl.state.observation_source = SOURCE_HARDWARE
  ok, reason = ctrl.policy_ready()
  assert ok, reason
  telemetry = ctrl.tick()
  assert ctrl.state.mode == MODE_POLICY  # kein Rückfall
  assert telemetry.action is not None


def test_veraltete_sensordaten_zaehlen_nicht_als_messung(sensor_link):
  """Ein stehengebliebener Stream darf nicht als aktuelle Armform durchgehen."""
  from spirob_control import sensors as sensors_module

  link, _master = sensor_link(np.full(13, 0.1))
  ctrl = Controller(sensors=link)
  ctrl.state.use_sensors = True
  assert ctrl.tick().measured_chain_xz is not None
  # Zeitstempel des letzten Frames künstlich altern lassen
  link._last_frame_ts -= sensors_module.FRAME_TIMEOUT_S + 1.0
  assert link.has_data is False
  assert ctrl.tick().measured_chain_xz is None
