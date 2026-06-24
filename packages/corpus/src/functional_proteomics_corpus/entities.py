"""Deterministic dictionary entity tagging for the v0.1 corpus."""

from __future__ import annotations

import re

ENTITY_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("IL-10", ("IL-10", "interleukin 10")),
    ("LPS", ("LPS", "lipopolysaccharide")),
    ("PBMC", ("PBMC", "peripheral blood mononuclear cells")),
    ("nELISA", ("nELISA",)),
    ("TNF alpha", ("TNF alpha", "TNF-alpha")),
    ("IL-1 beta", ("IL-1 beta",)),
    ("IL-1 alpha", ("IL-1 alpha",)),
    ("IL-6", ("IL-6",)),
    ("IL-12 p40", ("IL-12 p40",)),
    ("IFN gamma", ("IFN gamma", "IFN-gamma")),
    ("CCL1", ("CCL1",)),
    ("CCL22", ("CCL22",)),
    ("CCL24", ("CCL24",)),
    ("G-CSF", ("G-CSF",)),
    ("GM-CSF", ("GM-CSF",)),
    ("secretome", ("secretome",)),
    ("cytokine", ("cytokine", "cytokines")),
    ("monocyte", ("monocyte", "monocytes")),
    ("macrophage", ("macrophage", "macrophages")),
    ("whole blood", ("whole blood",)),
    ("donor", ("donor", "donors")),
    ("perturbation", ("perturbation", "perturbations")),
)

ASSAY_CONTEXT_ENTITIES = frozenset(
    {
        "secretome",
        "cytokine",
        "monocyte",
        "macrophage",
        "whole blood",
        "donor",
        "perturbation",
    }
)

_ALIAS_TO_CANONICAL = {
    alias.casefold(): canonical for canonical, aliases in ENTITY_ALIASES for alias in aliases
}


def normalize_entity(value: str) -> str:
    """Return the canonical v0.1 entity name when ``value`` is a known alias."""

    return _ALIAS_TO_CANONICAL.get(value.casefold(), value)


def tag_entities(text: str) -> list[str]:
    """Tag corpus text with the deterministic v0.1 dictionary."""

    matches: list[str] = []
    seen: set[str] = set()
    for canonical, aliases in ENTITY_ALIASES:
        if canonical in seen:
            continue
        if any(_contains_alias(text, alias) for alias in aliases):
            seen.add(canonical)
            matches.append(canonical)
    return matches


def assay_context_tags(entities: list[str]) -> list[str]:
    """Return the subset of entity tags used as assay/context tags."""

    return [entity for entity in entities if entity in ASSAY_CONTEXT_ENTITIES]


def _contains_alias(text: str, alias: str) -> bool:
    pattern = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])",
        flags=re.IGNORECASE,
    )
    return pattern.search(text) is not None
