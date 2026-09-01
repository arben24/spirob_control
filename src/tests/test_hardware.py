"""Die serielle Anbindung darf ohne Gerät nichts tun - und nichts werfen.

Ein abgezogenes Kabel, ein belegter Port, eine fehlende pyserial-Installation:
alles Betriebszustände, in denen die GUI weiterlaufen muss.
"""

from __future__ import annotations

from spirob_control.hardware import HardwareLink, available_ports


def test_ohne_verbindung_ist_alles_ein_no_op():
  link = HardwareLink()
  assert link.connected is False
  link.poll()
  link.send_forces([10.0, 20.0])
  link.start()
  link.stop()
  link.disconnect()
  assert link.signals()["tendon_len"].tolist() == [0.0, 0.0]


def test_unbekannter_port_meldet_fehler_statt_zu_werfen():
  link = HardwareLink()
  assert link.connect("/dev/does-not-exist") is False
  assert link.last_error
  assert link.connected is False


def test_portliste_ist_abfragbar():
  # Darf leer sein, muss aber eine Liste von Paaren liefern.
  for entry in available_ports():
    assert len(entry) == 2
