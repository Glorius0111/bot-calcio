"""Passo D (parte 1): Analisi Marcatori.

Input per giocatore: xG per 90 minuti, minuti previsti, flag rigorista.
Formula: xG_eff = xG_per90 * (minuti/90) [+ bonus rigori]
         P(gol almeno 1) = 1 - exp(-xG_eff)  (Poisson: P(X>=1))

Bonus rigorista: +0.25 xG_eff (valore standard: un rigore ~0.76 xG,
distribuito sulla probabilità di averne uno in partita ~30% => ~0.23).
"""
import math
from dataclasses import dataclass

BONUS_RIGORISTA_XG = 0.25


@dataclass
class Marcatore:
    nome: str
    squadra: str
    xg_per90: float
    minuti_previsti: int = 90
    rigorista: bool = False
    xg_effettivi: float = 0.0
    prob_gol: float = 0.0


def prob_marcatura(xg_per90: float, minuti_previsti: int = 90,
                   rigorista: bool = False) -> tuple[float, float]:
    """Ritorna (xg_effettivi, P(gol))."""
    if xg_per90 < 0:
        xg_per90 = 0.0
    minuti_previsti = max(0, min(90, minuti_previsti))
    xg_eff = xg_per90 * (minuti_previsti / 90.0)
    if rigorista:
        xg_eff += BONUS_RIGORISTA_XG
    p = 1.0 - math.exp(-xg_eff)
    return round(xg_eff, 3), round(max(0.0, min(1.0, p)), 4)


def analizza_marcatori(giocatori: list[dict]) -> list[Marcatore]:
    """giocatori: [{nome, squadra, xg_per90, minuti_previsti, rigorista}]. Ordinati per prob decrescente."""
    out: list[Marcatore] = []
    for g in giocatori:
        nome = (g.get("nome", "") or "").strip()
        if len(nome) < 3 or nome.replace(".", "").strip().lower() in (
                "na", "n/a", "unknown", "tbc"):
            continue  # righe spazzatura delle fonti (es. "N.A")
        xg_eff, p = prob_marcatura(
            float(g.get("xg_per90", 0.0)),
            int(g.get("minuti_previsti", 90)),
            bool(g.get("rigorista", False)),
        )
        out.append(Marcatore(
            nome=nome,
            squadra=g.get("squadra", "?"),
            xg_per90=float(g.get("xg_per90", 0.0)),
            minuti_previsti=int(g.get("minuti_previsti", 90)),
            rigorista=bool(g.get("rigorista", False)),
            xg_effettivi=xg_eff,
            prob_gol=p,
        ))
    out.sort(key=lambda m: m.prob_gol, reverse=True)
    return out
