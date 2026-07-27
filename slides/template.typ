// Template für die Präsentation auf Basis von Touying (HTWK Corporate Design).
// Touying wird beim CI-Build automatisch aus dem Typst-Paketregister geladen.
#import "@preview/touying:0.7.4": *
#import themes.simple: *

// HTWK Leipzig Corporate Design Farben
#let htwk-blue = rgb("#022541")      // Primärfarbe (Dunkelblau)
#let htwk-cyan = rgb("#009EE3")      // Sekundärfarbe (Cyan für Akzente / Tapes)
#let htwk-gray = rgb("#2E3639")      // Textfarbe (Dunkelgrau)
#let htwk-lightgray = rgb("#BEC3C6") // Silbergrau (Hintergründe / Linien)

// Text für die Fußzeile. In main.typ per `#footer-text.update("...")` setzen.
#let footer-text = state("footer-text", "<Projektname> | <Vorname Nachname>")

// Automatische Sektions-Trennfolien: Jede Überschrift der Ebene 1 (`= ...`)
// erzeugt automatisch eine eigene, vollflächige blaue Trennfolie.
#let htwk-section-slide(self) = {
  slide(
    config: config-page(
      header: none,
      footer: none,
      fill: htwk-blue,
      margin: 0pt,
    )
  )[
    #set align(center + horizon)
    #show heading: set align(center)
    #text(size: 18pt, weight: "bold", fill: white)[
      #utils.display-current-heading(level: 1)
    ]
  ]
}

// Kopfzeile mit HTWK-Logo (kein Folientitel im Header, der steht auf der Folie selbst)
#let htwk-header(self) = {
  block(
    width: 100%,
    height: 1em,
    inset: (x: 2.5em, y: 1em),
    stroke: none,
  )[
    #align(right + horizon)[
      #image("Images/HTWK_Logo.jpg", height: 4.6em)
    ]
  ]
}

// Fußzeile mit Trennlinie, Fußzeilentext (siehe footer-text) und Foliennummer
#let htwk-footer(self) = {
  block(
    width: 100%,
    height: 2em,
    inset: (x: 2em, bottom: 1em),
  )[
    #line(length: 100%, stroke: 0.5pt + htwk-lightgray)
    #v(0.2em)
    #grid(
      columns: (1fr, 1fr),
      align: (left, right),
      context text(size: 9pt, fill: htwk-gray.lighten(20%))[#footer-text.get()],
      []
    )
  ]
}

// Titelfolie im HTWK Corporate Design
#let htwk-title-slide(
  title: [],
  subtitle: [],
  author: [],
  date: [],
  institution: [],
) = {
  slide(
    config: config-page(
      margin: (top: 1.5cm, bottom: 1.5cm, x: 2.5cm),
      header: none,
      footer: none,
    )
  )[
    // Logo oben rechts platzieren
    #align(right)[
      #image("Images/HTWK_Logo.jpg", width: 25%)
    ]

    #v(1.2cm)

    // Titelblock mit Doppel-Tapes auf der linken Seite (HTWK-H-Branding)
    #grid(
      columns: (auto, 1fr),
      gutter: 1.2cm,
      align: horizon,
      grid(
        columns: 2,
        gutter: 4pt,
        rect(width: 8pt, height: 2.2cm, fill: htwk-cyan, radius: 2pt),
        rect(width: 8pt, height: 2.2cm, fill: htwk-cyan, radius: 2pt),
      ),
      [
        #text(size: 18pt, weight: "bold", fill: htwk-blue)[#title] \
        #v(0.6em)
        #text(size: 9pt, fill: htwk-gray)[#subtitle]
      ]
    )

    #v(2fr)

    // Metadaten-Block unten (Autor:in/Team links, Datum rechts)
    #grid(
      columns: (1fr, 1fr),
      align: (left, right),
      [
        #text(size: 9pt, weight: "bold", fill: htwk-blue)[#author] \
        #text(size: 7pt, fill: htwk-gray)[#institution]
      ],
      [
        #text(size: 7pt, fill: htwk-gray)[#date]
      ]
    )
  ]
}

// Haupt-Theme-Funktion. In main.typ einmal per `#show: praesentation` aktivieren,
// danach die eigentlichen Folien schreiben (siehe main.typ als Beispiel).
#let praesentation(body) = {
  show: simple-theme.with(
    aspect-ratio: "16-9",
    header: htwk-header,
    footer: htwk-footer,
    config-page(
      margin: (top: 4.2em, bottom: 2.8em, x: 2.5em),
      fill: white,
    ),
    config-common(
      handout: false,
      new-section-slide-fn: htwk-section-slide,
    )
  )

  // Schrift- und Absatzkonfiguration (muss NACH dem Theme stehen, um wirksam zu sein)
  set text(font: "Arial", size: 16pt, fill: htwk-gray, lang: "de")
  show heading: set text(font: "Arial", fill: htwk-blue)

  // Ebene-2-Überschriften (`== ...`) bekommen die "Doppel-Tapes" als Folientitel-Branding
  show heading.where(level: 2): it => {
    v(0.1em)
    grid(
      columns: (auto, 1fr),
      gutter: 0.8em,
      align: horizon,
      grid(
        columns: 2,
        gutter: 3pt,
        rect(width: 4pt, height: 1.3em, fill: htwk-cyan, radius: 1pt),
        rect(width: 4pt, height: 1.3em, fill: htwk-cyan, radius: 1pt),
      ),
      text(size: 18pt, weight: "bold", fill: htwk-blue)[#it.body]
    )
    v(0.4em)
  }

  set list(marker: (
    circle(radius: 2.5pt, fill: htwk-cyan),
    rect(width: 4pt, height: 4pt, fill: htwk-blue, radius: 1pt)
  ))
  set par(justify: false, leading: 0.8em)

  body
}
