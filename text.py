"""Tokenisation shared by the lexical and latent semantic retrievers."""
from __future__ import annotations

import re

_TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset("""a an and are as at be by for from has have in is it its of on or that the this to was
were will with when which than then so if not no can may must should would each any all into over under
between during while before after about up down out off per via also only more most less such these those
their there been being do does did but they them we you your our""".split())


def stem(token: str) -> str:
    """Very light suffix stripping, enough to match 'cooling' with 'cool' and 'zones' with 'zone'."""
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    return [stem(t) for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


def with_bigrams(tokens: list[str]) -> list[str]:
    return tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
