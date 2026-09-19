"""Provider DEMO: genera tutte le partite di una giornata senza API key.

Serve per provare subito l'automazione. I numeri sono PLAUSIBILI
(Serie A) ma non reali: sostituirli con provider reale in produzione.
"""
import random
from .base import BaseProvider

SERIE_A = ["Inter", "Milan", "Napoli", "Juventus", "Roma", "Lazio",
           "Atalanta", "Fiorentina", "Torino", "Bologna", "Udinese",
           "Empoli", "Lecce", "Verona", "Cagliari", "Genoa",
           "Parma", "Como", "Venezia", "Monza"]

MARCATORI_TIPO = [
    ("Lautaro", 0.62, False), ("Thuram", 0.50, False), ("Calhanoglu", 0.25, True),
    ("Leao", 0.48, False), ("Pulisic", 0.42, True), ("Morata", 0.45, False),
    ("Osimhen", 0.65, False), ("Kvara", 0.38, False), ("Politano", 0.30, True),
    ("Vlahovic", 0.55, True), ("Yildiz", 0.32, False),
    ("Dybala", 0.44, True), ("Dovbyk", 0.52, False),
    ("Retegui", 0.58, True), ("Lookman", 0.46, False),
]


def _rnd(a: float, b: float) -> float:
    return round(random.uniform(a, b), 1)


class DemoProvider(BaseProvider):
    """Crea N partite automatiche (default giornata da 10)."""

    def __init__(self, seed: int = 7, n_partite: int = 10,
                 partite_giocate: int = 9):
        self.seed = seed
        self.n_partite = n_partite
        self.partite_giocate = partite_giocate

    def get_partite(self) -> list[dict]:
        random.seed(self.seed)
        squadre = SERIE_A[:]
        random.shuffle(squadre)
        partite = []
        for i in range(0, self.n_partite * 2, 2):
            casa, osp = squadre[i], squadre[i + 1]
            marc = []
            for nome, xg, rig in random.sample(MARCATORI_TIPO, 4):
                sq = casa if random.random() < 0.5 else osp
                marc.append({"nome": nome, "squadra": sq,
                             "xg_per90": xg,
                             "minuti_previsti": random.choice([90, 85, 80, 75]),
                             "rigorista": rig})
            partite.append({
                "casa": casa, "trasferta": osp,
                "partite_casa": self.partite_giocate,
                "partite_trasferta": self.partite_giocate,
                "soglia_minima_partite": 6,
                "soglia_angoli": 8.5, "soglia_tiri": 4.5,
                "soglia_cartellini": 3.5,
                "tasso_cartellini": 0.14, "severita_arbitro": 1.0,
                "angoli": {
                    "casa_fatti_casa": _rnd(4.5, 7.0),
                    "casa_subiti_casa": _rnd(2.5, 5.0),
                    "ospite_fatti_fuori": _rnd(3.5, 6.5),
                    "ospite_subiti_fuori": _rnd(3.0, 5.5)},
                "tiri_in_porta": {
                    "casa_fatti_casa": _rnd(4.0, 6.5),
                    "casa_subiti_casa": _rnd(2.5, 4.5),
                    "ospite_fatti_fuori": _rnd(3.5, 6.0),
                    "ospite_subiti_fuori": _rnd(3.0, 5.0)},
                "falli": {
                    "commessi_casa": _rnd(10.0, 13.5),
                    "subiti_casa": _rnd(10.5, 13.5),
                    "commessi_ospite": _rnd(10.0, 13.5),
                    "subiti_ospite": _rnd(10.5, 13.5)},
                "marcatori": marc,
            })
        return partite
