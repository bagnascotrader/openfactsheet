"""Versioned methodology object (CLAUDE.md section 9)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def _freeze(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in obj.items()})
    if isinstance(obj, list | tuple):
        return tuple(_freeze(v) for v in obj)
    return obj


def _thaw(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {k: _thaw(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return [_thaw(v) for v in obj]
    return obj


@dataclass(frozen=True)
class Methodology:
    """Deterministic, versioned canonical conventions.

    Every report embeds the full methodology so that results remain auditable
    when conventions evolve between releases.
    """

    version: str
    conventions: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "conventions", _freeze(self.conventions))

    def get(self, path: str) -> Any:
        """Look up a convention by dotted path, e.g. ``"tail.var_confidence"``."""
        node: Any = self.conventions
        for part in path.split("."):
            node = node[part]
        return node

    @property
    def name(self) -> str:
        return f"OpenFactsheet Methodology {self.version}"

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "name": self.name, "conventions": _thaw(self.conventions)}

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def describe(self) -> str:
        """Human-readable list of canonical assumptions."""
        c = self.conventions
        ann = c["annualization"]["periods_per_year"]
        lines = [
            self.name,
            "",
            f"Return type:             {c['return_type']} (decimal)",
            "Annualization factors:   "
            + ", ".join(f"{k}={v:g}" for k, v in ann.items())
            + "; irregular/unknown frequency is never annualized",
            f"Risk-free rate:          {c['risk_free']['description']}",
            f"Standard deviation:      {c['dispersion']['description']}",
            f"Annual return:           {c['annual_return']['description']}",
            f"Sortino target (MAR):    {c['downside']['description']}",
            f"Omega threshold:         {c['omega']['description']}",
            f"VaR / ES:                {c['tail']['description']}",
            f"Drawdowns:               {c['drawdown']['description']}",
            f"Skewness / kurtosis:     {c['distribution']['description']}",
            f"Benchmark alignment:     {c['benchmark']['description']}",
            f"Missing data:            {c['missing_data']['description']}",
        ]
        return "\n".join(lines)
