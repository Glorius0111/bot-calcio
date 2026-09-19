"""Passo C: Modello Matematico - Distribuzione di Poisson.

Stesso modello usato dai bookmaker: trasforma una media attesa (lambda)
in probabilità matematica di Over.
"""
import math


def poisson_pmf(k: int, lam: float) -> float:
    """P(X = k) per Poisson(lambda)."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    if k < 0:
        return 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def poisson_cdf(k: int, lam: float) -> float:
    """P(X <= k) per Poisson(lambda)."""
    if lam <= 0:
        return 1.0
    if k < 0:
        return 0.0
    return sum(poisson_pmf(i, lam) for i in range(k + 1))


def prob_over(lam: float, soglia: float) -> float:
    """Probabilità P(X > soglia) per una linea Over tipo 8.5 / 4.5 / 3.5.

    Es: prob_over(10.2, 8.5) -> P(X >= 9).
    Ritorna valore 0..1.
    """
    if lam <= 0:
        return 0.0
    # Over N.5 => serve almeno floor(N.5)+1 gol/angoli/tiri
    k_min = int(math.floor(soglia)) + 1
    # P(X >= k_min) = 1 - P(X <= k_min - 1)
    return max(0.0, min(1.0, 1.0 - poisson_cdf(k_min - 1, lam)))


def prob_under(lam: float, soglia: float) -> float:
    """P(X <= floor(soglia))."""
    if lam <= 0:
        return 1.0
    k_max = int(math.floor(soglia))
    return max(0.0, min(1.0, poisson_cdf(k_max, lam)))


def prob_esatta(k: int, lam: float) -> float:
    return poisson_pmf(k, lam)
