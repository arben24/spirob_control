#!/usr/bin/env bash
# ---------------------------------------------------------------------------
#  SpiRob Control unter Linux/macOS starten.
#
#  Legt beim ersten Aufruf .venv an, installiert die Abhängigkeiten und
#  startet danach die GUI.
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

PYEXE=".venv/bin/python"

if [ ! -x "$PYEXE" ]; then
  echo "[1/3] Lege virtuelle Umgebung an ..."
  python3 -m venv .venv
fi

if [ ! -f ".venv/.installed" ]; then
  echo "[2/3] Installiere Abhängigkeiten ..."
  "$PYEXE" -m pip install --upgrade pip
  "$PYEXE" -m pip install -r requirements.txt
  touch .venv/.installed
fi

echo "[3/3] Starte SpiRob Control ..."
exec "$PYEXE" -m spirob_control
