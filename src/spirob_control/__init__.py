"""SpiRob Control - grafische Bedienoberfläche für den Seilzug-Tentakel SpiRob.

Zwei Betriebsarten, eine Oberfläche:

* **Handbetrieb** - zwei Schieberegler geben direkt die Zugkraft der beiden
  Seile vor.
* **Policy** - eine im Reinforcement Learning trainierte Regelung übernimmt die
  Seilkräfte, vorgegeben wird nur noch die Zielposition der Spitze.

Beides läuft immer gegen den digitalen Zwilling (MuJoCo) und kann zusätzlich
auf die echte Hardware (ESP32-Motorcontroller, serielle Schnittstelle) gelegt
werden.

Start::

    python -m spirob_control
"""

__version__ = "1.0.0"
