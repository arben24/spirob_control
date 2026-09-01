"""Farben und ttk-Stile der Oberfläche.

An einer Stelle gebündelt, damit Fenster, Zeichenfläche und Statusleiste
dieselbe Palette benutzen. Als ttk-Thema wird bewusst ``clam`` erzwungen: nur
dieses Thema übernimmt gesetzte Farben auf allen Plattformen zuverlässig -- das
Windows-Standardthema ``vista`` ignoriert die meisten Farbangaben still, und
die GUI sähe dort anders aus als hier beschrieben.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

# Dunkle, kontrastarme Palette - im Labor angenehmer als Weiß und auf dem
# Beamer noch lesbar.
BG = "#12161c"
PANEL = "#1a1f27"
CARD = "#222833"
BORDER = "#2f3743"
TEXT = "#e6edf3"
MUTED = "#8b98a5"
ACCENT = "#4da3ff"
OK = "#3ecf8e"
WARN = "#ffb454"
ERROR = "#ff6b63"

TENDON_TROUGHS = ("#3a201e", "#16283c")
"""Abgedunkelte Seilfarben für die Laufbahn der Schieberegler."""

TENDON_COLORS = ("#ff6b63", "#4da3ff")
"""Farbe je Seil: Seil 0 (rot, biegt nach +x), Seil 1 (blau, biegt nach -x).

Dieselben Farben wie im MuJoCo-Modell, damit Schieberegler und 3D-Ansicht
zusammenpassen.
"""


SCALE = 1.0
"""Aktueller Vergrößerungsfaktor der Oberfläche.

Wird von :func:`apply_scale` gesetzt. Zeichenflächen fragen ihn über
:func:`canvas_font` ab - deren Schriften hängen an keinem Widget und würden
sonst als einzige nicht mitwachsen.
"""

_BASE_SIZES: dict[str, int] = {}
_FONTS: dict[str, tkfont.Font] = {}
_STYLE: ttk.Style | None = None


def canvas_font(size: int, family: str = "TkFixedFont") -> tuple[str, int]:
  """Schrift für Text auf einer Zeichenfläche, mitskaliert."""
  return (family, max(6, round(size * SCALE)))


def apply_scale(factor: float) -> None:
  """Alle Schriften und Abstände auf diesen Faktor bringen.

  Die ttk-Stile verweisen auf dieselben Schriftobjekte, deshalb genügt es,
  deren Größe zu ändern - alle vorhandenen Bedienelemente wachsen sofort mit.
  """
  global SCALE

  SCALE = factor
  for name, font in _FONTS.items():
    font.configure(size=max(6, round(_BASE_SIZES[name] * factor)))
  if _STYLE is not None:
    _STYLE.configure("TButton", padding=(round(10 * factor), round(6 * factor)))
    _STYLE.configure("Stop.TButton", padding=(round(10 * factor), round(10 * factor)))
    _STYLE.configure("TNotebook.Tab", padding=(round(12 * factor), round(6 * factor)))


def setup(root: tk.Misc) -> dict[str, tkfont.Font]:
  """ttk-Stile setzen und die benutzten Schriften zurückgeben."""
  style = ttk.Style(root)
  style.theme_use("clam")

  base = tkfont.nametofont("TkDefaultFont").actual()["family"]
  fonts = {
    "title": tkfont.Font(family=base, size=15, weight="bold"),
    "heading": tkfont.Font(family=base, size=10, weight="bold"),
    "body": tkfont.Font(family=base, size=10),
    "small": tkfont.Font(family=base, size=9),
    "value": tkfont.Font(family="TkFixedFont", size=11, weight="bold"),
    "mono": tkfont.Font(family="TkFixedFont", size=9),
  }

  style.configure(".", background=PANEL, foreground=TEXT, fieldbackground=CARD,
                  bordercolor=BORDER, lightcolor=PANEL, darkcolor=PANEL,
                  font=fonts["body"])
  style.configure("TFrame", background=PANEL)
  style.configure("Card.TFrame", background=CARD, relief="flat")
  style.configure("Header.TFrame", background=BG)
  style.configure("TLabel", background=PANEL, foreground=TEXT)
  style.configure("Card.TLabel", background=CARD, foreground=TEXT)
  style.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=fonts["small"])
  style.configure("Heading.TLabel", background=CARD, foreground=ACCENT, font=fonts["heading"])
  style.configure("Title.TLabel", background=BG, foreground=TEXT, font=fonts["title"])
  style.configure("Value.TLabel", background=CARD, foreground=TEXT, font=fonts["value"])
  style.configure("Status.TLabel", background=BG, foreground=MUTED, font=fonts["small"])

  style.configure("TButton", background=CARD, foreground=TEXT, borderwidth=1,
                  focusthickness=0, padding=(10, 6))
  style.map("TButton",
            background=[("active", BORDER), ("disabled", PANEL)],
            foreground=[("disabled", MUTED)])
  style.configure("Accent.TButton", background=ACCENT, foreground="#0b1017")
  style.map("Accent.TButton", background=[("active", "#7cbcff"), ("disabled", BORDER)])
  style.configure("Stop.TButton", background=ERROR, foreground="#1a0605",
                  font=fonts["heading"], padding=(10, 10))
  style.map("Stop.TButton", background=[("active", "#ff9089")])

  style.configure("TCheckbutton", background=CARD, foreground=TEXT)
  style.map("TCheckbutton", background=[("active", CARD)],
            indicatorcolor=[("selected", ACCENT), ("!selected", BG)])
  style.configure("TRadiobutton", background=CARD, foreground=TEXT)
  style.map("TRadiobutton", background=[("active", CARD)],
            indicatorcolor=[("selected", ACCENT), ("!selected", BG)])

  style.configure("TCombobox", fieldbackground=BG, background=CARD, foreground=TEXT,
                  arrowcolor=TEXT, selectbackground=BG, selectforeground=TEXT)
  # Ohne diese Zuordnung zeichnet clam die schreibgeschützte Combobox in
  # Systemfarben - auf dunklem Grund wäre der Porteintrag dann kaum lesbar.
  style.map("TCombobox",
            fieldbackground=[("readonly", BG)],
            foreground=[("readonly", TEXT), ("disabled", MUTED)],
            selectbackground=[("readonly", BG)],
            selectforeground=[("readonly", TEXT)],
            arrowcolor=[("disabled", MUTED)])
  style.configure("Vertical.TScrollbar", background=CARD, troughcolor=BG,
                  bordercolor=BORDER, arrowcolor=MUTED, width=12)
  style.map("Vertical.TScrollbar", background=[("active", BORDER)])
  root.option_add("*TCombobox*Listbox.background", CARD)
  root.option_add("*TCombobox*Listbox.foreground", TEXT)
  root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
  root.option_add("*TCombobox*Listbox.selectForeground", "#0b1017")

  # Schieberegler: dickere Bahn und ein gut greifbarer Knopf.
  style.configure("Horizontal.TScale", background=CARD, troughcolor=BG,
                  bordercolor=BORDER, lightcolor=ACCENT, darkcolor=ACCENT)
  for name, color in zip(("Tendon0.Horizontal.TScale", "Tendon1.Horizontal.TScale"), TENDON_COLORS):
    style.configure(name, background=CARD, troughcolor=BG, bordercolor=BORDER,
                    lightcolor=color, darkcolor=color)

  style.configure("TSeparator", background=BORDER)
  style.configure("TNotebook", background=PANEL, borderwidth=0)
  style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(12, 6))
  style.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", TEXT)])

  # Ausgangsgrößen merken, damit apply_scale immer vom Original ausgeht und
  # sich Rundungsfehler nicht über viele Schritte aufsummieren.
  _FONTS.clear()
  _FONTS.update(fonts)
  _BASE_SIZES.clear()
  _BASE_SIZES.update({name: int(font.cget("size")) for name, font in fonts.items()})
  globals()["_STYLE"] = style
  return fonts


def card(master: tk.Misc, title: str | None = None, fonts: dict | None = None) -> ttk.Frame:
  """Ein abgesetzter Block mit optionaler Überschrift."""
  outer = ttk.Frame(master, style="Card.TFrame", padding=(12, 10))
  if title:
    # Bewusst mit grid platziert: die Karten werden von den Aufrufern ebenfalls
    # mit grid gefüllt, und Tk lässt in einem Container nur einen
    # Geometrie-Manager zu. Inhalt beginnt deshalb in Zeile 1.
    ttk.Label(outer, text=title.upper(), style="Heading.TLabel").grid(
      row=0, column=0, columnspan=9, sticky="w", pady=(0, 8))
  return outer
