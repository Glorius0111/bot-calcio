"""Runner batch: elabora TUTTE le partite e produce report + classifica.

- Per ogni match -> genera_report (filtro, Poisson, marcatori, cartellini)
- Salva 1 file txt per partita + 1 classifica riepilogativa
- Ritorna lista ordinata per affidabilità (prob max tra i mercati)
"""
from pathlib import Path
from .report import genera_report
from .html_report import genera_html


def slug(s: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in s).strip("_")


def etichetta(giudizio: str) -> str:
    """Versione corta del giudizio per tabelle leggibili."""
    g = giudizio or ""
    if g.startswith("Dati Provvisori"):
        return "PROVVISORIO"
    if "Alta Affidabilit" in g:
        return "ALTA"
    if "Buona Affidabilit" in g:
        return "BUONA"
    if "Media" in g:
        return "MEDIA"
    return "MONITORARE"


def quando(r: dict) -> str:
    """'20/09 20:45' o '20/09' o ''."""
    d = r.get("data", "")
    try:
        y, mo, g = d.split("-")
        base = f"{g}/{mo}"
    except ValueError:
        return d
    return base + (f" {r['ora']}" if r.get("ora") else "")


def riga(r: dict) -> str:
    top = r.get("top_marcatore", "")
    base = (f"{quando(r):<12}"
            f"{r['partita']:<30} "
            f"Ang {r['over_angoli']:>5}% | "
            f"Tiri {r['over_tiri']:>5}% | "
            f"Cart {r['over_cartellini']:>5}% | "
            f"O2.5 {r.get('gol_o25', 0):>5}% | "
            f"GG {r.get('gol_gg', 0):>5}% => {etichetta(r['giudizio'])}")
    if r.get("idea"):
        base += f" | IDEA: {r['idea']}"
    return base + (f" | gol: {top}" if top else "")


def elabora_tutte(partite: list[dict], out_dir: str | Path = "reports",
                  risultati_giocati: list[dict] = None) -> list[dict]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    risultati = []
    for m in partite:
        rep = genera_report(m)
        fname = f"{slug(rep.partita)}.txt"
        (out / fname).write_text(rep.testo, encoding="utf-8")
        best = max(rep.angoli.prob_perc, rep.tiri.prob_perc, rep.cartellini_prob)
        top_m = ""
        if rep.marcatori:
            m0 = rep.marcatori[0]
            rig = "[RIG] " if m0.rigorista else ""
            top_m = f"{rig}{m0.nome} {m0.prob_gol * 100:.0f}%"
        risultati.append({
            "partita": rep.partita,
            "lega": m.get("lega", ""),
            "data": m.get("data", ""),
            "ora": m.get("ora", ""),
            "stato": m.get("stato", "prossima"),
            "giudizio": rep.giudizio,
            "top_marcatore": top_m,
            "over_angoli": rep.angoli.prob_perc,
            "over_tiri": rep.tiri.prob_perc,
            "over_cartellini": rep.cartellini_prob,
            "gol_o25": rep.gol_o25,
            "gol_gg": rep.gol_gg,
            "idea": rep.idea,
            "giocabili": rep.giocabili,
            "det": {
                "ang": rep.angoli.atteso_totale,
                "ang_casa": rep.ang_casa, "ang_osp": rep.ang_osp,
                "tiri": rep.tiri.atteso_totale,
                "tiri_casa": rep.tiri_casa, "tiri_osp": rep.tiri_osp,
                "cart": rep.cartellini_attesi,
                "falli": rep.cartellini_dettaglio,
                "falli_tot": rep.falli_tot,
                "gol": rep.gol_attesi,
                "gol_casa": rep.gol_casa, "gol_osp": rep.gol_osp,
                "o15": rep.gol_o15, "o25": rep.gol_o25,
                "o35": rep.gol_o35, "gg": rep.gol_gg,
                "uno": rep.uno, "ics": rep.ics, "due": rep.due,
                "poss": m.get("possesso"), "tt": m.get("tiri_totali"),
                "xgs": m.get("xg_squadre"),
                "scala_a": rep.scala_angoli, "scala_t": rep.scala_tiri,
                "scala_g": rep.scala_gol,
                "off_tot": rep.off_tot, "off_o35": rep.off_o35,
                "scala_o": rep.scala_off,
                "marcatori": [(mm.nome, mm.squadra, round(mm.prob_gol * 100, 0),
                               mm.rigorista) for mm in rep.marcatori[:6]],
                "filtro": rep.filtro_msg,
                "giocate": (m.get("partite_casa", 0), m.get("partite_trasferta", 0)),
            },
            "best": best,
            "filtro_ok": rep.filtro_ok,
            "file": fname,
            "testo": rep.testo,
        })
    # Ordina: prima filtro_ok, poi best desc
    risultati.sort(key=lambda r: (r["filtro_ok"], r["best"]), reverse=True)

    # Classifica riepilogativa, raggruppata per lega e ordinata per data/ora
    righe = ["CLASSIFICA AFFIDABILITA' — TUTTE LE PARTITE", ""]
    gruppi: dict[str, list] = {}
    for r in risultati:
        gruppi.setdefault(r["lega"] or "Varie", []).append(r)
    for lega, lst in gruppi.items():
        lst.sort(key=lambda x: (x.get("data", ""), x.get("ora", "") or "99"))
        righe.append(f"== {lega} ({len(lst)} partite) ==")
        for r in lst:
            righe.append(riga(r))
        righe.append("")
    righe.append("Legenda: ANG=Over 8.5 angoli, TIRI=Over 8.5 tiri in porta, "
                 "CART=Over 3.5 cartellini, O2.5=Over 2.5 gol, GG=entrambe segnano.")
    righe.append("IDEA=linea con probabilita' 55-78%, quella che il book quota "
                 "~1.40-1.85 (le linee base oltre l'80% non vengono quotate).")
    righe.append("PROVVISORIO = dati reali ma campione < 6: nessun pronostico. "
                 "ALTA/BUONA/MEDIA = giudizi operativi.")
    (out / "_classifica.txt").write_text("\n".join(righe), encoding="utf-8")
    genera_html(risultati, out, risultati_giocati=risultati_giocati or [])
    return risultati
