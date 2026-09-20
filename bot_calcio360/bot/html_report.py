"""Pagina HTML unica v2: timeline per orario, colori, filtri, tutto chiaro.

Zero dipendenze esterne. Rigenerata ad ogni run.
"""
import html as _h
from datetime import datetime
from pathlib import Path


def _esc(x) -> str:
    return _h.escape(str(x))


def _col(p) -> str:
    return "background:#3f6fd1"


def _blocco_risultati(risultati_giocati: list[dict]) -> list[str]:
    """Sezione RISULTATI: partite già finite con punteggio (niente analisi)."""
    if not risultati_giocati:
        return []
    gruppi: dict[str, list] = {}
    for r in risultati_giocati:
        try:
            y, m, g = r.get("data", "").split("-")
            gruppi.setdefault(f"{g}/{m}", []).append(r)
        except ValueError:
            pass
    p = ["<h2>Risultati già giocati</h2><div class='grid'>"]
    for giorno, lst in sorted(gruppi.items()):
        cards = "".join(
            f"<div class='card'><div class='top'><span class='ora'>{_esc(giorno)}</span>"
            f"<span class='lega'>{_esc(x.get('lega', ''))}</span></div>"
            f"<div class='match'>{_esc(x.get('casa', ''))} "
            f"{_esc(x.get('risultato', '-'))} {_esc(x.get('trasferta', ''))}</div>"
            f"<span class='verd'>FINALE</span></div>"
            for x in lst)
        p.append(cards)
    p.append("</div>")
    return p


def _blocco_live(risultati: list[dict]) -> list[str]:
    """IN CAMPO ORA: partite iniziate da meno di 2 ore.

    ONESTA': senza feed live a pagamento il punteggio in diretta non c'e';
    si mostrano i valori pre-partita con l'avviso chiaro.
    """
    live = [r for r in risultati if r.get("stato") == "live"]
    if not live:
        return []
    p = ["<h2>In campo ora (valori pre-partita: il live vero richiede feed a pagamento)</h2>"
         "<div class='grid'>"]
    for r in live:
        p.append(
            f"<div class='card'><div class='top'>"
            f"<span class='ora'>LIVE {_esc(r.get('ora', ''))}</span>"
            f"<span class='lega'>{_esc(r.get('lega', ''))}</span></div>"
            f"<div class='match'>{_esc(r['partita'])}</div>"
            f"<span class='verd mid'>IN CORSO</span>"
            f"<div class='sub2' style='font-size:12px;color:#aab'>Punteggio live non "
            f"disponibile gratis — sotto i valori pre-partita.</div>"
            f"{_dettaglio(r, None)}</div>")
    p.append("</div>")
    return p


def _giorno_label(d: str) -> str:
    nomi = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    try:
        from datetime import date as _d
        y, m, g = d.split("-")
        dt = _d(int(y), int(m), int(g))
        return f"{nomi[dt.weekday()]} {g}/{m}"
    except (ValueError, AttributeError):
        return d or "?"

CSS = """
*{box-sizing:border-box}body{font-family:system-ui,-apple-system,'Segoe UI',Arial,sans-serif;
max-width:1200px;margin:0 auto;padding:16px;color:#eef1f6;
background:radial-gradient(1200px 400px at 20% -5%,#1c2b4a 0%,#0f1115 55%) fixed,#0f1115}
h1{font-size:26px;margin:4px 0;letter-spacing:.3px}
h1 .gold{color:#e8c96a}
h2{font-size:16px;margin:28px 0 10px;color:#e8c96a;text-transform:uppercase;letter-spacing:1px}
.sub{color:#9aa3b5}.legenda{background:linear-gradient(180deg,#1b2130,#161b26);
border:1px solid #2c3446;padding:12px 16px;border-radius:14px;
font-size:14px;line-height:1.7}
.filtri{margin:14px 0;display:flex;gap:8px;flex-wrap:wrap}
.filtri button{background:#1a2030;color:#e8eaf0;border:1px solid #39415a;
border-radius:20px;padding:7px 14px;cursor:pointer;font-size:14px}
.filtri button.on{background:#e8c96a;border-color:#e8c96a;color:#1a1a1a;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}
.card{background:linear-gradient(180deg,#1c2230,#141922);
border:1px solid #2e3648;border-radius:16px;padding:16px;
box-shadow:0 6px 18px rgba(0,0,0,.35)}
.card .top{display:flex;justify-content:space-between;align-items:center;gap:8px}
.ora{font-size:13px;color:#e8c96a;font-weight:700;white-space:nowrap}
.lega{font-size:11px;color:#9aa3b5;text-transform:uppercase;letter-spacing:.6px;white-space:nowrap}
.match{font-size:19px;font-weight:800;margin:8px 0 4px}
.verd{font-size:12px;font-weight:700;padding:2px 10px;border-radius:12px;
background:#3a3f4b;display:inline-block;margin:4px 0}
.verd.ok{background:#1f7a3d}.verd.mid{background:#8a6d1c}
.verd.pre{background:#2456a6}.verd.fin{background:#7a2020}
.verd.live{background:#1f7a3d;animation:pulse 1.6s infinite}
@keyframes pulse{50%{opacity:.55}}
.vtext{font-size:13px;font-weight:700}
.vtext.ok{color:#7ddf9a}.vtext.mid{color:#e8c96a}.vtext.no{color:#aab}
.mrow{display:flex;align-items:center;gap:8px;margin:6px 0;font-size:13px}
.mrow .lab{width:44px;color:#9aa3b5;flex:none;font-weight:600}
.bar{flex:1;height:12px;border-radius:7px;background:#232936;overflow:hidden;
box-shadow:inset 0 1px 3px rgba(0,0,0,.5)}
.bar i{display:block;height:100%;border-radius:7px}
.bar.b-ang i{background:linear-gradient(90deg,#0284c7,#38bdf8)}
.bar.b-tiri i{background:linear-gradient(90deg,#059669,#34d399)}
.bar.b-cart i{background:linear-gradient(90deg,#b45309,#fbbf24)}
.bar.b-o25 i{background:linear-gradient(90deg,#7c3aed,#a78bfa)}
.bar.b-gg i{background:linear-gradient(90deg,#e11d48,#fb7185)}
.mrow .val{width:46px;text-align:right;font-weight:800}
.idea{margin-top:10px;font-size:14px;background:linear-gradient(180deg,#2a2413,#201b0e);
border:1px solid #6b5a26;border-radius:10px;
padding:8px 12px}.idea b{color:#e8c96a}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.chip{font-size:12px;background:#232a3a;border:1px solid #46536e;border-radius:12px;
padding:3px 11px;color:#d5dbe8}
.blocco{background:#12161f;border:1px solid #262d3d;border-radius:12px;padding:12px 14px;margin:8px 0}
.blocco h4{margin:0 0 6px;font-size:14px;color:#fff}
.blocco .sub2{font-size:12px;color:#9aa3b5;margin-bottom:4px}
.gol{font-size:13px;color:#c8ccd6;margin-top:6px}
.gol b{color:#e8c96a}
details{margin-top:8px}summary{cursor:pointer;color:#e8c96a;font-size:13px;font-weight:600}
.agg{background:linear-gradient(180deg,#27a04c,#1c7a3a);color:#fff;font-weight:800;border:none;border-radius:12px;
padding:12px 24px;font-size:16px;cursor:pointer;box-shadow:0 4px 14px rgba(31,122,61,.4)}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
@media (max-width:560px){body{padding:10px}h1{font-size:19px}.card{padding:12px}
.mrow{font-size:12px}.filtri button{padding:9px 16px;font-size:15px}
table{font-size:13px}th,td{padding:5px 6px}}
"""

JS = """
function f(leg){document.querySelectorAll('.filtri button').forEach(b=>b.classList.remove('on'));
event.target.classList.add('on');
document.querySelectorAll('#prossime .card').forEach(c=>{
c.style.display=(leg==='TUTTE'||c.dataset.lega===leg||c.dataset.giorno===leg)?'':'none';});}
"""


def _dettaglio(r: dict, barra) -> str:
    """Dettaglio a blocchi chiari con barre."""
    d = r.get("det", {})
    b = []

    def righe_scala(sc: dict) -> str:
        return " · ".join(f"Over {s}: {p:.0f}%" for s, p in (sc or {}).items())

    gc, ga = d.get("giocate", (0, 0))
    b.append(f"<div class='blocco'><div class='sub2'>{_esc(d.get('filtro', ''))} "
             f"Partite giocate: casa {gc}, trasferta {ga} (servono 6).</div></div>")

    b.append(f"<div class='blocco'><h4>Angoli — previsti circa {d.get('ang', 0):.0f}</h4>"
             f"<div class='sub2'>Casa circa {d.get('ang_casa', 0):.0f} · "
             f"Ospite circa {d.get('ang_osp', 0):.0f}</div>"
             f"<div class='sub2'>{_esc(righe_scala(d.get('scala_a')))}</div></div>")

    _tt = d.get("tt") or {}
    _poss = d.get("poss") or {}
    extra_t = ""
    if _tt:
        extra_t += (f"<div class='sub2'>Tiri totali: casa {_tt.get('casa')} / "
                    f"ospite {_tt.get('ospite')}</div>")
    if _poss:
        extra_t += (f"<div class='sub2'>Possesso: casa {_poss.get('casa')}% / "
                    f"ospite {_poss.get('ospite')}%</div>")
    b.append(f"<div class='blocco'><h4>Tiri in porta — previsti circa {d.get('tiri', 0):.0f}</h4>"
             f"<div class='sub2'>Casa circa {d.get('tiri_casa', 0):.0f} · "
             f"Ospite circa {d.get('tiri_osp', 0):.0f}</div>"
             f"<div class='sub2'>{_esc(righe_scala(d.get('scala_t')))}</div>"
             + extra_t + "</div>")

    b.append(f"<div class='blocco'><h4>Cartellini — previsti circa {d.get('cart', 0):.0f} "
             f"(da {d.get('falli_tot', 0):.0f} falli)</h4>"
             f"<div class='sub2'>{_esc((d.get('falli', '') or '').split('|')[0])}</div></div>")

    if d.get("off_tot"):
        b.append(f"<div class='blocco'><h4>Fuorigioco — previsti circa {d.get('off_tot', 0):.0f} "
                 f"(Over 3,5: {d.get('off_o35', 0):.0f}%)</h4>"
                 f"<div class='sub2'>{_esc(righe_scala(d.get('scala_o')))}</div></div>")

    b.append(f"<div class='blocco'><h4>Gol — previsti circa {d.get('gol', 0):.1f} "
             f"({d.get('gol_casa', 0):.1f} casa + {d.get('gol_osp', 0):.1f} ospite)</h4>"
             f"<div class='sub2'>Over 1,5: {d.get('o15', 0):.0f}% · Over 2,5: {d.get('o25', 0):.0f}% · "
             f"Over 3,5: {d.get('o35', 0):.0f}% · Entrambe segnano: {d.get('gg', 0):.0f}%</div>"
             f"<div class='sub2'>Esito 1X2: 1 al {d.get('uno', 0):.0f}% · "
             f"X al {d.get('ics', 0):.0f}% · 2 al {d.get('due', 0):.0f}%</div>"
             f"<div class='sub2'>Doppie chance: 1X {d.get('dc1x', 0):.0f}% · "
             f"12 {d.get('dc12', 0):.0f}% · X2 {d.get('dcx2', 0):.0f}%</div>"
             f"<div class='sub2'>Casa segna: Over 0,5 {d.get('ch_o05', 0):.0f}% · "
             f"Over 1,5 {d.get('ch_o15', 0):.0f}% · Ospite segna: Over 0,5 "
             f"{d.get('ao_o05', 0):.0f}% · Over 1,5 {d.get('ao_o15', 0):.0f}%</div>" +
             (f"<div class='sub2'>xG squadre: casa {d['xgs'].get('casa')} / "
              f"ospite {d['xgs'].get('ospite')}</div>" if d.get("xgs") else "") +
             "</div>")

    marc = d.get("marcatori", [])
    if marc:
        righe = "".join(
            f"<div class='sub2'>• {_esc(n)} ({_esc(s)}): segna nel {p:.0f}% dei casi"
            + (" — tira i rigori" if rig else "") + "</div>"
            for n, s, p, rig, q in marc)
        b.append(f"<div class='blocco'><h4>Marcatori</h4>{righe}</div>")
    rk = d.get("rischio", [])
    if rk:
        righe = ""
        for x in rk:
            n, s, g, p = x[0], x[1], x[2], x[3]
            fpg = x[4] if len(x) > 4 else None
            plu = x[6] if len(x) > 6 else None
            righe += (f"<div class='sub2'>• {_esc(n)} ({_esc(s)}): {g} gialli — "
                      f"ammonito nel {p:.0f}%")
            if fpg is not None:
                righe += f" · {fpg} falli/gara"
            if plu is not None:
                righe += f" · <b>PLUS {plu:.0f}%</b>"
            righe += "</div>"
        b.append(f"<div class='blocco'><h4>A rischio ammonizione (+ PLUS = "
                 f"ammonito oppure 2+ falli)</h4>{righe}</div>")
    return "".join(b)


def genera_html(risultati: list[dict], out_dir: str | Path,
                titolo: str = "Bot Calcio 360° — weekend",
                risultati_giocati: list[dict] = None) -> Path:
    out = Path(out_dir)
    ordina = sorted(risultati,
                    key=lambda r: (r.get("data", ""), r.get("ora", "") or "99"))
    leghe = sorted({r.get("lega", "Varie") or "Varie" for r in risultati})
    giorni = sorted({r.get("data", "") for r in risultati})

    _cls = {"Ang": "b-ang", "Tiri": "b-tiri", "Cart": "b-cart",
            "O2.5": "b-o25", "GG": "b-gg"}
    def barra(label: str, val) -> str:
        try:
            v = float(val)
        except (TypeError, ValueError):
            v = 0
        return (f"<div class='mrow'><span class='lab'>{label}</span>"
                f"<div class='bar {_cls.get(label, '')}'>"
                f"<i style='width:{max(0, min(100, v))}%'></i></div>"
                f"<span class='val'>{v:.0f}%</span></div>")

    p = [f"<!DOCTYPE html><html lang='it'><head><meta charset='utf-8'>"
         f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>{_esc(titolo)}</title><style>{CSS}</style></head><body>",
         f"<div class='topbar'><div><h1>Bot Calcio <span class='gold'>360°</span> — weekend</h1>",
         f"<p class='sub'>Aggiornato: {_esc(datetime.now().strftime('%d/%m/%Y %H:%M'))} "
         f"· {len(risultati)} partite · dati reali 2026/27</p></div>",
         f"<div><button class='agg' onclick=\"fetch('/aggiorna',{{method:'POST'}})"
         f".then(r=>{{if(!r.ok)throw 0;location.reload()}})"
         f".catch(()=>alert('Qui su Netlify il bottone non puo aggiornare da solo: "
         f"la pagina si aggiorna con un nuovo deploy (trascina di nuovo la cartella) "
         f"oppure con Azioni GitHub dal telefono. In locale col server invece funziona.'))\">"
         f"AGGIORNA DATI</button></div></div>",
         "<div class='legenda'><b>Come si legge:</b> ogni mercato ha il suo colore "
         "(azzurro=angoli, verde=tiri, giallo=cartellini, viola=gol, rosa=GG), "
         "il numero a destra dice tutto. "
         "<b>IDEA</b> = la linea piu' vicina al 65%: non e' a caso e non e' la piu' alta — "
         "sopra il 78% i book pagano spiccioli, sotto il 55% e' rischioso. "
         "Sotto IDEA trovi le <b>altre linee che valgono</b>, in ordine di bonta'. "
         "<b>PROVVISORIO</b> = dati veri ma campione sotto 6 partite: guardare, non giocare.<br>"
         "Premi <b>AGGIORNA DATI</b> in alto per riscaricare tutto da solo.</div>",
         ] + _blocco_risultati(risultati_giocati or []) + [
         "<div class='filtri'><button class='on' onclick=\"f('TUTTE')\">Tutte</button>"]
    NOMI_BREVI = {"Serie A": "Serie A", "Premier League 2026/27": "Premier",
                  "La Liga 2026/27": "Liga", "Bundesliga 2026/27": "Bundes",
                  "Ligue 1 2026/27": "Ligue 1", "Liga Portugal 2026/27": "Portogallo",
                  "Eredivisie 2026/27": "Olanda"}
    for l in leghe:
        breve = NOMI_BREVI.get(l, l.split()[0])
        p.append(f"<button data-f='{((_esc(l)))}' "
                 f"onclick=\"f(this.getAttribute('data-f'))\">{_esc(breve)}</button>")
    for g in giorni:
        p.append(f"<button onclick=\"f('{_esc(_giorno_label(g))}')\">{_esc(_giorno_label(g))}</button>")
    p.append("</div><div class='grid' id='prossime'>")

    for r in ordina:
        v = r.get("giudizio", "")
        vt = "ok" if v.startswith(("Alta", "Buona")) else ("mid" if "Media" in v else "no")
        vbreve = v.split(" — ")[0]
        ora = f"{_giorno_label(r.get('data', ''))} {_esc(r.get('ora', ''))}".strip()
        st = r.get("stato", "prossima")
        if st == "live":
            badge = "<span class='verd live'>IN CORSO</span>"
        elif st == "finita":
            badge = f"<span class='verd fin'>FINITA {_esc(r.get('risultato', ''))}</span>"
        else:
            badge = "<span class='verd pre'>DA GIOCARE</span>"
        det = "<br>".join(_esc(x) for x in r.get("testo", "").splitlines()[2:])
        p.append(
            f"<div class='card' data-lega='{_esc(r.get('lega', ''))}' "
            f"data-giorno='{_esc(_giorno_label(r.get('data', '')))}'>"
            f"<div class='top'><span class='ora'>{_esc(ora)}</span>"
            f"<span class='lega'>{_esc(r.get('lega', ''))}</span></div>"
            f"<div class='match'>{_esc(r['partita'])}</div>"
            f"{badge} "
            f"<span class='vtext {vt}'>{_esc(vbreve)}</span>"
            f"{barra('Ang', r['over_angoli'])}{barra('Tiri', r['over_tiri'])}"
            f"{barra('Cart', r['over_cartellini'])}{barra('O2.5', r.get('gol_o25', 0))}"
            f"{barra('GG', r.get('gol_gg', 0))}")
        if r.get("idea"):
            p.append(f"<div class='idea'>La giocata piu' sensata: <b>{_esc(r['idea'])}</b></div>")
        gio = r.get("giocabili", [])[1:4]
        if gio:
            p.append("<div class='chips'>" + "".join(
                f"<span class='chip'>{_esc(g)}</span>" for g in gio) + "</div>")
        if r.get("top_marcatore"):
            p.append(f"<div class='gol'>Marcatore: {_esc(r['top_marcatore'])}</div>")
        if r.get("rischio_top"):
            p.append(f"<div class='gol'>A rischio giallo: <b>{_esc(r['rischio_top'])}</b></div>")
        p.append(f"<details><summary>Dettaglio completo</summary>{_dettaglio(r, barra)}</details></div>")
    p.append(f"</div><script>{JS}</script></body></html>")
    dest = out / "_report.html"
    dest.write_text("\n".join(p), encoding="utf-8")
    return dest
