"""Sensorplatine: Frame-Parser, Winkelberechnung und die serielle Anbindung.

Die Winkelberechnung wird gegen synthetische Daten geprüft, bei denen die
richtige Antwort bekannt ist, und die serielle Anbindung gegen ein virtuelles
Terminalpaar - damit läuft der komplette Weg vom Byte bis zum Gelenkwinkel im
Test, ohne dass Hardware angeschlossen sein muss.
"""

from __future__ import annotations

import numpy as np
import pytest

from spirob_control import kinematics, sensors

ANGLES = np.array([0.2, -0.1, 0.05, 0.3, -0.25, 0.0, 0.15, -0.05, 0.1, 0.2, -0.3, 0.12, -0.08])


def test_winkel_werden_exakt_zurueckgerechnet():
  """Neigungen -> Beschleunigungen -> Winkel muss die Ausgangswinkel treffen."""
  pitch = kinematics.segment_pitch(ANGLES)
  acc = {sid: (0.0, np.cos(p), -np.sin(p)) for sid, p in zip(sensors.SENSOR_IDS, pitch)}
  ordered = sensors.order_and_normalize(acc)
  assert ordered is not None and ordered.shape == (sensors.NUM_SEGMENTS, 3)
  assert np.allclose(sensors.solve_joint_angles(ordered), ANGLES, atol=1e-9)


def test_fehlender_sensor_liefert_keine_winkel():
  """Lieber gar keine Winkel als Winkel mit einem Loch darin."""
  acc = {sid: (0.0, 1.0, 0.0) for sid in sensors.SENSOR_IDS[:-1]}
  assert sensors.order_and_normalize(acc) is None


def test_winkel_werden_auf_die_mechanische_grenze_begrenzt():
  acc = np.zeros((sensors.NUM_SEGMENTS, 3))
  acc[:, 1] = 1.0
  acc[1::2, 1] = 0.0
  acc[1::2, 2] = 1.0  # 90 Grad Sprünge, mechanisch unmöglich
  angles = sensors.solve_joint_angles(acc)
  assert np.all(np.abs(angles) <= sensors.JOINT_LIMIT_RAD + 1e-12)


def test_parser_findet_frames_im_stroem(make_frame):
  build_frame = make_frame
  parser = sensors.BinaryFrameParser()
  pitch = kinematics.segment_pitch(ANGLES)
  # Störbytes davor, zwei Frames dahinter: der Parser gibt einen Frame erst
  # frei, wenn dahinter der nächste Kopf steht (Schutz gegen Fehltreffer).
  parser.add_data(b"INFO,irgendwas\n" + build_frame(pitch, 1) + build_frame(pitch, 2)
                  + sensors.FRAME_HEADER)
  frames = parser.extract_frames()
  assert len(frames) == 2
  assert set(frames[-1]["sensors"]) == set(sensors.SENSOR_IDS)


def test_parser_ueberspringt_kaputte_bytes(make_frame):
  build_frame = make_frame
  parser = sensors.BinaryFrameParser()
  pitch = kinematics.segment_pitch(ANGLES)
  good = build_frame(pitch, 7)
  parser.add_data(good[:20] + good + good + sensors.FRAME_HEADER)  # angebrochener Frame vorn
  frames = parser.extract_frames()
  assert len(frames) >= 1


def test_serielle_anbindung_ueber_virtuelles_terminal(sensor_link):
  """Kompletter Weg: Bytes auf einer seriellen Leitung -> Gelenkwinkel."""
  link, master = sensor_link(ANGLES)
  assert link.connected and link.has_data
  assert np.allclose(link.joint_angles, ANGLES, atol=1e-6)

  signals = link.signals()
  assert signals["joint_pos"].shape == (sensors.NUM_JOINTS,)
  assert signals["segment_pitch"].shape == (2 * sensors.NUM_SEGMENTS,)

  # Der Spiegel-Schalter der Oberfläche wirkt sofort auf den nächsten Frame.
  link.sign = -1.0
  sensor_link.feed(link, master, ANGLES, first_id=3)
  assert np.allclose(link.joint_angles, -ANGLES, atol=1e-6)


def test_ohne_verbindung_passiert_nichts():
  link = sensors.JointSensorLink()
  link.poll()
  assert link.connected is False
  assert link.has_data is False
  assert link.signals()["joint_pos"].tolist() == [0.0] * sensors.NUM_JOINTS
  assert link.connect("/dev/gibtesnicht") is False
  assert link.last_error


def test_verbinden_scheitert_ohne_frames():
  """Ein offener Port ohne Datenstrom gilt nicht als Verbindung.

  Genau dieser Fall trat auf, als die GUI die Platine mit der falschen
  Baudrate ansprach: Der Port ließ sich öffnen, die Oberfläche meldete
  Erfolg - und es kamen nie Winkel an. Jetzt zählt nur, ob Frames ankommen.
  """
  import os

  if not hasattr(os, "openpty"):
    pytest.skip("Virtuelles Terminal nur unter POSIX verfügbar")
  pytest.importorskip("serial")
  master, slave = os.openpty()
  link = sensors.JointSensorLink()
  try:
    assert link.connect(os.ttyname(slave)) is False
    assert link.connected is False
    assert "keine Daten" in (link.last_error or "")
    # Die Meldung nennt jede probierte Baudrate, damit man weiß, was versucht wurde.
    for baud in sensors.BAUD_CANDIDATES:
      assert str(baud) in link.last_error
  finally:
    link.disconnect()
    os.close(master)
    os.close(slave)


def test_status_text_nennt_die_ursache():
  link = sensors.JointSensorLink()
  assert "nicht verbunden" in link.status_text().lower()
