# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from settings_registry import SettingSpec, ValueType

_INT_RE = re.compile(r"^[+-]?(?:0|[1-9][0-9]*)$")
_FLOAT_RE = re.compile(r"^[+-]?(?:(?:0|[1-9][0-9]*)(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")
_TIME_RE = re.compile(r"^(?P<hour>[0-9]|[01][0-9]|2[0-3]):(?P<minute>[0-5][0-9])$")
_MM_DD_RE = re.compile(r"^(?P<month>0[1-9]|1[0-2])-(?P<day>0[1-9]|[12][0-9]|3[01])$")


@dataclass(frozen=True)
class ParseIssue:
    code: str
    key: str
    message_id: str
    blocking: bool = True


@dataclass(frozen=True)
class ParseResult:
    value: Any = None
    issue: Optional[ParseIssue] = None

    @property
    def ok(self) -> bool:
        return self.issue is None


def _issue(spec: SettingSpec, code: str) -> ParseResult:
    return ParseResult(issue=ParseIssue(code=code, key=spec.key, message_id=code))


def _parse_int(spec: SettingSpec, raw: Any, optional: bool = False, zero_none: bool = False) -> ParseResult:
    if raw is None or (optional and raw == ""):
        return ParseResult(value=None) if optional else _issue(spec, "PARSE_INT_REQUIRED")
    if isinstance(raw, bool):
        return _issue(spec, "PARSE_INT_BOOL_NOT_ALLOWED")
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, str) and _INT_RE.fullmatch(raw):
        value = int(raw, 10)
    else:
        return _issue(spec, "PARSE_INT_INVALID")
    if zero_none and value == 0:
        return ParseResult(value=None)
    if spec.minimum is not None and value < spec.minimum:
        return _issue(spec, "PARSE_VALUE_BELOW_MINIMUM")
    if spec.maximum is not None and value > spec.maximum:
        return _issue(spec, "PARSE_VALUE_ABOVE_MAXIMUM")
    return ParseResult(value=value)


def _parse_float(spec: SettingSpec, raw: Any) -> ParseResult:
    if isinstance(raw, bool):
        return _issue(spec, "PARSE_FLOAT_BOOL_NOT_ALLOWED")
    if isinstance(raw, (int, float)):
        value = float(raw)
    elif isinstance(raw, str) and _FLOAT_RE.fullmatch(raw):
        value = float(raw)
    else:
        return _issue(spec, "PARSE_FLOAT_INVALID")
    if not math.isfinite(value):
        return _issue(spec, "PARSE_FLOAT_NON_FINITE")
    if spec.minimum is not None and value < spec.minimum:
        return _issue(spec, "PARSE_VALUE_BELOW_MINIMUM")
    if spec.maximum is not None and value > spec.maximum:
        return _issue(spec, "PARSE_VALUE_ABOVE_MAXIMUM")
    return ParseResult(value=value)


def parse_value(spec: SettingSpec, raw: Any) -> ParseResult:
    """Strict, side-effect-free parse. Issues never include the raw value."""
    if spec.codec_id == "optional_int_zero_none":
        return _parse_int(spec, raw, optional=True, zero_none=True)
    if spec.value_type is ValueType.INT:
        return _parse_int(spec, raw)
    if spec.value_type is ValueType.OPTIONAL_INT:
        return _parse_int(spec, raw, optional=True)
    if spec.value_type is ValueType.FLOAT:
        return _parse_float(spec, raw)
    if spec.value_type is ValueType.BOOL:
        if raw is True or raw is False:
            return ParseResult(value=raw)
        if raw == "true":
            return ParseResult(value=True)
        if raw == "false":
            return ParseResult(value=False)
        return _issue(spec, "PARSE_BOOL_INVALID")
    if spec.value_type in (ValueType.STRING, ValueType.SECRET):
        if raw is None and (spec.default_new_install is None or spec.default_rc19 is None):
            return ParseResult(value=None)
        if not isinstance(raw, str):
            return _issue(spec, "PARSE_STRING_INVALID")
        return ParseResult(value=raw)
    if spec.value_type is ValueType.ENUM:
        if not isinstance(raw, str):
            return _issue(spec, "PARSE_ENUM_INVALID_TYPE")
        if raw not in spec.option_values:
            return _issue(spec, "PARSE_ENUM_UNKNOWN_VALUE")
        return ParseResult(value=raw)
    if spec.value_type is ValueType.TIME_HH_MM:
        if not isinstance(raw, str):
            return _issue(spec, "PARSE_TIME_INVALID_TYPE")
        match = _TIME_RE.fullmatch(raw)
        if not match:
            return _issue(spec, "PARSE_TIME_INVALID")
        return ParseResult(value="{:02d}:{}".format(int(match.group("hour")), match.group("minute")))
    if spec.value_type is ValueType.OPTIONAL_MM_DD:
        if raw is None or raw == "":
            return ParseResult(value=None)
        if not isinstance(raw, str):
            return _issue(spec, "PARSE_MM_DD_INVALID_TYPE")
        match = _MM_DD_RE.fullmatch(raw)
        if not match:
            return _issue(spec, "PARSE_MM_DD_INVALID")
        month, day = int(match.group("month")), int(match.group("day"))
        month_lengths = (0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
        if day > month_lengths[month]:
            return _issue(spec, "PARSE_MM_DD_INVALID_CALENDAR_DAY")
        return ParseResult(value=raw)
    return _issue(spec, "PARSE_CODEC_UNSUPPORTED")


def format_value(spec: SettingSpec, value: Any) -> str:
    if spec.value_type is ValueType.SECRET:
        return "set" if value else "not_set"
    if value is None:
        return ""
    if spec.value_type is ValueType.BOOL:
        return "true" if value else "false"
    if spec.value_type is ValueType.FLOAT:
        return format(value, ".15g")
    return str(value)
