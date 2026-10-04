"""Tolerant parsing of model output into a validated ``Proposal``.

Language models wrap JSON in prose and code fences, and occasionally truncate it. The
parser extracts the first balanced JSON object and validates it against the schema. It
never guesses at missing content: anything that cannot be validated raises
``ParseError`` and the agent falls back to the deterministic reasoner.
"""
from __future__ import annotations

import json

from pydantic import ValidationError

from .schema import Proposal


class ParseError(ValueError):
    pass


def extract_json(text: str) -> str:
    start = text.find("{")
    if start < 0:
        raise ParseError("no JSON object found in model output")
    depth, in_string, escaped = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start: i + 1]
    raise ParseError("JSON object is not closed (output was probably truncated)")


def parse_proposal(text: str) -> Proposal:
    try:
        return Proposal.model_validate(json.loads(extract_json(text)))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ParseError(str(exc).splitlines()[0]) from exc
