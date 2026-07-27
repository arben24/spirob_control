// ==========================================
// EINSTELLUNGEN & TEMPLATE-DEFINITION
// ==========================================

// Visuell abgesetzter Hinweis-Kasten, um pro Kapitel zu skizzieren, welche
// Inhalte dort erwartet werden. Vor der Abgabe entfernen oder durch eigenen
// Text ersetzen.
#let hinweis(body) = rect(
  width: 100%,
  fill: luma(245),
  stroke: 0.5pt + luma(200),
  inset: 10pt,
  radius: 4pt,
)[
  #text(size: 9pt, style: "italic", fill: luma(90))[
    *Was gehört in dieses Kapitel?* #body
  ]
]

#let project(
  title: "",
  subtitle: "",
  author: "",
  supervisor: "",
  faculty: "",
  date: none,
  body,
) = {
  // --- Seiteneinrichtung & Metadaten ---
  set document(author: author, title: title)
  
  // A4 mit spezifischen Rändern
  set page(
    paper: "a4",
    margin: (x: 30mm, top: 25mm, bottom: 25mm),
    numbering: "1",
    header: none,
    footer: none,
  )
  
  // Sprache und Textformatierung
  set text(font: "New Computer Modern", lang: "de", size: 11pt)
  
  // Absatzformatierung
  set par(justify: true, leading: .8em, first-line-indent: 0em)

  // Überschriften-Nummerierung
  set heading(numbering: "1.1")
  
  // Mathe-Nummerierung
  set math.equation(numbering: "(1)")

  // Bildunterschriften formatieren
  show figure.caption: it => [
    #text(size: 9pt)[*#it.supplement #it.counter.display():* #it.body]
  ]

  show heading: set block(above: 2em, below: 1.5em) // 1.5em Abstand zwischen Überschrift und folgendem Text

  // ==========================================
  // TITELSEITE
  // ==========================================
  
  align(center)[
    #v(2cm)
    #image("Images/HTWK_Logo.jpg", width: 60mm)
    #v(0.8cm)
    
    #text(18pt, smallcaps(faculty)) \
    #v(1.0cm)
    #text(14pt, smallcaps(subtitle)) \
    #v(0.5cm)
    
    #line(length: 100%, stroke: 1.5pt)
    #[
      #set par(leading: 0.4em)
      #text(22pt, weight: "bold", title)
    ]
    #line(length: 100%, stroke: 1.5pt)
    #v(1.5cm)
    
    #align(center)[
      #grid(
        columns: (auto, auto),
        gutter: 1em,
        align: (right, left),
        emph("Autor:"), author,
        emph("Betreuer:"), supervisor
      )
    ]
    
    #v(1fr)
    #text(12pt)[
      #if date == none [
        #datetime.today().display("[day].[month].[year]")
      ] else [
        #date
      ]
    ]
  ]
  
  pagebreak()

  // ==========================================
  // FRONT MATTER (Inhaltsverzeichnis, etc.)
  // ==========================================

  set page(
    paper: "a4",
    margin: (x: 30mm, top: 25mm, bottom: 25mm),
    numbering: "i", // Hier stellen wir für das Verzeichnis auf "i"
    header: [
      #set text(8pt)
      #align(right)[
        // #smallcaps(title)
      ]
      #line(length: 100%, stroke: 0.5pt)
    ],
    footer: context [
      // 1. Die Linie über die gesamte Breite der Seite
      #line(length: 100%, stroke: 0.5pt)
      
      // 2. Ein kleiner Abstand zwischen Linie und Zahl
      #v(2mm)
      
      // 3. Die eigentliche Seitenzahl (hier zentriert)
      #align(center)[
        // .display() ohne Parameter übernimmt automatisch das "i" oder "1" 
        // aus der aktuellen 'set page(numbering: ...)' Regel!
        #counter(page).display()
      ]
    ]
  )
  
  // Zähler für die Verzeichnisse explizit auf 1 setzen (Seite i)
  counter(page).update(1)

  // Inhaltsverzeichnis
  outline(title: "Inhaltsverzeichnis", indent: auto)
  pagebreak()
  
  // Abbildungsverzeichnis
  outline(
    title: "Abbildungsverzeichnis", 
    target: figure.where(kind: image)
  )
  pagebreak()

  // Tabellenverzeichnis
  outline(
    title: "Tabellenverzeichnis", 
    target: figure.where(kind: table)
  )
  pagebreak()

  // ==========================================
  // HAUPTTEIL
  // ==========================================
  
  // Zähler wieder auf 1 zurücksetzen
  counter(page).update(1)
  
  // Seitenzahlen-Stil für den Hauptteil auf normale Zahlen ändern
  set page(numbering: "1")

  body
}
