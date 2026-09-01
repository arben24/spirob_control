# Quellcode & Coding-Regeln

In diesem Ordner liegt der gesamte Quellcode der Projektarbeit. Diese Datei
richtet sich an Entwickler:innen und wird **bewusst nicht** in die
MkDocs-Website aufgenommen; die Anwender-Dokumentation steht in `../docs/`.

## Aufbau

```
src/
├── spirob_control/          Das Programm (siehe ../docs/architektur.md)
│   ├── app.py               Fenster, Bedienelemente, 50-Hz-Takt
│   ├── controller.py        Regelkreis - kennt keine Widgets
│   ├── simulation.py        MuJoCo-Modell und Sensorsignale
│   ├── policy.py            Vorwärtspass der trainierten Netze (NumPy)
│   ├── hardware.py          serielle Verbindung zum Motor-Controller
│   ├── sensors.py           Sensorplatine: Frames -> 13 Gelenkwinkel
│   ├── kinematics.py        Vorwärtskinematik (Armform, Spitze)
│   ├── view.py              3D- und Schema-Ansicht
│   ├── workspace.py         Arbeitsraum-Geometrie (nur Standardbibliothek)
│   ├── theme.py             Farben, Schriften, ttk-Stile
│   ├── settings.py          zuletzt benutzte Einstellungen
│   └── assets/              spirob.xml und die exportierten Policies
├── tools/export_policy.py   Checkpoint -> .npz (läuft im Trainings-Repo)
├── tests/                   pytest-Suite, ohne Hardware und ohne Bildschirm
├── run_gui.bat, run_gui.sh  Startskripte
├── requirements.txt         Abhängigkeiten für pip
└── pyproject.toml           Projekt- und Testkonfiguration
```

## Starten und testen

```bash
# starten
./run_gui.sh              # bzw. run_gui.bat unter Windows
# oder
python -m spirob_control

# testen
python -m pytest
```

## Allgemeine Regeln

- Sinnvolle, sprechende Namen für Variablen, Funktionen und Dateien verwenden.
- Code in kleine, testbare Einheiten aufteilen.
- Keine Zugangsdaten, Tokens oder Passwörter einchecken (siehe `.gitignore`).
- Build-Artefakte und Abhängigkeiten gehören **nicht** ins Repository. Die
  exportierten Policies (`assets/policies/*.npz`, je ~250 KiB) sind eine
  bewusste Ausnahme: ohne sie ist das Programm nicht lauffähig, und sie sind
  das Bindeglied zum Trainingsprojekt.

## Konventionen in diesem Projekt

- **Einrückung: zwei Leerzeichen**, wie im Trainings-Repo `RL_explor`, aus dem
  Teile dieses Codes stammen.
- **Kommentare und Dokumentation auf Deutsch**, Bezeichner auf Englisch.
  Kommentare erklären, *warum* etwas so ist – das *was* steht im Code.
- **Kraftkonvention:** nach außen immer der Betrag der Zugkraft in Newton
  (0 … 150). Nur die Simulation rechnet mit negativen (ziehenden) Stellgrößen,
  und die Umrechnung steht ausschließlich in `Simulation.apply_forces()`.
- **Der Regelkreis kennt keine Oberfläche.** Alles Fachliche gehört in
  `controller.py` oder tiefer, damit es ohne Fenster testbar bleibt.
- **Nichts blockiert im Takt.** Serielles Lesen holt nur, was schon im Puffer
  liegt; kein `sleep`, kein Warten auf Antwort. Das gilt für beide Geräte.
- **Eine Datenquelle meldet, was sie liefern kann.** Jede Quelle hat
  `provides`, `connect`, `poll`, `signals`, `disconnect`; ob eine Policy damit
  laufen kann, entscheidet allein `Controller.policy_ready()`.
- **Fehler dürfen den Takt nicht abbrechen.** Ein abgezogenes USB-Kabel ist ein
  Betriebszustand: Meldung in die Statuszeile, Simulation läuft weiter.
- **Windows zuerst mitdenken:** keine POSIX-Pfade, kein `select()` auf `stdin`,
  Portauswahl über `serial.tools.list_ports`, Dateien mit `pathlib`.

## Policies aktualisieren

Die `.npz`-Dateien in `spirob_control/assets/policies/` werden mit
`tools/export_policy.py` **im Trainings-Repo** erzeugt – dort liegen PyTorch
und die Checkpoints. Details in `../docs/policies.md`.

## Python-Werkzeuge

Für Python-Code wird als Paket- und Projektmanager **`uv`** empfohlen; `pip`
mit `requirements.txt` funktioniert genauso und ist der Weg, den die
Startskripte gehen.

### Was ist uv?

`uv` ist ein sehr schneller, in Rust geschriebener Paket- und Projektmanager
für Python. Er ersetzt `pip`, `virtualenv`, `pip-tools` und `pyenv` durch ein
einziges Werkzeug und verwaltet virtuelle Umgebungen, Abhängigkeiten sowie
Python-Versionen. Abhängigkeiten werden reproduzierbar über `pyproject.toml`
und `uv.lock` festgehalten.

### Installation

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Alternativ über pipx: `pipx install uv`.

### Nutzung

```bash
uv sync                          # Umgebung aus pyproject.toml aufbauen
uv add <paket>                   # Abhängigkeit hinzufügen
uv run python -m spirob_control  # Programm starten
uv run pytest                    # Tests ausführen
```

`pyproject.toml` (und, falls erzeugt, `uv.lock`) **werden eingecheckt**, damit
die Umgebung reproduzierbar ist. Der Ordner `.venv/` ist über die `.gitignore`
ausgeschlossen.

## Weitere Sprachen

Die Firmware des Motorcontrollers (C++/PlatformIO) gehört nicht zu diesem
Repository; sie liegt im Trainingsprojekt unter `spirob/pio_project/`. Kommt
hier später Code in einer anderen Sprache dazu, gehören dessen Regeln
(Formatierung, Build-Werkzeug, Linter) an diese Stelle.
