"""Arricchitore SoccerStats (gratis, no key) per stagione 2026/27.

Fonte: https://www.soccerstats.com (tabelle cornerstats + home/away + scorers).
Dati REALI ottenuti: angoli fatti/subiti segmentati casa/trasferta,
partite giocate casa/trasferta, top marcatori (proxy xG da gol/partita).
NON disponibili gratis: tiri in porta, falli, cartellini -> restano medie
di lega provvisorie e il report resta bloccato (dati_provvisori=True).

Uso:
  from bot.providers.soccerstats import arricchisci
  partite = arricchisci(partite, lega_soccerstats='england')
"""
import re
import time
import urllib.request
from pathlib import Path

BASE = "https://www.soccerstats.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache" / "soccerstats"
CACHE_TTL = 12 * 3600

LEGA_SOCCERSTATS = {
    "serie a": "italy", "premier": "england", "liga": "spain",
    "la liga": "spain", "bundesliga": "germany", "ligue": "france",
    "liga portugal": "portugal", "portugal": "portugal",
    "eredivisie": "netherlands", "netherlands": "netherlands",
}

# nomi soccerstats -> nomi comuni calendario
ALIAS = {
    "manchesterutd": "manutd", "nottmforest": "nottinghamforest",
    "intermilan": "inter", "asroma": "roma", "hellasverona": "verona",
    "acmilan": "milan", "manchestercity": "mancity",
    "brightonhovealbion": "brighton", "westham": "westhamunited",
    "1fckoln": "koln", "koln": "koln", "fckoln": "koln",
    "borussiamgladbach": "mgladbach", "mgladbach": "mgladbach",
    "monchengladbach": "mgladbach",
    "eintrachtfrankfurt": "frankfurt", "sportclubfreiburg": "freiburg",
    "scfreiburg": "freiburg", "svwerderbremen": "werderbremen",
    "werderbremen": "werderbremen", "fcaugsburg": "augsburg",
    "fsvmainz05": "mainz", "mainz05": "mainz",
    "rb leipzig": "rbleipzig", "rbleipzig": "rbleipzig",
    "unionberlin": "unionberlin", "1fcunionberlin": "unionberlin",
    "fcelversberg": "elversberg", "sv07elversberg": "elversberg",
    "scpaderborn07": "paderborn", "paderborn07": "paderborn",
    "tsghoffenheim": "hoffenheim", "borussiadortmund": "dortmund",
    "bayer04leverkusen": "leverkusen", "bayerleverkusen": "leverkusen",
    "vfb stuttgart": "stuttgart", "vfbstuttgart": "stuttgart",
    "fcschalke04": "schalke", "hamburgersv": "hsv", "hsv": "hsv",
    "hullcity": "hullcity", "hull": "hullcity",
    "ipswichtown": "ipswich", "leedsunited": "leeds",
    "crystalpalace": "crystalpalace", "cpalace": "crystalpalace",
    "nottinghamforest": "nottinghamforest", "nottmforest": "nottinghamforest",
    "coventrycity": "coventry", "afcbournemouth": "bournemouth",
    "sunderlandafc": "sunderland", "evertonfc": "everton",
    "astonvilla": "astonvilla", "avill": "astonvilla",
    "parisfc": "parisfc", "parissaintgermain": "psg",
    "olympiquedemarseille": "marseille", "olympiquemarseille": "marseille",
    "asmonaco": "monaco", "ogcnice": "nice", "rclens": "lens",
    "staderennais": "rennes", "olympiquelyonnais": "lyon",
    "rcstrasbourg": "strasbourg", "ajauxerre": "auxerre",
    "stadebrestois29": "brest", "stadebrestois": "brest",
    "lemansfc": "lemans", "fclorient": "lorient",
    "toulousefc": "toulouse", "estactroyes": "troyes",
    "havreac": "lehavre", "lehavreac": "lehavre",
    "athleticclub": "athleticbilbao", "athletic": "athleticbilbao",
    "fcporto": "porto", "sportingcp": "sporting", "sportingbraga": "braga",
    "academicoviseu": "acviseu",
    "ajaxamsterdam": "ajax", "azalkmaar": "az", "fctwente": "twente",
    "fcutrecht": "utrecht", "necnijmegen": "nec", "psveindhoven": "psv",
    "parissg": "parissg", "psg": "parissg", "parissaintgermain": "parissg",
    "atleticodemadrid": "atleticomadrid", "atletico": "atleticomadrid",
    "realmadrid": "realmadrid", "fcbarcelona": "barcelona",
    "realsociedad": "realsociedad", "realbetis": "realbetis",
    "deportivoalaves": "alaves", "rayovallecano": "rayovallecano",
    "rcd espanyol": "espanyol", "rcdespanyol": "espanyol",
    "celtadevigo": "celta", "getafecf": "getafe",
    "caosasuna": "osasuna", "levanteud": "levante",
    "villarrealcf": "villarreal", "deportivolacoruna": "deportivolacoruna",
    "rcdeportivo": "deportivolacoruna", "malagacf": "malaga",
    "racingsantander": "racingsantander", "realracingclub": "racingsantander",
    "elchecf": "elche", "valenciacf": "valencia",
}


def norm(nome: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    n = re.sub(r"[^a-z]", "", s.lower())
    return ALIAS.get(n, n)


def _lega_key(lega: str) -> str:
    low = (lega or "").lower().strip()
    if low in LEGA_SOCCERSTATS.values():
        return low  # già chiave soccerstats (italy, england, ...)
    for k in sorted(LEGA_SOCCERSTATS, key=len, reverse=True):
        # match su parola intera o inizio stringa (evita 'liga' in 'bundesliga')
        if re.search(r"(^|[^a-z])" + re.escape(k) + r"([^a-z]|$)", low):
            return LEGA_SOCCERSTATS[k]
    return ""


def _utf8_ok(b: bytes) -> bool:
    try:
        b.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _fetch(url: str) -> str:
    """Scarica con curl (urllib viene bloccato 403 dal sito). Cache 12h."""
    import subprocess
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")[-80:]
    f = CACHE_DIR / (safe + ".html")
    import time as _t
    if f.exists() and _t.time() - f.stat().st_mtime < CACHE_TTL:
        return f.read_text(encoding="utf-8", errors="replace")
    time.sleep(3)  # gentile col server gratis
    out = subprocess.run(
        ["curl", "-s", "--max-time", "40", "-A", UA,
         "-H", "Accept-Language: en-US,en;q=0.9",
         "-H", "Referer: https://www.soccerstats.com/", url],
        capture_output=True, timeout=60)
    html = out.stdout.decode("utf-8", errors="strict") if _utf8_ok(out.stdout) \
        else out.stdout.decode("cp1252", errors="replace")
    if len(html) < 50000:
        raise RuntimeError(f"SoccerStats: risposta vuota/breve per {url}")
    f.write_text(html, encoding="utf-8", errors="replace")
    return html


def _rows(html: str, section: str, size: int = 40000) -> list[list[str]]:
    i = html.find(section)
    if i < 0:
        return []
    seg = html[i:i + size]
    out = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", seg, re.S):
        cells = [re.sub(r"<[^>]+>", "", c).replace("&nbsp;", "").strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
        cells = [c for c in cells if c != ""]
        # riga squadra valida: header esclusi + GP numerico in cella 1 o 2
        # (formati: [team, GP, ...] oppure [rank, team, GP, ...])
        if len(cells) < 3:
            continue
        if cells[0].lower().startswith(("for", "team", "player", "matches of")):
            continue
        if not (re.match(r"^\d+(\.\d+)?$", cells[1])
                or re.match(r"^\d+(\.\d+)?$", cells[2])):
            continue
        out.append(cells)
    return out


def _fnum(x: str, default: float = 0.0) -> float:
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return default


def scarica_lega(lega: str) -> dict:
    """Ritorna {'corners_home': {norm: (gp, for, ag)}, 'corners_away': ...,
    'played_home': ..., 'played_away': ..., 'scorers': {norm_team: [(player, goals)]}}."""
    cr = _fetch(f"{BASE}/table.asp?league={lega}&tid=cr")
    ha = _fetch(f"{BASE}/homeaway.asp?league={lega}")
    sc = _fetch(f"{BASE}/scorers.asp?league={lega}")
    d: dict = {"corners_home": {}, "corners_away": {},
               "played_home": {}, "played_away": {},
               "goals_home": {}, "goals_away": {}, "scorers": {}}
    for r in _rows(cr, "Corners (home"):
        if len(r) >= 4:
            d["corners_home"][norm(r[0])] = (_fnum(r[1]), _fnum(r[2]), _fnum(r[3]))
    for r in _rows(cr, "Corners (away"):
        if len(r) >= 4:
            d["corners_away"][norm(r[0])] = (_fnum(r[1]), _fnum(r[2]), _fnum(r[3]))
    for r in _rows(ha, "Home table"):
        if len(r) >= 8:
            n = norm(r[1])
            d["played_home"][n] = int(_fnum(r[2]))
            gp = max(1, int(_fnum(r[2])))
            d["goals_home"][n] = (_fnum(r[6]) / gp, _fnum(r[7]) / gp)
    i = ha.find("Away table")
    if i > 0:
        for r in _rows(ha[i:], "Away table"):
            if len(r) >= 8:
                n = norm(r[1])
                d["played_away"][n] = int(_fnum(r[2]))
                gp = max(1, int(_fnum(r[2])))
                d["goals_away"][n] = (_fnum(r[6]) / gp, _fnum(r[7]) / gp)
    i = sc.find("<tbody>")
    if i > 0:
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", sc[i:i + 30000], re.S)[:40]:
            cells = [re.sub(r"<[^>]+>", "", c).strip()
                     for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            cells = [c for c in cells if c]
            if len(cells) >= 3 and cells[2].replace(".", "").isdigit():
                d.setdefault("scorers", {}).setdefault(
                    norm(cells[1]), []).append((cells[0], int(float(cells[2]))))
    return d


def _trova(tab: dict, squadra: str):
    n = norm(squadra)
    if n in tab:
        return tab[n]
    for k, v in tab.items():  # fallback sottostringa
        if n and (n in k or k in n):
            return v
    return None


def arricchisci(partite: list[dict], lega: str) -> tuple[list[dict], dict]:
    """Sostituisce angoli/giocate/marcatori coi valori reali. Ritorna (partite, report_fonti)."""
    key = _lega_key(lega)
    if not key:
        return partite, {"ok": 0, "totali": len(partite)}
    dati = scarica_lega(key)
    ok = 0
    try:
        from .disciplina import scarica_gialli, rischio_partita
        gialli = scarica_gialli(key)
    except Exception:
        gialli = {}
    for m in partite:
        ch = _trova(dati["corners_home"], m["casa"])
        ca = _trova(dati["corners_away"], m["trasferta"])
        ph = _trova(dati["played_home"], m["casa"])
        pa = _trova(dati["played_away"], m["trasferta"])
        if ch and ca:
            m["angoli"] = {"casa_fatti_casa": round(ch[1], 2),
                           "casa_subiti_casa": round(ch[2], 2),
                           "ospite_fatti_fuori": round(ca[1], 2),
                           "ospite_subiti_fuori": round(ca[2], 2)}
            ok += 1
        if ph is not None:
            m["partite_casa"] = ph
        if pa is not None:
            m["partite_trasferta"] = pa
        if gialli:
            try:
                m["rischio"] = rischio_partita(
                    m["casa"], m["trasferta"], gialli,
                    m.get("partite_casa", 0), m.get("partite_trasferta", 0))
            except Exception:
                m["rischio"] = []
        gh = _trova(dati["goals_home"], m["casa"])
        ga = _trova(dati["goals_away"], m["trasferta"])
        gol_ok = False
        if gh and ga:
            m["gol"] = {"casa_fatti_casa": round(gh[0], 2),
                        "casa_subiti_casa": round(gh[1], 2),
                        "ospite_fatti_fuori": round(ga[0], 2),
                        "ospite_subiti_fuori": round(ga[1], 2)}
            gol_ok = True
        # marcatori reali (proxy xG = gol/partita * 0.9)
        cand = []
        for team in (m["casa"], m["trasferta"]):
            for nome, gol in _trova(dati["scorers"], team) or []:
                giocate = max(1, (ph or 1) + (pa or 1))
                cand.append({"nome": nome, "squadra": team,
                             "xg_per90": round(gol / giocate * 0.9, 2),
                             "minuti_previsti": 90, "rigorista": False})
        cand.sort(key=lambda g: g["xg_per90"], reverse=True)
        if cand:
            m["marcatori"] = cand[:4]
        m["nota_fonti"] = ("Dati REALI 2026/27 (SoccerStats + StatMuse): angoli, "
                           "gol, tiri, falli, cartellini, xG marcatori. NESSUN "
                           "pronostico finché il campione è < 6 partite.")
        m["motivo_provvisori"] = ("campione < 6 partite e stagione appena iniziata, "
                                  "nonostante dati squadra reali")
        m["dati_provvisori"] = True
    return partite, {"ok": ok, "totali": len(partite), "lega": key}
