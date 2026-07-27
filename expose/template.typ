// ==========================================
// EINSTELLUNGEN & TEMPLATE-DEFINITION (Exposé)
// ==========================================
// Bewusst schlanker als report/template.typ: ein Exposé ist kurz
// (ca. 2-3 Seiten) und braucht daher kein Inhalts-/Abbildungsverzeichnis
// oder Titelblatt auf einer eigenen Seite.

// Visuell abgesetzter Hinweis-Kasten, um pro Abschnitt zu skizzieren, welche
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
    *Was gehört in diesen Abschnitt?* #body
  ]
]

#let expose(
  title: "",
  author: "",
  supervisor: "",
  date: none,
  body,
) = {
  set document(author: author, title: title)

  set page(
    paper: "a4",
    margin: (x: 25mm, top: 25mm, bottom: 25mm),
    numbering: "1",
    footer: context [
      #line(length: 100%, stroke: 0.5pt)
      #v(2mm)
      #align(center)[#counter(page).display()]
    ],
  )

  set text(font: "New Computer Modern", lang: "de", size: 11pt)
  set par(justify: true, leading: .8em, first-line-indent: 0em)
  set heading(numbering: "1.")
  show heading: set block(above: 1.5em, below: 1em)

  // Kopfblock: Logo, Titel, Autor:in/Betreuer:in, Datum - kein eigenes
  // Titelblatt, da das Exposé kurz ist.
  align(right)[
    #image("Images/HTWK_Logo.jpg", width: 35mm)
  ]
  v(0.5em)
  align(center)[
    #text(20pt, weight: "bold")[Exposé: #title]
    #v(0.4em)
    #text(11pt)[
      #author
      #if supervisor != "" [ · Betreuer:in: #supervisor]
    ]
    #v(0.2em)
    #text(10pt, fill: luma(90))[
      #if date == none [
        #datetime.today().display("[day].[month].[year]")
      ] else [
        #date
      ]
    ]
  ]
  v(1.2em)
  line(length: 100%, stroke: 1pt)
  v(1em)

  body
}
