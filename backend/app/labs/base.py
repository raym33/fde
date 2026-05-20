import asyncio
import concurrent.futures
from abc import ABC, abstractmethod
from typing import Any, Coroutine

from app.labs.schemas import CoreReportDraft, LabDefinition, LabRunResult


class BaseLab(ABC):
    def __init__(self, definition: LabDefinition) -> None:
        self.definition = definition

    @abstractmethod
    def run(self) -> LabRunResult:
        """Run a deterministic experiment and return measured scores."""

    @abstractmethod
    def build_report(self, result: LabRunResult) -> CoreReportDraft:
        """Build a human-reviewable report from a successful run."""


def weighted_score(parts: dict[str, tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in parts.values())
    if total_weight <= 0:
        return 0.0
    return round(sum(score * weight for score, weight in parts.values()) / total_weight, 2)


def run_coro(coro: Coroutine[Any, Any, Any]) -> Any:
    """Ejecuta una corrutina desde código síncrono de forma segura.

    Los labs corren de forma síncrona (smoke CLI y endpoints `def` que FastAPI
    despacha en un threadpool). Si no hay event loop activo usamos asyncio.run;
    si lo hubiera, ejecutamos en un hilo aparte con su propio loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(lambda: asyncio.run(coro)).result()

