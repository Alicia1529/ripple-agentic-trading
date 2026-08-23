"""Immutable execution-stage operational facts."""

from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Any, Mapping
from urllib.parse import urlsplit

from ._immutable_json import freeze_json, thaw_json, validate_json
from ._validation import (
    require_aware_timestamp,
    require_canonical_uuid,
    require_decimal_string,
    require_nonempty_string,
)


_REQUIRED_FIELDS = {
    "execution_event_id",
    "order_plan_id",
    "account_id",
    "occurred_at",
    "kind",
    "order_id",
    "payload",
}
_PLAN_LEVEL_KINDS = {"planned", "aborted"}
_ORDER_LEVEL_KINDS = {
    "scaled",
    "clipped",
    "submission_started",
    "broker_acknowledged",
    "partially_filled",
    "filled",
    "rejected",
    "unknown",
}
_EVIDENCE_FIELDS = {"uri", "sha256"}
_REASON_CODE = re.compile(r"[a-z][a-z0-9_]*")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _require_reason_code(value: Any, field: str) -> str:
    value = require_nonempty_string(value, field)
    if not _REASON_CODE.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase machine-readable identifier")
    return value


def _validate_evidence(value: Any) -> None:
    if not isinstance(value, Mapping) or set(value) != _EVIDENCE_FIELDS:
        raise ValueError("evidence fields do not match the schema")
    uri = require_nonempty_string(value["uri"], "evidence uri")
    try:
        parsed = urlsplit(uri)
    except ValueError as error:
        raise ValueError("evidence uri must be a valid absolute URI") from error
    if not parsed.scheme or (not parsed.netloc and not parsed.path):
        raise ValueError("evidence uri must be a valid absolute URI")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("evidence uri must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("evidence uri must not contain a query or fragment")
    digest = require_nonempty_string(value["sha256"], "evidence sha256")
    if not _SHA256.fullmatch(digest):
        raise ValueError("evidence sha256 must be 64 lowercase hexadecimal characters")


def _validate_adjustment(payload: Mapping[str, Any]) -> None:
    if set(payload) != {"sizing_field", "original_value", "actual_value", "rule_code"}:
        raise ValueError("adjustment payload fields do not match the schema")
    if payload["sizing_field"] not in ("quantity", "dollar_amount"):
        raise ValueError("sizing_field must be quantity or dollar_amount")
    original = require_decimal_string(payload["original_value"], "original_value")
    actual = require_decimal_string(payload["actual_value"], "actual_value")
    _require_reason_code(payload["rule_code"], "rule_code")
    if not Decimal("0") < Decimal(actual) < Decimal(original):
        raise ValueError("adjustment actual_value must be greater than zero and less than original_value")


def _validate_submission_started(payload: Mapping[str, Any]) -> None:
    if not {"submission_attempt_id"} <= set(payload) <= {"submission_attempt_id", "evidence"}:
        raise ValueError("submission_started payload fields do not match the schema")
    require_canonical_uuid(payload["submission_attempt_id"], "submission_attempt_id")
    if "evidence" in payload:
        _validate_evidence(payload["evidence"])


def _validate_acknowledgement(payload: Mapping[str, Any]) -> None:
    if set(payload) != {"submission_attempt_id", "broker_order_id", "evidence"}:
        raise ValueError("broker_acknowledged payload fields do not match the schema")
    require_canonical_uuid(payload["submission_attempt_id"], "submission_attempt_id")
    require_nonempty_string(payload["broker_order_id"], "broker_order_id")
    _validate_evidence(payload["evidence"])


def _validate_fill(payload: Mapping[str, Any]) -> None:
    required = {
        "submission_attempt_id",
        "broker_order_id",
        "cumulative_quantity",
        "average_price",
        "cumulative_fees",
        "evidence",
    }
    if set(payload) != required:
        raise ValueError("fill payload fields do not match the schema")
    require_canonical_uuid(payload["submission_attempt_id"], "submission_attempt_id")
    require_nonempty_string(payload["broker_order_id"], "broker_order_id")
    quantity = require_decimal_string(payload["cumulative_quantity"], "cumulative_quantity")
    price = require_decimal_string(payload["average_price"], "average_price")
    fees = require_decimal_string(payload["cumulative_fees"], "cumulative_fees")
    if Decimal(quantity) <= 0 or Decimal(price) <= 0 or Decimal(fees) < 0:
        raise ValueError("fill values must have positive quantity and price and non-negative fees")
    _validate_evidence(payload["evidence"])


def _validate_rejection(payload: Mapping[str, Any]) -> None:
    if not {"source", "reason_code"} <= set(payload):
        raise ValueError("rejected payload fields do not match the schema")
    source = payload["source"]
    _require_reason_code(payload["reason_code"], "reason_code")
    if source in ("execution_guard", "risk_engine"):
        if not set(payload) <= {"source", "reason_code", "evidence"}:
            raise ValueError("local rejected payload fields do not match the schema")
        if "evidence" in payload:
            _validate_evidence(payload["evidence"])
        return
    if source != "broker" or not {
        "source",
        "reason_code",
        "submission_attempt_id",
        "evidence",
    } <= set(payload) <= {
        "source",
        "reason_code",
        "submission_attempt_id",
        "broker_order_id",
        "evidence",
    }:
        raise ValueError("broker rejected payload fields do not match the schema")
    require_canonical_uuid(payload["submission_attempt_id"], "submission_attempt_id")
    if "broker_order_id" in payload:
        require_nonempty_string(payload["broker_order_id"], "broker_order_id")
    _validate_evidence(payload["evidence"])


def _validate_payload(kind: str, payload: Any) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    if kind == "planned":
        if payload:
            raise ValueError("planned payload must be empty")
    elif kind == "aborted":
        if not {"reason_code"} <= set(payload) <= {"reason_code", "evidence"}:
            raise ValueError("aborted payload fields do not match the schema")
        _require_reason_code(payload["reason_code"], "reason_code")
        if "evidence" in payload:
            _validate_evidence(payload["evidence"])
    elif kind in {"scaled", "clipped"}:
        _validate_adjustment(payload)
    elif kind == "submission_started":
        _validate_submission_started(payload)
    elif kind == "broker_acknowledged":
        _validate_acknowledgement(payload)
    elif kind in {"partially_filled", "filled"}:
        _validate_fill(payload)
    elif kind == "rejected":
        _validate_rejection(payload)
    elif kind == "unknown":
        if not {"submission_attempt_id", "reason_code"} <= set(payload) <= {
            "submission_attempt_id",
            "reason_code",
            "evidence",
        }:
            raise ValueError("unknown payload fields do not match the schema")
        require_canonical_uuid(payload["submission_attempt_id"], "submission_attempt_id")
        _require_reason_code(payload["reason_code"], "reason_code")
        if "evidence" in payload:
            _validate_evidence(payload["evidence"])


@dataclass(frozen=True, init=False)
class ExecutionEvent:
    execution_event_id: str
    order_plan_id: str
    account_id: str
    occurred_at: str
    kind: str
    order_id: str | None
    payload: Mapping[str, Any]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("ExecutionEvent values must be created with from_dict()")

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "ExecutionEvent":
        if not isinstance(document, Mapping) or set(document) != _REQUIRED_FIELDS:
            raise ValueError("ExecutionEvent fields do not match the schema")
        kind = document["kind"]
        if not isinstance(kind, str):
            raise ValueError("ExecutionEvent kind is not supported")
        if kind not in _PLAN_LEVEL_KINDS | _ORDER_LEVEL_KINDS:
            raise ValueError("ExecutionEvent kind is not supported")
        order_id = document["order_id"]
        if kind in _PLAN_LEVEL_KINDS:
            if order_id is not None:
                raise ValueError("plan-level events must not have an order_id")
        else:
            order_id = require_canonical_uuid(order_id, "order_id")
        _validate_payload(kind, document["payload"])
        validate_json(document)

        event = object.__new__(cls)
        object.__setattr__(event, "execution_event_id", require_canonical_uuid(
            document["execution_event_id"], "execution_event_id"
        ))
        object.__setattr__(event, "order_plan_id", require_canonical_uuid(
            document["order_plan_id"], "order_plan_id"
        ))
        object.__setattr__(event, "account_id", require_nonempty_string(
            document["account_id"], "account_id"
        ))
        object.__setattr__(event, "occurred_at", require_aware_timestamp(
            document["occurred_at"], "occurred_at"
        ))
        object.__setattr__(event, "kind", kind)
        object.__setattr__(event, "order_id", order_id)
        object.__setattr__(event, "payload", freeze_json(document["payload"]))
        return event

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_event_id": self.execution_event_id,
            "order_plan_id": self.order_plan_id,
            "account_id": self.account_id,
            "occurred_at": self.occurred_at,
            "kind": self.kind,
            "order_id": self.order_id,
            "payload": thaw_json(self.payload),
        }
