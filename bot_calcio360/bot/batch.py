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


def etichetta_stato(r: dict) -> str:
    s = r.get("stato", "prossima")
    if s == "live":
        return "IN CORSO"
    if s == "finita":
        return f"FINITA {r.get('risultato', '')}".strip()
    return "DA GIOCARE"


def riga(r: dict) -> str:
    top = r.get("top_marcatore", "")
    tag = ""
    if r.get("stato") == "live":
        tag = "[IN CORSO] "
    elif r.get("stato") == "finita" and r.get("risultato"):
        tag = f"[FINITA {r['risultato']}] "
    base = (f"{quando(r):<12}"
            f"{tag}{r['partita']:<30} "
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
        if not m.get("stato"):
            try:
                from .providers.fixtures_auto import stato_match
                from datetime import datetime as _dt
                m["stato"] = stato_match(m.get("data", ""), m.get("ora", ""), _dt.now())
            except Exception:
                m["stato"] = "prossima"
        rep = genera_report(m)
        fname = f"{slug(rep.partita)}.txt"
        (out / fname).write_text(rep.testo, encoding="utf-8")
        best = max(rep.angoli.prob_perc, rep.tiri.prob_perc, rep.cartellini_prob)
        top_m = ""
        if rep.marcatori:
            m0 = rep.marcatori[0]
            rig = "[RIG] " if m0.rigorista else ""
            top_m = f"{rig}{m0.nome} {m0.prob_gol * 100:.0f}%"
        rk = m.get("rischio", [])
        top_r = ""
        if rk:
            x0 = rk[0]
            top_r = f"{x0['nome']} {x0['prob']:.0f}%"
            if x0.get("quasi") is not None:
                top_r += f" (QUASI PLUS {x0['quasi']:.0f}%)"
            elif x0.get("plus") is not None:
                top_r += f" (PLUS {x0['plus']:.0f}%)"
        risultati.append({
            "partita": rep.partita,
            "lega": m.get("lega", ""),
            "data": m.get("data", ""),
            "ora": m.get("ora", ""),
            "stato": m.get("stato", "prossima"),
            "risultato": m.get("risultato", ""),
            "giudizio": rep.giudizio,
            "top_marcatore": top_m,
            "rischio_top": top_r,
            "over_angoli": rep.angoli.prob_perc,
            "over_tiri": rep.tiri.prob_perc,
            "over_cartellini": rep.cartellini_prob,
            "gol_o25": rep.gol_o25,
            "gol_gg": rep.gol_gg,
            "idea": rep.idea,
            "giocabili": rep.giocabili,
            "fair": {
                "O2.5": round(100 / rep.gol_o25, 2) if rep.gol_o25 > 0 else 0,
                "GG": round(100 / rep.gol_gg, 2) if rep.gol_gg > 0 else 0,
                "1": round(100 / rep.uno, 2) if rep.uno > 0 else 0,
                "X": round(100 / rep.ics, 2) if rep.ics > 0 else 0,
                "2": round(100 / rep.due, 2) if rep.due > 0 else 0,
            },
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
                "dc1x": rep.dc1x, "dc12": rep.dc12, "dcx2": rep.dcx2,
                "ch_o05": rep.casa_o05, "ch_o15": rep.casa_o15,
                "ao_o05": rep.osp_o05, "ao_o15": rep.osp_o15,
                "poss": m.get("possesso"), "tt": m.get("tiri_totali"),
                "xgs": m.get("xg_squadre"),
                "scala_a": rep.scala_angoli, "scala_t": rep.scala_tiri,
                "scala_g": rep.scala_gol, "scala_f": rep.scala_falli,
                "off_tot": rep.off_tot, "off_o35": rep.off_o35,
                "scala_o": rep.scala_off,
                "marcatori": [(mm.nome, mm.squadra, round(mm.prob_gol * 100, 0),
                               mm.rigorista,
                               round(1 / mm.prob_gol, 2) if mm.prob_gol > 0 else 0)
                              for mm in rep.marcatori[:6]],
                "rischio": [(x["nome"], x["squadra"], x["gialli"], x["prob"],
                             x.get("plus"), x.get("quasi"))
                            for x in (m.get("rischio", [])[:4])],
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
