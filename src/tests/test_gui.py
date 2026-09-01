"""Klickt die Oberfläche einmal komplett durch - ohne Benutzer, ohne Hardware.

Ein Rauchtest, kein Test der Darstellung: Er ruft jedes Bedienelement einmal
auf und prüft, dass dabei nichts fliegt, der Takt läuft und die beiden
Schutzmechanismen greifen (kein Senden ohne Verbindung, Rückfall in den
Handbetrieb, wenn der Policy die Sensordaten fehlen). Genau das sind die
Stellen, die man beim Ausprobieren von Hand am leichtesten übersieht.

Ohne Fenstersystem (Kopfloser Server, CI-Runner) wird der Test übersprungen.
"""

from __future__ import annotations

import time
import tkinter

import pytest

pytest.importorskip("tkinter")


@pytest.fixture
def app():
  try:
    from spirob_control.app import SpirobApp

    window = SpirobApp()
  except tkinter.TclError as exc:  # kein Display verfügbar
    pytest.skip(f"Kein Fenstersystem verfügbar: {exc}")
  yield window
  window._on_close()


def pump(window, seconds: float) -> None:
  """Ereignisschleife für eine Weile laufen lassen (der Takt hängt an ``after``)."""
  end = time.perf_counter() + seconds
  while time.perf_counter() < end:
    window.update()
    time.sleep(0.004)


def test_bedienelemente_durchklicken(app, monkeypatch):
  from tkinter import messagebox

  # Meldungsfenster würden den Test blockieren.
  monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: None)
  monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: None)

  app._refresh_ports()
  app.var_f0.set(50.0)
  app._on_force_slider(0)
  app.var_f1.set(30.0)
  app._on_force_slider(1)
  pump(app, 0.2)
  assert app.controller.state.manual_forces == [50.0, 30.0]

  app._release_forces()
  assert app.controller.state.manual_forces == [0.0, 0.0]

  app.var_limit.set(42.0)
  app._on_limit_change()
  assert app.controller.state.force_limit_n == pytest.approx(42.0)

  app._toggle_emergency_stop()
  assert app.controller.state.emergency_stop is True
  app._toggle_emergency_stop()
  assert app.controller.state.emergency_stop is False

  app._reset_simulation()
  for mode in ("2d", "3d"):
    app.var_view.set(mode)
    app._on_view_change()
    pump(app, 0.15)
  app._reset_camera()

  for label in list(app._policies):
    app.var_policy.set(label)
    app._load_policy()
    assert app.controller.policy is not None

  app.notebook.select(1)
  for angle in (-1.6, 0.0, 1.6):
    app.var_angle.set(angle)
    app._on_target_change()
  app.var_snap.set(False)
  app.var_radius.set(0.42)
  app._on_target_change()
  app.var_snap.set(True)
  app._on_target_change()
  pump(app, 0.3)


def test_kein_senden_ohne_verbindung(app, monkeypatch):
  from tkinter import messagebox

  monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: None)
  app.var_send_hw.set(True)
  app._on_send_toggle()
  assert app.var_send_hw.get() is False
  assert app.controller.state.send_to_hardware is False


def test_policy_ohne_sensordaten_faellt_zurueck(app):
  """Hardware-Rückmeldung ohne Verbindung: zurück in den Handbetrieb, 0 N."""
  if not app._policies:
    pytest.skip("Keine Policy vorhanden")
  app.notebook.select(1)
  app.var_source.set("hardware")
  app._on_source_change()
  pump(app, 0.5)
  assert app.controller.state.mode == "manual"
  assert app.controller.telemetry.forces_n.tolist() == [0.0, 0.0]
  assert app.notebook.index("current") == 0


def test_3d_ansicht_fuellt_die_flaeche(app):
  """Die 3D-Ansicht muss beim Vergrößern des Fensters mitwachsen.

  Sie hing früher an einer festen Obergrenze und stand dann klein in der Mitte,
  sobald man das Fenster maximiert hat - im Vollbild der auffälligste Fehler,
  den die Oberfläche hatte.
  """
  app.var_view.set("3d")
  app._on_view_change()
  pump(app, 0.8)
  if app.view._render_failed or app.view._photo is None:
    pytest.skip("Auf diesem Rechner ist kein 3D-Rendering verfügbar")

  for geometry in ("1500x950+20+20", "1100x700+20+20"):
    app.geometry(geometry)
    pump(app, 1.2)
    canvas = (app.view.canvas.winfo_width(), app.view.canvas.winfo_height())
    assert (app.view._photo.width(), app.view._photo.height()) == canvas, (
      f"Bild {app.view._photo.width()}x{app.view._photo.height()} passt nicht zur "
      f"Zeichenfläche {canvas[0]}x{canvas[1]}"
    )


def test_regeltakt_bleibt_trotz_grossem_fenster(app):
  """Ein großes Fenster darf die Bildrate drücken, aber nicht den Regeltakt."""
  app.var_view.set("3d")
  app._on_view_change()
  app.geometry("1500x950+20+20")
  pump(app, 1.5)
  before = app.controller.telemetry.ticks
  start = time.perf_counter()
  pump(app, 2.0)
  rate = (app.controller.telemetry.ticks - before) / (time.perf_counter() - start)
  assert rate > 40.0, f"Regeltakt auf {rate:.1f} Hz eingebrochen"


def test_sensorplatine_ueber_die_oberflaeche(app, sensor_link, monkeypatch):
  """Der Haken „Sensordaten verwenden“ verbindet, zeigt an und trennt wieder."""
  from tkinter import messagebox

  monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: None)
  monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: None)

  link, master = sensor_link([0.1] * 13)
  port = link.port
  link.disconnect()  # die Oberfläche soll den Port selbst öffnen

  app.var_sensor_port.set(port)
  app.var_use_sensors.set(True)
  app._on_use_sensors_toggle()
  assert app.controller.state.use_sensors is True
  assert app.controller.sensors.connected is True

  # Frames einspeisen, bis die Anbindung sie verarbeitet hat.
  sensor_link.feed(app.controller.sensors, master, [0.1] * 13, first_id=10)
  pump(app, 0.3)
  assert app.controller.sensors_active is True
  assert app.controller.telemetry.measured_tcp_xz is not None

  app.var_use_sensors.set(False)
  app._on_use_sensors_toggle()
  pump(app, 0.2)
  assert app.controller.sensors.connected is False
  assert app.controller.telemetry.measured_chain_xz is None


def test_haken_geht_bei_falschem_port_wieder_heraus(app, monkeypatch):
  from tkinter import messagebox

  monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: None)
  monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: None)

  app.var_sensor_port.set("/dev/gibtesnicht")
  app.var_use_sensors.set(True)
  app._on_use_sensors_toggle()
  assert app.var_use_sensors.get() is False
  assert app.controller.state.use_sensors is False
