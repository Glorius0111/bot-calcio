"""Provider calendari AUTOMATICI (gratis, no key): sportbusy.com.

Scarica i calendari 2026/27 dei top-5 e prende le partite dei prossimi
giorni (default: da oggi a +3 giorni) con data, ora (ET->CET) e giornata.
I nomi vengono normalizzati a quelli corti del bot.
Niente più file scritti a mano.
"""
import re
import subprocess
import time
from datetime import date, timedelta
from pathlib import Path

from .base import BaseProvider

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache" / "calendari"
CACHE_TTL = 6 * 3600

LEAGUES = {
    "italy": ("serie-a-2026-27", "Serie A"),
    "england": ("premier-league-2026-27", "Premier League 2026/27"),
    "spain": ("la-liga-2026-27", "La Liga 2026/27"),
    "germany": ("bundesliga-2026-27", "Bundesliga 2026/27"),
    "france": ("ligue-1-2026-27", "Ligue 1 2026/27"),
    "portugal": (None, "Liga Portugal 2026/27"),
    "netherlands": (None, "Eredivisie 2026/27"),
    "champions": ("champions-league-2026-27", "Champions League 2026/27"),
    "europa": ("europa-league-2026-27", "Europa League 2026/27"),
}

COPPE = {"champions", "europa"}

NOMI_PT_NL = {
    "FC Porto": "Porto", "SL Benfica": "Benfica", "Sporting CP": "Sporting",
    "Casa Pia AC": "Casa Pia", "CD Santa Clara": "Santa Clara",
    "Moreirense": "Moreirense", "CS Marítimo": "Maritimo", "CS Maritimo": "Maritimo",
    "Gil Vicente FC": "Gil Vicente", "GD Estoril Praia": "Estoril",
    "SC Braga": "Braga", "FC Famalicão": "Famalicao", "FC Famalicao": "Famalicao",
    "CD Nacional": "Nacional", "FC Arouca": "Arouca", "Rio Ave FC": "Rio Ave",
    "FC Alverca": "Alverca", "Academico Viseu": "Ac. Viseu",
    "Vitoria Guimaraes": "Guimaraes", "Vitória Guimarães": "Guimaraes",
    "Sporting Braga": "Braga", "Ajax Amsterdam": "Ajax",
    "Estrela Amadora": "Estrela Amadora", "Gil Vicente": "Gil Vicente",
    "AFC Ajax": "Ajax", "PSV Eindhoven": "PSV", "Feyenoord": "Feyenoord",
    "AZ Alkmaar": "AZ", "FC Twente": "Twente", "FC Utrecht": "Utrecht",
    "NEC Nijmegen": "NEC",
}

MESE_BREVE = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
              "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}


GIORNO_BREVE = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4,
                "Sat": 5, "Sun": 6}


def stato_match(data_iso: str, ora: str, adesso=None) -> str:
    """'live' se in campo ora (kickoff passato da <120 min), 'prossima' o 'finita'."""
    from datetime import datetime as _dt
    try:
        h, mi = (ora or "99:99").split(":")
        kick = _dt.fromisoformat(f"{data_iso}T{h}:{mi}:00")
    except ValueError:
        return "prossima"
    now = adesso
    mins = (now - kick).total_seconds() / 60 if now else 9999
    if 0 <= mins <= 120:
        return "live"
    if mins > 120:
        return "finita"
    return "prossima"


def scarica_risultati(league_key: str, display: str,
                      dal: date, al: date) -> list[dict]:
    """Partite GIOCATE con punteggio da soccerstats results.asp."""
    html = _fetch(f"https://www.soccerstats.com/results.asp?league={league_key}")
    out = []
    pat = re.compile(
        r"<font[^>]*>(Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\d{1,2} [A-Z][a-z]{2})</font>"
        r"</td><td[^>]*>([^<>]+?)&nbsp;</td><td[^>]*>.*?<b>(\d+:\d+)</b>",
        re.S)
    for m in pat.finditer(html):
        try:
            gg, mon = m.group(2).split(" ")
            d = date(2026 if MESE_BREVE[mon] >= 8 else 2027,
                     MESE_BREVE[mon], int(gg))
        except (ValueError, KeyError):
            continue
        if not (dal <= d <= al):
            continue
        # ospite: cella successiva
        seg = html[m.end():m.end() + 300]
        mo = re.search(r"</td><td[^>]*>&nbsp;([^<>]+?)</td>", seg)
        if not mo:
            continue
        out.append({"data": d.isoformat(), "ora": "",
                    "casa": m.group(3).strip(), "trasferta": mo.group(1).strip(),
                    "risultato": m.group(4), "lega": display})
    return out


def scarica_prossime_soccerstats(league_key: str, display: str,
                                 dal: date, al: date) -> list[dict]:
    """Prossime partite da soccerstats latest.asp (righe col punteggio '-')."""
    html = _fetch(f"https://www.soccerstats.com/latest.asp?league={league_key}")
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        if "<b> - </b>" not in tr and "<b>-</b>" not in tr:
            continue  # solo partite non giocate (punteggio '-')
        dm = re.search(r"<font[^>]*>(\d{1,2} [A-Z][a-z]{2})</font>", tr)
        tm = re.search(r"<b>\s*([^<>]+?)\s*</b>\s*-\s*([^<>]+?)\s*</td>", tr)
        if not (dm and tm):
            continue
        try:
            gg, mon = dm.group(1).split(" ")
            mese = MESE_BREVE[mon]
            anno = 2026 if mese >= 8 else 2027
            d = date(anno, mese, int(gg))
        except (ValueError, KeyError):
            continue
        if not (dal <= d <= al):
            continue
        casa = NOMI_PT_NL.get(tm.group(1).strip(), tm.group(1).strip())
        trasf = NOMI_PT_NL.get(tm.group(2).strip(), tm.group(2).strip())
        out.append({"data": d.isoformat(), "ora": "", "casa": casa,
                    "trasferta": trasf, "lega": display, "turno": ""})
    return out

MESE = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5,
        "June": 6, "July": 7, "August": 8, "September": 9, "October": 10,
        "November": 11, "December": 12}

NOMI = {
    "AC Milan": "Milan", "AS Roma": "Roma", "Internazionale": "Inter",
    "AFC Bournemouth": "Bournemouth", "Brighton & Hove Albion": "Brighton",
    "Brighton &amp; Hove Albion": "Brighton",
    "Leeds United": "Leeds", "Manchester City": "Man City",
    "Manchester United": "Man Utd", "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nottm Forest", "Tottenham Hotspur": "Tottenham",
    "Ipswich Town": "Ipswich", "Coventry City": "Coventry",
    "1. FC Köln": "Koln", "1. FC Union Berlin": "Union Berlin",
    "1. FSV Mainz 05": "Mainz", "1899 Hoffenheim": "Hoffenheim",
    "Bayer 04 Leverkusen": "Leverkusen", "Borussia Dortmund": "Dortmund",
    "Borussia Mönchengladbach": "M'gladbach", "Eintracht Frankfurt": "Eintracht Frankfurt",
    "FC Augsburg": "Augsburg", "FC Bayern München": "Bayern",
    "FC Schalke 04": "Schalke", "Hamburger SV": "HSV", "RB Leipzig": "RB Leipzig",
    "SC Freiburg": "Freiburg", "SC Paderborn 07": "Paderborn",
    "SV Elversberg": "Elversberg", "VfB Stuttgart": "Stuttgart",
    "Werder Bremen": "Werder Bremen",
    "Athletic Bilbao": "Athletic Club", "Atlético de Madrid": "Atletico Madrid",
    "Celta de Vigo": "Celta Vigo", "Deportivo Alaves": "Alavés",
    "Deportivo La Coruña": "Deportivo La Coruna", "Elche CF": "Elche",
    "Espanyol": "Espanyol", "FC Barcelona": "Barcelona", "Getafe": "Getafe",
    "Levante UD": "Levante", "Málaga": "Malaga", "Osasuna": "Osasuna",
    "Racing Santander": "Racing Santander", "Rayo Vallecano": "Rayo Vallecano",
    "Real Betis": "Real Betis", "Real Madrid": "Real Madrid",
    "Real Sociedad": "Real Sociedad", "Sevilla": "Sevilla", "Valencia": "Valencia",
    "Villarreal": "Villarreal",
    "AJ Auxerre": "Auxerre", "AS Monaco": "Monaco", "Angers SCO": "Angers",
    "FC Lorient": "Lorient", "Le Havre AC": "Le Havre", "Le Mans FC": "Le Mans",
    "Lille OSC": "Lille", "OGC Nice": "Nice", "Olympique Lyonnais": "Lyon",
    "Olympique Marseille": "Marseille", "Paris FC": "Paris FC",
    "Paris Saint-Germain": "PSG", "RC Lens": "Lens", "RC Strasbourg": "Strasbourg",
    "Stade Brestois 29": "Brest", "Stade Rennais": "Rennes",
    "Toulouse FC": "Toulouse", "Troyes AC": "Troyes",
}

PRI = {"angoli": {"casa_fatti_casa": 5.3, "casa_subiti_casa": 4.6,
                  "ospite_fatti_fuori": 4.8, "ospite_subiti_fuori": 5.0},
       "tiri_in_porta": {"casa_fatti_casa": 4.6, "casa_subiti_casa": 4.0,
                         "ospite_fatti_fuori": 4.2, "ospite_subiti_fuori": 4.4},
       "falli": {"commessi_casa": 12.0, "subiti_casa": 12.0,
                 "commessi_ospite": 12.0, "subiti_ospite": 12.0}}


def _fetch(url: str) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")[-60:]
    f = CACHE_DIR / (safe + ".html")
    import time as _t
    if f.exists() and _t.time() - f.stat().st_mtime < CACHE_TTL:
        return f.read_text(encoding="utf-8", errors="replace")
    time.sleep(2)
    out = subprocess.run(
        ["curl", "-s", "--max-time", "40", "-A", UA, url],
        capture_output=True, timeout=60)
    html = out.stdout.decode("utf-8", errors="replace")
    if len(html) < 50000:
        raise RuntimeError(f"Calendario vuoto: {url}")
    f.write_text(html, encoding="utf-8", errors="replace")
    return html


def _et_a_cet(ora_et: str) -> str:
    """'9:00 AM ET' -> '15:00' (settembre: ET+6)."""
    m = re.match(r"(\d+):(\d+) (AM|PM)", ora_et or "")
    if not m:
        return ""
    h, mi, ap = int(m.group(1)), m.group(2), m.group(3)
    if ap == "PM" and h != 12:
        h += 12
    if ap == "AM" and h == 12:
        h = 0
    return f"{(h + 6) % 24:02d}:{mi}"


def scarica_calendario(slug: str) -> list[dict]:
    """Tutti i match futuri: [{data, ora, casa, trasferta, turno}]."""
    import html as _h
    html = _fetch(f"https://www.sportbusy.com/{slug}")
    html = _h.unescape(html)
    out = []
    # blocchi per data: 'Saturday, September 19, 2026'
    for dm in re.finditer(
            r"((?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day), ([A-Z][a-z]+) (\d+), (\d{4})", html):
        giorno = date(int(dm.group(4)), MESE[dm.group(2)], int(dm.group(3)))
        seg = html[dm.end():dm.end() + 20000]
        seg = seg[:seg.find("day, ") if seg.find("day, ") > 0 else len(seg)]
        for mm in re.finditer(
                r"(\d{1,2}:\d{2} [AP]M ET)</div><div><div[^>]*>(.+?) at (.+?)</div>"
                r"<div[^>]*>(?:Round|Matchweek|Jornada|Spieltag|Journée)?\s*([^<·]*)", seg):
            ora, osp, casa, turno = (mm.group(1), mm.group(2).strip(),
                                     mm.group(3).strip(), mm.group(4).strip())
            out.append({"data": giorno.isoformat(), "ora": _et_a_cet(ora),
                        "trasferta": NOMI.get(osp, osp), "casa": NOMI.get(casa, casa),
                        "turno": turno})
    return out


class AutoFixtureProvider(BaseProvider):
    """Prossime partite (da ieri a +giorni). Zero file manuali."""

    def __init__(self, leghe: list[str] = None, giorni: int = 3,
                 indietro: int = 1, oggi: date = None):
        self.leghe = leghe or ["italy", "england", "spain", "germany", "france",
                               "portugal", "netherlands", "champions", "europa"]
        self.giorni = giorni
        self.indietro = indietro
        self.oggi = oggi or date.today()

    def get_partite(self) -> list[dict]:
        partite = []
        dal = self.oggi - timedelta(days=self.indietro)
        al = self.oggi + timedelta(days=self.giorni)
        try:
            tabellini = self.get_risultati()
        except Exception:
            tabellini = []

        def _norm2(s: str) -> str:
            return re.sub(r"[^a-z]", "", (s or "").lower())

        def cerca_risultato(casa: str, trasf: str, data_iso: str):
            nc, nt = _norm2(casa), _norm2(trasf)
            for r in tabellini:
                if (_norm2(r["casa"]) in (nc, nt) and _norm2(r["trasferta"]) in (nt, nc)
                        and abs((date.fromisoformat(r["data"])
                                 - date.fromisoformat(data_iso)).days) <= 1):
                    if _norm2(r["casa"]) == nc:
                        return r["risultato"]
                    a, b = r["risultato"].split(":")
                    return f"{b}:{a}"
            return ""
        for key in self.leghe:
            slug, display = LEAGUES[key]
            try:
                if slug:
                    cal = scarica_calendario(slug)
                    fx = [f for f in cal
                          if dal <= date.fromisoformat(f["data"]) <= al]
                    base = [{"data": f["data"], "ora": f["ora"], "casa": f["casa"],
                             "trasferta": f["trasferta"], "lega": display,
                             "turno": f.get("turno", "")} for f in fx]
                else:
                    base = scarica_prossime_soccerstats(key, display, dal, al)
            except Exception as e:
                print(f"[CAL] {display}: errore ({e}), salto")
                continue
            n = 0
            from datetime import datetime as _dt
            adesso = _dt.now()
            is_coppa = key in COPPE
            for f in base:
                mturno = re.search(r"(\d+)", f.get("turno", ""))
                gioc = 1 if is_coppa else (max(0, int(mturno.group(1)) - 1) if mturno else 4)
                ris = cerca_risultato(f["casa"], f["trasferta"], f["data"])
                stato = "finita" if ris else stato_match(f["data"], f["ora"], adesso)
                partite.append({
                    "casa": f["casa"], "trasferta": f["trasferta"],
                    "lega": f.get("lega", display), "data": f["data"], "ora": f["ora"],
                    "stato": stato, "risultato": ris,
                    "turno": f.get("turno", ""),
                    "partite_casa": gioc, "partite_trasferta": gioc,
                    "soglia_minima_partite": 6,
                    "soglia_angoli": 8.5, "soglia_tiri": 8.5,
                    "soglia_cartellini": 3.5,
                    "tasso_cartellini": 0.14, "severita_arbitro": 1.0,
                    **{k: dict(v) for k, v in PRI.items()},
                    "marcatori": [],
                    "nota_fonti": ("Calendario automatico + dati REALI 2026/27. "
                                   "NESSUN pronostico finché il campione è < 6."),
                    "motivo_provvisori": ("campione < 6 partite e stagione appena "
                                          "iniziata, nonostante dati squadra reali"),
                    "dati_provvisori": True,
                })
                n += 1
            print(f"[CAL] {display}: {n} partite dal {dal} al {al}")
        return partite

    def get_risultati(self) -> list[dict]:
        """Partite GIOCATE con punteggio (ultimi 2 giorni + oggi)."""
        from .soccerstats import _lega_key
        dal = self.oggi - timedelta(days=2)
        out = []
        for key in self.leghe:
            _, display = LEAGUES[key]
            sskey = {"italy": "italy", "england": "england", "spain": "spain",
                     "germany": "germany", "france": "france",
                     "portugal": "portugal", "netherlands": "netherlands"}.get(key, "")
            if not sskey:
                continue
            try:
                out += scarica_risultati(sskey, display, dal, self.oggi)
            except Exception as e:
                print(f"[RIS] {display}: errore ({e})")
        out.sort(key=lambda x: x["data"])
        print(f"[RIS] {len(out)} risultati dal {dal} al {self.oggi}")
        return out
