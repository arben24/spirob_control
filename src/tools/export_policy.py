"""Exportiert eine trainierte SpiRob-Policy in ein torch-freies ``.npz``-Paket.

Warum dieses Skript existiert
-----------------------------
Die Policies werden im Trainings-Repo (``RL_explor``, mjlab + rsl_rl + PyTorch,
CUDA) trainiert. Diese GUI soll aber auf einem beliebigen Windows-Rechner mit
``pip install -r requirements.txt`` laufen -- ohne PyTorch, ohne mjlab, ohne
GPU. Der Actor ist ein reines MLP aus ``Linear``- und ``ELU``-Schichten, und
der deterministische Aktionsvorschlag ist exakt dessen Ausgabe (die Policies
sind mit ``obs_normalization=False`` und skalarer Standardabweichung
trainiert). Damit lässt sich der Vorwärtspass in wenigen Zeilen NumPy
nachbilden -- siehe ``spirob_control/policy.py``.

Dieses Skript wird deshalb **einmalig im Trainings-Repo** ausgeführt und legt
die Gewichte plus das Beobachtungs-Layout als ``.npz`` in
``spirob_control/assets/policies/`` ab. Die ``.npz``-Dateien sind eingecheckt;
die GUI braucht dieses Skript zur Laufzeit nicht.

Aufruf (im Trainings-Repo, z. B. ``~/RL_explor``)::

    .venv/bin/python .../tools/export_policy.py \
        --checkpoint logs/rsl_rl/rl_explor_spirob_tcp_tendon/<run>/model_499.pt \
        --sensor-level tendon \
        --out .../spirob_control/assets/policies/reach_tendon.npz

Das Beobachtungs-Layout wird dabei **nicht** aus dem Checkpoint gelesen (das
würde eine komplette Sim-Umgebung bauen), sondern aus der Tabelle unten
rekonstruiert und anschließend gegen die Eingangsdimension des Netzes geprüft.
Passt beides nicht zusammen, bricht der Export ab, statt später in der GUI
einen plausibel aussehenden, aber falschen Vektor zu erzeugen.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

# Beobachtungs-Terme des Actors je Sensor-Level, in genau der Reihenfolge, in
# der mjlab sie konkateniert (Dict-Reihenfolge in
# ``base_env_cfg.make_actor_terms``). (Name, Dimension eines Frames).
#
# "target" ist beim Reach-Task die kommandierte TCP-Position (x, y, z) relativ
# zum Roboterfuß; y ist immer 0, weil der SpiRob in der x-z-Ebene arbeitet.
SENSOR_LEVELS: dict[str, list[tuple[str, int]]] = {
  "force": [("target", 3), ("last_action", 2)],
  "tendon": [("target", 3), ("last_action", 2), ("tendon_len", 2), ("tendon_vel", 2)],
  "imu": [
    ("target", 3),
    ("last_action", 2),
    ("tendon_len", 2),
    ("tendon_vel", 2),
    ("segment_pitch", 28),
  ],
  "joints": [("target", 3), ("last_action", 2), ("joint_pos", 13), ("joint_vel", 13)],
}

# Signale, die die jeweilige Datenquelle liefern muss. "target" und
# "last_action" füllt die GUI selbst.
SIGNAL_TERMS = ("tendon_len", "tendon_vel", "joint_pos", "joint_vel", "segment_pitch")

HISTORY_LENGTH = 5  # ObservationGroupCfg(history_length=5) im Reach-Task
ACTION_CLIP = 5.0  # RslRlOnPolicyRunnerCfg.clip_actions


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("--checkpoint", required=True, type=Path, help="model_*.pt aus logs/rsl_rl/...")
  parser.add_argument("--sensor-level", required=True, choices=sorted(SENSOR_LEVELS))
  parser.add_argument("--out", required=True, type=Path, help="Zieldatei (.npz)")
  parser.add_argument("--name", help="Anzeigename in der GUI (Default: aus --out abgeleitet)")
  parser.add_argument("--task", default="RlExplor-Spirob-Tcp-Reach", help="Task-ID für die Dokumentation")
  parser.add_argument("--history-length", type=int, default=HISTORY_LENGTH)
  parser.add_argument(
    "--description", default="", help="Ein Satz, den die GUI unter der Auswahl anzeigt"
  )
  return parser.parse_args()


def extract_layers(state_dict: dict) -> list[tuple[np.ndarray, np.ndarray]]:
  """(Gewicht, Bias) je Linear-Schicht des Actor-MLP, in Reihenfolge.

  Die Schlüssel heißen ``mlp.<idx>.weight`` / ``mlp.<idx>.bias``; die
  ungeraden Indizes sind die ELU-Aktivierungen und tauchen im ``state_dict``
  gar nicht auf. Sortiert wird numerisch nach ``<idx>`` -- lexikografisch wäre
  ``mlp.10`` vor ``mlp.2`` einsortiert und das Netz wäre still vertauscht.
  """
  indices = sorted(
    {int(key.split(".")[1]) for key in state_dict if key.startswith("mlp.") and key.endswith(".weight")}
  )
  if not indices:
    raise SystemExit("Im Checkpoint ist kein 'mlp.*'-Actor enthalten.")
  layers = []
  for idx in indices:
    weight = state_dict[f"mlp.{idx}.weight"].detach().cpu().numpy().astype(np.float32)
    bias = state_dict[f"mlp.{idx}.bias"].detach().cpu().numpy().astype(np.float32)
    layers.append((weight, bias))
  return layers


def main() -> None:
  args = parse_args()
  if not args.checkpoint.exists():
    raise SystemExit(f"Checkpoint nicht gefunden: {args.checkpoint}")

  checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
  if "actor_state_dict" not in checkpoint:
    raise SystemExit(f"Unerwartetes Checkpoint-Format, Schlüssel: {sorted(checkpoint)}")
  layers = extract_layers(checkpoint["actor_state_dict"])

  terms = SENSOR_LEVELS[args.sensor_level]
  expected_dim = sum(dim for _, dim in terms) * args.history_length
  actual_dim = int(layers[0][0].shape[1])
  if expected_dim != actual_dim:
    raise SystemExit(
      f"Layout des Sensor-Levels {args.sensor_level!r} ergibt {expected_dim} Eingänge, "
      f"das Netz erwartet aber {actual_dim}. Falsches Level oder anderer Task -- "
      "Export abgebrochen, damit die GUI keinen falschen Vektor baut."
    )

  manifest = {
    "name": args.name or args.out.stem,
    "task": args.task,
    "sensor_level": args.sensor_level,
    "description": args.description,
    "checkpoint": str(args.checkpoint),
    "iteration": int(checkpoint.get("iter", -1)),
    "input_dim": actual_dim,
    "action_dim": int(layers[-1][0].shape[0]),
    "action_clip": ACTION_CLIP,
    "history_length": args.history_length,
    "terms": [{"name": name, "dim": dim} for name, dim in terms],
    "required_signals": [name for name, _ in terms if name in SIGNAL_TERMS],
    "activation": "elu",
  }

  arrays: dict[str, np.ndarray] = {"manifest": np.array(json.dumps(manifest, indent=2))}
  for i, (weight, bias) in enumerate(layers):
    arrays[f"W{i}"] = weight
    arrays[f"b{i}"] = bias
  arrays["num_layers"] = np.array(len(layers))

  args.out.parent.mkdir(parents=True, exist_ok=True)
  np.savez_compressed(args.out, **arrays)

  params = sum(w.size + b.size for w, b in layers)
  shape = " -> ".join([str(actual_dim)] + [str(w.shape[0]) for w, _ in layers])
  print(f"[OK] {args.out}  ({args.out.stat().st_size / 1024:.0f} KiB)")
  print(f"     Task {args.task}, Level {args.sensor_level}, Iteration {manifest['iteration']}")
  print(f"     MLP {shape}, {params} Parameter")
  print(f"     Benötigte Signale: {manifest['required_signals'] or '(keine)'}")


if __name__ == "__main__":
  main()
