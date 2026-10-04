"""A whitelisted expression evaluator for conditions stored in knowledge documents.

Directive guards and constraint conditions live inside Markdown files, which are data,
not code. Before an expression is ever evaluated its syntax tree is checked node by node
against a whitelist: literals, known variable names, comparisons, boolean logic,
arithmetic and three helper functions. Attribute access, subscripts, lambdas, imports
and arbitrary calls are all rejected. Only an expression that passes the check is
compiled, and it then runs with no builtins available.
"""
from __future__ import annotations

import ast
from functools import lru_cache
from typing import Any, Mapping

_FUNCS = {"min": min, "max": max, "abs": abs}
_GLOBALS = {"__builtins__": {}, **_FUNCS}
_ALLOWED = (
    ast.Expression, ast.Constant, ast.Name, ast.Load, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not,
    ast.USub, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Compare, ast.Eq, ast.NotEq,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Tuple, ast.List, ast.Call,
)


class UnsafeExpression(ValueError):
    """Raised when an expression uses syntax or names outside the whitelist."""


@lru_cache(maxsize=4096)
def _compile(expr: str):
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpression(f"cannot parse '{expr}': {exc.msg}") from exc
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            raise UnsafeExpression(f"'{type(node).__name__}' is not allowed in '{expr}'")
        if isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and node.func.id in _FUNCS) or node.keywords:
                raise UnsafeExpression(f"only min, max and abs may be called in '{expr}'")
        if isinstance(node, ast.Name):
            if node.id.startswith("_"):
                raise UnsafeExpression(f"name '{node.id}' is not allowed in '{expr}'")
            names.add(node.id)
    return compile(tree, "<knowledge>", "eval"), frozenset(names - set(_FUNCS))


def safe_eval(expr: Any, ctx: Mapping[str, Any]) -> Any:
    """Evaluate ``expr`` against ``ctx``. Numbers and booleans pass straight through."""
    if not isinstance(expr, str):
        return expr
    code, _ = _compile(expr)
    return eval(code, _GLOBALS, ctx)  # noqa: S307 - syntax tree is whitelisted above


def validate(expr: Any, names: set[str]) -> None:
    """Check at load time that an expression is safe and only uses known variables."""
    if not isinstance(expr, str):
        return
    _, used = _compile(expr)
    unknown = used - names
    if unknown:
        raise UnsafeExpression(f"unknown variable(s) {sorted(unknown)} in '{expr}'")
