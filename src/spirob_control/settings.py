"""Merkt sich die zuletzt benutzten Einstellungen zwischen zwei Starts.

Nur Bequemlichkeit: Port, Policy, Betriebsart und Ansicht. Die Datei liegt im
Benutzerprofil (unter Windows ``%USERPROFILE%\\.spirob_control.json``), nicht im
Repository -- die GUI läuft auch dann korrekt, wenn sie fehlt, unlesbar ist
oder veraltete Werte enthält. Deshalb ist hier alles in ``try`` gefasst: eine
kaputte Einstellungsdatei darf den Start nicht verhindern.
"""

from __future__ import annotations

import json
from pathlib import Path

SETTINGS_PATH = Path.home() / ".spirob_control.json"

DEFAULTS: dict = {
  "port": "",
  "sensor_port": "",
  "sensor_flip": False,
  "policy": "reach_tendon.npz",
  "view_mode": "3d",
  "ui_scale": 1.0,
  "force_limit_n": 150.0,
  "send_to_hardware": False,
}


def load() -> dict:
  values = dict(DEFAULTS)
  try:
    if SETTINGS_PATH.exists():
      stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
      if isinstance(stored, dict):
        values.update({k: v for k, v in stored.items() if k in DEFAULTS})
  except Exception:
    pass
  return values


def save(values: dict) -> None:
  try:
    SETTINGS_PATH.write_text(
      json.dumps({k: v for k, v in values.items() if k in DEFAULTS}, indent=2),
      encoding="utf-8",
    )
  except Exception:
    pass
