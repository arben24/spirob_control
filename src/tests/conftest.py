"""Gemeinsame Testhilfen.

Vor allem eines: eine echte Sensoranbindung, gespeist über ein virtuelles
Terminalpaar. Damit läuft in den Tests derselbe Weg wie im Betrieb - Bytes auf
einer seriellen Leitung, Frame-Parser, Winkelberechnung, Glättung -, ohne dass
Hardware angeschlossen sein muss.
"""

from __future__ import annotations

import os
import struct
import threading
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

  Ein Hintergrund-Thread schreibt fortlaufend Frames auf das virtuelle
  Terminal - so wie es die echte Platine tut, die von sich aus sendet. Das ist
  nicht nur bequemer als einmaliges Schreiben: ``connect()`` gilt erst als
  erfolgreich, wenn tatsächlich Frames ankommen, und genau dieses Verhalten
  soll der Test mitprüfen.
  """
  if not HAS_PTY:
    pytest.skip("Virtuelles Terminal nur unter POSIX verfügbar")
  pytest.importorskip("serial")
  opened: list[tuple] = []

  def make(angles):
    master, slave = os.openpty()
    state = {"angles": np.asarray(angles, dtype=float), "id": 1}
    stop = threading.Event()

    def writer() -> None:
      while not stop.is_set():
        pitch = kinematics.segment_pitch(state["angles"])
        try:
          os.write(
            master,
            build_frame(pitch, state["id"]) + build_frame(pitch, state["id"] + 1)
            + sensors.FRAME_HEADER,
          )
        except OSError:
          return
        state["id"] += 2
        time.sleep(0.02)

    thread = threading.Thread(target=writer, daemon=True)
    thread.start()

    link = sensors.JointSensorLink()
    ok = link.connect(os.ttyname(slave))
    opened.append((link, master, slave, stop, thread))
    assert ok, link.last_error
    return link, master

  def feed(link, master, angles, first_id: int = 0) -> None:
    """Andere Winkel senden und warten, bis die Anbindung sie verarbeitet hat.

    Gewartet wird auf den Frame-Zähler, nicht auf ``has_data``: Der steht nach
    dem Verbinden schon auf True, und ein zu früher Abbruch würde die neuen
    Winkel gar nicht mehr einlesen.
    """
    for link_, master_, _slave, _stop, _thread in opened:
      if link_ is link:
        break
    before = link.frames
    for _ in range(200):
      link.poll()
      if link.frames > before + 2:
        return
      time.sleep(0.002)
    raise AssertionError("Die Sensoranbindung hat die Testframes nicht gelesen.")

  make.feed = feed
  yield make

  for link, master, slave, stop, thread in opened:
    stop.set()
    thread.join(timeout=1.0)
    link.disconnect()
    os.close(master)
    os.close(slave)
