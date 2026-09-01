#import "template.typ": expose, hinweis

#show: expose.with(
  title: "SpiRob Control - eine grafische Bedienoberfläche für einen seilzuggetriebenen Tentakelgreifer",
  author: "Nico Beyer",
  supervisor: "<Name Betreuer:in eintragen>",
  date: none,
)

= Zielstellung

Der SpiRob ist ein seilzuggetriebener Tentakelgreifer nach dem Vorbild
logarithmisch gewundener Spiralen @wang_2025: eine Kette aus 14 Segmenten, die
von nur zwei Seilen gebogen wird. Für ihn existieren bereits ein
Simulationsmodell, eine Firmware für die Kraftregelung und mehrere im
Reinforcement Learning trainierte Regelungen. Bedienen ließ er sich bisher
allerdings nur über die Schieberegler des MuJoCo-Viewers oder über
Kommandozeilenwerkzeuge, die die vollständige Trainingsumgebung samt PyTorch
und GPU voraussetzen.

Ziel der Arbeit ist eine eigenständige, bewusst einfache grafische
Bedienoberfläche, die den Roboter auf zwei Wegen fahrbar macht: von Hand über
zwei Schieberegler für die Seilkräfte und über eine trainierte Policy, der nur
noch die Zielposition der Spitze vorgegeben wird. Die Oberfläche soll die
Simulation und die reale Hardware in einem Programm zusammenführen, ohne
Trainingsbibliotheken auskommen und auf einem beliebigen Windows-Rechner nach
dem Klonen des Repositories startbar sein.

= Forschungsfragen

- Lässt sich eine im Reinforcement Learning trainierte Regelung so aus ihrer
  Trainingsumgebung herauslösen, dass sie ohne PyTorch, ohne die
  Trainingsbibliotheken und ohne GPU dasselbe Verhalten zeigt - und woran lässt
  sich das nachweisen?
- Welche Bedienelemente braucht ein Roboter mit zwei Stellgrößen wirklich,
  damit sowohl direkte Kraftvorgabe als auch zielbasierte Ansteuerung ohne
  Vorwissen bedienbar sind?
- Wie viel Sensorik ist nötig, damit eine solche Policy ihr Ziel hält, und
  welche der trainierten Varianten ist mit der vorhandenen Hardware
  überhaupt lauffähig?
- Wie muss ein Regelkreis aufgebaut sein, der Simulation, Policy und
  serielle Hardwareanbindung in einem einzigen Prozess bei 50 Hz bedient und
  dabei gegen abgezogene Kabel, fehlende Treiber und fehlende Grafikbeschleunigung
  unempfindlich bleibt?

= Zeitplan

#table(
  columns: (auto, 1fr),
  inset: 8pt,
  [*Zeitraum*], [*Phase / Meilenstein*],
  [Woche 1], [Einarbeitung: bestehendes Simulationsmodell, Firmware-Protokoll und trainierte Policies sichten],
  [Woche 2], [Konzept: Betriebsarten, Bedienelemente, Architektur des Regelkreises festlegen],
  [Woche 3], [Umsetzung Teil 1: Export der Policies, Nachbau des Beobachtungsvektors, Regelkreis und Tests],
  [Woche 4], [Umsetzung Teil 2: Oberfläche, 3D- und Schemaansicht, serielle Anbindung, Windows-Start],
  [Woche 5], [Evaluation: Zielgenauigkeit je Sensor-Level, Zeitverhalten des Regelkreises, Inbetriebnahme an der Hardware],
  [Woche 6], [Dokumentation, schriftliche Arbeit, Präsentation, Abgabe],
)

= Literatur

#bibliography("references.bib", style: "ieee", full: true, title: none)
