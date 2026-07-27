# Typst: Was ist das und wie nutze ich es?

Das Exposé (`expose/`), die schriftliche Arbeit (`report/`) und die
Präsentation (`slides/`) werden in diesem Projekt mit **Typst** statt mit
LaTeX oder Word geschrieben.

## Was ist Typst?

Typst ist ein modernes Textsatzsystem (Alternative zu LaTeX) mit einer
leicht lesbaren, an Markdown erinnernden Syntax. Vorteile gegenüber LaTeX:

- **Sehr schnelle Kompilierung** (oft nur Millisekunden) – dadurch eine
  flüssige Live-Vorschau direkt beim Tippen.
- **Klare, verständliche Fehlermeldungen** statt kryptischer LaTeX-Logs.
- Keine komplizierte lokale Installation nötig (siehe unten).

Du musst Typst dafür nicht auf deinem Rechner installieren – am einfachsten
arbeitest du direkt im Editor mit Live-Vorschau (siehe nächster Abschnitt).

## Lokal zum Laufen bringen

### Variante 1: VS Code mit Live-Vorschau (empfohlen)

1. Installiere die VS-Code-Extension **Tinymist Typst**.
2. Öffne z. B. `report/main.typ`.
3. Klicke oben rechts im Editor auf das **Live-Preview-Icon** (Dokument mit
   Lupe).
4. Das Dokument wird beim Tippen automatisch neu kompiliert und als PDF direkt
   daneben angezeigt – kein manuelles Kompilieren nötig.

### Variante 2: Kommandozeile

Falls du lieber im Terminal arbeitest oder kein VS Code nutzt:

```bash
# Typst installieren (z. B. via winget, homebrew oder direkt von typst.app)
# https://github.com/typst/typst#installation

# Dokument einmalig kompilieren
typst compile report/main.typ report.pdf

# Bei jeder Änderung automatisch neu kompilieren
typst watch report/main.typ report.pdf
```

## Wie ist `report/` aufgebaut?

```text
report/
├── main.typ           # Haupt-Datei: bindet Template + Kapitel ein
├── template.typ       # Layout (Titelseite, Kopf-/Fußzeile, Verzeichnisse)
├── references.bib     # Literaturverzeichnis
├── Images/             # Bilder für die Arbeit
└── Sections/           # Ein Kapitel pro Datei
    ├── 01_Motivation.typ
    ├── 02_Grundlagen.typ
    ├── 03_StandDerTechnik.typ
    ├── 04_EntwurfDesign.typ
    ├── 05_Umsetzung.typ
    ├── 06_MessungenEvaluationDiskussion.typ
    └── 07_ZusammenfassungAusblick.typ
```

`main.typ` bindet die Kapitel aus `Sections/` der Reihe nach ein. Die
Kapitelstruktur orientiert sich an einer klassischen Abschlussarbeit. Jedes
Kapitel beginnt mit einem grau hinterlegten **Hinweis-Kasten**
(`#hinweis[...]`, definiert in `template.typ`), der skizziert, welche Inhalte
dort erwartet werden – nach und nach durch eigenen Text ersetzen oder
entfernen. Die mitgelieferten Beispiel-Inhalte zeigen zusätzlich, wie man in
Typst zitiert, Formeln schreibt, Bilder/Tabellen einfügt, Code-Blöcke
einbindet und Kapitel referenziert.

`slides/` für die Präsentation ist analog aufgebaut (`main.typ` +
`template.typ`), aber ohne Kapitel-Struktur.

## Und das Exposé (`expose/`)?

Vor Beginn der eigentlichen Arbeit steht meist ein kurzes **Exposé** (ca.
2-3 Seiten), das den Plan für die Arbeit skizziert. Dafür gibt es den
eigenen Ordner `expose/` mit eigener, bewusst schlanker `template.typ` (kein
Inhaltsverzeichnis nötig bei so wenigen Seiten). `expose/main.typ` enthält
vier Abschnitte – auch hier mit Hinweis-Kästen, was jeweils erwartet wird:

- **Zielstellung** – worum geht es, was soll erreicht werden?
- **Forschungsfragen** – welche konkreten Fragen sollen beantwortet werden?
- **Zeitplan** – grober zeitlicher Ablauf der Arbeit.
- **Literatur** – vorläufige Leseliste als Startpunkt.

## Beispiele aus den mitgelieferten Kapiteln

**Zitieren** (Quelle muss in `references.bib` stehen):

```typst
Wichtiger Fakt aus der Literatur @sagan_1993.
```

**Formel mit Nummerierung und Referenz:**

```typst
$ E = m c^2 $ <eq:beispiel>

Wie in @eq:beispiel gezeigt, ...
```

**Bild mit Beschriftung:**

```typst
#figure(
  image("../Images/CylinderImage.jpg", width: 60%),
  caption: "Beschreibung des Bildes",
) <fig:beispiel>
```

**Tabelle:**

```typst
#figure(
  table(
    columns: (auto, auto),
    [*Parameter*], [*Wert*],
    [Geschwindigkeit], [10.5 m/s],
  ),
  caption: [Beispieltabelle],
)
```

**Code-Block mit Syntax-Hervorhebung** (z. B. im Kapitel „Umsetzung"):

````typst
```python
def beispiel_funktion(x):
    return x * 2
```
````

**Kapitel referenzieren:**

```typst
= Einleitung <sec:einleitung>
...
Wie bereits in @sec:einleitung erwähnt, ...
```

## Wichtig

Du musst Typst nicht lokal installieren, um die finalen PDFs zu bekommen –
das übernimmt die GitLab-CI/CD-Pipeline automatisch bei jedem Push (siehe
Haupt-README). Eine lokale Vorschau (Variante 1 oder 2 oben) ist nur zum
komfortablen Schreiben und Prüfen während der Arbeit hilfreich.
