"""Digitaler Zwilling: das MuJoCo-Modell des SpiRob und seine Signale.

Das Modell (``assets/spirob.xml``) ist genau das, auf dem die Policies
trainiert wurden -- unverändert übernommen, damit Simulation und Policy
zusammenpassen. Es ist eine ebene Kette aus 14 Segmenten mit 13 Drehgelenken um
die y-Achse; zwei Seile (``tendon_0`` links, ``tendon_1`` rechts) laufen außen
an der Kette entlang und werden von zwei Kraftaktoren gezogen.

Zwei Konventionen, die man leicht verwechselt:

* **Sim-Stellgröße** ``ctrl`` ist eine *ziehende* Kraft und damit negativ,
  Bereich ``-150 .. 0`` N.
* **GUI und Hardware** rechnen mit dem Betrag der Seilkraft, ``0 .. 150`` N.

Umgerechnet wird ausschließlich hier (:meth:`Simulation.apply_forces`), damit
es dafür genau eine Stelle gibt.

Der Regeltakt ist derselbe wie im Training: 5 Simulationsschritte à 4 ms
ergeben 50 Hz Policy-Takt.
"""

from __future__ import annotations

from pathlib import Path

import mujoco
import numpy as np

MODEL_PATH = Path(__file__).resolve().parent / "assets" / "spirob.xml"

DECIMATION = 5
"""Simulationsschritte je Regelschritt (4 ms * 5 = 20 ms = 50 Hz)."""

FORCE_LIMIT_N = 150.0
"""Betrag der maximalen Seilkraft; entspricht ctrlrange = (-150, 0) im XML."""

TENDON_REST_LEN = 0.4258
"""Seillänge in der gestreckten Ruhelage, auf dem kompilierten Modell gemessen.

Wird abgezogen, damit die Beobachtung ``tendon_len`` um null herum liegt --
exakt wie ``mdp.tendon_len_rel`` im Training.
"""

NUM_SEGMENTS = 14
NUM_TENDONS = 2


class Simulation:
  """MuJoCo-Modell, Regelschritt und die Signale, die eine Policy braucht."""

  def __init__(self, model_path: Path | str = MODEL_PATH) -> None:
    self.model_path = Path(model_path)
    self.model = mujoco.MjModel.from_xml_path(str(self.model_path))
    self.data = mujoco.MjData(self.model)

    # Reihenfolgen wie im Training: mjlab löst Namensmuster in Modellreihenfolge
    # auf, also aufsteigende IDs. Für die Gelenke ist das j_12 (Basis) .. j_0
    # (Spitze), für die IMU-Sites site_imu_13 (Basis) .. site_imu_0 (Spitze).
    self.joint_ids = np.array(
      sorted(
        mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, f"j_{i}")
        for i in range(NUM_SEGMENTS - 1)
      )
    )
    self.imu_site_ids = np.array(
      sorted(
        mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, f"site_imu_{i}")
        for i in range(NUM_SEGMENTS)
      )
    )
    self.tendon_ids = np.array(
      [
        mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_TENDON, f"tendon_{i}")
        for i in range(NUM_TENDONS)
      ]
    )
    self.tcp_site_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, "site_tcp")
    if self.tcp_site_id < 0 or np.any(self.joint_ids < 0) or np.any(self.tendon_ids < 0):
      raise RuntimeError(f"{self.model_path} enthält nicht die erwarteten Gelenke/Seile/Sites.")

    self.qpos_adr = np.array([self.model.jnt_qposadr[j] for j in self.joint_ids])
    self.qvel_adr = np.array([self.model.jnt_dofadr[j] for j in self.joint_ids])

    # Gliedlängen der Kette, Basis -> Spitze: der Versatz eines Segments zum
    # nächsten, zuletzt der Versatz vom letzten Segment zum TCP. Aus dem
    # kompilierten Modell gelesen, damit die Vorwärtskinematik über die
    # gemessenen Winkel dieselbe Geometrie benutzt wie die Simulation.
    body_ids = [
      mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, f"seg_{i}")
      for i in range(NUM_SEGMENTS - 1, -1, -1)
    ]
    lengths = [float(self.model.body_pos[child][2]) for child in body_ids[1:]]
    lengths.append(float(self.model.site_pos[self.tcp_site_id][2]))
    self.link_lengths = np.array(lengths)

    self.reset()

  # -- Zustand ---------------------------------------------------------------

  def reset(self) -> None:
    """Zurück in die gestreckte Ruhelage, Seilkräfte auf null."""
    mujoco.mj_resetData(self.model, self.data)
    self.data.ctrl[:] = 0.0
    mujoco.mj_forward(self.model, self.data)

  @property
  def timestep(self) -> float:
    return float(self.model.opt.timestep)

  @property
  def control_period(self) -> float:
    """Dauer eines Regelschritts [s] -- 0.02 s bei 50 Hz."""
    return self.timestep * DECIMATION

  # -- Regelkreis ------------------------------------------------------------

  def apply_forces(self, forces_n) -> None:
    """Seilkräfte als Beträge [N] setzen (0 .. 150) und ins Modell schreiben."""
    forces = np.clip(np.asarray(forces_n, dtype=float), 0.0, FORCE_LIMIT_N)
    self.data.ctrl[:NUM_TENDONS] = -forces

  def step(self, substeps: int = DECIMATION) -> None:
    mujoco.mj_step(self.model, self.data, nstep=substeps)

  # -- Messgrößen ------------------------------------------------------------

  def signals(self) -> dict[str, np.ndarray]:
    """Alle Signale, die irgendeine Policy als Beobachtung braucht.

    Die Simulation ist die einzige Datenquelle, die *jedes* Signal liefern
    kann -- auf der Hardware fehlt je nach angeschlossener Platine das eine
    oder andere.
    """
    return {
      "tendon_len": self.data.ten_length[self.tendon_ids] - TENDON_REST_LEN,
      "tendon_vel": self.data.ten_velocity[self.tendon_ids].copy(),
      "joint_pos": self.data.qpos[self.qpos_adr].copy(),
      "joint_vel": self.data.qvel[self.qvel_adr].copy(),
      "segment_pitch": self.segment_pitch_cos_sin(),
      "force": np.abs(self.data.ctrl[:NUM_TENDONS].copy()),
    }

  def segment_pitch_cos_sin(self) -> np.ndarray:
    """Cosinus und Sinus der Neigung jedes Segments (Basis -> Spitze).

    Stellvertreter für die IMUs im XML: die Bewegung ist eben und dreht nur um
    y, ein fusionierter IMU-Wert reduziert sich also auf die Neigung des
    Segments. Aus der Rotationsmatrix der Site abgelesen: bei einer Drehung um
    y ist ``R[0, 2] = sin`` und ``R[2, 2] = cos``.
    """
    mats = self.data.site_xmat[self.imu_site_ids].reshape(-1, 3, 3)
    pitch = np.arctan2(mats[:, 0, 2], mats[:, 2, 2])
    return np.concatenate([np.cos(pitch), np.sin(pitch)])

  def tcp_xz(self) -> tuple[float, float]:
    """TCP-Position (x, z) [m] im Basis-Koordinatensystem."""
    pos = self.data.site_xpos[self.tcp_site_id]
    return float(pos[0]), float(pos[2])

  def chain_xz(self) -> np.ndarray:
    """Stützpunkte der Kette (x, z) von der Basis bis zum TCP, Form (N, 2).

    Basis für die 2D-Schemaansicht der GUI.
    """
    sites = self.data.site_xpos[self.imu_site_ids][:, [0, 2]]
    tcp = self.data.site_xpos[self.tcp_site_id][[0, 2]]
    return np.vstack([[0.0, 0.0], sites, tcp])

  def tendon_forces_n(self) -> np.ndarray:
    """Aktuell gestellte Seilkräfte als Beträge [N]."""
    return np.abs(self.data.ctrl[:NUM_TENDONS].copy())
