"""Prüft, dass die exportierten Policies zum Modell und zur Simulation passen.

Der teure Teil dieses Projekts ist nicht der Code, sondern die Übereinstimmung
zwischen dem, was im Training gelernt wurde, und dem, was die GUI dem Netz
vorsetzt. Diese Tests sichern genau diese Nahtstelle ab: Layout, Dimensionen
und - im Rollout - dass die Policy den Arm tatsächlich zum Ziel bringt.
"""

from __future__ import annotations

import numpy as np
import pytest

from spirob_control import policy as policy_module
from spirob_control import workspace
from spirob_control.controller import action_to_forces
from spirob_control.simulation import FORCE_LIMIT_N, Simulation

ALL_POLICIES = policy_module.available_policies()


def test_policies_vorhanden():
  assert ALL_POLICIES, "Im Ordner assets/policies liegt keine einzige Policy."


@pytest.mark.parametrize("info", ALL_POLICIES, ids=lambda i: i.path.stem)
def test_layout_passt_zum_netz(info):
  """Summe der Termdimensionen mal Historie muss die Netzeingabe ergeben."""
  loaded = policy_module.Policy(info.path)
  assert sum(t.dim for t in loaded.terms) * loaded.history_length == loaded.input_dim
  assert loaded.action_dim == 2


@pytest.mark.parametrize("info", ALL_POLICIES, ids=lambda i: i.path.stem)
def test_simulation_liefert_alle_signale(info):
  """Was die Policy verlangt, muss die Simulation in genau dieser Länge liefern."""
  sim = Simulation()
  signals = sim.signals()
  loaded = policy_module.Policy(info.path)
  for term in loaded.terms:
    if term.name in ("target", "last_action"):
      continue
    assert term.name in signals, f"Simulation liefert {term.name!r} nicht"
    assert len(signals[term.name]) == term.dim


@pytest.mark.parametrize("info", ALL_POLICIES, ids=lambda i: i.path.stem)
def test_beobachtung_hat_richtige_laenge(info):
  loaded = policy_module.Policy(info.path)
  sim = Simulation()
  obs = loaded.observation((0.0, 0.33), sim.signals())
  assert obs.shape == (loaded.input_dim,)


def test_historie_wird_beim_start_aufgefuellt():
  """Der erste Takt darf keine künstlichen Nullen in der Vergangenheit zeigen.

  Beim ersten Push füllt mjlab den ganzen Ringpuffer mit dem ersten Wert; wird
  das hier nicht nachgebildet, sieht die Policy einen Sprung, den es im
  Training nie gab.
  """
  loaded = policy_module.Policy(policy_module.ASSET_DIR / "reach_force.npz")
  obs = loaded.observation((0.1, 0.3), {})
  target_block = obs[: 3 * loaded.history_length].reshape(loaded.history_length, 3)
  assert np.allclose(target_block, [0.1, 0.0, 0.3])


def test_aktion_wird_begrenzt():
  loaded = policy_module.Policy(policy_module.ASSET_DIR / "reach_force.npz")
  action = loaded.act((5.0, 5.0), {})  # weit außerhalb des trainierten Bereichs
  assert np.all(np.abs(action) <= loaded.action_clip + 1e-9)


def test_kraftabbildung_entspricht_dem_training():
  """action -> Kraft muss TendonEffortActionCfg(scale=75, offset=-75) spiegeln."""
  assert action_to_forces([-1.0, 1.0])[0] == pytest.approx(FORCE_LIMIT_N)
  assert action_to_forces([-1.0, 1.0])[1] == pytest.approx(0.0)
  assert action_to_forces([0.0, 0.0])[0] == pytest.approx(75.0)
  # Außerhalb des Bereichs wird geklemmt, nicht extrapoliert.
  assert action_to_forces([-5.0, 5.0]).tolist() == [FORCE_LIMIT_N, 0.0]


@pytest.mark.parametrize("angle", [-1.0, 0.6])
def test_policy_erreicht_das_ziel(angle):
  """Rollout in der Simulation: die Spitze muss in die Nähe des Ziels kommen.

  Die Schranke von 120 mm ist bewusst großzügig - geprüft wird nicht die Güte
  der Regelung (die steht im Trainingsprotokoll), sondern dass die Kette aus
  Export, Beobachtungsaufbau und Kraftabbildung insgesamt stimmt. Ist irgendwo
  darin die Reihenfolge vertauscht, landet der Arm meterweit daneben oder
  klappt vollständig ein.
  """
  loaded = policy_module.Policy(policy_module.ASSET_DIR / "reach_joints.npz")
  sim = Simulation()
  target = workspace.shell_point(angle)
  for _ in range(750):  # 15 s bei 50 Hz
    action = loaded.act(target, sim.signals())
    sim.apply_forces(action_to_forces(action))
    sim.step()
  x, z = sim.tcp_xz()
  assert np.hypot(x - target[0], z - target[1]) < 0.12
