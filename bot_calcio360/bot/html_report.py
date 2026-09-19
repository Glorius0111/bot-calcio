"""Pagina HTML unica v2: timeline per orario, colori, filtri, tutto chiaro.

Zero dipendenze esterne. Rigenerata ad ogni run.
"""
import html as _h
from datetime import datetime
from pathlib import Path


def _esc(x) -> str:
    return _h.escape(str(x))


def _col(p) -> str:
    try:
        p = float(p)
    except (TypeError, ValueError):
        return "background:#3a3f4b"
    if p >= 70:
        return "background:#1f7a3d"
    if p >= 55:
        return "background:#8a6d1c"
    return "background:#3a3f4b"


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
*{box-sizing:border-box}body{font-family:system-ui,-apple-system,Arial,sans-serif;
max-width:1200px;margin:0 auto;padding:16px;background:#0f1115;color:#e8eaf0}
h1{font-size:24px;margin:4px 0}h2{font-size:17px;margin:26px 0 10px;color:#9fd0ff}
.sub{color:#aab}.legenda{background:#1a1e27;padding:12px 16px;border-radius:12px;
font-size:14px;line-height:1.7}
.filtri{margin:14px 0;display:flex;gap:8px;flex-wrap:wrap}
.filtri button{background:#222836;color:#e8eaf0;border:1px solid #39415a;
border-radius:20px;padding:7px 14px;cursor:pointer;font-size:14px}
.filtri button.on{background:#2456a6;border-color:#2456a6}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px}
.card{background:#171b23;border:1px solid #2a2f3a;border-radius:14px;padding:14px}
.card .top{display:flex;justify-content:space-between;align-items:center;gap:8px}
.ora{font-size:13px;color:#9fd0ff;font-weight:700;white-space:nowrap}
.lega{font-size:12px;color:#aab;white-space:nowrap}
.match{font-size:18px;font-weight:700;margin:8px 0 2px}
.verd{font-size:12px;font-weight:700;padding:2px 10px;border-radius:12px;
background:#3a3f4b;display:inline-block;margin:4px 0}
.verd.ok{background:#1f7a3d}.verd.mid{background:#8a6d1c}
.mrow{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:13px}
.mrow .lab{width:44px;color:#aab;flex:none}
.bar{flex:1;height:10px;border-radius:6px;background:#262b36;overflow:hidden}
.bar i{display:block;height:100%;border-radius:6px}
.mrow .val{width:44px;text-align:right;font-weight:700}
.idea{margin-top:8px;font-size:14px;background:#1d2f4d;border-radius:8px;
padding:7px 10px}.idea b{color:#9fd0ff}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.chip{font-size:12px;background:#1d2f4d;border:1px solid #35507e;border-radius:12px;
padding:2px 10px}
.blocco{background:#141821;border-radius:10px;padding:10px 12px;margin:8px 0}
.blocco h4{margin:0 0 6px;font-size:14px;color:#fff}
.blocco .sub2{font-size:12px;color:#aab;margin-bottom:4px}
.gol{font-size:13px;color:#c8ccd6;margin-top:6px}
details{margin-top:8px}summary{cursor:pointer;color:#9fd0ff;font-size:13px}
.agg{background:#1f7a3d;color:#fff;font-weight:700;border:none;border-radius:10px;
padding:12px 22px;font-size:16px;cursor:pointer}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
@media (max-width:560px){body{padding:10px}h1{font-size:19px}.card{padding:12px}
.mrow{font-size:12px}.filtri button{padding:9px 16px;font-size:15px}
table{font-size:13px}th,td{padding:5px 6px}}
"""

JS = """
function f(leg){document.querySelectorAll('.filtri button').forEach(b=>b.classList.remove('on'));
event.target.classList.add('on');
document.querySelectorAll('.card').forEach(c=>{
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
             f"X al {d.get('ics', 0):.0f}% · 2 al {d.get('due', 0):.0f}%</div>" +
             (f"<div class='sub2'>xG squadre: casa {d['xgs'].get('casa')} / "
              f"ospite {d['xgs'].get('ospite')}</div>" if d.get("xgs") else "") +
             "</div>")

    marc = d.get("marcatori", [])
    if marc:
        righe = "".join(
            f"<div class='sub2'>• {_esc(n)} ({_esc(s)}): segna nel {p:.0f}% dei casi"
            + (" — tira i rigori" if rig else "") + "</div>"
            for n, s, p, rig in marc)
        b.append(f"<div class='blocco'><h4>Marcatori</h4>{righe}</div>")
    return "".join(b)


def genera_html(risultati: list[dict], out_dir: str | Path,
                titolo: str = "Bot Calcio 360° — weekend") -> Path:
    out = Path(out_dir)
    ordina = sorted(risultati,
                    key=lambda r: (r.get("data", ""), r.get("ora", "") or "99"))
    leghe = sorted({r.get("lega", "Varie") or "Varie" for r in risultati})
    giorni = sorted({r.get("data", "") for r in risultati})

    def barra(label: str, val) -> str:
        try:
            v = float(val)
        except (TypeError, ValueError):
            v = 0
        return (f"<div class='mrow'><span class='lab'>{label}</span>"
                f"<div class='bar'><i style='{_col(v)};width:{max(0, min(100, v))}%'></i></div>"
                f"<span class='val'>{v:.0f}%</span></div>")

    p = [f"<!DOCTYPE html><html lang='it'><head><meta charset='utf-8'>"
         f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>{_esc(titolo)}</title><style>{CSS}</style></head><body>",
         f"<div class='topbar'><div><h1>{_esc(titolo)}</h1>",
         f"<p class='sub'>Aggiornato: {_esc(datetime.now().strftime('%d/%m/%Y %H:%M'))} "
         f"· {len(risultati)} partite · dati reali 2026/27</p></div>",
         f"<div><button class='agg' onclick=\"fetch('/aggiorna',{{method:'POST'}})"
         f".then(r=>{{if(!r.ok)throw 0;location.reload()}})"
         f".catch(()=>alert('Aggiornamento automatico attivo solo in locale. "
         f"Su Netlify: ricarica il sito dopo ogni nuovo deploy.'))\">"
         f"AGGIORNA DATI</button></div></div>",
         "<div class='legenda'><b>Come si legge:</b> le barre sono le probabilità "
         "(verde = alte, gialle = zona quota giocabile ~1.40-1.85). "
         "<b>IDEA</b> = la linea piu' vicina al 65%: non e' a caso e non e' la piu' alta — "
         "sopra il 78% i book pagano spiccioli, sotto il 55% e' rischioso. "
         "Sotto IDEA trovi le <b>altre linee che valgono</b>, in ordine di bonta'. "
         "<b>PROVVISORIO</b> = dati veri ma campione sotto 6 partite: guardare, non giocare.<br>"
         "Premi <b>AGGIORNA DATI</b> in alto per riscaricare tutto da solo.</div>",
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
    p.append("</div><div class='grid'>")

    for r in ordina:
        v = r.get("giudizio", "")
        vcls = "ok" if v.startswith(("Alta", "Buona")) else ("mid" if "Media" in v else "")
        vbreve = v.split(" — ")[0]
        ora = f"{_giorno_label(r.get('data', ''))} {_esc(r.get('ora', ''))}".strip()
        det = "<br>".join(_esc(x) for x in r.get("testo", "").splitlines()[2:])
        p.append(
            f"<div class='card' data-lega='{_esc(r.get('lega', ''))}' "
            f"data-giorno='{_esc(_giorno_label(r.get('data', '')))}'>"
            f"<div class='top'><span class='ora'>{_esc(ora)}</span>"
            f"<span class='lega'>{_esc(r.get('lega', ''))}</span></div>"
            f"<div class='match'>{_esc(r['partita'])}</div>"
            f"<span class='verd {vcls}'>{_esc(vbreve)}</span>"
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
        p.append(f"<details><summary>Dettaglio completo</summary>{_dettaglio(r, barra)}</details></div>")
    p.append(f"</div><script>{JS}</script></body></html>")
    dest = out / "_report.html"
    dest.write_text("\n".join(p), encoding="utf-8")
    return dest
