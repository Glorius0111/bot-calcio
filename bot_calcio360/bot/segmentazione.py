"""Passo B: Segmentazione dei Dati (Casa vs Trasferta).

MAI usare statistiche generali. Regole:
- squadra casa -> solo dati in casa (fatti/subiti in casa)
- squadra trasferta -> solo dati fuori casa (fatti/subiti fuori casa)

Stima incrociata attacco/difesa:
  atteso_casa   = (casa_fatti_casa + trasferta_subiti_fuori) / 2
  atteso_ospite = (trasferta_fatti_fuori + casa_subiti_casa) / 2
  totale = atteso_casa + atteso_ospite
"""

from dataclasses import dataclass


@dataclass
class StimaSegmentata:
    atteso_casa: float
    atteso_ospite: float
    totale: float
    dettaglio: str


def stima_attesi_totali(casa_fatti: float, casa_subiti: float,
                        trasferta_fatti: float, trasferta_subiti: float,
                        label: str = "") -> StimaSegmentata:
    """Calcola attesi incrociando attacco casalingo con difesa esterna e viceversa."""
    atteso_casa = (casa_fatti + trasferta_subiti) / 2.0
    atteso_ospite = (trasferta_fatti + casa_subiti) / 2.0
    totale = atteso_casa + atteso_ospite
    dettaglio = (
        f"{label}: casa_atteso={atteso_casa:.2f} "
        f"(media tra {casa_fatti:.2f} fatti in casa e {trasferta_subiti:.2f} subiti fuori dall'avversario), "
        f"ospite_atteso={atteso_ospite:.2f} "
        f"(media tra {trasferta_fatti:.2f} fatti fuori e {casa_subiti:.2f} subiti in casa), "
        f"totale={totale:.2f}"
    )
    return StimaSegmentata(atteso_casa=atteso_casa, atteso_ospite=atteso_ospite,
                           totale=totale, dettaglio=dettaglio)
