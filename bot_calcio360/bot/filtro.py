"""Passo A: Filtro di Sicurezza (Campione Minimo)."""
from dataclasses import dataclass


@dataclass
class FiltroResult:
    ok: bool
    partite_casa: int
    partite_trasferta: int
    soglia_minima: int
    messaggio: str


def verifica_campione(partite_casa: int, partite_trasferta: int,
                      soglia_minima: int = 6) -> FiltroResult:
    """Regola manuale: almeno 6-8 partite giocate nella stagione in corso.

    Default 6 (soglia prudente). Usa 8 per massima affidabilità.
    Se una delle due squadre è sotto soglia -> analisi bloccata / da monitorare.
    """
    ok = partite_casa >= soglia_minima and partite_trasferta >= soglia_minima
    if ok:
        msg = (f"Campione sufficiente: {partite_casa} e {partite_trasferta} "
               f"partite (>= {soglia_minima}). Analisi affidabile.")
    else:
        msg = (f"Campione INSUFFICIENTE: casa={partite_casa}, "
               f"trasferta={partite_trasferta}, richiesti >= {soglia_minima}. "
               f"All'inizio del campionato le statistiche sono instabili: "
               f"partita da monitorare, nessun pronostico.")
    return FiltroResult(ok=ok, partite_casa=partite_casa,
                        partite_trasferta=partite_trasferta,
                        soglia_minima=soglia_minima, messaggio=msg)
