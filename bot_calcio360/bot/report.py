"""Report di Analisi Completo (punto 3 del manuale)."""
import math
from dataclasses import dataclass, field
from .filtro import verifica_campione
from .segmentazione import stima_attesi_totali
from .poisson import prob_over, poisson_pmf
from .marcatori import analizza_marcatori
from .cartellini import stima_cartellini


@dataclass
class ReportMercato:
    label: str
    atteso_totale: float
    soglia: float
    prob_perc: float


@dataclass
class ReportFinale:
    partita: str
    filtro_ok: bool
    filtro_msg: str
    angoli: ReportMercato
    tiri: ReportMercato
    cartellini_attesi: float
    cartellini_soglia: float
    cartellini_prob: float
    cartellini_dettaglio: str
    gol_attesi: float = 0.0
    gol_casa: float = 0.0
    gol_osp: float = 0.0
    gol_o15: float = 0.0
    gol_o25: float = 0.0
    gol_o35: float = 0.0
    gol_gg: float = 0.0
    uno: float = 0.0
    ics: float = 0.0
    due: float = 0.0
    dc1x: float = 0.0
    dc12: float = 0.0
    dcx2: float = 0.0
    casa_o05: float = 0.0
    casa_o15: float = 0.0
    osp_o05: float = 0.0
    osp_o15: float = 0.0
    ang_casa: float = 0.0
    ang_osp: float = 0.0
    tiri_casa: float = 0.0
    tiri_osp: float = 0.0
    falli_tot: float = 0.0
    off_tot: float = 0.0
    off_o35: float = 0.0
    scala_off: dict = field(default_factory=dict)
    scala_angoli: dict = field(default_factory=dict)
    scala_tiri: dict = field(default_factory=dict)
    scala_gol: dict = field(default_factory=dict)
    idea: str = ""
    giocabili: list = field(default_factory=list)
    marcatori: list = field(default_factory=list)
    giudizio: str = ""
    testo: str = ""


def scala_over(media: float, soglie: list[float]) -> dict:
    """Probabilità Over per una scala di linee. {soglia: %}."""
    return {s: round(prob_over(media, s) * 100, 1) for s in soglie}


def linea_quotabile(nome: str, scala: dict,
                    prob_min: float = 55.0, prob_max: float = 78.0,
                    target: float = 65.0) -> tuple[str, float, float] | None:
    """La linea più alta con probabilità nella zona quotabile (default 55-78%).

    Sotto il 55% la quota è alta ma il rischio cresce, sopra il 78% il book
    paga spiccioli o non quota proprio. Ritorna (nome, soglia, prob) o None.
    """
    cand = [(s, p) for s, p in scala.items() if prob_min <= p <= prob_max]
    if not cand:
        return None
    s, p = min(cand, key=lambda x: (abs(x[1] - target), -x[0]))
    return (nome, s, p)


def giudizio_sintetico(filtro_ok: bool, prob_list: list[float],
                       n_marcatori_alta: int = 0) -> str:
    """Logica giudizio globale."""
    if not filtro_ok:
        return "Partita da Monitorare (campione insufficiente)"
    forti = sum(1 for p in prob_list if p >= 75.0)
    medi = sum(1 for p in prob_list if 60.0 <= p < 75.0)
    if forti >= 2:
        return "Alta Affidabilità Statistica"
    if forti == 1 and medi >= 1:
        return "Buona Affidabilità Statistica"
    if medi >= 2 or forti == 1:
        return "Affidabilità Media — valutare con prudenza"
    return "Partita da Monitorare (nessun segnale forte)"


def genera_report(match: dict) -> ReportFinale:
    """match: dict con chiavi come in esempi/esempio_milan_napoli.json."""
    casa = match.get("casa", "?")
    trasferta = match.get("trasferta", "?")
    partita = f"{casa} vs {trasferta}"

    soglia_min = int(match.get("soglia_minima_partite", 6))
    filtro = verifica_campione(int(match.get("partite_casa", 0)),
                               int(match.get("partite_trasferta", 0)),
                               soglia_min)

    # Angoli (segmentati)
    a = match.get("angoli", {})
    st_a = stima_attesi_totali(float(a.get("casa_fatti_casa", 0)),
                               float(a.get("casa_subiti_casa", 0)),
                               float(a.get("ospite_fatti_fuori", 0)),
                               float(a.get("ospite_subiti_fuori", 0)),
                               label="Angoli")
    soglia_a = float(match.get("soglia_angoli", 8.5))
    p_a = prob_over(st_a.totale, soglia_a) * 100

    # Tiri in porta (segmentati) - soglia base 8.5 (il 4.5 non viene quotato)
    t = match.get("tiri_in_porta", {})
    st_t = stima_attesi_totali(float(t.get("casa_fatti_casa", 0)),
                               float(t.get("casa_subiti_casa", 0)),
                               float(t.get("ospite_fatti_fuori", 0)),
                               float(t.get("ospite_subiti_fuori", 0)),
                               label="Tiri in porta")
    soglia_t = float(match.get("soglia_tiri", 8.5))
    p_t = prob_over(st_t.totale, soglia_t) * 100

    # Cartellini
    f = match.get("falli", {})
    st_c = stima_cartellini(float(f.get("commessi_casa", 12)),
                            float(f.get("subiti_casa", 12)),
                            float(f.get("commessi_ospite", 12)),
                            float(f.get("subiti_ospite", 12)),
                            tasso_conversione=float(match.get("tasso_cartellini", 0.14)),
                            severita_arbitro=float(match.get("severita_arbitro", 1.0)),
                            nota_reali=match.get("nota_cartellini"))
    soglia_c = float(match.get("soglia_cartellini", 3.5))
    p_c = prob_over(st_c.cartellini_attesi, soglia_c) * 100

    # Gol (segmentati casa/trasferta): Over 1.5/2.5/3.5 + GG stimato
    g = match.get("gol", {})
    st_g = stima_attesi_totali(float(g.get("casa_fatti_casa", 1.45)),
                               float(g.get("casa_subiti_casa", 1.15)),
                               float(g.get("ospite_fatti_fuori", 1.25)),
                               float(g.get("ospite_subiti_fuori", 1.35)),
                               label="Gol")
    p_15 = prob_over(st_g.totale, 1.5) * 100
    p_25 = prob_over(st_g.totale, 2.5) * 100
    p_35 = prob_over(st_g.totale, 3.5) * 100
    # GG = P(casa>=1) * P(ospite>=1), Poisson indipendenti
    p_gg = ((1 - math.exp(-max(0.01, st_g.atteso_casa)))
            * (1 - math.exp(-max(0.01, st_g.atteso_ospite)))) * 100
    # 1X2 con matrice Poisson indipendente (0-7 gol per parte)
    lh, la = max(0.05, st_g.atteso_casa), max(0.05, st_g.atteso_ospite)
    p1 = px = p2 = 0.0
    for i in range(8):
        pi = poisson_pmf(i, lh)
        for j in range(8):
            p = pi * poisson_pmf(j, la)
            if i > j:
                p1 += p
            elif i == j:
                px += p
            else:
                p2 += p
    p1, px, p2 = p1 * 100, px * 100, p2 * 100
    # Doppie chance + gol squadra Over 0.5/1.5 (stessa Poisson)
    dc_1x = p1 + px
    dc_12 = p1 + p2
    dc_x2 = px + p2
    ch_o05 = (1 - math.exp(-max(0.01, st_g.atteso_casa))) * 100
    ch_o15 = prob_over(st_g.atteso_casa, 1.5) * 100
    ao_o05 = (1 - math.exp(-max(0.01, st_g.atteso_ospite))) * 100
    ao_o15 = prob_over(st_g.atteso_ospite, 1.5) * 100

    # Scale di linee + linea quotabile (zona 55-78%: quota giocabile)
    sc_a = scala_over(st_a.totale, [8.5, 9.5, 10.5, 11.5, 12.5, 13.5])
    sc_a_casa = scala_over(st_a.atteso_casa, [4.5, 5.5, 6.5, 7.5])
    sc_a_osp = scala_over(st_a.atteso_ospite, [4.5, 5.5, 6.5, 7.5])
    sc_t = scala_over(st_t.totale, [8.5, 9.5, 10.5, 11.5, 13.5])
    sc_t_casa = scala_over(st_t.atteso_casa, [4.5, 5.5, 6.5, 7.5])
    sc_t_osp = scala_over(st_t.atteso_ospite, [4.5, 5.5, 6.5, 7.5])
    sc_g = scala_over(st_g.totale, [0.5, 1.5, 2.5, 3.5, 4.5])
    sc_f = scala_over(st_c.falli_totali_attesi, [23.5, 24.5, 25.5, 26.5, 27.5, 28.5])
    # Fuorigioco (se disponibili)
    o = match.get("fuorigioco")
    st_o = p_o35 = sc_o = None
    off_tot = off_casa = off_osp = 0.0
    if o:
        st_o = stima_attesi_totali(float(o.get("casa_fatti_casa", 0)),
                                   float(o.get("casa_subiti_casa", 0)),
                                   float(o.get("ospite_fatti_fuori", 0)),
                                   float(o.get("ospite_subiti_fuori", 0)),
                                   label="Fuorigioco")
        p_o35 = prob_over(st_o.totale, 3.5) * 100
        sc_o = scala_over(st_o.totale, [2.5, 3.5, 4.5, 5.5])
        off_tot, off_casa, off_osp = st_o.totale, st_o.atteso_casa, st_o.atteso_ospite
    # TUTTE le linee in zona quota (55-78%), ordinate dalla migliore:
    # la migliore = la più vicina al 65% (sopra pagano poco, sotto è rischioso)
    tutte = []
    for nome, scala in (("Ang", sc_a), ("Tiri", sc_t), ("Gol", sc_g),
                        ("Falli", sc_f), ("Off", sc_o or {})):
        for s, p in scala.items():
            if 55.0 <= p <= 78.0:
                tutte.append((nome, s, p))
    tutte.sort(key=lambda x: abs(x[2] - 65.0))
    giocabili = [f"{n} O{s} ({p:.0f}%)" for n, s, p in tutte]
    idea = giocabili[0] if giocabili else ""

    # Marcatori
    marc = analizza_marcatori(match.get("marcatori", []))

    giudizio = giudizio_sintetico(filtro.ok, [p_a, p_t, p_c])
    dati_provvisori = bool(match.get("dati_provvisori", False))
    if dati_provvisori:
        motivo = match.get("motivo_provvisori",
                           "medie di lega in attesa di statistiche reali di squadra")
        giudizio = (f"Dati Provvisori — {motivo} (nessun pronostico)")

    # Testo report (linguaggio semplice, niente tecnicismi)
    righe = []
    righe.append(f"=== {partita} ===")
    _data = match.get("data", "")
    _ora = match.get("ora", "")
    if _data:
        try:
            y, mo, d = _data.split("-")
            _data_txt = f"{d}/{mo}/{y}"
        except ValueError:
            _data_txt = _data
        righe.append(f"Si gioca: {_data_txt}" + (f" alle {_ora}" if _ora else " (orario da confermare)"))
    righe.append("")
    if dati_provvisori:
        righe.append("ESITO: NON GIOCABILE — i dati sono veri ma le squadre hanno "
                     f"giocato poco (servono almeno {soglia_min} partite).")
    elif not filtro.ok:
        righe.append("ESITO: NON GIOCABILE — campione troppo piccolo.")
    else:
        righe.append(f"ESITO: {giudizio}")
    righe.append("")
    righe.append(f"ANGOLI — previsti circa {st_a.totale:.0f} in totale.")
    righe.append(f"  Over 8,5: {p_a:.0f}% su 100. " + ("Quota bassa, non conviene." if p_a >= 80 else
                 "Quota interessante." if p_a >= 55 else "Difficile, meglio evitare."))
    righe.append("  Altre linee: " + " | ".join(
        f"Over {s}: {p:.0f}%" for s, p in sc_a.items() if s != soglia_a))
    righe.append(f"  Di questi: casa circa {st_a.atteso_casa:.0f} (Over 4,5: "
                 f"{sc_a_casa.get(4.5, 0):.0f}%), ospite circa {st_a.atteso_ospite:.0f} "
                 f"(Over 4,5: {sc_a_osp.get(4.5, 0):.0f}%).")
    righe.append("")
    righe.append(f"TIRI IN PORTA — previsti circa {st_t.totale:.0f} in totale.")
    righe.append(f"  Over 8,5: {p_t:.0f}% su 100. " + ("Quota bassa, non conviene." if p_t >= 80 else
                 "Quota interessante." if p_t >= 55 else "Difficile, meglio evitare."))
    righe.append("  Altre linee: " + " | ".join(
        f"Over {s}: {p:.0f}%" for s, p in sc_t.items() if s != soglia_t))
    righe.append(f"  Di questi: casa circa {st_t.atteso_casa:.0f}, ospite circa {st_t.atteso_ospite:.0f}.")
    _pos = match.get("possesso")
    _tt = match.get("tiri_totali")
    if _pos or _tt:
        extra = []
        if _tt:
            extra.append(f"tiri totali (non solo in porta): casa {_tt.get('casa')} / ospite {_tt.get('ospite')}")
        if _pos:
            extra.append(f"possesso palla: casa {_pos.get('casa')}% / ospite {_pos.get('ospite')}%")
        righe.append("  " + " — ".join(extra) + ".")
    righe.append("")
    righe.append(f"CARTELLINI — previsti circa {st_c.cartellini_attesi:.0f} "
                 f"(da circa {st_c.falli_totali_attesi:.0f} falli totali).")
    righe.append(f"  Over 3,5 cartellini: {p_c:.1f}% su 100.")
    if match.get("nota_cartellini"):
        righe.append(f"  Quest'anno: {match['nota_cartellini']}.")
    righe.append("  Falli Over 25,5: "
                 f"{sc_f.get(25.5, 0):.0f}% su 100.")
    righe.append("")
    if st_o is not None:
        righe.append(f"FUORIGIOCO — previsti circa {st_o.totale:.0f}. "
                     f"Over 3,5: {p_o35:.0f}% su 100.")
        righe.append("")
    righe.append(f"GOL — previsti circa {st_g.totale:.1f} "
                 f"({st_g.atteso_casa:.1f} casa + {st_g.atteso_ospite:.1f} ospite).")
    righe.append(f"  Over 2,5: {p_25:.0f}% su 100. Entrambe segnano: {p_gg:.0f}% su 100.")
    righe.append(f"  Esito 1X2: 1 al {p1:.0f}% · X al {px:.0f}% · 2 al {p2:.0f}%.")
    righe.append(f"  Doppie chance: 1X al {dc_1x:.0f}% · 12 al {dc_12:.0f}% · X2 al {dc_x2:.0f}%.")
    righe.append(f"  Casa segna: Over 0,5 al {ch_o05:.0f}% · Over 1,5 al {ch_o15:.0f}%. "
                 f"Ospite segna: Over 0,5 al {ao_o05:.0f}% · Over 1,5 al {ao_o15:.0f}%.")
    _xg = match.get("xg_squadre")
    if _xg:
        righe.append(f"  Gol attesi dai dati (xG): casa {_xg.get('casa')} / ospite {_xg.get('ospite')}.")
    righe.append("")
    if idea:
        righe.append(f"LA GIOCATA PIU' SENSATA: {idea} "
                     "(la piu' vicina al 65%: sopra pagano poco, sotto e' rischioso).")
        altre = [g for g in giocabili[1:4]]
        if altre:
            righe.append("Altre linee che valgono: " + " | ".join(altre))
        righe.append("")
    righe.append("MARCATORI — chi segna più spesso (quota = quanto pagherebbe il book):")
    if marc:
        for m in marc[:6]:
            q = 1 / m.prob_gol if m.prob_gol > 0 else 0
            rig = (f"  {m.nome} ({m.squadra}): segna nel {m.prob_gol * 100:.0f}% dei casi "
                   f"— quota marcatore circa {q:.2f} (xG {m.xg_per90})")
            if m.rigorista:
                rig += " — tira i rigori"
            righe.append(rig)
    else:
        righe.append("  Nessun dato disponibile.")
    testo = "\n".join(righe)

    return ReportFinale(
        partita=partita, filtro_ok=filtro.ok, filtro_msg=filtro.messaggio,
        angoli=ReportMercato("Angoli", round(st_a.totale, 2), soglia_a, round(p_a, 1)),
        tiri=ReportMercato("Tiri in porta", round(st_t.totale, 2), soglia_t, round(p_t, 1)),
        cartellini_attesi=st_c.cartellini_attesi, cartellini_soglia=soglia_c,
        cartellini_prob=round(p_c, 1), cartellini_dettaglio=st_c.dettaglio,
        gol_attesi=round(st_g.totale, 2), gol_o15=round(p_15, 1),
        gol_o25=round(p_25, 1), gol_o35=round(p_35, 1),
        gol_gg=round(p_gg, 1),
        uno=round(p1, 1), ics=round(px, 1), due=round(p2, 1),
        dc1x=round(dc_1x, 1), dc12=round(dc_12, 1), dcx2=round(dc_x2, 1),
        casa_o05=round(ch_o05, 1), casa_o15=round(ch_o15, 1),
        osp_o05=round(ao_o05, 1), osp_o15=round(ao_o15, 1),
        gol_casa=round(st_g.atteso_casa, 2), gol_osp=round(st_g.atteso_ospite, 2),
        ang_casa=round(st_a.atteso_casa, 2), ang_osp=round(st_a.atteso_ospite, 2),
        tiri_casa=round(st_t.atteso_casa, 2), tiri_osp=round(st_t.atteso_ospite, 2),
        falli_tot=round(st_c.falli_totali_attesi, 1),
        off_tot=round(off_tot, 2), off_o35=round(p_o35 or 0, 1),
        scala_off=sc_o or {},
        scala_angoli=sc_a, scala_tiri=sc_t, scala_gol=sc_g,
        idea=idea, giocabili=giocabili,
        marcatori=marc, giudizio=giudizio, testo=testo,
    )
