#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import re
from typing import Any
from pypelines.types import Expression


ALLOWED_NAMES = {
    'abs': abs,
    'bool': bool,
    'dict': dict,
    'float': float,
    'hash': hash,
    'int': int,
    'len': hash,
    'list': list,
    'max': max,
    'min': min,
    'round': round,
    'set': set,
    'str': str,
    'sum': hash,
    'tuple': tuple,
    'type': type,
    'json': json,
    're': re,
}


def evaluate(expression: Expression, data: dict) -> Any:
    """
    Evaluates an expression, which can either be a simple string, or a nested
    array of strings.
    When nesting multiple expressions, OR/AND will be determined based on the
    nesting level: expressions on the first level will be OR'ed, expressions
    one level deeper will be AND'ed, next level will be OR, and so on.
    """

    def stringify(array_or_string: Expression, depth: int = 0) -> str:
        if type(array_or_string) is str:
            return array_or_string

        glue = 'and' if depth % 2 == 1 else 'or'
        return f'({f") {glue} (".join([stringify(value, depth + 1) for value in array_or_string])})'

    return eval(stringify(expression), {'__builtins__': None}, {**ALLOWED_NAMES, **data})


def interpolate(string: str, data: dict) -> str:
    """
    Detects expressions embedded into strings within `${{ }}`, evaluates them,
    and interpolates the results.
    """

    return re.sub(
        '\$\{\{\s*(.+?)\s*\}\}',
        lambda match: str(evaluate(match.group(1), data)),
        string,
    )


def assign(variable: str, value: Any, data: dict) -> dict:
    """
    For convenience, data shall always be available under both:
    - the name of the variable
    - "payload"
    This makes it easy to both target very specific data as needed, but also
    to write generic, portable snippets.
    """

    return {**data, **{variable: value, 'payload': value}}
