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
