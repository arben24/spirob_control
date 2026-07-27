# Quellcode & Coding-Regeln

In diesem Ordner liegt der gesamte Quellcode der Projektarbeit. Diese Datei wird
**bewusst nicht** in die MkDocs-Website aufgenommen – sie richtet sich an
Entwickler:innen, nicht an die Website-Besucher.

## Allgemeine Regeln

- Sinnvolle, sprechende Namen für Variablen, Funktionen und Dateien verwenden.
- Code in kleine, testbare Einheiten aufteilen.
- Keine Zugangsdaten, Tokens oder Passwörter einchecken (siehe `.gitignore`).
- Build-Artefakte und Abhängigkeiten gehören **nicht** ins Repository.

## Python

Für Python-Code wird als Paket- und Projektmanager **`uv`** genutzt.

### Was ist uv?

`uv` ist ein extrem schneller, in Rust geschriebener Paket- und Projektmanager
für Python. Er ersetzt `pip`, `virtualenv`, `pip-tools` und `pyenv` durch ein
einziges Werkzeug und verwaltet virtuelle Umgebungen, Abhängigkeiten sowie sogar
Python-Versionen. Abhängigkeiten werden reproduzierbar über eine
`pyproject.toml` und eine `uv.lock`-Datei festgehalten.

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
# Neues Projekt initialisieren (erzeugt pyproject.toml)
uv init

# Abhängigkeit hinzufügen (aktualisiert pyproject.toml + uv.lock)
uv add requests

# Entwicklungs-Abhängigkeit hinzufügen
uv add --dev pytest

# Umgebung aus der Lock-Datei synchronisieren
uv sync

# Ein Skript in der Projektumgebung ausführen
uv run python main.py

# Tests ausführen
uv run pytest
```

Die Dateien `pyproject.toml` und `uv.lock` **werden eingecheckt**, damit die
Umgebung reproduzierbar ist. Der virtuelle-Umgebungsordner `.venv/` wird über die
`.gitignore` ausgeschlossen.

## Weitere Sprachen

Ergänze hier bei Bedarf Regeln für andere verwendete Sprachen (z. B. C++, Rust,
JavaScript) – etwa Formatierung, Build-Tool und Linter.
