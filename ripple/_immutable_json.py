"""Internal helpers for validated, immutable JSON documents."""

from copy import deepcopy
import math
from types import MappingProxyType
from typing import Any, Mapping


def validate_json(value: Any) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise ValueError("Document contains a non-finite number")
    if isinstance(value, list):
        for item in value:
            validate_json(item)
        return
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("Document keys must be strings")
        for item in value.values():
            validate_json(item)
        return
    raise ValueError("Document must contain JSON values only")


def freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(freeze_json(item) for item in value)
    return deepcopy(value)


def thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw_json(item) for item in value]
    return deepcopy(value)
