#import "@preview/touying:0.7.4": *
#import themes.simple: *
#import "template.typ": praesentation, htwk-title-slide, footer-text
#import "template.typ": htwk-blue, htwk-cyan, htwk-gray, htwk-lightgray

#footer-text.update("SpiRob Control | Nico Beyer")

#show: praesentation

#htwk-title-slide(
  title: "SpiRob Control",
  subtitle: "Eine grafische Bedienoberfläche für einen seilzuggetriebenen Tentakelgreifer",
  author: "Nico Beyer",
  date: [#datetime.today().display("[day].[month].[year]")],
  institution: "<Studiengang> | HTWK Leipzig",
)

== Agenda
#outline(title: none, indent: 1.5em, depth: 1)

= Ausgangslage

== Der SpiRob
#grid(
  columns: (1fr, 1fr),
  gutter: 1.5em,
  [
    - Tentakelgreifer nach dem Vorbild einer logarithmischen Spirale
    - 14 Segmente, 13 Gelenke - alle in *einer* Ebene
    - Angetrieben von genau *zwei Seilen*
    - Die Firmware regelt die *Zugkraft*, 0 - 150 N je Seil

    === Der Kern des Problems
    Zwei Zahlen bestimmen die Form eines Arms mit dreizehn Gelenken.
  ],
  [
    #align(center + horizon)[
      #rect(stroke: 0.5pt + htwk-lightgray, inset: 6pt, radius: 4pt)[
        #image("Images/gui-schema.png", height: 11em)
        #v(0.2em)
        #text(size: 7pt, fill: htwk-gray)[Die Oberfläche in der Schema-Ansicht, mit erreichbarem Arbeitsraum]
      ]
    ]
  ]
)

== Was es schon gab - und was fehlte
#grid(
  columns: (1fr, 1fr),
  gutter: 1.5em,
  [
    === Vorhanden
    - Abgestimmtes MuJoCo-Modell
    - Firmware mit Kraftregelung (ESP32)
    - Vier trainierte Policies (PPO)
  ],
  [
    === Bedienbar nur über
    - Schieberegler des MuJoCo-Viewers
    - Kommandozeile *mit* PyTorch, mjlab, CUDA
    - Auf den Controller geflashte Netze
  ]
)

#v(0.5em)
#align(center)[
  #text(weight: "bold", fill: htwk-cyan)[
    Ziel: eine Oberfläche, die beides bedienbar macht - auf jedem Windows-Rechner.
  ]
]

= Umsetzung

== Zwei Betriebsarten, jeweils zwei Regler
#grid(
  columns: (1fr, 1fr),
  gutter: 1.5em,
  [
    === Handbetrieb
    - Ein Regler je Seil, 0 - 150 N
    - Wirkt sofort auf Simulation und (freigegeben) Hardware

    === Policy
    - Regler für *Winkel* und *Abstand* der Spitze
    - Die trainierte Regelung stellt die Kräfte, 50-mal je Sekunde
  ],
  [
    #align(center + horizon)[
      #rect(stroke: 0.5pt + htwk-lightgray, inset: 6pt, radius: 4pt)[
        #image("Images/gui-policy.png", height: 11em)
        #v(0.2em)
        #text(size: 7pt, fill: htwk-gray)[Policy-Betrieb mit 3D-Ansicht und Telemetrie]
      ]
    ]
  ]
)

== Zwei Quellen, ein Beobachtungsvektor
#grid(
  columns: (1fr, 1fr),
  gutter: 1.5em,
  [
    - *Motor-Controller* (USB 1): Seilkraft, Seillänge
    - *Sensorplatine* (USB 2): 14 Beschleunigungssensoren $arrow.r$ 13 Gelenkwinkel
    - Daraus die *gemessene* Armform - der Roboter kann seine Spitze sonst nicht sehen
    - Fehlt einer Policy ein Signal: Handbetrieb statt Ersatzwerte

    #text(weight: "bold", fill: htwk-cyan)[
      Aus dem angezeigten Zielabstand wird eine Messung.
    ]
  ],
  [
    #align(center + horizon)[
      #rect(stroke: 0.5pt + htwk-lightgray, inset: 6pt, radius: 4pt)[
        #image("Images/gui-sensoren.png", height: 11em)
        #v(0.2em)
        #text(size: 7pt, fill: htwk-gray)[Grün: gemessen. Gestrichelt: Simulation.]
      ]
    ]
  ]
)

== Die Policy ohne PyTorch
- Der Actor ist ein MLP aus *Linear + ELU*, deterministisch ausgewertet
- Exportiert werden nur die *Gewichte* plus ein Manifest des Beobachtungslayouts
- Der Vorwärtspass ist NumPy - kein PyTorch, kein mjlab, keine GPU

#v(0.6em)
#align(center)[
  #text(weight: "bold", fill: htwk-cyan)[250 KiB je Policy statt eines Software-Stacks]
]

#v(0.6em)
Heikel ist nicht das Netz, sondern der *Beobachtungsvektor*: Termreihenfolge,
Historie über fünf Takte, die begrenzte letzte Aktion. Stimmt hier etwas nicht,
rechnet das Netz weiter - der Arm bewegt sich einfach falsch.

== Ein Thread, 50 Hz
- Regelkreis und Anzeige in *einer* Ereignisschleife - keine Sperren, keine Wettläufe
- Regelschritt $approx$ 0,1 ms, Bildausgabe 6 - 8 ms von 20 ms Budget
- Die Bildrate regelt sich selbst - der Regeltakt bleibt bei 50 Hz
- Verpasste Takte werden übersprungen, nicht nachgeholt
- Fehler sind Betriebszustände: Kabel ab, kein Treiber, kein OpenGL $arrow.r$ Meldung statt Absturz

= Ergebnisse

== Der Nachbau entspricht dem Training
#figure(
  table(
    columns: (auto, auto, auto, auto),
    inset: 8pt,
    align: (left, right, right, right),
    [*Sensor-Level*], [*Nachbau*], [*Spanne*], [*Training*],
    [force], [294 mm], [177 - 443 mm], [344 mm],
    [tendon], [75 mm], [38 - 132 mm], [68 mm],
    [imu], [91 mm], [21 - 285 mm], [44 mm],
    [joints], [63 mm], [18 - 116 mm], [42 mm],
  )
)
#text(size: 9pt, fill: htwk-gray)[
  Mittlerer Zielabstand im eingeschwungenen Zustand, elf Zielwinkel, Simulation.
  Auch das erwartete *Scheitern* von `force` wird reproduziert - der beste Beleg
  dafür, dass der Beobachtungsvektor stimmt.
]

== Stand und Ausblick
#grid(
  columns: (1fr, 1fr),
  gutter: 1.5em,
  [
    === Erreicht
    - Zwei Betriebsarten in einer Oberfläche
    - Vier Policies ohne Trainingsstack nutzbar
    - Sensorplatine eingebunden: alle vier Level auch auf der Hardware
    - Stabile 50 Hz, 51 automatisierte Tests
    - `git clone` + Doppelklick unter Windows
  ],
  [
    === Nächste Schritte
    - Messreihen am realen Aufbau: Sim-to-Real je Sensor-Level
    - Aufzeichnen der Messfahrten aus der Oberfläche heraus
    - Einbaulage der Platine automatisch prüfen
  ]
)

= Abschluss <touying:hidden>

#slide(
  config: config-page(
    header: none,
    footer: none,
    fill: htwk-blue,
    margin: 0pt,
  )
)[
  #align(center + horizon)[
    #text(size: 28pt, weight: "bold", fill: white)[Vielen Dank für Ihre Aufmerksamkeit!]
    #v(1em)
    #text(size: 18pt, style: "italic", fill: htwk-cyan)[Fragen & Diskussion]
  ]
]
