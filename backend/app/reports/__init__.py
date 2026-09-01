"""
Report-Export: TXT.

Der Generator bekommt das kanonische ``ResultsOut``-Modell (engine/results.py)
sowie den ``JobOut`` für Kopf-Metadaten und liefert den fertigen Inhalt als
``str`` zurück — Schreiben nach ``docs/`` und das Streamen an den Client
übernimmt die API-Schicht (api/jobs.py).
"""
from __future__ import annotations

from .txt_report import generate_txt_report

__all__ = ["generate_txt_report"]
