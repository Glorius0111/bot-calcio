"""CLI automazione totale.

COMANDO UNICO (tutto automatico: calendari + dati reali + report + pagina):
  python batch_main.py --auto --open
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bot.batch import elabora_tutte, riga as _riga


def parse_leagues(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def main():
    ap = argparse.ArgumentParser(description="Bot 360 — automazione tutte le partite")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--auto", action="store_true",
                    help="TUTTO AUTOMATICO: scarica calendari top-5 + dati reali + report + pagina")
    ap.add_argument("--giorni", type=int, default=3,
                    help="con --auto: partite da oggi a +N giorni (default 3)")
    ap.add_argument("--indietro", type=int, default=1,
                    help="con --auto: includi anche ieri e N giorni fa (default 1)")
    ap.add_argument("--file", default=None,
                    help="file JSON con {'partite': [...]} vere 2026/27, zero rete (es. esempi/serie_a_2026_27_g5.json)")
    ap.add_argument("--enrich", default="none", choices=["none", "soccerstats", "full"],
                    help="arricchisce --file con dati reali gratis (full=tutto reale)")
    ap.add_argument("--lega", default=None,
                    help="forza lega per --file senza campo lega (italy, england, spain, germany, france)")
    ap.add_argument("--soglia-tiri", type=float, default=8.5,
                    help="soglia base tiri in porta (default 8.5: il 4.5 non viene quotato)")
    ap.add_argument("--soglia-angoli", type=float, default=8.5)
    ap.add_argument("--open", action="store_true",
                    help="apre _report.html nel browser a fine run")
    ap.add_argument("--serve", action="store_true",
                    help="avvia il server locale con tasto AGGIORNA DATI")
    ap.add_argument("--api", action="store_true", help="usa API-Football reale")
    ap.add_argument("--check", action="store_true", help="testa key + quota (1 chiamata)")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="reports")
    ap.add_argument("--league", type=int, default=None, help="singola lega (legacy)")
    ap.add_argument("--leagues", default="135",
                    help="liste leghe: 135=SerieA,39=Premier,140=Liga,78=Bundes,61=Ligue1,2=UCL")
    ap.add_argument("--season", type=int, default=2024,
                    help="2024=stagione completa 2024/25 con dati (default). 2023 ok, 2025 vuota su free.")
    ap.add_argument("--round", default=None)
    ap.add_argument("--max-per-league", type=int, default=10,
                    help="quante partite per lega (usa 2 per test quota free)")
    ap.add_argument("--ultime-n", type=int, default=3,
                    help="partite storiche per media (3=~82 chiamate/lega, 6=~150). Default 3 per free.")
    ap.add_argument("--max-calls", type=int, default=90,
                    help="budget chiamate API per giro (default 90/100 free)")
    args = ap.parse_args()

    if args.check:
        from bot.providers.api_football import ApiFootballProvider
        prov = ApiFootballProvider(leagues=[135], season=args.season)
        try:
            st = prov.check_key()
            print(f"Key OK. Quota: {st.get('response', st)}")
        except Exception as e:
            print(f"Key KO: {e}")
            print("Crea .env con: API_FOOTBALL_KEY=tua_key")
        return

    giocati: list = []
    if args.auto:
        from bot.providers.fixtures_auto import AutoFixtureProvider
        prov = AutoFixtureProvider(giorni=args.giorni, indietro=args.indietro)
        print("[AUTO] scarico calendari top-5 2026/27 ...")
        partite = prov.get_partite()
        try:
            giocati = prov.get_risultati()
        except Exception as e:  # noqa: BLE001
            print(f"[RIS] salto risultati ({e})")
            giocati = []
        for p in partite:
            p["soglia_tiri"] = args.soglia_tiri
            p["soglia_angoli"] = args.soglia_angoli
        from bot.providers.soccerstats import arricchisci, _lega_key
        gruppi: dict[str, list] = {}
        for p in partite:
            gruppi.setdefault(p.get("lega", ""), []).append(p)
        for lega, plist in gruppi.items():
            _, rep = arricchisci(plist, _lega_key(lega))
            print(f"[SOCCERSTATS] {lega}: angoli reali {rep['ok']}/{rep['totali']}")
        from bot.providers.statmuse import enrich_full
        rep2 = {"tiri_reali": 0, "falli_reali": 0, "xg_reali": 0, "totali": 0}
        for lega, plist in gruppi.items():
            r = enrich_full(plist, _lega_key(lega))
            for k in rep2:
                rep2[k] += r.get(k, 0)
        print(f"[STATMUSE] tiri reali {rep2['tiri_reali']}/{rep2['totali']}, "
              f"falli reali {rep2['falli_reali']}/{rep2['totali']}, "
              f"xG reali {rep2['xg_reali']} marcatori")
    elif args.file:
        from bot.providers.file_list import FileListProvider
        prov = FileListProvider(args.file)
        print(f"[FILE] leggo partite vere da {args.file} (nessuna chiamata API) ...")
        partite = prov.get_partite()
        if args.lega:
            for p in partite:
                p["lega"] = args.lega
        for p in partite:
            p["soglia_tiri"] = args.soglia_tiri
            p["soglia_angoli"] = args.soglia_angoli
        if args.enrich in ("soccerstats", "full"):
            from bot.providers.soccerstats import arricchisci
            gruppi: dict[str, list] = {}
            for p in partite:
                gruppi.setdefault(p.get("lega", "Serie A"), []).append(p)
            for lega, plist in gruppi.items():
                _, rep = arricchisci(plist, lega)
                print(f"[SOCCERSTATS] {lega}: angoli reali {rep['ok']}/{rep['totali']}")
            if args.enrich == "full":
                from bot.providers.statmuse import enrich_full
                from bot.providers.soccerstats import _lega_key
                rep2 = {"tiri_reali": 0, "falli_reali": 0, "xg_reali": 0,
                        "totali": 0}
                for lega, plist in gruppi.items():
                    r = enrich_full(plist, _lega_key(lega))
                    for k in rep2:
                        rep2[k] += r.get(k, 0)
                print(f"[STATMUSE] tiri reali {rep2['tiri_reali']}/{rep2['totali']}, "
                      f"falli reali {rep2['falli_reali']}/{rep2['totali']}, "
                      f"xG reali {rep2['xg_reali']} marcatori")
    elif args.api:
        from bot.providers.api_football import ApiFootballProvider
        leagues = [args.league] if args.league else parse_leagues(args.leagues)
        prov = ApiFootballProvider(leagues=leagues, season=args.season,
                                   round_name=args.round,
                                   max_partite_per_league=args.max_per_league,
                                   ultime_n=args.ultime_n,
                                   max_calls=args.max_calls)
        print(f"[API] leagues={leagues} season={args.season} round={args.round} "
              f"ultime_n={args.ultime_n} max_calls={args.max_calls} ...")
        partite = prov.get_partite()
    else:
        from bot.providers.demo import DemoProvider
        prov = DemoProvider(seed=args.seed, n_partite=args.n)
        print(f"[DEMO] genero {args.n} partite simulate (seed={args.seed}) ...")
        partite = prov.get_partite()

    print(f"Partite da analizzare: {len(partite)}")
    ris = elabora_tutte(partite, out_dir=args.out, risultati_giocati=giocati)
    print(f"\nReport salvati in {args.out}/ + _classifica.txt\n")
    from bot.batch import quando
    giorno_corr = None
    for r in sorted(ris, key=lambda x: (x.get("data", ""), x.get("ora", "") or "99")):
        g = (r.get("data", "") or "?")[:10]
        if g != giorno_corr:
            giorno_corr = g
            try:
                y, mo, d = g.split("-")
                print(f"\n== {d}/{mo} ==")
            except ValueError:
                print(f"\n== {g} ==")
        print("  " + _riga(r))
    print()
    print("Legenda: Ang=Over 8.5 angoli, Tiri=Over 8.5 tiri in porta, "
          "Cart=Over 3.5 cartellini, O2.5=Over 2.5 gol, GG=entrambe segnano.")
    print("IDEA=linea con prob. 55-78%, quella che il book quota ~1.40-1.85.")
    print("PROVVISORIO=dati reali ma campione<6, nessun pronostico. "
          "ALTA/BUONA/MEDIA=giudizi operativi. [RIG]=rigorista.")
    print(f"Pagina unica: {args.out}/_report.html")
    if args.serve:
        import subprocess as _sp
        _sp.run([sys.executable, "server.py", "--out", args.out],
                cwd=str(Path(__file__).parent))
        return
    if args.open:
        import webbrowser
        from pathlib import Path as _P
        webbrowser.open(_P(args.out, "_report.html").resolve().as_uri())


if __name__ == "__main__":
    main()
