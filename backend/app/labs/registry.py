"""Registry for pluggable FDE Labs."""
from __future__ import annotations

from importlib import import_module
from typing import Type

from app.labs.base import BaseLab
from app.labs.catalog import LABS_BY_ID


LAB_CLASSES: dict[str, Type[BaseLab]] = {}
BUILTIN_LAB_MODULES = [
    "app.labs.evaluators.rag_grounding",
    "app.labs.evaluators.model_routing_cost",
    "app.labs.evaluators.agent_workflow",
    "app.labs.evaluators.roi_solutions",
    "app.labs.evaluators.grc_eu_ai_act",
    "app.labs.evaluators.market_intelligence",
]


def register_lab(lab_id: str):
    """Register a lab class by catalog id.

    New labs should:

    1. add a `LabDefinition` in `catalog.py`;
    2. implement `BaseLab`;
    3. decorate the class with `@register_lab("your_lab_id")`.
    """
    def decorator(cls: Type[BaseLab]) -> Type[BaseLab]:
        if lab_id in LAB_CLASSES and LAB_CLASSES[lab_id] is not cls:
            raise ValueError(f"Duplicate lab registration for {lab_id}")
        if lab_id not in LABS_BY_ID:
            raise KeyError(f"Lab {lab_id!r} is not defined in catalog.py")
        LAB_CLASSES[lab_id] = cls
        return cls

    return decorator


def load_builtin_labs() -> None:
    for module in BUILTIN_LAB_MODULES:
        import_module(module)


def make_lab(lab_id: str) -> BaseLab:
    load_builtin_labs()
    if lab_id not in LAB_CLASSES:
        raise KeyError(f"Unknown lab_id: {lab_id}")
    return LAB_CLASSES[lab_id](LABS_BY_ID[lab_id])


load_builtin_labs()
