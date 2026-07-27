# Projektarbeit – <Projektname>

> Dieses README ist gleichzeitig der Projekt-Steckbrief **und** die Startseite der
> generierten Website (via GitLab Pages). Bitte die Platzhalter `<...>` ausfüllen
> und diesen Hinweis-Block am Ende löschen.

## Projektinformationen

| Feld            | Wert                     |
| --------------- | ------------------------ |
| Projektname     | `<Projektname>`          |
| Studiengang     | `<Studiengang>`          |
| Betreuer:in     | `<Name Betreuer:in>`     |
| Abgabedatum     | `<TT.MM.JJJJ>`           |

## Team

Bei einer Einzelarbeit reicht eine Zeile, bei einer Gruppenarbeit bitte alle
Mitglieder eintragen.

| Name                  |
| --------------------- |
| `<Vorname Nachname>`  |
| `<Vorname Nachname>`  |

## Kurzbeschreibung (Abstract)

<Kurze Zusammenfassung des Projekts in 3–5 Sätzen: Was wurde gemacht, warum und
mit welchem Ergebnis?>

> **Beispiel:** *„In diesem Projekt wurde ein Webdienst zur automatisierten
> Erkennung von Objekten in Kamerabildern mittels eines neuronalen Netzes
> entwickelt. Ziel war es, die manuelle Sichtprüfung in der Qualitätskontrolle
> teilweise zu automatisieren. Das entwickelte System erreicht auf dem eigenen
> Testdatensatz eine Erkennungsgenauigkeit von 94 % und wurde als
> Prototyp erfolgreich in eine bestehende Anwendung integriert."*

## Ziele

- <Ziel 1>
- <Ziel 2>
- <Ziel 3>

> **Beispiel:**
> - Implementierung eines Prototyps zur Objekterkennung auf Basis eines
>   vortrainierten neuronalen Netzes
> - Aufbau und Auswertung eines eigenen Testdatensatzes
> - Integration des Modells in eine bestehende Anwendung per REST-Schnittstelle

## Ergebnisse

- <Ergebnis 1>
- <Ergebnis 2>
- <Ergebnis 3>

> **Beispiel:**
> - Prototyp erfolgreich implementiert, getestet und dokumentiert
> - Erkennungsgenauigkeit von 94 % auf dem Testdatensatz erreicht
> - REST-Schnittstelle produktiv integriert und im Rahmen der Präsentation
>   demonstriert

## Verwendete Technologien

- <Technologie / Sprache / Framework 1>
- <Technologie / Sprache / Framework 2>

> **Beispiel:** Python, PyTorch, FastAPI, Docker, GitLab CI/CD, Typst

---

## Wie funktioniert dieses Repository?

Dieses Repository ist eine Vorlage, die Code, Dokumentation und die schriftlichen
Abgaben (Arbeit + Präsentation) bündelt. Die PDFs und die Website werden
**automatisch von der GitLab-CI/CD-Pipeline** gebaut – du musst nichts manuell
kompilieren.

| Ordner        | Zweck                                                                      |
| ------------- | -------------------------------------------------------------------------- |
| `src/`        | Dein Quellcode. Coding-Regeln stehen in `src/README.md`.                   |
| `docs/`       | Zusätzliche Markdown-Dokumentation für die Website. Eine kurze Anleitung dazu liegt in `docs/anleitung.md` (auf der Website unter „Dokumentation → Anleitung"). |
| `expose/`     | Kurzes Exposé (ca. 2-3 Seiten) vor Beginn der eigentlichen Arbeit: Zielstellung, Forschungsfragen, Zeitplan, Literatur. |
| `report/`     | Die schriftliche Arbeit in Typst: `main.typ` bindet Layout (`template.typ`), die 7 Kapitel (`Sections/`, von Motivation bis Zusammenfassung/Ausblick) und Literatur (`references.bib`) ein. |
| `slides/`     | Die Präsentation, ebenfalls in Typst (`main.typ` + `template.typ`) – funktioniert genauso wie `report/`, nur ohne Kapitel-Struktur. Alles zu Typst (was es ist, lokale Nutzung, Beispiele) steht in `docs/typst.md` (auf der Website unter „Dokumentation → Typst"). |
| `extra/`      | Zusätzliches Material, das in keinen anderen Ordner passt (z. B. Datensätze, Messwerte, Exporte, Rohbilder). |

### Was passiert automatisch?

Bei jedem Push auf den Branch `main` läuft die Pipeline (`.gitlab-ci.yml`) und:

1. **Report** – kompiliert `report/main.typ` zu einer PDF (als CI-Artefakt).
2. **Slides** – kompiliert `slides/main.typ` zu einer PDF (als CI-Artefakt).
3. **Exposé** – kompiliert `expose/main.typ` zu einer PDF (als CI-Artefakt).
4. **Website** – baut aus diesem README und `docs/` eine statische Website
   (inkl. Downloads-Seite mit allen drei PDFs) und veröffentlicht sie über
   **GitLab Pages**.

Die PDFs werden dabei **nicht** ins Repository zurückcommittet – sie entstehen
nur temporär während des CI-Laufs und werden anschließend als CI-Artefakt und
eingebettet auf der Website unter „Downloads" (siehe `docs/downloads.md`)
bereitgestellt.

### Was musst du tun?

1. Metadaten und Abschnitte oben in diesem README ausfüllen.
2. Deinen Code in `src/` ablegen und die Coding-Regeln in `src/README.md` beachten.
3. Zu Beginn das Exposé in `expose/main.typ` ausfüllen (Zielstellung,
   Forschungsfragen, Zeitplan, Literatur).
4. Die schriftliche Arbeit in `report/` (die 7 Kapitel in `report/Sections/`
   nach und nach ausfüllen – die Hinweis-Kästen je Kapitel zeigen, was
   erwartet wird) und die Präsentation in `slides/main.typ` schreiben.
   Hinweise zu Typst gibt es in `docs/typst.md`.
5. Optional: zusätzliche Doku-Seiten in `docs/` anlegen und in `mkdocs.yml`
   verlinken.
6. Committen und pushen – den Rest erledigt die Pipeline.
