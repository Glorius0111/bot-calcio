from bot.poisson import prob_over
from bot.filtro import verifica_campione
from bot.segmentazione import stima_attesi_totali
from bot.marcatori import prob_marcatura


def test_poisson_over_alta_media():
    # lambda 10.2, Over 8.5 deve essere > 65% (verificato: ~68.9%)
    assert prob_over(10.2, 8.5) > 0.65


def test_poisson_over_bassa_media():
    assert prob_over(2.0, 4.5) < 0.15


def test_filtro_blangenheim():
    assert verifica_campione(9, 9, 6).ok is True
    assert verifica_campione(3, 9, 6).ok is False


def test_segmentazione():
    s = stima_attesi_totali(6.0, 4.0, 5.0, 5.0)
    assert abs(s.totale - ((6.0 + 5.0) / 2 + (5.0 + 4.0) / 2)) < 1e-9


def test_rigorista_bonus():
    _, p_no = prob_marcatura(0.40, 90, False)
    _, p_si = prob_marcatura(0.40, 90, True)
    assert p_si > p_no
