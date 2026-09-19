"""Provider REALE multilega: API-Football (api-sports.io).
https://v3.football.api-sports.io

- Supporta più campionati insieme: leagues=[135,39,140,78,61]
  135=Serie A, 39=Premier, 140=Liga, 78=Bundesliga, 61=Ligue 1, 2=Champions
- Cache locale 7 giorni per non bruciare i 100 req/giorno del piano free
- Carica key da .env (API_FOOTBALL_KEY=...) o env var
- Marcatori: stima da top scorers (goals -> xG proxy), rigorista se penalties>30% gol

Costo stimato primo giro: ~1 fixture/league + 1 topscorer/league + N squadre nuove.
Giri successivi: solo fixtures (1/league) grazie alla cache.
"""
import json
import os
import time
import urllib.request
from pathlib import Path
from .base import BaseProvider

BASE_URL = "https://v3.football.api-sports.io"
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache"
CACHE_TTL = 7 * 24 * 3600

LEAGUES_DEFAULT = {
    135: "Serie A", 39: "Premier League", 140: "Liga",
    78: "Bundesliga", 61: "Ligue 1",
}


def load_env_dotenv():
    """Carica API_FOOTBALL_KEY da bot_calcio360/.env senza dipendenze."""
    for p in [Path.cwd() / ".env",
              Path(__file__).resolve().parent.parent.parent / ".env"]:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("API_FOOTBALL_KEY=") and "API_FOOTBALL_KEY" not in os.environ:
                    os.environ["API_FOOTBALL_KEY"] = line.split("=", 1)[1].strip().strip("'\"")


CALLS = {"n": 0}


def _get(path: str, key: str, params: dict = None, retries: int = 4) -> dict:
    """GET con throttle + retry su 429 (piano free: max ~10 req/min)."""
    import urllib.error
    from urllib.parse import urlencode
    url = BASE_URL + path
    if params:
        url += "?" + urlencode({k: v for k, v in params.items() if v is not None})
    last_err = None
    for tent in range(retries):
        try:
            # throttle base: 7s tra chiamate (~8/min, sicuro per free)
            time.sleep(7)
            req = urllib.request.Request(url, headers={"x-apisports-key": key})
            with urllib.request.urlopen(req, timeout=30) as r:
                CALLS["n"] += 1
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                time.sleep(65)  # quota/minuto esaurita: aspetta 1 min e riprova
                continue
            raise
    raise last_err


class QuotaStop(Exception):
    """Alzato quando si raggiunge il budget chiamate giornaliero."""


def _stat(stat_list: list, name: str) -> float:
    for s in (stat_list or []):
        if s.get("type") == name:
            try:
                v = s.get("value")
                return float(v) if v is not None else 0.0
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _cache_get(name: str):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / f"{name}.json"
    if f.exists() and time.time() - f.stat().st_mtime < CACHE_TTL:
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _cache_set(name: str, data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")


class ApiFootballProvider(BaseProvider):
    def __init__(self, leagues: list[int] | int = 135, season: int = 2025,
                 round_name: str = None, ultime_n: int = 6, key: str = None,
                 max_partite_per_league: int = 10, max_calls: int = 90):
        load_env_dotenv()
        if isinstance(leagues, int):
            leagues = [leagues]
        self.leagues = leagues
        self.season = season
        self.round_name = round_name
        self.ultime_n = ultime_n
        self.key = (key or os.getenv("API_FOOTBALL_KEY", "")).strip()
        self.max_partite = max_partite_per_league
        self.max_calls = max_calls

    def _budget_ok(self) -> bool:
        return CALLS["n"] < self.max_calls

    def check_key(self) -> dict:
        """Test rapido: 1 sola chiamata a /status (conta nel quota)."""
        if not self.key:
            raise RuntimeError("Manca API_FOOTBALL_KEY")
        return _get("/status", self.key)

    def _team_avg(self, league: int, team_id: int, home_away: str) -> dict:
        ck = f"team_{league}_{team_id}_{home_away}_n{self.ultime_n}"
        hit = _cache_get(ck)
        # invalida cache vuota precedente (bug parametro last su free)
        if hit and hit.get("n", 0) > 0:
            return hit
        # FREE: niente parametro 'last' (bloccato) -> prendi tutte (38) e filtra in locale
        data = _get("/fixtures", self.key, {
            "league": league, "season": self.season, "team": team_id})
        all_fx = data.get("response", [])
        # solo finite (FT/AET/PEN) con data passata, ordinate dalla più recente
        done = [f for f in all_fx
                if f.get("fixture", {}).get("status", {}).get("short") in ("FT", "AET", "PEN")]
        done.sort(key=lambda f: f["fixture"]["date"], reverse=True)
        sel = [f for f in done
               if (home_away == "home" and f["teams"]["home"]["id"] == team_id)
               or (home_away == "away" and f["teams"]["away"]["id"] == team_id)]
        fixtures = sel[:self.ultime_n]
        if not fixtures:
            d = {"corners_f": 5.0, "corners_a": 5.0, "sog_f": 4.5,
                 "sog_a": 4.5, "fouls_c": 12.0, "fouls_s": 12.0, "n": 0}
            _cache_set(ck, d)
            return d
        c_f = c_a = s_f = s_a = f_c = f_s = 0.0
        valid = 0
        for fx in fixtures:
            if not self._budget_ok():
                break  # budget finito: usa quel che hai, il resto domani (cache)
            try:
                sd = _get("/fixtures/statistics", self.key,
                          {"fixture": fx["fixture"]["id"]})
            except Exception:
                continue
            me = opp = None
            for t in sd.get("response", []):
                if t["team"]["id"] == team_id:
                    me = t["statistics"]
                else:
                    opp = t["statistics"]
            if not me:
                continue
            c_f += _stat(me, "Corner Kicks"); c_a += _stat(opp, "Corner Kicks")
            s_f += _stat(me, "Shots on Goal"); s_a += _stat(opp, "Shots on Goal")
            f_c += _stat(me, "Fouls"); f_s += _stat(opp, "Fouls")
            valid += 1
        d = {"corners_f": round(c_f / valid, 2) if valid else 5.0,
             "corners_a": round(c_a / valid, 2) if valid else 5.0,
             "sog_f": round(s_f / valid, 2) if valid else 4.5,
             "sog_a": round(s_a / valid, 2) if valid else 4.5,
             "fouls_c": round(f_c / valid, 1) if valid else 12.0,
             "fouls_s": round(f_s / valid, 1) if valid else 12.0,
             "n": valid}
        _cache_set(ck, d)
        return d

    def _topscorers_map(self, league: int) -> dict:
        """{nome_squadra: [{nome, xg_per90 stimato, rigorista}]} — 1 call/league, cache 7gg."""
        ck = f"scorers_{league}_{self.season}"
        hit = _cache_get(ck)
        if hit:
            return hit
        try:
            data = _get("/players/topscorers", self.key,
                        {"league": league, "season": self.season})
        except Exception:
            return {}
        out: dict = {}
        for p in data.get("response", [])[:30]:
            pl, st = p.get("player", {}), (p.get("statistics") or [{}])[0]
            team = (st.get("team") or {}).get("name", "?")
            goals = (st.get("goals") or {}).get("total") or 0
            pen = (st.get("penalty") or {}).get("scored") or 0
            mins = (st.get("games") or {}).get("minutes") or 900
            if goals <= 0 or mins <= 0:
                continue
            per90 = goals / (mins / 90.0)
            xg_proxy = round(per90 * 0.9, 2)  # proxy onesto senza xG veri
            out.setdefault(team, []).append({
                "nome": pl.get("name", "?"), "squadra": team,
                "xg_per90": xg_proxy, "minuti_previsti": 85,
                "rigorista": pen >= max(2, goals * 0.3)})
        _cache_set(ck, out)
        return out

    def get_partite(self) -> list[dict]:
        if not self.key:
            raise RuntimeError(
                "Manca API_FOOTBALL_KEY. Crea .env con API_FOOTBALL_KEY=tua_key")
        partite = []
        for league in self.leagues:
            if not self._budget_ok():
                print(f"[QUOTA] budget {self.max_calls} raggiunto, mi fermo. "
                      f"Rilancia domani: cache in .cache/ riprende da qui.")
                break
            params = {"league": league, "season": self.season}
            if self.round_name:
                params["round"] = self.round_name
                data = _get("/fixtures", self.key, params)
                fixtures = data.get("response", [])[:self.max_partite]
            else:
                # Stagioni passate: 'next' è vuoto -> prendi un round giocato (FT)
                # 1 sola chiamata da 380 partite, poi filtro locale.
                data = _get("/fixtures", self.key, params)
                all_fx = data.get("response", [])
                gioc = [f for f in all_fx
                        if f.get("fixture", {}).get("status", {}).get("short") == "FT"]
                # prendi le ultime del campionato (più dati storici disponibili)
                fixtures = gioc[-self.max_partite:] if gioc else all_fx[:self.max_partite]
            scorers = self._topscorers_map(league)
            for fx in fixtures:
                if not self._budget_ok():
                    print(f"[QUOTA] budget {self.max_calls} raggiunto a "
                          f"{len(partite)} partite. Rilancia domani per completare.")
                    return partite
                home = fx["teams"]["home"]["name"]
                away = fx["teams"]["away"]["name"]
                hid, aid = fx["teams"]["home"]["id"], fx["teams"]["away"]["id"]
                h = self._team_avg(league, hid, "home")
                a = self._team_avg(league, aid, "away")
                marc = (scorers.get(home, [])[:2] + scorers.get(away, [])[:2])
                partite.append({
                    "casa": home, "trasferta": away,
                    "lega": LEAGUES_DEFAULT.get(league, str(league)),
                    "partite_casa": h["n"], "partite_trasferta": a["n"],
                    "soglia_minima_partite": 6,
                    "soglia_angoli": 8.5, "soglia_tiri": 4.5,
                    "soglia_cartellini": 3.5,
                    "tasso_cartellini": 0.14, "severita_arbitro": 1.0,
                    "angoli": {
                        "casa_fatti_casa": h["corners_f"],
                        "casa_subiti_casa": h["corners_a"],
                        "ospite_fatti_fuori": a["corners_f"],
                        "ospite_subiti_fuori": a["corners_a"]},
                    "tiri_in_porta": {
                        "casa_fatti_casa": h["sog_f"],
                        "casa_subiti_casa": h["sog_a"],
                        "ospite_fatti_fuori": a["sog_f"],
                        "ospite_subiti_fuori": a["sog_a"]},
                    "falli": {
                        "commessi_casa": h["fouls_c"],
                        "subiti_casa": h["fouls_s"],
                        "commessi_ospite": a["fouls_c"],
                        "subiti_ospite": a["fouls_s"]},
                    "marcatori": marc,
                    "fixture_id": fx["fixture"]["id"],
                    "data": fx["fixture"]["date"],
                })
        return partite
