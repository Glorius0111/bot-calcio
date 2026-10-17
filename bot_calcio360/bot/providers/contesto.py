"""Occhio dell'esperto: forma recente + precedenti H2H + accordo col modello.

Fonte: Statbunker UpcomingMatches (form ultima 3 + incroci diretti).
Regola dichiarata (contesto + modello, NON cambia le probabilità):
  CONSIGLIATA se contesto >= +1 E modello pro-casa (gol attesi casa-ospite >= +0.5),
    oppure contesto molto forte da solo (>= +3);
  EVITARE se contesto <= -1 E modello contro la casa (<= -0.3),
    oppure contesto molto contro da solo (<= -3);
  altrimenti NEUTRA.
Assenze/infortuni: non pubblicati gratis in forma leggibile -> non inventati.
"""
import re
import subprocess
import time
from pathlib import Path

from .soccerstats import norm

BASE = "https://www.statbunker.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache" / "contesto"
CACHE_TTL = 12 * 3600

COMP_IDS = {"england": 791, "spain": 792, "france": 796,
            "italy": 797, "germany": 798}


def _fetch(url: str) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")[-60:]
    f = CACHE_DIR / (safe + ".html")
    import time as _t
    if f.exists() and _t.time() - f.stat().st_mtime < CACHE_TTL:
        return f.read_text(encoding="utf-8", errors="replace")
    html = ""
    for tent in range(3):
        time.sleep(2 + tent * 5)
        try:
            out = subprocess.run(
                ["curl", "-s", "--max-time", "100", "-A", UA, url],
                capture_output=True, timeout=130)
            html = out.stdout.decode("utf-8", errors="replace")
            if len(html) >= 20000:
                break
        except Exception:
            html = ""
    if len(html) < 20000:
        raise RuntimeError(f"Statbunker vuoto dopo retry: {url}")
    f.write_text(html, encoding="utf-8", errors="replace")
    return html


def _lettere(segmento: str, n: int = 3) -> str:
    spans = re.findall(r'class="([wdl])">([WDL])<', segmento)
    return "".join(s[1] for s in spans[:n])


def scarica_contesto(lega_key: str) -> dict:
    """{(norm_casa, norm_ospite): {forma_casa, forma_osp, h2h, wh, lh}}."""
    comp = COMP_IDS.get(lega_key or "")
    if not comp:
        return {}
    html = _fetch(f"{BASE}/competitions/UpcomingMatches?comp_id={comp}")
    out = {}
    chunks = re.split(r'<span class="matchTeam">', html)[1:]
    i = 0
    while i + 1 < len(chunks):
        casa = re.search(r"<p>([^<>]+)</p>", chunks[i])
        osp = re.search(r"<p>([^<>]+)</p>", chunks[i + 1])
        # tutto ciò che segue la squadra ospite (orario + statistiche)
        seg = chunks[i + 1][:12000]
        i += 2
        if not (casa and osp):
            continue
        mh = re.search(r"Home Form(.*?)</li>", seg, re.S)
        ma = re.search(r"Away Form(.*?)</li>", seg, re.S)
        forma_c = _lettere(mh.group(1)) if mh else ""
        forma_o = _lettere(ma.group(1)) if ma else ""
        # H2H: voci "<li>Vs avversario ..." (i title="Vs ..." interni non contano)
        h2h_letters = []
        for hm in re.finditer(r"<li>\s*Vs [A-Za-z][^<>]{1,40}", seg):
            tail = seg[hm.end():hm.end() + 2500]
            tail = tail[:tail.find("</li>") if "</li>" in tail else len(tail)]
            h2h_letters += re.findall(r'class="([wdl])">([WDL])<', tail)
            if len(h2h_letters) >= 5:
                break
        h2h = "".join(s[1] for s in h2h_letters[:5])
        wh, lh = h2h.count("W"), h2h.count("L")
        out[(norm(casa.group(1)), norm(osp.group(1)))] = {
            "forma_casa": forma_c, "forma_osp": forma_o,
            "h2h": h2h or "-", "wh": wh, "lh": lh}
    return out


def _trova(tab: dict, casa: str, trasf: str):
    import re as _re

    def _n(s):
        return norm(s)
    nc, nt = _n(casa), _n(trasf)
    if (nc, nt) in tab:
        return tab[(nc, nt)]
    for (kc, kt), v in tab.items():
        if nc and nt and ((nc in kc or kc in nc) and (nt in kt or kt in nt)):
            return v
    return None


def contesto_partita(casa: str, trasferta: str, tab: dict,
                     diff_attesi: float = 0.0) -> dict:
    """Fatti + semaforo. Regola dichiarata (contesto + modello):
    CONSIGLIATA se contesto >= +1 E modello pro-casa (diff attesi >= +0.2),
      oppure contesto forte da solo (>= +2);
    EVITARE se contesto <= -1 E modello contro la casa (diff <= -0.2),
      oppure contesto molto contro (<= -2);
    altrimenti NEUTRA. Senza dati: NEUTRA spiegata."""
    c = _trova(tab, casa, trasferta)
    if not c:
        return {"forma_casa": "", "forma_osp": "", "h2h": "-",
                "semaforo": "NEUTRA",
                "note": ["Precedenti non disponibili gratis per questa lega."]}
    wh_f = c["forma_casa"].count("W")
    wa_f = c["forma_osp"].count("W")
    punteggio = (wh_f - wa_f) + (c["wh"] - c["lh"])
    note = []
    if c["forma_casa"]:
        note.append(f"{casa} in forma: {c['forma_casa']} nelle ultime 3.")
    if c["forma_osp"]:
        note.append(f"{trasferta} in forma: {c['forma_osp']} nelle ultime 3.")
    if c["h2h"] != "-":
        note.append(f"Ultimi incroci: {c['h2h']} (vittorie casa {c['wh']}, ospite {c['lh']}).")
    if punteggio >= 2 or (punteggio >= 1 and diff_attesi >= 0.2):
        sem = "CONSIGLIATA"
        note.append("Contesto e modello concordano per la casa.")
    elif punteggio <= -2 or (punteggio <= -1 and diff_attesi <= -0.2):
        sem = "EVITARE"
        note.append("Contesto e modello contro la casa: meglio evitare.")
    else:
        sem = "NEUTRA"
        note.append("Contesto equilibrato: vale solo il modello.")
    return {"forma_casa": c["forma_casa"], "forma_osp": c["forma_osp"],
            "h2h": c["h2h"], "semaforo": sem, "note": note}
