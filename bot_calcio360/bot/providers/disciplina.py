"""Cartellini giocatori: chi rischia l'ammonizione (dati REALI 2026/27).

Fonte: Statbunker TopYellowCards per i top-5 (gialli totali + split casa/trasferta).
Probabilità ammonizione (stima onesta): P = 1 - exp(-gialli_luogo / partite_luogo).
"""
import math
import re
import subprocess
import time
from pathlib import Path

from .soccerstats import norm

BASE = "https://www.statbunker.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache" / "disciplina"
CACHE_TTL = 12 * 3600

COMP_IDS = {"england": 791, "spain": 792, "italy": 797,
            "germany": 798, "france": 796}


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
    if len(html) < 20000:
        raise RuntimeError(f"Statbunker vuoto: {url}")
    f.write_text(html, encoding="utf-8", errors="replace")
    return html


def scarica_gialli(lega_key: str) -> dict:
    """{norm_team: [(nome, tot, home, away), ...] ordinati per tot desc}."""
    comp = COMP_IDS.get(lega_key or "")
    if not comp:
        return {}
    html = _fetch(f"{BASE}/competitions/TopYellowCards?comp_id={comp}")
    out: dict = {}
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = [re.sub(r"<[^>]+>", "", c).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
        cells = [c for c in cells if c]
        if len(cells) < 5:
            continue
        def _n(x: str) -> int:
            try:
                return int(x)
            except ValueError:
                return 0
        tot, hm, aw = _n(cells[2]), _n(cells[3]), _n(cells[4])
        out.setdefault(norm(cells[1]), []).append((cells[0], tot, hm, aw))
    for v in out.values():
        v.sort(key=lambda x: x[1], reverse=True)
    return out


def _trova(tab: dict, squadra: str):
    n = norm(squadra)
    if n in tab:
        return tab[n]
    for k, v in tab.items():
        if n and (n in k or k in n):
            return v
    return []


def rischio_partita(casa: str, trasferta: str, gialli: dict,
                    giocate_casa: int, giocate_osp: int) -> list[dict]:
    """Top a rischio per parte: [{nome, squadra, yc, prob}]."""
    out = []
    for squadra, cand, gioc, idx in (
            (casa, _trova(gialli, casa), max(1, giocate_casa), 2),
            (trasferta, _trova(gialli, trasferta), max(1, giocate_osp), 3)):
        if not cand:
            continue
        best = max(cand[:6], key=lambda x: x[idx])
        yc = best[idx]
        prob = round((1 - math.exp(-yc / gioc)) * 100, 1)
        out.append({"nome": best[0], "squadra": squadra,
                    "gialli": yc, "prob": prob})
    out.sort(key=lambda x: x["prob"], reverse=True)
    return out
