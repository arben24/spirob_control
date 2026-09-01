"""Einstiegspunkt: ``python -m spirob_control``.

Fehler beim Start (fehlendes MuJoCo, kein Fenstersystem) werden hier
abgefangen und als verständliche Meldung ausgegeben, statt als Rückverfolgung
in einem Konsolenfenster, das sich unter Windows sofort wieder schließt.
"""

from __future__ import annotations

import sys


def main() -> int:
  try:
    from .app import main as run
  except ImportError as exc:
    print(f"Eine benötigte Bibliothek fehlt: {exc}", file=sys.stderr)
    print("Bitte zuerst die Abhängigkeiten installieren:", file=sys.stderr)
    print("    pip install -r requirements.txt", file=sys.stderr)
    return 1

  try:
    run()
  except KeyboardInterrupt:
    return 130
  except Exception as exc:  # pragma: no cover
    print(f"Die Oberfläche konnte nicht gestartet werden: {exc}", file=sys.stderr)
    return 1
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
