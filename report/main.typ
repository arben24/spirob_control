#import "template.typ": project

#show: project.with(
  title: "<Projektname>",
  subtitle: "<Modulnummer - Modulname>",
  // Bei Gruppenarbeiten alle Namen eintragen, z. B. durch Kommas getrennt:
  // author: "Max Mustermann, Erika Musterfrau",
  author: "<Vorname Nachname>",
  supervisor: "<Name Betreuer:in>",
  faculty: "<Studiengang / Fakultät>",
  date: none, // none = heutiges Datum automatisch einsetzen, oder z. B. "26. März 2026"
)

// Hier werden die einzelnen Kapitel eingebunden. Die Struktur orientiert
// sich an einer klassischen Abschlussarbeit; die Hinweis-Kästen in jedem
// Kapitel skizzieren die jeweils erwarteten Inhalte und können nach und nach
// durch eigenen Text ersetzt werden. Die Beispiel-Inhalte zeigen zusätzlich,
// wie man in Typst zitiert, Formeln schreibt, Bilder/Tabellen einfügt,
// Code-Blöcke einbindet und Kapitel referenziert.

#include "Sections/01_Motivation.typ"
#pagebreak()
#include "Sections/02_Grundlagen.typ"
#pagebreak()
#include "Sections/03_StandDerTechnik.typ"
#pagebreak()
#include "Sections/04_EntwurfDesign.typ"
#pagebreak()
#include "Sections/05_Umsetzung.typ"
#pagebreak()
#include "Sections/06_MessungenEvaluationDiskussion.typ"
#pagebreak()
#include "Sections/07_ZusammenfassungAusblick.typ"

// ==========================================
// LITERATURVERZEICHNIS
// ==========================================

#pagebreak()
#bibliography("references.bib", style: "ieee", title: "Literaturverzeichnis")
