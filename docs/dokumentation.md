# Übersicht

Diese Dokumentation beschreibt **SpiRob Control** – die grafische
Bedienoberfläche für den seilzuggetriebenen Tentakel SpiRob.

## Worum geht es?

Der SpiRob ist eine Kette aus 14 Segmenten mit 13 Drehgelenken, die sich in
einer Ebene biegt. Zwei Seile laufen außen an der Kette entlang; zieht der
Motor an einem davon, krümmt sich der Arm zu dieser Seite. Mehr Stellgrößen
gibt es nicht: **zwei Zahlen bestimmen die gesamte Form des Roboters.**

Genau darauf ist die Oberfläche zugeschnitten. Sie kennt zwei Betriebsarten:

| Betriebsart     | Was man vorgibt                          | Was die Software tut                             |
| --------------- | ---------------------------------------- | ------------------------------------------------ |
| **Handbetrieb** | zwei Seilkräfte (0 – 150 N)              | reicht sie direkt an Simulation und Hardware durch |
| **Policy**      | eine Zielposition der Spitze             | eine trainierte Regelung bestimmt daraus 50-mal je Sekunde die Seilkräfte |

In beiden Fällen läuft der digitale Zwilling (MuJoCo) mit und zeigt, was der
Roboter gerade tut – mit oder ohne angeschlossene Hardware.

## Die Seiten dieser Dokumentation

| Seite                              | Inhalt                                                                 |
| ---------------------------------- | ---------------------------------------------------------------------- |
| [Installation](installation.md)    | Voraussetzungen, Einrichtung unter Windows und Linux, Tests             |
| [Bedienung](bedienung.md)          | Jedes Bedienelement der Oberfläche, Tastenkürzel, typische Abläufe      |
| [Architektur](architektur.md)      | Aufbau des Programms, Regeltakt, warum es ohne Threads auskommt         |
| [Hardware](hardware.md)            | Serielles Protokoll, Anschluss, Sicherheit, Grenzen des Hardwarebetriebs |
| [Policies](policies.md)            | Woher die Netze kommen, wie sie exportiert werden, was sie leisten      |

## Aufbau des Quellcodes

Der gesamte Code liegt in `src/`:

```
src/
├── spirob_control/          Das Programm selbst
│   ├── app.py               Fenster, Bedienelemente, 50-Hz-Takt
│   ├── controller.py        Regelkreis (Modus, Kräfte, Sicherheitsgrenze)
│   ├── simulation.py        MuJoCo-Modell, Regelschritt, Sensorsignale
│   ├── policy.py            Vorwärtspass der trainierten Netze (NumPy)
│   ├── hardware.py          serielle Verbindung zum ESP32
│   ├── view.py              3D-Ansicht und Schema-Ansicht
│   ├── workspace.py         Geometrie des erreichbaren Arbeitsraums
│   ├── theme.py             Farben und Stile
│   ├── settings.py          zuletzt benutzte Einstellungen
│   └── assets/              MuJoCo-Modell und exportierte Policies
├── tools/export_policy.py   Checkpoint -> NumPy-Paket (nur im Trainings-Repo)
├── tests/                   pytest-Suite
├── run_gui.bat / run_gui.sh Startskripte
└── requirements.txt         Abhängigkeiten
```

!!! tip "Kurz und bündig"
    Wer nur den Roboter bewegen will, braucht nur zwei Seiten:
    [Installation](installation.md) und [Bedienung](bedienung.md).
