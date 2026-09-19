"""Provider da file: legge una lista partite 2026/27 da JSON locale, zero rete.

Formato file: {"partite": [match-dict, ...]} (vedi esempi/serie_a_2026_27_g5.json).
Serve per usare le partite vere quando l'API free non copre la stagione.
"""
import json
from pathlib import Path
from .base import BaseProvider


class FileListProvider(BaseProvider):
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def get_partite(self) -> list[dict]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "partite" in data:
            return data["partite"]
        if isinstance(data, list):
            return data
        raise ValueError(f"Formato non valido in {self.path}: serve {{'partite': [...]}}")
