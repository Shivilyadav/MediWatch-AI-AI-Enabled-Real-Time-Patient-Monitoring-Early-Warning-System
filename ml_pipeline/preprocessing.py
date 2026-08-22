"""Leakage-safe preprocessing primitives for future MediWatch model training.

Stage 2 deliberately performs median imputation only. Statistics are fit on
training rows and can be applied to validation/test rows without refitting.
No temporal interpolation, backfill, rolling feature, scaling, or label change
is performed here.
"""

from __future__ import annotations

import math
import json
from statistics import median
from pathlib import Path
from typing import Iterable, Mapping


class TrainingOnlyMedianImputer:
    """Median imputer whose fit and transform phases are deliberately separate."""

    def __init__(self, features: Iterable[str]):
        self.features = tuple(features)
        self.medians_: dict[str, float] | None = None

    @staticmethod
    def _as_number(value: object) -> float | None:
        if value is None or value == "":
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    def fit(self, rows: Iterable[Mapping[str, object]]) -> "TrainingOnlyMedianImputer":
        values = {feature: [] for feature in self.features}
        for row in rows:
            for feature in self.features:
                number = self._as_number(row.get(feature))
                if number is not None:
                    values[feature].append(number)
        empty = [feature for feature, observed in values.items() if not observed]
        if empty:
            raise ValueError(f"Cannot fit median imputer; all values missing for {empty}")
        self.medians_ = {feature: float(median(observed)) for feature, observed in values.items()}
        return self

    def transform(self, rows: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
        if self.medians_ is None:
            raise RuntimeError("Imputer must be fit on training data before transform")
        transformed: list[dict[str, object]] = []
        for row in rows:
            output = dict(row)
            for feature in self.features:
                number = self._as_number(row.get(feature))
                output[feature] = self.medians_[feature] if number is None else number
            transformed.append(output)
        return transformed

    def fit_transform(self, rows: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
        rows = list(rows)
        return self.fit(rows).transform(rows)

    def to_dict(self) -> dict[str, object]:
        if self.medians_ is None:
            raise RuntimeError("Cannot serialize an unfitted imputer")
        return {"type": "training_only_median_imputer", "features": list(self.features), "medians": self.medians_}

    def save(self, path: Path) -> None:
        """Persist only training-fitted parameters for later validation/test inference."""
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
