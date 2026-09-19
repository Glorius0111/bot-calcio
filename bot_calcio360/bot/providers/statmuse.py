"""Provider StatMuse (gratis, no key): tiri/falli/cartellini/xG REALI 2026/27.

StatMuse risponde in linguaggio naturale e la risposta è nel meta
description della pagina (es. '...have 14.50 fouls committed per match
in the Premier League at home this season.').

Per ogni squadra nel suo contesto (casa/fuori):
  tiri fatti ......... shots on target per game (venue)
  tiri subiti ........ totale 'conceded' / partite giocate (venue)
  falli commessi ..... fouls committed per game (venue)
  falli subiti ....... fouls drawn per game (venue)
  gialli/rossi ....... yellow/red cards per game (venue)
Per marcatore: expected goals per 90 + penalties (rigorista reale).

Cache su disco per query (resume-safe). Ritardo 2s tra chiamate.
"""
import re
import subprocess
import time
import html as _html
import unicodedata
from pathlib import Path

BASE = "https://www.statmuse.com/fc/ask"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache" / "statmuse"
DELAY = 2.0

TEAM_SLUG = {
    "man city": "manchester-city", "man utd": "manchester-united",
    "nottm forest": "nottingham-forest",     "m'gladbach": "borussia-monchengladbach",
    "koln": "fc-koln", "psg": "paris-saint-germain", "hsv": "hamburger-sv",
    "hull city": "hull-city", "ipswich": "ipswich-town", "leeds": "leeds-united",
    "coventry": "coventry-city", "inter": "inter-milan", "milan": "ac-milan",
    "roma": "as-roma", "paris fc": "paris-fc", "rb leipzig": "rb-leipzig",
    "eintracht frankfurt": "eintracht-frankfurt", "freiburg": "sc-freiburg",
    "werder bremen": "werder-bremen", "mainz": "mainz-05", "schalke": "schalke-04",
    "paderborn": "sc-paderborn", "hoffenheim": "tsg-hoffenheim",
    "elversberg": "sv-elversberg", "augsburg": "fc-augsburg",
    "dortmund": "borussia-dortmund", "leverkusen": "bayer-leverkusen",
    "stuttgart": "vfb-stuttgart", "bayern": "bayern-munich",
    "union berlin": "union-berlin", "celta vigo": "celta-vigo",
    "deportivo la coruna": "deportivo-la-coruna", "real betis": "real-betis",
    "athletic club": "athletic-club", "rayo vallecano": "rayo-vallecano",
    "real sociedad": "real-sociedad", "atletico madrid": "atletico-madrid",
    "real madrid": "real-madrid", "sevilla": "sevilla-fc",
}


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()


def slug_team(nome: str) -> str:
    low = _ascii(nome).strip().lower()
    if low in TEAM_SLUG:
        return TEAM_SLUG[low]
    return re.sub(r"[^a-z0-9]+", "-", low).strip("-")


def slug_player(nome: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _ascii(nome).strip().lower()).strip("-")


LEAGUE_HINT = {
    "england": "premier league", "italy": "serie a", "spain": "laliga",
    "germany": "bundesliga", "france": "ligue 1",
    "portugal": "primeira liga", "netherlands": "eredivisie",
    "champions": "champions league", "europa": "europa league",
}


def ask(slug: str, league_hint: str = None) -> tuple[float | None, str]:
    """Ritorna (valore, testo risposta). None se non parsabile o lega sbagliata."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / (re.sub(r"[^a-z0-9-]+", "_", slug).strip("_")[:100] + ".txt")
    if f.exists():
        raw = f.read_text(encoding="utf-8", errors="replace")
    else:
        time.sleep(DELAY)
        out = subprocess.run(
            ["curl", "-s", "--max-time", "30", "-A", UA, f"{BASE}/{slug}"],
            capture_output=True, timeout=60)
        page = out.stdout.decode("utf-8", errors="replace")
        m = re.search(r'<meta name="description" content="([^"]*)"', page)
        raw = _html.unescape(m.group(1)) if m else ""
        f.write_text(raw, encoding="utf-8", errors="replace")
    if not raw or "0 games" in raw or "no games" in raw.lower():
        return None, raw
    if "couldn't find" in raw.lower() or "instant answers to your" in raw.lower():
        return None, raw
    if league_hint and league_hint not in raw.lower():
        return None, raw  # squadra sbagliata (es. Inter Miami invece di Inter)
    m = re.search(r"(?:have|has|had|tallied) ([\d.]+) ", raw)
    if not m:
        return None, raw
    try:
        return float(m.group(1)), raw
    except (TypeError, ValueError):
        return None, raw


def hint_for_lega(lega_display: str) -> str:
    """Hint di competizione dal nome visualizzato (evita lega sbagliata)."""
    low = (lega_display or "").lower()
    if "champions" in low:
        return "champions league"
    if "europa" in low:
        return "europa league"
    from .soccerstats import _lega_key
    return LEAGUE_HINT.get(_lega_key(lega_display), "")


def team_enrich(squadra: str, venue: str, giocate: int,
                lega_key: str = None, hint: str = None) -> dict:
    """venue: 'home' o 'away'. Ritorna dict con valori reali o None."""
    ven_q = "at-home" if venue == "home" else "away"
    ven_d = "at-home" if venue == "home" else "on-the-road"
    hint = hint or LEAGUE_HINT.get(lega_key or "")
    t = slug_team(squadra)
    out: dict = {"squadra": squadra}

    def q(template: str):
        v, _ = ask(template.format(t=t), league_hint=hint)
        return v

    out["sot_for"] = q(f"{{t}}-shots-on-target-per-game-{ven_q}-this-season")
    out["sot_against"] = None
    v, _ = ask(f"how-many-shots-on-target-have-{t}-conceded-{ven_d}-this-season",
               league_hint=hint)
    if v is not None and giocate > 0:
        out["sot_against"] = round(v / giocate, 2)
    out["fouls_for"] = q(f"{{t}}-fouls-per-game-{ven_q}-this-season")
    out["fouls_drawn"] = q(f"{{t}}-fouls-drawn-per-game-{ven_q}-this-season")
    out["yc"] = q(f"{{t}}-yellow-cards-per-game-{ven_q}-this-season")
    out["rc"] = q(f"{{t}}-red-cards-per-game-{ven_q}-this-season")
    out["xg"] = q(f"{{t}}-expected-goals-per-game-{ven_q}-this-season")
    out["off_for"] = q(f"{{t}}-offsides-per-game-{ven_q}-this-season")
    out["poss"] = q(f"{{t}}-possession-per-game-{ven_q}-this-season")
    out["shots"] = q(f"{{t}}-shots-per-game-{ven_q}-this-season")
    return out


def player_enrich(nome: str, lega_key: str = None, hint: str = None) -> dict:
    """xG per 90 + rigori reali del giocatore."""
    if not nome or len(nome.strip()) < 3 or nome.strip().lower() in ("n/a", "unknown"):
        return {"xg_per90": None, "penalties": None}
    p = slug_player(nome)
    hint = hint or LEAGUE_HINT.get(lega_key or "")
    xg, _ = ask(f"{p}-expected-goals-per-90-this-season", league_hint=hint)
    pen, _ = ask(f"{p}-penalties-scored-this-season", league_hint=hint)
    return {"xg_per90": xg, "penalties": pen}


def _num(v, default: float) -> float:
    return v if isinstance(v, (int, float)) else default


def enrich_full(partite: list[dict], lega_key: str = None,
                hint: str = None) -> dict:
    """Riempie tiri/falli/cartellini/marcatori con valori REALI 2026/27.

    Ritorna {'tiri_reali': n, 'falli_reali': n, 'xg_reali': n, 'totali': n}.
    I campi mancanti restano alle medie di lega (dichiarato in nota).
    """
    rep = {"tiri_reali": 0, "falli_reali": 0, "xg_reali": 0,
           "totali": len(partite)}
    for m in partite:
        gh = _num(m.get("partite_casa", 0), 0)
        ga = _num(m.get("partite_trasferta", 0), 0)
        h = team_enrich(m["casa"], "home", int(gh), lega_key, hint)
        a = team_enrich(m["trasferta"], "away", int(ga), lega_key, hint)

        t_ok = (h["sot_for"] is not None and a["sot_for"] is not None
                and h["sot_against"] is not None and a["sot_against"] is not None)
        f_ok = (h["fouls_for"] is not None and a["fouls_for"] is not None
                and h["fouls_drawn"] is not None and a["fouls_drawn"] is not None)

        t = m.setdefault("tiri_in_porta", {})
        if t_ok:
            t["casa_fatti_casa"] = round(h["sot_for"], 2)
            t["ospite_fatti_fuori"] = round(a["sot_for"], 2)
            t["casa_subiti_casa"] = h["sot_against"]
            t["ospite_subiti_fuori"] = a["sot_against"]
            rep["tiri_reali"] += 1

        f = m.setdefault("falli", {})
        if f_ok:
            f["commessi_casa"] = round(h["fouls_for"], 1)
            f["commessi_ospite"] = round(a["fouls_for"], 1)
            f["subiti_casa"] = round(h["fouls_drawn"], 1)
            f["subiti_ospite"] = round(a["fouls_drawn"], 1)
            rep["falli_reali"] += 1

        if h.get("yc") is not None and a.get("yc") is not None:
            yc_h = round(h["yc"] + (h.get("rc") or 0), 2)
            yc_a = round(a["yc"] + (a.get("rc") or 0), 2)
            m["nota_cartellini"] = (f"{m['casa']} {yc_h}/gara, "
                                    f"{m['trasferta']} {yc_a}/gara")

        if h.get("off_for") is not None and a.get("off_for") is not None:
            m["fuorigioco"] = {
                "casa_fatti_casa": round(h["off_for"], 2),
                "casa_subiti_casa": round(a["off_for"], 2),
                "ospite_fatti_fuori": round(a["off_for"], 2),
                "ospite_subiti_fuori": round(h["off_for"], 2)}

        if h.get("poss") is not None and a.get("poss") is not None:
            def _pct(v):
                v = round(v, 1)
                return round(v * 100, 1) if v < 1 else v  # 0.32 -> 32%
            m["possesso"] = {"casa": _pct(h["poss"]),
                             "ospite": _pct(a["poss"])}
        if h.get("shots") is not None and a.get("shots") is not None:
            m["tiri_totali"] = {"casa": round(h["shots"], 1),
                                "ospite": round(a["shots"], 1)}
        if h.get("xg") is not None and a.get("xg") is not None:
            m["xg_squadre"] = {"casa": round(h["xg"], 2),
                               "ospite": round(a["xg"], 2)}

        for g in m.get("marcatori", []):
            pe = player_enrich(g["nome"], lega_key, hint)
            if pe["xg_per90"] is not None:
                g["xg_per90"] = pe["xg_per90"]
                g["_xgr"] = True
                rep["xg_reali"] += 1
            # altrimenti resta la stima da gol reali (soccerstats)
            if pe["penalties"] is not None and pe["penalties"] >= 1:
                g["rigorista"] = True

        reali = ["angoli", "gol", "giocate"]
        stime = []
        reali.append("tiri") if t_ok else stime.append("tiri")
        reali.append("falli") if f_ok else stime.append("falli")
        if any(mm.get("_xgr") for mm in m.get("marcatori", [])):
            reali.append("marcatori-xG")
        elif m.get("marcatori"):
            stime.append("xG (stima da gol)")
        m["nota_fonti"] = ("REALI 2026/27: " + ", ".join(reali)
                           + (". STIME (medie lega): " + ", ".join(stime) + "." if stime else ".")
                           + " NESSUN pronostico finché il campione è < 6 partite.")
        m["motivo_provvisori"] = ("campione < 6 partite e stagione appena iniziata, "
                                  "nonostante dati squadra reali")
        m["dati_provvisori"] = True
    return rep
