"""Gemeinsame Testhilfen.

Vor allem eines: eine echte Sensoranbindung, gespeist über ein virtuelles
Terminalpaar. Damit läuft in den Tests derselbe Weg wie im Betrieb - Bytes auf
einer seriellen Leitung, Frame-Parser, Winkelberechnung, Glättung -, ohne dass
Hardware angeschlossen sein muss.
"""

from __future__ import annotations

import os
import struct
import time

import numpy as np
import pytest

from spirob_control import kinematics, sensors

HAS_PTY = hasattr(os, "openpty")
"""Virtuelle Terminals gibt es nur unter POSIX; unter Windows wird übersprungen."""


def build_frame(pitch_rad, frame_id: int = 1) -> bytes:
  """Ein ACC-Frame, in dem jedes Segment die angegebene Neigung hat.

  Die Sensoren messen die Schwerkraft im eigenen Koordinatensystem; bei einer
  Neigung ``p`` um die x-Achse ist das ``(0, cos p, -sin p)``.
  """
  payload = b""
  for sensor_id, pitch in zip(sensors.SENSOR_IDS, pitch_rad):
    payload += struct.pack("<B3f", sensor_id, 0.0, float(np.cos(pitch)), float(-np.sin(pitch)))
  head = sensors.FRAME_HEADER + sensors.FRAME_META.pack(
    frame_id, frame_id * 1000, sensors.MODE_ACC, len(sensors.SENSOR_IDS)
  )
  return head + payload


@pytest.fixture(autouse=True)
def isolierte_einstellungen(tmp_path, monkeypatch):
  """Kein Test schreibt in die echte Einstellungsdatei des Benutzers.

  Die Oberfläche merkt sich beim Schließen Port, Policy und Kraftgrenze in
  ``~/.spirob_control.json``. Ohne diese Umleitung würde ein Test, der die
  Kraftgrenze verstellt, sie dem nächsten echten Start hinterlassen - genau so
  ist bei der Entwicklung einmal eine auf 42 N gedeckelte Policy entstanden,
  die scheinbar grundlos schlecht geregelt hat.
  """
  from spirob_control import settings

  monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "einstellungen.json")


@pytest.fixture
def make_frame():
  """Gibt :func:`build_frame` an den Test weiter."""
  return build_frame


@pytest.fixture
def sensor_link():
  """``make(winkel)`` liefert eine verbundene Platine, die diese Winkel meldet.

  Die Ports werden am Ende des Tests zuverlässig wieder geschlossen.
  """
  if not HAS_PTY:
    pytest.skip("Virtuelles Terminal nur unter POSIX verfügbar")
  pytest.importorskip("serial")
  opened: list[tuple] = []

  def make(angles):
    master, slave = os.openpty()
    link = sensors.JointSensorLink()
    assert link.connect(os.ttyname(slave)), link.last_error
    opened.append((link, master, slave))
    feed(link, master, angles, first_id=1)
    return link, master

  def feed(link, master, angles, first_id: int) -> None:
    """Frames schreiben und warten, bis die Anbindung sie verarbeitet hat.

    Gewartet wird auf den Frame-Zähler, nicht auf ``has_data``: Nach dem ersten
    Frame steht der schon auf True, und ein zu früher Abbruch würde die neuen
    Winkel gar nicht mehr einlesen.
    """
    before = link.frames
    pitch = kinematics.segment_pitch(angles)
    os.write(
      master,
      build_frame(pitch, first_id) + build_frame(pitch, first_id + 1) + sensors.FRAME_HEADER,
    )
    for _ in range(100):
      link.poll()
      if link.frames > before:
        return
      time.sleep(0.002)
    raise AssertionError("Die Sensoranbindung hat die Testframes nicht gelesen.")

  make.feed = feed
  yield make

  for link, master, slave in opened:
    link.disconnect()
    os.close(master)
    os.close(slave)
