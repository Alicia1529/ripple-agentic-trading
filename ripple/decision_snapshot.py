"""Immutable decision-stage input snapshots."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import math
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID


_REQUIRED_FIELDS = {"snapshot_id", "as_of", "universe", "inputs"}


def _validate_json(value: Any) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise ValueError("DecisionSnapshot inputs contain a non-finite number")
    if isinstance(value, list):
        for item in value:
            _validate_json(item)
        return
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("DecisionSnapshot input keys must be strings")
        for item in value.values():
            _validate_json(item)
        return
    raise ValueError("DecisionSnapshot inputs must contain JSON values only")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return deepcopy(value)


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return deepcopy(value)


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
        snapshot_id = document["snapshot_id"]
        if not isinstance(snapshot_id, str):
            raise ValueError("DecisionSnapshot snapshot_id must be a UUID")
        try:
            if str(UUID(snapshot_id)) != snapshot_id:
                raise ValueError
        except ValueError as error:
            raise ValueError("DecisionSnapshot snapshot_id must be a canonical UUID") from error

        as_of = document["as_of"]
        if not isinstance(as_of, str):
            raise ValueError("DecisionSnapshot as_of must be a timestamp")
        try:
            parsed_as_of = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("DecisionSnapshot as_of must be an ISO-8601 timestamp") from error
        if parsed_as_of.utcoffset() is None:
            raise ValueError("DecisionSnapshot as_of must include a timezone offset")

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
        _validate_json(inputs)
        snapshot = object.__new__(cls)
        object.__setattr__(snapshot, "snapshot_id", snapshot_id)
        object.__setattr__(snapshot, "as_of", as_of)
        object.__setattr__(snapshot, "universe", tuple(universe))
        object.__setattr__(snapshot, "inputs", _freeze(inputs))
        return snapshot

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "as_of": self.as_of,
            "universe": list(self.universe),
            "inputs": _thaw(self.inputs),
        }
