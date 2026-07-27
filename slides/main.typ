#import "@preview/touying:0.7.4": *
#import themes.simple: *
#import "template.typ": praesentation, htwk-title-slide, footer-text
#import "template.typ": htwk-blue, htwk-cyan, htwk-gray, htwk-lightgray

// Text der Fußzeile (erscheint klein unten auf jeder Folie außer der Titelfolie)
#footer-text.update("<Projektname> | <Vorname Nachname>")

#show: praesentation

#htwk-title-slide(
  title: "<Projektname>",
  subtitle: "<Kurze Beschreibung des Projekts / Modulname>",
  author: "<Vorname Nachname>",
  date: [#datetime.today().display("[day].[month].[year]")],
  institution: "<Studiengang> | HTWK Leipzig",
)

== Agenda
// #outline() erzeugt automatisch ein Inhaltsverzeichnis aus allen
// Überschriften der Ebene 1 (den Kapitel-Trennfolien weiter unten).
#outline(title: none, indent: 1.5em, depth: 1)

// ---------------------------------------------------------------------
// Eine Überschrift der Ebene 1 (ein einzelnes "=") erzeugt automatisch
// eine eigene, vollflächige blaue Trennfolie mit dem Kapitelnamen.
// ---------------------------------------------------------------------
= Kapitel 1: Einleitung

// Überschriften der Ebene 2 ("==") sind normale Folientitel mit dem
// HTWK-Tape-Branding davor (siehe template.typ).
== Beispiel: Aufzählung
- Erster Stichpunkt
- Zweiter Stichpunkt
  - Ein Unterpunkt (einfach einrücken)
- *Wichtiger* Punkt lässt sich fett hervorheben

== Beispiel: Grid-Layout mit Bild
// #grid(...) teilt eine Folie in mehrere Spalten - praktisch für
// Text-neben-Bild-Layouts.
#grid(
  columns: (1fr, 1fr),
  gutter: 1.5em,
  [
    === Text-Spalte
    - Beliebiger Inhalt links, z. B. Erklärungen
    - Auch Formeln sind möglich: $E = m c^2$
  ],
  [
    #align(center + horizon)[
      #rect(stroke: 0.5pt + htwk-lightgray, inset: 6pt, radius: 4pt)[
        #image("Images/CylinderImage.jpg", height: 8em)
        #v(0.2em)
        #text(size: 7pt, fill: htwk-gray)[Beispielbild mit kleiner Bildunterschrift]
      ]
    ]
  ]
)

= Kapitel 2: Ergebnisse

== Beispiel: Tabelle
#figure(
  table(
    columns: (auto, auto, auto),
    inset: 8pt,
    align: horizon,
    [*Parameter*], [*Wert*], [*Einheit*],
    [Geschwindigkeit], [10.5], [m/s],
    [Druck], [101325], [Pa],
  )
)

== Beispiel: Text farbig hervorheben
#align(center)[
  #text(weight: "bold", fill: htwk-cyan)[
    Wichtige Kernaussagen lassen sich so farblich absetzen.
  ]
]

// Unsichtbare Überschrift (erscheint nicht in Agenda/Navigation), sorgt aber
// für eine sauber abgegrenzte neue Folien-Gruppe - ohne das wuerde der Titel
// der vorherigen Folie leicht sichtbar durchscheinen.
= Abschluss <touying:hidden>

// ---------------------------------------------------------------------
// Eigene, vollflächige Abschlussfolie (wie die Trennfolien oben) -
// dafür #slide(...) direkt mit eigener config-page nutzen.
// ---------------------------------------------------------------------
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
