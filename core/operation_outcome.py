"""Shared transport/journal interpretation of explicit unknown outcomes."""


def is_unknown_result(result):
    if isinstance(result, dict):
        return result.get('outcome') == 'unknown'
    if isinstance(result, (tuple, list)):
        return any(isinstance(value, dict) and value.get('outcome') == 'unknown' for value in result[1:])
    return False
