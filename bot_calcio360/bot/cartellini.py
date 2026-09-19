"""Passo D (parte 2): Cartellini.

Incrocio falli commessi/subiti (segmentati casa/trasferta) per stimare
tensione e aggressività, poi conversione falli -> cartellini.

Modello:
  falli_totali_attesi = stima segmentata su (falli_commessi_casa_casa,
                        falli_subiti_casa_casa, falli_commessi_ospite_fuori,
                        falli_subiti_ospite_fuori)
  Semplificazione robusta: media dei falli commessi delle due squadre
  (segmentati) + correzione aggressività avversaria (falli subiti).

  cartellini_attesi = falli_totali_attesi * tasso_conversione
  tasso default 0.14 (Serie A ~ 1 cartellino ogni ~7 falli fischiati a squadra?
  in realtà ~25 falli totali -> ~4 cartellini => ~0.16). Parametrico per
  campionato e severità arbitro (moltiplicatore 0.8-1.3).
"""
from dataclasses import dataclass
from .segmentazione import stima_attesi_totali
from .poisson import prob_over


@dataclass
class StimaCartellini:
    falli_totali_attesi: float
    cartellini_attesi: float
    prob_over_35: float
    prob_over_45: float
    dettaglio: str


def stima_cartellini(falli_commessi_casa: float, falli_subiti_casa: float,
                     falli_commessi_ospite: float, falli_subiti_ospite: float,
                     tasso_conversione: float = 0.14,
                     severita_arbitro: float = 1.0,
                     nota_reali: str = None) -> StimaCartellini:
    # Falli totali attesi: incrocio commessi casa-segmentati e subiti avversari
    # atteso_falli_casa = (commessi_casa + subiti_ospite)/2  (quanto picchia la casa + quanto subisce l'ospite)
    # atteso_falli_ospite = (commessi_ospite + subiti_casa)/2
    f_casa = (falli_commessi_casa + falli_subiti_ospite) / 2.0
    f_ospite = (falli_commessi_ospite + falli_subiti_casa) / 2.0
    falli_tot = f_casa + f_ospite

    cart = falli_tot * tasso_conversione * severita_arbitro

    p35 = prob_over(cart, 3.5)
    p45 = prob_over(cart, 4.5)
    det = (f"Falli attesi: casa {f_casa:.1f} + ospite {f_ospite:.1f} = {falli_tot:.1f}; "
           f"cartellini attesi {cart:.2f} (tasso {tasso_conversione}, arbitro x{severita_arbitro})")
    if nota_reali:
        det += f" | REALI 2026/27: {nota_reali}"
    return StimaCartellini(falli_totali_attesi=round(falli_tot, 2),
                           cartellini_attesi=round(cart, 2),
                           prob_over_35=round(p35 * 100, 1),
                           prob_over_45=round(p45 * 100, 1),
                           dettaglio=det)
