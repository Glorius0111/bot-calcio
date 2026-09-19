"""Provider dati: interfaccia comune per automazione tutte le partite.

Ogni provider deve implementare get_partite() -> list[dict match].
Il dict match è quello già usato da bot.report.genera_report.
"""
from abc import ABC, abstractmethod


class BaseProvider(ABC):
    @abstractmethod
    def get_partite(self) -> list[dict]:
        """Ritorna lista di match-dict pronti per genera_report."""
        raise NotImplementedError
