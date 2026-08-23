"""Immutable decision-stage input snapshots."""

from dataclasses import dataclass
from typing import Any, Mapping

from ._immutable_json import freeze_json, thaw_json, validate_json
from ._validation import require_aware_timestamp, require_canonical_uuid


_REQUIRED_FIELDS = {"snapshot_id", "as_of", "universe", "inputs"}


@dataclass(frozen=True, init=False)
class DecisionSnapshot:
    snapshot_id: str
    as_of: str
    universe: tuple[str, ...]
    inputs: Mapping[str, Any]

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "DecisionSnapshot":
        if not isinstance(document, Mapping) or set(document) != _REQUIRED_FIELDS:
            raise ValueError("DecisionSnapshot fields do not match the schema")
        snapshot_id = require_canonical_uuid(document["snapshot_id"], "snapshot_id")
        as_of = require_aware_timestamp(document["as_of"], "as_of")

        universe = document["universe"]
        if (
            not isinstance(universe, list)
            or not universe
            or not all(isinstance(symbol, str) and symbol for symbol in universe)
            or len(set(universe)) != len(universe)
        ):
            raise ValueError("DecisionSnapshot universe must contain unique symbols")

        inputs = document["inputs"]
        if not isinstance(inputs, Mapping):
            raise ValueError("DecisionSnapshot inputs must be an object")
        validate_json(inputs)
        snapshot = object.__new__(cls)
        object.__setattr__(snapshot, "snapshot_id", snapshot_id)
        object.__setattr__(snapshot, "as_of", as_of)
        object.__setattr__(snapshot, "universe", tuple(universe))
        object.__setattr__(snapshot, "inputs", freeze_json(inputs))
        return snapshot

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "as_of": self.as_of,
            "universe": list(self.universe),
            "inputs": thaw_json(self.inputs),
        }
