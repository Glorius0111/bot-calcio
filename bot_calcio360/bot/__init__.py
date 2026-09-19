"""Bot Statistico Calcio a 360° - package."""
from .poisson import poisson_pmf, poisson_cdf, prob_over
from .filtro import verifica_campione, FiltroResult
from .segmentazione import stima_attesi_totali
from .marcatori import prob_marcatura, analizza_marcatori
from .cartellini import stima_cartellini
from .report import genera_report

__all__ = [
    "poisson_pmf", "poisson_cdf", "prob_over",
    "verifica_campione", "FiltroResult",
    "stima_attesi_totali",
    "prob_marcatura", "analizza_marcatori",
    "stima_cartellini",
    "genera_report",
]
