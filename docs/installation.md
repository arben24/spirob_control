# Installation

## Voraussetzungen

* **Python 3.10 oder neuer.** Unter Windows von
  [python.org](https://www.python.org/downloads/) installieren und dabei
  **„Add python.exe to PATH“** ankreuzen. Tkinter, das die Oberfläche
  zeichnet, ist Teil der offiziellen Installation.
* Eine Grafikkarte mit OpenGL für die 3D-Ansicht. Fehlt sie oder streikt der
  Treiber, schaltet die Oberfläche selbsttätig auf die Schema-Ansicht um –
  bedienbar bleibt sie in jedem Fall.
* Für den Hardwarebetrieb: der SpiRob mit ESP32-Motorcontroller und ein
  USB-Kabel. Ohne Hardware läuft alles andere trotzdem.

Es wird **kein** PyTorch, **kein** mjlab und **keine** CUDA-Installation
gebraucht – die trainierten Policies liegen als NumPy-Gewichte im Repository.

## Schnellweg (empfohlen)

**Windows**

```bat
git clone <URL dieses Repositories>
cd spirob_control\src
run_gui.bat
```

**Linux / macOS**

```bash
git clone <URL dieses Repositories>
cd spirob_control/src
./run_gui.sh
```

Das Startskript legt beim ersten Aufruf die virtuelle Umgebung `src/.venv` an,
installiert die Abhängigkeiten und startet die GUI. Bei jedem weiteren Aufruf
startet es direkt – unter Windows genügt dann ein Doppelklick auf
`run_gui.bat`.

## Von Hand

```bash
cd src
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt   # Windows
# .venv/bin/python -m pip install -r requirements.txt     # Linux/macOS
.venv\Scripts\python -m spirob_control
```

Alternativ mit `uv` (siehe `src/README.md`):

```bash
cd src
uv sync
uv run python -m spirob_control
```

## Tests ausführen

```bash
cd src
.venv\Scripts\python -m pip install pytest
.venv\Scripts\python -m pytest
```

Die Suite läuft in unter einer Sekunde und braucht weder Hardware noch
Bildschirm. Sie prüft unter anderem, ob das Beobachtungslayout jeder Policy zu
ihrem Netz passt und ob ein vollständiger Rollout in der Simulation die Spitze
tatsächlich ans Ziel bringt.

## Bekannte Stolpersteine

| Symptom | Ursache und Abhilfe |
| ------- | ------------------- |
| „Python 3 wurde nicht gefunden“ | Python fehlt oder ist nicht im `PATH`. Neu installieren und „Add python.exe to PATH“ ankreuzen. |
| Die Portliste bleibt leer | Kein USB-Seriell-Treiber installiert (CP210x, CH340) oder Kabel ohne Datenadern. Nach dem Anstecken „Suchen“ drücken. |
| Beim Verbinden: „Zugriff verweigert“ / „Port besetzt“ | Ein anderes Programm hält den Port – typischerweise der serielle Monitor der Arduino-IDE oder von PlatformIO. Dort trennen. |
| Unter Linux: „Permission denied“ auf `/dev/ttyUSB0` | Benutzer zur Gruppe `dialout` hinzufügen: `sudo usermod -aG dialout $USER`, danach neu anmelden. |
| Die 3D-Ansicht bleibt leer, in der Statuszeile steht eine Meldung | Kein OpenGL verfügbar (etwa in einer Fernwartungssitzung). Die Oberfläche wechselt automatisch in die Schema-Ansicht. |
| Die Oberfläche startet, aber der Regeltakt liegt deutlich unter 50 Hz | Sehr langsamer Rechner oder sehr großes Fenster. Auf „Schema“ umschalten – das Rendern entfällt dann. |
