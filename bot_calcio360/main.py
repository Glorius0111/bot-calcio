"""CLI Bot Statistico Calcio a 360°.

Uso:
  python main.py esempi/esempio_milan_napoli.json
  python main.py esempi/esempio_milan_napoli.json --soglia-angoli 9.5 --soglia-tiri 5.5
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bot.report import genera_report


def main():
    ap = argparse.ArgumentParser(description="Bot Statistico Calcio a 360°")
    ap.add_argument("input", help="File JSON partita (vedi esempi/)")
    ap.add_argument("--soglia-angoli", type=float, default=None)
    ap.add_argument("--soglia-tiri", type=float, default=None)
    ap.add_argument("--soglia-cartellini", type=float, default=None)
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if args.soglia_angoli is not None:
        data["soglia_angoli"] = args.soglia_angoli
    if args.soglia_tiri is not None:
        data["soglia_tiri"] = args.soglia_tiri
    if args.soglia_cartellini is not None:
        data["soglia_cartellini"] = args.soglia_cartellini

    rep = genera_report(data)
    print(rep.testo)


if __name__ == "__main__":
    main()
