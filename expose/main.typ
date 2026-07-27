#import "template.typ": expose, hinweis

#show: expose.with(
  title: "<Arbeitstitel der Abschlussarbeit>",
  author: "<Vorname Nachname>",
  supervisor: "<Name Betreuer:in>",
  date: none, // none = heutiges Datum automatisch einsetzen, oder z. B. "26. März 2026"
)

= Zielstellung

#hinweis[
  Was ist das übergeordnete Ziel der Arbeit? Welches Problem soll gelöst
  bzw. welcher Beitrag geleistet werden? 3-5 Sätze reichen meist aus.
]

#"<Kurzer Text: Worum geht es in der Arbeit und was soll am Ende erreicht sein?>"

= Forschungsfragen

#hinweis[
  Welche konkreten Fragen soll die Arbeit beantworten? Meist 2-4 klar
  formulierte, überprüfbare Fragen, die sich direkt aus der Zielstellung
  ableiten.
]

- #"<Forschungsfrage 1>"
- #"<Forschungsfrage 2>"
- #"<Forschungsfrage 3>"

= Zeitplan

#hinweis[
  Grober zeitlicher Ablauf der Arbeit, z. B. je Phase mit Kalenderwoche
  oder Datum. Eine einfache Tabelle reicht aus.
]

#table(
  columns: (auto, 1fr),
  inset: 8pt,
  [*Zeitraum*], [*Phase / Meilenstein*],
  [#"<KW/Datum>"], [#"<z. B. Einarbeitung, Stand der Technik>"],
  [#"<KW/Datum>"], [#"<z. B. Konzept / Entwurf>"],
  [#"<KW/Datum>"], [#"<z. B. Umsetzung>"],
  [#"<KW/Datum>"], [#"<z. B. Evaluation, Auswertung>"],
  [#"<KW/Datum>"], [#"<z. B. Schreiben, Abgabe>"],
)

= Literatur

#hinweis[
  Erste, vorläufige Literaturliste als Ausgangspunkt für die Arbeit - wird
  im Laufe der Arbeit weiter ergänzt (siehe auch `report/references.bib`).
]

#bibliography("references.bib", style: "ieee", full: true, title: none)
